---
name: dd-release-implement
description: "Use when: implementing a release from the first task reservation through the final-rc ship — the whole implement-to-close arc under the v2/rc segment model. Covers TDD reservation, alpha/segment close (qa-only), rc-1 through rc-N, and the final-rc closure (memory update, CLOSURE.md, disposition sweep, artifact GC, archive) before the develop-to-main ship PR."
applyTo: "specs/releases/*/TASKS.md"
---

# dd-release-implement

> **Not a hook-enforced mechanism.** No engine advances gates, drives closure, or reads
> `TASKS.md`. Every boundary below holds because implementers, reviewers and
> `product-engineer` uphold it directly; the git chokepoints (`DADAIA.md` §3) are the
> only mechanical backstop.

## 1. When to invoke

Any implementer (`software-engineer`, `ai-engineer`, `qa-engineer`) working a task inside
an `Aprovado` release, and `product-engineer` at the final-rc closure — from the first
reservation through the ship PR and the post-deploy branch cut.

## 2. Resolve release and segment

Read `specs/releases/ACTIVE.md` (schema v2): `release:`, optional `segment:`
(`alpha-N`/`rc-N`), `phase:`. A `segment:` present means `TASKS.md` lives at
`releases/<release-id>/<segment>/TASKS.md`; otherwise at `releases/<release-id>/TASKS.md`.
Full navigation protocol: `dadaia-workspace-spec-navigator`.

## Review/QA gate cadence (canonical home — this table exists nowhere else in `public/`)

| Boundary | Who validates | What unlocks |
|---|---|---|
| Per task | implementer discipline only — TDD, unit/integration tests, local CI preflight, `implementation-complete` handoff; marker stays `[-]` | nothing; no per-task reviewer gate |
| End of each `alpha-N` | `qa-engineer` only, `APPROVE`/`REQUEST_CHANGES` | a qa-gated commit on the branch — no push/PR/merge/CLOSURE |
| At `rc-N` ship | `qa-engineer` + `code-reviewer` + `security-reviewer`, all `APPROVE` the same commit | `[x]`; ship; deploy; close; CLOSURE/memory |

Any `REQUEST_CHANGES`, CRITICAL/HIGH finding, failed E2E, or missing evidence sends the
work back to implementation; rework continues until every required validator approves
the same commit or the operator stops the release.

**Order (D8/FR5): review → closure → archive → ship.** The pre-PR six-axis code review
of the delta runs on the thawed tree, before the `git mv` archive step — never after;
only ship steps follow archive.

## 3. The arc, step by step

Each step ends on a checkable criterion. Steps 8–12 are final-rc-only — the rc round
where the trio approves and the release ships (A10.3: segment closes on branch, rc-1
merges the whole scope, rc-N rounds are fixes, the final rc ships).

1. **Reserve.** Flip `[ ]`→`[-]` in the active `TASKS.md`, commit
   `chore(tasks): start <id>` (`dadaia-task-manager`). *Done when:* the reservation
   commit exists and no other task on the branch is `[-]`.
2. **TDD loop.** Implement with tests; run the local CI preflight. *Done when:* the
   suite is green and an `implementation-complete` handoff is emitted.
3. **Segment close (`alpha-N`).** Once every task in the segment is review-ready,
   request `qa-engineer`. *Done when:* `qa-engineer` `APPROVE`s a commit on the branch —
   flip every reviewed task `[x]`; no push/PR/merge/CLOSURE yet.
4. **Scope-complete.** All segments' tasks are `[x]`. *Done when:* `TASKS.md` (or every
   segment's `TASKS.md`) carries zero `[ ]`/`[-]` rows.
5. **rc-1 PR.** Open the `feature/{M.m.p}` → `develop` PR carrying the whole scope.
   *Done when:* it merges (branch contract: `DADAIA.md` §4 Gitflow, `dd-gitflow-default`).
6. **rc-N rounds.** Fix/adjust only — never new backlog scope. *Done when:* CI is green
   on the round's `feature/{M.m.p}` → `develop` PR and it merges.
7. **Final-rc trio review.** `qa-engineer` + `code-reviewer` + `security-reviewer` all
   `APPROVE` the same commit. *Done when:* all three verdicts are `APPROVE` on that sha —
   only then may `[x]`, CLOSURE, merge, deploy, or close proceed.
8. **Memory update (`product-engineer`).** Set `ACTIVE.md` phase to `CLOSURE`, update
   `specs/memory/**` atoms to the product's current state. Protocol detail:
   `CLOSURE-CHECKS.md` §1. *Done when:* `dadaia specs doctor` reports the memory atoms
   clean.
9. **Write `CLOSURE.md`.** Copy `CLOSURE-TEMPLATE.md` (sibling) to
   `specs/releases/<release-id>/CLOSURE.md`; fill every section. *Done when:* every
   template section is filled or explicitly marked n/a with a reason.
10. **Disposition sweep.** Flip every bug/backlog item picked into (or superseded by)
    this release to a terminal token — including the CONSUMED→DELIVERED **update**, never
    a duplicate `## LEDGER` line (BL-DUP). Rule: `CLOSURE-CHECKS.md` §2. *Done when:*
    every picked item has exactly one terminal `LEDGER` line with evidence.
11. **Artifact GC sweep.** Run only after `## Validations`/`## Dispositions` evidence
    pointers are final. Keep/delete rule and lane guard: `CLOSURE-CHECKS.md` §3. *Done
    when:* `CLOSURE.md`'s `## Artifact GC sweep` table records kept/deleted counts.
12. **Archive.** `git mv specs/releases/<release-id> specs/_archive/releases/<release-id>`;
    point `ACTIVE.md` at the next release or `release: none`. *Done when:* the release
    directory is under `_archive/` and `ACTIVE.md` is repointed, in the same commit as
    steps 8–11 (memory → CLOSURE → sweep → archive, one commit).
13. **Ship PR.** Open `develop` → `main`. *Done when:* it merges — mechanics, the
    security-verdict PR gate, and CI: `DADAIA.md` §4 Gitflow, `dd-gitflow-default`.
14. **Post-deploy.** Delete `feature/{M.m.p}`; cut `feature/{next}` from `main` in the
    same step. *Done when:* exactly one `feature/*` branch exists, named for the next
    version — full rule: `dd-gitflow-default` §4 (not restated here).

## 4. Test-stewardship touchpoints (reference)

Declare test intent at birth and pass the admission filter before a test enters the
permanent suite: `dadaia-test-stewardship` §A/§B. Demotion and quarantine/SCAFFOLD
expiry are closure-time work (step 10, `CLOSURE-CHECKS.md` §4), not earlier steps'.

## Checklist

- [ ] Release + segment resolved from `ACTIVE.md`.
- [ ] Task reserved (`[-]`) with an isolated `chore(tasks): start <id>` commit.
- [ ] Current step (§3) identified before attempting its unlock action.
- [ ] CI green before any push; trio `APPROVE`d before any final-rc unlock action.
- [ ] At final rc: memory → CLOSURE → disposition sweep → artifact GC → archive, one
      commit, in that order, before the ship PR.
