# RC-FLOW — the state ladder (dd-release-implement)

Disclosed reference reached from `SKILL.md` §3 (T-050-21 rename; `RELEASE.json` replaces `CLOSURE.md` prose — see `RELEASE-EVENTS.md`).
Absorbs `CLOSURE-CHECKS.md`'s disposition-sweep, artifact-GC, out-of-scope and segments sections.

## Review/QA gate cadence

| Boundary | Who validates | What unlocks |
|---|---|---|
| Per task | implementer discipline only (TDD, tests, local CI preflight, handoff); marker stays `[-]` | nothing; no per-task reviewer gate |
| End of each `alpha-N` | `qa-engineer` only, `APPROVE`/`REQUEST_CHANGES` | a qa-gated commit on the branch — no push/PR/merge/closure |
| At `rc-N` ship | `qa-engineer` + `code-reviewer` + `security-reviewer`, all `APPROVE` the same commit | `[x]`; ship; deploy; close; memory update |

- Any `REQUEST_CHANGES`, CRITICAL/HIGH finding, failed E2E, or missing evidence sends the work back to implementation.
- Rework continues until every required validator approves the same commit, or the operator stops the release.
- Order (D8/FR5): review -> closure -> archive -> ship.
- The pre-PR six-axis code review runs on the thawed tree, before the `git mv` archive step — never after.

## The arc, step by step

Each step ends on a checkable criterion. Steps 8-12 are final-rc-only.
A10.3: segment closes on branch, rc-1 merges the whole scope, rc-N rounds are fixes, the final rc ships.

**Step 1 — Reserve.**
- Flip `[ ]`->`[-]` in the active `TASKS.md`, commit `chore(tasks): start <id>` (`dadaia-task-manager`).
- Done when: the reservation commit exists and no other task on the branch is `[-]`.

**Step 2 — TDD loop.**
- Implement with tests; run the local CI preflight.
- Done when: the suite is green and an `implementation-complete` handoff is emitted.

**Step 3 — Segment close (`alpha-N`).**
- Once every task in the segment is review-ready, request `qa-engineer`.
- Operative dependency: run `dd-architecture-survey` before this segment's review closes.
- `dd-architecture-survey` turns the standing "bug-history review" order into one report plus one dispositioned candidate.
- Done when: `qa-engineer` `APPROVE`s a commit; flip every reviewed task `[x]`; no push/PR/merge/closure yet.

