"""The shipped record schemas: closed envelopes, and what each accepts and refuses.

handoff-v1 (DADAIA §5.4; sa-handoff-self-pull-requirement-diverges#46.1,
sa-handoff-self-pull-requirement-diverges#46.2, sa-handoff-self-pull-requirement-diverges#46.3:
one ``jsonschema`` engine, one verdict per doc); bug-record-v1 (SPEC v0.5.0 A2.1); finding-record-v1
(A13.1); decision-record-v1 (v0.5.0 specs-canon closure); release-state-v1 (no ``rc`` at any depth).
Size: SMALL — schema documents only. The schema checks live here, not beside the stdlib-only core
models (bug mutation-baseline-core-models-scope-now-imports-jsonschema-isolated-venv-cannot-collect).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

pytestmark = pytest.mark.contract

_SCHEMAS = Path(__file__).resolve().parents[2] / "dadaia_workspace" / "public" / "schemas"
_PATHS = {
    "handoff": _SCHEMAS / "handoff-v1.schema.json",
    "bug": _SCHEMAS / "bugs" / "bug-record-v1.schema.json",
    "finding": _SCHEMAS / "audits" / "finding-record-v1.schema.json",
    "adr": _SCHEMAS / "ADRs" / "decision-record-v1.schema.json",
    "release": _SCHEMAS / "releases" / "release-state-v1.schema.json",
}


def _schema(kind: str) -> dict[str, Any]:
    return json.loads(_PATHS[kind].read_text(encoding="utf-8"))  # type: ignore[no-any-return]


_TS = "2026-08-27T10:31:16Z"
_BASE: dict[str, dict[str, Any]] = {
    "handoff": {
        "schema_version": "handoff-v1.2",
        "self_pull": {"refs": ["specs/memory/ARCHITECTURE.md"]},
        "agent": "dd-code-reviewer",
        "context": "dadaia-workspace",
        "produced_at": _TS,
        "scope": "dadaia-workspace/tests",
        "metrics": {"files_changed": 2, "tests_added": 1},
        "artifact": {"type": "report", "path": ".dadaia/reports/r.html", "content_hash": "a" * 64},
        "findings": [
            {"severity": "HIGH", "message": "m", "detail_md": "d", "fix_recommendation": "f"}
        ],
        "verdict": "APPROVED",
        "verdict_reason": "Contract is valid.",
    },
    # write-once fields absent entirely, never null (A2.2b)
    "bug": {
        "id": "sample-bug",
        "ts": _TS,
        "reported_by": "dd-software-engineer",
        "title": "sample bug",
        "severity": "MEDIUM",
        "surface": "tests",
        "component": "features/bugs/service.py#BugService",
        "context": "dadaia-workspace",
        "symptom": "something broke",
        "repro": "run the thing",
        "expected": "it should not break",
        "status": "open",
        "cause": None,
        "caused_by": None,
        "resolved_release": None,
        "audited": None,
        "closed_at": None,
    },
    # the SPEC FR13 example, as appended
    "finding": {
        "id": "20261020-five-release-window-F003",
        "pillar": "bugs",
        "severity": "HIGH",
        "refs": ["certify-skip-detail-leaks-full-codex-output", "<sha-A>"],
        "claim": "fix-induced bug: the leak rides the second render path the fix introduced",
        "evidence": "git show <sha-A> -- dadaia_workspace/features/certification",
        "disposition": "open",
        "release": None,
        "reason": None,
    },
    "adr": {
        "id": "0001",
        "ts": _TS,
        "title": "Features depend on ports, not adapters",
        "status": "proposed",
        "context": "Features need I/O but must stay unit-testable.",
        "decision": "We will define a Protocol per I/O boundary.",
        "consequences": "+ testable with fakes",
        "measured_by": None,
        "supersedes": None,
        "amends": None,
    },
    "release": {
        "schema": "release-state-v1",
        "release": "0.6.0",
        "phase": "IMPLEMENTATION",
        "defined": {"sha": "a" * 40, "ts": _TS},
        "implemented": None,
        "shipped": None,
        "log": [],
    },
}

#: The governance rewrite each record takes after its fix/remediation — valid, immutable core untouched.
_REWRITE: dict[str, dict[str, Any]] = {
    "bug": {
        "status": "resolved",
        "closed_at": "2026-09-01T00:00:00Z",
        "cause": "root cause narrative",
        "resolved_release": "0.5.0",
        "solution": "the fix narrative",
        "evidence_loop": "pytest -q tests/unit",
        "evidence_seam": "tests/contract/test_x.py::test_y",
        "evidence_diff": "net-neutral: relocated",
    },
    "finding": {"disposition": "resolved", "release": "0.5.1", "reason": "one render path"},
}


@pytest.mark.parametrize(
    ("kind", "properties"),
    [
        pytest.param("handoff", None, id="handoff"),
        pytest.param("bug", None, id="bug"),
        pytest.param("finding", {"id", "pillar", "severity", "refs", "claim", "evidence", "disposition", "release", "reason"}, id="finding"),
        pytest.param("adr", {"id", "ts", "title", "status", "context", "decision", "consequences", "measured_by", "supersedes", "amends", "ruling"}, id="adr"),
        pytest.param("release", {"schema", "release", "phase", "defined", "implemented", "shipped", "log"}, id="release"),
    ],
)  # fmt: skip
def test_schema_is_draft_2020_12_and_closes_the_envelope(
    kind: str, properties: set[str] | None
) -> None:
    """Every record schema is valid Draft 2020-12 and refuses an unknown top-level key; the
    finding, ADR and release schemas require exactly their declared property set."""
    schema = _schema(kind)
    Draft202012Validator.check_schema(schema)
    assert schema["additionalProperties"] is False
    if properties is not None:
        # ADR 0151 M1: `ruling` is required on `accepted` only, by the schema's allOf.
        assert set(schema["properties"]) == set(schema["required"]) | {"ruling"} & properties
        assert set(schema["properties"]) == properties


def _milestone(**extra: object) -> dict[str, object]:
    return {"sha": "a" * 40, "ts": _TS, **extra}


def _artifact_path(path: str) -> dict[str, object]:
    return {**_BASE["handoff"]["artifact"], "path": path}


@pytest.mark.parametrize(
    ("kind", "overrides"),
    [
        pytest.param("handoff", {}, id="handoff"),
        pytest.param("bug", {}, id="bug-as-appended"),
        pytest.param("bug", _REWRITE["bug"], id="bug-after-resolution"),
        pytest.param("finding", {}, id="finding-as-appended"),
        pytest.param("finding", _REWRITE["finding"], id="finding-after-remediation"),
        pytest.param("adr", {}, id="adr"),
        pytest.param("adr", {"supersedes": "0002"}, id="adr-supersedes-a-string"),
        pytest.param("adr", {"amends": "0002"}, id="adr-amends-a-string"),
        pytest.param("release", {}, id="release-minimal"),
        pytest.param("release", {"log": [{"ts": _TS, "agent": "t", "kind": "note", "text": "hi"}]}, id="release-log-entry"),
    ],
)  # fmt: skip
def test_a_valid_record_validates(kind: str, overrides: dict[str, Any]) -> None:
    errors = list(Draft202012Validator(_schema(kind)).iter_errors({**_BASE[kind], **overrides}))
    assert errors == []


_DROP = object()


@pytest.mark.parametrize(
    ("kind", "overrides", "field"),
    [
        pytest.param("handoff", {"metrics": _DROP}, "metrics", id="handoff-missing-metrics"),
        pytest.param("handoff", {"verdict": "MAYBE"}, "verdict", id="handoff-invalid-verdict"),
        pytest.param("handoff", {"self_pull": _DROP}, "self_pull", id="handoff-v1.2-without-self-pull"),
        pytest.param("handoff", {"schema_version": "handoff-v1.1"}, "schema_version", id="handoff-v1.1"),
        pytest.param("handoff", {"schema_version": "handoff-v1"}, "schema_version", id="handoff-v1"),
        pytest.param("handoff", {"self_pull": {"refs": []}}, "refs", id="handoff-empty-refs"),
        pytest.param("handoff", {"artifact": _artifact_path("/etc/passwd")}, None, id="handoff-absolute-path"),
        pytest.param("handoff", {"artifact": _artifact_path("../report.html")}, None, id="handoff-parent-traversal"),
        pytest.param("handoff", {"artifact": _artifact_path(".dadaia/reports/../states/p.json")}, None, id="handoff-embedded-parent-traversal"),
        pytest.param("bug", {"unexpected": "nope"}, None, id="bug-unknown-property"),
        # no `picked` status: the pick is the bundled definition commit (v0.5.0 FR2)
        pytest.param("bug", {"status": "picked"}, "status", id="bug-picked-status"),
        pytest.param("finding", {"unexpected": "nope"}, None, id="finding-unknown-property"),
        pytest.param("finding", {"disposition": "picked"}, "disposition", id="finding-bad-disposition"),
        pytest.param("adr", {"unexpected": "nope"}, None, id="adr-unknown-property"),
        pytest.param("adr", {"status": "in-review"}, "status", id="adr-bad-status"),
        pytest.param("adr", {"id": "1"}, "id", id="adr-non-4-digit-id"),
        pytest.param("release", {"rc": 9}, None, id="release-top-level-rc"),
        pytest.param("release", {"implemented": _milestone(rc=9)}, None, id="release-milestone-rc"),
        pytest.param("release", {"schema": "release-event-v1"}, "schema", id="release-wrong-schema-id"),
        pytest.param("release", {"defined": _milestone(bogus=1)}, None, id="release-defined-closed"),
        pytest.param("release", {"implemented": _milestone(bogus=1)}, None, id="release-implemented-closed"),
        pytest.param("release", {"shipped": _milestone(bogus=1)}, None, id="release-shipped-closed"),
        pytest.param("release", {"log": [{"ts": _TS, "agent": "t"}]}, None, id="release-log-entry-without-kind-text"),
    ],
)  # fmt: skip
def test_an_invalid_record_is_refused(
    kind: str, overrides: dict[str, Any], field: str | None
) -> None:
    doc = {k: v for k, v in {**_BASE[kind], **overrides}.items() if v is not _DROP}
    errors = list(Draft202012Validator(_schema(kind)).iter_errors(doc))
    assert errors
    if field is not None:
        assert any(field in e.json_path or field in e.message for e in errors), errors


@pytest.mark.parametrize(
    ("kind", "categories"),
    [
        pytest.param("bug", {"immutable-core", "write-once", "mutable-governance"}, id="bug"),
        pytest.param("finding", {"immutable-core", "mutable-governance"}, id="finding"),
    ],
)
def test_mutability_is_declared_per_property_and_the_rewrite_spares_the_core(
    kind: str, categories: set[str]
) -> None:
    """A2.1/A13.1: every property carries ``x-mutability`` in its closed set; ``required`` is
    every property but the write-once ones; the governance rewrite touches no immutable-core field.
    A finding's only mutable fields are disposition/release/reason."""
    properties = _schema(kind)["properties"]
    mutability = {name: spec["x-mutability"] for name, spec in properties.items()}
    assert set(mutability.values()) == categories
    required = set(_schema(kind)["required"])
    assert required == {n for n, c in mutability.items() if c != "write-once"}
    assert not {n for n in _REWRITE[kind] if mutability[n] == "immutable-core"}
    if kind == "finding":
        assert {n for n, c in mutability.items() if c == "mutable-governance"} == set(
            _REWRITE[kind]
        )


