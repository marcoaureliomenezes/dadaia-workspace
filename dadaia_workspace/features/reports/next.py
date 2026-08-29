"""Reports-next feature service — discovers the next expected agent handoff.

Infra-free per the constitution (L67): this module imports only ``core/`` and the
Python standard library. It resolves the active release by reading the live release
directory's ``RELEASE.json`` mutable state document (v0.5.x, successor to the
RELEASE.jsonl fold; v0.5.0 FR4/T-050-21A, A4.1 — ``ACTIVE.md`` is retired, no file
replaces it), reads that release's ``PLAN.md``, and the ``.dadaia/handoff/`` tree via
``core.handoff_index.scan_handoffs`` — the one discovery primitive every handoff reader
now shares (release 0.5.1 K6).

Wiring (which context/specs_dir/reports_root to use) is resolved in
``dadaia_workspace.container.build_reports_next_service`` — never here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from dadaia_workspace.core.exceptions import NoActiveReleaseError, NoAgentSequenceError
from dadaia_workspace.core.handoff_index import scan_handoffs
from dadaia_workspace.core.release_state import parse_release_state

#: Canonical 9-agent core topology. Owner names parsed from
#: PLAN.md are filtered to this set so prose like ``owner: TBD`` never enters a sequence.
#: Source of truth: .dadaia/agentic/agents.index.json (updated v0.1.7).
CANONICAL_AGENTS: frozenset[str] = frozenset(
    {
        "ai-engineer",
        "code-reviewer",
        "product-engineer",
        "project-auditor",
        "project-manager",
        "qa-engineer",
        "security-reviewer",
        "software-architect",
        "software-engineer",
    }
)

# Owner declaration forms (FR-RN-1 contract), scanned in document order via finditer:
#   (owner: <agent>)   |   **Owner:** <agent>   |   owner: <agent>   (YAML inline)
_OWNER_RE = re.compile(
    r"\(owner:\s*([a-z][a-z0-9-]+)\)"
    r"|\*\*owner:\*\*\s*([a-z][a-z0-9-]+)"
    r"|(?:^|\s)owner:\s*([a-z][a-z0-9-]+)",
    re.IGNORECASE | re.MULTILINE,
)

_NO_SEQUENCE_MSG = (
    "No agent sequence found in PLAN.md. Ensure PLAN.md declares owners using "
    "(owner: <agent>) pattern."
)


@dataclass
class ReportsNextResult:
    """Outcome of resolving the next expected agent for the active release."""

    next_agent: str | None
    release_id: str
    completed_agents: list[str] = field(default_factory=list)
    pending_agents: list[str] = field(default_factory=list)


class ReportsNextService:
    """Resolves the next agent that has not yet emitted a handoff for the active release.

    Args:
        specs_dir: Absolute path to the active context's ``specs/`` directory.
        reports_root: Root of the handoff tree (``<workspace>/.dadaia/handoff``).
        context_name: Context directory under ``reports_root`` (the repo slug).
    """

    def __init__(self, specs_dir: Path, reports_root: Path, context_name: str) -> None:
        self._specs_dir = specs_dir
        self._reports_root = reports_root
        self._context = context_name

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve_next(self) -> ReportsNextResult:
        """Return the next expected agent (or ``None`` if all have emitted handoffs).

        Raises:
            NoActiveReleaseError: no live release directory carries a ``RELEASE.json``.
            NoAgentSequenceError: PLAN.md missing or declares no recognizable owners.
        """
        release_id = self._active_release()
        sequence = self._agent_sequence(self._specs_dir / "releases" / release_id / "PLAN.md")
        completed: list[str] = []
        pending: list[str] = []
        for agent in sequence:
            (completed if self._has_handoff(agent, release_id) else pending).append(agent)
        return ReportsNextResult(
            next_agent=pending[0] if pending else None,
            release_id=release_id,
            completed_agents=completed,
            pending_agents=pending,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _active_release(self) -> str:
        """Resolve the live release id (v0.5.x, successor to the RELEASE.jsonl fold;
        v0.5.0 FR4/T-050-21A, A4.1): the ONE directory directly under ``releases/`` —
        excluding ``_archive``/``_ideas`` (A4.6) — that carries a ``RELEASE.json``. No
        file replaces ``ACTIVE.md``; this directory scan is the sole successor of its
        ``release:`` field."""
        releases_root = self._specs_dir / "releases"
        candidates: list[str] = []
        if releases_root.is_dir():
            candidates = sorted(
                d.name
                for d in releases_root.iterdir()
                if d.is_dir()
                and d.name not in ("_archive", "_ideas")
                and (d / "RELEASE.json").is_file()
            )
        if not candidates:
            raise NoActiveReleaseError(
                "No active release: no directory under releases/ carries a "
                "RELEASE.json under the active context. Run "
                "`eval $(dadaia context bind <name> --mode read)` and open a release."
            )
        if len(candidates) > 1:
            raise NoActiveReleaseError(
                "No active release: multiple live release directories carry a "
                f"RELEASE.json ({', '.join(candidates)}) — ambiguous, refusing to guess."
            )
        release_id = candidates[0]
        json_path = releases_root / release_id / "RELEASE.json"
        try:
            state = parse_release_state(json_path.read_text(encoding="utf-8"))
        except ValueError as exc:
            raise NoActiveReleaseError(
                f"No active release: {release_id}/RELEASE.json failed to parse: {exc}"
            ) from exc
        if not state.phase:
            raise NoActiveReleaseError(
                f"No active release: {release_id}/RELEASE.json carries no 'phase' value."
            )
        return release_id

    def _agent_sequence(self, plan_path: Path) -> list[str]:
        if not plan_path.is_file():
            raise NoAgentSequenceError(_NO_SEQUENCE_MSG)
        text = plan_path.read_text(encoding="utf-8")
        seen: set[str] = set()
        sequence: list[str] = []
        for m in _OWNER_RE.finditer(text):
            name = (m.group(1) or m.group(2) or m.group(3) or "").lower()
            if name in CANONICAL_AGENTS and name not in seen:
                seen.add(name)
                sequence.append(name)
        if not sequence:
            raise NoAgentSequenceError(_NO_SEQUENCE_MSG)
        return sequence

    def _has_handoff(self, agent: str, release_id: str) -> bool:
        context_dir = self._reports_root / self._context
        for handoff in scan_handoffs(context_dir):
            if handoff.release_id == release_id and handoff.agent == agent:
                return True
        return False
