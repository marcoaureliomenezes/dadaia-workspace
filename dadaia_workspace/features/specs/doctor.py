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
import sys
from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import StrEnum
from pathlib import Path

import yaml

from dadaia_workspace.core.protocols.process_runner import ProcessResult, ProcessRunner
from dadaia_workspace.features.spec_context import lease, session_identity

#: SPEC-DOC-029: a ``<ctx>.lock.json`` filename component must be a real context name
#: (same path-traversal allowlist lease/session_identity enforce — CWE-22/CWE-59).
_CTX_NAME_RE = re.compile(r"[A-Za-z0-9_-]+")


def _validate_ctx_name(ctx: str) -> str:
    if not _CTX_NAME_RE.fullmatch(ctx):
        raise ValueError(f"invalid context name {ctx!r}")
    return ctx


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
# Vintage releases (Created: <= 2026-06-04) are excluded — this grandfathers the frozen
# pre-June-5 _archive sub-patch releases (v0.1.4.1..v0.1.4.6, ctx-inject-v2-drift-fix-v1)
# that predate the SemVer-folder mandate's rollout; the rule keeps hard-enforcing for
# every release created after the cutoff (v0.1.44 onward). See specs/bugs/
# specs-doctor-errors-on-frozen-nonsemver-archives.md (v0.1.45).
RELEASE_SEMVER_RE = re.compile(r"^v\d+\.\d+\.\d+$")
RELEASE_SEMVER_CUTOFF = date(2026, 6, 1)  # WARNING starts here
RELEASE_SEMVER_HARD = date(2026, 7, 1)  # ERROR starts here
RELEASE_VINTAGE_CUTOFF = date(2026, 6, 4)  # releases on/before this are excluded

# SPEC-DOC-027 (ADR-9, v0.1.11): permanent documented allowlist of legacy ``_archive``
# release-dir names that predate the SemVer naming canon. These are FROZEN HISTORY:
# renaming an archived dir would break historical pointers and is pure churn, so the
# honest permanent record is this enumerated allowlist (rationale: ADR-9). The doctor
# stays silent for exactly these names *only inside _archive/releases/* — they never
# silence a non-canon dir in the LIVE releases/ tree, and any name NOT in this set
# still WARNs, so forward enforcement for new/unrecognised legacy dirs is intact.
#   - ``ctx-inject-v2-drift-fix-v1`` / ``memory-markdown-source-v1``: pre-canon
#     descriptive-slug releases (the slug-naming era before SemVer dirs).
#   - ``v0.1.4.1``..``v0.1.4.6`` + ``v0.1.4.3-report-retention``: the v0.1.4.x hotfix
#     family, four-segment + suffixed names that predate the three-segment canon.
RELEASE_NAMING_LEGACY_ALLOWLIST: frozenset[str] = frozenset(
    {
        "ctx-inject-v2-drift-fix-v1",
        "memory-markdown-source-v1",
        "v0.1.4.1",
        "v0.1.4.2",
        "v0.1.4.3",
        "v0.1.4.3-report-retention",
        "v0.1.4.4",
        "v0.1.4.5",
        "v0.1.4.6",
    }
)

# SPEC-DOC-023: hotfix bullets older than 72 hours in ## Hotfixes pendentes get WARNING
_HOTFIX_STALE_HOURS = 72

# SPEC-DOC-030 (constitution §8 collision-safe naming): every new specs/audits/ directory
# must be named ``<YYYYMMDDTHHMMSSZ>-<session_id_8chars>`` so two concurrent additive
# sessions never collide. Compact timestamp (no colons/dashes inside it) + an 8-char
# session discriminator.
AUDIT_DIR_NAME_RE = re.compile(r"^\d{8}T\d{6}Z-[A-Za-z0-9]{8}$")

# Four audit dirs from the v0.1.9/v0.1.10 audit cycles predate the doctor WARN and are
# grandfathered in place by the constitution §8 amendment (2026-06-10) — their session ids
# are unrecoverable and their timestamps are cross-referenced in immutable ledger reports.
_AUDIT_DIR_GRANDFATHER: frozenset[str] = frozenset(
    {
        "2026-06-09T075056Z",
        "2026-06-10T010550Z",
        "2026-06-10T052944Z",
        "2026-06-10T140553Z",
    }
)

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

# ──────────────────────────────────────────────────────────────────────────────
# SPEC-DOC-031 / SPEC-DOC-032 — closure-disposition canon (T-011-10, bug B1, ADR-6/ADR-11)
# ──────────────────────────────────────────────────────────────────────────────

