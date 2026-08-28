---
name: dd-release-implement
description: "Use when: implementing a release from the first task reservation through the final-rc ship — the whole implement-to-close arc under the v2/rc segment model. Short SKILL-plus-disclosed-siblings shape (T-050-21, FR12): RC-FLOW.md (state ladder + gate cadence), RELEASE-EVENTS.md (RELEASE.json state+log contract), MEMORY-UPDATE.md (closure memory protocol). CLOSURE.md/CLOSURE-TEMPLATE.md retired — the closure narrative now lives in RELEASE.json's log."
applyTo: "specs/releases/*/TASKS.md"
---

# dd-release-implement

> **Not a hook-enforced mechanism.** No engine advances gates, drives closure, or reads
> `TASKS.md`. Every boundary holds because implementers, reviewers and
> `product-engineer` uphold it directly; the git chokepoints (`DADAIA.md` §3) are the
> only mechanical backstop.

## 1. When to invoke

Any implementer (`software-engineer`, `ai-engineer`, `qa-engineer`) working a task inside
an `Aprovado` release, and `product-engineer` at the final-rc closure — from the first
reservation through the ship PR and the post-deploy branch cut.

## 2. Resolve release and segment

Resolve the active release and phase by reading **`RELEASE.json`** directly — the live
release's `specs/releases/<release-id>/RELEASE.json`, a mutable state document (no fold:
`phase` is a plain top-level field; parser: `core/release_state.py`) — the SDD gate
itself reads this same field; `ACTIVE.md` retired at T-050-21A, no replacement file. A
`segment` field present means `TASKS.md` lives at
`releases/<release-id>/<segment>/TASKS.md`; otherwise at `releases/<release-id>/TASKS.md`.
Full navigation protocol: `dadaia-workspace-spec-navigator`.

## 3. The state ladder, the gate cadence, and the 14-step arc

Disclosed sibling: **`RC-FLOW.md`** — the review/QA gate cadence table, the full
step-by-step arc (reserve → TDD → segment close → scope-complete → rc rounds →
final-rc trio → memory update → closure narrative → disposition sweep → artifact GC →
archive → ship → post-deploy), the `dd-architecture-survey` operative pointer at
segment close, the out-of-scope list, and the segments rule. Read it before acting on
any step past reservation.

## 4. Updating `RELEASE.json`

Disclosed sibling: **`RELEASE-EVENTS.md`** — the state document's shape, who sets which
milestone, and the `log` conventions that now carry the retired `CLOSURE.md`'s narrative
content (summary, size accounting, drifts, artifact GC, test dispositions) — everything
else (dispositions, record-only observations, intake candidates, tasks-completed,
validations, memory updates) already has a **native** home and needs no `log` entry at
all; see that file's conversion table.

## 5. Memory update at closure (step 8 of the arc)

Disclosed sibling: **`MEMORY-UPDATE.md`** — the full protocol `product-engineer` runs
at `RC-FLOW.md` step 8: gate-phase verification, atom update rules, the forbidden
history/changelog sections, and the folder-catalog shape.

## 6. Test-stewardship touchpoints (reference)

Declare test intent at birth and pass the admission filter before a test enters the
permanent suite: `dadaia-test-stewardship` §A/§B. Demotion and quarantine/SCAFFOLD
expiry are closure-time work (`RC-FLOW.md` step 9's `closure-test-dispositions` log
entry), not earlier steps'.

## Checklist

- [ ] Release + segment resolved by reading `RELEASE.json` directly.
- [ ] Task reserved (`[-]`) with an isolated `chore(tasks): start <id>` commit.
- [ ] Current step (`RC-FLOW.md`) identified before attempting its unlock action.
- [ ] CI green before any push; trio `APPROVE`d before any final-rc unlock action.
- [ ] At final rc: memory update → closure narrative (`RELEASE-EVENTS.md` log entries) →
      disposition sweep → artifact GC → archive, one commit, in that order, before the
      ship PR.
