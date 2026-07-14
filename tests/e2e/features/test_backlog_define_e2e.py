"""E2E for ``dadaia lifecycle backlog define`` — the REAL workflow, end-to-end (T-26-08).

Drives the published CLI surface against a fully-initialised workspace (real
``WorkspaceService.init`` + real public-asset install, so the actual
``backlog_definition/*.md`` fragments are on disk and loaded by the fragment-driven
workflow). The assertion proves the verb runs the real :class:`BacklogDefinitionWorkflow`
— the §4 seven-step sequence with real fragment ids — and exits cleanly, NOT the
``_deferred`` fail-loud stub it previously routed to.

In-process via ``CliRunner`` (the ``test_public_pipeline`` e2e pattern): a subprocess
would escape the conftest no-real-venv monkeypatch and build a real venv into ``tmp_path``
(disk hazard). The full real CLI app + real container + real fragments is exercised.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

pytestmark = pytest.mark.e2e

_runner = CliRunner()

# The §4 seven-step sequence — proof the verb ran the real workflow, not _deferred.
_EXPECTED_SEQUENCE = [
    "intake_grill",
    "subject_bind",
    "existing_backlog_review",
    "reconcile_decision",
    "conflict_resolution_grill",
    "backlog_author",
    "backlog_review_gate",
]


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A real, fully-installed workspace (fragments staged + projected on disk)."""
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(tmp_path)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_backlog_define_runs_the_real_workflow_and_exits_clean(workspace: Path) -> None:
    # The fragment-driven workflow loads its fragments from the packaged source root
    # (``dadaia_workspace/public/lifecycle_fragments/``) — the loader fails on a missing
    # fragment id, so a successful clean run is itself proof the real fragments are present.
    from dadaia_workspace.features.lifecycle.fragments.loader import FragmentLoader

    fragment_root = FragmentLoader().root / "backlog_definition"
    assert (fragment_root / "intake_grill.md").exists(), (
        f"backlog_definition fragments missing from package source: "
        f"{sorted(fragment_root.glob('*')) if fragment_root.exists() else 'dir missing'}"
    )

    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "backlog-definition",
            "--harness",
            "fake",
            "--release-id",
            "v0.1.26",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output

    payload = json.loads(result.output)
    assert payload["status"] == "OK", payload
    assert payload["completed"] is True, payload
    # The real workflow runs the §4 sequence in order — the _deferred stub would have
    # raised NotImplementedError and never produced a step list.
    labels = [step["label"] for step in payload["steps"]]
    assert labels == _EXPECTED_SEQUENCE, labels
    # Model steps carry their real fragment id (not a generic "Run the step" prompt).
    intake = next(s for s in payload["steps"] if s["label"] == "intake_grill")
    assert intake["fragment_id"] == "backlog_definition.intake_grill", intake


def test_backlog_define_rejects_claude_harness_law1(workspace: Path) -> None:
    result = _runner.invoke(
        app,
        ["lifecycle", "backlog-definition", "--release-id", "v0.1.26", "--harness", "claude"],
    )
    assert result.exit_code != 0
    assert "Layer-2 workflow harness" in result.output or "LAW 1" in result.output
