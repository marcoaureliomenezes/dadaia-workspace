"""No public law, scaffold or schema text declares a RETIRED bug-record key as a live
field.

Intent: CONTRACT — 0.4.7 FR1/FR7 (code review c3 HIGH-3/LOW-10). `bug-record-v1.schema
.json` is `additionalProperties: false` with none of the seven derived-provenance keys,
so an agent obeying a scaffolded rule that still lists one writes a record the ledger
rules reject. FR7's AC grep covered the skill corpus, never the key NAMES.

Size: SMALL (reads the shipped `public/` tree; no subprocess, no fixture, no network).
"""

from __future__ import annotations

from pathlib import Path

import pytest

import dadaia_workspace

pytestmark = pytest.mark.contract

_PUBLIC = Path(dadaia_workspace.__file__).resolve().parent / "public"

#: The seven derived-provenance keys 0.4.7 FR1 retired — the git-derived cache the
#: record used to carry. `BugRecord.from_dict` ignores them; `to_dict` never emits them.
_RETIRED_KEYS = (
    "lineage_source",
    "registration_commit",
    "registration_granularity",
    "resolved_commit",
    "resolution_granularity",
    "root_cause",
    "migration_note",
)

#: The ONE sentence a retired key may still appear in: the retirement itself. A line
#: that says "retired" documents the removal; any other line declares a live field.
_RETIREMENT_MARKER = "retired"


def _public_text_files() -> list[Path]:
    return sorted(
        path for suffix in ("*.md", "*.json") for path in _PUBLIC.rglob(suffix) if path.is_file()
    )


def test_no_public_asset_names_a_retired_bug_record_key_as_a_live_field() -> None:
    offenders: list[str] = []
    for path in _public_text_files():
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if _RETIREMENT_MARKER in line:
                continue
            for key in _RETIRED_KEYS:
                if key in line:
                    rel = path.relative_to(_PUBLIC.parent.parent).as_posix()
                    offenders.append(f"{rel}:{lineno} names retired key {key!r}")

    assert not offenders, "\n".join(offenders)
