# PLAN — Release: 0.5.0

**Status:** Draft
**Release ID:** 0.5.0
**Owner:** dd-software-engineer

Candidate 9. This file holds Job 1 (the demolition, SPEC AC1.1–AC1.10, Approved at 2ace25f28); Jobs 2–5 and Reconciliation join it at their definition. Paths are relative to `dadaia_workspace/` (`f/` = `features/`, `pub/` = `public/`, `S/` = `pub/skills/`, `GF/` = `S/dd-gitflow-default/scripts/`) unless they start with `tests/`, `scripts/`, `specs/`, `.github/` or `AGENTS.md`.

## 1. As-is review

Bug history read at 13269b5c9 (permanent architecture review; `bugs.py stats`, the ledger filtered on worktree, gate and verify surfaces, `git log -p` on `GF/`):
- `worktree.py merge` carries five records in nine days, each patched in place: `worktree-merge-first-approved-overrides-newer-rejected`, `worktree-merge-rewrites-the-branch-before-refusing` (rejected), `worktree-merge-union-duplicates-ledger-records-on-in-place-mutation`, `worktree-merge-linearizes-a-branch-already-containing-work` (fix reverted, T-050-191), `worktree-script-fix-lines-hand-build-the-cli-path`. Repetition on one unit: the merge holds four jobs (allowed sets, verdict, the `verify:` run, the fast-forward) for every kind alike.
- `memory-update-same-commit-docs-unsatisfiable-under-the-release-kind`: an atom and its derived section could not land in one merge because the `release` and `impl` allowed sets split them; 0189 (release kind carries derived docs) was the layered fix and was rejected. Cause: the kind split itself.
- `_worktree_end._verify` runs a tracked `verify:` line with `shell=True` (shell injection) and the full `scripts/ci.py` at every merge: gate 1, ~6 min on 67 landings (`T040135Z`).
- Fixed-depth path readers: `core/workspace_layout.protected_glob` reads `parts[3:]`, `GF/_worktree_end._target` reads `parts[1]`, `GF/_worktree_git.rows` globs `worktrees/<repo>/*`; each would misread a two-level tree name.
- `_release_plan._schedule_errors` (Parallel schedule) has no bug of its own; ADR 0194 moves the DAG into the PLAN and task state into per-job files, so the check leaves with the law that taught it.

| unit | today | bugs | verdict | why |
|---|---|---|---|---|
| `GF/_worktree_kinds.py` `KINDS`, `CAPS`, `allows`, `kind_holding`, `kind_for`, `_NAME_RE` | four kinds, their allowed sets, the `<M.m.p><l>-<kind>` grammar | 1 (`memory-update-same-commit-…`) | REBUILD | 0191: one tree per job; becomes `_worktree_names.py`, the one grammar and the one tail reader |
| `GF/_worktree_new.py` `new` | derives a letter and a kind, caps per kind, needs the trio for `impl` | 0 | REBUILD | the name is given (`<M.m.p>-rc<N>/<job>`, `backlog/<slug>`); a job needs its rc's Approved SPEC; no caps, no task trees (operator order, §2) |
| `GF/_worktree_end.py` `merge`, `_check_allowed`, `_verify` | one merge for every kind: allowed set, verdict, `verify:` (`shell=True`), ff | 5 | REBUILD | 0190: a job merge needs the verdict naming its CI-matrix run and runs the job gate; a `define`/`backlog` merge lands `specs/` only and runs the ledger checks only; argv, `shell=False` |
| `GF/_worktree_end.py` `_check_approved`, `_series` | verdict carry-over by patch and message series | 1 | KEEP | 0168's carry stands (AC1.2) |
| `GF/_worktree_git.py` `ours`, `rows` | reads `_NAME_RE`, globs one level | 0 | UPDATE | read the tree name through the grammar module |
| `scripts/ci.py` `JOBS`, `main` | one level: every named CI job | 0 | UPDATE | AC1.1: `task FILE…`, `stage`, `job` levels over the same steps |
| `AGENTS.md` `verify:` line | the merge's shell command | 0 | DELETE | AC1.2 |
| `core/workspace_layout.protected_glob` | computes the repo tail at a fixed depth | 0 | UPDATE | takes the tail; the gate gets it from the grammar module |
| `f/spec_context/gate_policy._kind_holding`, `_worktree_fix` | names a kind in the merge-only BLOCK's fix | 0 | DELETE | no kind left; the fix is `worktree.py list` |
| `S/dd-bug-resolution/scripts/_specs._kind`, `_bound_fix` kind glob | sends a ledger write to a `*-<kind>` tree | 0 | UPDATE | any open tree of the repo |
| `core/gitflow.Gitflow`, `f/chokepoints/branch_policy.check_branch_policy` | pushes only the work branch | 0 | UPDATE | AC1.2: a job branch `wt/<M.m.p>-rc<N>/<job>` is pushable, no other `wt/` |
| `.github/workflows/ci.yml` push triggers; `scripts/guards/repo.ci_triggers_gitflow` | work branch only | 0 | UPDATE | `wt/**` triggers the matrix; the guard pins it |
| `S/dd-release-implementation/scripts/_release_plan._schedule_errors`, `SCHEDULE` | judges the Parallel schedule | 0 | DELETE | AC1.8 |
| `S/dd-release-implementation/scripts/_release_plan` `job_errors` | — | — | ADD | AC1.10: a job file's stages; no unit parses `tasks/<job>.md` |
| `core/workspace_layout.SPECS_CANON` | admits `rc-<N>/{SPEC,PLAN,TASKS}.md` | 0 | UPDATE | AC1.9: `rc-<N>/tasks/<job>.md` |
| law: `pub/data/worktrees-AGENTS.md`, `S/dd-gitflow-default/SKILL.md` §3a, `RC-FLOW.md`, `MEMORY-UPDATE.md`, `S/dd-manager-orchestration/SKILL.md`, `S/dd-release-definition/SKILL.md` §4–§5, `S/dd-audit-project/PILLAR-SPECS.md` | the kinds ritual, the 9-step closure, the Parallel schedule | 1 | REBUILD | AC1.5, AC1.6, AC1.8: rewritten once to the new model |
| law hit lines: `pub/scaffold/{releases,bugs,ADRs}/AGENTS.md`, `S/dd-bug-resolution/SKILL.md`, `S/dd-release-implementation/SKILL.md`, `S/dd-bug-registration/SKILL.md` §3, `S/dd-code-review/SKILL.md` §3 | old-ritual lines | 0 | DELETE | AC1.8: the hit lines only; Job 5 rewrites these files |

