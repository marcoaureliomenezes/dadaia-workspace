---
name: dd-backlog-definition
description: >
  Use when adding, deduplicating or exiting a specs/backlog/BACKLOG.json entry, or compiling the operator intake report: backlog.py new|exit|check, staleness/dedup sanitizing and the terminal disposition vocabulary. Picking entries into a candidate is dd-release-definition's.
---

# dd-backlog-definition

> `dd-product-engineer` runs this continuously.

## The document

1. Open `specs/backlog/AGENTS.md` (the area's scoped law) and follow it.
2. Write in a `backlog` worktree (`worktrees/AGENTS.md`). Append via `python3 .agents/skills/dd-backlog-definition/scripts/backlog.py new <slug> --title "…" --description "…" --provenance "<operator words or intake item + date>" --relates <slugs>|none`; validate via `.dadaia/.venv/bin/dadaia doctor` (`ledgers`
   section).

## Continuous curation

- Re-read the whole document on every new entry.
- Dedup: compare a new entry's title+description against every ACTIVE item for the
  same subject — by domain concept, not by the request's
  wording; exit a near-duplicate as `rejected`, its `--reason` `absorbed by <existing slug>`.
- Staleness: an ACTIVE item untouched since the last closure is a
  sanitize candidate; a confirmed-invalid item exits as `rejected` with a one-line
  `reason`; a merely-postponed one stays `active[]`.

## The intake gate — the only path to a new entry

- Only the operator creates demand. An entry materializes via the main thread's
  operator-facing intake report (handoff with `next_handoff.agent: "human"` plus its
  HTML report), or via an operator-ratified in-release deferral (already counts as
  intake).
- The main thread compiles every actionable defect (review findings, closure returns, audit
  observations) into that report at each release close and review round; the operator's ruling on that report is what creates an entry.
- A record-only observation (INFO-grade, awareness-only) terminates in the
  reviewer's own findings.

## Pick and dispositions

- The pick is the SPEC's `**Origin:** backlog:<ids>` line; the entry keeps its status.
- It exits exactly once, at closure, by `python3 .agents/skills/dd-backlog-definition/scripts/backlog.py exit <slug> --disposition
  <disposition> [--release <id>] [--reason <text>]` — one histo
  record, refused on a second exit (`dd-release-implementation` RC-FLOW step 4).

## Done when

- `python3 .agents/skills/dd-backlog-definition/scripts/backlog.py check --specs <specs-dir>` exits 0 and `.dadaia/.venv/bin/dadaia doctor` prints no `BL-` finding.
- Every entry added this session names its intake item or operator words in `provenance`.

## References

- `dd-release-definition` — the picked-set consumer.
- Script: `python3 .agents/skills/dd-backlog-definition/scripts/backlog.py` — `new`, `exit` and `check`.
- A `subject.ref` naming a code/doc anchor is judged by `.dadaia/.venv/bin/dadaia doctor` — `BL-SCHEMA` names the ref it cannot resolve.
