"""The origin rerun fix is spelled over its words: a blank in the path stays one word."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from dadaia_workspace.core.skill_owner import load_owner
from tests.helpers.oslib import command

_EXIT = load_owner("dd-backlog-definition", "_backlog_exit")


def test_the_origin_rerun_fix_quotes_a_path_with_a_blank(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        _EXIT, "run", lambda argv, **_: subprocess.CompletedProcess(argv, 1, "", "")
    )
    spec = tmp_path / "a b" / "SPEC.md"
    with pytest.raises(_EXIT.Refusal) as refused:
        _EXIT._origin_ids(spec)
    assert refused.value.fix == command(sys.executable, str(_EXIT._RELEASE), "origin", str(spec))
