"""The packaged baseline has one strict parser: a pattern that cannot load is a refusal, never a dropped row."""

from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path
from types import ModuleType

import pytest

from dadaia_workspace.core.cli_line import shell_line
from dadaia_workspace.core.skill_owner import load_owner
from tests.helpers.oslib import write_text

_SOURCE = Path(load_owner("dd-bug-resolution", "_privacy").__file__ or "")

_GOOD = {"id": "ok", "regex": "abc"}
_FALLBACK = "Agent action: run `uvx dadaia-workspace init` with the workspace's directory as its first argument"


def _baseline_at(tmp_path: Path, text: str | bytes) -> ModuleType:
    shutil.copy(_SOURCE, tmp_path / "_privacy.py")
    (tmp_path / "privacy_baseline.json").write_bytes(
        text if isinstance(text, bytes) else text.encode("utf-8")
    )
    spec = importlib.util.spec_from_file_location("_privacy_probe", tmp_path / "_privacy.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("text", "named"),
    [
        ("{not json", "privacy_baseline.json"),
        (json.dumps({"patterns": [_GOOD, "oops"]}), "row 2"),
        (json.dumps({"patterns": [_GOOD, {"id": "broken", "regex": "("}]}), "row 2 (broken)"),
        (json.dumps({"patterns": [{"id": "x", "regex": "a", "exclude_regex": "("}]}), "row 1 (x)"),
    ],
    ids=["bad-json", "non-object-row", "bad-regex", "bad-exclude"],
)
def test_a_malformed_baseline_refuses_naming_the_row_with_one_fix(
    tmp_path: Path, text: str, named: str
) -> None:
    module = _baseline_at(tmp_path, text)
    with pytest.raises(load_owner("dd-bug-resolution", "_refusal").Refusal) as caught:
        module.load_baseline()
    assert named in str(caught.value)
    assert caught.value.fix == _FALLBACK


def test_a_wellformed_baseline_loads_every_row(tmp_path: Path) -> None:
    module = _baseline_at(tmp_path, json.dumps({"patterns": [_GOOD]}))
    assert [p.id for p in module.load_baseline()] == ["ok"]


def test_a_baseline_that_is_not_utf8_is_reinstalled_not_restored_from_git(tmp_path: Path) -> None:
    module = _baseline_at(tmp_path, b"\xff\xfe")
    with pytest.raises(load_owner("dd-bug-resolution", "_refusal").Refusal) as caught:
        module.load_baseline()
    assert "no pattern was applied" in str(caught.value)
    assert caught.value.fix == _FALLBACK


def test_a_baseline_inside_a_workspace_is_reinstalled_by_init_of_that_workspace(
    tmp_path: Path,
) -> None:
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    write_text(tmp_path / ".dadaia" / "states" / "spec_contexts.json", "{}")
    inside = tmp_path / ".agents" / "skills" / "dd-bug-resolution" / "scripts"
    inside.mkdir(parents=True)
    module = _baseline_at(inside, b"\xff\xfe")
    with pytest.raises(load_owner("dd-bug-resolution", "_refusal").Refusal) as caught:
        module.load_baseline()
    assert caught.value.fix == shell_line(
        "uvx", "dadaia-workspace", "init", str(tmp_path.resolve())
    )