### 1.1 Authorities

| question | authority | consults | deleted |
|---|---|---|---|
| is this a canonical worktree name, and what is a path's repo-relative tail | `GF/_worktree_names.locate` | `GF/_worktree_git`, `GF/_worktree_end`, `GF/_worktree_new`, `f/spec_context/gate_policy`, doctor and reaper through `worktree.py list` | `_worktree_kinds._NAME_RE`, `kind_for`, `protected_glob`'s fixed depth |
| what a gate level runs | `scripts/ci.py` `LEVELS` | `GF/_worktree_end` (argv) | the `verify:` line, `_verify` |
| which `wt/` branch is pushable | `core/gitflow.Gitflow.role_of` | `f/chokepoints/branch_policy` | — |
| is a job file well formed | `_release_plan.job_errors` | `_release_tree` (`release.py check`) | `_schedule_errors` |

## 2. Job 1 — the demolition

One worktree (`worktrees/dadaia-workspace/0.5.0-rc9-job1`, operator-authorized `git worktree add`); every task runs inside it. One review at its end, `scripts/ci.py` once on the result, one manual merge. No markers, no start or done commits; a task's commit subject starts with its id; a stage closes with a commit whose body carries `stage: J1.S<m> — unit+integration green`. REBUILD commits name the SPEC's Job 1 as the verdict for the demolished kinds and gate-1 code.

- Gates: task — `ruff` and `mypy` on the touched files plus its owner tests (`-n 2`); stage — unit + integration (`-n 2`), green before the next stage opens; job — `scripts/ci.py` once, at the end.
- AC1.3, operator order 2026-10-05, verbatim: "a release ja tem que começar fazendo ... vocÊ está proibio de rodar 1 worktree para cada tasks ou rodar CI para cada teste ... não podemos perder mais tempo". The `<job>--<task-id>` shape and the ≤ 5 task-worktree counter leave: a job's tasks share its tree, a stage is the barrier. The SPEC delta lands at Reconciliation (main thread).
- Deviation, recorded: J1.S2.T3 (`ci.py` levels) and the first cut of J1.S2.T1 were written before the stage order arrived; J1.S2.T3's tests landed with its code in 0fce6c788, not as an S1 xfail.

### Stage J1.S1 — RED (tests only)

- Contract: exit tests are the acceptance tests below, each a strict xfail; envelope `tests/**`; ACs AC1.2 (branch policy), AC1.9, AC1.10.

