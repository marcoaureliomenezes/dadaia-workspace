---
name: dd-release-implement
description: "Use when: implementing an Aprovado release's TASKS.md — reserving a task, the TDD loop, deciding what a review boundary unlocks, or the push checkpoint. Owns the Review/QA gate-cadence table and the decision procedure for what a task+segment state permits or forbids. The implementers' operational reference."
applyTo: "specs/releases/*/TASKS.md"
---

# dd-release-implement

> **Not a hook-enforced mechanism.** No engine advances gates or reads `TASKS.md`.
> Every boundary below holds because implementers and reviewers uphold it; the git
> chokepoints (`DADAIA.md` §3) are the only mechanical backstop.

## 1. When to invoke

Any implementer (`software-engineer`, `ai-engineer`, `qa-engineer`) working a task inside
an `Aprovado` release, from the first reservation through the ship push.

## 2. Resolve release and segment

Read `specs/releases/ACTIVE.md` (schema v2): `release:`, optional `segment:`
(`alpha-N`/`rc-N`), `phase:`. A `segment:` present means `TASKS.md` lives at
`releases/<release-id>/<segment>/TASKS.md`; otherwise at `releases/<release-id>/TASKS.md`.
Full navigation protocol: `dadaia-workspace-spec-navigator`.

## 3. Reserve → TDD loop

Flip `[ ]`→`[-]`, commit `chore(tasks): start <id>`, do the work, flip `[-]`→`[x]` only
after review clears (§4). Full marker discipline, recovery cases and the gate's block
reasons: `dadaia-task-manager` — referenced here, not restated.

## 4. Which review boundary applies now

**Order (D8/FR5): review → closure → archive → ship.** The pre-PR six-axis code review
of the delta runs on the thawed tree, before the `git mv` archive step — never after;
only ship steps (merge to `develop`, diff security review, push, PR to `main`) follow
archive. `dd-release-closure`'s finalization paragraph states the same order.

Given "I am inside task T-N of `<segment>`", resolve top-to-bottom — the first matching
row is the answer:

| State | Permitted now | Forbidden until the next gate clears |
|---|---|---|
| Task `[-]`, tests green, no alpha-close yet | Keep working; local commits; push implementation commits to `feature/{M.m.p}` | Mark `[x]`; PR; merge; write CLOSURE |
| All of `alpha-N`'s tasks review-ready, `qa-engineer` not yet `APPROVE` | Request the qa-engineer review | Push `develop`; merge; CLOSURE; `[x]` on any task in this alpha |
| `qa-engineer` `APPROVE`d this `alpha-N` | Mark `[x]`; commit the qa artifact on the branch | Push `develop`, PR, merge, deploy, close — only `rc-N` ship unlocks those |
| `rc-N` ship elected, not all three of qa/code/security `APPROVE`d the **same** commit | Rework loop; resubmit | Merge to `develop`; push; open PR; deploy; close |
| `rc-N` ship, all three `APPROVE`d the same commit (review cleared) | Mark `[x]`; memory update + `CLOSURE.md` + archive (`dd-release-closure`); merge to `develop` (milestone b); diff security review; push; open PR `develop`→`main`; merge | — |

The **Review/QA gate cadence** (source of the table above, canonical home — this table
exists nowhere else in `public/`):

| Boundary | Who validates | What unlocks |
|---|---|---|
| Per task | implementer discipline only — TDD, unit/integration tests, pre-push CI, `implementation-complete` handoff; marker stays `[-]` | nothing; no per-task reviewer gate |
| End of each `alpha-N` | `qa-engineer` only, `APPROVE`/`REQUEST_CHANGES` | a qa-gated commit on the branch — no push/PR/merge/CLOSURE |
| At `rc-N` ship | `qa-engineer` + `code-reviewer` + `security-reviewer`, all `APPROVE` the same commit | `[x]`; merge to `develop` (milestone b); diff review; push; PR to `main`; merge; deploy; close; CLOSURE/memory |

Any `REQUEST_CHANGES`, CRITICAL/HIGH finding, failed E2E, or missing evidence sends the
work back to implementation; rework continues until every required validator approves
the same commit or the operator stops the release.

## 5. Push checkpoint (reference)

Branch, merge-milestone and push mechanics: `dd-gitflow-default`. After every push or PR,
watch CI to green — read the failing log, fix the cause, push again, keep watching.

## 6. Test-stewardship touchpoints (reference)

Declare test intent at birth and pass the admission filter before a test enters the
permanent suite: `dadaia-test-stewardship` §A/§B. Demotion and quarantine/SCAFFOLD
expiry are closure-time work (`dd-release-closure`), not this skill's.

## 7. Checklist

- [ ] Release + segment resolved from `ACTIVE.md`.
- [ ] Task reserved (`[-]`) with an isolated `chore(tasks): start <id>` commit.
- [ ] §4's current-state row identified before attempting any unlock action.
- [ ] Push checkpoint passed (CI green, security verdict current) before any push.
- [ ] Test intents declared; admission filter satisfied for every new test.
