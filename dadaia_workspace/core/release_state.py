"""Pure parse/serialize helpers over ``release-state-v1`` (v0.5.x successor to the
``RELEASE.jsonl`` event fold, operator ruling 2026-08-2x: "transformar o arquivo
canonico das specs RELEASE.jsonl em RELEASE.json -- e um arquivo altamente mutavel
onde acompanhamos o estado do release. Nao faz sentido ser append-only.").

``specs/releases/<release-id>/RELEASE.json`` is now ONE mutable JSON object -- the
state IS the document, no event stream to fold. This module retires
``core/release_events.py`` (``parse_release_events``/``fold_release_events``/
``ReleaseEvent``/``ReleaseFold``): there is nothing left to fold, so there is nothing
left to export under those names. Schema:
``dadaia_workspace/public/schemas/releases/release-state-v1.schema.json``.

**This module never performs file I/O** (``core/`` file-I/O purity ratchet,
``tests/contract/test_core_file_io_purity.py``, architect A9) -- it parses/serializes
already-read text. The ONE tri-state disk read of a release's ``RELEASE.json`` stays a
``features``-layer concern (``features.specs.doctor_common``), same precedent this
module's predecessor set.

``segment`` is carried as an OPTIONAL top-level field, outside the operator's literal
five-milestone shape, because the ADR-1/ADR-5 dir-based segment mechanism
(``releases/<id>/<segment>/TASKS.md`` routing) is live, orthogonal state that the
migration must not silently drop -- flagged for the operator/product-engineer to fold
into a future ADR rather than invented as a workaround here.
"""

from __future__ import annotations

from pathlib import Path

import json
from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "MEMORY_WRITE_PHASES",
    "PHASES",
    "SCHEMA",
    "ReleaseState",
    "parse_release_state",
    "serialize_release_state",
]

#: The schema identifier every ``RELEASE.json`` document's ``schema`` field must carry.
SCHEMA = "release-state-v1"

#: The canonical release-state document filename (release 0.4.6 FR1, ADR 0007): the
#: underscore prefix groups it with ``_archive``/``_ideas`` and sorts it apart from the
#: working SPEC/PLAN/TASKS trio. ONE decider — no reader hand-builds this name.
RELEASE_STATE_FILENAME = "_RELEASE.json"

#: The pre-0.4.6 filename, recognised READ-side only so a consumer instance keeps
#: working until ``specs doctor --fix`` renames it. Writers always use
#: :data:`RELEASE_STATE_FILENAME`.
LEGACY_RELEASE_STATE_FILENAME = "RELEASE.json"


def release_state_file(release_dir: "Path") -> "Path | None":
    """The release-state document inside ``release_dir``: the canonical
    :data:`RELEASE_STATE_FILENAME` when present, else the legacy name, else ``None``.
    The ONE existence-and-name rule every live-release discovery goes through."""
    canonical = release_dir / RELEASE_STATE_FILENAME
    if canonical.is_file():
        return canonical
    legacy = release_dir / LEGACY_RELEASE_STATE_FILENAME
    if legacy.is_file():
        return legacy
    return None


#: Canonical release lifecycle phase vocabulary (constitution §7; the ``phase`` field
#: of release-state-v1). ONE home (F007, 20260830 audit) — every consumer imports this
#: set; ``"none"`` is the scaffold default meaning "no active release".
PHASES: frozenset[str] = frozenset(
    {
        "DISCOVERY",
        "DEFINITION",
        "SPEC",
        "PLAN",
        "TASKS",
        "IMPLEMENTATION",
        "CLOSURE",
        "ARCHIVED",
        "none",
    }
)

#: Phases in which product-engineer may write memory atoms (constitution §13 / FR-P1-13).
MEMORY_WRITE_PHASES: frozenset[str] = frozenset({"DEFINITION", "CLOSURE"})

#: Per-milestone-kind required inner keys (light structural validation only -- the
#: schema file is the shape authority; this is a parse-time sanity check, not a second
#: schema implementation).
_MILESTONE_REQUIRED: dict[str, frozenset[str]] = {
    "defined": frozenset({"sha", "ts"}),
    "implemented": frozenset({"sha", "rc", "ts"}),
    "shipped": frozenset({"sha", "pr", "ts"}),
    "audited": frozenset({"sha", "ts", "audit"}),
}

_TOP_LEVEL_REQUIRED: frozenset[str] = frozenset(
    {"schema", "release", "phase", "rc", "defined", "implemented", "shipped", "audited", "log"}
)

_NOTE_REQUIRED: frozenset[str] = frozenset({"ts", "agent", "kind", "text"})


