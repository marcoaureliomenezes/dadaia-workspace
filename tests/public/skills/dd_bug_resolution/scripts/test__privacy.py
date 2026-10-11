"""The packaged baseline has one strict parser: a pattern that cannot load is a refusal, never a dropped row."""

from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path
from types import ModuleType

import pytest

from dadaia_workspace.core.skill_owner import load_owner

_SOURCE = Path(load_owner("dd-bug-resolution", "_privacy").__file__ or "")

_GOOD = {"id": "ok", "regex": "abc"}


def _baseline_at(tmp_path: Path, text: str) -> ModuleType:
    shutil.copy(_SOURCE, tmp_path / "_privacy.py")
    (tmp_path / "privacy_baseline.json").write_text(text, encoding="utf-8")
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
    assert caught.value.fix.startswith("Operator action:")


def test_a_wellformed_baseline_loads_every_row(tmp_path: Path) -> None:
    module = _baseline_at(tmp_path, json.dumps({"patterns": [_GOOD]}))
    assert [p.id for p in module.load_baseline()] == ["ok"]
