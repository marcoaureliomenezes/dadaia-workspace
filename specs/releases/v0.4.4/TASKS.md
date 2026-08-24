# TASKS — Release v0.4.4 — organize the core

**Status:** Aprovado
**Amendment 1:** Aprovado (operator, 2026-08-23) (2026-08-23, the skills audit folded in — SPEC §2/§8).
**T-044-54 … T-044-62 are Draft and not implementable** until the operator approves the
amendment delta; every original task id, the five segments and the `rc` lane are unchanged.
**Release ID:** v0.4.4
**Owner:** product-engineer
**Source SPEC:** `specs/releases/v0.4.4/SPEC.md`
**Source PLAN:** `specs/releases/v0.4.4/PLAN.md`
**Branch:** `feature/0.4.4` (cut from `develop` — recorded exception E-1)
**Segments:** `S1 … S5` — internal work boundaries on `feature/0.4.4`, each closed by a
`qa-engineer` review **committed on the branch**: no merge, no PR, no `rc` burned (SPEC D8).
**Candidates:** `rc-1 … rc-N` (G5 — **no alpha, no beta**). `rc-1` burns when the **whole**
scope is implemented, validated, gate-green and closed by QA, and is merged into `develop`
(milestone (b)); `rc-2 … rc-N` are adjustment rounds on that same scope found by testing the
merged `develop`; the **final `rc`** carries memory + CLOSURE + archive and ships. If nothing
is found, the final `rc` **is** `rc-1`.

This file is the single marker surface for all of it (D1); the blocks below are the
segments and the lane. `ACTIVE.md` carries no `segment:` line.

## Task status markers

- `[ ]` OPEN · `[-]` IN PROGRESS · `[x]` DONE

## Segment and candidate map

**Execution order is the block order below, not numeric id order.** Ids are stable
identifiers: T-044-52 and T-044-53 execute *before* T-044-47 … 51, because the closure
artifacts ride the **final** `rc`; and *(A1)* T-044-54 … 60 execute **inside `S3`, before
T-044-21**, while T-044-61 … 62 execute **at the head of `S5`, before T-044-33**.

| Block | Tasks | Contents | Gate |
|---|---|---|---|
| W0 | T-044-01 … 02 | definition commit + milestone (a), **v1 mechanic once** (E-1/D2) | APPROVED security verdict on the pushed `develop` delta |
| `S1` | T-044-03 … 11 | HIGH marker bug + gitflow v2 (FR1–FR6) | `qa-engineer` review **committed** + `software-architect` **AR-2** ruling |
| `S2` | T-044-13 … 16 | rules→skills governance map (FR7–FR9) | `qa-engineer` review committed |
| `S3` | T-044-18 … 20, **T-044-54 … 60** *(A1)*, T-044-21 … 24 | core skills consolidation (FR10–FR14) **+ the audit's B/C work (FR24–FR31)** — all content before the single projection cycle | `qa-engineer` review committed + `software-architect` **AR-1** ruling |
| `S4` | T-044-26 … 31 | spec-context associated repos (FR15–FR19) | `qa-engineer` review committed |
| `S5` | **T-044-61 … 62** *(A1)*, T-044-33 … 42 | the anti-loop pair (FR22–FR23) **first**, then the bug sweep (8 tasks) + branch hygiene (FR20) | `qa-engineer` review committed |
| scope complete | T-044-44 … 46 | full gates → six-axis review → security review → QA closes the release | the trio APPROVED |
| `rc-1` | T-044-52 | PR `feature/0.4.4` → `develop` — **milestone (b)**, the first v2 merge | merged, CI green |
| `rc-2 … rc-N` | T-044-53 | adjustment rounds on this scope, found by testing the merged `develop` | one QA close + one merge per round |
| final `rc` | T-044-47 … 51 | memory → CLOSURE → archive → version bump + merge → ship | full trio still green, then the PR to `main` |

**Retired ids** (the D8 restructure removed the work they encoded — a per-segment merge no
longer exists): **T-044-12, T-044-17, T-044-25, T-044-32, T-044-43**. They are listed here
so no surviving id had to be renumbered; they are not reused.

Order across the lane is fixed: **review → closure → archive → ship**. The six-axis review
is its own task and runs on a **thawed** tree, before `rc-1` and again over any later `rc`
delta — always before the archive move.

## Standing rules for this release

- **`product-engineer` has no shell.** Every task marked **[git]** or carrying a command is
  executed by the dispatcher, `software-engineer`, `ai-engineer` or `qa-engineer`.
  `product-engineer` authors text only.
- **Shell-less reservation obligation.** When the dispatcher relays work for a shell-less
  sub-agent it commits that sub-agent's `[ ]`→`[-]` flip **before** relaying the next item —
  never batched. Applies to T-044-47 and T-044-48.
- **Reservation is observable.** Flip `[ ]`→`[-]` and commit `chore(tasks): start <id>`
  before the work (`dadaia-task-manager`). **One `[-]` at a time** unless a task below
  declares a sanctioned parallel pair.
- **Green at every commit:** `dadaia ci preflight`, `dadaia backlog doctor`,
  `dadaia specs doctor`, `dadaia public doctor`. **No `--no-verify`, ever.**
- **RED before GREEN**, on the executed path.
- **The standing order is an acceptance.** A diff that adds a branch, a flag, a second code
  path, a cross-feature reach-in or a new side effect to an existing feature is rejected,
  whatever the test result. Every review verdict states the **bug-surface delta** of the
  feature it touched, with bug-history evidence.
- **Satisfiable diagnostics.** Every new check is green at HEAD the moment it lands, and no
  new check goes silent where it should error.
- **Test intent at birth.** `Intent: CONTRACT — v0.4.4 <A-id>` or `Intent: SENTINEL — <seam>`.
  **Zero new `tests/e2e/**`** without a named `qa-engineer` exception in that candidate's QA
  artifact.
- **Never prune to go green.** A deletion, skip or disable is a `qa-engineer` verdict with
  evidence, executed by `software-engineer`.
- **Lane discipline.** `ai-engineer` performs every skill/persona/rule/projected-asset edit;
  `software-engineer` every production-code, CI-YAML and test edit; `project-manager` any
  backlog-file mechanics; `product-engineer` only specs and memory.
- **Escalate at discovery.** An actionable defect found mid-segment is fixed in that segment
  or escalated to the operator immediately. A defect in the tooling is registered as a bug
  and fixed as an Arm-B rider on `feature/0.4.4` — never accumulated for closure.
- **No new scope in an `rc`.** An `rc-N ≥ 2` carries only fixes, adjustments and
  improvements **on this release's scope**, found by testing the merged `develop`. A demand
  outside this scope is backlog for a later release (SPEC A21.7, R-8).
- **A completed task group is one commit** — stage exactly the task's write set, never `-A`.
- **Measurements** (V1–V19, PLAN §6) are captured under `.dadaia/tmp/<agent>/<YYYYMMDD>/`.
- *(A1)* **The AI surface only shrinks.** Every task touching
  `public/{agents,skills,data,entities}/**` is net-negative in lines, or its commit message
  says why not (SPEC A21.8). A pointer replaces a restatement; never the reverse.
- *(A1)* **Amendment gate.** No task in T-044-54 … T-044-62 is reserved (`[ ]`→`[-]`) before
  the operator writes `Aprovado` in SPEC §8's Amendment 1 block. Reserving one earlier is a
  discipline violation, not a gate block — the gate reads no marker.
- *(A1)* **From T-044-62 onward, every `resolved` event carries the three evidence fields**
  (red-loop command, test seam, diff direction). Earlier bug tasks in this release restate
  them as CLOSURE validations; no past event is rewritten (A23.2/A23.4).

## Acceptance and evidence map