def test_the_bug_law_points_at_x_mutability_and_lists_no_fields() -> None:
    """sa-spec-doc-033-duplicates-bugs-check#B7: the scaffold bugs law names the schema's
    x-mutability and restates no field list (no line naming three or more properties)."""
    properties = set(_schema("bug")["properties"])
    law = (_SCHEMAS.parent / "scaffold" / "bugs" / "AGENTS.md").read_text(encoding="utf-8")
    assert "x-mutability" in law
    assert not [ln for ln in law.splitlines() if len(properties & set(ln.split("`"))) >= 3]


def test_the_surface_names_no_library_fact() -> None:
    """sa-consumer-law-carries-library-facts#FR8.1: the bug schema projected beside every
    consumer's bugs.py carries no library layer or package list for ``surface``."""
    surface = _schema("bug")["properties"]["surface"]
    assert "enum" not in surface and "x-enum-append" not in surface
    assert surface["type"] == "string" and surface["minLength"] == 1
    assert "dadaia_workspace" not in surface["description"]


def test_handoff_schema_verdict_enum_is_the_two_tokens() -> None:
    """verdict-vocabulary-persona-schema-mismatch: the one verdict vocabulary (the public text
    rows live in test_public_source_hygiene)."""
    assert _schema("handoff")["properties"]["verdict"]["enum"] == ["APPROVED", "REJECTED"]
