"""sa-backlog-intents-have-two-grammars: the backlog-v1 schema is the
one intents grammar — its kind enum is the model's, and a code ref is repo-relative
``path[#word]`` (privacy: no absolute, ``~``, drive or ``..`` path is ever committed).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from dadaia_workspace.core.models.backlog import SubjectKind

_SCHEMA = json.loads(
    (
        Path(__file__).resolve().parents[3]
        / "dadaia_workspace/public/schemas/backlog/backlog-v1.schema.json"
    ).read_text(encoding="utf-8")
)
_INTENT = Draft202012Validator({"$defs": _SCHEMA["$defs"], "$ref": "#/$defs/intent"})


def test_the_model_kinds_are_the_schema_kinds() -> None:
    kinds = _SCHEMA["$defs"]["intent"]["properties"]["subject"]["properties"]["kind"]["enum"]
    assert sorted(kinds) == sorted(k.value for k in SubjectKind)


@pytest.mark.parametrize(
    ("kind", "ref", "valid"),
    [
        ("code", "pkg/m.py#Widget", True),
        ("code", "/abs/m.py#W", False),
        ("code", "~/secret/foo.py#Bar", False),
        ("code", "../other-repo/foo.py#Bar", False),
        ("code", "C:/x/foo.py#Bar", False),
        ("code", "pkg/m.py", True),
        ("code", "cmd/w.go#Widget", True),
        ("code", "pkg/m.py#", False),
        ("doc", "   ", False),
        ("api", "x", False),
    ],
)
def test_the_schema_judges_a_subject_ref(kind: str, ref: str, valid: bool) -> None:
    intent = {"subject": {"kind": kind, "ref": ref}, "change": "c"}
    assert _INTENT.is_valid(intent) is valid