# ADR-11 single-source status-token vocabulary.
#
# Backlog (case-insensitive prefix match on the Status line value):
#   non-terminal = {OPEN, PICKED, CANDIDATE}; terminal = {DELIVERED, SUPERSEDED,
#   RESOLVED, CONSUMED, DEFERRED, REJECTED} (+ free suffixes like ``— vX.Y.Z``).
# Only the NON-TERMINAL set drives SPEC-DOC-031: a non-terminal backlog entry whose
# slug is referenced by an archived release is the consumed-but-unsanitized drift.
_BACKLOG_NONTERMINAL_PREFIXES: tuple[str, ...] = ("open", "picked", "candidate")

# Bugs (ADR-11): the canon is exactly {Open, Closed} (case-insensitive). SPEC-DOC-032
# WARNs on anything else (legacy Fixed/resolved/Rejected tokens, etc.).
_BUG_STATUS_CANON: frozenset[str] = frozenset({"open", "closed"})

# Match a Status line in a backlog entry: ``Status: ...`` or ``**Status:** ...``.
_BACKLOG_STATUS_RE = re.compile(r"^\s*(?:\*\*)?status\*?\*?\s*:?\*?\*?\s*(.+)$", re.IGNORECASE)

# Match a bug frontmatter ``status:`` line (frontmatter is leading YAML-like lines).
_BUG_STATUS_RE = re.compile(r"^status\s*:\s*(\S+)", re.IGNORECASE | re.MULTILINE)

# Aggregate / free-form backlog files that are not per-slug backlog entries.
_BACKLOG_AGGREGATE_FILES: frozenset[str] = frozenset({"candidates.md", "ideas.md", "README.md"})

# ADR-6: matches inside a ``## Backlog returns`` section of an archived CLOSURE are a
# legitimate return (the slug is being ADDED for a future release, not consumed) and are
# the documented false-positive class. SPEC-DOC-031 stays WARN (never ERR) for this reason.
_BACKLOG_RETURNS_HEADING_RE = re.compile(r"^##\s+Backlog\s+returns\b", re.IGNORECASE)


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