| Task | FR / bug | Acceptance ids | Evidence |
|---|---|---|---|
| T-044-01 | — | — | definition commit sha; `ACTIVE.md` `DEFINITION`; `## ACTIVE` empty; `superseded` event |
| T-044-02 | — | SPEC §7 | V1 + V2 capture; pushed `develop` sha; APPROVED security handoff |
| T-044-03 | bug `sdd-artifact-linter-mutates-task-markers` | R-3 / D7 | RED-then-GREEN **or** evidenced negative + writer census + contract test; `resolved` event |
| T-044-04 | FR1 | A1.1–A1.5 | V3 capture; law-source diff; projection byte-identity |
| T-044-05 | FR2 | A2.1–A2.5 | skill diff; folder rename; grep for the old name |
| T-044-06 | FR3 | A3.1–A3.6 | RED-then-GREEN refusal fixtures; regex grep; LOC delta |
| T-044-07 | FR4 | A4.1–A4.5 | CI run links; guard fixtures; verdict-gate fixtures |
| T-044-08 | FR5 | A5.1–A5.4 | V3 re-capture; 14-surface diff |
| T-044-09 | bug `prepush-gate-omits-import-boundary-contracts-ci-runs` / FR6 | A6.1–A6.3 | RED-then-GREEN; parity test; `resolved` event |
| T-044-10 | — | D-3 | V4 capture (both edges), venv reinstall output |
| T-044-11 | all `S1` | A1–A6 ids | `qa-engineer` artifact committed + `software-architect` AR-2 ruling |
| ~~T-044-12~~ | — | — | **retired** at the D8 restructure (was the per-segment PR) |
| T-044-13 | FR7 | A7.1–A7.4 | map JSON + schema; validation output |
| T-044-14 | FR8 | A8.1–A8.3 | constitution diffs (repo + scaffold); operator confirmation reference |
| T-044-15 | FR9 | A9.1–A9.5 | 6 mutation fixtures; ported `--self-test`; deleted-script proof |
| T-044-16 | all `S2` | A7–A9 ids | `qa-engineer` artifact committed |
| ~~T-044-17~~ | — | — | **retired** at the D8 restructure |
| T-044-18 | FR10 | A10.1–A10.3 | grep; section-by-section coverage table |
| T-044-19 | FR11 | A11.1–A11.4 | V5 capture; folder diff; link-not-copy proof |
| T-044-20 | FR12 | A12.1–A12.4 | per-skill commits; V6 capture; CLI verb check |
| **T-044-54** *(A1)* | FR25 | A25.1–A25.5 | per-skill diffs; V17 capture; grep for the private worked example and "one question per turn" |
| **T-044-55** *(A1)* | FR26 + FR10 | A26.1–A26.5, A10.4 | sibling files on disk; V17 body-size capture; the one surviving audit-dimension list |
| **T-044-56** *(A1)* | FR28 | A28.1–A28.4 | frontmatter diffs; V16 capture; enforcer equivalence in both directions |
| **T-044-57** *(A1)* | FR24 + FR29 | A24.1–A24.4, A29.1–A29.6 | per-persona line counts (V17); the **coverage table** (removed block → surviving home); V15 negation capture |
| **T-044-58** *(A1)* | FR27 | A27.1–A27.20 | one grep per sediment line; the citation check green at HEAD |
| **T-044-59** *(A1)* | FR31 / bug `dadaia-md-projected-twice-into-claude-code-context` | A31.1–A31.6 | RED-then-GREEN on the injected context; per-harness single-load evidence; `resolved` event |
| **T-044-60** *(A1)* | FR30 | A30.1–A30.4 | V18 capture (bound + unbound), on a real session |
| T-044-21 | FR13 | A13.1–A13.4 | V7 multiset diff; V9 capture; sibling-file byte check |
| T-044-22 | FR13 / AR-1 | A13.5 | `software-architect` ruling |
| T-044-23 | FR14 | A14.1–A14.4 | study handoff, validated |
| T-044-24 | all `S3` | A10–A14 ids | `qa-engineer` artifact committed |
| ~~T-044-25~~ | — | — | **retired** at the D8 restructure |
| T-044-26 | FR15 | A15.1–A15.3 | V8 capture; migration round-trip |
| T-044-27 | FR16 | A16.1–A16.4 | alive/dead fixtures on N+1 repos |
| T-044-28 | FR17 | A17.1–A17.3 | CLI fixtures |
| T-044-29 | FR18 + superseded bug | A18.1–A18.5 | RED-then-GREEN on the bug repro; export round-trip; panel render |
| T-044-30 | FR19 | A19.1–A19.2 | bind + doctor fixtures with a specs-bearing associated repo |
| T-044-31 | all `S4` | A15–A19 ids | `qa-engineer` artifact committed |
| ~~T-044-32~~ | — | — | **retired** at the D8 restructure |
| **T-044-61** *(A1)* | FR22 | A22.1–A22.5 | skill diff (net-negative); "Done when" per phase; the no-seam clause grep |
| **T-044-62** *(A1)* | FR23 | A23.1–A23.6 | RED-then-GREEN refusal fixtures; `bug-event-v1` diff; law + skill wording; historical events still readable |
| T-044-33 … 40 | the 8 remaining bugs | per task | RED-then-GREEN + `resolved` event **carrying the three fields** (A23.4) each |
| T-044-41 | FR20 | A20.1–A20.4 | V10 capture before/after; per-branch tag proof |
| T-044-42 | all `S5` | bug ids + A20 | `qa-engineer` artifact committed |
| ~~T-044-43~~ | — | — | **retired** at the D8 restructure |
| T-044-44 | FR21 | A21.1–A21.6 | gate output; V11 + V12 capture |
| T-044-45 | all | A21.1–A21.3 | `code-reviewer` APPROVED on a **thawed** tree, with the bug-surface verdict |
| T-044-46 | all | — | `security-reviewer` APPROVED + `qa-engineer` release verdict ("closed by QA") |
| **T-044-52** | — | — | **`rc-1`**: PR `feature→develop` merged; CI green; verdict handoff for the PR head sha |
| **T-044-53** | — | A21.7 | **`rc-2 … rc-N`**: per round — the finding on `develop`, its fix, QA close, delta reviews, merge |
| T-044-47 | all | SPEC §5 | memory diff; `specs doctor` 0 errors |
| T-044-48 | all picked | A21.5 + closure obligations | `CLOSURE.md`; sweeps complete; `rc` ledger |
| T-044-49 | — | — | `git mv` archive; `ACTIVE.md` `ARCHIVED` |
| T-044-50 | — | — | `0.4.4` bump + `[0.4.4]`; final-`rc` PR `feature→develop` merged; CI green |
| T-044-51 | — | — | PR `develop→main` merged; `0.4.4` published; `feature/0.4.4` deleted; `feature/0.4.5` cut from `main`; V13 |

---

## W0 — definition

- [x] **T-044-01 — [git] Definition commit**

**Owner role:** dispatcher (+ `project-manager` for the backlog mechanics) · **Commit:**
`docs(T-044-01): v0.4.4 definition — organize the core`

**Preconditions:** SPEC, PLAN and TASKS authored and carrying `**Status:** Aprovado`;
working tree on `feature/0.4.4`.

**Write set (staging only — content authored by `product-engineer` / `project-manager`):**
`specs/releases/ACTIVE.md`, `specs/releases/v0.4.4/{SPEC,PLAN,TASKS}.md`,
`specs/backlog/BACKLOG.md` (purge-on-pick: the four `## ACTIVE` subsections removed),
`specs/bugs/bugs.jsonl` (the one `superseded` event).

**Description:** The pick and the SPEC ride **one** commit (`DADAIA.md` §5). `ACTIVE.md`
reads `release: v0.4.4` / `phase: DEFINITION` — the phase advances to `IMPLEMENTATION` in
T-044-02, not here. Append the supersession before committing:
`dadaia bugs append --bug-id context-list-current-branch-stale-for-alive-repo --event superseded --superseded-by spec-context-associated-repos`.

**Done criterion:** one commit with exactly those paths; `## ACTIVE` empty; `backlog doctor`
and `specs doctor` clean.

**Parallelism:** none — first task.

---

- [x] **T-044-02 — [git] Milestone (a): merge, security review, push (v1 mechanic, once)**

**Owner role:** dispatcher + `security-reviewer` · **Commit:** merge commit on `develop`
(plus the `ACTIVE.md` phase flip)

**Preconditions:** T-044-01 `[x]`.

**Write set:** `specs/releases/ACTIVE.md` (`DEFINITION` → `IMPLEMENTATION`), then git refs
(`develop`), the security handoff and the V1/V2 captures.

**Description:** Capture **V1** (`dadaia bugs status` — must show the 11 picked bugs, one
already `superseded`) and **V2** (`specs doctor`, `backlog doctor`). Then, **per E-1/D2 and
this once only**, the v1 mechanic: merge `feature/0.4.4` into local `develop`; run a
diff-based `security-reviewer` review of `origin/develop..develop`; push `develop`. v2's
inverted chokepoint does not exist yet, so a `feature/*` push would be refused.

**Done criterion:** V1 and V2 captured and consistent with SPEC §7; `develop` pushed;
APPROVED handoff covering the pushed delta; CI green; `ACTIVE.md` reads `IMPLEMENTATION`.

**Parallelism:** none.

---

## Segment `S1` — the gitflow contract, v2

- [x] **T-044-03 — Bug (Arm B): `sdd-artifact-linter-mutates-task-markers` (HIGH)**

**Owner role:** software-engineer · **Commit:** `fix(T-044-03): <root cause>` ·
**Lands first in the release** (D7).

**Write set:** `dadaia_workspace/hooks/**` and/or `tests/**` as the reproduction dictates;
`specs/bugs/bugs.jsonl`.

