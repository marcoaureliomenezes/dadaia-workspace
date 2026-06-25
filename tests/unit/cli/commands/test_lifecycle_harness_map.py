"""Unit tests for the lifecycle CLI harness map and resolution.

`_HARNESS_KINDS` + `_resolve_harness` are the single seam that turns a
`--harness <name>` / `--step-harness <label>=<name>` token into an
`AgentRuntimeKind`. Adding a harness must require only a map entry — no change to
`phase_workflow.py` / `pipeline.py`.
"""

from __future__ import annotations

import pytest
import typer

from dadaia_workspace.cli.commands.lifecycle import _HARNESS_KINDS, _resolve_harness
from dadaia_workspace.core.models.lifecycle import AgentRuntimeKind


def test_harness_map_includes_pi() -> None:
    assert _HARNESS_KINDS["pi"] is AgentRuntimeKind.PI_HEADLESS


def test_harness_map_covers_all_runtime_kinds() -> None:
    # Every selectable runtime kind has a CLI label (FAKE is also wired for tests).
    assert set(_HARNESS_KINDS.values()) == set(AgentRuntimeKind)


def test_resolve_harness_pi() -> None:
    assert _resolve_harness("pi") is AgentRuntimeKind.PI_HEADLESS
    assert _resolve_harness("PI") is AgentRuntimeKind.PI_HEADLESS


def test_resolve_harness_unknown_raises_bad_parameter() -> None:
    with pytest.raises(typer.BadParameter):
        _resolve_harness("nope")
