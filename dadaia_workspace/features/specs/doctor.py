"""SpecsDoctor — structural validation for SDD release-lifecycle specs (Markdown memory).

Runs the structural checks defined in release `sdd-release-lifecycle-v1`,
extended for the product memory folder catalog and the D-OC-1 orchestration
registry coherence invariant, plus the 7 TREE invariants from release
`spec-context-tree-v2`, plus the CAT-1 catalog sync check from release
`memory-context-enforcement-v1`, plus the LINT-1 check from release
`memory-markdown-source-v1`:

  1. specs/constitution.md exists
  2. specs/memory/architecture.md, tech-stack.md and quality-assurance.md exist with
     non-empty first heading; specs/memory/product/index.md exists (folder catalog
     entry); legacy product.html at memory/ root reported as error; stray .html atoms
     flagged as legacy; broken [[slug]] wikilinks from product/*.md reported as warning
  3. specs/releases/ACTIVE.md exists, parseable, phase canonical
  4. active release has SPEC+PLAN+TASKS with Status: Aprovado (warn if Draft + phase != ARCHIVED)
  5. PLAN <= 300 lines (warning <= 2026-05-16; error >= 2026-05-17)
  6. each _archive/releases/<id>/ has CLOSURE.md with 4 mandatory sections + >=1 evidence triple
  7. no SPEC/PLAN/TASKS outside releases/*/ or _archive/releases/*/ (warn during legacy window)
  8. no ## heading matching Changelog|History|Histórico|Versions? in any memory .md body
  9. release id in ACTIVE.md corresponds to a real directory
 10. (reserved — HTML image-link check retired with HTML atoms)
 11. (reserved — HTML mermaid-script check retired with HTML atoms)
 D-OC-1. bidirectional orchestration registry coherence (requires public_dir):
     - Forward: every Tier-1 name → workflow file exists; every Tier-2 name → playbook
       heading exists in SKILL.md.
     - Reverse: every non-deprecated playbook heading → appears as Tier-2 row in PM router.

TREE invariants (spec-context-tree-v2):
  TREE-1. specs/foundation/ exists → WARN-ONLY (migration: dadaia migrate tree-v2)
  TREE-2. specs/SPEC.md at tree root → WARN-ONLY (migration: dadaia migrate tree-v2)
  TREE-3. memory/architecture.md | tech-stack.md | quality-assurance.md | product/index.md absent → WARNING
  TREE-4. backlog/ | bugs/ | releases/ absent → AUTO-FIX (create dir + README.md + .gitkeep)
  TREE-5. specs/AGENTS.md absent or hash differs from canonical template → WARN-ONLY (drift)
  TREE-5M. specs/memory/AGENTS.md absent → WARN-ONLY (projected later by ai-engineer WS-2)
  TREE-6. releases/<id>/ missing mandatory SDD artifact for its phase → NO AUTO-FIX
  TREE-7. bugs/<slug>.md missing session_id frontmatter field → NO AUTO-FIX

CAT-1 (memory-context-enforcement-v1):
  CAT-1. catalog.json absent when feature .md atoms exist → WARNING
         catalog.json present but slugs ↔ .md files out of sync → WARNING (per slug/file)

LINT-1 (memory-markdown-source-v1):
  LINT-1. frontmatter/schema violations in .md atoms → ERROR
          token_estimate drift > 20% in .md atoms → WARNING

Pure module — no I/O outside the supplied specs_dir / public_dir. No external dependencies.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import StrEnum
from html.parser import HTMLParser
from pathlib import Path

import yaml

CANONICAL_STATUS = {"Draft", "Em revisão", "Aprovado"}
CANONICAL_PHASES = {
    "DISCOVERY",
    "DEFINITION",  # v0.1.7: release-definition phase; product-engineer authors memory here
    "SPEC",
    "PLAN",
    "TASKS",
    "IMPLEMENTATION",
    "CLOSURE",
    "ARCHIVED",
    "none",  # scaffold default: no active release
}
BACKLOG_BULLET_RE = re.compile(r"^- \S.*? — .+? \(owner: [a-z-]+, contexto: .+?\)\s*$")
# SPEC-DOC-022: format for ## Hotfixes pendentes bullets
# Pattern: - <YYYY-MM-DDTHHMMSSZ> <severity> <component> — <one-liner> (post-mortem: <link>)
BACKLOG_HOTFIX_RE = re.compile(
    r"^- (\d{4}-\d{2}-\d{2}T\d{6}Z) (LOW|MEDIUM|HIGH|CRITICAL) ([\w\-/]+) — .+ \(post-mortem: .+\)$"
)
FORBIDDEN_MEMORY_H2_RE = re.compile(r"^(Changelog|History|Hist[óo]rico|Versions?)\b", re.IGNORECASE)
# Top-level memory files (.md canonical source).
TOPLEVEL_MEMORY_FILES = ("architecture.md", "tech-stack.md", "quality-assurance.md")
# Product memory is a folder catalog: index.md is required + 0..N feature .md atoms.
PRODUCT_INDEX_REL = "product/index.md"
HARD_LIMIT_PLAN_CUTOFF = date(2026, 5, 17)
PLAN_MAX_LINES = 300

# D-OC-1: orchestration registry coherence (orchestration-consolidation-v1).
#
# The PM Step-3 tables have the format:
#   Tier-1: | Demand pattern | `<name>` | `public/workflows/<name>.workflow.md` |
#   Tier-2: | Demand pattern | `<name>` |  (or  | `<name>` (annotation) | ...)
#
# Both tables have the canonical name in the SECOND column (the first column
# contains the free-text demand pattern).  To match either, we look for a row
# where the second pipe-delimited cell starts with a backtick-quoted name.
#
# Tier-1: the workflow-file cell (`public/workflows/…`) is the distinguishing marker.
_TIER1_ROW_RE = re.compile(
    r"^\|[^|]+\|\s+`([a-z][a-z0-9-]+)`\s+\|\s+`public/workflows/",
    re.MULTILINE,
)
# Tier-2: second column starts with a backtick-quoted name.
_TIER2_ROW_RE = re.compile(
    r"^\|[^|]+\|\s+`([a-z][a-z0-9-]+)`",
    re.MULTILINE,
)
# Playbook headings in SKILL.md: `### Playbook — <name>` optionally followed by `[deprecated]`.
_PLAYBOOK_HEADING_RE = re.compile(
    r"^###\s+Playbook\s+—\s+([a-z][a-z0-9-]+)(\s+\[deprecated\])?",
    re.MULTILINE | re.IGNORECASE,
)

# SPEC-DOC-016: SemVer folder naming for releases created on/after this date (D3).
# Vintage releases (Created: <= 2026-05-17) are excluded.
RELEASE_SEMVER_RE = re.compile(r"^v\d+\.\d+\.\d+$")
RELEASE_SEMVER_CUTOFF = date(2026, 6, 1)  # WARNING starts here
RELEASE_SEMVER_HARD = date(2026, 7, 1)  # ERROR starts here
RELEASE_VINTAGE_CUTOFF = date(2026, 5, 17)  # releases on/before this are excluded

# SPEC-DOC-023: hotfix bullets older than 72 hours in ## Hotfixes pendentes get WARNING
_HOTFIX_STALE_HOURS = 72

# ──────────────────────────────────────────────────────────────────────────────
# TREE invariant constants (spec-context-tree-v2)
# ──────────────────────────────────────────────────────────────────────────────

# TREE-3: memory .md files that must exist.  No Jinja templates — .md is canonical source.
# Kept as a tuple of (rel_path,) for structural consistency with the check loop.
_TREE3_MEMORY_FILES: tuple[str, ...] = (
    "architecture.md",
    "tech-stack.md",
    "quality-assurance.md",
    "product/index.md",
)

# TREE-4: directories that must exist.  Value = README.md content source file (relative
# to the scaffold source dir embedded in the package).
_TREE4_REQUIRED_DIRS = ("audits", "backlog", "bugs", "releases")

# TREE-6: mandatory artifacts per phase bucket.
# For the ACTIVE release, if phase is IMPLEMENTATION or CLOSURE, all three must exist.
_TREE6_IMPL_ARTIFACTS = ("SPEC.md", "PLAN.md", "TASKS.md")

# Migration hint printed loudly for TREE-1 and TREE-2 (regardless of --fix).
_TREE_MIGRATION_HINT = (
    "[TREE MIGRATION REQUIRED] Run: dadaia migrate tree-v2\n"
    "  This command moves deprecated content to releases/legacy/ "
    "without destroying SDD-approved artifacts."
)

# LINT-1: path to the lint-memory-atoms.py script, resolved from this file's location.
# dadaia_workspace/features/specs/doctor.py → dadaia_workspace/public/scripts/
_LINT_SCRIPT: Path = (
    Path(__file__).resolve().parent.parent.parent / "public" / "scripts" / "lint-memory-atoms.py"
)


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class SpecsDoctorIssue:
    code: str
    severity: Severity
    description: str
    path: str | None = None
    fixable: bool = False

    def to_dict(self) -> dict[str, str | None]:
        return {
            "code": self.code,
            "severity": self.severity.value,
            "description": self.description,
            "path": self.path,
        }


# ---------------------------------------------------------------------------
# Markdown memory atom helpers
# ---------------------------------------------------------------------------

_MD_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
# Any ATX heading (H1-H6): satisfies the "has a heading" requirement.
_MD_HEADING_RE = re.compile(r"^#{1,6}\s+\S", re.MULTILINE)
_MD_H1_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
_MD_H2_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)
_WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


@dataclass
class _MemoryMdSummary:
    has_heading: bool
    heading_text: str
    forbidden_h2: list[str]
    frontmatter: dict | None  # type: ignore[type-arg]
    body: str


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


# _MemoryHtmlSummary and _MemoryParser are retained for any callers that still
# parse HTML assets (e.g. non-atom HTML files served by the panel).
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


def _read_active_md(
    path: Path,
) -> tuple[str | None, str | None, str | None, str | None]:
    """Returns (release_id, segment, phase, error_message_or_none).

    Schema v2 (ADR-1/ADR-5): ACTIVE.md may carry an optional ``segment:`` line
    (e.g. ``alpha-2``, ``rc-1``) identifying the active segment of a release.
    ``segment`` is ``None`` for flat (pre-segment) releases — back-compatible.
    """
    if not path.exists():
        return None, None, None, "ACTIVE.md not found"
    text = path.read_text(encoding="utf-8")
    release = None
    segment = None
    phase = None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("release:"):
            value = line.split(":", 1)[1].strip()
            release = value if value else None
        elif line.startswith("segment:"):
            value = line.split(":", 1)[1].strip()
            segment = value if value and value != "none" else None
        elif line.startswith("phase:"):
            value = line.split(":", 1)[1].strip()
            phase = value if value else None
    if release is None or phase is None:
        return release, segment, phase, "ACTIVE.md missing 'release:' or 'phase:' line"
    return release, segment, phase, None


def _extract_status(md_path: Path) -> str | None:
    if not md_path.exists():
        return None
    for line in md_path.read_text(encoding="utf-8").splitlines()[:30]:
        m = re.search(r"\*\*Status:\*\*\s*(.+?)\s*$", line)
        if m:
            return m.group(1).strip()
    return None


def _split_tier_blocks(text: str) -> tuple[str, str]:
    """Split project-manager.md into its Tier-1 and Tier-2 table sections.

    Returns (tier1_block, tier2_block) as plain strings. Either may be empty
    if the respective heading is absent.
    """
    tier1_match = re.search(r"#### Tier-1[^\n]*\n", text)
    tier2_match = re.search(r"#### Tier-2[^\n]*\n", text)
    if not tier1_match or not tier2_match:
        return "", ""
    tier1_block = text[tier1_match.end() : tier2_match.start()]
    tier2_end = re.search(r"^###", text[tier2_match.end() :], re.MULTILINE)
    if tier2_end:
        tier2_block = text[tier2_match.end() : tier2_match.end() + tier2_end.start()]
    else:
        tier2_block = text[tier2_match.end() :]
    return tier1_block, tier2_block


def _extract_tier1_names(pm_text: str) -> list[str]:
    """Return canonical Tier-1 workflow names from the PM Step-3 Tier-1 table."""
    tier1_block, _ = _split_tier_blocks(pm_text)
    return re.findall(_TIER1_ROW_RE, tier1_block)


def _extract_tier2_names(pm_text: str) -> list[str]:
    """Return canonical Tier-2 playbook names from the PM Step-3 Tier-2 table."""
    _, tier2_block = _split_tier_blocks(pm_text)
    return re.findall(_TIER2_ROW_RE, tier2_block)


def _extract_playbook_headings(skill_text: str) -> dict[str, bool]:
    """Return {playbook_name: is_deprecated} from SKILL.md ``### Playbook — <name>`` headings."""
    matches = re.findall(_PLAYBOOK_HEADING_RE, skill_text)
    return {name: bool(dep.strip()) for name, dep in matches}


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
    """Diagnose specs/ structure under SDD release-lifecycle.

    Args:
        specs_dir: Path to the ``specs/`` directory.
        public_dir: Optional path to ``dadaia_workspace/public/``. When provided,
            the D-OC-1 orchestration-registry coherence check is enabled, and
            the TREE-3/TREE-4/TREE-5 auto-fix + drift-detect features are available
            (templates loaded from ``public_dir/templates/``).
            When *not* provided the TREE checks still run but TREE-3 fix and TREE-5
            hash comparison are skipped (issue is still emitted, fix is no-op).
    """

    def __init__(
        self,
        specs_dir: Path,
        public_dir: Path | None = None,
        templates_dir: Path | None = None,
    ) -> None:
        self.specs_dir = Path(specs_dir)
        self.public_dir: Path | None = Path(public_dir) if public_dir is not None else None
        # templates_dir is resolved from public_dir if not explicitly supplied.
        if templates_dir is not None:
            self._templates_dir: Path | None = Path(templates_dir)
        elif self.public_dir is not None:
            candidate = self.public_dir / "templates"
            self._templates_dir = candidate if candidate.is_dir() else None
        else:
            self._templates_dir = None

        # Scaffold source dir (for TREE-4 README content).
        if self.public_dir is not None:
            scaffold_candidate = self.public_dir / "scaffold"
            self._scaffold_dir: Path | None = (
                scaffold_candidate if scaffold_candidate.is_dir() else None
            )
        else:
            self._scaffold_dir = None

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
        # checks 10 and 11 (HTML image-links / mermaid-script) retired with HTML atoms
        issues.extend(self._check_backlog_schema())
        issues.extend(self._check_release_semver_naming())
        issues.extend(self._check_orchestration_registry())
        # TREE invariants (spec-context-tree-v2)
        issues.extend(self._check_tree1_foundation())
        issues.extend(self._check_tree2_root_spec_md())
        issues.extend(self._check_tree3_memory_md())
        issues.extend(self._check_tree4_required_dirs())
        issues.extend(self._check_tree5_agents_md())
        issues.extend(self._check_memory_agents_md())
        issues.extend(self._check_tree6_release_artifacts())
        issues.extend(self._check_tree7_bug_session_id())
        # CAT-1 (memory-context-enforcement-v1) — now based on .md files
        issues.extend(self._check_cat1_catalog_sync())
        # LINT-1 (memory-markdown-source-v1) — invoke lint-memory-atoms.py
        issues.extend(self._check_lint1_memory_atoms())
        # SPECS-VERSION (specs-evolution / FR-S05) — pattern-version staleness
        issues.extend(self._check_specs_pattern_version())
        return issues

    def _check_specs_pattern_version(self) -> list[SpecsDoctorIssue]:
        """WARN-only: the tree's ``specs_pattern_version`` is below the canonical
        version the library ships. Recommends ``dadaia specs upgrade`` (FR-S05)."""
        from dadaia_workspace.core import specs_version as _ver

        current = _ver.read_pattern_version(self.specs_dir)
        if current >= _ver.CANONICAL_SPECS_VERSION:
            return []
        return [
            SpecsDoctorIssue(
                code="SPECS-VERSION",
                severity=Severity.WARNING,
                description=(
                    f"specs_pattern_version is {current}, below the canonical "
                    f"{_ver.CANONICAL_SPECS_VERSION}. Run: dadaia specs upgrade"
                ),
                path=str(self.specs_dir / "constitution.md"),
            )
        ]

    def fix(self, issues: list[SpecsDoctorIssue] | None = None) -> list[SpecsDoctorIssue]:
        """Apply auto-fixes for all fixable issues.

        Resolves TREE-3 (render missing memory HTML from Jinja templates) and
        TREE-4 (create missing dirs with README.md + .gitkeep).  Warn-only and
        no-fix invariants are never touched.

        Args:
            issues: Pre-computed issue list (avoids a second ``check()`` call).
                    If None, ``check()`` is called internally.

        Returns:
            List of issues that were fixed (i.e. ``fixable=True`` issues that
            were acted upon).  Issues that could not be fixed due to missing
            templates are omitted and left as residual issues on the next
            ``check()`` call.
        """
        if issues is None:
            issues = self.check()
        fixed: list[SpecsDoctorIssue] = []
        for issue in issues:
            if not issue.fixable:
                continue
            try:
                if issue.code == "TREE-4":
                    self._fix_tree4(issue)
                    fixed.append(issue)
            except Exception:
                # Leave as residual — will re-appear on next check()
                pass
        return fixed

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

    # 2 + helper used by 8
    def _check_memory_files(self) -> list[SpecsDoctorIssue]:
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

    # 3 + 9
    def _check_active_md(self) -> list[SpecsDoctorIssue]:
        issues: list[SpecsDoctorIssue] = []
        path = self.specs_dir / "releases" / "ACTIVE.md"
        release, segment, phase, err = _read_active_md(path)
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
        release, segment, phase, err = _read_active_md(path)
        if err or not release or release == "none":
            return issues
        # Schema v2 (ADR-1/ADR-5): when ACTIVE.md carries a segment, the active
        # SPEC/PLAN/TASKS live in releases/<release>/<segment>/; else flat.
        rdir = self.specs_dir / "releases" / release
        if segment:
            rdir = rdir / segment
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
                        description=(f"CLOSURE.md missing required sections: {missing}"),
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

    # 10 — retired (HTML memory atoms deleted in memory-markdown-source-v1)
    # Image-link checks applied to .html atoms are no longer needed.
    # This stub keeps the method available if callers enumerate the check list.
    def _check_memory_image_links(self) -> list[SpecsDoctorIssue]:
        return []

    # 11 — retired (HTML memory atoms deleted in memory-markdown-source-v1)
    # Mermaid-script checks applied to .html atoms are no longer needed.
    def _check_memory_mermaid_script(self) -> list[SpecsDoctorIssue]:
        return []

    # 12
    def _check_backlog_schema(self) -> list[SpecsDoctorIssue]:
        """Validate bullet format in specs/backlog/candidates.md (SPEC-DOC-012).

        Validates two sections:
        - ``## Candidatas ativas`` — format: ``- <name> — <one-liner> (owner: <agent>, contexto: <link>)``
        - ``## Hotfixes pendentes`` — format (D22): ``- <ts> <severity> <component> — <one-liner> (post-mortem: <link>)``

        Also emits WARNING for bullets in ``## Hotfixes pendentes`` whose timestamp is
        older than 72 hours without being moved to ``## Histórico`` (D23).

        Sections starting with ``## Histórico`` are skipped. Backlog file absent → noop.
        Failures produce WARNING (not ERROR) during initial adoption period.

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
        in_hotfixes_section = False
        now_utc = datetime.now(tz=UTC)

        for lineno, raw_line in enumerate(text.splitlines(), start=1):
            line = raw_line.rstrip()
            if line.startswith("## "):
                in_candidatas_section = bool(re.match(r"^##\s+Candidatas", line))
                in_hotfixes_section = bool(re.match(r"^##\s+Hotfixes\s+pendentes", line))
                continue

            # --- ## Candidatas ativas section ---
            if in_candidatas_section:
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
                continue

            # --- ## Hotfixes pendentes section ---
            if in_hotfixes_section:
                if not line.startswith("- "):
                    continue
                m = BACKLOG_HOTFIX_RE.match(line)
                if not m:
                    issues.append(
                        SpecsDoctorIssue(
                            code="SPEC-DOC-012",
                            severity=Severity.WARNING,
                            description=(
                                f"candidates.md line {lineno}: hotfix bullet does not match "
                                "expected format "
                                "'- <YYYY-MM-DDTHHMMSSZ> <LOW|MEDIUM|HIGH|CRITICAL> <component>"
                                " — <one-liner> (post-mortem: <link>)': "
                                f"{line!r}"
                            ),
                            path=str(candidates_path),
                        )
                    )
                else:
                    # Check staleness (D23): timestamp older than _HOTFIX_STALE_HOURS
                    ts_raw = m.group(1)  # e.g. 2026-05-14T120000Z
                    try:
                        ts = datetime.strptime(ts_raw, "%Y-%m-%dT%H%M%SZ").replace(tzinfo=UTC)
                        age_hours = (now_utc - ts).total_seconds() / 3600
                        if age_hours > _HOTFIX_STALE_HOURS:
                            issues.append(
                                SpecsDoctorIssue(
                                    code="SPEC-DOC-012",
                                    severity=Severity.WARNING,
                                    description=(
                                        f"candidates.md line {lineno}: hotfix bullet is stale "
                                        f"({age_hours:.0f}h > {_HOTFIX_STALE_HOURS}h). "
                                        "Consider promoting to a hotfix release or moving to "
                                        "## Histórico (D23)."
                                    ),
                                    path=str(candidates_path),
                                )
                            )
                    except ValueError:
                        pass  # timestamp parse failure already flagged above

        return issues

    # D-OC-1
    def _check_orchestration_registry(self) -> list[SpecsDoctorIssue]:
        """D-OC-1: bidirectional orchestration-registry coherence.

        Requires ``self.public_dir`` to be set. If not set, the check is skipped
        (noop) and an [ok] pseudo-result is NOT emitted — the check simply does
        not run.

        Forward check:
        - Every Tier-1 name in PM Step-3 router → ``public/workflows/<name>.workflow.md``
          must exist under ``self.public_dir``.
        - Every Tier-2 name in PM Step-3 router → ``### Playbook — <name>`` heading
          must exist in SKILL.md.

        Reverse check:
        - Every non-deprecated ``### Playbook — <name>`` heading in SKILL.md →
          must appear as a Tier-2 row in the PM router table.
        """
        if self.public_dir is None:
            return []

        issues: list[SpecsDoctorIssue] = []
        pm_path = self.public_dir / "agents" / "project-manager.md"
        skill_path = self.public_dir / "skills" / "project-orchestration" / "SKILL.md"

        if not pm_path.exists():
            issues.append(
                SpecsDoctorIssue(
                    code="D-OC-1",
                    severity=Severity.ERROR,
                    description=(
                        "D-OC-1: project-manager.md not found at "
                        "public/agents/project-manager.md — cannot run D-OC-1 check"
                    ),
                    path=str(pm_path),
                )
            )
            return issues

        if not skill_path.exists():
            issues.append(
                SpecsDoctorIssue(
                    code="D-OC-1",
                    severity=Severity.ERROR,
                    description=(
                        "D-OC-1: SKILL.md not found at "
                        "public/skills/project-orchestration/SKILL.md — cannot run D-OC-1 check"
                    ),
                    path=str(skill_path),
                )
            )
            return issues

        pm_text = pm_path.read_text(encoding="utf-8")
        skill_text = skill_path.read_text(encoding="utf-8")

        tier1_names = _extract_tier1_names(pm_text)
        tier2_names = _extract_tier2_names(pm_text)
        playbooks = _extract_playbook_headings(skill_text)

        # --- Forward checks ---
        for name in tier1_names:
            wf_path = self.public_dir / "workflows" / f"{name}.workflow.md"
            if not wf_path.exists():
                issues.append(
                    SpecsDoctorIssue(
                        code="D-OC-1",
                        severity=Severity.ERROR,
                        description=(
                            f"D-OC-1: Tier-1 name '{name}' has no workflow file at "
                            f"public/workflows/{name}.workflow.md"
                        ),
                        path=str(wf_path),
                    )
                )

        tier1_set = set(tier1_names)
        for name in tier2_names:
            # A Tier-2 name that also appears in Tier-1 is a cross-reference row
            # (e.g. `spec-refinement` in Tier-2 defers to the Tier-1 workflow file).
            # Its artifact is the workflow file — already checked above — so no
            # separate playbook-heading check is needed.
            if name in tier1_set:
                continue
            if name not in playbooks:
                issues.append(
                    SpecsDoctorIssue(
                        code="D-OC-1",
                        severity=Severity.ERROR,
                        description=(
                            f"D-OC-1: Tier-2 name '{name}' has no playbook heading "
                            f"'### Playbook — {name}' in SKILL.md"
                        ),
                        path=str(skill_path),
                    )
                )

        # --- Reverse check ---
        tier2_set = set(tier2_names)
        for name, is_deprecated in playbooks.items():
            if is_deprecated:
                continue  # deprecated playbooks are exempt from the reverse check
            if name not in tier2_set:
                issues.append(
                    SpecsDoctorIssue(
                        code="D-OC-1",
                        severity=Severity.ERROR,
                        description=(
                            f"D-OC-1: Playbook heading '### Playbook — {name}' in SKILL.md "
                            "has no Tier-2 router row in project-manager.md "
                            "(add it or annotate [deprecated])"
                        ),
                        path=str(skill_path),
                    )
                )

        return issues

    # 13
    def _check_release_semver_naming(self) -> list[SpecsDoctorIssue]:
        """SPEC-DOC-016: release folder names must follow SemVer (v<M>.<m>.<p>) for releases
        whose SPEC.md has Created: >= RELEASE_SEMVER_CUTOFF.

        Vintage releases (Created: <= RELEASE_VINTAGE_CUTOFF) are excluded.
        Severity: WARNING until RELEASE_SEMVER_HARD, ERROR on/after that date.

        Applies to both specs/releases/ and specs/_archive/releases/.
        """
        issues: list[SpecsDoctorIssue] = []
        today = date.today()

        # Only run this check if we are at or past the cutoff
        if today < RELEASE_SEMVER_CUTOFF:
            return issues

        severity = Severity.ERROR if today >= RELEASE_SEMVER_HARD else Severity.WARNING

        for releases_root in (
            self.specs_dir / "releases",
            self.specs_dir / "_archive" / "releases",
        ):
            if not releases_root.exists():
                continue
            for entry in releases_root.iterdir():
                if not entry.is_dir():
                    continue
                folder_name = entry.name
                # Resolve Created: date from SPEC.md
                spec_path = entry / "SPEC.md"
                created = _extract_created_date(spec_path) if spec_path.exists() else None

                # Skip vintage releases (Created: <= RELEASE_VINTAGE_CUTOFF)
                if created is not None and created <= RELEASE_VINTAGE_CUTOFF:
                    continue

                # Skip releases without a determinable Created: date
                # (they could be legacy — give benefit of the doubt)
                if created is None:
                    continue

                # Skip releases created before the cutoff
                if created < RELEASE_SEMVER_CUTOFF:
                    continue

                if not RELEASE_SEMVER_RE.match(folder_name):
                    issues.append(
                        SpecsDoctorIssue(
                            code="SPEC-DOC-016",
                            severity=severity,
                            description=(
                                f"Release folder '{folder_name}' does not follow SemVer "
                                f"naming (^v\\d+\\.\\d+\\.\\d+$). Created: {created}. "
                                "Rename to v<MAJOR>.<MINOR>.<PATCH> (D3, SPEC-DOC-016)."
                            ),
                            path=str(entry),
                        )
                    )
        return issues

    # ──────────────────────────────────────────────────────────────────────────
    # TREE invariants
    # ──────────────────────────────────────────────────────────────────────────

    def _check_tree1_foundation(self) -> list[SpecsDoctorIssue]:
        """TREE-1: specs/foundation/ must NOT exist (deprecated layout).

        Warn-only (fixable=False).  A loud migration hint pointing to
        ``dadaia migrate tree-v2`` is emitted regardless of the --fix flag.
        Auto-moving is intentionally blocked: foundation/ may hold SDD-approved
        content and reclassification requires operator consent.
        """
        foundation = self.specs_dir / "foundation"
        if not foundation.exists():
            return []
        return [
            SpecsDoctorIssue(
                code="TREE-1",
                severity=Severity.WARNING,
                description=(
                    "specs/foundation/ exists — this is the deprecated layout. "
                    f"{_TREE_MIGRATION_HINT}"
                ),
                path=str(foundation),
                fixable=False,
            )
        ]

    def _check_tree2_root_spec_md(self) -> list[SpecsDoctorIssue]:
        """TREE-2: specs/SPEC.md at the tree root must NOT exist (deprecated).

        Warn-only (fixable=False).  A loud migration hint pointing to
        ``dadaia migrate tree-v2`` is emitted regardless of the --fix flag.
        Auto-moving is intentionally blocked: root SPEC.md may hold
        SDD-approved content that requires operator consent to reclassify.
        """
        root_spec = self.specs_dir / "SPEC.md"
        if not root_spec.exists():
            return []
        return [
            SpecsDoctorIssue(
                code="TREE-2",
                severity=Severity.WARNING,
                description=(
                    "specs/SPEC.md exists at the tree root — this is the deprecated layout. "
                    f"{_TREE_MIGRATION_HINT}"
                ),
                path=str(root_spec),
                fixable=False,
            )
        ]

    def _check_tree3_memory_md(self) -> list[SpecsDoctorIssue]:
        """TREE-3: required memory .md atom files must exist.

        Checks: memory/architecture.md, memory/tech-stack.md,
        memory/quality-assurance.md, memory/product/index.md.

        .md is the canonical source (memory-markdown-source-v1 / D-4).
        No auto-fix: .md atoms are operator-authored, not generated from templates.
        """
        issues: list[SpecsDoctorIssue] = []
        mem_dir = self.specs_dir / "memory"
        for rel_path in _TREE3_MEMORY_FILES:
            target = mem_dir / rel_path
            if target.exists():
                continue
            issues.append(
                SpecsDoctorIssue(
                    code="TREE-3",
                    severity=Severity.WARNING,
                    description=(
                        f"memory/{rel_path} is missing — required memory .md atom. "
                        "Create it using `dadaia memory product add` or the born-markdown scaffold."
                    ),
                    path=str(target),
                    fixable=False,
                )
            )
        return issues

    def _check_tree4_required_dirs(self) -> list[SpecsDoctorIssue]:
        """TREE-4: backlog/, bugs/, and releases/ must exist under specs/.

        When a directory is absent the issue is emitted as fixable=True.
        The fix creates the dir, writes README.md (content copied from the
        canonical scaffold source), and touches .gitkeep — matching the exact
        output of ``scaffold()``.
        """
        issues: list[SpecsDoctorIssue] = []
        for dirname in _TREE4_REQUIRED_DIRS:
            target = self.specs_dir / dirname
            if target.exists():
                continue
            fixable = (
                self._scaffold_dir is not None
                and (self._scaffold_dir / dirname / "README.md").exists()
            )
            issues.append(
                SpecsDoctorIssue(
                    code="TREE-4",
                    severity=Severity.WARNING,
                    description=(
                        f"specs/{dirname}/ is missing — required spec tree directory. "
                        + (
                            "Auto-fix available (run doctor --fix)."
                            if fixable
                            else "No scaffold source available — create manually."
                        )
                    ),
                    path=str(target),
                    fixable=fixable,
                )
            )
        return issues

    def _fix_tree4(self, issue: SpecsDoctorIssue) -> None:
        """Create the missing directory with README.md and .gitkeep."""
        assert issue.code == "TREE-4"
        target = Path(issue.path)  # type: ignore[arg-type]
        dirname = target.name
        target.mkdir(parents=True, exist_ok=True)
        # README.md — copy from scaffold source
        readme_content = ""
        if self._scaffold_dir is not None:
            src_readme = self._scaffold_dir / dirname / "README.md"
            if src_readme.exists():
                readme_content = src_readme.read_text(encoding="utf-8")
        readme = target / "README.md"
        if not readme.exists():
            readme.write_text(readme_content, encoding="utf-8")
        # .gitkeep
        gitkeep = target / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.write_text("", encoding="utf-8")

    def _check_tree5_agents_md(self) -> list[SpecsDoctorIssue]:
        """TREE-5: specs/AGENTS.md must exist and its content must match the canonical template.

        Absent file → WARNING (fixable=False; cannot auto-create because the file
        is intended for operator customisation).
        Hash drift → WARNING (fixable=False; silent overwrite would destroy
        operator customisation — user must merge manually).

        When no templates_dir is available, hash comparison is skipped and
        only presence is checked.
        """
        agents_md = self.specs_dir / "AGENTS.md"
        if not agents_md.exists():
            return [
                SpecsDoctorIssue(
                    code="TREE-5",
                    severity=Severity.WARNING,
                    description=(
                        "specs/AGENTS.md is missing — expected SDD workflow contract. "
                        "Create it from the canonical template "
                        "(dadaia_workspace/public/templates/specs-AGENTS.md) "
                        "or run `dadaia specs init` to scaffold it."
                    ),
                    path=str(agents_md),
                    fixable=False,
                )
            ]

        # Hash comparison against canonical template
        if self._templates_dir is None:
            return []
        canonical_path = self._templates_dir / "specs-AGENTS.md"
        if not canonical_path.exists():
            return []
        canonical_text = canonical_path.read_text(encoding="utf-8")
        current_text = agents_md.read_text(encoding="utf-8")
        canonical_hash = hashlib.sha256(canonical_text.encode("utf-8")).hexdigest()
        current_hash = hashlib.sha256(current_text.encode("utf-8")).hexdigest()
        if canonical_hash == current_hash:
            return []
        return [
            SpecsDoctorIssue(
                code="TREE-5",
                severity=Severity.WARNING,
                description=(
                    f"specs/AGENTS.md has drifted from canonical template "
                    f"(current sha256:{current_hash[:12]}… vs "
                    f"canonical sha256:{canonical_hash[:12]}…). "
                    "Review the diff and merge any upstream changes manually — "
                    "auto-overwrite is disabled to protect operator customisations. "
                    "Canonical template: dadaia_workspace/public/templates/specs-AGENTS.md"
                ),
                path=str(agents_md),
                fixable=False,
            )
        ]

    def _check_memory_agents_md(self) -> list[SpecsDoctorIssue]:
        """Check: specs/memory/AGENTS.md must exist (WARNING only).

        The file is created during WS-2 (ai-engineer projects it from
        dadaia_workspace/public/data/memory-AGENTS.md).  It is expected to be
        absent on fresh scaffolds and early in the lifecycle, so absence is
        flagged as WARN (never ERROR) and does NOT cause doctor to exit non-zero.
        """
        memory_agents_md = self.specs_dir / "memory" / "AGENTS.md"
        if memory_agents_md.exists():
            return []
        return [
            SpecsDoctorIssue(
                code="TREE-5M",
                severity=Severity.WARNING,
                description=(
                    "specs/memory/AGENTS.md is missing — expected memory ownership contract. "
                    "Project it by running `dadaia public install --target all` after "
                    "dadaia_workspace/public/data/memory-AGENTS.md has been created."
                ),
                path=str(memory_agents_md),
                fixable=False,
            )
        ]

    def _check_tree6_release_artifacts(self) -> list[SpecsDoctorIssue]:
        """TREE-6: for the ACTIVE release, mandatory SDD artifacts must exist for its phase.

        Rule: if the active release exists and its phase is IMPLEMENTATION or CLOSURE,
        then SPEC.md, PLAN.md, and TASKS.md must all be present in the release directory.
        Any missing file is an ERROR (no auto-fix — creating an empty PLAN.md would
        constitute an unapproved artifact; human review is required).

        Inactive / non-active releases are not checked here (SPEC-DOC-004 already
        checks the active release's artifact statuses; we only add the TREE-6
        structural check for the IMPLEMENTATION/CLOSURE gates).

        Note: this invariant applies to the ACTIVE release only.  The broader
        per-release artifact check (SPEC-DOC-004) covers Status: field validation.
        """
        issues: list[SpecsDoctorIssue] = []
        active_path = self.specs_dir / "releases" / "ACTIVE.md"
        release, segment, phase, err = _read_active_md(active_path)
        if err or not release or release == "none":
            return issues
        if phase not in ("IMPLEMENTATION", "CLOSURE"):
            return issues
        rdir = self.specs_dir / "releases" / release
        if segment:  # schema v2: artifacts live in the active segment dir
            rdir = rdir / segment
        if not rdir.exists():
            return issues  # already reported by SPEC-DOC-009
        for fname in _TREE6_IMPL_ARTIFACTS:
            fpath = rdir / fname
            if not fpath.exists():
                issues.append(
                    SpecsDoctorIssue(
                        code="TREE-6",
                        severity=Severity.ERROR,
                        description=(
                            f"Active release '{release}' (phase={phase}) is missing "
                            f"mandatory SDD artifact: {fname}. "
                            "Create the artifact via the SDD lifecycle (product-engineer) — "
                            "do NOT create an empty placeholder."
                        ),
                        path=str(fpath),
                        fixable=False,
                    )
                )
        return issues

    def _check_tree7_bug_session_id(self) -> list[SpecsDoctorIssue]:
        """TREE-7: every bugs/<slug>.md must have a session_id frontmatter field.

        Expected frontmatter format (YAML-like leading lines):
            session_id: <value>   OR   session_id: null

        Missing field → ERROR (no auto-fix — injecting a session_id would
        falsify authorship; human review is required).

        If bugs/ does not exist, this check is a no-op.
        """
        issues: list[SpecsDoctorIssue] = []
        bugs_dir = self.specs_dir / "bugs"
        if not bugs_dir.exists():
            return issues
        for bug_file in sorted(bugs_dir.glob("*.md")):
            # Skip README.md and other non-bug files
            if bug_file.name in ("README.md",):
                continue
            text = bug_file.read_text(encoding="utf-8")
            has_session_id = bool(re.search(r"^session_id\s*:", text, re.MULTILINE))
            if not has_session_id:
                issues.append(
                    SpecsDoctorIssue(
                        code="TREE-7",
                        severity=Severity.ERROR,
                        description=(
                            f"bugs/{bug_file.name} is missing the required 'session_id:' "
                            "frontmatter field. "
                            "Add 'session_id: null' if the session is unknown. "
                            "Do NOT inject a fabricated session ID."
                        ),
                        path=str(bug_file),
                        fixable=False,
                    )
                )
        return issues

    # LINT-1 (memory-markdown-source-v1)
    def _check_lint1_memory_atoms(self) -> list[SpecsDoctorIssue]:
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

        try:
            result = subprocess.run(
                [sys.executable, str(_LINT_SCRIPT), "--memory-dir", str(mem_dir)],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except subprocess.TimeoutExpired:
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
        output = (result.stdout + result.stderr).strip()
        issues: list[SpecsDoctorIssue] = []

        if result.returncode == 0:
            return []
        if result.returncode == 1:
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
        elif result.returncode == 2:
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
                        f"{result.returncode}:\n{output}"
                    ),
                    path=str(mem_dir),
                )
            )
        return issues

    # CAT-1 (memory-context-enforcement-v1 / memory-markdown-source-v1)
    def _check_cat1_catalog_sync(self) -> list[SpecsDoctorIssue]:
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
