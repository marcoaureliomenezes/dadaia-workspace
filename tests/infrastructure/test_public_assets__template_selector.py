"""``install(template=X)`` is the only writer of ``applied_template`` and
projects X's cells in the same pass; an unknown id changes nothing; no ``template`` keeps
the saved one. Templates and cells come from ``TEMPLATES``/``CORE_AGENTS``, never literals.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.core.exceptions import PublicAssetError
from dadaia_workspace.core.model_registry import CORE_AGENTS, TEMPLATES, resolve_agent_model
from dadaia_workspace.infrastructure.json_agent_model_policy_store import JsonAgentModelPolicyStore
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from tests.helpers.harness_profile import register_all


def _other_template() -> str:
    """A template whose cells differ from the default's, so a projection change is visible."""
    default = {a: resolve_agent_model(a, None) for a in CORE_AGENTS}
    return next(
        t
        for t, cells in TEMPLATES.items()
        if any(
            (cells[a].model, cells[a].effort) != (default[a].model, default[a].effort)
            for a in CORE_AGENTS
        )
    )


def _frontmatter(ws: Path, agent: str) -> dict[str, str]:
    text = (ws / ".claude" / "agents" / f"{agent}.md").read_text(encoding="utf-8")
    pairs = (line.partition(":") for line in text.split("---\n", 2)[1].splitlines())
    return {k: v.strip() for k, _, v in pairs if not k.startswith(" ")}


def _projections(ws: Path) -> dict[str, bytes]:
    return {a: (ws / ".claude" / "agents" / f"{a}.md").read_bytes() for a in CORE_AGENTS}


def _installed(tmp_path: Path) -> tuple[FileSystemPublicAssetManager, Path]:
    ws = tmp_path / "ws"
    ws.mkdir()
    register_all(ws)
    mgr = FileSystemPublicAssetManager()
    mgr.install(ws)
    return mgr, ws


def test_template_is_saved_and_its_cells_projected(tmp_path: Path) -> None:
    mgr, ws = _installed(tmp_path)
    x = _other_template()

    mgr.install(ws, template=x)  # type: ignore[call-arg]

    assert JsonAgentModelPolicyStore(ws).load().applied_template == x  # type: ignore[union-attr]
    for agent in CORE_AGENTS:
        cell = TEMPLATES[x][agent]
        fm = _frontmatter(ws, agent)
        assert (fm["model"], fm["effort"]) == (cell.model, cell.effort)


def test_unknown_template_names_valid_ids_and_changes_nothing(tmp_path: Path) -> None:
    mgr, ws = _installed(tmp_path)
    mgr.install(ws, template=_other_template())  # type: ignore[call-arg]
    store = JsonAgentModelPolicyStore(ws)
    overlay_before, projections_before = store.path.read_bytes(), _projections(ws)

    with pytest.raises((ValueError, PublicAssetError)) as raised:
        mgr.install(ws, template="turbo-mode")  # type: ignore[call-arg]

    assert all(t in str(raised.value) for t in TEMPLATES)
    assert store.path.read_bytes() == overlay_before
    assert _projections(ws) == projections_before


def test_no_template_keeps_the_saved_one(tmp_path: Path) -> None:
    mgr, ws = _installed(tmp_path)
    x = _other_template()
    mgr.install(ws, template=x)  # type: ignore[call-arg]
    projections = _projections(ws)

    mgr.install(ws)

    assert JsonAgentModelPolicyStore(ws).load().applied_template == x  # type: ignore[union-attr]
    assert _projections(ws) == projections
