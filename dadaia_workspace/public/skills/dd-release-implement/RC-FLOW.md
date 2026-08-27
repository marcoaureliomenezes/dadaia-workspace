# RC-FLOW — the state ladder (dd-release-implement)

Disclosed reference reached from `SKILL.md` §3. Absorbs `CLOSURE-CHECKS.md`'s
disposition-sweep, artifact-GC, out-of-scope and segments sections (T-050-21 rename;
content unchanged in substance except where the RELEASE.jsonl fold replaces `CLOSURE.md`
prose — see `RELEASE-EVENTS.md`'s conversion table).

## Review/QA gate cadence

| Boundary | Who validates | What unlocks |
|---|---|---|
| Per task | implementer discipline only — TDD, unit/integration tests, local CI preflight, `implementation-complete` handoff; marker stays `[-]` | nothing; no per-task reviewer gate |
| End of each `alpha-N` | `qa-engineer` only, `APPROVE`/`REQUEST_CHANGES` | a qa-gated commit on the branch — no push/PR/merge/closure |
| At `rc-N` ship | `qa-engineer` + `code-reviewer` + `security-reviewer`, all `APPROVE` the same commit | `[x]`; ship; deploy; close; memory update |

Any `REQUEST_CHANGES`, CRITICAL/HIGH finding, failed E2E, or missing evidence sends the
work back to implementation; rework continues until every required validator approves
the same commit or the operator stops the release.

**Order (D8/FR5): review → closure → archive → ship.** The pre-PR six-axis code review
of the delta runs on the thawed tree, before the `git mv` archive step — never after;
only ship steps follow archive.

## The arc, step by step

Each step ends on a checkable criterion. Steps 8–12 are final-rc-only — the rc round
where the trio approves and the release ships (A10.3: segment closes on branch, rc-1
merges the whole scope, rc-N rounds are fixes, the final rc ships).

1. **Reserve.** Flip `[ ]`→`[-]` in the active `TASKS.md`, commit
   `chore(tasks): start <id>` (`dadaia-task-manager`). *Done when:* the reservation
   commit exists and no other task on the branch is `[-]`.
2. **TDD loop.** Implement with tests; run the local CI preflight. *Done when:* the
   suite is green and an `implementation-complete` handoff is emitted.
3. **Segment close (`alpha-N`).** Once every task in the segment is review-ready,
   request `qa-engineer`. **Operative dependency:** at this close, run
   `dd-architecture-survey` (backlog candidate — not yet shipped; this pointer stays
   here so a future rebuild of this file cannot drop it, per the entry's own
   surface-ownership ruling) to turn the standing "architecture review oriented by bug
   history" order into one report plus one dispositioned top candidate, before this
   segment's `qa-engineer` review closes. *Done when:* `qa-engineer` `APPROVE`s a
   commit on the branch — flip every reviewed task `[x]`; no push/PR/merge/closure yet.
4. **Scope-complete.** All segments' tasks are `[x]`. *Done when:* `TASKS.md` (or every
   segment's `TASKS.md`) carries zero `[ ]`/`[-]` rows.
5. **rc-1 PR.** Append a `rc` open record (`RELEASE-EVENTS.md`), open the
   `feature/{M.m.p}` → `develop` PR carrying the whole scope. *Done when:* it merges
   (branch contract: `DADAIA.md` §4 Gitflow, `dd-gitflow-default`).
6. **rc-N rounds.** Fix/adjust only — never new backlog scope. *Done when:* CI is green
   on the round's `feature/{M.m.p}` → `develop` PR and it merges.
7. **Final-rc trio review.** `qa-engineer` + `code-reviewer` + `security-reviewer` all
   `APPROVE` the same commit; `qa-engineer` appends the `implemented` milestone
   (`RELEASE-EVENTS.md`) **on that closed commit's sha**, then the `rc` close record.
   *Done when:* all three verdicts are `APPROVE` on that sha — only then may `[x]`,
   closure, merge, deploy, or archive proceed.
8. **Memory update (`product-engineer`).** Append `phase: CLOSURE` to `RELEASE.jsonl`
   (`ACTIVE.md` retired at T-050-21A, no mirror to keep in sync); update `specs/memory/**`
   atoms to the product's current state. Protocol detail: `MEMORY-UPDATE.md`. *Done
   when:* `dadaia specs doctor` reports the memory atoms clean.
9. **Record the closure narrative.** Append the `note` records `RELEASE-EVENTS.md`
   conventions describe (summary, size accounting, drifts, artifact-GC, test
   dispositions) — `CLOSURE.md`/`CLOSURE-TEMPLATE.md` retire here (T-050-21); until
   T-050-25A finishes retiring the doctor-side `CLOSURE.md` parsers, also write the
   minimal freeform `CLOSURE.md` that `RELEASE-EVENTS.md` names (SPEC-DOC-006
   compatibility only — no template dependency). *Done when:* every narrative class has either a
   `note` record or the named native home (`RELEASE-EVENTS.md`'s conversion table).
10. **Disposition sweep.** Flip every bug/backlog item picked into (or superseded by)
    this release to a terminal token — vocabulary and format: `dd-backlog-definition`
    §2. **CONSUMED → terminal token is an update, never a second histo record** —
    purge-on-pick already exited a fully-consumed slug at SPEC time (sometimes
    provisionally `CONSUMED`); this sweep rewrites that ONE `backlog_histo.jsonl`
    record's disposition in place, never appends a second one for the same slug. A bug
    is never silently dropped: either `dadaia bugs update <id> --set status=resolved …`
    already closed it, or a superseding backlog item's `superseded_by` covers its
    acceptance and its own `status=superseded` update runs now. Stale or invalid
    backlog items get `DEFERRED`/`REJECTED` with a reason, never removed —
    never-delete law (`DADAIA.md` §6 Backlog). *Done when:* `dadaia bugs stats` and
    `dadaia backlog doctor` show zero non-terminal picked items for this release.
11. **Artifact GC sweep.** Run once step 9's narrative records are final — before the
    archive move, never before. **Scope:** this release's own working artifacts under
    `.dadaia/` — its coordination handoffs, its HTML reports, its `.dadaia/tmp/<agent>/`
    captures, and its lifecycle run records. Never another release's artifacts, never
    anything outside `.dadaia/`.
    - KEEP anything a surviving `note`/handoff evidence pointer references. Cross-check
      every candidate path before deleting; when in doubt, keep.
    - DELETE the rest, once unreferenced: consumed coordination handoffs (ack-on-consume
      already deletes most as they are read — canonical rule at `dadaia-handoff-emitter`,
      not restated here; this sweep catches only what per-consume deletion missed),
      report/handoff artifacts superseded by this closure's own `note` records, and tmp
      captures scoped to this release.
    - **Lane guard (AG.1, inherited by every deletion lane in this release):** resolve
      the target, refuse any resolved target outside `.dadaia/`, never follow a
      symlinked directory.
    *Done when:* the `closure-artifact-gc` `note` record states kept/deleted counts per
    artifact class, with evidence.
12. **Archive.** `git mv specs/releases/<release-id> specs/_archive/releases/<release-id>`;
    append `phase: ARCHIVED` to the now-archived `RELEASE.jsonl` — nothing to repoint,
    the next release starts fresh with its own `RELEASE.jsonl`. *Done when:* the
    release directory is under `_archive/`, in the same commit as steps 8–11 (memory →
    closure narrative → sweep → archive, one commit).
13. **Ship PR.** Open `develop` → `main`. On merge, append the `shipped` milestone
    (`RELEASE-EVENTS.md`). *Done when:* it merges — mechanics, the security-verdict PR
    gate, and CI: `DADAIA.md` §4 Gitflow, `dd-gitflow-default`.
14. **Post-deploy.** Delete `feature/{M.m.p}`; cut `feature/{next}` from `main` in the
    same step. *Done when:* exactly one `feature/*` branch exists, named for the next
    version — full rule: `dd-gitflow-default` §4 (not restated here).

## Test-stewardship touchpoints (reference)

Declare test intent at birth and pass the admission filter before a test enters the
permanent suite: `dadaia-test-stewardship` §A/§B. Demotion and quarantine/SCAFFOLD
expiry are closure-time work (step 9's `closure-test-dispositions` note), not earlier
steps'.

## Out of scope for closure

- Writing source code, tests, or pipelines (other agents). The closer **records** test
  dispositions — it never authors a test.
- Modifying `specs/constitution.md` (requires explicit operator approval).
- Memory updates happen in the CLOSURE phase, or the DEFINITION phase under its own
  constitution authorization (not this closure flow). Memory edits by any other agent,
  or in any other phase, are gate-blocked.
- Re-opening an archived release. Once archived, a new release supersedes it.

## Segments (ADR-1/ADR-5)

When the active release carries a `phase` record's `data.segment` (RELEASE.jsonl — the
field the schema itself carries for this purpose), each segment closes independently,
but `RELEASE.jsonl` stays **one file per
release**, never one per segment — `TASKS.md` is the artifact that splits under
`specs/releases/<release-id>/<segment>/TASKS.md`; `RELEASE.jsonl` records which segment
each `phase`/`note` belongs to via `data.segment` instead of splitting the file. Per
ADR-3, qa-only gates an `alpha-N` (commit, no closure/ship), and the full trio + closure
+ archive happen at the shipping `rc-N` — the final-rc steps above. Flat releases are
unchanged.
