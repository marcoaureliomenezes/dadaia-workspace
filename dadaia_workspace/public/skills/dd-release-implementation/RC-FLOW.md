# RC-FLOW — the candidate arc (dd-release-implementation)

Disclosed reference reached from `SKILL.md` §2. The release has OPEN scope; each
CANDIDATE is one closed-scope cycle below; version and branch never change between
candidates.

## Review/QA gate cadence

| Boundary | Who validates | What unlocks |
|---|---|---|
| Per task | implementer discipline only (TDD, tests, local CI preflight, handoff); marker stays `[-]` | nothing; no per-task reviewer gate |
| Candidate close | `dd-code-reviewer` `APPROVED` (three axes, six lenses) on the same commit | `[x]`; the candidate's work -> integration PR |
| Promote (ship) | pre-staged security verdict naming the integration tip | the integration -> principal PR |

- Any `REJECTED`, CRITICAL/HIGH finding, failed E2E, or missing evidence sends the work back to implementation.
- Rework continues until every required validator approves the same commit, or the operator stops the candidate.
- Order per candidate: review -> closure -> merge -> gate.
- The pre-PR three-axis code review (`dd-code-review`) runs before the merge, never after.

## The candidate arc, step by step

Each step ends on a checkable criterion. Steps 5–8 are candidate-closure work.

**Step 1 — Reserve.**
- Flip `[ ]`->`[-]` in the release root's `TASKS.md`, commit `chore(tasks): start <id>` alone.
- Abandon instead: flip `[-]`->`[ ]`, commit `chore(tasks): abandon <id>` naming the reason.
- Dispatching a shell-less sub-agent: commit its flip before relaying the work item — one flip per dispatch, never batched.
- Recovery — two simultaneous `[-]`, or a foreign `[-]` from another session: read `git log`, report to the operator, never transition it yourself.
- Recovery — a gate block: run the block's own one `fix:` line; a BLOCK whose fix is itself blocked is a Stall, reported at once.
- Done when: the reservation commit exists and no other task on the branch is `[-]`.

**Step 2 — TDD loop.**
- Implement with tests; run the local CI preflight.
- Done when: the suite is green and an `implementation-complete` handoff is emitted.

**Step 3 — Scope-complete.**
- All the candidate's tasks are `[x]`; the architecture lens runs `dd-architecture-survey` before the review closes.
- Done when: `TASKS.md` carries zero `[ ]`/`[-]` rows.

**Step 4 — Candidate trio review.**
- `dd-code-reviewer` `APPROVED` on the same commit.
- Done when: the verdict is `APPROVED` on that sha.

**Step 5 — Memory update (`dd-product-engineer`).**
- Memory is closure procedure, never a task: a TASKS.md task whose write set names `specs/memory` is refused by `.dadaia/.venv/bin/dadaia doctor` (SPEC-DOC-047).
- Reconcile product atoms from the code diff — `memory.py drift`, per-atom `git diff`, DELETE → UPDATE → ADD, `catalog generate`, derived docs in the same commit, `release.py memory` — protocol: `MEMORY-UPDATE.md`.
- Done when: one `kind: memory` log entry covers every worklist entry as reviewed or changed, `.dadaia/.venv/bin/dadaia doctor` is clean and the derived-docs test is green.

**Step 6 — Record the candidate's closure narrative.**
- Append the `log` entries `RELEASE-EVENTS.md` describes, each with its `kind`: `summary`, `size`, `drifts`, `artifact-gc`, `test-dispositions`, `dispositions`.
- Done when: every narrative class has a `log` entry or its named native home.

**Step 7 — Disposition sweep.**
- Flip every bug/backlog item picked into (or superseded by) this candidate to a terminal token.
- A picked backlog entry exits by `python3 .agents/skills/dd-backlog-definition/scripts/backlog.py exit <slug> --disposition …`, once.
- An audit finding moves by `python3 .agents/skills/dd-audit-project/scripts/audit.py disposition <dir> <finding> --disposition …`; when none is `open`, `python3 .agents/skills/dd-audit-project/scripts/audit.py close <dir> --sha <window-end>` appends the histo record and deletes the directory.
- A bug is never silently dropped — `python3 .agents/skills/dd-bug-resolution/scripts/bugs.py resolve` already closed it, or a superseder covers it.
- Age the ledger once the sweep is terminal: `python3 .agents/skills/dd-bug-resolution/scripts/bugs.py archive` — a numbered step here, never a call another script makes (scripts never call each other).
- Done when: `python3 .agents/skills/dd-bug-resolution/scripts/bugs.py stats` and `.dadaia/.venv/bin/dadaia doctor`'s `ledgers` section show zero non-terminal picked items.

**Step 8 — Artifact GC sweep.**
- `.dadaia/.venv/bin/dadaia doctor` dry: read every `WS-<zone>-<verdict>` line and the `compliance:` score line.
- `.dadaia/.venv/bin/dadaia doctor --fix` runs the reaper (slop MOVED to `.dadaia/reaped/`, 7-day hold) then the specs repairs; list what it held for the operator.
- Done when: the `kind: artifact-gc` log entry records the `compliance(total)` line and it reads 100%, or names the slop the operator holds.

**Step 9 — Candidate PR.**
- Open the work -> integration PR (branch names: the constitution's `gitflow:`) (security verdict covering the head, `dd-gitflow-default` §2a); watch CI to green; merge.
- Done when: it merges green.

The arc ends here. Gate -> promote -> record -> branch cut: `dd-gitflow-default` steps
9-12.

## Test-stewardship touchpoints (reference)

- Declare test intent at birth; pass the admission filter (`dd-test-stewardship`, intent and admission) before a test enters the suite.
- Demotion and quarantine/SCAFFOLD expiry are candidate-closure work (step 6's `kind: test-dispositions` log entry).

## Out of scope for closure

- Writing source code, tests, or pipelines (other agents) — the closer records test dispositions, never authors a test.
- Modifying `specs/constitution.md` (requires explicit operator approval).
- Memory updates outside CLOSURE phase (or DEFINITION under its own authorization) — gate-blocked for any other agent/phase.
- Minting a version, writing a CHANGELOG section or moving a closed trio on disk — release-please owns the first two, git owns the third.