**Description:** Reproduce on the executed path first: edit a `specs/releases/**/TASKS.md`
through the file tools and observe whether any product-owned writer mutates a
`[ ]`/`[-]`/`[x]` marker, a `**Status:**` token, or injects body content. If it reproduces,
fix the structural cause — never by excluding a path from a formatter that should not be
running. If it does **not** reproduce (R-3: the bug was re-filed from another repo's ledger
and no post-write markdown formatter exists in this package's hooks), close it with
**evidence**: a census of every product-owned writer of `specs/releases/**/*.md` and a
contract test pinning that none of them mutates a marker or a status token.

**Done criterion:** RED-then-GREEN, or the evidenced negative plus its contract test;
`resolved` event with `--resolution-evidence`; bug `Closed`.

**Parallelism:** none.

---

- [x] **T-044-04 — FR1: one gitflow law section**

**Owner role:** ai-engineer · **Commit:** `docs(T-044-04): one gitflow section in the law`

**Preconditions:** T-044-03 `[x]`.

**Write set:** `dadaia_workspace/public/data/DADAIA.md` (**source only** — projected law is
PROTECTED), then `public stage` + `public install --target all`.

**Description:** Collapse §3's chokepoint row, §5 Branches/Releases/Hotfixes and §6 Push
green into one gitflow section carrying G2–G7. Replace `alpha-N → rc-N` with `rc-N`. Move
the stage rows to `feature/{M.m.p}` (D6). Retire the hotfix stage (G2). Capture **V3**
before and after.

**Done criterion:** A1.1–A1.5 hold; projections byte-identical to the source.

**Parallelism:** none.

---

- [x] **T-044-05 — FR2: `dd-gitflow-default`, renamed and rewritten in one touch**

**Owner role:** ai-engineer · **Commit:**
`docs(T-044-05): rename dadaia-gitflow to dd-gitflow-default and rewrite to v2`

**Preconditions:** T-044-04 `[x]` (the skill points at the law section).

**Write set:** `dadaia_workspace/public/skills/dd-gitflow-default/**` (from
`dadaia-gitflow/`), the manifest, `public/entities/registry.json`, projections.

**Description:** Rename the folder (D3) and rewrite to the v2 contract: branch table, stage
contract, start-of-work protocol, branch-creation rule, uniqueness + delete-after-deploy +
same-step next-cut rules (discipline, G7), anti-slop/anti-stale guidance, the CI/CD
automation section, and the explicit mechanical-vs-discipline split. Shape per G12; anything
long is disclosed to a sibling file in the same folder.

**Done criterion:** A2.1–A2.5 hold; no `dadaia-gitflow` path survives anywhere.

**Parallelism:** none.

---

- [x] **T-044-06 — FR3: invert the chokepoint to v2**

**Owner role:** software-engineer · **Commit:**
`fix(T-044-06): feature branches are pushable, develop and main are PR-only`

**Preconditions:** T-044-05 `[x]`.

**Write set:** `dadaia_workspace/features/chokepoints/service.py`,
`dadaia_workspace/cli/commands/ci.py`, their tests.

**Description:** Apply the inversion exactly as PLAN §4 names it: `_PERMITTED_BRANCH_RES`
becomes three patterns with no `v` and no hotfix row; `_PUSHABLE_BRANCH` inverts;
`push_gate_decision` keeps branch policy + denylist scan and **deletes** the security-verdict
step; `gc-push-verdicts` is re-keyed to the merged PR head sha (D5). Deleted code is
deleted, not flagged off.

**Done criterion:** A3.1–A3.6 hold; LOC delta measured and ≤ 0.

**Parallelism:** none.

---

- [x] **T-044-07 — FR4: CI sees the feature branch; the verdict becomes a PR gate**

**Owner role:** software-engineer · **Commit:**
`ci(T-044-07): trigger on feature pushes and gate the security verdict at the PR`

**Preconditions:** T-044-06 `[x]`.

**Write set:** `.github/workflows/ci.yml`, its tests/fixtures.

**Description:** Extend triggers to `push: feature/**` and `pull_request: [develop, main]`.
Extend `pr-source-guard` **in the same job** to guard both edges. Add the security-verdict PR
gate keyed on the PR head sha. Record A4.4's limit in the job's own comment: this job does
not run on the PR that introduces it; it is advisory at `rc-1` and required from `rc-2`, and
the required-checks list is re-supplied whole when the operator sets it (`gh api PATCH`
clobbers).

**Done criterion:** A4.1–A4.5 hold.

**Parallelism:** none.

---

- [x] **T-044-08 — FR5: collapse 14 surfaces to pointers**

**Owner role:** ai-engineer (personas, skills, registry) + `software-engineer` (the shell
script header and the CLI docstring) · **Commit:**
`docs(T-044-08): the branch model is stated twice, everywhere else points`

**Preconditions:** T-044-07 `[x]`.

**Write set:** `public/agents/{ai-engineer,project-manager,qa-engineer,software-engineer,code-reviewer,security-reviewer,product-engineer}.md`,
`public/entities/registry.json`, `public/skills/{dd-release-definition,dd-release-implement,dd-bug-fix,dd-bug-registration,dadaia-task-manager}/SKILL.md`,
`public/scripts/pre-push-ci-gate.sh` (header), `dadaia_workspace/cli/commands/ci.py`
(docstring), projections.

**Description:** One pointer line each, naming both homes. Resolve `dd-release-implement`
L43 by replacing it with the pointer. Remove the `hotfix/{M.m.p}` cut instruction from
`dd-bug-fix` (G2/G3). Re-capture **V3**; the delta must be negative.

**Done criterion:** A5.1–A5.4 hold.

**Parallelism:** **sanctioned pair** — this task's `public/**` half may run in parallel with
T-044-09, whose write set (`public/scripts/pre-push-ci-gate.sh` body + preflight tests) is
disjoint from the personas/skills half. If the same script is touched by both, serialize.

---

- [x] **T-044-09 — FR6 / bug: the preflight stops lying about CI equivalence**

**Owner role:** software-engineer · **Commit:**
`fix(T-044-09): lint-imports joins the preflight so local and CI gate the same set`

**Preconditions:** T-044-07 `[x]`.

**Write set:** `dadaia_workspace/public/scripts/pre-push-ci-gate.sh` (and/or the package
preflight it calls), its tests, `specs/bugs/bugs.jsonl`.

**Description:** Add `lint-imports --config setup.cfg` to the existing preflight sequence —
one command in a list, no new code path. Pin parity with a test that fails when either side
gains a check the other lacks.

**Done criterion:** A6.1–A6.3 hold; `resolved` event appended; bug `Closed`.

**Parallelism:** paired with T-044-08 (see above).

---

- [x] **T-044-10 — [git] Make v2 live: reinstall the workspace venv and probe both edges**

**Owner role:** dispatcher / software-engineer · **Commit:** none (environment + capture)

**Preconditions:** T-044-06 … T-044-09 `[x]`.

**Description:** The workspace venv is **not** an editable install (D-3), so the new
chokepoint is inert until reinstalled. Reinstall into `.dadaia/.venv`, then capture **V4**:
a `feature/*` push is allowed and a `develop` push is refused, both by the executed path,
each refusal naming the PR route.

**Done criterion:** V4 captured showing both outcomes; `dadaia --version` consistent.

**Parallelism:** none.

---

- [x] **T-044-11 — `S1` QA close + AR-2 architecture ruling**

**Owner role:** qa-engineer + software-architect · **Commit:**
`chore(T-044-11): S1 qa review`

**Preconditions:** T-044-03 … T-044-10 `[x]`.

**Description:** QA verdict over A1–A6 with the bug-surface statement, **committed on
`feature/0.4.4`** — this closes the segment; nothing is merged and no `rc` is burned (D8).
`software-architect` rules **AR-2**: the before/after count of enforcement points, and an
explicit refusal of any dual path (a hook remnant plus a CI job).

**Done criterion:** QA artifact committed on the branch; AR-2 ruling recorded; no dual path.

**Parallelism:** none.

*(T-044-12 retired at the D8 restructure — a per-segment merge no longer exists.)*

---

## Segment `S2` — the rules→skills governance map

- [x] **T-044-13 — FR7: the JSON map and its schema**

**Owner role:** ai-engineer · **Commit:** `feat(T-044-13): the rules-to-skills map`

**Preconditions:** T-044-11 `[x]` (`S1` closed on the branch).

**Write set:** `dadaia_workspace/public/entities/rules-skills-map.json` + its schema,
manifest, projections.

**Description:** Rows of `{topic, section, skills[], justification}`, key = the **bold
topic** of `DADAIA.md` (G9). Seed with the gitflow row and the scan's §F rows. One skill per
topic; two only with a justification; every skill on disk placed.

**Done criterion:** A7.1–A7.4 hold.

**Parallelism:** none.

---

- [x] **T-044-14 — FR8: the map is core law**

**Owner role:** ai-engineer (scaffold) + product-engineer (`specs/constitution.md`) ·
**Commit:** `docs(T-044-14): declare the rules-to-skills map as core law`

**Preconditions:** T-044-13 `[x]`; **operator confirmation** for the `specs/constitution.md`
edit (approval of the SPEC, per D-8/§8).

**Write set:** `specs/constitution.md`, `dadaia_workspace/public/scaffold/constitution.md`,
`dadaia_workspace/public/data/DADAIA.md` (§9 pointer), projections.

**Done criterion:** A8.1–A8.3 hold.

**Parallelism:** none.

---

- [x] **T-044-15 — FR9: one enforcer, and one retirement**

**Owner role:** software-engineer (the test) + ai-engineer (the script retirement) ·
**Commit:** `feat(T-044-15): one map enforcer replaces the skill-collision lint`

**Preconditions:** T-044-14 `[x]`.

**Write set:** `tests/contract/test_rules_skills_map.py` (+ fixtures),
`dadaia_workspace/public/scripts/lint-skill-collisions.py` (**deleted**), manifest,
projections, `tests/contract/test_public_scripts_thin_wrapper.py` docstring if it names the
retired script.

**Description:** The test carries **every** invariant of A9, including the activation-overlap
check the retired script owned (D4). The retirement lands in the **same commit** as the test
so coverage never gaps; the script's `--self-test` fixtures are ported.

**Done criterion:** A9.1–A9.5 hold; six mutation fixtures each turn the test red.

**Parallelism:** none.

---

- [x] **T-044-16 — `S2` QA close**

**Owner role:** qa-engineer · **Commit:** `chore(T-044-16): S2 qa review`

**Done criterion:** QA artifact over A7–A9 **committed on the branch**, with the bug-surface
statement. No merge, no PR.

*(T-044-17 retired at the D8 restructure.)*

---

## Segment `S3` — core skills consolidation

- [x] **T-044-18 — FR10: fold `dd-release-closure` into `dd-release-implement`**

**Owner role:** ai-engineer · **Commit:**
`docs(T-044-18): fold release closure into release implement`

**Preconditions:** T-044-16 `[x]` (`S2` closed on the branch).

**Write set:** `public/skills/dd-release-implement/**` (SKILL.md + siblings),
`public/skills/dd-release-closure/` (**deleted**), every pointer (`DADAIA.md`,
`dd-backlog-definition`, `dd-release-definition`, `dd-audit-project`, `dd-gitflow-default`,
agents), manifest, registry, projections, map row.

**Done criterion:** A10.1–A10.3 hold, with the section-by-section coverage table as evidence.

---

- [x] **T-044-19 — FR11: `dd-ai-eng-knowhow` replaces four skills**

**Owner role:** ai-engineer · **Commit:**
`docs(T-044-19): one AI-harness skill replaces four`

**Preconditions:** T-044-18 `[x]`.

**Write set:** `public/skills/dd-ai-eng-knowhow/**` (new), the four retired folders
(deleted), `public/data/DADAIA.md` §2 line, every agent referencing `harness-primitives`,
manifest, registry, projections, map row. Capture **V5**.

**Done criterion:** A11.1–A11.4 hold.

---

- [x] **T-044-20 — FR12: four renames, one commit each, plus `dd-grill-me` ratified** (033bc6f7 dd-grill-me, 14746d8d dd-cli-library incl. dead-verb `hotfix` fix, 7c608ea9 dd-manager-orchestration, e563ab2a dd-workspace-doctor; map enforcer 15/15 green after every commit; V6 captured)

**Owner role:** ai-engineer · **Commits:** one per skill,
`docs(T-044-20): rename <old> to <new>`

**Preconditions:** T-044-19 `[x]`.

**Write set (per commit):** the skill folder, manifest, registry, map row, every referencing
file, projections.

**Description:** `dadaia-grill-me`→`dd-grill-me` (ratifying the worktree uplift with its
sibling files), `dadaia-cli`→`dd-cli-library` (**verified against the live command tree** —
a named verb that no longer exists is a defect fixed here),
`project-orchestration`→`dd-manager-orchestration`,
`dadaia-workspace-doctor`→`dd-workspace-doctor`. The map enforcer must be green after
**every** commit. Capture **V6**.

**Done criterion:** A12.1–A12.4 hold.

---

> **T-044-54 … T-044-60 — Amendment 1 (Aprovado, operator 2026-08-23).** The audit's sections **B** and **C**, in
> the only satisfiable order: trims → disclosures → invocation model → the persona pass →
> the sediment sweep (whose citation check lands **last**, green at HEAD) → the double-load
> bug → `ctx_inject`. All of it **before T-044-21**, so the projected inventory is
> regenerated **once** (SPEC D11, AR-1). None is reservable before the operator approves
> the amendment.

- [x] **T-044-54 — FR25: the four kept skills are trimmed**

**Owner role:** ai-engineer · **Commit:** `docs(T-044-54): trim the four skills the audit keeps`

**Preconditions:** T-044-20 `[x]`; Amendment 1 `Aprovado`.

**Write set:** `public/skills/{dd-grill-me,dd-gitflow-default,dd-release-implement,dd-bug-registration}/**`,
`public/agents/software-architect.md` (the grill-cadence alignment only), projections.

**Description:** Align the architect persona to the skill's frontier-per-round cadence
(delete "One question per turn"); remove the private worked example (a `v0.4.2` merge sha)
from `dd-gitflow-default` and give each milestone a checkable "done"; delete
`dd-release-implement`'s false "exists nowhere else" claim and leave the cadence one home;
cut `dd-bug-registration` §6–§7. Capture **V17** before and after.

**Done criterion:** A25.1–A25.5 hold; the four skills are net-negative in lines.

**Parallelism:** none.

---

- [x] **T-044-55 — FR26 (+FR10 A10.4): depth moves to sibling files**

**Owner role:** ai-engineer · **Commit:** `docs(T-044-55): disclose skill depth to siblings`

**Preconditions:** T-044-54 `[x]`.

**Write set:** `public/skills/dd-release-implement/CLOSURE-TEMPLATE.md` (new sibling),
`public/skills/{dadaia-handoff-emitter,dd-backlog-definition,dd-audit-project,dadaia-test-stewardship}/**`
(+ their new siblings), `public/agents/project-auditor.md` (the dimension list), manifest,
projections, map rows.

**Description:** Five moves, each a **move**, not a copy: the CLOSURE template out of the
folded skill's body; the handoff field tables and both JSON examples replaced by a pointer
at `.dadaia/agentic/schemas/handoff-v1.schema.json`; `dd-backlog-definition` §7 deleted (its
declaration lives in `rules-skills-map.json`, enforced once — D4/D10); the audit rubric to
`RUBRIC.md` with **one** dimension list reconciled against the `project-auditor` persona;
the stewardship numeric parameters to a file. Every moved block stays reachable by a named
pointer from `SKILL.md`. Capture **V17**.

**Done criterion:** A26.1–A26.5 and A10.4 hold; nothing disclosed is unreachable.

---

- [x] **T-044-56 — FR28: the invocation model**

**Owner role:** ai-engineer (frontmatter) + software-engineer (the enforcer check) ·
**Commit:** `docs(T-044-56): user-invoked skills and operative dependency form`

**Preconditions:** T-044-55 `[x]`.

**Write set:** every `SKILL.md` frontmatter, the FR9 contract test, projections.

**Description:** A skill no persona's `skills:` allowlist grants to a model carries
`disable-model-invocation: true` and a human-summary description (`dd-audit-project` first).
Operative dependencies become **"Call the Skill tool with `<name>`"**; a pure reference
pointer stays prose. The equivalence is checked **in both directions** inside FR9's test —
no hand-kept list. Capture **V16**.

**Done criterion:** A28.1–A28.4 hold.

---

- [x] **T-044-57 — FR24 + FR29: the persona pass, in one touch per file**

**Owner role:** ai-engineer · **Commit:**
`docs(T-044-57): personas carry only what the law does not, and state the bug-surface delta`

**Preconditions:** T-044-56 `[x]`.

**Write set:** all nine `public/agents/*.md`, `public/entities/registry.json` if a mandate
line moves, projections.

**Description:** **One pass per persona file** (A29.6): cut what `DADAIA.md` already states
(Step 0 → one pointer, handoff-first, NO-LOCKS, the `[SCOPE ERROR]`/"workflows" blocks, the
push rule already pointered by FR5, the four "Intake routing" copies, the `constitution §N`
citations), rewrite "Hard rules" as **positive targets**, and add the **bug-surface axis**
as a required verdict field to `code-reviewer`, `qa-engineer` and `software-architect`.
Produce the **coverage table** — per removed block, its surviving home — as the commit's
evidence; a fact with no other home stays. Capture **V17** (lines) and **V15** (negations).

**Done criterion:** A24.1–A24.4 and A29.1–A29.6 hold; every persona is 120–220 lines and
the coverage table is complete.

**Parallelism:** none — nine files, one pass.

---

- [x] **T-044-58 — FR27: the 25 sediments, and the citation check**

**Owner role:** ai-engineer (content) + software-engineer (the check) · **Commit:**
`fix(T-044-58): every cited path and command exists, and a check keeps it that way`

**Preconditions:** T-044-57 `[x]` — seven of the sediments live in the personas.

**Write set:** the remaining skill/persona texts carrying a sediment, the FR9 contract test
(the citation check), fixtures, projections.

**Description:** Work A27.1–A27.19 as a checklist, one grep per line; where FR10/FR11
already deleted the file that carried an item, **state that** rather than assume it. Then
land the citation check **inside FR9's test** (D4/D10): resolve every cited path (`test -e`)
and every cited `dadaia` verb (`--help`), failing on the first that does not exist. It must
be **green at HEAD the moment it lands** — which is why it is last.

**Done criterion:** A27.1–A27.20 hold; a planted dead citation turns the check red.

---

- [x] **T-044-59 — FR31 / bug (Arm B): the law is loaded once per harness**

**Owner role:** software-engineer · **Commit:**
`fix(T-044-59): project the law once per harness`

**Preconditions:** T-044-58 `[x]`; **before** T-044-21 (D11 — this changes the projected
inventory).

**Write set:** `dadaia_workspace/features/public/**` and/or
`infrastructure/public_assets/**`, tests, `specs/bugs/bugs.jsonl`.

**Description:** Bug `dadaia-md-projected-twice-into-claude-code-context` (MEDIUM). The
whole law is in a Claude Code session twice — root import chain **and**
`.claude/rules/DADAIA.md`, ~3.3k duplicated tokens per turn. Reproduce first, then fix at
the **projection seam** with one decision (which harness receives the rules-dir mirror) —
never a per-file exclusion inside the installer. **Verify `.codex/` and `.kimi-code/`** for
the same double load and record the result per harness, including "was already single". No
harness may end with zero copies.

**Done criterion:** A31.1–A31.6 hold; `resolved` event appended; bug `Closed`.

---

- [x] **T-044-60 — FR30: `ctx_inject` stops restating the law**

**Owner role:** software-engineer · **Commit:**
`fix(T-044-60): the per-prompt injection carries state, not restatement`

**Preconditions:** T-044-59 `[x]`.

**Write set:** `dadaia_workspace/hooks/ctx_inject.py`, its tests.

**Description:** Delete the four-point dispatcher preflight (a restatement of `DADAIA.md`
§1/§2) and print the ALIVE context list **only when the session is unbound**. The lean
memory prefix (tech-stack verbatim + `catalog.json`) is untouched — this removes
restatement, never memory. Capture **V18** for a bound and an unbound session, on a real
session.

**Done criterion:** A30.1–A30.4 hold; ≤ 0.7k tokens for a bound session; net LOC ≤ 0.

---

- [x] **T-044-21 — FR13: one projection cycle and a deliberate golden regen**

**Owner role:** software-engineer (goldens) + ai-engineer (projection) · **Commit:**
`test(T-044-21): regenerate the install goldens for the consolidated skill set`

**Preconditions:** T-044-20 `[x]` — *(A1)* and T-044-54 … T-044-60 `[x]`, so **every**
content and inventory change of this segment is absorbed by **one** regen (D11).

**Write set:** `tests/unit/infrastructure/_golden/*.json`, any inventory-coupled test,
manifest, projections.

**Description:** `dadaia public stage` + `install --target all` + `doctor`; then
`UPDATE_INSTALL_GOLDENS=1` for the three goldens under `tests/unit/infrastructure/_golden/`
(the two inventory-bearing ones — `install_target_resolution_v0158.json`,
`doctor_all_four_v0158.json` — are the ones this release moves;
`panel_runtime_validation_v0158.json` must come back byte-identical, and a diff there is a
defect, not a regen). Explain **every** regenerated line in the commit message against a
named FR, with a multiset diff. Re-verify the other inventory-coupled tests
(`tests/e2e/features/test_public_pipeline.py`, `tests/integration/test_public_assets.py`,
`tests/integration/scripts/test_check_skill_orphans.py`) without weakening an assertion.
Capture **V7** and **V9**.

**Done criterion:** A13.1–A13.4 hold.

---

- [x] **T-044-22 — AR-1: architecture ruling on byte-goldens-over-inventory**

**Owner role:** software-architect · **Commit:** ruling recorded in the QA/architecture
artifact

**Preconditions:** T-044-21 `[x]`.

**Description:** Rule on the mechanism, not the regen: two goldens encode the entire
projected file inventory, so every legitimate rename forces a regen and a regen is exactly
where an unintended change hides; three further tests couple to the same inventory. Verdict:
keep-with-discipline, replace with a structural assertion, or split the inventory out of the
byte golden — with the bug-surface argument. Work beyond the regen is **intake**, not scope.

**Done criterion:** A13.5 — ruling recorded, disposition named.

---

- [x] **T-044-23 — FR14: the nine-skill study**

**Owner role:** ai-engineer · **Commit:** `docs(T-044-23): nine-skill disposition study`

**Preconditions:** T-044-22 `[x]` (the study reads the final inventory).

**Write set:** `.dadaia/handoff/dadaia-workspace/…-ai-engineer-nine-skill-study.handoff.json`
(+ an HTML report only if the operator asks).

**Description:** One proposal per skill — `architect-core-workflow`, `dadaia-task-manager`,
`dadaia-handoff-emitter`, `dadaia-step0-memory-bootstrap`, `dadaia-test-stewardship`,
`dadaia-workspace-spec-reviewer`, `dadaia-workspace-spec-navigator`,
`dadaia-workspace-manager`, `dev-server-registry` — naming exactly one of **Update / Fuse /
Retire / Merge**, with evidence (staleness, overlap, map topic or orphan status, size against
the ceiling) and a blast radius. **Nothing is executed** (SPEC §4.3).

**Done criterion:** A14.1–A14.4 hold; handoff validates.

---

- [x] **T-044-24 — `S3` QA close**

**Owner role:** qa-engineer · **Commit:** `chore(T-044-24): S3 qa review` — committed on the
branch; no merge, no PR.

*(T-044-25 retired at the D8 restructure.)*

---

## Segment `S4` — spec-context associated repos

- [x] **T-044-26 — FR15: the model and its v2→v3 migration**

**Owner role:** software-engineer · **Commit:**
`feat(T-044-26): a context owns one main repo and N associated repos`

**Preconditions:** T-044-24 `[x]` (`S3` closed on the branch).

**Write set:** `dadaia_workspace/core/models/spec_context.py`,
`dadaia_workspace/features/migrate/state_v2.py`, the registry schema, tests.

**Description:** Ordered `associated_repos` (slug + url) next to the unique main repo; the
schema bumps v2→v3 with a backup-first, idempotent migration. **One accessor** serves every
consumer (A15.3) — no second repo-resolution path is created. Capture **V8**.

**Done criterion:** A15.1–A15.3 hold.

---

- [x] **T-044-27 — FR16: ALIVE/DEAD covers every repo**

**Owner role:** software-engineer · **Commit:**
`feat(T-044-27): alive and dead cover the whole repo set`

**Preconditions:** T-044-26 `[x]`. **Write set:** `features/spec_context/**`, tests.

**Done criterion:** A16.1–A16.4 hold.

---

- [x] **T-044-28 — FR17: `context repo add/remove/list` and `create --associated`**

**Owner role:** software-engineer · **Commit:** `feat(T-044-28): context repo verbs`

**Preconditions:** T-044-27 `[x]`. **Write set:** `cli/commands/context.py`, tests.

**Done criterion:** A17.1–A17.3 hold.

---

- [x] **T-044-29 — FR18: `show`, `list`, export/import, panel — and the superseded bug**

**Owner role:** software-engineer · **Commit:**
`fix(T-044-29): one branch resolution for context list and show, plus the associated repo surfaces`

**Preconditions:** T-044-28 `[x]`.

**Write set:** `cli/commands/context.py`, `features/export/service.py`,
`features/panel/service.py`, tests, `specs/bugs/bugs.jsonl`.

**Description:** Carries the acceptance of the superseded bug
`context-list-current-branch-stale-for-alive-repo`: `list` and `show` must resolve
`current_branch` through **one** implementation (A18.3) — not by adding a refresh call to
`list`. Its repro is the RED test. Then the associated-repo columns, the export round-trip
and the panel card.

**Done criterion:** A18.1–A18.5 hold; the bug is `Closed` with
`superseded_by: spec-context-associated-repos`.

---

- [x] **T-044-30 — FR19: one place of control**

**Owner role:** software-engineer · **Commit:**
`test(T-044-30): only the main repo carries specs, bind and memory`

**Preconditions:** T-044-29 `[x]`. **Write set:** tests; production code only if a leak is
found.

**Done criterion:** A19.1–A19.2 hold, proven with an associated repo that carries its own
`specs/`.

---

- [x] **T-044-31 — `S4` QA close** · **Owner role:** qa-engineer ·
**Commit:** `chore(T-044-31): S4 qa review` — committed on the branch; no merge, no PR.

*(T-044-32 retired at the D8 restructure.)*

---

## Segment `S5` — the bug sweep and branch hygiene

Every bug task in this block is Arm B on `feature/0.4.4`: reproduce → RED → root-cause fix →
GREEN → `resolved` event with `--resolution-evidence` → commit. **Owner role:**
software-engineer, unless stated. Each diff must leave its feature **smaller or equal**.

> *(A1)* **T-044-61 and T-044-62 open the segment**, so the eight fixes below are the first
> work run under the method and the gate. Both are Draft until Amendment 1 is approved; if
> the operator approves the amendment after the sweep has started, the remaining fixes still
> adopt them from that point, and the ones already closed are restated in CLOSURE (A23.4).

- [x] **T-044-61 — FR22: `dd-bug-fix` §3–§5 becomes a method**

**Owner role:** ai-engineer · **Commit:**
`docs(T-044-61): root cause becomes a method with a Done when per phase`

**Preconditions:** T-044-31 `[x]` (`S4` closed); Amendment 1 `Aprovado`.

**Write set:** `public/skills/dd-bug-fix/**` (+ a sibling if depth is disclosed), map row,
projections.

**Description:** Rewrite §3–§5 as the six phases, each ending in a checkable **"Done when"**
(SPEC FR22): red loop before any hypothesis → minimise until load-bearing → 3–5 falsifiable
hypotheses → instrument, never read code for a theory → regression test **at the correct
seam** → cleanup. State once: *"no correct seam exists → register an architecture finding
and dispatch `software-architect` before fixing"*. Delete the stale "still being designed"
line and fix the description's grant claim. **No new skill** — the method lives here
(SPEC §4.10).

**Done criterion:** A22.1–A22.5 hold; the skill is net-negative in lines.

---

- [x] **T-044-62 — FR23: the `resolved` event refuses evidence that cannot be checked**

**Owner role:** software-engineer (CLI + schema) + ai-engineer (skill + law wording) ·
**Commit:** `feat(T-044-62): resolved evidence carries the loop, the seam and the diff direction`

**Preconditions:** T-044-61 `[x]`.

**Write set:** `dadaia_workspace/cli/commands/bugs.py`, the `bug-event-v1` schema and its
feature module, tests, `public/data/DADAIA.md` §6 (source only) + projections,
`public/skills/dd-bug-fix/**`.

**Description:** RED first: today an evidence-free `resolved` is accepted (132 of 438 on
disk are exactly that). Then the refusal — **one validation inside the existing append
path**, no second command and no bypass flag — for the three fields: the red-loop command,
the test seam, and the **diff direction** (lines/branches/flags added vs removed on the
touched feature). A net-positive diff routes to `software-architect` **before** the commit;
the law says it once (§6), `dd-bug-fix` operates it. Historical events stay readable and are
never rewritten.

**Done criterion:** A23.1–A23.6 hold; `S5`'s first bug appends a well-formed event on the
first try.

---

- [x] **T-044-33 — bug `backlog-doctor-silent-on-duplicate-top-level-sections` (MEDIUM)**

**Commit:** `fix(T-044-33): the backlog parser refuses duplicate top-level sections`

**Write set:** `dadaia_workspace/features/backlog/document.py`, `doctor.py`, tests.
**Description:** `_top_level_sections()` uses `dict.setdefault`, so a duplicated `## ACTIVE`
/ `## LEDGER` is silently dropped and duplicate slugs are never compared. Fix at the parser:
the document schema says exactly two top-level sections — make the parser say so too, rather
than adding a second validation pass.
**Done criterion:** the duplicated-document repro is a RED test that goes GREEN; `Closed`.

**Resolution:** Fixed at the parser only (`document.py`), `doctor.py` untouched —
`_top_level_sections` now returns EVERY occurrence's body range per heading name (was
`dict.setdefault`, first-wins) plus a located `DocumentError` for a repeated top-level
heading; `load_document` parses all of them, so a duplicated slug reaches the doctor's
existing (already-correct) BL-DUP check instead of the second copy vanishing. RED-to-GREEN
seam: `tests/unit/features/backlog/test_document.py::test_duplicate_top_level_active_heading_yields_document_error_and_parses_both_bodies`
(+ LEDGER sibling; end-to-end integration test in `test_backlog_doctor.py`). Full suite:
2756 passed, 4 pre-existing skips. Diff is net-positive (+52/-20, one file) — flagged in the
`resolved` event per FR23/`dd-bug-fix` for a `software-architect` review before this lands
past this commit; `bugs.jsonl` carries the evidence.

