# PLAN — Release: 0.5.0, candidate 25

**Status:** Approved
**Release ID:** 0.5.0
**Owner:** dd-sw-engineer-sr

The SPEC says what (FR1 to FR6; `AC<n>.<k>` belongs to FR`<n>`). This PLAN records the as-is review (section 1), the DAG of two jobs (the DAG heading), the dispatch (section 2), the acts that are not tasks (section 3), the consumers of every changed name and grammar (section 4), the tests of record (section 5), and the pre-mortem answers and risks (section 6).

**Evidence.** The as-is review is the read-only pass `.dadaia/handoff/dadaia-workspace/2026-10-28T012403Z-dd-sw-engineer-sr-rc25-as-is-review.handoff.json`, corrected by the `dd-researcher` pre-mortem (`.dadaia/tmp/main-thread/20261025/rc25-premortem.md`) and the main thread's ruling on it. Where this PLAN and the handoff disagree, this PLAN wins.

**Rulings carried.** The SPEC's R1 ("Remover o PR-only (Recomendado)") and R2 ("Confirmar (Recomendado)"), grill handoff `2026-10-28T012556Z-main-rc25-grill`; ADR 0283 (proposed; the operator accepts it with SPEC and PLAN, before any Job 2 task); the main thread's ruling that baseline `_publish` creates the local `refs/heads/<role>` at the tip and pushes it by name.

## 1. As-is review

DELETE, REBUILD, UPDATE, KEEP, ADD last. No unit here is ADD. `bugs.py stats` reports no REBUILD due on a unit this candidate touches (SPEC, Bug window review); the REBUILD rows below are the ones the demand forces.

