# RELEASE-EVENTS — the `_RELEASE.json` state contract

Disclosed reference reached from `SKILL.md`/`RC-FLOW.md` whenever the arc updates
release state.

## Shape

- `specs/releases/<release-id>/_RELEASE.json` is one mutable object with the seven
  required fields `{schema, release, phase, defined, implemented, shipped, log}`.
- `phase` takes its lifecycle value from the
  release-state schema (`.dadaia/agentic/schemas/releases/release-state-v1.schema.json`) and is
  overwritten on a transition. `defined`, `implemented` and `shipped` are the
  sha-bearing facts.
- `log` is append-only, oldest first. Every entry carries `{ts, agent, kind, text}`.
  The schema retains legacy kinds so archived and earlier-candidate history stays
  readable. From the live candidate's birth onward, `release.py check` accepts only
  `note`, `milestone`, `summary` and `memory`.

## Current entries

| Kind | Writer | Completion criterion |
|---|---|---|
| `note` | `release.py new`, or the agent recording an operator authorization verbatim | The entry holds one fact that belongs to no typed entry. |
| `milestone` | `release.py phase` | `{candidate, milestone, sha}` matches the transition. |
| `summary` | the closer, Read-then-Edit | Its text contains `delivered: …; carried: …; backlog exits: …`. |
| `memory` | `release.py memory` | It is the one closure entry and carries `{since, until, reviewed, changed}`. |

`memory` is closure-only. A rerun at the same HEAD appends nothing. `release.py check`
requires one memory entry at or after `implemented.ts` and reads no git to validate that
fact; `release.py drift` remains the worklist command used before the entry is written.

An open bug blocks `ship` by default. A carried bug needs all three facts: one
`--allow-open <id>` flag per open id, a `kind: note` starting `Operator authorization verbatim:` and naming that id, and the id in the summary's `carried` field. The bug
stays open.

## Milestones

| Milestone | Command | Written shape |
|---|---|---|
| candidate birth | `release.py new <id>` | `phase: DEFINITION` plus a `note` |
| definition | `release.py phase IMPLEMENTATION --sha <sha>` | `defined: {sha, ts}` plus a `milestone` |
| implementation | `release.py phase CLOSURE --sha <sha>` | `implemented: {sha, ts}` plus a `milestone` |
| ship | `release.py ship --sha <sha> [--pr <n>]` | `shipped: {sha, pr, ts}`, then archive |

Historical log
entries are read, never rewritten to the lean vocabulary.
