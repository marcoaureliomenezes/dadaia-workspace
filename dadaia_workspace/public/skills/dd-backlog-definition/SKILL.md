---
name: dd-backlog-definition
description: >
  Curate specs/backlog: the BACKLOG.json active[] document, staleness/dedup
  sanitizing, the operator-gated intake report (the only path to a new entry), and
  the terminal disposition vocabulary. Use when touching a backlog file, compiling an
  intake report, or handing release-definition its picked set.
---

# dd-backlog-definition

> `dd-project-manager` runs this continuously — not a release-boundary event.

## The document

1. Open `specs/backlog/AGENTS.md` (the area's scoped law) and follow it — `BACKLOG.json`
   shape, required fields, live status tokens, the histo record, the dispositions.
2. Append via `python3 .agents/skills/dd-backlog-definition/scripts/backlog.py new <slug>`; validate via `dadaia doctor` (`ledgers`
   section).

## Continuous curation

- Re-read the whole document on every new entry — it is small enough that partial
  review is a discipline failure.
- Dedup: compare a new entry's title+description against every ACTIVE item for the
  same subject — by domain concept (`dd-domain-modeling`), not by the request's
  wording; merge a near-duplicate into the existing entry.
- Staleness: an ACTIVE item with no reads/updates past a reasonable window is a
  sanitize candidate; a confirmed-invalid item exits as `rejected` with a one-line
  `reason`; a merely-postponed one stays `active[]`.

## The intake gate — the only path to a new entry

- Only the operator creates demand. An entry materializes via the PM's
  operator-facing intake report (handoff with `next_handoff.agent: "human"` plus its
  HTML report), or via an operator-ratified in-release deferral (already counts as
  intake).
- Compile every actionable defect (review findings, closure returns, audit
  observations) into that report at each release close and review round — never
  write a technical residual directly into `BACKLOG.json`.
- A record-only observation (INFO-grade, awareness-only) terminates in the
  reviewer's own findings, not in an intake report.

## Pick and dispositions

- A picked entry stays in `active[]` with `status: picked` —
  nothing is purged at pick time.
- It exits exactly once, at closure, by `python3 .agents/skills/dd-backlog-definition/scripts/backlog.py exit <slug> --disposition
  delivered|superseded|rejected [--release <id>] [--reason <text>]` — one histo
  record, refused on a second exit (`dd-release-implementation` RC-FLOW step 7).
- `dd-release-definition` consumes the picked set with no further triage — the
  backlog it reads is already sanitized.

## Done when

- Every live candidate is in `active[]` with a live token; every closed one has
  exactly one histo record.
- No entry was created outside the operator-gated intake path.
- A picked entry's SPEC exists in the same commit its `active[]` entry turned `picked`.

## References

- `dd-release-definition` — the picked-set consumer.
- Script: `python3 .agents/skills/dd-backlog-definition/scripts/backlog.py` — `new`, `exit`, `check`, and `subjects` (the declared aliases plus the document's live bindings).
- A `subject.ref` naming a code/doc/cli anchor is judged by `dadaia doctor` — `BL-SCHEMA` names the ref it cannot resolve.
