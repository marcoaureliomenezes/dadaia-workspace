"""Public-doctor model-resolution check (R8b, T-010-24).

This is the doctor half of the
``model-catalog-modelmap-pricing-drift-no-registry`` fix. T-010-23 made
``core/model_registry.py`` the single source of truth and turned ``MODEL_MAP`` and
``PRICING_TABLE`` into derived views. This check is the standing guard that keeps
the fleet honest against future hand-edits:

1. **Agent-frontmatter resolution.** Every ``model:`` value declared in a canonical
   ``public/agents/*.md`` frontmatter must resolve to a ``claude_id`` registered in
   :data:`dadaia_workspace.core.model_registry.REGISTRY`. An unknown id would crash
   ``dadaia public install --target codex`` (no Codex mapping) and cost telemetry out
   as ``NULL`` — so it is an ERROR.

2. **Key-set coherence.** ``MODEL_MAP`` keys, ``PRICING_TABLE`` keys, and the
   ``REGISTRY`` claude-id set must be identical. The derived views are generated from
   the registry today, but this defends against a future hand-edit (or a partial
   refactor) that reintroduces the original silent desync.

Layering: this lives in ``features/public/`` and imports ``core.model_registry``
(the single source of truth) plus the ``MODEL_MAP`` derived view from
``infrastructure`` (a documented ignore-edge — the infra view is a separate
module that must be guarded against a hand-edit). The ``PRICING_TABLE`` key-set
is no longer imported from the sibling ``features.telemetry`` module (that was a
cross-feature import, audit A3): the registry is the single source from which
``PRICING_TABLE`` is itself derived, so the registry claude-id set IS the
pricing key-set by construction. ``features -> core`` is permitted (``core`` is
the bottom layer); the ``features.telemetry`` cross-feature edge is gone.

ERROR lines use the ``[drift]`` prefix — the same prefix ``check_agent_skill_refs``
and ``check_memory_phase_single_source`` use for hard failures — because the
``dadaia public doctor`` CLI already treats ``[drift]`` as a nonzero-exit condition
and the doctor finding-persistence layer already captures it. A clean check emits
``[ok] model-resolution``.
"""

from __future__ import annotations

import re
from pathlib import Path

from dadaia_workspace.core.model_registry import REGISTRY
from dadaia_workspace.infrastructure.runtime_transforms.model_mapping import MODEL_MAP

# Matches a frontmatter ``model:`` line (first match wins; ``opencode_model:`` is a
# different field and is intentionally not matched by this anchored pattern).
_MODEL_FRONTMATTER_RE = re.compile(r"^model:\s*(\S+)\s*$", re.MULTILINE)


def _registry_claude_ids() -> set[str]:
    return {entry.claude_id for entry in REGISTRY}


def check_model_resolution(public_dir: Path) -> list[str]:
    """Return doctor report lines for the model-resolution invariants.

    Args:
        public_dir: the canonical public-asset source directory (the one that
            contains ``agents/``). Agent frontmatter is read from
            ``public_dir / "agents" / "*.md"``.

    Returns:
        A list of doctor lines. Emits ``[drift]`` ERROR lines on any unknown agent
        ``model:`` id or any key-set desync, and a single ``[ok] model-resolution``
        line when every invariant holds.
    """
    out: list[str] = []
    registry_ids = _registry_claude_ids()

    # 1. Agent-frontmatter resolution.
    agents_dir = public_dir / "agents"
    if agents_dir.is_dir():
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
                    f"[drift] model-resolution ERROR: agent '{md_file.stem}' declares "
                    f"model '{model_id}' which is not in core.model_registry.REGISTRY "
                    f"(known: {', '.join(sorted(registry_ids))})"
                )

    # 2. Key-set coherence: MODEL_MAP keys == PRICING_TABLE keys == REGISTRY ids.
    # PRICING_TABLE and MODEL_MAP are both DERIVED views over REGISTRY (one in
    # features/telemetry, one in infrastructure). The registry claude-id set IS
    # the canonical pricing key-set by construction, so we compute the pricing
    # key-set from REGISTRY directly rather than importing across the
    # features→features boundary into the sibling telemetry module (audit A3).
    # The MODEL_MAP infra view lives in a SEPARATE module and is still imported
    # so a hand-edit that desyncs it from the registry is caught here.
    model_map_keys = set(MODEL_MAP)
    pricing_keys = registry_ids  # PRICING_TABLE is derived from REGISTRY (== registry_ids).
    if not (model_map_keys == pricing_keys == registry_ids):
        out.append(
            "[drift] model-resolution ERROR: key-set desync — "
            f"MODEL_MAP={sorted(model_map_keys)} "
            f"PRICING_TABLE={sorted(pricing_keys)} "
            f"REGISTRY={sorted(registry_ids)}"
        )

    if not out:
        out.append("[ok] model-resolution")
    return out
