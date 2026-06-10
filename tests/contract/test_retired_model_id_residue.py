"""Retired model-id residue contract (WS-R8 / AC-R8-04, release v0.1.10).

T-010-23 consolidated model identity into the single ``core/model_registry.py`` registry
and, in doing so, **dropped** model ids that had drifted or were superseded — most notably
the standalone ``claude-haiku-3-5`` pricing key, which never had a ``MODEL_MAP`` entry and
was the haiku-tier desync documented in bug
``model-catalog-modelmap-pricing-drift-no-registry``. Once an id is retired it must not
resurface as a *live* model assignment (agent frontmatter, MODEL_MAP/PRICING_TABLE data, or
runtime resolution code) — that would silently re-open the drift the registry closed.

This contract greps ``dadaia_workspace/`` for each retired id and fails on any occurrence,
with **one principled exclusion**: ``core/model_registry.py`` itself. The registry's module
docstring legitimately names the dropped ids to *explain the lineage* of the drift it fixed
(why ``claude-haiku-3-5`` was dropped and where its historical pricing now lives under
``claude-haiku-4-5-20251001``). That historical narrative is the canonical home for the
dead names; everywhere else, a retired id is residue.

If a future change genuinely needs to re-introduce a historical id (e.g. to cost very old
telemetry), it does so by appending a dated pricing row under a *current* registry entry —
never by reviving the bare retired key as an active assignment.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CODE_ROOT = _REPO_ROOT / "dadaia_workspace"
# The registry's own docstring is the sanctioned home for retired-id lineage.
_REGISTRY_REL = "core/model_registry.py"

# Model ids retired by T-010-23's registry consolidation. ``claude-haiku-3-5`` is the
# dropped standalone pricing key (had no MODEL_MAP entry; the drift in
# model-catalog-modelmap-pricing-drift-no-registry). Add an id here when a future release
# retires one — and the grep then keeps it from resurfacing as a live assignment.
RETIRED_MODEL_IDS = ("claude-haiku-3-5",)


def _scanned_sources() -> list[Path]:
    files: list[Path] = []
    for path in sorted(_CODE_ROOT.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        if path.relative_to(_REPO_ROOT).as_posix().endswith(_REGISTRY_REL):
            continue  # registry docstring owns the retired-id lineage
        files.append(path)
    return files


def test_retired_model_ids_absent_from_live_code() -> None:
    """No retired model id appears in shippable code outside the registry's lineage docstring."""
    offenders: list[str] = []
    for src in _scanned_sources():
        rel = src.relative_to(_REPO_ROOT).as_posix()
        for lineno, line in enumerate(src.read_text(encoding="utf-8").splitlines(), 1):
            for retired in RETIRED_MODEL_IDS:
                if retired in line:
                    offenders.append(f"{rel}:{lineno}: {line.strip()}")
    assert not offenders, (
        "retired model id(s) resurfaced as live assignments (re-opens the registry drift "
        "closed by T-010-23):\n" + "\n".join(offenders)
    )


def test_retired_ids_do_not_resolve_in_the_registry() -> None:
    """A retired id must not be reachable through the registry index (real behavior check)."""
    from dadaia_workspace.core.model_registry import registry_by_claude_id

    index = registry_by_claude_id()
    leaked = [mid for mid in RETIRED_MODEL_IDS if mid in index]
    assert not leaked, f"retired model id(s) resolve in the registry index: {leaked}"
