# RELEASE-EVENTS — the `RELEASE.json` state+log contract

Disclosed reference reached from `SKILL.md`/`RC-FLOW.md` wherever the arc says "update
the release state" or "append a log entry". `specs/releases/<release-id>/RELEASE.json`
is ONE mutable JSON object — the release's current state, never an append-only event
stream (retires `RELEASE.jsonl`, `release-event-v1.schema.json`,
`core/release_events.py`). Schema:
`dadaia_workspace/public/schemas/releases/release-state-v1.schema.json`.

## Shape

`{schema, release, phase, rc, defined, implemented, shipped, audited, segment?, log[]}`
`phase`, `rc`, `segment` are rewritten in place on every transition — no history of
prior values survives in the field itself; a transition worth remembering becomes a
`log` entry. `defined`/`implemented`/`shipped`/`audited` are the four sha-bearing
milestone facts, each set at most once meaningfully (a later legitimate rewrite is a
correction, not a duplicate) or `null` before that point. `log` is the one append-only
array inside the document — oldest first, never rewritten once appended.

## Who sets which milestone

| Milestone | Set by | Shape |
|---|---|---|
| `phase` | whoever drives the transition (`product-engineer` at DEFINITION/CLOSURE, the first implementer at IMPLEMENTATION) | phase string |
| `defined` | `product-engineer`, at the definition promotion commit | `{sha, ts}` |
| `implemented` | `qa-engineer`, at final-`rc` QA close, on the closed commit's sha — not the merge commit (D3) | `{sha, rc, ts}` |
| `shipped` | `project-manager` (or whoever merges the ship PR) | `{sha, pr, ts}` |
| `audited` | `project-auditor`, the same atomic rewrite that sets a bug's `resolved_commit`/`audited` | `{sha, ts, audit}` |

## `log` — the retired `CLOSURE.md` narrative's home

Every closure-narrative class (summary, size accounting, drifts, artifact-GC, test
dispositions) lands as one `log` entry, `kind` naming the class. Already-native classes
need no entry: dispositions (`backlog_histo.jsonl`/`BUGS.jsonl`'s `resolved_release`),
tasks completed (`TASKS.md` `[x]` + sha), validations (trio `APPROVE` handoffs), memory
updates (the atom diffs themselves).

## Write seam

A code path rewrites the milestone fields through `core/atomic_write.py`'s CAS seam
(refuse-stale); an agent with file tools may Read-then-Edit directly, same discipline.
Parser: `core/release_state.py` (no file I/O).
