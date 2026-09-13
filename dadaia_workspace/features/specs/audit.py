"""The two audit verbs: disposition a finding, close the audit (0.4.7 FR4).

``specs/audits/**`` had no actor. A finding's governance triple was rewritten with file
tools, the ``audits_histo.jsonl`` record was hand-written, and the directory was removed
by hand — three acts, in order, that an agent had to remember; a half-done sweep left an
audit that looked closed and was not. These two functions are the one path:

- :func:`disposition_finding` rewrites exactly the mutable-governance triple, through
  :meth:`FindingRecord.apply_governance_update` inside ``JsonlRecordStore.update`` —
  the immutable core is refused by the model, not by a check written here.
- :func:`close_audit` is all-or-nothing: every finding must already be terminal, and the
  histo record is appended LAST, immediately before the directory is deleted, so a
  refusal at any earlier point leaves the audit exactly as it was.

Every refusal is an :class:`AuditError` carrying exactly one ``fix:`` line.
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from shutil import rmtree

from dadaia_workspace.core.kernel_tunables import DADAIA_BIN
from dadaia_workspace.core.models.findings import FindingRecord
from dadaia_workspace.core.models.histo import (
    AUDIT_PILLARS,
    FINDINGS_DISPOSITIONS,
    HistoRecord,
)
from dadaia_workspace.infrastructure.jsonl_record_store import JsonlRecordStore

__all__ = ["AuditError", "close_audit", "disposition_finding"]

#: The evidence each disposition must carry — one table, no per-word branch. A
#: ``resolved``/``superseded`` finding names the remediation release that closed it; a
#: ``deferred``/``rejected`` one names why, because nothing else records the decision.
_REQUIRED_EVIDENCE: dict[str, str] = {
    "resolved": "release",
    "superseded": "release",
    "deferred": "reason",
    "rejected": "reason",
}


class AuditError(ValueError):
    """One refusal of an audit verb, message carrying exactly one ``fix:`` line."""


def _findings_store(audit_dir: Path) -> JsonlRecordStore[FindingRecord]:
    return JsonlRecordStore(
        audit_dir / "FINDINGS.jsonl",
        to_dict=FindingRecord.to_dict,
        from_dict=FindingRecord.from_dict,
    )


def _audit_dir(specs_dir: Path, audit: str, *, fix: str) -> Path:
    """Resolve one live audit directory, or refuse naming the ones that exist and the
    *fix* line of the verb that asked.

    *audit* is operator input naming a directory :func:`close_audit` DELETES, so it is
    CONFINED before it is read: the fully resolved target must sit strictly inside the
    resolved ``specs/audits/``. One containment rule covers every escape shape —
    ``..`` traversal, an absolute path, and a symlink out of the tree (CWE-22/CWE-59) —
    so there is no second, per-shape check to keep in step with it.
    """
    audits = (specs_dir / "audits").resolve()
    target = (audits / audit).resolve()
    confined = target != audits and target.is_relative_to(audits)
    if confined and (target / "FINDINGS.jsonl").is_file():
        return target
    live = sorted(
        child.name
        for child in (audits.iterdir() if audits.is_dir() else [])
        if child.is_dir() and child.name != "_archive"
    )
    raise AuditError(
        f"{audit!r} does not name a live audit with a FINDINGS.jsonl under "
        f"specs/audits/. Live audits: {', '.join(live) or '(none)'}.\n"
        f"fix: {fix}"
    )


def _read_findings(audit_dir: Path) -> list[FindingRecord]:
    records: list[FindingRecord] = []
    for index, line in enumerate(
        audit_dir.joinpath("FINDINGS.jsonl").read_text(encoding="utf-8").split("\n"), start=1
    ):
        if not line.strip():
            continue
        try:
            records.append(FindingRecord.from_dict(json.loads(line)))
        except (ValueError, TypeError) as exc:
            raise AuditError(
                f"specs/audits/{audit_dir.name}/FINDINGS.jsonl line {index} is not a valid "
                f"finding record: {exc}\n"
                f"fix: sed -n '{index}p' specs/audits/{audit_dir.name}/FINDINGS.jsonl"
            ) from exc
    return records


def disposition_finding(
    specs_dir: Path,
    audit: str,
    finding_id: str,
    *,
    disposition: str,
    release: str | None = None,
    reason: str | None = None,
) -> FindingRecord:
    """Rewrite one finding's governance triple in place and return the new record.

    Refuses — writing nothing — an unknown audit, an unknown finding id, a word outside
    the one finding vocabulary, or a disposition missing the evidence it requires.
    """
    audit_dir = _audit_dir(
        specs_dir,
        audit,
        fix=f"{DADAIA_BIN} audit disposition <audit-dir> <finding-id> "
        "--disposition resolved --release <release-id>",
    )

    if disposition not in FINDINGS_DISPOSITIONS:
        raise AuditError(
            f"unknown disposition {disposition!r}: a finding is dispositioned as one of "
            f"{'|'.join(FINDINGS_DISPOSITIONS)} (the word 'fixed' was retired — one "
            "finding vocabulary, 0.4.7 FR4).\n"
            f"fix: {DADAIA_BIN} audit disposition {audit} {finding_id} --disposition resolved "
            "--release <release-id>"
        )

    required = _REQUIRED_EVIDENCE[disposition]
    supplied = {"release": release, "reason": reason}[required]
    if not (supplied or "").strip():
        example = (
            "--release <release-id>"
            if required == "release"
            else "--reason '<why it was not fixed>'"
        )
        raise AuditError(
            f"disposition {disposition!r} requires --{required}: the finding's governance "
            "triple is the only surviving record of how it was closed.\n"
            f"fix: {DADAIA_BIN} audit disposition {audit} {finding_id} "
            f"--disposition {disposition} {example}"
        )

    known = [record.id for record in _read_findings(audit_dir)]
    if finding_id not in known:
        raise AuditError(
            f"{finding_id!r} does not name a finding of audit {audit!r}. Known findings: "
            f"{', '.join(known) or '(none)'}.\n"
            f"fix: grep {finding_id} specs/audits/{audit}/FINDINGS.jsonl"
        )

    changes: dict[str, object] = {"disposition": disposition}
    if release is not None:
        changes["release"] = release
    if reason is not None:
        changes["reason"] = reason
    return _findings_store(audit_dir).update(
        finding_id, lambda record: record.apply_governance_update(changes)
    )


def close_audit(
    specs_dir: Path,
    audit: str,
    *,
    sha: str,
    histo_append: Callable[[HistoRecord], None],
    denylist_terms: Sequence[tuple[str, str]],
) -> HistoRecord:
    """Archive one fully dispositioned audit: append its ONE histo record, then delete
    the directory (0.4.7 FR4).

    ``denylist_terms`` is redacted through :meth:`HistoRecord.redact` before the append —
    the same write-time seam ``backlog_exit`` and ``BugService`` already enforce, so one
    record shape has one redaction point, not three.

    All-or-nothing. Every finding must already be terminal and the release they name
    must be one release — otherwise nothing is written and nothing is deleted. The histo
    record is appended LAST, so the directory is never gone without its record.
    """
    audit_dir = _audit_dir(
        specs_dir, audit, fix=f"{DADAIA_BIN} audit close <audit-dir> --sha <window-end-sha>"
    )
    records = _read_findings(audit_dir)
    if not records:
        raise AuditError(
            f"audit {audit!r} carries no findings — an audit closes on the record of what "
            "it found.\n"
            f"fix: grep . specs/audits/{audit}/FINDINGS.jsonl"
        )

    open_ids = [record.id for record in records if record.disposition not in FINDINGS_DISPOSITIONS]
    if open_ids:
        raise AuditError(
            f"audit {audit!r} still carries {len(open_ids)} undispositioned finding(s): "
            f"{', '.join(open_ids)}. Every finding gets a disposition before the audit "
            "closes.\n"
            f"fix: {DADAIA_BIN} audit disposition {audit} {open_ids[0]} --disposition resolved "
            "--release <release-id>"
        )

    releases = sorted({record.release for record in records if record.release})
    if len(releases) > 1:
        raise AuditError(
            f"audit {audit!r} names {len(releases)} remediation releases "
            f"({', '.join(releases)}); an audit generates exactly one.\n"
            f"fix: {DADAIA_BIN} audit disposition {audit} <finding-id> --disposition resolved "
            f"--release {releases[0]}"
        )

    pillars = Counter(record.pillar for record in records)
    dispositions = Counter(record.disposition for record in records)
    record = HistoRecord(
        id=audit,
        ts=datetime.now(tz=UTC).strftime("%Y-%m-%d"),
        disposition="resolved",
        release=releases[0] if releases else None,
        reason=None,
        summary=", ".join(f"{pillar} {pillars[pillar]}" for pillar in AUDIT_PILLARS),
        entry={
            "sha": sha,
            "pillars": {pillar: pillars[pillar] for pillar in AUDIT_PILLARS},
            "dispositions": dict(dispositions),
        },
    ).redact(denylist_terms)
    histo_append(record)
    rmtree(audit_dir)
    return record