| unit | today | bugs | verdict | why |
|---|---|---|---|---|
| `features/chokepoints/branch_policy.py` `_refuse_branch` principal/integration arm (:136-139) and role-birth arm (:109-119) | refuses every direct push of principal or integration ("advances only via a PR", fix "open a PR/MR … on your git host"); refuses a birth onto an origin holding the other role | `public-law-teaches-the-private-pipeline` (44d9f4a1f reworded the fix line only), `gitflow-law-refuses-the-release-pr-…` (4a473a049 kept :136), `pre-push-refusal-misnames-the-pushable-set-…` (ed36aed70 rebuilt only the role-None arm) | DELETE | R1 and ADR 0214: both arms are the requirement. `_refuse_branch` keeps its role-None arms. Two symptom patches kept the refusal; the structural cause is ADR 0036 against ADR 0214 |
| `branch_policy.py` `check_branch_policy` (:142-170) | `births` parameter and `role in (principal, integration) and local_sha in births` | ADR 0036 | REBUILD | the condition becomes `role is None and not _pushable(branch)`; the refspec-match and not-a-head checks stay |
| `push_gate.py` `push_gate_decision` births block (:194-205); `ObjectSource.remote_branch` (:53); `ObjectSource.unpublished` row (:51) | computes `unborn`, `bootstrap`, `births` | ADR 0036 | DELETE | the birth is the general case once nothing is refused. `remote_branch`'s one reader is :199. The `unpublished` row's one gate reader is :201 (section 6, point 3) |
| `infrastructure/git_objects.py` `remote_branch` (:690-693) | offline read of `refs/remotes/origin/<branch>` | none | DELETE | dead once the block goes |
| `git_objects.py` `GitSubprocessObjectReader.unpublished` (:682-688) and module `unpublished` (:672) | class method: fail-closed wrapper; module function: the ONE range rule | none | KEEP | the module function still has readers (`git_subprocess.py:172`); the class method keeps its three tests (`test_git_objects.py`), whose removal is not in the operator's order (section 6, point 3) |
| `features/spec_context/service.py` `_publish` (:615-649) | pushes `<origin/principal or anchor>:refs/heads/<role>` birth refspecs, which only the birth exemption admits | `sa-principal-branch-defaults-to-main-and-cut-point-diverges` | REBUILD | creates each missing role branch as the local head at its tip and pushes it by name (AC2.2): ordinary heads, one gate rule. Without it every birth is refused as outside the gitflow (pre-mortem 1). The needs-`origin` sites stay out (SPEC non-goals) |
| `cli/commands/ci.py` `_gate_inputs`, `GateFixes` | builds work/head for fix lines | `several-work-*` family | KEEP | `fixes.work` keeps its readers (:129 role-None arm, push_gate.py:190) |
| `tests/features/chokepoints/test_branch_policy.py` | five PR-only rows (:132-136), M2 rows (:137-141), `_PR_TO_*` (:122-123), `_birth_fix` (:126-127), `_birth` (:58-64), birth rows (:108-111), `_birth_from_any_source` and row (:82-86, :112) | ADR 0036 `measured_by` | REBUILD | the PR-only and M2 rows move to the admitted table; the rest is deleted; row :136 (a tag onto the principal) stays refused with the outside-the-gitflow text; row :144 stays refused with refspec text |
| `tests/cli/commands/test_ci.py` births test (:221-276) | :255, :263 admitted; :267-276 refused | ADR 0036 | REBUILD | :267-276 flips to admitted |
| `tests/fixtures/fix_world.py` (:422-431, :1262-1269); `tests/features/chokepoints/test_push_gate.py:207`; `tests/e2e/test_push_gate_check.py` (:5, :78) | the birth Case, its helpers and the PR Skip; the `remote_branch` fake; the docstring | the refusal harness | DELETE / UPDATE | a row leaves with the refusal that owned it. `_refuse_branch` keeps its worktree-verbs Skip, so the census holds |
| `tests/core/test_cli_line__refusal_fix_lines_clear_their_refusal.py` (:178-192) | wt-task / wt-main rows | none | KEEP | covers the role-None arm only |
| `tests/features/spec_context/test_service__context_baseline.py` | rows :156, :159, :162, :187 pass today | none | UPDATE | rows stay green unchanged; one test is added for the local role heads (J2.T2) |
| `public/skills/dd-gitflow-default/SKILL.md` steps 2, 4, 8-11, line 32, §2a, §3b, §4, :4, :14 | `origin/` refs in steps 2 and 4 (exit 1 with no remote); "advances only by PR"; §3b "Both PR edges" | `gitflow-step2-…`, `gitflow-step4-…`, `gitflow-law-refuses-…`, `promote-and-release-pr-each-name-two-things`, `rc-flow-makes-the-candidate-pr-routine-…` (five records in one day, each rewording while writing `origin/` refs) | REBUILD | step 2 defines the ref once; rows are pushable; one verb "merge" in steps 8-11; §3b is the merge gate. CICD-AUTOMATION.md:3 is the evidence of the intended contract (KEEP) |
| `tests/core/test_gitflow.py` (:154, :170, :171, row parse :147-149) | pin "advances only by PR" and `== ["work"]` | `gitflow-pu3-refuses-the-job-branch-rebase-merge-prescribes` | REBUILD | repinned to the new line-32 wording; a Pushable-column assert is added (J1.T1) |
| `public/data/dadaia-AGENTS.md:25` (projects to `.dadaia/AGENTS.md`) | "admits the initial ref for either PR-only branch …" | ADR 0036 | REBUILD | the sentence goes; the hook admits the contract's pushable branches |
| `public/data/AGENTS.md` :55, :94; `CONTEXT-MAP.md:64`; `worktrees-AGENTS.md:17` | "the PR gate"; "a promote is its PR plus `release.py ship`" | `gitflow-law-refuses-…` | UPDATE | "the merge gate"; "its merge plus `release.py ship`". `worktrees-AGENTS.md:6` is the model (remote optional): KEEP |
| `public/scaffold/releases/AGENTS.md:44`; mirror `specs/releases/AGENTS.md:44`; `templates/shipped-hashes.json`; `core/specs_version.py` `CANON_AT[13]` | "Promote is merging the promote PR" | `promote-and-release-pr-each-name-two-things` | UPDATE | "the integration → principal merge (step 10)"; digest and pin ride the task (stamp 13 is unpublished) |
| `dd-release-implementation` `RC-FLOW.md` :9, :40, `SKILL.md` :4, :7; `scripts/release.py` :5, :58; `_release_tree.py:304` | "the PR gate", "the candidate PR", "records the merged promote PR" | `release-ship-requires-a-pr-number` (`--pr` optional) | UPDATE | wording only. `SHIP_PR` (`_release_phase.py:116`) already says "when the host has one": KEEP, so `test_release.py:586` is untouched. `RELEASE-EVENTS.md:41` KEEP |
| `dd-code-review/SKILL.md:61`; `agents/dd-code-reviewer.md` :55, :57 | review "per The PR gate" | none | UPDATE | repoint to the merge gate. :3, :22, :28 KEEP: a reviewer still reviews a PR where the host has one |
| `docs/getting-started.md` :171, :174; `specs/memory/ARCHITECTURE.md:148`; atoms `sdd-gate-v3`, `release-lifecycle`, `agent-comms` | state the PR-only rule | none | UPDATE at the reconcile (FR6) | the wt-rc's last commits; `llms-full.txt` is regenerated again after `docs/` |
| `.github/workflows/ci.yml:3-5`; `docs/distribution.md`; `README.md`; `llms.txt` | a developer-only "PR only" comment; the library's own pipeline; 0 hits | none | KEEP | nothing reads the comment; developer pipeline is out of the library |

