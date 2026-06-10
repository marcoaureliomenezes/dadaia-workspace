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
(``MODEL_MAP``/``PRICING_TABLE`` are re-exported from their owning modules). No
import-linter contract forbids ``features -> core``; ``core`` is the bottom layer.
The check does not import ``infrastructure``.

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
from dadaia_workspace.features.telemetry.pricing import PRICING_TABLE
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
    model_map_keys = set(MODEL_MAP)
    pricing_keys = set(PRICING_TABLE)
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
