"""Coherence validator (v0.1.55 FR1): constitution, orchestration registry.

Single-responsibility sibling of the SpecsDoctor coordinator. Owns the cross-cutting coherence
checks: constitution presence (SPEC-DOC-001), the D-OC-1 orchestration-registry coherence,
pattern-version staleness (SPECS-VERSION), constitution file-refs (SPEC-DOC-028), and the
constitution runtime-enum guard (SPEC-DOC-037).

v0.1.76 T-4 (FR7, NO-LOCKS DOCTRINE): the former lease<->session coherence backstop
(SPEC-DOC-029) is RETIRED. It diagnosed a residual ``<ctx>.lock.json`` holder against the
incumbent pointer / session record for possible "out-of-band forgery" — a diagnosis that
depended on the lease's acquisition/CAS authority actually meaning something. T-3 deleted
that authority (``acquire``/``steal``/the by-session index); a residual lock record is now
legacy/diagnostic noise, not a security-relevant divergence, and its stale-reclaim WARN
rung exactly duplicated ``LOCK-GC`` (``features/spec_context/doctor.py``). Retiring the
check (rather than leaving a no-op standing) also retires its sole reason to hold a
``spec_context`` cross-feature import edge — this module is leaf-only now, importing only
the shared leaves + core (R-1 cap invariant preserved without needing a seam at all).
"""

from __future__ import annotations

import re
from pathlib import Path

from dadaia_workspace.features.specs.doctor_types import Severity, SpecsDoctorIssue

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

# SPEC-DOC-037 (v0.1.47 W1-9 / WS-E): the constitution must not re-encode a mutable
# runtime-kind roster. It states the runtime-kind invariant and cites ``[[tech-stack]]`` as
# the roster single-source. Any standalone ``AgentRuntimeKind`` member token (the distinctive
# ALL-CAPS enum identifiers) enumerated in ``specs/constitution.md`` is an ERROR — this is the
# recurrence guard behind the v0.1.47 constitution rewrite. The tokens are word-bounded and
# uppercase, so lowercase English prose ("fake") never matches; ``{claude, codex, pi}`` (the
# Layer model set W2 keeps) is deliberately NOT matched — only runtime-kind ENUM members are.
_CONSTITUTION_RUNTIME_KIND_RE = re.compile(
    r"\b(FAKE|CODEX_EXEC|CLAUDE_SDK|PI_HEADLESS|OPENCODE_RUN)\b"
)

# SPEC-DOC-028: path-like backtick references in constitution.md.
_CONSTITUTION_REF_RE = re.compile(
    r"`([A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:py|md|sh|json|toml|txt|cfg|yml|yaml))`"
)


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


class CoherenceValidator:
    """Constitution, orchestration-registry, and pattern-version coherence."""

    def __init__(
        self,
        specs_dir: Path,
        public_dir: Path | None = None,
        repo_root: Path | None = None,
    ) -> None:
        self.specs_dir = specs_dir
        self.public_dir = public_dir
        self.repo_root = repo_root

    def check_constitution(self) -> list[SpecsDoctorIssue]:
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

    def check_orchestration_registry(self) -> list[SpecsDoctorIssue]:
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

    def check_specs_pattern_version(self) -> list[SpecsDoctorIssue]:
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

    def check_constitution_file_refs(self) -> list[SpecsDoctorIssue]:
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
        for m in _CONSTITUTION_REF_RE.finditer(text):
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

    def check_constitution_no_runtime_enum(self) -> list[SpecsDoctorIssue]:
        """SPEC-DOC-037 (v0.1.47 W1-9 / WS-E): constitution must not enumerate runtime kinds.

        The constitution states the runtime-kind INVARIANT and cites ``[[tech-stack]]`` (the
        roster single-source) instead of re-encoding a mutable ``AgentRuntimeKind`` roster.
        Any standalone enum-member token (FAKE / CODEX_EXEC / CLAUDE_SDK / PI_HEADLESS /
        OPENCODE_RUN, matched word-bounded + uppercase per :data:`_CONSTITUTION_RUNTIME_KIND_RE`)
        in ``specs/constitution.md`` is an ERROR — the recurrence guard behind the constitution
        rewrite. The Layer model set ``{claude, codex, pi}`` is not a runtime-kind enumeration
        and is deliberately not matched. Absent constitution → no-op (SPEC-DOC-001 owns that).
        """
        path = self.specs_dir / "constitution.md"
        if not path.exists():
            return []
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return []
        found = sorted({m.group(1) for m in _CONSTITUTION_RUNTIME_KIND_RE.finditer(text)})
        if not found:
            return []
        tokens = ", ".join(found)
        return [
            SpecsDoctorIssue(
                code="SPEC-DOC-037",
                severity=Severity.ERROR,
                description=(
                    f"constitution.md enumerates AgentRuntimeKind member/harness-roster "
                    f"token(s) ({tokens}). The constitution must state the runtime-kind "
                    "invariant and cite [[tech-stack]] as the roster single-source, never "
                    "enumerate concrete runtime kinds (SPEC-DOC-037, ERROR)."
                ),
                path=str(path),
            )
        ]