### 1.1 Authorities

| question | authority | consults | deleted |
|---|---|---|---|
| is a push of a principal or integration ref admitted | `branch_policy.check_branch_policy` (role-None check only) | `push_gate.push_gate_decision`, `cli/commands/ci.py` | `_refuse_branch` PR arm and birth arm, `births`, push_gate.py :194-205, `remote_branch` |
| how a role branch is first published | `service._publish`: local head, pushed by name | the gate, as an ordinary ref | the birth refspecs (:646) |
| how integration and principal advance | SKILL.md §2a rows | root map :55, CONTEXT-MAP :64, RC-FLOW :9/:40, scaffold releases :44, `.dadaia/AGENTS.md` (from `dadaia-AGENTS.md:25`), getting-started | `dadaia-AGENTS.md:25`'s "PR-only … initial ref" |
| what gates that merge | SKILL.md §3b | `dd-code-review:61`, `dd-code-reviewer:57`, root map :55 | "that quote is the verdict's only record" |
| what "B lacks a change A holds" means | SKILL.md step 2 | step 4 | the `origin/` literals of steps 2 and 4 |
| which branches the history-rewrite rule covers | SKILL.md line 32 | `tests/core/test_gitflow.py` | "or a branch that advances only by PR" |

## DAG

The two jobs share no file. The wave column is the SPEC's ranking (law first, features after); it orders review attention and does not serialize dispatch. No edge: the law states what the gate does, and no test reads one against the other, so the main thread dispatches both together. The `W:` of each row is the exact union of its job file's tasks.

| job | waits on | wave | `W:` |
|---|---|---:|---|
| Job 1 | - | 1 | `tests/core/test_gitflow.py` `dadaia_workspace/public/skills/dd-gitflow-default/SKILL.md` `dadaia_workspace/public/scaffold/releases/AGENTS.md` `specs/releases/AGENTS.md` `dadaia_workspace/public/templates/shipped-hashes.json` `dadaia_workspace/core/specs_version.py` `dadaia_workspace/public/data/AGENTS.md` `dadaia_workspace/public/data/CONTEXT-MAP.md` `dadaia_workspace/public/data/dadaia-AGENTS.md` `dadaia_workspace/public/data/worktrees-AGENTS.md` `dadaia_workspace/public/skills/dd-release-implementation/RC-FLOW.md` `dadaia_workspace/public/skills/dd-release-implementation/SKILL.md` `dadaia_workspace/public/skills/dd-release-implementation/scripts/release.py` `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_tree.py` `dadaia_workspace/public/skills/dd-code-review/SKILL.md` `dadaia_workspace/public/agents/dd-code-reviewer.md` `llms-full.txt` |
| Job 2 | - | 3 | `tests/features/chokepoints/test_branch_policy.py` `tests/features/chokepoints/test_push_gate.py` `tests/cli/commands/test_ci.py` `tests/e2e/test_push_gate_check.py` `tests/fixtures/fix_world.py` `tests/features/spec_context/test_service__context_baseline.py` `dadaia_workspace/features/spec_context/service.py` `dadaia_workspace/features/chokepoints/branch_policy.py` `dadaia_workspace/features/chokepoints/push_gate.py` `dadaia_workspace/infrastructure/git_objects.py` |

Edges outside the DAG, none of them a job:

