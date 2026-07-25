"""``release-definition`` accepts an operator demand — the channel back into a rejection.

Bug release-definition-has-no-demand-channel-for-review-corrections. ``backlog-definition``
has had ``--demand`` since bug backlog-define-has-no-demand-input-channel;
``release-definition`` did not, so when a reviewer REJECTED a SPEC, PLAN or TASKS the
operator's only channel into the next attempt was the engine's own rejection digest. They
could not supply the decision the reviewer asked for — only re-roll the same dice, at
minutes of live worker time per cycle.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration


def test_the_cli_exposes_demand() -> None:
    from typer.testing import CliRunner

    from dadaia_workspace.cli.main import app

    out = CliRunner().invoke(app, ["lifecycle", "release-definition", "--help"]).output
    assert "--demand" in out, "release-definition must expose the operator demand channel"


def test_the_demand_reaches_every_model_step_prompt() -> None:
    """Injected as an '## Operator demand' block, exactly as backlog-definition does."""
    from dadaia_workspace.features.lifecycle.workflows import _fragment_gate

    src = _fragment_gate.__file__
    with open(src, encoding="utf-8") as fh:
        body = fh.read()
    assert "_operator_demand" in body, (
        "the shared fragment gate must inject the operator demand, or only "
        "backlog-definition would carry it"
    )
    assert "## Operator demand" in body


def test_the_release_workflow_accepts_it() -> None:
    import inspect

    from dadaia_workspace.features.lifecycle.workflows.release_definition import (
        ReleaseDefinitionWorkflow,
    )

    params = inspect.signature(ReleaseDefinitionWorkflow.run).parameters
    assert "operator_demand" in params, params.keys()