| id | AC | `W:` | owner tests |
|---|---|---|---|
| J1.S1.T1 | AC1.2 | `tests/unit/features/chokepoints/test_branch_policy.py` | same — a job branch pushes; a `define`, `backlog` or task-shaped `wt/` branch refuses |
| J1.S1.T2 | AC1.9 | `tests/unit/features/specs/test_canon.py` | same — a job file is canon; a stray `tasks/` file is not; a closed rc's `TASKS.md` still is |
| J1.S1.T3 | AC1.10 | `tests/contract/test_release_script.py` | same — one valid job file passes `check`; a stage-1 non-test `W:` refuses |

### Stage J1.S2 — code

- Contract: exit tests are J1.S1's, now passing, plus each task's owner tests; envelope `dadaia_workspace/**` but `public/**/*.md`, `scripts/**`, `.github/workflows/ci.yml`, `AGENTS.md`, `tests/**`; ACs AC1.1–AC1.5, AC1.8 (the Parallel schedule check), AC1.9, AC1.10.

| id | AC | `W:` | owner tests |
|---|---|---|---|
| J1.S2.T1 | AC1.2–AC1.5 | `GF/worktree.py`, `GF/_worktree_names.py` (was `_worktree_kinds.py`), `GF/_worktree_new.py`, `GF/_worktree_end.py`, `GF/_worktree_git.py`, `AGENTS.md`, `f/spec_context/doctor.py` | `tests/integration/test_worktree_new.py`, `tests/integration/test_worktree_lifecycle.py`, `tests/helpers/worktree_ws.py` |
| J1.S2.T2 | AC1.3 | `core/workspace_layout.py` `protected_glob`, `f/spec_context/gate_policy.py`, `S/dd-bug-resolution/scripts/_specs.py`, `S/dd-release-implementation/scripts/_release_phase.py` | `tests/unit/features/spec_context/test_gate_policy.py`, `tests/unit/hooks/test_pre_gate.py` (a protected glob blocks in a job tree), `tests/unit/skills/test_bug_resolution_bugs_script.py` |
| J1.S2.T3 | AC1.1 | `scripts/ci.py` | `tests/integration/test_ci_script.py` |
| J1.S2.T4 | AC1.2 | `core/gitflow.py`, `f/chokepoints/branch_policy.py`, `.github/workflows/ci.yml`, `scripts/guards/repo.py` | `tests/unit/features/chokepoints/test_branch_policy.py`, guard plant `job-trigger` |
| J1.S2.T5 | AC1.9 | `core/workspace_layout.py` `SPECS_CANON` | `tests/unit/features/specs/test_canon.py` |
| J1.S2.T6 | AC1.8, AC1.10 | `S/dd-release-implementation/scripts/_release_plan.py`, `_release_tree.py` | `tests/contract/test_release_script.py`, `tests/helpers/release_state.py` |

- J1.S2.T2 and J1.S2.T5 both touch `core/workspace_layout.py`, in disjoint functions; T5 runs after T2.

### Stage J1.S3 — law and log

- Contract: exit checks are AC1.8's two greps printing `0`, `public stage`/`install`/`doctor` clean, `release.py check` clean; envelope `dadaia_workspace/public/**/*.md`, `CONTEXT.md`, `specs/releases/0.5.0/_RELEASE.json`; ACs AC1.5, AC1.6, AC1.7, AC1.8.

| id | AC | `W:` | owner tests |
|---|---|---|---|
| J1.S3.T1 | AC1.5, AC1.6, AC1.8 | `pub/data/worktrees-AGENTS.md`, `pub/data/AGENTS.md`, `S/dd-gitflow-default/SKILL.md`, `S/dd-release-implementation/{SKILL,RC-FLOW,MEMORY-UPDATE}.md`, `S/dd-manager-orchestration/SKILL.md`, `CONTEXT.md` | none (law text) |
| J1.S3.T2 | AC1.8, AC1.10 | `S/dd-release-definition/SKILL.md`, `S/dd-audit-project/PILLAR-SPECS.md` | none (law text) |
| J1.S3.T3 | AC1.8 | the hit lines of `pub/scaffold/{releases,bugs,ADRs}/AGENTS.md`, `S/dd-bug-resolution/SKILL.md`, `S/dd-bug-registration/SKILL.md`, `S/dd-code-review/SKILL.md` | none (law text) |
| J1.S3.T4 | AC1.7 | `specs/releases/0.5.0/_RELEASE.json` | none (log data) |
