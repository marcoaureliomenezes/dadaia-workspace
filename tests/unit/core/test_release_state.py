"""``core.release_state`` — the ``release-state-v1`` reader/writer (v0.5.x, successor to
the ``core.release_events`` fold; operator ruling: RELEASE.jsonl -> RELEASE.json, a
mutable state document, never append-only).

Intent: CONTRACT — the document is the state (no fold): ``parse_release_state`` decodes
a whole ``RELEASE.json`` object in one shot and rejects anything malformed in full
(no partial-line tolerance, unlike the retired JSONL fold), and
``serialize_release_state`` round-trips it byte-for-byte deterministically.
Size: SMALL — pure functions over in-memory text, no I/O.
"""

from __future__ import annotations

import json

import pytest

from dadaia_workspace.core.release_state import (
    SCHEMA,
    ReleaseState,
    parse_release_state,
    serialize_release_state,
)

pytestmark = pytest.mark.unit


def _doc(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "schema": SCHEMA,
        "release": "0.5.0",
        "phase": "IMPLEMENTATION",
        "rc": None,
        "defined": {"sha": "a" * 40, "ts": "2026-08-27T10:31:16Z"},
        "implemented": None,
        "shipped": None,
        "audited": None,
        "log": [
            {
                "ts": "2026-08-27T12:25:47Z",
                "agent": "software-engineer",
                "kind": "note",
                "text": "T-050-02's definition PR is pending.",
            }
        ],
    }
    base.update(overrides)
    return base


def test_parse_release_state_reads_every_field() -> None:
    state = parse_release_state(json.dumps(_doc()))

    assert state.schema == SCHEMA
    assert state.release == "0.5.0"
    assert state.phase == "IMPLEMENTATION"
    assert state.rc is None
    assert state.defined == {"sha": "a" * 40, "ts": "2026-08-27T10:31:16Z"}
    assert state.implemented is None
    assert state.shipped is None
    assert state.audited is None
    assert len(state.log) == 1
    assert state.log[0]["kind"] == "note"
    assert state.segment is None


def test_parse_release_state_reads_optional_segment() -> None:
    state = parse_release_state(json.dumps(_doc(segment="rc-1")))
    assert state.segment == "rc-1"


@pytest.mark.parametrize(
    "mutator,match",
    [
        (lambda d: d.pop("phase"), "missing required"),
        (lambda d: d.__setitem__("schema", "release-event-v1"), "expected 'release-state-v1'"),
        (lambda d: d.__setitem__("phase", 3), "'phase' must be a string"),
        (lambda d: d.__setitem__("rc", "one"), "'rc' must be an integer"),
        (lambda d: d.__setitem__("defined", {"sha": "a" * 40}), "missing required key"),
        (lambda d: d.__setitem__("log", [{"ts": "x"}]), "missing required key"),
        (lambda d: d.__setitem__("log", "not-a-list"), "'log' must be an array"),
    ],
)
def test_parse_release_state_rejects_malformed_documents_in_full(mutator, match) -> None:
    """A single mutable document has no "skip the bad part" tolerance — any structural
    defect fails the whole parse, never a partial/best-effort state (unlike the retired
    JSONL fold, which tolerated one bad line among many good ones)."""
    doc = _doc()
    mutator(doc)

    with pytest.raises(ValueError, match=match):
        parse_release_state(json.dumps(doc))


def test_parse_release_state_rejects_invalid_json() -> None:
    with pytest.raises(ValueError, match="not valid JSON"):
        parse_release_state("not-json-at-all")


def test_parse_release_state_rejects_non_object_top_level() -> None:
    with pytest.raises(ValueError, match="must be a JSON object"):
        parse_release_state(json.dumps(["a", "list"]))


def test_serialize_release_state_round_trips() -> None:
    original = parse_release_state(json.dumps(_doc(segment="alpha-2")))

    text = serialize_release_state(original)
    reparsed = parse_release_state(text)

    assert reparsed == original
    assert text.endswith("\n")
    # Field order is fixed and readable — schema/release/phase lead, log trails.
    assert list(json.loads(text).keys())[:3] == ["schema", "release", "phase"]
    assert list(json.loads(text).keys())[-1] == "log"


def test_release_state_is_a_frozen_dataclass_value_object() -> None:
    state = ReleaseState(
        schema=SCHEMA,
        release="0.6.0",
        phase="DISCOVERY",
        rc=None,
        defined=None,
        implemented=None,
        shipped=None,
        audited=None,
    )
    with pytest.raises(AttributeError):
        state.phase = "SPEC"  # type: ignore[misc]


def test_phase_vocabulary_single_home() -> None:
    """F007 (20260830-design-bug-surface-audit): the release phase vocabulary has ONE
    home — ``core.release_state.PHASES`` — and every consumer imports it. Intent:
    contract; size: unit.

    ``doctor_release.CANONICAL_PHASES`` (the documented import site) and
    ``gate_policy``'s memory-write subset must be the same objects, not re-typed
    literals — a re-typed literal is exactly the duplicated-decider class the
    demolished lifecycle cluster died of.
    """
    from dadaia_workspace.core import release_state
    from dadaia_workspace.features.spec_context import gate_policy
    from dadaia_workspace.features.specs import doctor_release

    assert doctor_release.CANONICAL_PHASES is release_state.PHASES
    assert gate_policy._MEMORY_WRITE_PHASES is release_state.MEMORY_WRITE_PHASES
    assert release_state.MEMORY_WRITE_PHASES < release_state.PHASES
