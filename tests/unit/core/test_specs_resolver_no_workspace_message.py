"""Outside a workspace, say so — do not blame the context name.

Bug ``r12-bugs-append-rejects-context-name`` (consumer-side validator, R12): running
``dadaia bugs append --context <name>`` from outside any workspace failed with "Could not
resolve specs_dir", and the validator read it — reasonably — as "the registered context
is rejected". The context name was never the problem: the registry that resolves it lives
inside a workspace, and there was no workspace to look in.

A wrong diagnosis costs more than a bare failure: it sends the reader to fix the thing
that was already correct.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import typer

from dadaia_workspace.core.specs_resolver import resolve_specs_dir

pytestmark = pytest.mark.unit


def test_outside_a_workspace_the_error_names_the_missing_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outside = tmp_path / "not-a-workspace"
    outside.mkdir()
    monkeypatch.chdir(outside)

    with pytest.raises(typer.BadParameter) as excinfo:
        resolve_specs_dir(specs_dir=None)

    message = str(excinfo.value)
    assert "No dadaia workspace was found" in message, message
    assert "context registry lives inside a workspace" in message, message
    assert "--specs-dir" in message, "the reader still needs the escape hatch"