# HTML-era parser deleted in v0.1.7 post-memory-markdown-source-v1 cleanup.


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
        process_runner: ProcessRunner | None = None,
        repo_root: Path | None = None,
        workspace_state_dir: Path | None = None,
        pid_probe: lease.PidProbe | None = None,
    ) -> None:
        self.specs_dir = Path(specs_dir)
        self.public_dir: Path | None = Path(public_dir) if public_dir is not None else None
        # repo_root: when supplied, the constitution file-ref invariant (SPEC-DOC-028)
        # resolves path-like references against it. None → that check is a no-op.
        self.repo_root: Path | None = Path(repo_root) if repo_root is not None else None
        # workspace_state_dir: the workspace-level ``.dadaia/`` directory holding
        # ``states/ctx_locks/*.lock`` + ``sessions/*.json``. The doctor is otherwise a
        # pure module scoped to specs_dir/public_dir (both under the repo); lease/session
        # records live at the WORKSPACE root, outside the specs tree, so the lease↔session
        # coherence backstop (SPEC-DOC-029) can only run when a caller injects this path.
        # None (the default) → the backstop is a documented no-op.
        self.workspace_state_dir: Path | None = (
            Path(workspace_state_dir) if workspace_state_dir is not None else None
        )
        # pid_probe: the PID-liveness seam for the SPEC-DOC-029 three-state triage
        # (T-011-03). Composition-root-wired (like ``workspace_state_dir``): the CLI
        # ``dadaia specs doctor`` builds it from the hook layer's ``OsProcessProbe`` and
        # injects it here. ``features/specs/doctor.py`` therefore NEVER imports the
        # infrastructure process-probe adapter — the import-linter layering law holds.
        # ``None`` (the default / a pure-module construction) ⇒ TTL-only liveness:
        # a TTL-expired record is treated as a dead holder (no veto), and a legacy
        # pid-less record likewise degrades to the TTL verdict.
        self.pid_probe: lease.PidProbe | None = pid_probe
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

        # ProcessRunner: injected for tests/DI; lazily resolved to the infra adapter in
        # production when not provided.
        self._process_runner: ProcessRunner | None = process_runner

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
        # v0.1.10 / T-010-14 (R6b) — ledger invariants + identity-coherence backstop
        issues.extend(self._check_phase_markers_coherence())  # SPEC-DOC-024
        issues.extend(self._check_unique_release_ids())  # SPEC-DOC-026
        issues.extend(self._check_release_naming_canon())  # SPEC-DOC-027
        issues.extend(self._check_constitution_file_refs())  # SPEC-DOC-028
        issues.extend(self._check_lease_session_coherence())  # SPEC-DOC-029
        issues.extend(self._check_audits_naming_canon())  # SPEC-DOC-030
        # v0.1.11 / T-011-10 (bug B1) — closure-disposition canon
        issues.extend(self._check_consumed_backlog_disposition())  # SPEC-DOC-031
        issues.extend(self._check_bug_status_canon())  # SPEC-DOC-032
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

        Resolves TREE-4 only (create missing spec-tree dirs with README.md +
        .gitkeep, from the canonical scaffold source).  TREE-3 memory atoms are
        operator-authored ``.md`` (no Jinja/HTML generation) and are warn-only;
        warn-only and no-fix invariants are never touched.

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
        """SPEC-DOC-006: every archived release dir must have a complete CLOSURE.md.

        v0.1.10 (T-010-14): recurse into nested archive layouts so legacy milestone
        dirs (e.g. ``_archive/releases/v0.2.0/v0.1.9``) that carry SDD release
        artifacts (SPEC/PLAN/TASKS) but no CLOSURE.md are also caught — the original
        check only inspected the top level of ``_archive/releases/``.
        """
        issues: list[SpecsDoctorIssue] = []
        arch = self.specs_dir / "_archive" / "releases"
        if not arch.exists():
            return issues
        for release_dir in self._iter_archive_release_dirs(arch):
            # Documented-legacy nested milestone dirs (e.g. v0.2.0/v0.1.9) are slated
            # for rename + retro-CLOSURE in T-010-15. Until then they are surfaced at
            # WARNING — not ERROR — so doctor stays exit-0 on the un-repaired tree
            # (matching the SPEC-DOC-026 legacy carve-out). Top-level archive dirs keep
            # the original ERROR contract.
            is_legacy_nested = self._is_legacy_nested_release(release_dir, arch)
            closure = release_dir / "CLOSURE.md"
            if not closure.exists():
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-006",
                        severity=(Severity.WARNING if is_legacy_nested else Severity.ERROR),
                        description=(
                            "Archived release "
                            f"{release_dir.relative_to(self.specs_dir).as_posix()} "
                            "has no CLOSURE.md"
                            + (
                                " (documented-legacy nested dir — slated for "
                                "rename + retro-CLOSURE in T-010-15)"
                                if is_legacy_nested
                                else ""
                            )
                        ),
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

    # ──────────────────────────────────────────────────────────────────────────
    # Release-dir discovery helpers (shared by SPEC-DOC-006/026/027)
    # ──────────────────────────────────────────────────────────────────────────

    # A dir counts as a "release dir" iff it carries at least one SDD release artifact.
    _RELEASE_ARTIFACTS: tuple[str, ...] = ("SPEC.md", "PLAN.md", "TASKS.md", "CLOSURE.md")
    # Segment dirs (ADR-1/ADR-5) live *inside* a release dir and are not themselves
    # releases: alpha-N, rc-N, plus the historical `integration` segment container.
    _SEGMENT_NAME_RE = re.compile(r"^(?:alpha|rc)-\d+$|^integration$")

    def _is_release_dir(self, d: Path) -> bool:
        if not d.is_dir() or not any((d / a).exists() for a in self._RELEASE_ARTIFACTS):
            return False
        # Segment dirs (alpha-N/rc-N/integration) are an orthogonal lifecycle concept,
        # not releases — they carry artifacts but their *release id* is the parent dir.
        # Exclude them from release-id-uniqueness and naming-canon invariants.
        return self._SEGMENT_NAME_RE.match(d.name) is None

    def _iter_archive_release_dirs(self, arch: Path) -> list[Path]:
        """All release dirs under ``_archive/releases/`` (recursive).

        Recurses so nested legacy milestone layouts (``v0.2.0/v0.1.9``) are
        discovered. A dir qualifies only when it carries an SDD release artifact;
        plain segment containers without artifacts are skipped (their artifact-bearing
        children are still found by the recursion).
        """
        out: list[Path] = []
        for d in sorted(p for p in arch.rglob("*") if p.is_dir()):
            if self._is_release_dir(d):
                out.append(d)
        return out

    def _is_legacy_nested_release(self, d: Path, releases_root: Path) -> bool:
        """True when ``d`` is a release dir nested *below* the top level of a
        releases root — i.e. its parent is itself a release dir, not the root.

        These are the documented-legacy milestone dirs (audit §4 collision:
        ``_archive/releases/v0.2.0/v0.1.{6..9}``). Per T-010-14 they earn a WARNING,
        never an ERROR, until T-010-15 renames them.
        """
        try:
            d.relative_to(releases_root)
        except ValueError:
            return False
        parent = d.parent
        return parent != releases_root and self._is_release_dir(parent)

    def _iter_all_release_dirs(self) -> list[tuple[Path, Path, bool]]:
        """Enumerate every release dir across ``releases/`` and ``_archive/releases/``.

        Returns a list of ``(dir, releases_root, is_legacy_nested)`` triples. The
        active ``releases/`` root is enumerated at its top level only (a release in
        progress has no nested release dirs); the archive root is enumerated
        recursively to surface the nested-collision legacy layout.
        """
        out: list[tuple[Path, Path, bool]] = []
        live_root = self.specs_dir / "releases"
        if live_root.is_dir():
            for d in sorted(p for p in live_root.iterdir() if p.is_dir()):
                if self._is_release_dir(d):
                    out.append((d, live_root, False))
        arch_root = self.specs_dir / "_archive" / "releases"
        if arch_root.is_dir():
            for d in self._iter_archive_release_dirs(arch_root):
                out.append((d, arch_root, self._is_legacy_nested_release(d, arch_root)))
        return out

    # ──────────────────────────────────────────────────────────────────────────
    # T-010-14 (R6b) — ledger invariants
    # ──────────────────────────────────────────────────────────────────────────

    # SPEC-DOC-024: phase ↔ markers coherence.
    _TASK_MARKER_RE = re.compile(r"^\s*[-*]?\s*\[([ \-xX])\]", re.MULTILINE)

    def _active_tasks_markers(self, release: str, segment: str | None) -> list[str] | None:
        """Return the list of task marker chars (' ', '-', 'x') for the active release's
        TASKS.md, or None when TASKS.md is absent/unreadable."""
        rdir = self.specs_dir / "releases" / release
        if segment:
            rdir = rdir / segment
        tasks = rdir / "TASKS.md"
        if not tasks.exists():
            return None
        text = tasks.read_text(encoding="utf-8")
        return [m.group(1).lower() for m in self._TASK_MARKER_RE.finditer(text)]

    def _check_phase_markers_coherence(self) -> list[SpecsDoctorIssue]:
        """SPEC-DOC-024: ACTIVE.md ``phase`` must be coherent with the active release's
        TASKS.md markers (constitution §7 lifecycle).

        Mechanical rules (minimal):
        - phase ∈ {SPEC, DEFINITION}: the active TASKS must NOT already be an
          ``[x]``-majority (work claimed complete before implementation began —
          the live audit incident where phase=SPEC but 19/19 tasks were ``[x]``).
        - phase == IMPLEMENTATION: TASKS.md must exist and carry ``**Status:** Aprovado``.
        - phase == CLOSURE: every non-CLOSURE task must be ``[x]`` (no ``[ ]``/``[-]``).
        Other phases are not constrained here.
        """
        issues: list[SpecsDoctorIssue] = []
        active_path = self.specs_dir / "releases" / "ACTIVE.md"
        release, segment, phase, err = _read_active_md(active_path)
        if err or not release or release == "none" or phase is None:
            return issues
        rdir = self.specs_dir / "releases" / release
        if segment:
            rdir = rdir / segment
        if not rdir.exists():
            return issues  # release dir issues already reported by SPEC-DOC-009/004

        markers = self._active_tasks_markers(release, segment)

        if phase in ("SPEC", "DEFINITION"):
            if markers:
                done = sum(1 for m in markers if m == "x")
                if done * 2 > len(markers):  # strict [x]-majority
                    issues.append(
                        SpecsDoctorIssue(
                            code="SPEC-DOC-024",
                            severity=Severity.ERROR,
                            description=(
                                f"ACTIVE.md phase='{phase}' but the active release "
                                f"'{release}' has an [x]-majority TASKS.md "
                                f"({done}/{len(markers)} done). The phase field was "
                                "never advanced through IMPLEMENTATION — advance ACTIVE.md "
                                "or correct the markers (constitution §7)."
                            ),
                            path=str(active_path),
                        )
                    )
        elif phase == "IMPLEMENTATION":
            tasks = rdir / "TASKS.md"
            if not tasks.exists():
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-024",
                        severity=Severity.ERROR,
                        description=(
                            f"ACTIVE.md phase='IMPLEMENTATION' but active release "
                            f"'{release}' has no TASKS.md."
                        ),
                        path=str(tasks),
                    )
                )
            elif _extract_status(tasks) != "Aprovado":
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-024",
                        severity=Severity.ERROR,
                        description=(
                            f"ACTIVE.md phase='IMPLEMENTATION' but TASKS.md of release "
                            f"'{release}' is not '**Status:** Aprovado' "
                            f"(found '{_extract_status(tasks)}'). Implementation phase "
                            "requires an approved TASKS.md (constitution §7)."
                        ),
                        path=str(tasks),
                    )
                )
        elif phase == "CLOSURE" and markers is not None:
            unfinished = sum(1 for m in markers if m != "x")
            if unfinished:
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-024",
                        severity=Severity.ERROR,
                        description=(
                            f"ACTIVE.md phase='CLOSURE' but active release '{release}' "
                            f"has {unfinished} unfinished task marker(s) "
                            "(expected every task '[x]' before closure; "
                            "constitution §7)."
                        ),
                        path=str(active_path),
                    )
                )
        return issues

    def _check_unique_release_ids(self) -> list[SpecsDoctorIssue]:
        """SPEC-DOC-026: release ids (dir basenames) must be unique across
        ``releases/`` ∪ ``_archive/releases/`` (recursive).

        A collision among two real (non-legacy) dirs is an ERROR. A collision that
        involves a documented-legacy nested dir (``v0.2.0/v0.1.9`` milestone layout)
        is a WARNING — these are slated for rename in T-010-15 and must not break
        doctor exit-0 in the meantime.
        """
        issues: list[SpecsDoctorIssue] = []
        by_name: dict[str, list[tuple[Path, bool]]] = {}
        for d, _root, is_legacy in self._iter_all_release_dirs():
            by_name.setdefault(d.name, []).append((d, is_legacy))

        for name, entries in sorted(by_name.items()):
            if len(entries) < 2:
                continue
            any_legacy = any(is_legacy for _d, is_legacy in entries)
            severity = Severity.WARNING if any_legacy else Severity.ERROR
            paths = ", ".join(d.relative_to(self.specs_dir).as_posix() for d, _ in sorted(entries))
            note = (
                " (documented-legacy nested dir — slated for rename in T-010-15)"
                if any_legacy
                else ""
            )
            issues.append(
                SpecsDoctorIssue(
                    code="SPEC-DOC-026",
                    severity=severity,
                    description=(
                        f"Release id '{name}' is not unique across releases/ + "
                        f"_archive/releases/: {paths}{note}."
                    ),
                    path=str(self.specs_dir / "_archive" / "releases"),
                )
            )
        return issues

    def _check_release_naming_canon(self) -> list[SpecsDoctorIssue]:
        """SPEC-DOC-027: release dir names should match ``^v\\d+\\.\\d+\\.\\d+$``.

        Severity follows the same legacy policy as SPEC-DOC-016 so the two checks
        never disagree:
        - A non-conforming dir in the live ``releases/`` tree whose SPEC.md
          ``Created:`` date is on/after the canon cutoff (``RELEASE_SEMVER_CUTOFF``)
          is an ERROR — a release born after the canon must be SemVer-clean.
        - Every other non-conforming dir (archive, vintage ``Created:`` ≤
          ``RELEASE_VINTAGE_CUTOFF``, pre-cutoff, or undeterminable date) is a
          WARNING — legacy names predate the canon and are preserved until renamed.

        ADR-9 (v0.1.11): archived dirs whose name is in the permanent documented
        ``RELEASE_NAMING_LEGACY_ALLOWLIST`` are silenced entirely — they are frozen
        history that is never renamed. The allowlist is name-exact and ``_archive``-only,
        so any unrecognised legacy dir still WARNs and forward enforcement holds.
        """
        issues: list[SpecsDoctorIssue] = []
        for d, root, _is_legacy in self._iter_all_release_dirs():
            if RELEASE_SEMVER_RE.match(d.name):
                continue
            is_live = root == self.specs_dir / "releases"
            # ADR-9: archived dirs on the permanent legacy allowlist are silent (frozen
            # history, never renamed). The allowlist applies ONLY to _archive/ — a
            # non-canon dir in the live releases/ tree is never silenced this way.
            if not is_live and d.name in RELEASE_NAMING_LEGACY_ALLOWLIST:
                continue
            spec_path = d / "SPEC.md"
            created = _extract_created_date(spec_path) if spec_path.exists() else None
            born_after_canon = created is not None and created >= RELEASE_SEMVER_CUTOFF
            severity = Severity.ERROR if (is_live and born_after_canon) else Severity.WARNING
            issues.append(
                SpecsDoctorIssue(
                    code="SPEC-DOC-027",
                    severity=severity,
                    description=(
                        f"Release dir '{d.relative_to(self.specs_dir).as_posix()}' does "
                        "not follow the naming canon ^v<MAJOR>.<MINOR>.<PATCH>$ "
                        + (
                            "— rename it (SPEC-DOC-027)."
                            if severity == Severity.ERROR
                            else "— legacy name (WARNING, preserved until renamed)."
                        )
                    ),
                    path=str(d),
                )
            )
        return issues

    # SPEC-DOC-028: path-like backtick references in constitution.md.
    _CONSTITUTION_REF_RE = re.compile(
        r"`([A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:py|md|sh|json|toml|txt|cfg|yml|yaml))`"
    )

    def _check_constitution_file_refs(self) -> list[SpecsDoctorIssue]:
        """SPEC-DOC-028: every path-like backtick reference in constitution.md to a
        repo file should resolve.

        Resolution is relative to ``repo_root``; without it the check is a no-op
        (the doctor is otherwise a pure specs_dir-scoped module). References that
        are clearly not repo paths (bare filenames, glob-only, or generic tokens
        like ``<id>``) are skipped — only refs containing a ``/`` separator OR a
        recognised root-level filename are resolved, to avoid false positives on
        illustrative inline names.
        """
        if self.repo_root is None:
            return []
        constitution = self.specs_dir / "constitution.md"
        if not constitution.exists():
            return []
        text = constitution.read_text(encoding="utf-8")
        issues: list[SpecsDoctorIssue] = []
        seen: set[str] = set()
        for m in self._CONSTITUTION_REF_RE.finditer(text):
            ref = m.group(1)
            if ref in seen:
                continue
            seen.add(ref)
            # Only resolve refs that look like a real repo path: they must contain a
            # directory separator (e.g. ``docs/01_medium_codex.md``,
            # ``specs/memory/architecture.md``). Bare filenames (``AGENTS.md``,
            # ``CLAUDE.md``, ``SPEC.md``) are contract tokens that appear in many
            # locations and are intentionally not resolved here.
            if "/" not in ref:
                continue
            if (self.repo_root / ref).exists():
                continue
            issues.append(
                SpecsDoctorIssue(
                    code="SPEC-DOC-028",
                    severity=Severity.WARNING,
                    description=(
                        f"constitution.md references '{ref}' but it does not resolve "
                        f"against the repo root ({self.repo_root}). Fix the path or "
                        "remove the stale reference (SPEC-DOC-028)."
                    ),
                    path=str(constitution),
                )
            )
        return issues

    def _check_lease_session_coherence(self) -> list[SpecsDoctorIssue]:
        """SPEC-DOC-029 (D-2 backstop) — three-state triage (T-011-03, bug B3).

        The lease-record holder, the incumbent pointer, and the session record may never
        name three different sessions for one *live* context. But a TTL-expired lock left
        by a dead session is **not** forgery — it is just a stale lease that was never
        garbage-collected. Conflating the two produced the
        ``doctor-stale-lease-misdiagnosed-as-forgery`` bug (a ~36 h-old, ``ttl: 120`` record
        from a dead session alleged as "possible out-of-band lock/ptr forgery"). The triage
        distinguishes three states per ``<ctx>.lock.json`` record:

        * **(a) stale lease, holder dead/unprobeable** — the record is TTL-expired and the
          holder pid is dead (per the injected ``pid_probe``) OR the record predates the
          ``pid`` field (legacy, unprobeable ⇒ TTL verdict). ⇒ **WARN**: "stale lease from
          a dead session — safe to reclaim", naming the remediation commands
          (``dadaia doctor --fix`` / ``dadaia lock steal <ctx>``). No forgery wording; the
          overall doctor exit stays 0 when no other ERROR exists.
        * **(b) live holder, genuine incoherence** — the record is live (TTL-fresh, or
          TTL-expired but its pid is demonstrably alive per ``pid_probe``) AND the three
          identity sources genuinely diverge. ⇒ **ERROR** with the out-of-band forgery
          wording. This is the *only* state where forgery language is emitted.
        * **(c) coherent** — a live, coherent lease ⇒ silent.

        The doctor is a pure module scoped to specs_dir/public_dir; the lock and session
        stores live at the *workspace* root (``.dadaia/states/ctx_locks/<ctx>.lock.json``
        + ``.dadaia/sessions/<id>.json`` + ``.dadaia/sessions/runtime/<ctx>.ptr``), outside
        the specs tree. This backstop only runs when a caller injects ``workspace_state_dir``;
        with the default (``None``) it is a documented no-op (see ``__init__``).

        Liveness is the canonical lease verdict (:func:`lease.is_held`, which delegates to
        ``core.lock_liveness.is_stale``): TTL is the floor, the ``pid_probe`` is the veto. The
        probe is composition-root-wired via ``self.pid_probe`` (never an infrastructure
        import inside ``features``). The three-source divergence verdict for live holders is
        delegated to :func:`session_identity.coherence` — the single designed coherence API
        (FR-R3-02) — so there is no duplicate copy of that logic here.
        """
        state_dir = self.workspace_state_dir
        if state_dir is None:
            return []  # no-op: lease/session stores are unreachable from a pure specs_dir
        locks_dir = state_dir / "states" / "ctx_locks"
        if not locks_dir.is_dir():
            return []
        # session_identity / lease take the WORKSPACE root and append ``.dadaia/...``
        # internally; workspace_state_dir is that ``.dadaia`` directory, so its parent is
        # the workspace root.
        workspace_root = state_dir.parent
        issues: list[SpecsDoctorIssue] = []
        for record_file in sorted(locks_dir.glob("*.lock.json")):
            ctx = record_file.name[: -len(".lock.json")]
            try:
                _validate_ctx_name(ctx)
            except ValueError:
                continue  # not a real context-keyed record name
            record = lease.read_record(workspace_root, ctx)
            # State (a): a stale lease whose holder is dead/unprobeable. ``lease.is_held``
            # is True iff the record is live (TTL-fresh, or TTL-expired with an alive pid
            # under ``pid_probe``); not-held ⇒ reclaimable dead/legacy record.
            holder_is_live = lease.is_held(workspace_root, ctx, pid_probe=self.pid_probe)
            if not holder_is_live:
                holder = record.get("session_id") if isinstance(record, dict) else None
                holder_desc = repr(str(holder)) if holder else "an ended session"
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-029",
                        severity=Severity.WARNING,
                        description=(
                            f"Context {ctx!r}: stale lease from a dead session "
                            f"(holder {holder_desc}, heartbeat past TTL) — safe to reclaim. "
                            f"Run 'dadaia doctor --fix' to garbage-collect it, or "
                            f"'dadaia lock steal {ctx}' to take it over (SPEC-DOC-029, "
                            "WARNING)."
                        ),
                        path=str(record_file),
                    )
                )
                continue
            # State (b)/(c): the holder is LIVE. Only now is a three-source divergence a
            # genuine incoherence worth flagging as possible forgery.
            holder = record.get("session_id") if isinstance(record, dict) else None
            lock_holder = str(holder) if holder else None
            message = session_identity.coherence(workspace_root, ctx, lock_holder=lock_holder)
            if message is not None:
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-029",
                        severity=Severity.ERROR,
                        description=(
                            f"{message} — live lease↔session incoherence (possible "
                            "out-of-band lock/ptr forgery; D-2 backstop, SPEC-DOC-029)."
                        ),
                        path=str(record_file),
                    )
                )
            # else state (c): live + coherent ⇒ silent.
        return issues

    def _check_audits_naming_canon(self) -> list[SpecsDoctorIssue]:
        """SPEC-DOC-030 (constitution §8): WARN on any non-conforming ``specs/audits/`` dir.

        Forward enforcement of the collision-safe naming law: every audit directory must
        be named ``<YYYYMMDDTHHMMSSZ>-<session_id_8chars>`` (:data:`AUDIT_DIR_NAME_RE`) so
        two concurrent additive sessions never collide on a path. WARN-only (legacy names
        are preserved, never auto-renamed), mirroring the SPEC-DOC-027 legacy policy.

        Exempt: the four grandfathered dirs from the §8 amendment
        (:data:`_AUDIT_DIR_GRANDFATHER`) and ``specs/audits/_archive/``. Silent when the
        ``audits/`` dir is absent.
        """
        audits_dir = self.specs_dir / "audits"
        if not audits_dir.is_dir():
            return []
        issues: list[SpecsDoctorIssue] = []
        for child in sorted(audits_dir.iterdir()):
            if not child.is_dir():
                continue
            name = child.name
            if name == "_archive" or name in _AUDIT_DIR_GRANDFATHER:
                continue
            if AUDIT_DIR_NAME_RE.match(name):
                continue
            issues.append(
                SpecsDoctorIssue(
                    code="SPEC-DOC-030",
                    severity=Severity.WARNING,
                    description=(
                        f"Audit dir 'audits/{name}' does not follow the collision-safe "
                        "naming law <YYYYMMDDTHHMMSSZ>-<session_id_8chars> (constitution §8) "
                        "— rename it (SPEC-DOC-030, WARNING)."
                    ),
                    path=str(child),
                )
            )
        return issues

    def _backlog_status_value(self, text: str) -> str | None:
        """Extract the (first) Status line value from a backlog entry's body.

        Accepts both ``Status: <value>`` and ``**Status:** <value>``. Returns the
        stripped value, or ``None`` when no Status line is present.
        """
        for line in text.splitlines():
            m = _BACKLOG_STATUS_RE.match(line)
            if m:
                return m.group(1).strip()
        return None

    def _archive_consumption_hits(self, slug: str) -> list[str]:
        """Release ids of archived CLOSURE/SPEC that reference ``slug`` as consumed.

        Scans every ``specs/_archive/releases/*/CLOSURE.md`` and ``.../SPEC.md`` for a
        line containing ``slug``. Lines inside a ``## Backlog returns`` section are
        EXCLUDED (ADR-6: the slug is being ADDED for a future release, not consumed — the
        documented false-positive class). Returns the sorted, de-duplicated set of
        archived release ids that reference the slug outside Backlog-returns sections.
        """
        arch = self.specs_dir / "_archive" / "releases"
        if not arch.is_dir():
            return []
        hits: set[str] = set()
        for release_dir in self._iter_archive_release_dirs(arch):
            release_id = release_dir.name
            for doc_name in ("CLOSURE.md", "SPEC.md"):
                doc = release_dir / doc_name
                if not doc.is_file():
                    continue
                in_backlog_returns = False
                for raw_line in doc.read_text(encoding="utf-8").splitlines():
                    if raw_line.startswith("## "):
                        in_backlog_returns = bool(_BACKLOG_RETURNS_HEADING_RE.match(raw_line))
                    if in_backlog_returns:
                        continue
                    if slug in raw_line:
                        hits.add(release_id)
                        break
        return sorted(hits)

    def _check_consumed_backlog_disposition(self) -> list[SpecsDoctorIssue]:
        """SPEC-DOC-031 (T-011-10, bug B1, ADR-6): WARN on consumed-but-unsanitized backlog.

        A ``specs/backlog/<slug>.md`` entry whose Status line is an ADR-11 NON-TERMINAL
        token ({OPEN, PICKED, CANDIDATE}, case-insensitive prefix match) AND whose slug is
        referenced by an archived release CLOSURE/SPEC (outside ``## Backlog returns``
        sections) ⇒ **WARNING**. The lifecycle contract is that a backlog item consumed
        into a shipped+archived release must be flipped to a terminal disposition token
        during CLOSURE; a non-terminal status on a referenced slug is the drift.

        Severity is WARN, never ERR (ADR-6): a slug mention is necessary-but-not-sufficient
        evidence of consumption — the "Backlog returns" section (excluded here) and
        defer/supersede mentions in archived CLOSUREs are the known false-positive class.
        Aggregate files (``candidates.md``/``ideas.md``/``README.md``) are skipped.
        """
        backlog_dir = self.specs_dir / "backlog"
        if not backlog_dir.is_dir():
            return []
        issues: list[SpecsDoctorIssue] = []
        for entry in sorted(backlog_dir.glob("*.md")):
            if entry.name in _BACKLOG_AGGREGATE_FILES:
                continue
            slug = entry.stem
            status = self._backlog_status_value(entry.read_text(encoding="utf-8"))
            if status is None:
                continue
            status_lower = status.lower()
            if not status_lower.startswith(_BACKLOG_NONTERMINAL_PREFIXES):
                continue
            hits = self._archive_consumption_hits(slug)
            if not hits:
                continue
            releases = ", ".join(hits)
            issues.append(
                SpecsDoctorIssue(
                    code="SPEC-DOC-031",
                    severity=Severity.WARNING,
                    description=(
                        f"backlog/{entry.name} has non-terminal status '{status}' but its "
                        f"slug is referenced by archived release(s) {releases} (outside "
                        "'Backlog returns' sections). If it was consumed/shipped, flip the "
                        "status to an ADR-11 terminal token (DELIVERED/SUPERSEDED/RESOLVED/"
                        "CONSUMED — vX.Y.Z) with an evidence pointer. WARNING only — a slug "
                        "mention is not proof of consumption (ADR-6 false-positive class)."
                    ),
                    path=str(entry),
                )
            )
        return issues

    def _check_bug_status_canon(self) -> list[SpecsDoctorIssue]:
        """SPEC-DOC-032 (T-011-10, bug B1, ADR-11): WARN on non-canonical bug status tokens.

        Every ``specs/bugs/<slug>.md`` frontmatter ``status:`` must be in the ADR-11 bug
        canon {``Open``, ``Closed``} (case-insensitive). Anything else (legacy ``Fixed`` /
        ``resolved`` / ``Rejected`` etc.) ⇒ **WARNING**. A duplicate/rejected bug should be
        ``Closed`` with a ``superseded_by:`` frontmatter field, not a ``Rejected`` token.
        ``README.md`` is skipped; an absent ``bugs/`` dir is a no-op.
        """
        bugs_dir = self.specs_dir / "bugs"
        if not bugs_dir.is_dir():
            return []
        issues: list[SpecsDoctorIssue] = []
        for bug_file in sorted(bugs_dir.glob("*.md")):
            if bug_file.name in ("README.md",):
                continue
            m = _BUG_STATUS_RE.search(bug_file.read_text(encoding="utf-8"))
            if m is None:
                # Missing status is a separate concern (TREE-7 governs session_id); a bug
                # with no status line at all is not flagged by this status-canon check.
                continue
            status = m.group(1).strip()
            if status.lower() in _BUG_STATUS_CANON:
                continue
            issues.append(
                SpecsDoctorIssue(
                    code="SPEC-DOC-032",
                    severity=Severity.WARNING,
                    description=(
                        f"bugs/{bug_file.name} has status '{status}' outside the ADR-11 bug "
                        "canon {Open, Closed}. Normalize it: a fixed bug ⇒ 'Closed'; a "
                        "duplicate/rejected bug ⇒ 'Closed' with a 'superseded_by: <slug>' "
                        "frontmatter field (SPEC-DOC-032, WARNING)."
                    ),
                    path=str(bug_file),
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
