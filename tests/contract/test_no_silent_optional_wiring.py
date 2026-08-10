"""No-silent-optional-wiring guard — v0.3.0 successor.

The original guard pinned the lifecycle-engine builders (every optional collaborator of
the four workflow bodies had to be wired by the container or the body silently degraded).
The engine died in v0.3.0, but the MECHANISM it guarded against survives wherever the
composition root passes optional collaborators: ``build_panel_service`` accepts
``report_retention=None`` / ``adapter_registry=None`` / ``agents_provider=None`` and the
``PanelService`` degrades (503s / RuntimeError / no enrichment) when they are absent.

This contract pins: the container's ``build_panel_service`` ALWAYS wires the silently
degrading collaborators — a refactor that drops one of those kwargs must fail here, not
in production.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace import container

pytestmark = pytest.mark.contract


def test_build_panel_service_wires_every_silently_degrading_collaborator(
    tmp_path: Path,
) -> None:
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text(json.dumps({"version": "1", "contexts": []}))
    svc = container.build_panel_service(tmp_path)

    # ReportRetentionService: absent -> get_report_retention() raises RuntimeError.
    assert svc.get_report_retention() is not None

    # Adapter registry: absent -> get_session_adapter() always None (no enrichment).
    assert svc.get_session_adapter("claude") is not None

    # AgentsProvider: absent -> list_canonical_agents() raises RuntimeError.
    assert svc._agents() is not None
