#!/usr/bin/env python3
"""The four terminal transitions — the ONE way a bug record reaches a terminal status.

`resolve`/`supersede`/`defer`/`reject` each refuse an incomplete call with every missing
field named at once, leaving the record untouched: `status` and `closed_at` are stamped
here and nowhere else, which is why `update` refuses them (`_bugs_write.apply_update`).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _bugs_store import Records, Refusal, by_id  # noqa: E402
from _bugs_write import _redacted, _set, now_iso  # noqa: E402

REQUIRED_BY_VERB = {
    "resolve": ("cause", "caused_by", "resolved_release", "solution",
                "evidence_loop", "evidence_seam", "evidence_diff"),
    "supersede": ("by",), "defer": ("reason",), "reject": ("reason",),
}  # fmt: skip
_EVIDENCE_DIFF_RE = re.compile(r"^(net-negative|net-positive|net-neutral):\s*\S.*$")
STATUS_BY_VERB = {"resolve": "resolved", "supersede": "superseded",
                  "defer": "deferred", "reject": "rejected"}  # fmt: skip
_SCRIPT = Path(__file__).parent / "bugs.py"


def transition(records: Records, bug_id: str, verb: str, values: dict[str, Any],
               known_ids: set[str]) -> Records:  # fmt: skip
    """The ONE way a record reaches a terminal status. Every field the verb requires is
    checked first and every problem named at once; the record is untouched on refusal."""
    missing = [name for name in REQUIRED_BY_VERB[verb] if not (values.get(name) or "").strip()]
    if missing:
        raise Refusal(
            f"transition {verb!r} refused — {', '.join(repr(m) for m in missing)} required",
            f"{_SCRIPT} {verb} {bug_id} "
            + " ".join(f"--{m.replace('_', '-')} <{m}>" for m in missing),
        )
    record = by_id(records, bug_id)
    updated = dict(record)
    if verb == "resolve":
        if not _EVIDENCE_DIFF_RE.match(values["evidence_diff"]):
            raise Refusal(
                "'evidence_diff' must match '^(net-negative|net-positive|net-neutral): "
                "<rationale>'",
                f"{_SCRIPT} resolve {bug_id} --evidence-diff 'net-negative: <why>'",
            )
        if values["caused_by"] != "none" and values["caused_by"] not in known_ids:
            raise Refusal(
                f"caused_by {values['caused_by']!r} is not a record of this bug ledger",
                f"{_SCRIPT} resolve {bug_id} --caused-by none --specs <specs>",
            )
        for key in REQUIRED_BY_VERB["resolve"]:
            _set(updated, key, values[key])
        _set(updated, "diff_direction", values["evidence_diff"].split(":", 1)[0])
    elif verb == "supersede":
        _set(updated, "superseded_by", values["by"])
    else:
        _set(updated, "cause", values["reason"])
    updated["status"] = STATUS_BY_VERB[verb]
    updated["closed_at"] = record.get("closed_at") or now_iso()
    return [_redacted(updated) if r is record else r for r in records]
