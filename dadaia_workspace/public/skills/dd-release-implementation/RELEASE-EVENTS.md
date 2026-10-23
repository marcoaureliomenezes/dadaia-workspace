# RELEASE-EVENTS — the `_RELEASE.json` state contract

Disclosed reference reached from `SKILL.md`/`RC-FLOW.md` whenever the arc updates
release state.

## Shape

- `specs/releases/<release-id>/_RELEASE.json` is one mutable object; its fields are those of `.agents/skills/dd-release-implementation/scripts/schemas/release-state-v1.schema.json`.
- `phase` takes its lifecycle value from that schema and is overwritten on a transition.
- `log` is append-only, oldest first. Every entry carries `{ts, agent, kind, text}`.
  The schema retains legacy kinds so archived and earlier-candidate history stays
  readable. From the live candidate's birth onward, `release.py check` accepts only
  `note`, `milestone`, `summary` and `memory`.

## Current entries

| Kind | Writer | Completion criterion |
|---|---|---|
| `note` | `release.py new`, or the agent recording an operator authorization verbatim | The entry holds one fact that belongs to no typed entry. |
| `milestone` | `release.py phase` | `{candidate, milestone}` matches the transition. |
| `summary` | `dd-product-engineer`, Read-then-Edit | `release.py check` fullmatches its text, one line, against `delivered: …; carried: …; backlog exits: …`; each field is non-empty, `none` standing for an empty one. The last one at or after `defined.ts` is the closure summary. |
| `memory` | `release.py memory` | The latest `memory` entry governs and carries `{since, until, reviewed, changed}`. |

`memory` is closure-only. A rerun at the same HEAD appends nothing. `release.py check`
requires a memory entry at or after `implemented.ts` and reads no git to validate that
fact; `release.py drift` remains the worklist command used before the entry is written.

An open bug blocks `ship` by default. A carried bug needs all three facts: one
`--allow-open <id>` flag per open id, a `kind: note` starting `Operator authorization verbatim:` and naming that id, and the id in the summary's `carried` field. The bug
stays open.

## Milestones

A milestone or memory-window bound is found from its commit subject line, as a fix is (`specs/bugs/AGENTS.md` §Resolution); a stored sha is a hint a history rewrite can orphan. The subject is `chore(release): rc-<N> (phase|enters) <PHASE>`, optionally followed by more words, on a commit touching the release's own folder: `release.py phase` prints the `phase` form to commit, and both forms are read. The memory pass is `chore(release): rc-<N> memory pass recorded`.

| Milestone | Command | Written shape |
|---|---|---|
| candidate birth | `release.py new <id>` | `phase: DEFINITION` plus a `note` |
| definition | `release.py phase IMPLEMENTATION` | `defined: {ts}` plus a `milestone` |
| implementation | `release.py phase CLOSURE` | `implemented: {ts}` plus a `milestone` |
| ship | `release.py ship [--pr <n>]` | `shipped: {pr, ts}`, then archive |
