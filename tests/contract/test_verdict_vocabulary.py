"""One verdict vocabulary across the public surface.

Intent: CONTRACT — bug verdict-vocabulary-persona-schema-mismatch. Size: SMALL
(pure text reads over the real package tree).

The handoff schema (``public/schemas/handoff-v1.schema.json``) admits exactly two
verdict tokens: ``APPROVED`` and ``REJECTED``. A persona or skill instructing any
other token ("APPROVE", "REQUEST_CHANGES", "COMMENT") makes literal obedience emit
an INVALID handoff — the first write fails for every dispatched reviewer. This test
pins the single vocabulary: no public asset names a retired verdict token.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

_PUBLIC = Path(__file__).resolve().parent.parent.parent / "dadaia_workspace" / "public"

#: Retired verdict tokens a public asset must never instruct.
_RETIRED = re.compile(r"REQUEST_CHANGES|`APPROVE`(?!D)")


def test_handoff_schema_verdict_enum_is_the_two_tokens() -> None:
    schema = json.loads(
        (_PUBLIC / "schemas" / "handoff-v1.schema.json").read_text(encoding="utf-8")
    )
    verdict = schema["properties"]["verdict"]
    assert verdict["enum"] == ["APPROVED", "REJECTED"]


def test_no_public_asset_names_a_retired_verdict_token() -> None:
    offenders: list[str] = []
    for path in sorted(_PUBLIC.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        for match in _RETIRED.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            rel = path.relative_to(_PUBLIC.parent.parent).as_posix()
            offenders.append(f"{rel}:{line}: {match.group(0)}")
    assert not offenders, (
        "Public assets instructing a verdict token the handoff schema rejects "
        "(use APPROVED/REJECTED):\n" + "\n".join(offenders)
    )
