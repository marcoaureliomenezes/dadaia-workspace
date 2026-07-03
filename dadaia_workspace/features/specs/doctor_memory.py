"""Memory validator (v0.1.55 FR1): memory-atom files, atomicity, CAT-1, LINT-1.

Single-responsibility sibling of the SpecsDoctor coordinator. Owns the memory-markdown-source
invariants: required atoms present with a heading (SPEC-DOC-002/002L), no changelog/history
headings (SPEC-DOC-008), catalog↔atom sync (CAT-1), and the LINT-1 memory-atom lint. This module
HOLDS the single lazy ``infrastructure.subprocess_runner`` import edge (LINT-1 shell-out) — the
coordinator imports no subprocess adapter. Leaf-only: imports the shared leaves + core, never a
sibling validator.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

from dadaia_workspace.core.protocols.process_runner import ProcessResult, ProcessRunner
from dadaia_workspace.features.specs.doctor_types import (
    Severity,
    SpecsDoctorIssue,
    _MemoryMdSummary,
)

FORBIDDEN_MEMORY_H2_RE = re.compile(r"^(Changelog|History|Hist[óo]rico|Versions?)\b", re.IGNORECASE)
# Top-level memory files (.md canonical source).
TOPLEVEL_MEMORY_FILES = ("architecture.md", "tech-stack.md", "quality-assurance.md")
# Product memory is a folder catalog: index.md is required + 0..N feature .md atoms.
PRODUCT_INDEX_REL = "product/index.md"

# LINT-1: path to the lint-memory-atoms.py script, resolved from this file's location.
# dadaia_workspace/features/specs/doctor_memory.py → dadaia_workspace/public/scripts/
_LINT_SCRIPT: Path = (
    Path(__file__).resolve().parent.parent.parent / "public" / "scripts" / "lint-memory-atoms.py"
)

# ---------------------------------------------------------------------------
# Markdown memory atom helpers
# ---------------------------------------------------------------------------

_MD_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
# Any ATX heading (H1-H6): satisfies the "has a heading" requirement.
_MD_HEADING_RE = re.compile(r"^#{1,6}\s+\S", re.MULTILINE)
_MD_H1_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
_MD_H2_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)
_WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


def _parse_memory_md(path: Path) -> _MemoryMdSummary:
    """Extract the facts the doctor needs from a memory .md atom."""
    content = path.read_text(encoding="utf-8")

    # Extract frontmatter if present
    fm: dict | None = None  # type: ignore[type-arg]
    body = content
    m = _MD_FRONTMATTER_RE.match(content)
    if m:
        try:
            fm = yaml.safe_load(m.group(1))
        except yaml.YAMLError:
            fm = None
        body = content[m.end() :]

    # First H1 heading text (used for heading_text field; may be empty).
    h1_match = _MD_H1_RE.search(body)
    heading_text = h1_match.group(1).strip() if h1_match else ""
    # has_heading is True if the body contains ANY ATX heading (H1–H6), including
    # atoms that only have ## / ### level headings and no H1.
    has_heading = bool(_MD_HEADING_RE.search(body))

    # Check ## headings for forbidden patterns
    forbidden_h2: list[str] = []
    for h2_match in _MD_H2_RE.finditer(body):
        text = h2_match.group(1).strip()
        if text and FORBIDDEN_MEMORY_H2_RE.search(text):
            forbidden_h2.append(text)

    return _MemoryMdSummary(
        has_heading=has_heading,
        heading_text=heading_text,
        forbidden_h2=forbidden_h2,
        frontmatter=fm,
        body=body,
    )


def _iter_memory_md_files(mem_dir: Path) -> list[Path]:
    """All memory .md atom files that should be checked for atomicity.

    Includes the top-level singles (architecture.md, tech-stack.md) and every
    *.md under product/ except index.md (the catalog folder).
    """
    out: list[Path] = []
    for name in TOPLEVEL_MEMORY_FILES:
        p = mem_dir / name
        if p.exists():
            out.append(p)
    product_dir = mem_dir / "product"
    if product_dir.is_dir():
        # Recurse into thematic subdirs (v0.1.9 product/ tree).
        for p in sorted(product_dir.glob("**/*.md")):
            if p.name == "index.md":
                continue
            out.append(p)
    return out


class MemoryValidator:
    """Memory-atom files, atomicity, CAT-1 catalog sync, and LINT-1 lint."""

    def __init__(self, specs_dir: Path, process_runner: ProcessRunner | None = None) -> None:
        self.specs_dir = specs_dir
        # ProcessRunner: injected for tests/DI; lazily resolved to the infra adapter in
        # production when not provided.
        self._process_runner: ProcessRunner | None = process_runner

    def check_memory_files(self) -> list[SpecsDoctorIssue]:
        """Check #2: required memory .md atoms exist with non-empty heading.

        Canonical source format is .md (memory-markdown-source-v1).
        Stray .html files are flagged as legacy (SPEC-DOC-002L).
        The product.html-at-root legacy error is retained for historical compat.
        """
        issues: list[SpecsDoctorIssue] = []
        mem_dir = self.specs_dir / "memory"

        # Required top-level singles
        required: list[tuple[str, Path]] = [
            (name, mem_dir / name) for name in TOPLEVEL_MEMORY_FILES
        ]
        # Required folder catalog entry
        required.append((PRODUCT_INDEX_REL, mem_dir / PRODUCT_INDEX_REL))

        # Plus any optional feature .md atoms that DO exist — they must parse too
        product_dir = mem_dir / "product"
        feature_files: list[tuple[str, Path]] = []
        if product_dir.is_dir():
            feature_files = [
                (f"product/{p.relative_to(product_dir)}", p)
                for p in sorted(product_dir.rglob("*.md"))
                if p.name != "index.md"
            ]

        for rel, p in required + feature_files:
            if not p.exists():
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-002",
                        severity=Severity.ERROR,
                        description=f"memory/{rel} is missing — memory must be Markdown (.md)",
                        path=str(p),
                    )
                )
                continue
            try:
                summary = _parse_memory_md(p)
            except Exception as e:
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-002",
                        severity=Severity.ERROR,
                        description=f"memory/{rel} is not parseable: {e}",
                        path=str(p),
                    )
                )
                continue
            if not summary.has_heading:
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-002",
                        severity=Severity.ERROR,
                        description=f"memory/{rel} has no non-empty heading",
                        path=str(p),
                    )
                )

        # Legacy product.html at memory/ root (pre-folder-catalog) is still an error
        legacy_product = mem_dir / "product.html"
        if legacy_product.exists():
            issues.append(
                SpecsDoctorIssue(
                    code="SPEC-DOC-002L",
                    severity=Severity.ERROR,
                    description=(
                        "memory/product.html is legacy — product memory is now a folder "
                        "catalog. Move to _archive/legacy-memory/<timestamp>/ and create "
                        "memory/product/index.md + memory/product/<feature>.md files."
                    ),
                    path=str(legacy_product),
                )
            )

        # Flag any stray .html files in memory/ root or product/ as legacy.
        # AGENTS.md is a directory contract, not a memory atom — exempt it.
        # .html files are never written at runtime (D-4); any that appear are stale.
        if mem_dir.exists():
            for stray in mem_dir.glob("*.html"):
                if stray.name == "product.html":
                    continue  # already reported above
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-002L",
                        severity=Severity.ERROR,
                        description=(
                            f"memory/{stray.name} is a stray HTML file — "
                            "memory atoms must be .md (memory-markdown-source-v1, D-4). "
                            "Remove the .html file; the canonical source is the .md atom."
                        ),
                        path=str(stray),
                    )
                )
            if product_dir.is_dir():
                for stray in product_dir.glob("*.html"):
                    issues.append(
                        SpecsDoctorIssue(
                            code="SPEC-DOC-002L",
                            severity=Severity.ERROR,
                            description=(
                                f"memory/product/{stray.name} is a stray HTML file — "
                                "memory atoms must be .md (D-4). Remove the .html file."
                            ),
                            path=str(stray),
                        )
                    )

            # Orphaned .md files at root (no known canonical role) — flag as legacy.
            # AGENTS.md is exempt. TOPLEVEL_MEMORY_FILES (.md) are canonical. index.md in
            # product/ is the generated TOC.  Everything else is flagged.
            _canonical_root_md = {Path(f).name for f in TOPLEVEL_MEMORY_FILES}
            for legacy in mem_dir.glob("*.md"):
                if legacy.name == "AGENTS.md":
                    continue
                if legacy.name in _canonical_root_md:
                    continue
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-002L",
                        severity=Severity.ERROR,
                        description=(
                            f"memory/{legacy.name} is not a canonical memory atom. "
                            "Move to _archive/legacy-memory/<timestamp>/ if historical."
                        ),
                        path=str(legacy),
                    )
                )

        return issues

    def check_memory_atomicity(self) -> list[SpecsDoctorIssue]:
        """Check #8: no forbidden changelog/history ## headings in memory .md bodies.

        memory-markdown-source-v1: .md is now the canonical source.  We grep the
        Markdown body directly — no YAML escape hatch, no STRUCT bypass.
        Forbidden headings: ## Changelog, ## History, ## Histórico, ## Versions.
        """
        issues: list[SpecsDoctorIssue] = []
        mem_dir = self.specs_dir / "memory"

        for p in _iter_memory_md_files(mem_dir):
            try:
                summary = _parse_memory_md(p)
            except Exception:
                continue
            rel = p.relative_to(mem_dir).as_posix()
            for label in summary.forbidden_h2:
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-008",
                        severity=Severity.ERROR,
                        description=(
                            f"memory/{rel} has forbidden heading: ## {label!r} — "
                            "memory atoms must be atomic, not changelogs"
                        ),
                        path=str(p),
                    )
                )
        return issues

    def check_lint1_memory_atoms(self) -> list[SpecsDoctorIssue]:
        """LINT-1: invoke lint-memory-atoms.py over specs/memory/.

        ERROR on frontmatter/schema violations + forbidden headings.
        WARNING on token-estimate drift.

        The lint script is invoked as a subprocess using the same Python interpreter.
        If the script is not found, LINT-1 is skipped with a WARNING.
        """
        mem_dir = self.specs_dir / "memory"
        if not mem_dir.is_dir():
            return []
        if not _LINT_SCRIPT.exists():
            return [
                SpecsDoctorIssue(
                    code="LINT-1",
                    severity=Severity.WARNING,
                    description=(
                        "LINT-1: lint-memory-atoms.py not found at expected path "
                        f"({_LINT_SCRIPT}). Install or update dadaia_workspace package."
                    ),
                    path=str(_LINT_SCRIPT),
                )
            ]

        runner = self._process_runner
        if runner is None:
            from dadaia_workspace.infrastructure.subprocess_runner import SubprocessProcessRunner

            runner = SubprocessProcessRunner()

        try:
            # `-B` disables bytecode writing so no __pycache__/*.pyc is created under
            # dadaia_workspace/public/scripts/ when LINT-1 runs (T-011-15 / FR-W5-01).
            proc_result: ProcessResult = runner.run(
                [sys.executable, "-B", str(_LINT_SCRIPT), "--memory-dir", str(mem_dir)],
                timeout=30,
            )
        except TimeoutError:
            return [
                SpecsDoctorIssue(
                    code="LINT-1",
                    severity=Severity.WARNING,
                    description="LINT-1: lint-memory-atoms.py timed out (>30s).",
                    path=str(mem_dir),
                )
            ]
        except Exception as exc:
            return [
                SpecsDoctorIssue(
                    code="LINT-1",
                    severity=Severity.WARNING,
                    description=f"LINT-1: failed to invoke lint-memory-atoms.py: {exc}",
                    path=str(mem_dir),
                )
            ]
        # Exit codes: 0 = clean, 1 = at least one ERROR, 2 = warnings only
        output = (proc_result.stdout + proc_result.stderr).strip()
        # Drop the lint script's own "Summary: N OK, M WARN, K ERROR" line — it is scoped to
        # memory atoms only and, embedded in this issue's text, was mistaken for the doctor's
        # OVERALL verdict (bug: specs-doctor-dual-error-counter-confusing-output). The doctor
        # CLI now prints one authoritative overall verdict line instead.
        output = "\n".join(
            ln for ln in output.splitlines() if not ln.strip().startswith("Summary:")
        ).strip()
        issues: list[SpecsDoctorIssue] = []

        if proc_result.returncode == 0:
            return []
        if proc_result.returncode == 1:
            # ERRORs present
            issues.append(
                SpecsDoctorIssue(
                    code="LINT-1",
                    severity=Severity.ERROR,
                    description=(
                        "LINT-1: memory atom lint found frontmatter/schema violations "
                        f"or forbidden headings:\n{output}"
                    ),
                    path=str(mem_dir),
                )
            )
        elif proc_result.returncode == 2:
            # Warnings only (e.g. token_estimate drift)
            issues.append(
                SpecsDoctorIssue(
                    code="LINT-1",
                    severity=Severity.WARNING,
                    description=(
                        f"LINT-1: memory atom lint warnings (token_estimate drift etc.):\n{output}"
                    ),
                    path=str(mem_dir),
                )
            )
        else:
            # Unexpected exit code
            issues.append(
                SpecsDoctorIssue(
                    code="LINT-1",
                    severity=Severity.WARNING,
                    description=(
                        f"LINT-1: lint-memory-atoms.py exited with unexpected code "
                        f"{proc_result.returncode}:\n{output}"
                    ),
                    path=str(mem_dir),
                )
            )
        return issues

    def check_cat1_catalog_sync(self) -> list[SpecsDoctorIssue]:
        """CAT-1: catalog.json must stay in sync with *.md feature atom files.

        memory-markdown-source-v1: .md is canonical source; .html is retired.

        Logic:
        1. Enumerate ``memory/product/*.md`` excluding ``index.md`` → ``md_slugs``.
        2. If ``catalog.json`` is absent and md_slugs is non-empty → one WARNING.
        3. If ``catalog.json`` is present → parse ``features[].slug``:
           - One WARNING per slug in catalog that has no corresponding .md on disk.
           - One WARNING per .md on disk whose slug is not in the catalog.
        4. Severity is always WARNING (never ERROR) — catalog may simply need regeneration.
        """
        import json as _json

        issues: list[SpecsDoctorIssue] = []
        product_dir = self.specs_dir / "memory" / "product"
        catalog_path = product_dir / "catalog.json"

        if not product_dir.is_dir():
            return issues

        # Collect slugs from .md feature atoms (excluding index.md), recursing into subdirs
        md_slugs: set[str] = {p.stem for p in product_dir.rglob("*.md") if p.name != "index.md"}

        if not catalog_path.exists():
            if md_slugs:
                issues.append(
                    SpecsDoctorIssue(
                        code="CAT-1",
                        severity=Severity.WARNING,
                        description=(
                            f"catalog.json absent; {len(md_slugs)} feature .md atom"
                            f"{'s' if len(md_slugs) != 1 else ''} present; "
                            "run `dadaia memory catalog generate` to create it."
                        ),
                        path=str(catalog_path),
                    )
                )
            return issues

        # catalog.json exists — compare slug sets
        try:
            data = _json.loads(catalog_path.read_text(encoding="utf-8"))
            catalog_slugs: set[str] = {
                str(entry.get("slug", ""))
                for entry in data.get("features", [])
                if entry.get("slug")
            }
        except Exception as exc:
            issues.append(
                SpecsDoctorIssue(
                    code="CAT-1",
                    severity=Severity.WARNING,
                    description=f"catalog.json is not valid JSON: {exc}",
                    path=str(catalog_path),
                )
            )
            return issues

        # Slugs in catalog but no .md on disk
        for slug in sorted(catalog_slugs - md_slugs):
            issues.append(
                SpecsDoctorIssue(
                    code="CAT-1",
                    severity=Severity.WARNING,
                    description=(
                        f"catalog.json lists slug '{slug}' but no corresponding "
                        f"'{slug}.md' exists in memory/product/. "
                        "Run `dadaia memory catalog generate` to resync."
                    ),
                    path=str(product_dir / f"{slug}.md"),
                )
            )

        # .md atoms on disk but not in catalog
        for slug in sorted(md_slugs - catalog_slugs):
            issues.append(
                SpecsDoctorIssue(
                    code="CAT-1",
                    severity=Severity.WARNING,
                    description=(
                        f"'{slug}.md' exists in memory/product/ but is not listed in "
                        "catalog.json. "
                        "Run `dadaia memory catalog generate` to resync."
                    ),
                    path=str(product_dir / f"{slug}.md"),
                )
            )

        return issues
