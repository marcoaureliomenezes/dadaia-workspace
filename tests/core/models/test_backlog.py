"""The backlog-v1 schema is the
one intents grammar — its kind enum is the model's, and a code ref is repo-relative
``path[#word]`` (privacy: no absolute, ``~``, drive or ``..`` path is ever committed).
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from dadaia_workspace.core.models import backlog
from dadaia_workspace.core.models.backlog import SubjectKind
from tests.helpers.oslib import read_text

_SCHEMA = json.loads(
    read_text(
        Path(__file__).resolve().parents[3]
        / "dadaia_workspace/public/skills/dd-backlog-definition/scripts/schemas/backlog-v1.schema.json"
    )
)
_INTENT = Draft202012Validator({"$defs": _SCHEMA["$defs"], "$ref": "#/$defs/intent"})


def test_the_model_kinds_are_the_schema_kinds() -> None:
    kinds = _SCHEMA["$defs"]["intent"]["properties"]["subject"]["properties"]["kind"]["enum"]
    assert sorted(kinds) == sorted(k.value for k in SubjectKind)


def test_the_exempt_status_is_the_schema_owners_word_not_a_second_literal() -> None:
    literals = [
        n.value
        for n in ast.walk(ast.parse(read_text(Path(backlog.__file__))))
        if isinstance(n, ast.Constant) and n.value == "idea"
    ]
    assert (backlog.INTENTS_EXEMPT_STATUS, literals) == ("idea", [])


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