@dataclass(frozen=True)
class ReleaseState:
    """One release's complete mutable state -- the whole ``RELEASE.json`` document.

    ``defined``/``implemented``/``shipped``/``audited`` are ``dict | None`` rather than
    four near-identical dataclasses -- each already carries its own shape via
    :data:`_MILESTONE_REQUIRED` and gains nothing from a bespoke type per kind. ``log``
    is the append-only narrative array living INSIDE this otherwise-mutable document
    (governance text: closure narrative, drift/dispositions, free-form log) --
    rewritten in place by a CAS writer the same as every other field, never a second
    file.
    """

    schema: str
    release: str
    phase: str
    rc: int | None
    defined: dict[str, Any] | None
    implemented: dict[str, Any] | None
    shipped: dict[str, Any] | None
    audited: dict[str, Any] | None
    log: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    segment: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """The canonical field order this module always serializes -- schema first,
        log last, matching ``release-state-v1.schema.json``'s ``properties`` order."""
        out: dict[str, Any] = {
            "schema": self.schema,
            "release": self.release,
            "phase": self.phase,
            "rc": self.rc,
            "defined": self.defined,
            "implemented": self.implemented,
            "shipped": self.shipped,
            "audited": self.audited,
        }
        if self.segment is not None:
            out["segment"] = self.segment
        out["log"] = [dict(n) for n in self.log]
        return out


def _validate_milestone(kind: str, value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError(f"'{kind}' must be an object or null, got {type(value).__name__}")
    missing = _MILESTONE_REQUIRED[kind] - value.keys()
    if missing:
        raise ValueError(f"'{kind}' is missing required key(s): {sorted(missing)}")
    return value


def _validate_notes(value: Any) -> tuple[dict[str, Any], ...]:
    if not isinstance(value, list):
        raise ValueError(f"'log' must be an array, got {type(value).__name__}")
    log: list[dict[str, Any]] = []
    for i, entry in enumerate(value):
        if not isinstance(entry, dict):
            raise ValueError(f"log[{i}] must be an object, got {type(entry).__name__}")
        missing = _NOTE_REQUIRED - entry.keys()
        if missing:
            raise ValueError(f"log[{i}] is missing required key(s): {sorted(missing)}")
        log.append(entry)
    return tuple(log)


def parse_release_state(text: str) -> ReleaseState:
    """Decode ``text`` (the raw content of a ``RELEASE.json`` file) into a
    :class:`ReleaseState`.

    Pure -- no I/O. Raises :class:`ValueError` for anything that is not a single
    well-formed ``release-state-v1`` document: invalid JSON, a non-object top level, a
    missing required key, a wrong-typed value, or a milestone object missing its
    required inner keys. A single mutable document has no "skip the bad line, keep the
    rest" tolerance the old append-only fold needed -- a malformed ``RELEASE.json`` is
    UNKNOWN state, in full, and every caller must treat it that way (never guess a
    partial phase out of a document that failed to parse).
    """
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"RELEASE.json is not valid JSON: {exc}") from exc
    if not isinstance(obj, dict):
        raise ValueError(f"RELEASE.json must be a JSON object, got {type(obj).__name__}")
    missing = _TOP_LEVEL_REQUIRED - obj.keys()
    if missing:
        raise ValueError(f"RELEASE.json is missing required key(s): {sorted(missing)}")
    if obj["schema"] != SCHEMA:
        raise ValueError(f"RELEASE.json schema={obj['schema']!r}, expected {SCHEMA!r}")
    if not isinstance(obj["release"], str):
        raise ValueError("'release' must be a string")
    if not isinstance(obj["phase"], str):
        raise ValueError("'phase' must be a string")
    rc = obj["rc"]
    if rc is not None and not isinstance(rc, int):
        raise ValueError(f"'rc' must be an integer or null, got {type(rc).__name__}")
    segment = obj.get("segment")
    if segment is not None and not isinstance(segment, str):
        raise ValueError(f"'segment' must be a string or null, got {type(segment).__name__}")
    return ReleaseState(
        schema=obj["schema"],
        release=obj["release"],
        phase=obj["phase"],
        rc=rc,
        defined=_validate_milestone("defined", obj["defined"]),
        implemented=_validate_milestone("implemented", obj["implemented"]),
        shipped=_validate_milestone("shipped", obj["shipped"]),
        audited=_validate_milestone("audited", obj["audited"]),
        log=_validate_notes(obj["log"]),
        segment=segment,
    )


def serialize_release_state(state: ReleaseState) -> str:
    """Render *state* back to the canonical ``RELEASE.json`` text: 2-space indent,
    the fixed field order :meth:`ReleaseState.to_dict` declares, trailing newline."""
    return json.dumps(state.to_dict(), indent=2, ensure_ascii=False) + "\n"
