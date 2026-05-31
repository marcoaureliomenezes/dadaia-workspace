"""Reports-next feature service — discovers the next expected agent handoff.

Infra-free per the constitution (L67): this module imports only ``core/`` and the
Python standard library. It reads ``releases/ACTIVE.md``, the active release's
``PLAN.md``, and the ``.dadaia/reports/`` tree via :mod:`pathlib`, mirroring the
stdlib file access already used by ``ReportsValidationService``.

Wiring (which context/specs_dir/reports_root to use) is resolved in
``dadaia_workspace.container.build_reports_next_service`` — never here.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from dadaia_workspace.core.exceptions import NoActiveReleaseError, NoAgentSequenceError

#: Canonical 21-agent topology (data-architect is the 21st). Owner names parsed from
#: PLAN.md are filtered to this set so prose like ``owner: TBD`` never enters a sequence.
CANONICAL_AGENTS: frozenset[str] = frozenset(
    {
        "ai-engineer",
        "backend-engineer",
        "code-reviewer",
        "data-analyst",
        "data-architect",
        "data-engineer",
        "design-specialist",
        "devops-engineer",
        "frontend-engineer",
        "game-designer",
        "game-developer",
        "game-tester",
        "product-engineer",
        "project-auditor",
        "project-manager",
        "qa-engineer",
        "researcher",
        "security-reviewer",
        "software-architect",
        "software-engineer-node",
        "software-engineer-python",
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

_RELEASE_RE = re.compile(r"^release:\s*(.+?)\s*$", re.MULTILINE)

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
        reports_root: Root of the reports tree (``<workspace>/.dadaia/reports``).
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
            NoActiveReleaseError: ACTIVE.md missing or ``release: none``.
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
        active_path = self._specs_dir / "releases" / "ACTIVE.md"
        if not active_path.is_file():
            raise NoActiveReleaseError(
                "No active release: releases/ACTIVE.md not found under the active context. "
                "Run `dadaia context activate <name>` and open a release."
            )
        m = _RELEASE_RE.search(active_path.read_text(encoding="utf-8"))
        release = m.group(1).strip() if m else ""
        if not release or release.lower() == "none":
            raise NoActiveReleaseError(
                "No active release (releases/ACTIVE.md has `release: none`). "
                "Open a release before running `dadaia reports next`."
            )
        return release

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
        agent_dir = self._reports_root / self._context / agent
        if not agent_dir.is_dir():
            return False
        for path in sorted(agent_dir.rglob("*.handoff.json")):
            try:
                doc = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if isinstance(doc, dict) and doc.get("release_id") == release_id:
                return True
        return False
