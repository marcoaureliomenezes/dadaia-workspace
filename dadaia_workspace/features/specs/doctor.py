"""SpecsDoctor — structural validation for SDD release-lifecycle specs (HTML memory).

Runs the 11 structural checks defined in release `sdd-release-lifecycle-v1`,
extended for the product memory folder catalog (release `Product Memory Feature
Catalog v1`):

  1. specs/constitution.md exists
  2. specs/memory/architecture.html and tech-stack.html exist, parseable, with non-empty
     <h1>; specs/memory/product/index.html exists (folder catalog entry); legacy
     product.html at memory/ root reported as error; broken <a href> links from
     product/index.html reported as error
  3. specs/releases/ACTIVE.md exists, parseable, phase canonical
  4. active release has SPEC+PLAN+TASKS with Status: Aprovado (warn if Draft + phase != ARCHIVED)
  5. PLAN <= 300 lines (warning <= 2026-05-16; error >= 2026-05-17)
  6. each _archive/releases/<id>/ has CLOSURE.md with 4 mandatory sections + >=1 evidence triple
  7. no SPEC/PLAN/TASKS outside releases/*/ or _archive/releases/*/ (warn during legacy window)
  8. no <section class="changelog"> or <h2> matching Changelog|History|Histórico|Versions? in any memory HTML
  9. release id in ACTIVE.md corresponds to a real directory
 10. every <img src> in any memory HTML resolves to a real file
 11. memory HTML containing <pre class="mermaid"> has the Mermaid CDN <script>

Pure module — no I/O outside the supplied specs_dir. No external dependencies.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from enum import Enum
from html.parser import HTMLParser
from pathlib import Path

CANONICAL_STATUS = {"Draft", "Em revisão", "Aprovado"}
CANONICAL_PHASES = {
    "DISCOVERY",
    "SPEC",
    "PLAN",
    "TASKS",
    "IMPLEMENTATION",
    "CLOSURE",
    "ARCHIVED",
    "none",  # scaffold default: no active release
}
BACKLOG_BULLET_RE = re.compile(
    r"^- \S.*? — .+? \(owner: [a-z-]+, contexto: .+?\)\s*$"
)
FORBIDDEN_MEMORY_H2_RE = re.compile(
    r"^(Changelog|History|Hist[óo]rico|Versions?)\b", re.IGNORECASE
)
# Top-level memory files (still single HTML).
TOPLEVEL_MEMORY_FILES = ("architecture.html", "tech-stack.html")
# Product memory is a folder catalog: index.html is required + 0..N feature HTMLs.
PRODUCT_INDEX_REL = "product/index.html"
HARD_LIMIT_PLAN_CUTOFF = date(2026, 5, 17)
PLAN_MAX_LINES = 300


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class SpecsDoctorIssue:
    code: str
    severity: Severity
    description: str
    path: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "code": self.code,
            "severity": self.severity.value,
            "description": self.description,
            "path": self.path,
        }


@dataclass
class _MemoryHtmlSummary:
    has_h1: bool
    h1_text: str
    forbidden_h2: list[str]
    img_srcs: list[str]
    anchor_hrefs: list[str]
    has_mermaid_blocks: bool
    has_mermaid_script: bool


class _MemoryParser(HTMLParser):
    """Lightweight extractor for the few HTML facts the doctor needs."""

    def __init__(self) -> None:
        super().__init__()
        self._tag_stack: list[tuple[str, dict[str, str]]] = []
        self._current_text: list[str] = []
        self.h1_text = ""
        self.has_h1 = False
        self.forbidden_h2: list[str] = []
        self.img_srcs: list[str] = []
        self.anchor_hrefs: list[str] = []
        self.has_mermaid_blocks = False
        self.has_mermaid_script = False
        self._in_h1 = False
        self._in_h2 = False
        self._h2_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {k: (v or "") for k, v in attrs}
        self._tag_stack.append((tag, attr_map))
        if tag == "h1":
            self._in_h1 = True
            self._current_text = []
        elif tag == "h2":
            self._in_h2 = True
            self._h2_text = []
        elif tag == "img":
            src = attr_map.get("src", "")
            if src:
                self.img_srcs.append(src)
        elif tag == "a":
            href = attr_map.get("href", "")
            if href:
                self.anchor_hrefs.append(href)
        elif tag == "pre":
            if "mermaid" in attr_map.get("class", "").split():
                self.has_mermaid_blocks = True
        elif tag == "section":
            klass = attr_map.get("class", "")
            if "changelog" in klass.split():
                self.forbidden_h2.append(f"section class={klass!r}")
        elif tag == "script":
            src = attr_map.get("src", "")
            if "mermaid" in src.lower():
                self.has_mermaid_script = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "h1" and self._in_h1:
            self._in_h1 = False
            self.h1_text = "".join(self._current_text).strip()
            self.has_h1 = bool(self.h1_text)
        elif tag == "h2" and self._in_h2:
            self._in_h2 = False
            text = "".join(self._h2_text).strip()
            if text and FORBIDDEN_MEMORY_H2_RE.search(text):
                self.forbidden_h2.append(text)
        if self._tag_stack and self._tag_stack[-1][0] == tag:
            self._tag_stack.pop()

    def handle_data(self, data: str) -> None:
        if self._in_h1:
            self._current_text.append(data)
        elif self._in_h2:
            self._h2_text.append(data)


def _parse_memory_html(path: Path) -> _MemoryHtmlSummary:
    parser = _MemoryParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return _MemoryHtmlSummary(
        has_h1=parser.has_h1,
        h1_text=parser.h1_text,
        forbidden_h2=parser.forbidden_h2,
        img_srcs=parser.img_srcs,
        anchor_hrefs=parser.anchor_hrefs,
        has_mermaid_blocks=parser.has_mermaid_blocks,
        has_mermaid_script=parser.has_mermaid_script,
    )


def _iter_memory_html_files(mem_dir: Path) -> list[Path]:
    """All memory HTML files that should be checked for atomicity/imgs/mermaid.

    Includes the top-level singles (architecture.html, tech-stack.html) and every
    *.html under product/ (the catalog folder).
    """
    out: list[Path] = []
    for name in TOPLEVEL_MEMORY_FILES:
        p = mem_dir / name
        if p.exists():
            out.append(p)
    product_dir = mem_dir / "product"
    if product_dir.is_dir():
        out.extend(sorted(product_dir.glob("*.html")))
    return out


def _read_active_md(path: Path) -> tuple[str | None, str | None, str | None]:
    """Returns (release_id, phase, error_message_or_none)."""
    if not path.exists():
        return None, None, "ACTIVE.md not found"
    text = path.read_text(encoding="utf-8")
    release = None
    phase = None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("release:"):
            value = line.split(":", 1)[1].strip()
            release = value if value else None
        elif line.startswith("phase:"):
            value = line.split(":", 1)[1].strip()
            phase = value if value else None
    if release is None or phase is None:
        return release, phase, "ACTIVE.md missing 'release:' or 'phase:' line"
    return release, phase, None


def _extract_status(md_path: Path) -> str | None:
    if not md_path.exists():
        return None
    for line in md_path.read_text(encoding="utf-8").splitlines()[:30]:
        m = re.search(r"\*\*Status:\*\*\s*(.+?)\s*$", line)
        if m:
            return m.group(1).strip()
    return None


def _extract_created_date(md_path: Path) -> date | None:
    if not md_path.exists():
        return None
    for line in md_path.read_text(encoding="utf-8").splitlines()[:30]:
        m = re.search(r"\*\*Created:\*\*\s*(\d{4}-\d{2}-\d{2})", line)
        if m:
            try:
                y, mo, d = (int(x) for x in m.group(1).split("-"))
                return date(y, mo, d)
            except ValueError:
                return None
    return None


class SpecsDoctor:
    """Diagnose specs/ structure under SDD release-lifecycle."""

    def __init__(self, specs_dir: Path) -> None:
        self.specs_dir = Path(specs_dir)

    def check(self) -> list[SpecsDoctorIssue]:
        issues: list[SpecsDoctorIssue] = []
        issues.extend(self._check_constitution())
        issues.extend(self._check_memory_files())
        issues.extend(self._check_active_md())
        issues.extend(self._check_active_release_artifacts())
        issues.extend(self._check_plan_line_limit())
        issues.extend(self._check_archive_closures())
        issues.extend(self._check_no_orphan_specs())
        issues.extend(self._check_memory_atomicity())
        # 9: covered inside _check_active_md (release id ↔ dir)
        issues.extend(self._check_memory_image_links())
        issues.extend(self._check_memory_mermaid_script())
        issues.extend(self._check_backlog_schema())
        return issues

    # 1
    def _check_constitution(self) -> list[SpecsDoctorIssue]:
        path = self.specs_dir / "constitution.md"
        if not path.exists():
            return [
                SpecsDoctorIssue(
                    code="SPEC-DOC-001",
                    severity=Severity.ERROR,
                    description="specs/constitution.md is missing",
                    path=str(path),
                )
            ]
        return []

    # 2 + helper used by 8, 10, 11
    def _check_memory_files(self) -> list[SpecsDoctorIssue]:
        issues: list[SpecsDoctorIssue] = []
        mem_dir = self.specs_dir / "memory"

        # Required top-level singles
        required: list[tuple[str, Path]] = [
            (name, mem_dir / name) for name in TOPLEVEL_MEMORY_FILES
        ]
        # Required folder catalog entry
        required.append((PRODUCT_INDEX_REL, mem_dir / PRODUCT_INDEX_REL))

        # Plus any optional feature HTMLs that DO exist — they must parse too
        product_dir = mem_dir / "product"
        feature_files: list[tuple[str, Path]] = []
        if product_dir.is_dir():
            feature_files = [
                (f"product/{p.name}", p)
                for p in sorted(product_dir.glob("*.html"))
                if p.name != "index.html"
            ]

        for rel, p in required + feature_files:
            if not p.exists():
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-002",
                        severity=Severity.ERROR,
                        description=f"memory/{rel} is missing — memory must be HTML",
                        path=str(p),
                    )
                )
                continue
            try:
                summary = _parse_memory_html(p)
            except Exception as e:
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-002",
                        severity=Severity.ERROR,
                        description=f"memory/{rel} is not parseable HTML: {e}",
                        path=str(p),
                    )
                )
                continue
            if not summary.has_h1:
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-002",
                        severity=Severity.ERROR,
                        description=f"memory/{rel} has no non-empty <h1>",
                        path=str(p),
                    )
                )

        # Legacy product.html at memory/ root (pre-folder-catalog) is now an error
        legacy_product = mem_dir / "product.html"
        if legacy_product.exists():
            issues.append(
                SpecsDoctorIssue(
                    code="SPEC-DOC-002L",
                    severity=Severity.ERROR,
                    description=(
                        "memory/product.html is legacy — product memory is now a folder "
                        "catalog. Move to _archive/legacy-memory/<timestamp>/ and create "
                        "memory/product/index.html + memory/product/<feature>.html files."
                    ),
                    path=str(legacy_product),
                )
            )

        # Flag any legacy markdown memory files (root or product/)
        if mem_dir.exists():
            for legacy in mem_dir.glob("*.md"):
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-002L",
                        severity=Severity.ERROR,
                        description=(
                            f"memory/{legacy.name} is markdown — memory must be HTML. "
                            "Move legacy markdown to _archive/legacy-memory/<timestamp>/."
                        ),
                        path=str(legacy),
                    )
                )
            if product_dir.is_dir():
                for legacy in product_dir.glob("*.md"):
                    issues.append(
                        SpecsDoctorIssue(
                            code="SPEC-DOC-002L",
                            severity=Severity.ERROR,
                            description=(
                                f"memory/product/{legacy.name} is markdown — memory must be HTML."
                            ),
                            path=str(legacy),
                        )
                    )

        # Broken <a href> links from product/index.html
        index_path = mem_dir / PRODUCT_INDEX_REL
        if index_path.exists():
            try:
                index_summary = _parse_memory_html(index_path)
            except Exception:
                index_summary = None
            if index_summary is not None:
                for href in index_summary.anchor_hrefs:
                    if href.startswith(("http://", "https://", "mailto:", "#")):
                        continue
                    target = (index_path.parent / href).resolve()
                    if not target.exists():
                        issues.append(
                            SpecsDoctorIssue(
                                code="SPEC-DOC-002",
                                severity=Severity.ERROR,
                                description=(
                                    f"memory/product/index.html links to missing file: "
                                    f"<a href=\"{href}\"> (resolves to {target})"
                                ),
                                path=str(index_path),
                            )
                        )

        return issues

    # 3 + 9
    def _check_active_md(self) -> list[SpecsDoctorIssue]:
        issues: list[SpecsDoctorIssue] = []
        path = self.specs_dir / "releases" / "ACTIVE.md"
        release, phase, err = _read_active_md(path)
        if err:
            issues.append(
                SpecsDoctorIssue(
                    code="SPEC-DOC-003",
                    severity=Severity.ERROR,
                    description=err,
                    path=str(path),
                )
            )
            return issues
        if phase not in CANONICAL_PHASES:
            issues.append(
                SpecsDoctorIssue(
                    code="SPEC-DOC-003",
                    severity=Severity.ERROR,
                    description=(
                        f"ACTIVE.md phase '{phase}' is not canonical. "
                        f"Valid: {sorted(CANONICAL_PHASES)}"
                    ),
                    path=str(path),
                )
            )
        if release and release != "none":
            release_dir = self.specs_dir / "releases" / release
            if not release_dir.exists():
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-009",
                        severity=Severity.ERROR,
                        description=(
                            f"ACTIVE.md release='{release}' but no directory at {release_dir}"
                        ),
                        path=str(release_dir),
                    )
                )
        return issues

    # 4
    def _check_active_release_artifacts(self) -> list[SpecsDoctorIssue]:
        issues: list[SpecsDoctorIssue] = []
        path = self.specs_dir / "releases" / "ACTIVE.md"
        release, phase, err = _read_active_md(path)
        if err or not release or release == "none":
            return issues
        rdir = self.specs_dir / "releases" / release
        if not rdir.exists():
            return issues  # already reported by check 9
        for fname in ("SPEC.md", "PLAN.md", "TASKS.md"):
            fpath = rdir / fname
            if not fpath.exists():
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-004",
                        severity=Severity.ERROR,
                        description=f"Active release missing {fname}",
                        path=str(fpath),
                    )
                )
                continue
            status = _extract_status(fpath)
            if status is None:
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-004",
                        severity=Severity.ERROR,
                        description=f"{fname} has no `**Status:**` line",
                        path=str(fpath),
                    )
                )
            elif status not in CANONICAL_STATUS:
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-004",
                        severity=Severity.ERROR,
                        description=(
                            f"{fname} Status='{status}' is not canonical. "
                            f"Valid: {sorted(CANONICAL_STATUS)}"
                        ),
                        path=str(fpath),
                    )
                )
            elif status != "Aprovado" and phase != "ARCHIVED":
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-004",
                        severity=Severity.WARNING,
                        description=(
                            f"{fname} is '{status}' but ACTIVE.md phase is '{phase}'; "
                            "expected 'Aprovado' for implementation-bound phases"
                        ),
                        path=str(fpath),
                    )
                )
        return issues

    # 5
    def _check_plan_line_limit(self) -> list[SpecsDoctorIssue]:
        issues: list[SpecsDoctorIssue] = []
        for plan in self.specs_dir.glob("releases/*/PLAN.md"):
            n_lines = sum(1 for _ in plan.read_text(encoding="utf-8").splitlines())
            if n_lines <= PLAN_MAX_LINES:
                continue
            spec = plan.with_name("SPEC.md")
            created = _extract_created_date(spec) if spec.exists() else None
            severity = (
                Severity.ERROR
                if (created is not None and created >= HARD_LIMIT_PLAN_CUTOFF)
                else Severity.WARNING
            )
            issues.append(
                SpecsDoctorIssue(
                    code="SPEC-DOC-005",
                    severity=severity,
                    description=(
                        f"PLAN.md has {n_lines} lines > {PLAN_MAX_LINES} "
                        f"(created={created or 'unknown'})"
                    ),
                    path=str(plan),
                )
            )
        return issues

    # 6
    def _check_archive_closures(self) -> list[SpecsDoctorIssue]:
        issues: list[SpecsDoctorIssue] = []
        arch = self.specs_dir / "_archive" / "releases"
        if not arch.exists():
            return issues
        for release_dir in arch.iterdir():
            if not release_dir.is_dir():
                continue
            closure = release_dir / "CLOSURE.md"
            if not closure.exists():
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-006",
                        severity=Severity.ERROR,
                        description=f"Archived release {release_dir.name} has no CLOSURE.md",
                        path=str(closure),
                    )
                )
                continue
            text = closure.read_text(encoding="utf-8")
            required = ["## Summary", "## Validations", "## Drifts", "## Memory updates"]
            missing = [s for s in required if s not in text]
            if missing:
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-006",
                        severity=Severity.ERROR,
                        description=(
                            f"CLOSURE.md missing required sections: {missing}"
                        ),
                        path=str(closure),
                    )
                )
            # >=1 evidence triple inside Validations
            val_match = re.search(
                r"## Validations\s*(.*?)(?=^## |\Z)",
                text,
                re.MULTILINE | re.DOTALL,
            )
            if val_match:
                body = val_match.group(1)
                row_count = sum(
                    1
                    for ln in body.splitlines()
                    if re.match(r"^\s*\|[^|]+\|[^|]+\|[^|]+\|", ln)
                    and "---" not in ln
                    and "Description" not in ln
                )
                if row_count < 1:
                    issues.append(
                        SpecsDoctorIssue(
                            code="SPEC-DOC-006",
                            severity=Severity.ERROR,
                            description="CLOSURE.md has no validation triple in ## Validations",
                            path=str(closure),
                        )
                    )
        return issues

    # 7
    def _check_no_orphan_specs(self) -> list[SpecsDoctorIssue]:
        issues: list[SpecsDoctorIssue] = []
        for name in ("SPEC.md", "PLAN.md", "TASKS.md"):
            for p in self.specs_dir.rglob(name):
                rel = p.relative_to(self.specs_dir).as_posix()
                if rel.startswith(("releases/", "_archive/")):
                    continue
                # Top-level SPEC.md/PLAN.md/TASKS.md are legacy roots
                # features/<x>/SPEC.md is legacy too
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-007",
                        severity=Severity.WARNING,
                        description=(
                            f"Legacy {name} outside releases/ or _archive/releases/: {rel}. "
                            "Migrate to a release or archive as a legacy-feature."
                        ),
                        path=str(p),
                    )
                )
        return issues

    # 8
    def _check_memory_atomicity(self) -> list[SpecsDoctorIssue]:
        issues: list[SpecsDoctorIssue] = []
        mem_dir = self.specs_dir / "memory"
        for p in _iter_memory_html_files(mem_dir):
            try:
                summary = _parse_memory_html(p)
            except Exception:
                continue
            rel = p.relative_to(mem_dir).as_posix()
            for label in summary.forbidden_h2:
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-008",
                        severity=Severity.ERROR,
                        description=(
                            f"memory/{rel} has forbidden section: {label!r} — "
                            "memory must be atomic, not a changelog"
                        ),
                        path=str(p),
                    )
                )
        return issues

    # 10
    def _check_memory_image_links(self) -> list[SpecsDoctorIssue]:
        issues: list[SpecsDoctorIssue] = []
        mem_dir = self.specs_dir / "memory"
        for p in _iter_memory_html_files(mem_dir):
            try:
                summary = _parse_memory_html(p)
            except Exception:
                continue
            rel = p.relative_to(mem_dir).as_posix()
            for src in summary.img_srcs:
                if src.startswith(("http://", "https://", "data:")):
                    continue
                target = (p.parent / src).resolve()
                if not target.exists():
                    issues.append(
                        SpecsDoctorIssue(
                            code="SPEC-DOC-010",
                            severity=Severity.ERROR,
                            description=(
                                f"memory/{rel} references broken <img src=\"{src}\"> "
                                f"(resolves to {target})"
                            ),
                            path=str(p),
                        )
                    )
        return issues

    # 12
    def _check_backlog_schema(self) -> list[SpecsDoctorIssue]:
        """Validate bullet format in specs/backlog/candidates.md (SPEC-DOC-012).

        Only bullets inside sections whose header matches ``## Candidatas`` are
        validated.  Sections starting with ``## Histórico`` (and any other
        non-Candidatas sections such as ``## Convenções``) are skipped entirely.
        Backlog file absent → noop.  Failures produce WARNING (not ERROR) because
        backlog schema is guidance, not a hard contract.

        Note: only ``candidates.md`` is validated; other files under
        ``specs/backlog/`` (e.g. ``dadaia-workspace-panel.md``) are free-form
        and are not touched by this check.
        """
        issues: list[SpecsDoctorIssue] = []
        candidates_path = self.specs_dir / "backlog" / "candidates.md"
        if not candidates_path.exists():
            return issues

        text = candidates_path.read_text(encoding="utf-8")
        in_candidatas_section = False
        for lineno, raw_line in enumerate(text.splitlines(), start=1):
            line = raw_line.rstrip()
            if line.startswith("## "):
                in_candidatas_section = bool(re.match(r"^##\s+Candidatas", line))
                continue
            if not in_candidatas_section:
                continue
            if not line.startswith("- "):
                continue
            if not BACKLOG_BULLET_RE.match(line):
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-012",
                        severity=Severity.WARNING,
                        description=(
                            f"candidates.md line {lineno}: bullet does not match "
                            "expected format "
                            "'- <name> — <one-liner> (owner: <agent>, contexto: <link>)': "
                            f"{line!r}"
                        ),
                        path=str(candidates_path),
                    )
                )
        return issues

    # 11
    def _check_memory_mermaid_script(self) -> list[SpecsDoctorIssue]:
        issues: list[SpecsDoctorIssue] = []
        mem_dir = self.specs_dir / "memory"
        for p in _iter_memory_html_files(mem_dir):
            try:
                summary = _parse_memory_html(p)
            except Exception:
                continue
            rel = p.relative_to(mem_dir).as_posix()
            if summary.has_mermaid_blocks and not summary.has_mermaid_script:
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-011",
                        severity=Severity.WARNING,
                        description=(
                            f"memory/{rel} has <pre class=\"mermaid\"> blocks but no "
                            "Mermaid <script src=\"...mermaid...\"> — diagrams will not render"
                        ),
                        path=str(p),
                    )
                )
        return issues
