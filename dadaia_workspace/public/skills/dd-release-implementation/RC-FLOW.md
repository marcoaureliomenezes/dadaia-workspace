# RC-FLOW — the candidate arc (dd-release-implementation)

Disclosed reference reached from `SKILL.md` §3. Release-candidates model (0.4.6,
ADRs 0005–0009): the release has OPEN scope; each CANDIDATE is one closed-scope
cycle below. The version and the branch never change between candidates.

## Review/QA gate cadence

| Boundary | Who validates | What unlocks |
|---|---|---|
| Per task | implementer discipline only (TDD, tests, local CI preflight, handoff); marker stays `[-]` | nothing; no per-task reviewer gate |
| Candidate close | `qa-engineer` + `code-reviewer` + `security-reviewer`, all `APPROVED` on the same commit | `[x]`; the candidate's `feature -> develop` PR |
| Promote (ship) | pre-staged security verdict naming develop's tip | the `develop -> main` PR |

- Any `REJECTED`, CRITICAL/HIGH finding, failed E2E, or missing evidence sends the work back to implementation.
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
- `qa-engineer` + `code-reviewer` + `security-reviewer` all `APPROVED` on the same commit.
- Done when: all three verdicts are `APPROVED` on that sha.

**Step 5 — Memory update (`product-engineer`).**
- Set `phase: CLOSURE` in `_RELEASE.json` — after the last task is `[x]`, never before.
- Memory is closure procedure, never a task: a TASKS.md task whose write set names
  `specs/memory` is refused by `dadaia doctor` (SPEC-DOC-047).
- Update `specs/memory/**` atoms to the product's current state — protocol detail: `MEMORY-UPDATE.md`.
- Done when: `dadaia doctor`'s `specs` section reports the memory atoms clean and one `kind: memory` log entry records atoms reviewed-unchanged vs changed.

**Step 6 — Record the candidate's closure narrative.**
- Append the `log` entries `RELEASE-EVENTS.md` describes, each with its `kind`: `summary`, `size`, `drifts`, `artifact-gc`, `test-dispositions`, `dispositions`.
- Done when: every narrative class has a `log` entry or its named native home.

**Step 7 — Disposition sweep.**
- Flip every bug/backlog item picked into (or superseded by) this candidate to a terminal token.
- A picked backlog entry exits `active[]` here, once, into `backlog_histo.jsonl` as one `histo-record-v1` — never a second record for the same slug.
- A bug is never silently dropped — `dadaia bugs update` already closed it, or a superseder covers it.
- Done when: `dadaia bugs stats` and `dadaia doctor`'s `ledgers` section show zero non-terminal picked items.

**Step 8 — Artifact GC sweep.**
- `dadaia doctor` dry: read every `WS-<zone>-<verdict>` line and the `compliance:` score line.
- `dadaia doctor --fix` runs the reaper (slop MOVED to `.dadaia/reaped/`, 7-day hold) then the specs repairs; list what it held for the operator.
- Done when: the `kind: artifact-gc` log entry records the `compliance(total)` line and it reads 100%, or names the slop the operator holds.

**Step 9 — Candidate PR.**
- Open the `feature/{M.m.p}` -> `develop` PR (security verdict covering the head, `DADAIA.md` §4.2); watch CI to green; merge.
- Done when: it merges green.

**Step 10 — The promote-or-continue gate.**
- Ask the operator: **promote (deploy) or continue?** Never assume; never a hook.
- **Continue**: run `dadaia release rc-archive` — it validates the whole tree, moves the trio to `rc-N/` and parks the release in `DEFINITION` (trio absent or SPEC-only is legal there), then runs `bugs archive`. The next candidate starts at `dd-release-definition`, same version, same branch.
- **Promote**: proceed to step 11.

**Step 11 — Ship (promote only).**
- Open `develop` -> `main` with the pre-staged ship verdict naming develop's tip; on merge, set the `shipped` milestone (`RELEASE-EVENTS.md`); publication per the operator's order.
- Done when: it merges and the Release workflow is green end to end.

**Step 12 — Archive + branch cut (promote only).**
- `dadaia release archive <v> --shipped <sha> --pr <n> --next <M.m.p>` is the whole lane, all-or-nothing: it validates (tree, every task `[x]`, CLOSURE, `implemented`), sets `shipped` + `phase: ARCHIVED`, moves the directory to `_archive/<v>/` (final trio at root, `rc-N/` folders inside, ADR 0009), appends the histo record, births `<next>`, runs `bugs archive`.
- It never runs git: it PRINTS the `next:` lines — delete `feature/{v}`, cut `feature/{next}` from `main`, then `git merge -s ours origin/develop` as the new branch's first commit (the squash kept `main`'s tree, not `develop`'s history; without it every later `feature -> develop` PR is DIRTY, bug `squash-to-main-leaves-develop-history-divergent-…`). Run them in that order.
- Mint the new release's version in `pyproject` + the CHANGELOG top section.
- Done when: exactly one `feature/*` branch exists, named for the next version.

## Test-stewardship touchpoints (reference)

- Declare test intent at birth; pass the admission filter (`dd-test-stewardship`, intent and admission) before a test enters the suite.
- Demotion and quarantine/SCAFFOLD expiry are candidate-closure work (step 6's `kind: test-dispositions` log entry).

## Out of scope for closure

- Writing source code, tests, or pipelines (other agents) — the closer records test dispositions, never authors a test.
- Modifying `specs/constitution.md` (requires explicit operator approval).
- Memory updates outside CLOSURE phase (or DEFINITION under its own authorization) — gate-blocked for any other agent/phase.
- Re-opening an archived release — once archived, the next minted version supersedes it.
