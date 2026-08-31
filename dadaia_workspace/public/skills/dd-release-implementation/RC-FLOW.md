# RC-FLOW — the candidate arc (dd-release-implementation)

Disclosed reference reached from `SKILL.md` §3. Release-candidates model (0.4.6,
ADRs 0005–0009): the release has OPEN scope; each CANDIDATE is one closed-scope
cycle below. The version and the branch never change between candidates.

## Review/QA gate cadence

| Boundary | Who validates | What unlocks |
|---|---|---|
| Per task | implementer discipline only (TDD, tests, local CI preflight, handoff); marker stays `[-]` | nothing; no per-task reviewer gate |
| Candidate close | `qa-engineer` + `code-reviewer` + `security-reviewer`, all `APPROVE` the same commit | `[x]`; the candidate's `feature -> develop` PR |
| Promote (ship) | pre-staged security verdict naming develop's tip | the `develop -> main` PR |

- Any `REQUEST_CHANGES`, CRITICAL/HIGH finding, failed E2E, or missing evidence sends the work back to implementation.
- Rework continues until every required validator approves the same commit, or the operator stops the candidate.
- Order per candidate: review -> closure -> merge -> gate.
- The pre-PR three-axis code review (`dd-code-review`) runs before the merge, never after.

## The candidate arc, step by step

Each step ends on a checkable criterion. Steps 5–8 are candidate-closure work.

**Step 1 — Reserve.**
- Flip `[ ]`->`[-]` in the release root's `TASKS.md`, commit `chore(tasks): start <id>` (`dd-task-manager`).
- Done when: the reservation commit exists and no other task on the branch is `[-]`.

**Step 2 — TDD loop.**
- Implement with tests; run the local CI preflight.
- Done when: the suite is green and an `implementation-complete` handoff is emitted.

**Step 3 — Scope-complete.**
- All the candidate's tasks are `[x]`; run `dd-architecture-survey` before the review closes.
- Done when: `TASKS.md` carries zero `[ ]`/`[-]` rows.

**Step 4 — Candidate trio review.**
- `qa-engineer` + `code-reviewer` + `security-reviewer` all `APPROVE` the same commit.
- Done when: all three verdicts are `APPROVE` on that sha.

**Step 5 — Memory update (`product-engineer`).**
- Set `phase: CLOSURE` in `_RELEASE.json`.
- Update `specs/memory/**` atoms to the product's current state — protocol detail: `MEMORY-UPDATE.md`.
- Done when: `dadaia specs doctor` reports the memory atoms clean.

**Step 6 — Record the candidate's closure narrative.**
- Append the `log` entries `RELEASE-EVENTS.md` describes (summary, size, drifts, GC, dispositions).
- Done when: every narrative class has a `log` entry or its named native home.

**Step 7 — Disposition sweep.**
- Flip every bug/backlog item picked into (or superseded by) this candidate to a terminal token.
- CONSUMED -> terminal token is an update, never a second histo record.
- A bug is never silently dropped — `dadaia bugs update` already closed it, or a superseder covers it.
- Done when: `dadaia bugs stats` and `dadaia backlog doctor` show zero non-terminal picked items.

**Step 8 — Artifact GC sweep.**
- Scope: this candidate's own working artifacts under `.dadaia/` only.
- KEEP anything a surviving `note`/handoff evidence pointer references; lane guard (AG.1): never leave `.dadaia/`, never follow a symlinked directory.
- Done when: the `closure-artifact-gc` log entry states kept/deleted counts per class.

**Step 9 — Candidate PR.**
- Open the `feature/{M.m.p}` -> `develop` PR (security verdict covering the head, `DADAIA.md` §4.2); watch CI to green; merge.
- Done when: it merges green.

**Step 10 — The promote-or-continue gate.**
- Ask the operator: **promote (deploy) or continue?** Never assume; never a hook.
- **Continue**: run `dadaia release rc-archive` — the trio moves to `rc-N/`, phase resets to DISCOVERY, and the next candidate starts at `dd-release-definition`. Same version, same branch.
- **Promote**: proceed to step 11.

**Step 11 — Ship (promote only).**
- Open `develop` -> `main` with the pre-staged ship verdict naming develop's tip; on merge, set the `shipped` milestone (`RELEASE-EVENTS.md`); publication per the operator's order.
- Done when: it merges and the Release workflow is green end to end.

**Step 12 — Archive + branch cut (promote only).**
- `git mv specs/releases/<v>/ specs/releases/_archive/<v>/` — whole directory: the final trio stays at root, `rc-N/` folders inside (ADR 0009); set `phase: ARCHIVED`; append the histo record, same commit.
- Delete `feature/{v}`; cut `feature/{next patch}` from `main` in the same step; the new release is born with its version minted (pyproject + CHANGELOG top section).
- Done when: exactly one `feature/*` branch exists, named for the next version.

## Test-stewardship touchpoints (reference)

- Declare test intent at birth; pass the admission filter (`dd-test-stewardship`, intent and admission) before a test enters the suite.
- Demotion and quarantine/SCAFFOLD expiry are candidate-closure work (step 6's `closure-test-dispositions` log entry).

## Out of scope for closure

- Writing source code, tests, or pipelines (other agents) — the closer records test dispositions, never authors a test.
- Modifying `specs/constitution.md` (requires explicit operator approval).
- Memory updates outside CLOSURE phase (or DEFINITION under its own authorization) — gate-blocked for any other agent/phase.
- Re-opening an archived release — once archived, the next minted version supersedes it.
