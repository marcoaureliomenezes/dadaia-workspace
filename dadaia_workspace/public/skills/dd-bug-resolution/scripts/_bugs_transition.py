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
from _bugs_write import _SCRIPT, _set, now_iso  # noqa: E402

REQUIRED_BY_VERB = {
    "resolve": ("cause", "caused_by", "resolved_release", "solution",
                "evidence_loop", "evidence_seam", "evidence_diff"),
    "supersede": ("by",), "defer": ("reason",), "reject": ("reason",),
}  # fmt: skip
_EVIDENCE_DIFF_RE = re.compile(r"^(net-negative|net-positive|net-neutral):\s*\S.*$")
_SEAM_RE = re.compile(r"^([^\s:;]+)(?:::(?:\w+::)*(\w+))?")
STATUS_BY_VERB = {"resolve": "resolved", "supersede": "superseded",
                  "defer": "deferred", "reject": "rejected"}  # fmt: skip


def _seam_exists(seam: str, root: Path) -> bool:
    """The seam's leading ``path[::…::name]`` names a file under *root* and, with a name,
    a ``def <name>`` in it (ADR 0160) — judged once, here, never re-judged by ``check``."""
    match = _SEAM_RE.match(seam)
    if match is None or not (path := root / match[1]).is_file():
        return False
    return not match[2] or re.search(rf"\bdef {match[2]}\b", path.read_text("utf-8")) is not None


def transition(records: Records, bug_id: str, verb: str, values: dict[str, Any],
               root: Path) -> Records:  # fmt: skip
    """The ONE way a record reaches a terminal status. Every field the verb requires is
    checked first and every problem named at once; the record is untouched on refusal.
    A resolve's seam is read under *root*, the repo the ledger belongs to."""
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
        if not _seam_exists(values["evidence_seam"], root):
            raise Refusal(
                f"evidence_seam {values['evidence_seam']!r} names no file or 'def <name>' "
                f"under {root}",
                f"{_SCRIPT} resolve {bug_id} --evidence-seam <tests/path.py::test_name>",
            )
        for key in REQUIRED_BY_VERB["resolve"]:
            _set(updated, key, values[key])
    elif verb == "supersede":
        _set(updated, "superseded_by", values["by"])
    else:
        _set(updated, "cause", values["reason"])
    updated["status"] = STATUS_BY_VERB[verb]
    updated["closed_at"] = now_iso()
    return [updated if r is record else r for r in records]
