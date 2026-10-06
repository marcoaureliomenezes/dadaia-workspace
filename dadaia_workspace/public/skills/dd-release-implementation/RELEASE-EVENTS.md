# RELEASE-EVENTS — the `_RELEASE.json` state+log contract

Disclosed reference reached from `SKILL.md`/`RC-FLOW.md` wherever the arc says "update the release state" or "append a log entry".

- `specs/releases/<release-id>/_RELEASE.json` is ONE mutable JSON object — the release's current state, never an append-only event stream.
- Schema: `dadaia_workspace/public/schemas/releases/release-state-v1.schema.json`.

## Shape

- Fields, all seven required: `{schema, release, phase, defined, implemented, shipped, log[]}`.
- An audit is not a release milestone; the audit window is read from `audits/_archive/audits_histo.jsonl`.
- `phase` holds one value of the schema's `phase` enum (`release.py check` validates it).
- `phase` is rewritten in place on every transition — no history of prior values survives in the field.
- A transition worth remembering becomes a `log` entry.
- `defined`/`implemented`/`shipped` are the three sha-bearing milestone facts.
- `defined`/`implemented` hold the live candidate's stamp; each `phase` also appends a `kind: milestone` entry `{candidate, milestone, sha}`, the per-candidate history. Stamps older than these entries are the `Candidate defined at …`/`Candidate implemented at …` notes.
- `log` is the one append-only array inside the document — oldest first, never rewritten once appended; each entry is `{ts, agent, kind, text}`.
- `kind` is one of `note summary size drifts dispositions test-dispositions artifact-gc reviews merge memory milestone`.
- `release.py check` judges every phase: under DEFINITION, a closure entry after the candidate's birth note is a finding (a job's `kind: merge` entry is not one); every job file is judged (`dd-release-definition` §5).
- A merged job appends one `kind: merge` entry, Read-then-Edit (no verb writes it), text `job: <name>; start: <UTC>; end: <UTC>; wall: <min>; ritual_wait: <min>; dispatches: <n>; job_gate_runs: <n>` — `start` the committer time of the job branch's first commit, `end` the committer time of the merge that lands it; `release.py check` validates the shape.

## Who sets which milestone

| Milestone | Set by | Shape |
|---|---|---|
| `phase` + `defined` | `python3 .agents/skills/dd-release-implementation/scripts/release.py phase IMPLEMENTATION --sha <sha>` | phase string, `{sha, ts}` |
| `phase` + `implemented` | `python3 .agents/skills/dd-release-implementation/scripts/release.py phase CLOSURE --sha <sha>` | phase string, `{sha, ts}` |
| `phase: DEFINITION` | `python3 .agents/skills/dd-release-implementation/scripts/release.py new <id>` | phase string |
| `shipped`, then the directory moves to `_archive/<v>/` | `python3 .agents/skills/dd-release-implementation/scripts/release.py ship --sha <sha> --pr <n>`, refused on any `check` error | `{sha, pr, ts}` (`check` verifies it from 0.5.0 on) + one `delivered` histo line, `summary` null |


## `log` — the closure narrative's home

- Every closure-narrative class lands as one `log` entry whose `kind` names it — `summary`, `size`, `drifts`, `artifact-gc`, `test-dispositions`, `dispositions`, `memory`, `reviews`, `merge`.
- The `memory` entry is written only by `release.py memory`; it adds `since`, `until`, `reviewed`, `changed` to `{ts, agent, kind, text}` — the ledger-derived window (previous entry's `until`, else `defined.sha`) and the HEAD it closed at, the atoms read and left byte-identical, the atoms rewritten or created; `dispositions` records the sweep.
- Already-native facts need no entry: tasks completed (their commits, under their ids) and the `APPROVED` handoffs.

## Write seam

- `phase` and the three milestones move by verb only.
- `log` entries are Read-then-Edit by the agent that owns the narrative.
