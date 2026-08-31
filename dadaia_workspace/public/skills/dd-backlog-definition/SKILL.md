---
name: dd-backlog-definition
description: >
  Curate specs/backlog: the BACKLOG.json active[] document, staleness/dedup
  sanitizing, the operator-gated intake report (the only path to a new entry), and
  the terminal disposition vocabulary. Use when touching a backlog file, compiling an
  intake report, or handing release-definition its picked set.
---

# dd-backlog-definition

> `project-manager` runs this continuously — not a release-boundary event.

## The document

- `specs/backlog/BACKLOG.json` is the single source: `{schema: "backlog-v1",
  active: [...]}` — no per-entry files; schema:
  `dadaia_workspace/public/schemas/backlog/backlog-v1.schema.json`.
- Append via `dadaia backlog new <slug>`; validate via `dadaia backlog doctor`
  (BL-SCHEMA/CONFLICT/STALE).
- Required fields per entry: `id`, `title`, `opened`, `status`, `description`,
  `provenance`.
- **Status:** idea | candidate | picked — live (non-terminal) tokens only; a
  terminal disposition token belongs to a `backlog_histo.jsonl` record instead.
- `intents[]` is optional at `idea`, required from `candidate` on — every subject
  bound to a canonical anchor (`dadaia backlog subjects`).
- A closed item exits `active[]` into one append-only
  `specs/backlog/_archive/backlog_histo.jsonl` record — never deleted, never two
  records for one slug. Terminal tokens: `DELIVERED`, `SUPERSEDED`, `RESOLVED`,
  `CONSUMED`, `DEFERRED`, `REJECTED` (a live status token never appears in the
  histo, a terminal token never in `active[]`).

## Continuous curation

- Re-read the whole document on every new entry — it is small enough that partial
  review is a discipline failure.
- Dedup: compare a new entry's title+description against every ACTIVE item for the
  same subject; merge a near-duplicate into the existing entry.
- Staleness: an ACTIVE item with no reads/updates past a reasonable window is a
  sanitize candidate; disposition a confirmed-stale/invalid item to
  `DEFERRED`/`REJECTED` with a one-line reason.

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

- A picked entry exits `active[]` in the same commit that creates the release SPEC
  (purge-on-pick, `DADAIA.md` §6.6), leaving a provisional `CONSUMED` histo record.
- At closure, `dd-release-implement`'s disposition sweep rewrites that record in
  place to its terminal token.
- `dd-release-definition` consumes the picked set with no further triage — the
  backlog it reads is already sanitized.

## Done when

- Every live candidate is in `active[]` with a live token; every closed one has
  exactly one histo record.
- No entry was created outside the operator-gated intake path.
- A picked entry's SPEC exists in the same commit its `active[]` entry was purged.

## References

- `DADAIA.md` §6.6 — the backlog law this skill operates.
- `dd-release-definition` — the picked-set consumer.
- CLI: `dadaia backlog new`, `dadaia backlog doctor`, `dadaia backlog subjects`;
  exiting an item has no CLI verb — use file tools directly (ADDITIVE path).
