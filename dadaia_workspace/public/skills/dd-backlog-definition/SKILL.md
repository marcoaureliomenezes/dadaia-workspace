---
name: dd-backlog-definition
description: >
  Use when: curating specs/backlog/**, sanitizing for staleness, adjudicating an intake
  report, or checking the terminal disposition-token vocabulary. Owns the BACKLOG.json
  single-source active[] schema plus backlog_histo.jsonl, and the operator-gated intake
  gate — the only path to a new backlog entry. project-manager runs this continuously.
tldr: "Curate BACKLOG.json continuously; sanitize/dedup; only operator-gated intake creates a new entry; never delete."
applyTo: "specs/backlog/**"
---

# dd-backlog-definition

> Not hook-enforced. `project-manager` runs this protocol continuously; this skill is its authoritative source.

## 1. When

- `project-manager`, continuously — not a release-boundary event.
- Any time a backlog file is touched, an intake report is compiled, or release-definition needs the picked set.

## 2. Steps

1. Treat `specs/backlog/BACKLOG.json` as the single source: `{schema: "backlog-v1", active: [...]}` — no per-entry files.
2. Write a closed item's history to `specs/backlog/_archive/backlog_histo.jsonl` — one append-only record per exit.
3. Add an `active[]` entry with the required fields: `id`, `title`, `opened`, `status` (idea|candidate), `description`, `provenance`.
- **Status:** idea | candidate — a live (non-terminal) token; a terminal disposition token belongs to a `backlog_histo.jsonl` record instead.
4. Never write a terminal disposition token into `active[]` — that belongs to a `backlog_histo.jsonl` record.
5. Leave `intents[]` optional at `status: idea`; require it at `candidate`+ (a missing one is BL-SCHEMA, not a warning).
6. Append via `dadaia backlog new <slug>`; validate the document via `dadaia backlog doctor` (BL-SCHEMA/CONFLICT/STALE).
7. Scan for staleness: an `ACTIVE` item with no reads/updates past a reasonable window is a sanitize candidate.
8. Scan for dedup: compare a new entry's title+description against every `ACTIVE` item for the same subject before adding.
9. Merge a near-duplicate into the existing entry — never file it twice.
10. Disposition a confirmed-stale/invalid item to `DEFERRED`/`REJECTED` with a one-line reason, exited to the histo file.
11. Re-read the whole document on every new entry — `BACKLOG.json` is small enough that partial review is a discipline failure.
12. Never delete a backlog file or bug — move `active[]` -> `backlog_histo.jsonl`; the histo file itself is append-only.
13. Never write a technical residual (review finding, closure return, audit observation) directly into `BACKLOG.json`.
14. Compile every actionable defect into an operator-facing intake report at each release close and review round.
15. Skip re-adjudication for an operator-ratified deferral already recorded at approval time (pre-approved intake).
16. Terminate a record-only observation (INFO-grade, awareness-only) in the reviewer's own findings — never into an intake report.
17. Emit the intake report as the existing handoff-first shape: JSON handoff with `next_handoff.agent: "human"` plus its HTML report.
18. Purge on pick: exit a picked entry from `ACTIVE` in the same commit that creates the release SPEC.
19. Update a provisional `CONSUMED` in place at closure — never a second histo record for the same slug.

## 3. Done when

- Every live candidate is in `active[]` with a live status token, every closed one has exactly one histo record.
- No backlog entry was created outside the operator-gated intake path (or a pre-approved deferral).
- A picked entry's SPEC exists in the same commit its `active[]` entry is purged.

## 4. References

- Schema: `dadaia_workspace/public/schemas/backlog/backlog-v1.schema.json`.
- Terminal tokens — backlog (`backlog_histo.jsonl` `disposition`): `DELIVERED`, `SUPERSEDED`, `RESOLVED`, `CONSUMED`, `DEFERRED`, `REJECTED`.
- Terminal tokens — bug (`BUGS.jsonl` `status`): `resolved`, `superseded`, `deferred`, `rejected` (`open` is the only non-terminal value).
- `dd-release-implement` (`RC-FLOW.md` step 10) — the disposition-sweep executor at closure.
- `dd-release-definition` — the picked-set consumer, reads `active[]` with no further triage.
- `DADAIA.md` §6 (Backlog) — never-delete law, operator-gated intake doctrine.
- CLI: `dadaia backlog new <slug>`, `dadaia backlog doctor`, `dadaia backlog subjects`, `dadaia bugs status`, `dadaia bugs stats`.
- Exiting an item has no CLI verb yet — do it with file tools directly (ADDITIVE path, `DADAIA.md` §3).