- **ADR 0283 to Job 2.** The operator accepts 0283 in this `wt-rc`'s define with SPEC and PLAN (`docs(adr): accept …`, which sets `amends` to 0036); no Job 2 task starts before it.
- **The reconcile.** FR6 is the `wt-rc`'s last commits (`docs/getting-started.md`, `ARCHITECTURE.md:148`, the three atoms, `llms-full.txt` regenerated, `_RELEASE.json`).

Task counts: Job 1 has 4 (1 `sr`, 3 `jr`); Job 2 has 4 (3 `sr`, 1 `jr`): 8 tasks. Job 1 order: T1 RED, then T2 to T4 (independent files, serial in one tree). Job 2 order is forced: T1 and T2 RED, T3 baseline, then T4 deletion; T4 before T3 breaks every baseline birth (pre-mortem 1).

AC map. AC1.1, AC1.2: J2.T1 (rows), J2.T4. AC1.3: J2.T1, J2.T4. AC2.1: J2.T4. AC2.2: J2.T2, J2.T3. AC2.3: read at review. AC3.1: J1.T2. AC4.1, AC4.4: J1.T1, J1.T2. AC4.2, AC4.3: J1.T2. AC5.1: J1.T3, J1.T4. AC5.2: J1.T4. AC6.1: the reconcile.

## 2. Dispatch

