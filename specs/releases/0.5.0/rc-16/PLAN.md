# PLAN — Release: 0.5.0, candidate 16

**Status:** Draft
**Release ID:** 0.5.0
**Owner:** dd-sw-engineer-sr

The SPEC says what (FR1 to FR10, `AC<n>.<k>` belongs to Job `<n>`); this PLAN records the as-is review, the DAG with exact write ownership and the notes the main thread needs to dispatch. Paths are repository-relative to `repos/dadaia-workspace/`; `S/` = `dadaia_workspace/public/skills/dd-gitflow-default/scripts/`, `K/` = `…/dd-bug-resolution/scripts/`. Tasks: `tasks/job1.md` to `tasks/job10.md`.

**Evidence.** Long evidence is not copied here: the as-is review is `.dadaia/reports/dadaia-workspace/rc16-definition/ASIS.md` (HEAD `13e3fc074`; §0 findings H1-H9, §1.2 defect repros, §2 consumer sweeps, §3 design seams, §6 net lines) and the bug window is `.dadaia/reports/dadaia-workspace/rc16-definition/BUG-WINDOW.md` (R1-R5). Commands and results are in ASIS §7.

**Rulings carried (release grill 2026-10-14, verbatim choices).** 'Integração real'; 'Lanes laterais para ambos'; 'Verbo CLI + git hook'; 'Apagar o tipo plain'; 'Reusar o gate de job'; 'specs init corta o branch' (Job 9); 'Agente arruma, sem perda' (rollout, Job 10); 'Só reporta' (R2, Job 1); 'Converter em teste de recusa' (Job 2: no test is deleted). Decided by law and labelled "agent default, unruled" where a seam was open: ASIS §3 (Q1 the WT stays in `dd-gitflow-default/scripts/` and `dadaia worktree` is a thin runner; Q3 audits keep the direct-write law; Q5 cutover below).

## 1. As-is review

Order per row: DELETE, REBUILD, UPDATE, KEEP, ADD. Bug counts are ledger records whose `component` or `title` names the unit (ASIS `bug_slices.txt`); a count includes records that only mention the file, the judged chains are in §1.3.

