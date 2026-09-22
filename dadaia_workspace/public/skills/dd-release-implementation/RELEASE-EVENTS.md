# RELEASE-EVENTS — the `_RELEASE.json` state+log contract

Disclosed reference reached from `SKILL.md`/`RC-FLOW.md` wherever the arc says "update the release state" or "append a log entry".

- `specs/releases/<release-id>/_RELEASE.json` is ONE mutable JSON object — the release's current state, never an append-only event stream.
- Schema: `dadaia_workspace/public/schemas/releases/release-state-v1.schema.json`.

## Shape

- Fields, all seven required: `{schema, release, phase, defined, implemented, shipped, log[]}`.
- An audit is not a release milestone; the audit window is read from `audits/_archive/audits_histo.jsonl`.
- `phase` is one of `DEFINITION IMPLEMENTATION CLOSURE ARCHIVED` — nothing else validates.
- `phase` is rewritten in place on every transition — no history of prior values survives in the field.
- A transition worth remembering becomes a `log` entry.
- `defined`/`implemented`/`shipped` are the three sha-bearing milestone facts.
- Each milestone is set at most once meaningfully (a later legitimate rewrite is a correction, not a duplicate), or `null` before that point.
- `log` is the one append-only array inside the document — oldest first, never rewritten once appended; each entry is `{ts, agent, kind, text}`.
- `kind` is one of `note summary size drifts dispositions test-dispositions artifact-gc reviews merge memory`.

## Who sets which milestone

| Milestone | Set by | Shape |
|---|---|---|
| `phase` + `defined` | `python3 .agents/skills/dd-release-implementation/scripts/release.py phase IMPLEMENTATION --sha <sha>` | phase string, `{sha, ts}` |
| `phase` + `implemented` | `python3 .agents/skills/dd-release-implementation/scripts/release.py phase CLOSURE --sha <sha> [--pr <n>]` | phase string, `{sha, ts}` |
| `phase: DEFINITION` | `python3 .agents/skills/dd-release-implementation/scripts/release.py new <id>` | phase string |
| `phase: ARCHIVED` | no verb writes it — it describes history only |


## `log` — the closure narrative's home

- Every closure-narrative class lands as one `log` entry whose `kind` names it — `summary`, `size`, `drifts`, `artifact-gc`, `test-dispositions`, `dispositions`, `memory`, `reviews`, `merge`.
- The `memory` entry is written only by `release.py memory`; it adds `since`, `reviewed`, `changed` to `{ts, agent, kind, text}` — the drift window sha, the atoms read and left byte-identical, the atoms rewritten or created; `dispositions` records the sweep.
- Already-native facts need no entry: tasks completed (`TASKS.md` `[x]` + sha) and the trio `APPROVED` handoffs.

## Write seam

- `phase` and the three milestones move by verb only.
- `log` entries are Read-then-Edit by the agent that owns the narrative.