- **Agent cap: 2.** Each job is serial inside; the two jobs run together. One `dd-code-reviewer` review per job merge.
- **Job gate.** Each task's Definition of done is `python scripts/ci.py job` plus the test directories its change reaches, named in its job file (Job 2 includes `tests/e2e/test_push_gate_check.py`). Never the full CI line; no preflight; no new gate.
- **Commit shapes.** Shape 6 per task: a RED task is `test(J<n>.T<k>)`, a REBUILD `refactor(J<n>.T<k>): REBUILD <unit> — …`. A flipped or deleted assert is a `test(…)` commit whose body names the operator's order: "Remover o PR-only (Recomendado)" (R1) with the grill summary "Confirmar (Recomendado)" (R2), and lists those asserts with `path:line`. The scaffold mirror, digest and pin ride J1.T3 (a derived file is a `W:` entry).
- **Size.** Job 2 nets negative (SPEC goal 4: `branch_policy.py`, `push_gate.py`, `git_objects.py` and `service.py` together below 0; the estimate is about −35 before `_publish`'s lines); Job 1 rewords law in place.

## 3. Acts that are not tasks

- **ADR 0283 acceptance** and the SPEC and PLAN approval: the operator's, in this `wt-rc` (shapes 2 and 8), then `release.py phase IMPLEMENTATION`.
- **Reprojection.** After a Job 1 merge the main thread runs `public install` and `public doctor` (`[ok] public-privacy`), then `doctor`: `.agents/skills/**`, `.dadaia/AGENTS.md` and the persona copies are never hand-edited.
- **The two other r10 defects** (`root-map-protected-class-names-only-the-law-files`, `orchestration-restates-the-hotfix-exemption`): their own hotfix lane. The scorecard (SPEC goal 1) runs before the promote and never in the rc close path.
- **Adjacent ADR 0214 sites** (SPEC non-goals): the main thread inspects `published()`, baseline's `fetch`/`push` to `origin` and `dead()`'s refusal and registers any that breaks ADR 0214.
- **Other-context law.** `repos/dd-chain-explorer/specs/constitution.md:121` ("main advances only by PR") is that user's choice: flagged only.
- **Closure memory pass (FR6)**, per `MEMORY-UPDATE.md`.

## 4. Consumers of every changed name or grammar

| change | consumers | answer |
|---|---|---|
| "is never pushed directly — it advances only via a PR" (refusal text) | `test_branch_policy.py:132-136`; 0 other hits in `tests/` and `dadaia_workspace/` | J2.T1 flips the five rows |
| fix "open a PR/MR … on your git host" | `branch_policy.py:139`, `test_branch_policy.py:122-123`, `fix_world.py:1268` | 3 files; J2.T1 and J2.T4 |
| fix `git push origin refs/remotes/origin/<other>:<ref>` (role birth) | `branch_policy.py:117`, `fix_world.py:422, :1263`, `test_push_gate_check.py:5` | J2.T1 and J2.T4 |
| `check_branch_policy(…, births)` | caller `push_gate.py:203`; tests via `_birth`; `test_cli_line__refusal_fix_lines_clear_their_refusal.py:178,192` call it without `births` | the two test calls pass unchanged |
| `ObjectSource.remote_branch` | `push_gate.py:53`, fake `test_push_gate.py:207`, impl `git_objects.py:690` | 3 sites, deleted together (J2.T1 fake, J2.T4 rest) |
| baseline birth refspecs | `test_service__context_baseline.py` :156, :159, :162, :187 | stay green unchanged (J2.T3) |
| "advances only by PR" (SKILL.md:32) | `test_gitflow.py:154, :171`; the §2a rows `:147-149`, `:170` | J1.T1 repins; the row labels stay |
| `SHIP_PR` | `test_release.py:586` | not reworded: untouched |
| `.dadaia/AGENTS.md`, `.agents/skills/**`, personas | projections | reprojected after the merge (section 3) |
| the same grammar in other repos of the context | `repos/dd-chain-explorer` | 1 hit (`constitution.md:121`), its own law, flagged |

## 5. Tests of record

Each changed assert is a `test(<id>)` commit naming R1 and R2 and listing the `path:line`.

| assert | action | task |
|---|---|---|
| `test_branch_policy.py` :132-136 (PR-only rows), :137-141 (M2 rows) | move to the admitted table | J2.T1 |
| `test_branch_policy.py` :58-64, :82-86, :108-112, :122-123, :126-127 | delete | J2.T1 |
| `test_branch_policy.py` :136 (tag onto principal) | `named` string becomes the outside-the-gitflow text | J2.T1 |
| `test_ci.py` :267-276 | flips to admitted; :255, :263 stay | J2.T1 |
| `fix_world.py` :422-431, :1262-1269 (Case and PR Skip); `test_push_gate.py:207` | delete | J2.T1 |
| `test_push_gate_check.py` :5, :78 | reworded; two pass-matrix rows added | J2.T1 |
| `test_gitflow.py` :154, :171, :170 | repinned to the new line | J1.T1 |
| `test_service__context_baseline.py` | one test added, no assert moved | J2.T2 |

No assert is skipped or loosened beyond these. A row outside this table that turns red is a question for the main thread, never flipped silently.

## 6. Pre-mortem answers, and risks

1. **Baseline breaks (hit 1).** `_publish` enters Job 2 (`service.py`, T3). T2 is its RED (the local role heads exist at the tips); T3 holds the four baseline rows green before the deletion lands; T4 is last. If T3 meets a row that cannot pass without moving an existing local ref, it stops and returns the finding. It never moves a local branch silently.
2. **H4 and M2 rows (hit 2).** `_birth_from_any_source` and its row are deleted (a refspec mismatch), the M2 rows move to the admitted table, row :136 changes text (J2.T1).
3. **Readers of `unpublished` (the SPEC's open fact).** After :194-205 goes: the `ObjectSource.unpublished` Protocol row has 0 gate readers and leaves in J2.T4; `git_objects.unpublished` keeps `git_subprocess.py:172`; `GitSubprocessObjectReader.unpublished` has 0 production readers and keeps 3 tests. Deleting those tests needs the operator's order, which R1 does not cover, so the class method stays and goes to the main thread's intake as a proposal.
4. **Line 32 and `test_gitflow.py:170` (hit 3).** J1.T1 repins on the order; the row labels stay.
5. **`test_release.py:586` (hit 4).** `SHIP_PR` already reads "when the host has one"; it is not reworded and the test is not touched.
6. **Reference-transaction gate, `ci install-hook`, platform.** No hit (pre-mortem).
7. **The lost guard.** Nothing client-side stops an agent from pushing or force-pushing the principal. AC4.4 keeps the rule as law. The reviewer states this as the diff's one new surface; the diff otherwise shrinks.
8. **AC5.2 timing.** `rg` over `dadaia_workspace/public docs README.md llms.txt llms-full.txt` has 0 hits in `docs/` and `README.md` today; after J1.T4 (which regenerates `llms-full.txt`) it prints nothing. The reconcile regenerates again after `docs/`.
9. **Stamp 13 re-pin.** `CANON_AT[13]` is re-pinned in J1.T3 because the stamp is unpublished (v0.4.7 carries 7); `test_a_canon_change_bumps_the_stamp` computes the value.
10. **`.github/workflows/ci.yml:3-5`.** A stale developer comment; KEEP, nothing reads it.
