"""Public-doctor model-resolution check (R8b, T-010-24).

The doctor half of ``model-catalog-modelmap-pricing-drift-no-registry``:
``core/model_registry.py`` is the single source of truth.

1. **Agent-frontmatter resolution.** Every ``model:`` value declared in a canonical
   ``public/agents/*.md`` frontmatter must resolve to a ``claude_id`` registered in
   :data:`dadaia_workspace.core.model_registry.REGISTRY`. An unknown id would crash
   ``dadaia harness add codex`` (no Codex mapping) — so it is an ERROR.

Layering: ``features -> core`` only.

ERROR lines use the ``[drift]`` prefix — the same prefix ``check_agent_skill_refs``
uses for hard failures — because the
``dadaia public doctor`` CLI already treats ``[drift]`` as a nonzero-exit condition
and the doctor finding-persistence layer already captures it. A clean check emits
``[ok] model-resolution``.
"""

from __future__ import annotations

import re
from pathlib import Path

from dadaia_workspace.core.model_registry import (
    CLAUDE_EFFORTS,
    CORE_AGENTS,
    REGISTRY,
    AgentModelPolicyOverlay,
    resolve_agent_model,
)
from dadaia_workspace.core.models.doctor_report import DoctorLine, DoctorStatus

# Matches a frontmatter ``model:`` line (first match wins).
_MODEL_FRONTMATTER_RE = re.compile(r"^model:\s*(\S+)\s*$", re.MULTILINE)


def _registry_claude_ids() -> set[str]:
    return {entry.claude_id for entry in REGISTRY}


def _scan_frontmatter_models(
    agents_dir: Path, registry_ids: set[str], out: list[DoctorLine]
) -> None:
    """Append an ERROR line for every authored ``model:`` not resolving in REGISTRY."""
    if not agents_dir.is_dir():
        return
    for md_file in sorted(agents_dir.glob("*.md")):
        try:
            text = md_file.read_text(encoding="utf-8")
        except OSError:
            continue
        match = _MODEL_FRONTMATTER_RE.search(text)
        if match is None:
            continue
        model_id = match.group(1)
        if model_id not in registry_ids:
            out.append(
                DoctorLine(
                    DoctorStatus.DRIFT,
                    f"model-resolution ERROR: agent '{md_file.stem}' declares "
                    f"model '{model_id}' which is not in core.model_registry.REGISTRY "
                    f"(known: {', '.join(sorted(registry_ids))})",
                )
            )


def check_model_resolution(
    public_dir: Path, overlay: AgentModelPolicyOverlay | None = None
) -> list[DoctorLine]:
    """Return doctor report lines for the model-resolution invariants.

    Args:
        public_dir: the canonical public-asset source directory. Agent
            frontmatter is read from ``public_dir / "agents" / "*.md"``.
        overlay: the loaded agent-model-policy overlay (v0.1.65 FR7) — ``None``
            when absent/invalid (an invalid overlay is reported as a doctor ERROR
            by the asset manager, not here). The RESOLVED (model, effort) per core
            agent is validated against REGISTRY + the effort vocabulary.

    Returns:
        A list of doctor lines. Emits ``[drift]`` ERROR lines on any unknown agent
        ``model:`` id or an unresolvable core-agent policy resolution, and a single ``[ok] model-resolution`` line when every invariant
        holds.
    """
    out: list[DoctorLine] = []
    registry_ids = _registry_claude_ids()

    # 1a. Authored-frontmatter resolution (staged core bodies are model-agnostic
    # since FR1 — the regex simply finds nothing there).
    _scan_frontmatter_models(public_dir / "agents", registry_ids, out)

    # 1b. RESOLVED-roster validation (v0.1.65 FR7): the resolver's answer for each
    # core agent — templates assert at import; a present overlay layers on top —
    # must land on a registry model and a vocabulary effort.
    for agent in CORE_AGENTS:
        resolved = resolve_agent_model(agent, overlay)
        if resolved.model not in registry_ids:
            out.append(
                DoctorLine(
                    DoctorStatus.DRIFT,
                    f"model-resolution ERROR: resolved policy for core agent "
                    f"'{agent}' yields model '{resolved.model}' which is not in "
                    f"core.model_registry.REGISTRY",
                )
            )
        if resolved.effort not in CLAUDE_EFFORTS:
            out.append(
                DoctorLine(
                    DoctorStatus.DRIFT,
                    f"model-resolution ERROR: resolved policy for core agent "
                    f"'{agent}' yields effort {resolved.effort!r} outside the vocabulary "
                    f"({', '.join(CLAUDE_EFFORTS)})",
                )
            )

    if not out:
        out.append(DoctorLine(DoctorStatus.OK, "model-resolution"))
    return out
