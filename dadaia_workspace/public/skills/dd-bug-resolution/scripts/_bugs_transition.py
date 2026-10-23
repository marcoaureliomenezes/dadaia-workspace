#!/usr/bin/env python3
"""The three terminal transitions — the ONE way a bug record reaches a terminal status.

`resolve`/`supersede`/`reject` each refuse an incomplete call with every missing
field named at once, leaving the record untouched: `status` and `closed_at` are stamped
here and nowhere else, which is why `update` refuses them (`_bugs_write.apply_update`).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from _bugs_check import STATUS_BY_VERB, ambiguous
from _bugs_store import Records, Refusal, by_id
from _bugs_write import _set, now_iso
from _specs import choice

REQUIRED_BY_VERB = {
    "resolve": ("cause", "caused_by", "solution"),
    "supersede": ("by",), "reject": ("reason",),
}  # fmt: skip


def transition(
    records: Records,
    bug_id: str,
    verb: str,
    values: dict[str, Any],
    specs: Path,
) -> Records:
    """The ONE way a record reaches a terminal status. Every field the verb requires is
    checked first and every problem named at once; the record is untouched on refusal.
    A resolution persists the human diagnosis and the commit that fixed it; derived
    evidence remains in git and tests."""
    missing = [name for name in REQUIRED_BY_VERB[verb] if not (values.get(name) or "").strip()]
    if missing:
        raise choice(Refusal(f"transition {verb!r} refused — {', '.join(repr(m) for m in missing)} required"),
                     f"with {', '.join('--' + m.replace('_', '-') for m in missing)} set")  # fmt: skip
    if verb == "resolve" and (forms := ambiguous(specs, values["caused_by"].strip())):
        raise choice(
            Refusal(f"caused_by {values['caused_by']!r} is carried by several candidates"),
            f"with --caused-by one of {', '.join(forms)}",
        )
    record = by_id(records, bug_id)
    updated = dict(record)
    if verb == "resolve":
        for key in (*REQUIRED_BY_VERB["resolve"], "fix_sha"):
            _set(updated, key, values[key])
    elif verb == "supersede":
        _set(updated, "superseded_by", values["by"])
    else:
        _set(updated, "cause", values["reason"])
    updated["status"] = STATUS_BY_VERB[verb]
    updated["closed_at"] = now_iso()
    return [updated if r is record else r for r in records]