**Step 4 — Scope-complete.**
- All segments' tasks are `[x]`.
- Done when: `TASKS.md` (or every segment's `TASKS.md`) carries zero `[ ]`/`[-]` rows.

**Step 5 — rc-1 PR.**
- Set `rc` open in `RELEASE.json` (`RELEASE-EVENTS.md`), open the `feature/{M.m.p}` -> `develop` PR for the whole scope.
- Done when: it merges (branch contract: `DADAIA.md` §4 Gitflow, `dd-gitflow-default`).

**Step 6 — rc-N rounds.**
- Fix/adjust only — never new backlog scope.
- Done when: CI is green on the round's PR and it merges.

**Step 7 — Final-rc trio review.**
- `qa-engineer` + `code-reviewer` + `security-reviewer` all `APPROVE` the same commit.
- `qa-engineer` sets the `implemented` milestone on that closed commit's sha, then closes `rc`.
- Done when: all three verdicts are `APPROVE` on that sha — only then may `[x]`/closure/merge/deploy/archive proceed.

**Step 8 — Memory update (`product-engineer`).**
- Set `phase: CLOSURE` in `RELEASE.json` (no `ACTIVE.md` mirror to keep in sync).
- Update `specs/memory/**` atoms to the product's current state — protocol detail: `MEMORY-UPDATE.md`.
- Done when: `dadaia specs doctor` reports the memory atoms clean.

**Step 9 — Record the closure narrative.**
- Append the `log` entries `RELEASE-EVENTS.md` describes (summary, size, drifts, GC, dispositions).
- `CLOSURE.md`/`CLOSURE-TEMPLATE.md` retired at T-050-21 — never write one.
- Done when: every narrative class has a `log` entry or its named native home.

**Step 10 — Disposition sweep.**
- Flip every bug/backlog item picked into (or superseded by) this release to a terminal token.
- Vocabulary/format is `dd-backlog-definition` §2.
- CONSUMED -> terminal token is an update, never a second histo record.
- This sweep rewrites the ONE `backlog_histo.jsonl` record's disposition, never appends a second one.
- A bug is never silently dropped — `dadaia bugs update` already closed it, or a superseder covers it.
- Stale/invalid backlog items get `DEFERRED`/`REJECTED` with a reason, never removed (`DADAIA.md` §6).
- Done when: `dadaia bugs stats` and `dadaia backlog doctor` show zero non-terminal picked items.

**Step 11 — Artifact GC sweep.**
- Run once step 9's narrative records are final — before the archive move, never before.
- Scope: this release's own working artifacts under `.dadaia/` only, never another release's.
- KEEP: anything a surviving `note`/handoff evidence pointer references; cross-check before deleting.
- DELETE: consumed coordination handoffs the ack-on-consume rule missed (canonical rule: `dadaia-handoff-emitter`).
- DELETE (continued): report/handoff artifacts superseded by this closure's `note` records, and scoped tmp captures.
- Lane guard (AG.1): resolve the target, refuse any target outside `.dadaia/`, never follow a symlinked directory.
- Done when: the `closure-artifact-gc` log entry states kept/deleted counts per class, with evidence.

**Step 12 — Archive.**
- `git mv specs/releases/<release-id>/ specs/releases/_archive/<release-id>/` — the whole directory, verdicts included (operator ruling 2026-08-28, `DADAIA.md` §6.2).
- Set the archived directory's `RELEASE.json` `phase: ARCHIVED`.
- Append one summary record to `releases/_archive/releases_histo.jsonl`, same commit as the `git mv`.
- Done when: `specs/releases/<release-id>/` no longer exists live, `_archive/<release-id>/RELEASE.json` carries `phase: ARCHIVED`, and the histo record exists, in the same commit as steps 8-11.

**Step 13 — Ship PR.**
- Open `develop` -> `main`; on merge, set the `shipped` milestone (`RELEASE-EVENTS.md`).
- Done when: it merges — mechanics/gate/CI: `DADAIA.md` §4 Gitflow, `dd-gitflow-default`.

**Step 14 — Post-deploy.**
- Delete `feature/{M.m.p}`; cut `feature/{next}` from `main` in the same step.
- Done when: exactly one `feature/*` branch exists, named for the next version (`dd-gitflow-default` §4).

## Test-stewardship touchpoints (reference)

- Declare test intent at birth; pass the admission filter (`dadaia-test-stewardship` §A/§B) before a test enters the suite.
- Demotion and quarantine/SCAFFOLD expiry are closure-time work (step 9's `closure-test-dispositions` log entry).

## Out of scope for closure

- Writing source code, tests, or pipelines (other agents) — the closer records test dispositions, never authors a test.
- Modifying `specs/constitution.md` (requires explicit operator approval).
- Memory updates outside CLOSURE phase (or DEFINITION under its own authorization) — gate-blocked for any other agent/phase.
- Re-opening an archived release — once archived, a new release supersedes it.

## Segments (ADR-1/ADR-5)

- When the active release carries a `segment` field, each segment closes independently.
- `RELEASE.json` stays one file per release, never one per segment.
- `TASKS.md` is the artifact that splits, under `specs/releases/<release-id>/<segment>/TASKS.md`.
- `RELEASE.json`'s `segment` field names which one is active, instead of splitting the file.
- Per ADR-3, qa-only gates an `alpha-N` (commit, no closure/ship); the full trio + closure + archive happen at the shipping `rc-N`.
- Flat releases are unchanged.
