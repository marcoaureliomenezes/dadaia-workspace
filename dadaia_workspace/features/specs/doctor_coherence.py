"""Coherence validator (v0.1.55 FR1): constitution, orchestration registry, lease/session.

Single-responsibility sibling of the SpecsDoctor coordinator. Owns the cross-cutting coherence
checks: constitution presence (SPEC-DOC-001), the D-OC-1 orchestration-registry coherence,
pattern-version staleness (SPECS-VERSION), constitution file-refs (SPEC-DOC-028), the lease↔session
coherence backstop (SPEC-DOC-029), and the constitution runtime-enum guard (SPEC-DOC-037).

This module HOLDS the single ``spec_context.{lease, session_identity}`` cross-feature import edge
(moved off the coordinator) — the coordinator's ``pid_probe`` seam is typed against the
``doctor_types.PidProbe`` leaf instead, so the coordinator holds NO ``spec_context`` edge (R-1 cap
invariant). Leaf-only otherwise: imports the shared leaves + core, never a sibling validator.
"""

from __future__ import annotations

import re
from pathlib import Path

from dadaia_workspace.features.spec_context import lease, session_identity
from dadaia_workspace.features.specs.doctor_types import PidProbe, Severity, SpecsDoctorIssue

#: SPEC-DOC-029: a ``<ctx>.lock.json`` filename component must be a real context name
#: (same path-traversal allowlist lease/session_identity enforce — CWE-22/CWE-59).
_CTX_NAME_RE = re.compile(r"[A-Za-z0-9_-]+")

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


def _validate_ctx_name(ctx: str) -> str:
    if not _CTX_NAME_RE.fullmatch(ctx):
        raise ValueError(f"invalid context name {ctx!r}")
    return ctx


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
    """Constitution, orchestration-registry, pattern-version, and lease/session coherence."""

    def __init__(
        self,
        specs_dir: Path,
        public_dir: Path | None = None,
        repo_root: Path | None = None,
        workspace_state_dir: Path | None = None,
        pid_probe: PidProbe | None = None,
    ) -> None:
        self.specs_dir = specs_dir
        self.public_dir = public_dir
        self.repo_root = repo_root
        self.workspace_state_dir = workspace_state_dir
        self.pid_probe = pid_probe

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

    def check_lease_session_coherence(self) -> list[SpecsDoctorIssue]:
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
            # genuine incoherence worth flagging as possible forgery. Holder-
            # confirmation (v0.1.50 FR2): a live holder whose by-session index entry
            # names this ctx (same-CAS acquisition evidence) is the TRUE holder — a
            # drifted incumbent .ptr is then drift, never a forgery ERROR.
            holder = record.get("session_id") if isinstance(record, dict) else None
            lock_holder = str(holder) if holder else None
            holder_confirmed = bool(
                lock_holder and lease.session_holds(workspace_root, ctx, lock_holder)
            )
            message = session_identity.coherence(
                workspace_root, ctx, lock_holder=lock_holder, holder_confirmed=holder_confirmed
            )
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