---

- [x] **T-044-34 — bug `backlog-doctor-rejects-deferred-status-documented-by-skill` (LOW)**

**Commit:** `fix(T-044-34): one statement owns the deferred status`

**Preconditions:** T-044-33 `[x]` (same file; shared root — the doctor's ACTIVE-status
vocabulary). **Write set:** `features/backlog/doctor.py` or
`public/skills/dd-backlog-definition/SKILL.md`, tests.
**Description:** The skill lists `deferred` as a valid ACTIVE status; the doctor calls it
BL-STALE. **One** of the two is wrong — decide, state it once, and delete the other
statement. Do **not** add a compatibility branch.
**Done criterion:** a `deferred` ACTIVE entry either validates or is refused by a rule the
skill states; `Closed`.

**Resolution:** `deferred` is one of `core.models.backlog.TERMINAL_DISPOSITION_TOKENS` —
`dd-backlog-definition` SKILL.md's own §2 "Terminal disposition tokens" table already
lists `DEFERRED` as LEDGER-only, and the real `BACKLOG.md` never carries an ACTIVE
`deferred` entry today. The skill's ACTIVE `- **Status:**` enumeration line contradicted
its own table; `doctor.py`'s BL-STALE check was already correct — untouched. Fixed at the
skill only: `- **Status:** idea | candidate | deferred` → `idea | candidate` (1 line
changed, net-negative — no branch/flag added, `doctor.py` and its behaviour unchanged).
RED-to-GREEN seam: `tests/contract/test_backlog_status_vocabulary_contract.py::test_skill_active_status_enumeration_excludes_terminal_disposition_tokens`
(reads the real shipped SKILL.md against the real `TERMINAL_DISPOSITION_TOKENS`); the
literal bug repro is pinned by
`tests/integration/test_backlog_doctor.py::test_deferred_active_status_fires_bl_stale`.
Projection cycle run (`public stage` + `install --target all` + `public doctor` exit 0);
contract tier green (209 passed). Full suite: 2789 passed, 4 pre-existing environment
skips, 0 failures. `bugs.jsonl` carries the FR23 evidence.

