#!/usr/bin/env python3
"""The two verbs an audit moves by: disposition a finding, close the audit.

`close` is all-or-nothing: every finding must already be terminal and the releases they
name must be one release, or nothing is written and nothing is deleted. The histo record
is appended LAST, immediately before the directory is deleted, so the directory is never
gone without its record.
"""

from __future__ import annotations

import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from shutil import rmtree
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _audit_schema import AUDITS, DISPOSITIONS, FINDINGS, PILLARS, REQUIRED_EVIDENCE  # noqa: E402
from _audit_store import (  # noqa: E402
    SCRIPT,
    Refusal,
    append_histo,
    audit_dir,
    read_findings,
    write_findings,
)


def disposition(specs: Path, audit: str, finding_id: str, values: dict[str, Any]) -> str:
    """Rewrite one finding's governance triple in place; every other field stays byte-
    identical. Refuses — writing nothing — an unknown audit or finding, a word outside
    the one finding vocabulary, or a verdict missing the evidence it requires."""
    verdict = values["disposition"]
    example = f"--disposition {verdict} --release <release-id>"
    directory = audit_dir(specs, audit, f"{SCRIPT} disposition <audit-dir> <finding-id> {example}")
    if verdict not in DISPOSITIONS:
        raise Refusal(
            f"unknown disposition {verdict!r}: a finding is dispositioned as one of "
            f"{'|'.join(DISPOSITIONS)}",
            f"{SCRIPT} disposition {audit} {finding_id} --disposition resolved "
            "--release <release-id>",
        )
    required = REQUIRED_EVIDENCE[verdict]
    if not (values.get(required) or "").strip():
        needed = (
            "--release <release-id>"
            if required == "release"
            else "--reason '<why it was not fixed>'"
        )
        raise Refusal(
            f"disposition {verdict!r} requires --{required}: the finding's governance "
            "triple is the only surviving record of how it was closed",
            f"{SCRIPT} disposition {audit} {finding_id} --disposition {verdict} {needed}",
        )
    records = read_findings(directory)
    known = [str(record.get("id")) for record in records]
    if finding_id not in known:
        raise Refusal(
            f"{finding_id!r} does not name a finding of audit {audit!r}. Known findings: "
            f"{', '.join(known) or '(none)'}",
            f"grep {finding_id} specs/{AUDITS}/{audit}/{FINDINGS}",
        )
    for record in records:
        if record.get("id") == finding_id:
            record["disposition"] = verdict
            for field in ("release", "reason"):
                if values.get(field) is not None:
                    record[field] = values[field]
    write_findings(directory, records)
    return f"[ok] {finding_id} -> {verdict}"


def close(specs: Path, audit: str, sha: str) -> str:
    """Append the audit's ONE histo record, then delete the directory."""
    directory = audit_dir(specs, audit, f"{SCRIPT} close <audit-dir> --sha <window-end>")
    records = read_findings(directory)
    if not records:
        raise Refusal(
            f"audit {audit!r} carries no findings — an audit closes on the record of what it found",
            f"grep . specs/{AUDITS}/{audit}/{FINDINGS}",
        )
    open_ids = [str(r.get("id")) for r in records if r.get("disposition") not in DISPOSITIONS]
    if open_ids:
        raise Refusal(
            f"audit {audit!r} still carries {len(open_ids)} undispositioned finding(s): "
            f"{', '.join(open_ids)}. Every finding gets a disposition before the audit closes",
            f"{SCRIPT} disposition {audit} {open_ids[0]} --disposition resolved "
            "--release <release-id>",
        )
    releases = sorted({str(r["release"]) for r in records if r.get("release")})
    if len(releases) > 1:
        raise Refusal(
            f"audit {audit!r} names {len(releases)} remediation releases "
            f"({', '.join(releases)}); an audit generates exactly one",
            f"{SCRIPT} disposition {audit} <finding-id> --disposition resolved "
            f"--release {releases[0]}",
        )
    pillars = Counter(str(record.get("pillar")) for record in records)
    verdicts = Counter(str(record.get("disposition")) for record in records)
    append_histo(specs, {
        "id": audit,
        "ts": datetime.now(tz=UTC).strftime("%Y-%m-%d"),
        "disposition": "resolved",
        "release": releases[0] if releases else None,
        "reason": None,
        "summary": ", ".join(f"{pillar} {pillars[pillar]}" for pillar in PILLARS),
        "entry": {
            "sha": sha,
            "pillars": {pillar: pillars[pillar] for pillar in PILLARS},
            "dispositions": dict(verdicts),
        },
    })  # fmt: skip
    rmtree(directory)
    return f"[ok] archived audit {audit} -> specs/{AUDITS}/_archive/audits_histo.jsonl"