| unit | today | bugs | verdict | why |
|---|---|---|---|---|
| `S/_worktree_names.py` | one `NAME_RE` with six alternations, `locate` at fixed depth 2, `base`, `plain`, `non_code`, `pushable`, `name_of` | 3 + defect A | REBUILD (Job 5; the plain half DELETEd in Job 2) | the demand changes grammar, base, kind and push rule; as a flag it would keep both grammars. New: one leaf regex, `kind_of`, `base_of`, `locate` by the first `wt-` segment |
| `S/_worktree_git.py` | work-branch rule, `record_base`/`recorded_base`, `ours`, rows (`_ours`, `_absent`, `_row`), `diff_sha256`, `cli` | 6 | REBUILD `record_base`, `recorded_base`, `_ours`, `_absent` (Jobs 2, 5); KEEP the work-branch rule, `diff_sha256`, `cli` | ≥ 2 bugs and the base decider changes; the work-branch rule was rebuilt in rc-15 (`fb127322a`) and stays the one rule for path-less callers |
| `S/_worktree_new.py` | `_shape`, `_plain_base`, `_refuse_unready`, `_refuse_task`, `_refuse_unopened_bug`, `new` | 3 | DELETE `_plain_base` (Job 2); REBUILD `_shape`, `new` (Job 5); KEEP `_refuse_symlink`, `_refuse_unopened_bug`, `_refuse_unready` (reads `_RELEASE.json` from the rc's `wt-rc`) | two admission bugs, the second a fix-of-fix on `_refuse_unready`; the kind decides admission from the leaf |
| `S/_worktree_end.py` | merge/clean/preflight/digest; gate functions; `_kind_checks` if/elif by kind; `_into`, `_target`, `_open_tasks`, `_scaffold`, `_rmdir`, `_remove` | ≈ 13 (verdict chain of 4, verify chain of 3) | DELETE the plain row (Job 2); REBUILD `_kind_checks` as a kind table, `_into`, `_target`, `_open_tasks`→`_open_children` (Job 5); UPDATE `_check_ancestor` fix line and `_rmdir` (Job 8); KEEP unchanged `_check_approved`, `_series`, `_reviews`, `_moment`, `_gate`, `_declared*`, `_ledgers`, `_checks`, `_check_specs_only`, `_check_ancestor`, `_refuse_implementation_tests`, `_scaffold` (key only), `_kept`, `_refuse_dirty`, `merge`, `preflight`, `clean`, `digest` | no new gate function (ruling). The thirteen gate bugs sit in the KEEP functions and the demand touches none of their logic, so rewriting them restarts the loop |
| `S/worktree.py` | argparse verbs, one `Refusal`/`GitError` handler | 2 (fixed) | UPDATE (Job 5 error edge R4; Job 8 verb `sync`) | help text and fix lines name `dadaia worktree …` |
| `S/_worktree_sync.py`, `S/levels/{version,rc,job}.md` | — | — | ADD (Job 8) | no unit carries a rebase cascade or the per-level text the operator asked for in place of `.gitkeep`; `_check_ancestor`, `ours`, `base_of` are consulted, not copied |
| `K/_git.py` `scrubbed_env` | the one env of every skill-script git child and of `git_subprocess._run` | 3 | UPDATE (+2, Job 2) | the hook's marker `DADAIA_WT=1` lives in the one env builder |
| `K/_grammar.py` `TASK_ID_RE`; `_release_schema.py:258,286` | `.S<m>` accepted | 0 | DELETE the form (Job 3); `HISTORICAL_TASK_RE` keeps it for lineage | ADR 0231 retired stages (ASIS H6) |
| `_release_tree.py` (`_swept`, `_last_summary`, `_trace`, `_origin_row`), `release.py` `_refuse_unauthorized`, `_release_check.py` `_SUMMARY` | four readers decide which closure summary counts; `_trace` matches grammar words | 9 + 35 mention `release.py`; the chain is four `release-check-*` fixes in the window | REBUILD (Job 1, R1) | the fourth fix on one unit; one reader of the live candidate's closure summary, `_last_summary` and the partition leave |
| `features/specs/doctor_memory.py` placeholder detector | substring, then frontmatter test; a legacy-template table; `--fix` unlinks | 8; two CRITICAL data-loss fixes in a day | REBUILD (Job 1, R2): DELETE the unlink and the table | operator 'Só reporta': report with `Agent action: fill or delete the atom` |
| `infrastructure/python_env.py` `version_change`, `cli/commands/init.py` `_reconcile_upgrade` | the repair case is a `before is None` ternary in the printer | 5 | REBUILD (Job 1, R5) | the decider already returns `action`; add `repair` and delete the ternary |
| `_release_phase.py` `_worktree_rows`, `_refuse_open_worktrees` | refuses every open `wt/*` but its own and `f"{nxt}/define"` | 4 + `new-reconcile-opens-while-a-job-is-open` | REBUILD (Job 6) | the exception was added by a fix; new rule: any open tree except an rc's `wt-rc` |
| `dd-handoff-emitter/scripts/verdict.py` `_stats` (`:82`), `hash` call (`:131`) | counts `wt/{rc}/` prefixes; `hash` by path | 4 | UPDATE (±2, Job 6) | prefix `wt/<M.m.p>/rc-<N>/`; `hash` through the workspace CLI |
| `K/_specs.py:54` | `list` fix line names `worktree.py` | 1 | UPDATE (one string, Job 6) | public name moves to the CLI |
| `features/spec_context/gate_policy.py` (`_locate` `:71-79`, `:95`; `_WORKTREE_SCRIPT` `:53,164`) | reads `locate` through `load_owner`; protected globs by tail | 16 + defect A | UPDATE the fix-line string (Job 6); KEEP the `locate` consult | A is a `locate` defect closed in `_worktree_names` |
| `features/chokepoints/branch_policy.py` | `_pushable`, `check_branch_policy` | 3 | KEEP `_pushable`; UPDATE + `check_ref_policy` (+14, Job 4) | the unit owns "gitflow read by role"; the ref decision is the same question (`Gitflow.role_of`) |
| `cli/commands/ci.py` | `push-gate-check`, `install-hook`, `_gate_inputs` | 3 | UPDATE + `ref-gate-check` (+18, Job 4) | reuses `_gate_inputs` |
| `cli/commands/worktree.py`, `cli/main.py`, `public/scripts/reference-transaction.sh` | — | — | ADD (+22 py, +2, +40 sh; Job 4) | the operator's 'Verbo CLI + git hook'; the runner executes the one implementation (seam 1); the hook is one `INSTALLED_GIT_HOOKS` row |
| `core/workspace_layout.py` `INSTALLED_GIT_HOOKS`; `templates/shipped-hashes.json` | one hook row; append-only hash history | 12; 1 | UPDATE (+1 row, +1 entry; Job 4) | installer, `hook_state` and HOOKS-DRIFT-1 are table-driven |
| `features/spec_context/doctor.py` `_split_skill_fix` (`:164-176`) | the SKILL-MD-LENGTH fix opens a plain tree | 24 (TTL/reaper) | UPDATE (≈ −3, Job 2); KEEP the rest | consumer of the DELETE |
| `features/spec_context/service.py` (`install_git_hooks`, `dead`, `work_branch`) | installer, row and work-branch consumers | 23 | KEEP | row schema and installer unchanged |
| `features/spec_context/service.py` `baseline` (`:567-640`) | commits the onboarding paths off every branch, merges an existing local `<work>`, atomic anchor-first push | 26 mention it | UPDATE ≈ ±8 (Job 9) | already merges an existing `<work>`; it must accept one that holds the scaffold commit |
| `cli/commands/specs.py` `init` | scaffolds, upgrades or moves a foreign tree; never commits | 10 | UPDATE ≈ +10 (Job 9); open seam §2 | the demand adds one cut; no unit carries it (`core.gitflow.work_branch` is consulted, baseline's own cut is untouched) |
| `features/workspace/onboarding.py` `STEPS` row `first-pass` | the one next-step derivation that `doctor`, `init`, `context create` and SessionStart print; 3b fix names the audit skill | 12 | UPDATE the fix lambda ≈ +3 (Job 9); KEEP the state machine | the doctor ONBOARDING line is `Step.text`, so one edit serves every printer |
| `infrastructure/ledger_scripts.py` `WORKTREE_SCRIPT`, `worktree_rows`; `script_findings` + `cli/commands/doctor.py` `_absent_tree` | runs `worktree.py list --json`; absent-`--specs-dir` fallback | 9; 3 | UPDATE fix strings, KEEP row reading (Job 6); REBUILD the fallback (R3, Job 6) | third fix on one fallback |
| `hooks/ctx_inject.py` `_worktrees`; `core/gitflow.py` `work_branch`; `core/invocation.py` `scope`; `hooks/root_whitelist.py` + `workspace_layout.verdict` | rows renderer; path-less work-branch rule; depth-agnostic scope; nested folders are `canon` | 13; 4; 11; 8 | KEEP | row schema frozen; scope and verdict read below `worktrees/<r>` as `canon` |
| `scripts/guards/repo.py:534-540,1133`, `.github/workflows/ci.yml:4-5,17` | pins the `wt/**` push trigger | 3 | KEEP (`**` crosses `/`); UPDATE the comment (Job 6) | |
| `public/data/worktrees-AGENTS.md` (39) | seven tree kinds, plain, recorded base | — | REBUILD, shrinks (Job 7) | |
| skill, agent, law, template text naming the old grammar | | — | UPDATE (Job 7) | ASIS §2.2 |
| `tests/helpers/worktree_ws.py` + 45 test files naming `worktree.py`/`wt/`/`-rc<N>/` | old names in fixtures | — | UPDATE: ported with every assert intact; plain-only tests become refusal tests; new owner files `test__worktree_names.py`, `test__worktree_git.py`, `test__worktree_sync.py`, `test_reference_transaction.py`, `test_worktree.py` | root map §1: no test deleted, no assert loosened |

**Test rule.** No test is deleted (ruling 'Converter em teste de recusa'). The seven plain-only tests (`test__worktree_new.py:135,176,249`; `test__worktree_end.py:612,631` plus the `dadaia-base` assert `:640`; `test__worktree_end__preflight.py:134`; `test__worktree_end__verdict_binding.py:170`) are rewritten in J2.T3/T4 so that a plain name is refused with its fix line. Example-only uses of plain (`…__removal.py:77-91`, `…__preflight.py:186-220`, `…__scaffold.py:120`) are ported with assert counts unchanged (J2.T4/T5). The R2 test that asserted `--fix` removes an atom is rewritten to assert it stays (operator ruling), never deleted.

### 1.1 Authorities

| question | authority | consults | deleted |
|---|---|---|---|
| where a tree's merge goes (its base) | `S/_worktree_names.py` `base_of(name, work)`: the parent folder's integrating leaf, else `<work><v>` | `_worktree_end._target`, `_worktree_git._ours`, `digest`, `_kind_checks`, `_worktree_new.new`, `_worktree_sync` | `recorded_base`, `record_base`, the `branch.<b>.dadaia-base` config, `_plain_base`, `base()`'s `work`+`task` split, `_into`'s re-derivation |
| the tree kind | `kind_of(name)` from the leaf (`wt-rc`, `wt-main`, `wt-task-NNN`, `wt-hotfix-<bug>`, `wt-backlog-<slug>`) | `_kind_checks`, `pushable`, `_scaffold`, `new` admission, `list` | `NAME_RE` groups `plain/job/slug/bug/task`, `plain()`, `non_code()`, every `match["job"] == "define"` |
| the version `<v>` | the first path segment under `worktrees/<repo>/`, valid iff `<work><v>` exists locally | `new` (one `git branch --list`), `base_of` | `work_version` in `_shape`/`recorded_base`/`_plain_base` (it stays the rule for path-less callers) |
| the rc and job of a path | segments `rc-<N>`, `job-<n>` | `_open_children`, `verdict.py stats`, `_release_phase._refuse_open_worktrees`, `list` | the `<M.m.p>-rc<N>/<job>` split, `--`, `_open_tasks`' prefix test, `f"{nxt}/define"`, `verdict.py:82` |
| which refs may move | `reference-transaction.sh` + `ci ref-gate-check` → `branch_policy.check_ref_policy` (`Gitflow.role_of == "work"`) | `_git.scrubbed_env` (marker), the package git client, `install_git_hooks` | raw `git worktree add`/`merge` as an allowed path; the fix line `git rebase <work>` |
| which refs may be pushed | `pushable(ref)`: kind ∈ {rc, main, backlog}; tasks and hotfix are local | `branch_policy._pushable`, `ci.yml` `wt/**` | `pushable`'s `job not in (None, "define")` branch |
| path → (repo, name, tail) | `locate` | `gate_policy._locate`, `_worktree_end._target`, `_worktree_git` | the `parts[2]/parts[3]` fixed-depth guess, defect A |
| who writes the per-level `AGENTS.md` | `_worktree_new.new`, once per folder it creates, from `S/levels/<level>.md` | `_rmdir`, `_absent` | nothing (`.gitkeep` was never written) |
| who runs the sync cascade | `_worktree_sync` via `dadaia worktree sync` | `ours`, `base_of`, `_check_ancestor` | per-agent `git rebase <work>` |
| who gates the `wt-rc` merge | `_kind_checks` row `rc` = the job row + `_ledgers` | `_check_approved`, `_gate`, `_ledgers` | the `define` row and the unguarded `new reconcile` |
| the live candidate's closure summary | one reader in the release-check unit (Job 1) | `_swept`, `_refuse_unauthorized`, `_trace`, `_SUMMARY` | `_last_summary`, the partition in `release.py` |
| closure's open-tree rule | `_release_phase._refuse_open_worktrees` over `list --json` rows | `list` rows | the `nxt` computation and the `define` compare |
| the first-pass lane and the onboarding work branch | `specs init` cuts `feature/<v>` by `core.gitflow.work_branch`; `onboarding.py` `first-pass` names the lane | `baseline` publishes it, `dadaia worktree new` opens the lane | the plain tree of shape 9 |
| an unfilled placeholder atom | `doctor_memory` report with `Agent action: fill or delete the atom` | `doctor --fix` (deletes nothing) | the unlink, the legacy-template table |

### 1.2 Defects (A to G) and the Origin bugs

| id | at `13e3fc074` | closed by |
|---|---|---|
| A / `protected-globs-miss-a-plain-tree-path` | reproduces (ASIS §1.2): `locate` takes two segments whatever the tree shape | plain deleted in Job 2 (`block: security`, merges first); the `locate` RED at lane, rc, main and task depth is J5.T2 |
| B | fixed by `5c21ff6d8`/ADR 0250 | not re-registered; the atom is rewritten whole at Job 10 |
| C | partly: the third answer is plain's `_plain_base` | Job 2 deletes it; the other two answers are the rule's two verbs and stay |
| D / `new-reconcile-opens-while-a-job-is-open` | reproduces | reconcile becomes the last commits of `wt-rc`; closure refuses open job, task and lane trees (J6.T1 RED names the bug; J5.T6 refuses the old name) |
| E, F | fixed (`7b84a7ff5`, `ffa34bb48`) | not re-registered; their tests are kept (R4, J5.T4/T8) |
| G | 0097, 0107 already superseded by 0253; 0120, 0125, 0191 still contradict | the new ADR (supersedes 0191, 0125; amends 0120's push clause by text), proposed in the define tree for the operator to accept |

### 1.3 Bug-history reading

- **WT gate** (`_worktree_end.py`): the verdict chain is four records deep and the verify chain three; each fix landed inside `_check_approved`/`_gate` and the next bug was in the same function. The rc therefore changes none of them; the `rc` row calls the existing functions.
- **Work-branch name** (`_worktree_git.py`): three deciders collapsed to local branches in rc-15. The rc adds no fourth reader: `<v>` is the path's first segment validated by one `git branch --list`.
- **Admission** (`_worktree_new.py`): a fix-of-fix on `_refuse_unready`; its logic stays, only its source branch changes.
- **Closure exception** (`release-closure-refuses-the-next-candidates-define-tree`): a special case added by a fix, deleted in Job 6.
- **Hooks**: `pre-push-gate-never-runs-under-core-hookspath`, `push-refusal-advertises-no-verify`, `unrecoverable-fix-line-pushes-a-wt-branch-the-pre-push-refuses` (CRITICAL): the new hook reuses `git_hooks_dir`, `hook_state`, HOOKS-DRIFT-1, and J4.T5 pins that every fix line it prints is runnable on the new grammar. Windows: tests use `core/platform` helpers and `fix_line`/`cli_line`.
- **Bug window** (R1-R5): five REBUILD units; R1, R2, R5 are Job 1, R3 is folded into Job 6 (it edits `ledger_scripts.py`), R4 into Job 5 (the same modules).

### 1.4 Consumers of a DELETE or REBUILD grammar, public name or fix line

Sweep counts (ASIS §2): 18 production `.py` files, 29 law/skill/agent/template lines, 11 memory atoms, 7 derived docs, 45 test files. Each hit has an answering job:

| removed or changed | consumers | answer |
|---|---|---|
| the `NAME_RE` grammar, `locate`, `pushable` | `gate_policy.py:71-79,95`; `branch_policy.py:94-99`; `ledger_scripts.py`; the WT fix lines (`_worktree_end.py:53,84,143,232,384,431,436`, `_worktree_git.py:176`, `_worktree_new.py:60,81,88,106`) | Job 5 (inside the REBUILD); fix-line strings Job 6 |
| the public name `worktree.py` | `gate_policy.py:53,164`; `ledger_scripts.py:83`; `K/_specs.py:54`; `verdict.py:27,131`; `ci.yml:4-5`; 29 law lines | Job 6 (code), Job 7 (text) |
| `plain` | `doctor.py:164-176`; `dd-gitflow-default/SKILL.md:67`; map §7 3b; onboarding 3b | Jobs 2, 7, 9 |
| `.S<m>` task ids | `_release_schema.py:258,286`; `_bugs_check.py:18,78`; `memory_lint.py:74` (reads the historical form) | Job 3 |
| the `define`/`reconcile` trees | `_release_phase.py`, `RC-FLOW.md`, `specs/releases/AGENTS.md:27`, the memory atoms | Jobs 6, 7, 10 |
| the closure-summary readers | `_release_tree.py:133,145`; `release.py:194`; `_release_check.py:40,71` | Job 1 |
| the placeholder fix | `doctor_memory.py`; `test_doctor_memory.py`, `test_canon__scaffold_placeholder_repair.py` | Job 1 |
| `row` schema | `ctx_inject.py`, `doctor.py:260-270`, `service.py:681-707` | frozen; KEEP |
| the 17 projected-law mirrors | `.agents/skills/dd-gitflow-default/scripts/*` etc. | stale until `public install`, run by the main thread after Job 10 (ASIS H1) |

## DAG

| job | waits on | wave | `W:` |
|---|---|---:|---|
| Job 1 | — | 1 | `tests/public/skills/dd_release_implementation/scripts/test_release__lean_state.py`, `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_tree.py`, `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_check.py`, `dadaia_workspace/public/skills/dd-release-implementation/scripts/release.py`, `tests/features/specs/test_doctor_memory.py`, `tests/features/specs/test_canon__scaffold_placeholder_repair.py`, `dadaia_workspace/features/specs/doctor_memory.py`, `dadaia_workspace/features/specs/rules.py`, `dadaia_workspace/features/specs/doctor_structural.py`, `scripts/guards/slop.py`, `tests/cli/commands/test_init__init_reinit_upgrade.py`, `tests/infrastructure/test_python_env.py`, `dadaia_workspace/infrastructure/python_env.py`, `dadaia_workspace/cli/commands/init.py` |
| Job 2 | — | 1 | `tests/public/skills/dd_bug_resolution/scripts/test__git.py`, `dadaia_workspace/public/skills/dd-bug-resolution/scripts/_git.py`, `tests/public/skills/dd_gitflow_default/scripts/test__worktree_new.py`, `tests/public/skills/dd_gitflow_default/scripts/test__worktree_end.py`, `tests/public/skills/dd_gitflow_default/scripts/test__worktree_end__preflight.py`, `tests/public/skills/dd_gitflow_default/scripts/test__worktree_end__verdict_binding.py`, `tests/public/skills/dd_gitflow_default/scripts/test__worktree_end__removal.py`, `tests/public/skills/dd_gitflow_default/scripts/test__worktree_end__scaffold.py`, `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_names.py`, `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_git.py`, `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_new.py`, `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_end.py`, `tests/cli/commands/test_doctor__workspace_fix_lines_clear_their_finding.py`, `dadaia_workspace/features/spec_context/doctor.py` |
| Job 3 | — | 1 | `tests/public/skills/dd_bug_resolution/scripts/test_bugs.py`, `tests/public/skills/dd_release_implementation/scripts/test_release__release_script.py`, `dadaia_workspace/public/skills/dd-bug-resolution/scripts/_grammar.py`, `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_schema.py` |
| Job 4 | — | 1 | `tests/features/chokepoints/test_branch_policy.py`, `dadaia_workspace/features/chokepoints/branch_policy.py`, `tests/cli/commands/test_ci__cli_ci.py`, `dadaia_workspace/cli/commands/ci.py`, `tests/public/scripts/test_reference_transaction.py`, `tests/features/spec_context/test_doctor__hooks_drift.py`, `tests/features/spec_context/test_service__hook_refresh.py`, `dadaia_workspace/public/scripts/reference-transaction.sh`, `dadaia_workspace/core/workspace_layout.py`, `dadaia_workspace/public/templates/shipped-hashes.json`, `tests/cli/commands/test_worktree.py`, `dadaia_workspace/cli/commands/worktree.py`, `dadaia_workspace/cli/main.py` |
| Job 5 | Job 2 | 2 | `tests/helpers/worktree_ws.py`, `tests/fakes.py`, `tests/public/skills/dd_gitflow_default/scripts/test__worktree_names.py`, `tests/features/spec_context/test_gate_policy.py`, `tests/features/spec_context/test_gate_policy__law_states_what_the_code_does.py`, `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_names.py`, `tests/public/skills/dd_gitflow_default/scripts/test__worktree_git.py`, `tests/features/spec_context/test_doctor__worktree_rows.py`, `tests/features/spec_context/test_service__worktree_rows.py`, `tests/features/spec_context/test_service__context_dead_holds.py`, `tests/infrastructure/test_ledger_scripts.py`, `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_git.py`, `tests/public/skills/dd_gitflow_default/scripts/test__worktree_new.py`, `tests/public/skills/dd_gitflow_default/scripts/test_worktree__characterization.py`, `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_new.py`, `tests/public/skills/dd_gitflow_default/scripts/test__worktree_end.py`, `tests/public/skills/dd_gitflow_default/scripts/test__worktree_end__removal.py`, `tests/public/skills/dd_gitflow_default/scripts/test__worktree_end__preflight.py`, `tests/public/skills/dd_gitflow_default/scripts/test__worktree_end__scaffold.py`, `tests/public/skills/dd_gitflow_default/scripts/test__worktree_end__verdict_binding.py`, `tests/public/skills/dd_gitflow_default/scripts/test__worktree_end__verdict_ttl.py`, `tests/public/skills/dd_gitflow_default/scripts/test__worktree_end__worktree_ledger_conflict.py`, `tests/public/skills/dd_gitflow_default/scripts/test__worktree_end__define_gate.py`, `tests/core/test_gitflow.py`, `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_end.py`, `dadaia_workspace/public/skills/dd-gitflow-default/scripts/worktree.py`, `scripts/guards/slop.py`, `tests/hooks/test_sdd_gate.py`, `tests/hooks/test_pre_gate.py`, `tests/features/chokepoints/test_branch_policy.py`, `tests/hooks/test_root_whitelist.py`, `tests/hooks/test_sdd_post_gate.py`, `tests/infrastructure/runtime_transforms/test_hook_wrappers.py`, `tests/infrastructure/test_runtime_config__tool_caches_stay_in_the_tmp_zone.py`, `tests/features/spec_context/test_doctor__gate_allow_iff_doctor_keeps.py`, `tests/fixtures/hook_payloads/claude/scope.json`, `tests/fixtures/hook_payloads/codex/scope.json`, `tests/fixtures/hook_payloads/copilot/scope.json`, `tests/fixtures/hook_payloads/cursor/scope.json`, `tests/fixtures/hook_payloads/devin/scope.json`, `tests/fixtures/hook_payloads/kimi-code/scope.json` |
| Job 6 | Job 5 | 3 | `tests/public/skills/dd_bug_resolution/scripts/test__specs__workspace_root.py`, `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_phase.py`, `tests/public/skills/dd_handoff_emitter/scripts/test_verdict.py`, `tests/public/skills/dd_handoff_emitter/scripts/test_verdict__characterization.py`, `dadaia_workspace/public/skills/dd-handoff-emitter/scripts/verdict.py`, `tests/core/test_cli_line__fix_line_contract.py`, `tests/core/test_cli_line__refusal_fix_lines_clear_their_refusal.py`, `tests/features/spec_context/test_gate_policy.py`, `tests/infrastructure/test_ledger_scripts.py`, `dadaia_workspace/public/skills/dd-bug-resolution/scripts/_specs.py`, `dadaia_workspace/features/spec_context/gate_policy.py`, `dadaia_workspace/infrastructure/ledger_scripts.py`, `.github/workflows/ci.yml`, `tests/cli/commands/test_doctor__doctor_without_an_instance.py`, `tests/cli/commands/test_doctor__doctor_sections.py`, `dadaia_workspace/cli/commands/doctor.py` |
| Job 7 | Job 5 | 3 | `dadaia_workspace/public/data/worktrees-AGENTS.md`, `dadaia_workspace/public/skills/dd-gitflow-default/SKILL.md`, `dadaia_workspace/public/skills/dd-release-implementation/RC-FLOW.md`, `dadaia_workspace/public/skills/dd-release-implementation/SKILL.md`, `dadaia_workspace/public/skills/dd-manager-orchestration/SKILL.md`, `dadaia_workspace/public/skills/dd-release-definition/SKILL.md`, `dadaia_workspace/public/skills/dd-backlog-definition/SKILL.md`, `dadaia_workspace/public/skills/dd-bug-registration/SKILL.md`, `dadaia_workspace/public/skills/dd-code-review/SKILL.md`, `dadaia_workspace/public/skills/dd-handoff-emitter/SKILL.md`, `dadaia_workspace/public/skills/dd-audit-project/PILLAR-SPECS.md`, `dadaia_workspace/public/skills/dd-ai-eng-knowhow/CODEX.md`, `dadaia_workspace/public/agents/dd-code-reviewer.md`, `dadaia_workspace/public/agents/dd-sw-engineer-sr.md`, `dadaia_workspace/public/agents/dd-sw-engineer-jr.md`, `dadaia_workspace/public/data/AGENTS.md`, `dadaia_workspace/public/data/handoff-AGENTS.md`, `dadaia_workspace/public/data/dadaia-AGENTS.md`, `dadaia_workspace/public/data/CONTEXT-MAP.md`, `dadaia_workspace/public/scaffold/bugs/AGENTS.md`, `dadaia_workspace/public/scaffold/releases/AGENTS.md`, `dadaia_workspace/public/templates/repo-AGENTS.md`, `dadaia_workspace/public/schemas/handoff-v1.schema.json` |
| Job 8 | Job 5 | 3 | `tests/public/skills/dd_gitflow_default/scripts/test__worktree_sync.py`, `tests/public/skills/dd_gitflow_default/scripts/test__worktree_end.py`, `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_sync.py`, `dadaia_workspace/public/skills/dd-gitflow-default/scripts/worktree.py`, `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_end.py`, `tests/public/skills/dd_gitflow_default/scripts/test__worktree_new.py`, `tests/public/skills/dd_gitflow_default/scripts/test__worktree_end__removal.py`, `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_new.py`, `scripts/guards/slop.py`, `dadaia_workspace/public/skills/dd-gitflow-default/scripts/levels/version.md`, `dadaia_workspace/public/skills/dd-gitflow-default/scripts/levels/rc.md`, `dadaia_workspace/public/skills/dd-gitflow-default/scripts/levels/job.md` |
| Job 9 | Job 5 | 3 | `tests/cli/commands/test_specs.py`, `dadaia_workspace/cli/commands/specs.py`, `tests/features/spec_context/test_service__context_baseline.py`, `dadaia_workspace/features/spec_context/service.py`, `tests/features/workspace/test_onboarding__onboarding_steps.py`, `tests/features/workspace/test_onboarding.py`, `dadaia_workspace/features/workspace/onboarding.py` |
| Job 10 | Jobs 1–9 | 4 | `docs/index.md`, `docs/quickstart.md`, `docs/getting-started.md`, `docs/positioning.md`, `CONTEXT.md`, `README.md`, `tests/fixtures/quickstart.md`, `specs/backlog/BACKLOG.json`, `specs/backlog/_archive/backlog_histo.jsonl`, `specs/bugs/BUGS.jsonl`, `specs/bugs/_archive/bugs_histo.jsonl`, `specs/releases/0.5.0/_RELEASE.json` |

### Tasks per job

| job | tasks | sr | jr | pe |
|---|---:|---:|---:|---:|
| Job 1 | 6 | 4 | 2 | 0 |
| Job 2 | 8 | 4 | 4 | 0 |
| Job 3 | 2 | 1 | 1 | 0 |
| Job 4 | 8 | 4 | 4 | 0 |
| Job 5 | 10 | 4 | 6 | 0 |
| Job 6 | 8 | 4 | 4 | 0 |
| Job 7 | 4 | 1 | 3 | 0 |
| Job 8 | 4 | 2 | 2 | 0 |
| Job 9 | 6 | 5 | 1 | 0 |
| Job 10 | 2 | 1 | 0 | 1 |
| total | 58 | 30 | 27 | 1 |

## 2. Notes for the main thread

- **Waves** (the job map; agent default, unruled for wave 3 after the layout: law text for behaviour not yet built would drift). Wave 1: Jobs 1, 2, 3, 4, pairwise disjoint by file, tests included. Wave 2: Job 5. Wave 3: Jobs 6, 7, 8, 9, disjoint. Wave 4: Job 10 alone. A wave barrier holds: every job of a wave is merged before the next wave starts, so Job 6 also sees Job 4's `dadaia worktree` runner.
- **Merge order.** Job 2 first of all (`block: security`: the plain deletion closes `protected-globs-miss-a-plain-tree-path`); then Jobs 1, 3, 4 in any order; **main-thread step between waves 1 and 2, before Job 5 merges: the cleanup 'Agente arruma, sem perda'** in every repo holding an old-grammar tree (this define tree is gone by then; `worktrees/rand-engine/0.8.0-rc1/define`, `worktrees/<consumer>/0.12.0b-impl` with `wt/0.12.0{a,b,c}` and any empty dir): delete empty dirs and branches with no own commit, turn a tree with own work into tag `archive/wt/<name>` before removing it; then Job 5; then Jobs 6, 7, 8, 9; Job 10 last, then the candidate PR.
- **Critical path.** Job 2 → Job 5 → Job 8 → Job 10. Job 5 is the deepest chain (T1 → T2 → T3 → {T4 → T5, T6, T8} → T7, T9: five sequential tasks); Job 8 is three (T1 → T2 → T4); Jobs 6 and 9 are three and two.
- **Parallelism inside jobs.** Each job file states its chains; REDs with disjoint `W:` start together (Job 1: three pairs; Job 4: four chains; Job 5: after T3, four chains). The agent cap is the main thread's schedule (the operator's figure of 4 agents in parallel).
- **Cutover (Q5, ASIS H1).** The package loads the WT grammar from the checkout through `load_owner` while the instance runs `.agents/` copies, so Job 5's merge flips `locate`/`pushable` live. Merge it as late as wave 2 allows; from it, job branches are local-only (`verify:` runs at merge, no remote CI on them) while `feature/0.5.0` pushes continue; `public install` and `ci install-hook` of the new WT run after Job 10's merge (the hook, which refuses creation of a `wt/*` outside the marker, is installed in no repo before then); until then the doctor shows PROJECTION drift on the skills. Job 4's hook is not installed in any repo before that.
- **Rollout (after the Job 10 merge; the main thread's acts, no migration code).** `public install`, `ci install-hook --force` per repo, `doctor`, `certify`. The cleanup already ran before Job 5 (merge order): `_release_phase.py:89` exempts only `f"{nxt}/define"` and Job 6 deletes that exemption, so no old-grammar tree may survive Job 5's merge.
- **Cost statement (root map §1 gate-cost clause).** The `wt-rc` merge adds one run of the repo's `verify:` and one reviewer pass per rc, never above one run of the job gate. The hook adds no per-task or per-job requirement: the shell fast path is about 0 s and the python path 0.24 s (ASIS §3 seam 13), only on an unmarked update of a non-`wt/` head.
- **AC ids.** The ids per job: Job 1 AC1.1 (R1), AC1.2 (R2), AC1.3 (R5); Job 2 AC2.1 marker, AC2.2 plain, AC2.3 doctor fix; Job 3 AC3.1; Job 4 AC4.1 policy, AC4.2 ref-gate-check, AC4.3 hook refuses creation, AC4.4 runner, AC4.5 existing `wt/*` updates pass, AC4.6 `archive/wt/*` tags pass, AC4.7 harness-native worktrees pass; Job 5 AC5.0 fixtures, AC5.1 names, AC5.2 rows, AC5.3 new, AC5.4 merge by kind, AC5.5 readers, AC5.6 R4 error edge; Job 6 AC6.1 closure, AC6.2 verdict, AC6.3 fix lines, AC6.4 R3; Job 7 AC7.1 worktrees law, AC7.2 gitflow and release skills, AC7.3 other skills, AC7.4 agents, data, scaffold, template, schema; Job 8 AC8.1 `sync`, AC8.2 level `AGENTS.md`; Job 9 AC9.1 `specs init` cut, AC9.2 `baseline`, AC9.3 `first-pass` fix; Job 10 AC10.1 memory, AC10.2 derived docs, AC10.3 closure, AC10.4 rollout.
- **No memory path in any `W:`.** Job 10's memory pass is closure procedure (the check refuses `specs/memory` in a task `W:`).

### Open seams

1. **`specs init` commits the scaffold (Job 9).** The ruling cuts the branch; a lane cut from it sees only committed files, and `specs init` is pinned to commit nothing (`test_absent_specs_scaffolds_lists_paths_and_commits_nothing`). Agent default, unruled: `init` commits the scaffold on the branch it cuts (the commit is a sanctioned direct write like the first `specs init` already is). If J9.T1 cannot keep that assert unchanged, the task returns the seam to the main thread; a changed product contract needs the operator.
2. **Fail-open hook (Job 4).** Agent default, unruled: the hook fails open when the runner is unresolvable (the publication chokepoint stays pre-push).
3. **Hotfix lane's open-bug gate** reads `BUGS.jsonl` on `feature/<v>` (KEEP `_refuse_unopened_bug`); the registration that opens the bug is a `wt-backlog-<slug>` lane commit, as today.

## Pre-mortem

Consumer pre-mortem (read-only researcher) answered row by row (`dd-release-definition` §2).

| hit | answer | task |
|---|---|---|
| 1. Live flip: Job 5 changes `locate`/`kind_of`/`pushable`/closure while old-grammar trees exist (this define tree; `rand-engine/0.8.0-rc1/define`; `<consumer>/0.12.0b-impl`, `wt/0.12.0{a,b,c}`); `_release_phase.py:89` exempts only `{nxt}/define` | main-thread cleanup 'Agente arruma, sem perda' runs between waves 1 and 2, before Job 5 merges (merge order, §2); this define tree merges before implementation; `ci install-hook` stays after Job 10 | main thread; J6.T2 deletes the exemption |
| 2a. `scripts/guards/slop.py:46,51` allowance rows (`fix_placeholder_atom`, `_rmdir`) and self-plants `:688-694` go stale on a removal or rename | the row leaves with its function in R2; `_rmdir` row follows any rename in Job 5 and Job 8 | J1.T4, J5.T9, J8.T4 |
| 2b. `scripts/guards/workspace.py:12,16` quickstart fixture byte-equal to `docs/quickstart.md` (also read by `test_onboarding_journey.py:308-311`, `test_docs_derived_from_memory.py:35`) | the one editor of `docs/quickstart.md` is Job 10, and the fixture is in the same task; Job 9 edits neither | J10.T1 |
| 2c. `test_onboarding.py:84-92` pins the 3b fix words | moves with the fix line | J9.T5 |
| 2d. `test_branch_policy.py:110,162,195-205` pins `pushable` and the `archive/wt` tag carve-out | Job 4 keeps the carve-out green; Job 5 ports names with asserts intact | J4.T1, J5.T10 |
| 3. Hook: updates to existing `wt/*`; `archive/wt/*` tags; harness-native worktrees; `INSTALLED_GIT_HOOKS` (`workspace_layout.py:375`) and `install_git_hooks` (`service.py:160-183`) | creation-only rule (`old == 0 && new != 0`); one RED each: AC4.5, AC4.6, AC4.7; the table row and installer are table-driven (AC4.3 RED proves HOOKS-DRIFT-1 and install) | J4.T5, J4.T6 |
| 4. CI `wt/**` (`ci.yml:17`, `repo.py:534-540,1133`, `tests/scripts/test_ci.py:173`) | pushable: `wt-rc`, `wt-main`, `wt-backlog-*`; local only: `wt-task-*`, `wt-hotfix-*`. `**` crosses `/`, so the trigger and the `{"feature/**","wt/**"}` assert stay unchanged; only the `ci.yml:4-5` comment moves | J6.T6 |
| 5. R2 placeholder: `doctor_memory.py:72-141`, `rules.py:49-50`, `doctor_structural.py:238` text, `slop.py:46`, repair test | one task's `W:` | J1.T3, J1.T4 |
| `slop.py:138` `staged_task_id` reads the `.S` form | KEEP: it refuses a leftover id of the retired form in comments, which the retirement makes more right | J3 (decision, no edit) |
| `scaffold/releases/AGENTS.md:27` ships "authored in a `define` tree" | in the Job 7 text task | J7.T4 |
| `data/AGENTS.md:105` Level 3 text | Job 7 owns the file (map §7 3b wording); Job 9 owns the code and tests | J7.T4, J9.T5 |
| `onboarding.py:97-101` 3b fix line | Job 9 | J9.T6 |
| `_specs.py:23` docstring | Job 6 | J6.T6 |
| `repo.py:514-525` `adr_superseded_successor` | the new ADR names 0191 and 0125 in `supersedes` (product engineer); the acceptance commit flips them | no job |
| `.dadaia/agentic/manifest.json:389-409` lists the gitflow scripts | regenerated by projection after the merge, never hand-edited; Job 8's new files appear there then | main thread, `public install` |
| fixtures: `hook_payloads/*/scope.json` (6), `test_hook_wrappers.py:49,63`, `test_root_whitelist.py:110-113`, `test_doctor__gate_allow_iff_doctor_keeps.py:42`, `test_sdd_post_gate.py`, `test_runtime_config__tool_caches_stay_in_the_tmp_zone.py:66` | ported with asserts intact in the port task of the job that changes the grammar; a depth-agnostic file is left untouched and reported | J5.T10 |
| `test__git.py:31-126` | likely depth-agnostic; Job 2 owns it for the marker | J2.T1 |

## 6. Net lines (production code; tests and text apart)

Estimates from the units' present sizes; the reviewer measures the real diff.

| job | python | shell | note |
|---|---|---|---|
| 1 | ≈ −35 (R1 ≤ 0, R2 ≈ −30, R5 ≤ 0) | 0 | |
| 2 | ≈ −46 | 0 | tests: the plain-only ones converted, none removed |
| 3 | −2 | 0 | |
| 4 | +57 | +40 | tests ≈ +250 |
| 5 | −58 | 0 | tests ported, ≈ +200 for names and kind |
| 6 | −6 | 0 | R3 net ≤ 0 inside |
| 7 | text −10 | 0 | worktrees law 39 → ≤ 34 |
| 8 | +70 | 0 | +24 lines of level text |
| 9 | ≈ +21 | 0 | |
| 10 | 0 | 0 | |
| total | ≈ +1 (range −30 … +45) | +40 | |

Not ≤ 0. Stated reason (pre-review #5): the demand ADDS capabilities no unit can carry (hook ≈ 40 shell + ≈ 32 python, CLI runner 24, `sync` 50, level writer 20, onboarding cut 21) and DELETEs ≈ 160 python lines (plain, recorded base, kind if-chain, define exception, `.S`, the placeholder unlink, `_absent_tree`). Cheaper options tried: the hook deciding `feature/` by name (rejected: names are the constitution's); `sync` as a flag of `merge` (rejected: a second path inside the gate).