---

- [x] **T-044-35 — bug `atomic-writer-drift-guard-is-brittle-and-covers-only-two-of-eight-writers` (LOW)**

**Commit:** `test(T-044-35): a behavioural battery over every atomic writer`

**Write set:** `tests/unit/features/specs/test_migration_symlink_hardening.py` (and/or its
replacement), tests only.
**Description:** Replace the text-slicing guard with a **behavioural** battery parametrized
over every atomic writer: mode preservation, LF bytes on disk, no leftover temp file on an
injected failure, hardlink rebinding. The text comparison is deleted, not extended.

**Resolution:** Deleted `test_the_two_atomic_writers_do_not_drift` (the `inspect.getsource`
+ triple-quote-split comparison, 2 of 8 writers). Enumerated the package's 8 atomic-writer
primitives by grepping the `^def _*atomic\b` / `^def _*write.*atomic` naming pattern
(`write_text_atomic`, `_write_text_atomic`, `atomic_write_text`, `_atomic_write_text` x2,
`_atomic_write_json`, `_atomic_write`, `_atomic_write_bytes`) — matches the bug's stated
count exactly. Replaced with an `AtomicWriterCase` registry calling each writer at its real
entry point, parametrized over 4 behavioural dimensions (hardlink rebinding, CRLF-free
bytes, mode preservation, no leftover temp on an injected `os.replace` failure) — 32 test
items. Every per-writer expectation (`preserves_mode`/`cleans_up_on_failure`/
`lf_bytes_guaranteed`) was verified empirically (scratch probe script, not committed)
before being pinned, not assumed from reading source. That probing surfaced 2 genuine
production gaps, out of this task's tests-only write set: `hooks/_common.py:
atomic_write_text` and `infrastructure/public_assets_common.py:_atomic_write_text` leak
their `.tmp` sibling on an injected `os.replace` failure (6 of 8 writers wrap the swap in
try/except-cleanup; these 2 do not) — registered as bug
`two-atomic-writers-leak-temp-file-on-injected-os-replace-failure` (LOW) and pinned as
CURRENT (leaking) behaviour in the new battery rather than silently asserted away. Mode
preservation and CRLF-freedom assertions are Windows-aware (self-referential before/after
comparison + `sys.platform` skip, mirroring `test_repair_preserves_file_mode_and_newlines`)
— this repo's CI runs unit tests on windows-latest/macos-latest, so a POSIX-only assertion
would have reproduced the `mode-preservation-test-asserts-posix-only` gotcha class.
Red-loop evidence: replayed the OLD comparison algorithm against `write_text_atomic`'s real
source with only a comment reworded — identical behaviour, OLD guard reported a spurious
mismatch (bug repro step 1). Full suite: 2787 passed, 4 pre-existing skips. Diff is
net-positive (+279/-15, one file, tests-only) — flagged in the `resolved` event per
FR23/`dd-bug-fix` for a `software-architect` review before this lands past this commit
(growth is coverage expansion, 2→8 writers / 0→4 dimensions, mandated by this task's own
Done criterion — no production code touched); `bugs.jsonl` carries the evidence.
**Done criterion:** the battery covers all 8 writers; the brittle comparison is gone;
`Closed`.

---

- [x] **T-044-36 — bug `crlf-fixture-makes-a-windows-assertion-pass-for-the-wrong-reason` (LOW)**

**Write set:** the same test module.
**Description:** Write the fixture with an explicit `newline=` so its bytes are known on
every platform and the assertion can only fail for the reason it names.
**Done criterion:** the assertion is platform-independent; `Closed`.

**Resolution:** Swept all 16 `write_text()` call sites in
`test_migration_symlink_hardening.py` for the class (fixture write with no `newline=`
feeding a byte-sensitive downstream assertion) — found exactly one instance, unchanged
by T-044-35: `test_repair_preserves_file_mode_and_newlines`'s fixture write at the line
feeding `assert b"\r\n" not in atom.read_bytes()`. Fixed by adding explicit `newline=""`
(1 line modified, net-neutral), matching the same idiom this module's own
`AtomicWriterCase` registry already uses for its `lf_bytes_guaranteed=True` writers. The
other byte-sensitive assertion in the module
(`test_atomic_writer_never_leaves_crlf_bytes`) writes to a fresh un-fixtured path and is
already platform-guarded — not in class. A literal Windows red repro is unreproducible on
this Linux runner (confirmed empirically: monkeypatching `os.linesep` has no effect on
CPython's `Path.write_text` newline translation); root cause instead fully specified by
the documented `newline=None` contract. Full suite: 2792 passed, 4 pre-existing
environment skips, 0 failures. `bugs.jsonl` carries the FR23 evidence.

---

- [x] **T-044-37 — bug `migration-normalises-crlf-atoms-to-lf-contradicting-its-byte-preserve-wording` (LOW)**

**Commit:** `docs(T-044-37): the migration states its newline contract`

**Write set:** `dadaia_workspace/features/migrate/frontmatter_keys.py`, tests.
**Description:** Decide-then-state: either the migration is LF-canonical (consistent with
the projection contract) and says so, or it byte-preserves and the writer changes. Pin
whichever is chosen with a test. No third behaviour.
**Done criterion:** docstring and behaviour agree, pinned by a test; `Closed`.

**Resolution:** DECIDED (a) — LF-canonical, wording changes; behaviour is unchanged.
Evidence: `write_text_atomic` already guarantees LF bytes on disk on every platform
(`newline=""`, pinned `lf_bytes_guaranteed=True` for this exact writer in T-044-35's
battery); `infrastructure/public_assets_common`'s writer makes the identical guarantee for
projected assets (FR-RC2-2) — LF-canonical is this repo's platform-wide write contract for
managed files, not a one-off. Reproduced the repro verbatim against unmodified HEAD (CRLF
atom + retired key through `migrate_retired_frontmatter_keys`): output was already LF-only
— the composition was correct, only the module docstring's "byte-preserve everything else"
wording contradicted it. Root cause, precisely: `strip_frontmatter_keys` and
`write_text_atomic` are themselves line-ending AGNOSTIC (fed CRLF directly, both reproduce
it verbatim — pinned by
`test_strip_frontmatter_keys_preserves_crlf_given_directly`/`test_write_text_atomic_preserves_crlf_given_directly`);
the LF-canonicalisation is entirely a side effect of the caller's `Path.read_text()`
(universal-newline translation) composed ahead of this module, in every registered step.
Fixed the module docstring in `frontmatter_keys.py` to state the newline contract
explicitly and name the mechanism (0 executable lines touched, docstring-only,
net-neutral). Pinned end-to-end by
`test_migration_normalises_a_crlf_atom_to_lf_on_disk` (new file
`tests/unit/features/migrate/test_frontmatter_keys.py`, 3 tests, 79 lines) via the real
`migrate_retired_frontmatter_keys` pipeline. Full suite: 2792 passed, 4 pre-existing skips.

---

- [x] **T-044-38 — bug `no-ratchet-against-frozen-clock-tests-that-age-fixtures-by-the-real-clock` (LOW)**

**Commit:** `test(T-044-38): a ratchet against frozen-clock aging`

**Write set:** one source-scan contract test, in the shape the repo already uses for the
denylist no-allowlist contract.
**Description:** Fail any `tests/**` file that declares a frozen datetime constant **and**
calls `time.time()`/`datetime.now()`. Green at HEAD against all 9 aging sites.
**Done criterion:** the ratchet is green at HEAD and red on a planted violation; `Closed`.

**Resolution:** New AST-based contract test
`tests/contract/test_frozen_clock_aging_ratchet.py` (4 tests) — a raw-text/regex scan
(the denylist no-allowlist test's own shape) would false-positive on this very module's
docstring and on `test_tmp_gc_service.py`'s own explanatory comment, both of which
contain the literal text `time.time()` in prose, so detection is AST-based instead
(mirrors `test_core_file_io_purity.py`'s file-I/O ratchet for the identical reason).
Rule: a `tests/**` file fails iff it declares, at module level, BOTH a frozen
datetime/date constant (a constant-case name assigned a `datetime(...)`/`date(...)`
literal, or — only when the name itself carries a clock marker — a bare numeric/ISO-date
literal) AND a real-clock call (`time.time()` or a `.now()` call chaining to
`datetime`). Verified GREEN at HEAD: cross-referenced all 10 `tests/**` files performing
fixture ageing via `os.utime` — `test_tmp_gc_service.py` and the two retention test
modules derive every mtime from their OWN frozen constant (self-consistent, the tmp_gc
fix already landed); the other 7 derive from a real-clock call with no frozen constant
in the same file (both sides move together); `test_jsonl_log_rotation.py` ages to the
literal Unix epoch (a local var, not a module constant) — self-healing by construction.
0 violations across the entire `tests/**` tree (2803 tests collected). Mutation-sanity
fixture (in-memory, never a repo file — the `test_rules_skills_map.py` mutation pattern)
reproduces the tmp_gc shape (both a `time.time()` and a `datetime.now()` variant) and
proves both detectors turn RED; two negative controls prove the AND-not-OR precision
(a frozen constant alone, or a real-clock call alone, must each stay green). No
production code touched — guard-only, per the bug's own notes: the underlying tmp_gc
bug is already resolved. `evidence_diff` is `net-positive` (pure addition, no deletion)
— flagged per `dd-bug-fix` for a `software-architect` check, route-before-commit not
blocking (same posture as T-044-33/T-044-35). Full suite:
`pytest -p no:cacheprovider -q -m "not quarantine and not e2e" -n auto` → 2747 passed,
3 skipped (environment-gated), 0 failed; `ruff format --check`/`ruff check --no-cache`/
`mypy --strict` clean on the new file. `bugs.jsonl` carries the FR23 evidence.

---

- [x] **T-044-39 — bug `read-only-atom-honouring-is-advisory-and-root-bypasses-it` (LOW)**

**Write set:** `features/migrate/**` (the guard's site), tests.
**Description:** Either document the guard as advisory/best-effort, or move the check after
the no-change determination so a clean read-only atom stays silent. Prefer the smaller
diff; do not add a second permission probe.
**Done criterion:** the chosen behaviour is stated once and pinned; `Closed`.

---

- [x] **T-044-40 — bug `symlinked-specs-root-is-followed-by-migration-and-repair` (LOW)**

**Write set:** the context-resolution seam, tests.
**Description:** One deliberate decision applied **once at the resolution seam** — resolve
the named root knowingly, or refuse a symlinked root as the inner walk roots are refused.
Never duplicated into each write site.
**Done criterion:** the decision is implemented at one seam, documented, and pinned for both
`specs upgrade` and `specs doctor --fix`; `Closed`.

---

- [x] **T-044-41 — [git] FR20: branch hygiene on `origin` and locally**

**Owner role:** dispatcher · **Commit:** none (git refs) — capture **V10** before and after.

**Preconditions:** T-044-33 … T-044-40 `[x]`.

**Description:** For each slop branch — `chore/*` ×7, `feature/pi-fourth-harness-v1`,
`feature/v0.1.10`, `feature/0.1.5`, `0.1.7`, `0.1.8`, `0.2.0`, `0.2.1`, `0.4.2` — tag
`archive/<name>`, **prove reachability by the tag**, then delete the branch. Delete local
`hotfix/0.4.3` (its work is merged and published as `CHANGELOG [0.4.3]`). Tag pushes use the
carve-out; no `--no-verify`.

**Done criterion:** A20.1–A20.4 hold; V10 shows `origin` carrying `main`, `develop`,
`feature/0.4.4` and archive tags only.

---

- [x] **T-044-42 — `S5` QA close** · **Owner role:** qa-engineer ·
**Commit:** `chore(T-044-42): S5 qa review` — committed on the branch; verdict states the
bug-surface delta per bug. No merge, no PR.

**Resolution:** APPROVE. All 8 sweep bugs independently re-confirmed `resolved` with
complete FR23 evidence; every named pinning test re-run GREEN by name this session; all
4 architect firings re-read, SOUND, no puxadinho. FR23 gate re-proven live (A23.6):
missing-field `resolved` append refused by field name, well-formed accepted first try,
against a throwaway tmp specs dir, live ledger untouched. T-044-41/A20 independently
re-verified: origin heads = main+develop only, 50 archive tags, 3 spot-checked tags
resolve to real commits, local branches = the 3 permitted patterns, local `hotfix/0.4.3`
confirmed absent. Full gates green: ruff format/check clean, mypy --strict clean (273
files), full suite 2803 passed / 4 skipped (environment-gated) / 0 failed. Self-scan
(`tests/integration/test_repo_self_scan.py`) green against the close artifact itself
before commit. 6 bugs open at close (2 S5-adjacent by architect design, 4 foreign,
outside every S5 write set) — none blocking; full record + 7 accumulated intake
candidates in `specs/releases/v0.4.4/reviews/S5-qa-close.md` §4 for the PM's intake
feed.

*(T-044-43 retired at the D8 restructure.)*

---

## Scope complete — the release is closed by QA

- [ ] **T-044-44 — FR21: the invariants, measured**

**Owner role:** software-engineer + qa-engineer · **Commit:**
`chore(T-044-44): scope-complete gate capture`

**Preconditions:** T-044-42 `[x]` — all five segments closed on the branch.

**Description:** Run every gate; capture **V11** (production LOC per segment) and **V12**
(`dadaia bugs status`). A21.4's negative net is measured here, or its justification is
drafted for CLOSURE. *(A1)* Also capture **V14** (always-on tokens), **V15** (negations),
**V16** (description bytes), **V17** (per-skill/per-persona lines), **V18** (injected prefix,
bound and unbound) and **V19** (AI-surface LOC) — the evidence for A21.8–A21.11. A positive
AI-surface net is a **defect**, not a CLOSURE note: it is fixed here or ruled on by the
operator before ship.

**Done criterion:** A21.1–A21.6 hold, with evidence; *(A1)* A21.8–A21.11 hold, measured.

---

- [ ] **T-044-45 — Six-axis code review on the thawed tree**

**Owner role:** code-reviewer · **Preconditions:** T-044-44 `[x]`. Runs on the **thawed**
tree, before `rc-1` and before any archive move (D8/FR5 order).

**Done criterion:** APPROVED, with the explicit bug-surface verdict per touched feature.

---

- [ ] **T-044-46 — Security review + the QA release verdict ("closed by QA")**

**Owner role:** security-reviewer + qa-engineer · **Preconditions:** T-044-45 `[x]`.

**Description:** Diff-based security review covering the release delta and the `rc-1` PR
head sha. Special attention: the relocated verdict gate (no coverage hole between the
retired hook step and the CI job) and the branch-hygiene tag/delete sweep. `qa-engineer`
then issues the **release verdict** over the whole scope — the operator's "release fechada
pelo QA", which is the trigger for milestone (b).

**Done criterion:** APPROVED security handoff covering the PR head sha + the QA release
verdict recorded.

---

## `rc-1` — milestone (b), the release integrates

- [ ] **T-044-52 — [git] `rc-1`: PR `feature/0.4.4` → `develop` (first v2 merge)**

**Owner role:** dispatcher + security-reviewer · **Preconditions:** T-044-46 `[x]`.

**Description:** Push `feature/0.4.4` (permitted since `S1`), open the PR to `develop` with
the APPROVED verdict covering the **PR head sha**, watch CI to green, merge. That merged
`develop` **is `rc-1`** (G4/D8) — the first and only integration of the whole scope. The
verdict gate is advisory on this PR (A4.4); the operator sets it **required** before any
`rc-2`, re-supplying the required-checks list whole.

**Done criterion:** PR merged; CI green; APPROVED verdict recorded; `develop` carries the
whole scope.

**Parallelism:** none.

---

## `rc-2 … rc-N` — adjustment rounds on the merged scope

- [ ] **T-044-53 — Adjustment rounds: test `develop`, fix on the branch, merge again**

**Owner role:** qa-engineer + operator (finding) · software-engineer / ai-engineer (fixing) ·
dispatcher + security-reviewer (merging) · **Preconditions:** T-044-52 `[x]`.

**Description:** The merged `develop` is exercised — by the operator, by QA, by anyone. Each
finding **on this release's scope** becomes an adjustment, fix or improvement worked on
`feature/0.4.4`, QA-closed, delta-reviewed (code + security) and merged again by PR: one
`rc` per merge. **No new backlog enters an `rc`** (A21.7/R-8) — a demand outside this scope
is backlog for a later release, recorded for the PM's intake, never worked here. Repeat
until the operator and QA accept a candidate as final. **This task may close with zero
rounds**, in which case the final `rc` **is** `rc-1`.

**Done criterion:** every round has a QA close, a delta review, a merge and a ledger row
(finding → who found it → fix → `rc` number) for CLOSURE; the accepted final `rc` is named.

**Parallelism:** none — one round at a time.

---

## The final `rc` — closure, archive, ship

- [ ] **T-044-47 — Memory window (SPEC §5)**

**Owner role:** product-engineer · **Commit:** `docs(T-044-47): memory after v0.4.4`

**Preconditions:** T-044-53 `[x]` (the final `rc` is accepted); `ACTIVE.md` phase `CLOSURE`.

**Write set:** the atoms named in SPEC §5 — the **two mandatory rewrites**
(`sdd-gate-v3.md`, `sdd-bug-backlog-governance.md`) **first**, then the rest, one authoring
pass per atom; `product/index.md` + `catalog.json` regenerated.

**Done criterion:** memory describes the product as it now is, with no changelog; `specs
doctor` 0 errors.

---

- [ ] **T-044-48 — `CLOSURE.md` with every sweep**

**Owner role:** product-engineer · **Commit:** `docs(T-044-48): v0.4.4 closure`

**Preconditions:** T-044-47 `[x]`.

**Description:** Per the folded `dd-release-implement` (FR10/A10.3): summary, tasks +
commits, validations, size accounting, *(A1)* **AI-surface accounting** (V19 + the measured
targets with their V-ids) and the **audit-fold record** (per audit item, the FR that carried
it; per refused item, the reason and where it went), drifts, memory updates,
**dispositions** (4 backlog `DELIVERED · v0.4.4`; **12** bugs `Closed`; 1 `Closed` +
`superseded_by`), test dispositions,
record-only vs intake, the artifact GC sweep, the **`rc` ledger** (every `rc` burned, what
was found on `develop`, by whom, and its fix — A21.7), the AR-1/AR-2 rulings, the
standing-order verdict record, the restated v0.4.3 git-identity question, archive decision
`MOVE`.

**Done criterion:** every closure obligation in SPEC §5 is discharged.

---

- [ ] **T-044-49 — [git] Archive the release**

**Owner role:** dispatcher · **Commit:** `chore(T-044-49): archive v0.4.4`

**Description:** `git mv specs/releases/v0.4.4 specs/_archive/releases/v0.4.4`; set
`ACTIVE.md` to `phase: ARCHIVED`.

---

- [ ] **T-044-50 — [git] Final-`rc` merge: version bump and PR → `develop`**

**Owner role:** dispatcher + software-engineer + security-reviewer

**Preconditions:** T-044-49 `[x]`.

**Write set:** `pyproject.toml` (`0.4.3` → `0.4.4`), `CHANGELOG.md` (`[0.4.4]`, stating once
that `0.4.3` was minted locally and never published), then git refs.

**Description:** One axis: the release id **is** the package version. The memory window,
`CLOSURE.md` and the archive move ride this merge. Push `feature/0.4.4`, APPROVED verdict on
the PR head sha, PR to `develop`, CI green, merge — this burns the **final `rc`**.

---

- [ ] **T-044-51 — [git] Ship**

**Owner role:** dispatcher + security-reviewer · **Preconditions:** T-044-50 `[x]`.

**Description:** PR `develop → main`; watch CI to green; merge; publish **0.4.4** (PyPI
`0.4.2 → 0.4.4`; `0.4.3` stays retired unpublished). Then, **in the same step** (G3):
delete `feature/0.4.4` and cut **`feature/0.4.5` from `main`**. Run the reconciliation merge
of `main` into `develop`. Capture **V13** (the `SPEC-DOC-031` count **after** the archive
move). Set `ACTIVE.md` to the next release or `release: none`.

**Done criterion:** PR merged to `main`; CI green; `0.4.4` published; `feature/0.4.4` gone;
`feature/0.4.5` exists and is cut from `main`; V13 captured; worktree clean.

**Parallelism:** none — last task.
