# PLAN — Release: 0.5.0, candidate 12

**Status:** Draft
**Release ID:** 0.5.0
**Owner:** dd-software-engineer

The SPEC (Approved at `eb4ce8c93`) says what; this PLAN records the as-is review, the job DAG with exact write ownership, and the critical-path estimate SPEC G1 requires. Paths are repository-relative. Tasks live in `tasks/job1.md`–`tasks/job7.md`.

**Ceiling verdict (G1): EXCEEDED.** With FR7 (CP3) moved to rc-13, as G1 orders first, the critical path is 9.5–18.9 h against the 8.7 h ceiling, over by 0.8–10.2 h. The estimates are not compressed to fit. The operator's choice is required before approval; the options are quantified in §Schedule and estimate.

## As-is review

Order per row: DELETE → REBUILD → UPDATE → KEEP → ADD. Bug counts are from `cp.json` (futures audit, base `68557c582`, re-measured on `b1e402511`) and `specs/bugs/BUGS.jsonl`.

| unit | today | bugs | verdict | why |
|---|---|---|---|---|
| `public/skills/dd-domain-modeling/`, `dd-codebase-design/`, `dd-architecture-survey/` | three design skills, named by 13 sources, `behavior-map.json`, `CONTEXT.md` and one test (42 grep hits) | — | DELETE | operator ruling (AC1.2); a rule that lived only there moves to its owning skill as a pointer |
| law, skill and persona sources (AC1.6 set) | 288 official cells below 9 at `b1e402511` (scores 7.2/7.3) | — | UPDATE | text edits that delete or correct before they add (PLAN-law9); no mechanism |
| AC1.5 code text (`push_gate.py:210-211`, `canon.py:23,167`, `ci.py:74`, `release.py:59-60`, `invocation.py:3`, `_worktree_end.py:229-230`) | strings cite a deleted rule, an absent function, CI that need not exist | — | UPDATE | strings and docstrings only |
| `_worktree_new.py:87-95` job gate | opens a job when the rc SPEC is Approved, in phase DEFINITION | 1 (`worktree-new-opens-a-job-outside-implementation`) | REBUILD | its contract contradicts `specs/AGENTS.md` §3; one phase check replaces the status check |
| child-process test environments (12 files, 13 constructions) | each spawning test builds its own env; five Windows units were closed by a CI-selection change (`JB.S9.T11`), not in the test | 6 (`context-show-live-branch-…`, `coverage-line-…`, `fix-line-run-tests-…`, `fix-line-tests-expect-posix-bin-paths-…`, `hook-wrapper-tests-…`, `worktree-script-run-fails-winerror-193-…`) | REBUILD | rc-11 carry (FR3), ≥ 2-fix chain through `J7.S2.T2`; one builder (AC8.4, F018) |
| `hooks/root_whitelist.py` `_root_violation` | early return when the written path exists | 1 (`root-gate-blocks-editing-an-existing-entry`, caused by `sa-gate-allows-root-entries-the-reaper-moves`) | REBUILD | rc-11 carry (FR3) |
| `_worktree_end.py` `_check_approved` | verdict bound by `reviewed_sha` and `diff_sha256`; `ci_run` arm deleted | 3 (`job-merge-accepts-any-ci-run-url`, `job-merge-requires-a-remote-ci-run`, `merge-gate-accepts-verdict-written-by-the-merger`) | REBUILD | three fixes on one unit (FR3) |
| `hooks/ctx_inject.py` `_worktrees`, `ledger_scripts.py` `worktree_rows` | orphan line produced by one module, rendered by another | 1 (`orphan-worktree-line-absent-from-the-bind-block-on-windows`) | REBUILD | rc-11 carry (FR3) |
| `core/workspace_layout.py` `render_registry_tables` + `source_form` | the law's CLI form rendered at stage, then inverted at every comparator | 1 bug, 2 fixes (`51df83007`; `10ebbc4d8` caused by it) | REBUILD | a two-way translation added by consecutive fixes (FR3) |
| `json_context_store.py`, `migrate/state_v2.py`, `reconcile/service.py` | three writers of `spec_contexts.json`, two suppressed import edges | 14 (CP4), 2 regressions | REBUILD | one writer (FR5) |
| skill scripts (`dd-*/scripts/*.py`, 5,440 lines) | 7 `Refusal` classes, 3 commit loops, 9 git wrappers, 6 root finders, 41 `sys.path` mutations, a four-skill import cycle (7 cycles) | 55 (CP1), 32 regressions | REBUILD | one kernel in the staged `_ledger.py`/`_specs.py` (FR6) |
| `scripts/guards/{run,repo,slop}.py` | 3 `sys.path` mutations, counted by G4 | — | UPDATE | import root by configuration |
| ledger readers (`BUGS.jsonl` 8 modules, `_release_tree.py`, three subject parsers) | each ledger parsed by many modules | 42 (CP3), 22 regressions | REBUILD — moved to rc-13 | G1: over the ceiling, CP3 moves first |
| public-seam contract tests | 42 seams without a contract-complete test (`seams-42.txt`) | — | ADD | no unit carries the net (`today` —); 30 of them are written here |

### Authorities

| question | authority | consults | deleted |
|---|---|---|---|
| may a release job open | `_worktree_new.py` phase check via `_release_schema` | `worktree.py new` | the SPEC-status check (`worktree-new-opens-a-job-outside-implementation`) |
| who writes `spec_contexts.json` | `infrastructure/json_context_store.py` | `migrate/state_v2.py`, `reconcile/service.py` | their direct writes and both `ignore_imports` edges |
| skill-script refusal, commit loop, git, root walk | `dd-bug-resolution/scripts/_ledger.py` + `_specs.py`, staged into each skill | every skill script | six `Refusal` copies, two commit-loop copies, eight git wrappers, five root finders |
| a task id read by gitflow | `_release_schema.py`, staged into `dd-gitflow-default` | `_worktree_*.py` | the cross-skill `sys.path` edge |
| a child-process test environment | `tests/fixtures/harness_env.py` | every spawning test | 11 ad-hoc constructions |
| the workspace CLI spelling in shipped law | one spelling, read alike by stage, shipped history and TREE-5 | `template_history.was_shipped`, `doctor_structural._tree5_check` | `workspace_layout.source_form` (`shipped-law-hardcodes-the-posix-venv-path`) |
| law ≥ 9 | two fresh independent `dd-code-reviewer` judges | main thread records | main-thread scoring |

## DAG

| job | waits on | wave | `W:` | why |
|---|---|---:|---|---|
| Job 1 | — | 1 | `dadaia_workspace/public/data/AGENTS.md`, `dadaia_workspace/public/data/dadaia-AGENTS.md`, `dadaia_workspace/public/data/states-AGENTS.md`, `dadaia_workspace/public/data/handoff-AGENTS.md`, `dadaia_workspace/public/data/tmp-AGENTS.md`, `dadaia_workspace/public/data/worktrees-AGENTS.md`, `dadaia_workspace/public/data/CONTEXT-MAP.md`, `dadaia_workspace/public/templates/repo-AGENTS.md`, `dadaia_workspace/public/templates/specs-AGENTS.md`, `dadaia_workspace/public/scaffold/ADRs/AGENTS.md`, `dadaia_workspace/public/scaffold/audits/AGENTS.md`, `dadaia_workspace/public/scaffold/backlog/AGENTS.md`, `dadaia_workspace/public/scaffold/bugs/AGENTS.md`, `dadaia_workspace/public/scaffold/memory/AGENTS.md`, `dadaia_workspace/public/scaffold/releases/AGENTS.md`, `dadaia_workspace/public/agents/dd-code-reviewer.md`, `dadaia_workspace/public/agents/dd-product-engineer.md`, `dadaia_workspace/public/agents/dd-software-engineer.md`, `AGENTS.md`, `dadaia_workspace/public/skills/dd-ai-eng-knowhow/SKILL.md`, `dadaia_workspace/public/skills/dd-ai-eng-knowhow/AUTHORING.md`, `dadaia_workspace/public/skills/dd-ai-eng-knowhow/CLAUDE-CODE.md`, `dadaia_workspace/public/skills/dd-ai-eng-knowhow/CODEX.md`, `dadaia_workspace/public/skills/dd-ai-eng-knowhow/CONTEXT-ENGINEERING.md`, `dadaia_workspace/public/skills/dd-handoff-emitter/SKILL.md`, `dadaia_workspace/public/skills/dd-cli-library/SKILL.md`, `dadaia_workspace/public/skills/dd-audit-project/SKILL.md`, `dadaia_workspace/public/skills/dd-audit-project/FINDINGS-FORMAT.md`, `dadaia_workspace/public/skills/dd-audit-project/PILLAR-BUGS.md`, `dadaia_workspace/public/skills/dd-audit-project/PILLAR-MEMORY.md`, `dadaia_workspace/public/skills/dd-audit-project/PILLAR-SPECS.md`, `dadaia_workspace/public/skills/dd-backlog-definition/SKILL.md`, `dadaia_workspace/public/skills/dd-bug-registration/SKILL.md`, `dadaia_workspace/public/skills/dd-bug-resolution/SKILL.md`, `dadaia_workspace/public/skills/dd-bug-resolution/LINEAGE.md`, `dadaia_workspace/public/skills/dd-bug-resolution/RED-LOOP.md`, `dadaia_workspace/public/skills/dd-grill-me/SKILL.md`, `dadaia_workspace/public/skills/dd-grill-me/EMISSION-FORMAT.md`, `dadaia_workspace/public/skills/dd-grill-me/PROBLEM-TAXONOMY.md`, `dadaia_workspace/public/skills/dd-code-review/SKILL.md`, `dadaia_workspace/public/skills/dd-code-review/SLOP.md`, `dadaia_workspace/public/skills/dd-gitflow-default/SKILL.md`, `dadaia_workspace/public/skills/dd-manager-orchestration/SKILL.md`, `dadaia_workspace/public/skills/dd-release-definition/SKILL.md`, `dadaia_workspace/public/skills/dd-release-implementation/SKILL.md`, `dadaia_workspace/public/skills/dd-release-implementation/MEMORY-UPDATE.md`, `dadaia_workspace/public/skills/dd-release-implementation/RC-FLOW.md`, `dadaia_workspace/public/skills/dd-release-implementation/RELEASE-EVENTS.md`, `dadaia_workspace/public/skills/dd-spec-navigator/SKILL.md`, `tests/infrastructure/test_public_assets.py`, `tests/public/skills/dd_release_implementation/scripts/test_release.py`, `dadaia_workspace/features/chokepoints/push_gate.py`, `dadaia_workspace/features/specs/canon.py`, `dadaia_workspace/cli/commands/ci.py`, `dadaia_workspace/public/skills/dd-release-implementation/scripts/release.py`, `dadaia_workspace/core/invocation.py`, `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_end.py`, `dadaia_workspace/public/skills/dd-domain-modeling/SKILL.md`, `dadaia_workspace/public/skills/dd-domain-modeling/CONTEXT-FORMAT.md`, `dadaia_workspace/public/skills/dd-codebase-design/SKILL.md`, `dadaia_workspace/public/skills/dd-codebase-design/DEEPENING.md`, `dadaia_workspace/public/skills/dd-codebase-design/DESIGN-IT-TWICE.md`, `dadaia_workspace/public/skills/dd-architecture-survey/SKILL.md`, `dadaia_workspace/public/skills/dd-architecture-survey/HTML-REPORT.md`, `dadaia_workspace/public/entities/behavior-map.json`, `CONTEXT.md`, `dadaia_workspace/public/templates/shipped-hashes.json`, `specs/AGENTS.md`, `specs/ADRs/AGENTS.md`, `specs/audits/AGENTS.md`, `specs/backlog/AGENTS.md`, `specs/bugs/AGENTS.md`, `specs/memory/AGENTS.md`, `specs/releases/AGENTS.md`, `.dadaia/reports/dadaia-workspace/agentic-scorecard/<UTC>/` | FR1 first: every later agent works under the law it lands |
| Job 2 | Job 1 | 2 | `tests/public/skills/dd_gitflow_default/scripts/test__worktree_new.py`, `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_new.py`, `dadaia_workspace/public/data/worktrees-AGENTS.md`, `specs/bugs/BUGS.jsonl` | FR2 alone (the one behaviour change); precedes Job 7 on `_worktree_new.py` |
| Job 3 | Job 1 | 2 | `tests/cli/commands/test_reconcile__characterization.py`, `tests/cli/commands/test_context__characterization.py`, `tests/public/skills/dd_spec_navigator/scripts/test_memory__characterization.py`, `tests/public/skills/dd_gitflow_default/scripts/test_worktree__characterization.py`, `tests/public/skills/dd_handoff_emitter/scripts/test_verdict__characterization.py`, `tests/public/skills/dd_bug_resolution/scripts/test_bugs__characterization.py`, `tests/public/skills/dd_release_implementation/scripts/test_release__characterization.py`, `tests/public/skills/dd_cli_library/scripts/test_registry__characterization.py`, `tests/hooks/test_root_whitelist__characterization.py`, `tests/hooks/test_ctx_inject__characterization.py`, `tests/cli/commands/test_ci__characterization.py`, `tests/cli/commands/test_public__characterization.py` | FR4 before every CP job |
| Job 4 | Job 1 | 2 | `tests/fixtures/harness_env.py`, `tests/fixtures/test_harness_env.py`, `tests/fixtures/stores.py`, `tests/scripts/test_ci.py`, `tests/cli/commands/test_doctor.py`, `tests/cli/commands/test_doctor__workspace_fix_lines_clear_their_finding.py`, `tests/infrastructure/runtime_transforms/test_hook_wrappers.py`, `tests/infrastructure/runtime_transforms/test_hook_wrappers__hook_interpreter.py`, `tests/cli/commands/test_context__context_show_live_branch.py`, `tests/cli/commands/test_init__init_with_repo.py`, `tests/infrastructure/test_ledger_scripts.py`, `tests/cli/commands/test_specs.py`, `tests/cli/commands/test_ci__push_gate_gitflow_resolution.py`, `tests/features/certification/test_service.py`, `tests/core/test_invocation__one_bind.py`, `tests/e2e/test_one_line_bootstrap.py`, `tests/helpers/worktree_ws.py`, `tests/public/skills/dd_bug_resolution/scripts/test__specs__workspace_root.py`, `tests/public/skills/dd_handoff_emitter/scripts/test_verdict.py`, `tests/public/skills/dd_release_implementation/scripts/test__release_schema.py`, `tests/public/skills/dd_release_implementation/scripts/test_release__lean_state.py` | FR3 test-side units with AC8.4; precedes Job 7 on two CP1 test files |
| Job 5 | Job 1 | 2 | `dadaia_workspace/hooks/root_whitelist.py`, `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_end.py`, `dadaia_workspace/hooks/ctx_inject.py`, `dadaia_workspace/infrastructure/ledger_scripts.py`, `tests/core/test_workspace_layout.py`, `dadaia_workspace/core/workspace_layout.py`, `dadaia_workspace/core/template_history.py`, `dadaia_workspace/features/specs/doctor_structural.py`, `dadaia_workspace/features/specs/canon.py`, `dadaia_workspace/infrastructure/runtime_transforms/codex_assets.py`, `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_git.py`, `dadaia_workspace/public/scripts/pre-push-ci-gate.sh`, `dadaia_workspace/public/templates/shipped-hashes.json`, `dadaia_workspace/public/agents/dd-code-reviewer.md`, `dadaia_workspace/public/agents/dd-product-engineer.md`, `dadaia_workspace/public/agents/dd-software-engineer.md`, `dadaia_workspace/public/data/AGENTS.md`, `dadaia_workspace/public/data/dadaia-AGENTS.md`, `dadaia_workspace/public/data/handoff-AGENTS.md`, `dadaia_workspace/public/data/states-AGENTS.md`, `dadaia_workspace/public/scaffold/ADRs/AGENTS.md`, `dadaia_workspace/public/scaffold/memory/AGENTS.md`, `dadaia_workspace/public/scaffold/releases/AGENTS.md`, `dadaia_workspace/public/skills/dd-ai-eng-knowhow/SKILL.md`, `dadaia_workspace/public/skills/dd-ai-eng-knowhow/AUTHORING.md`, `dadaia_workspace/public/skills/dd-ai-eng-knowhow/CODEX.md`, `dadaia_workspace/public/skills/dd-audit-project/SKILL.md`, `dadaia_workspace/public/skills/dd-audit-project/PILLAR-SPECS.md`, `dadaia_workspace/public/skills/dd-backlog-definition/SKILL.md`, `dadaia_workspace/public/skills/dd-bug-resolution/LINEAGE.md`, `dadaia_workspace/public/skills/dd-cli-library/SKILL.md`, `dadaia_workspace/public/skills/dd-grill-me/SKILL.md`, `dadaia_workspace/public/skills/dd-handoff-emitter/SKILL.md`, `dadaia_workspace/public/skills/dd-release-implementation/MEMORY-UPDATE.md`, `dadaia_workspace/public/skills/dd-release-implementation/RC-FLOW.md`, `dadaia_workspace/public/skills/dd-spec-navigator/SKILL.md`, `dadaia_workspace/public/templates/repo-AGENTS.md`, `dadaia_workspace/public/templates/specs-AGENTS.md`, `specs/AGENTS.md`, `specs/ADRs/AGENTS.md`, `specs/memory/AGENTS.md`, `specs/releases/AGENTS.md` | FR3 production units; after Job 1 for the law edit, before Job 7 on `_worktree_end.py` |
| Job 6 | Job 3 | 3 | `tests/features/migrate/test_state_v2.py`, `tests/features/reconcile/test_service.py`, `dadaia_workspace/infrastructure/json_context_store.py`, `dadaia_workspace/features/migrate/state_v2.py`, `dadaia_workspace/features/reconcile/service.py`, `setup.cfg`, `scripts/guards/slop.py`, `scripts/guards/repo.py`, `scripts/guards/run.py`, `scripts/ci.py` | FR5 (CP4) after the net |
| Job 7 | Job 2, Job 3, Job 4, Job 5 | 3 | `tests/infrastructure/test_public_assets__public_scripts_thin_wrapper.py`, `tests/helpers/skill_scripts.py`, `tests/public/skills/dd_bug_resolution/scripts/test__ledger.py`, `tests/public/skills/dd_bug_resolution/scripts/test__specs__workspace_root.py`, `tests/public/skills/dd_gitflow_default/scripts/test__worktree_new.py`, `tests/public/skills/dd_release_implementation/scripts/test__release_schema.py`, `dadaia_workspace/public/skills/dd-bug-resolution/scripts/_ledger.py`, `dadaia_workspace/public/skills/dd-bug-resolution/scripts/_specs.py`, `dadaia_workspace/infrastructure/public_assets.py`, `dadaia_workspace/public/skills/dd-bug-resolution/scripts/bugs.py`, `dadaia_workspace/public/skills/dd-bug-resolution/scripts/_bugs_check.py`, `dadaia_workspace/public/skills/dd-bug-resolution/scripts/_bugs_store.py`, `dadaia_workspace/public/skills/dd-bug-resolution/scripts/_bugs_transition.py`, `dadaia_workspace/public/skills/dd-bug-resolution/scripts/_bugs_write.py`, `dadaia_workspace/public/skills/dd-release-implementation/scripts/release.py`, `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_check.py`, `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_new.py`, `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_phase.py`, `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_store.py`, `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_tree.py`, `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_schema.py`, `dadaia_workspace/public/skills/dd-gitflow-default/scripts/worktree.py`, `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_git.py`, `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_names.py`, `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_new.py`, `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_end.py`, `dadaia_workspace/public/skills/dd-spec-navigator/scripts/memory.py`, `dadaia_workspace/public/skills/dd-spec-navigator/scripts/_memory_catalog.py`, `dadaia_workspace/public/skills/dd-spec-navigator/scripts/_memory_check.py`, `dadaia_workspace/public/skills/dd-spec-navigator/scripts/_memory_drift.py`, `dadaia_workspace/public/skills/dd-spec-navigator/scripts/_memory_schema.py`, `dadaia_workspace/public/skills/dd-backlog-definition/scripts/backlog.py`, `dadaia_workspace/public/skills/dd-backlog-definition/scripts/_backlog_check.py`, `dadaia_workspace/public/skills/dd-backlog-definition/scripts/_backlog_exit.py`, `dadaia_workspace/public/skills/dd-backlog-definition/scripts/_backlog_store.py`, `dadaia_workspace/public/skills/dd-backlog-definition/scripts/_backlog_write.py`, `dadaia_workspace/public/skills/dd-audit-project/scripts/audit.py`, `dadaia_workspace/public/skills/dd-audit-project/scripts/_audit_check.py`, `dadaia_workspace/public/skills/dd-audit-project/scripts/_audit_store.py`, `dadaia_workspace/public/skills/dd-audit-project/scripts/_audit_verbs.py`, `dadaia_workspace/public/skills/dd-cli-library/scripts/registry.py` | FR6 (CP1) after the net and every job sharing its files |
| Reconciliation | Job 6, Job 7 | 4 | `specs/memory/ARCHITECTURE.md`, `specs/memory/product/catalog.json`, `specs/audits/20260930-structural-convergence/FINDINGS.jsonl`, `specs/backlog/BACKLOG.json`, `specs/backlog/_archive/backlog_histo.jsonl`, `specs/releases/0.5.0/_RELEASE.json` | closure: memory pass, finding dispositions, backlog exit, G4/F004/F009 measurement |

Waves 2 and 3 have disjoint `W:` sets (checked by `release.py check`). FR7 has no job: it moves to rc-13 with `one-task-id-subject-grammar` and `origin-findings-renamed-to-the-spec-head`, which stay active in the backlog. Its 9 CP3 seams stay in Job 3's net, because Job 7 rewrites the commit loop those writers run.

## Write ownership

Each overlap the SPEC names is written once per edit, ordered by a DAG edge:

- `_worktree_new.py`: J2.T2 (FR2's phase check, wave 2), then J7.T5 (kernel imports, wave 3; Job 7 waits on Job 2).
- `_worktree_end.py`: J1.T11 (AC1.5 docstring, wave 1), then J5.T2 (REBUILD of `_check_approved`, wave 2), then J7.T5 (kernel imports, wave 3).
- `release.py`: J1.T11 (AC1.5 `--origin` help, wave 1), then J7.T4 (kernel imports, wave 3).
- The public law edit of `shipped-law-hardcodes-the-posix-venv-path`: J5.T5 alone (wave 2, after Job 1). No Job 1 task makes it.
- `scripts/guards/slop.py`: J6.T3 alone (ignore cap −2 and its `sys.path` line); Job 7 does not touch `scripts/`.
- `tests/public/skills/dd_release_implementation/scripts/test__release_schema.py` and `tests/public/skills/dd_bug_resolution/scripts/test__specs__workspace_root.py`: J4.T2 (AC8.4, wave 2), then J7.T1 (CP1 test actions, wave 3).
- `tests/public/skills/dd_gitflow_default/scripts/test__worktree_new.py`: J2.T1, then J7.T1.
- `canon.py`, `shipped-hashes.json`, the repo `specs/**/AGENTS.md` copies and the law files carrying the CLI form: Job 1 (wave 1), then J5.T5 (wave 2).
- Generated projections (`.agents/`, `.claude/`, `.codex/`, `.kimi-code/`) are never in `W:`; public sources are staged and installed after their job merges.
- Every behaviour task is two dispatches in separate task trees (RED, then source-only): J1.T10/T11–T12, J2.T1/T2, J5.T4/T5, J6.T1/T2, J7.T1/T2–T7. REBUILD and characterization tasks are single dispatches that keep their tests. CP tasks never edit a `*__characterization.py` file (AC4.3).
- Job-0 RED batch is empty (SPEC §5); the main thread re-runs the full suite once at rc-12 birth before Job 1 (`pytest -n 2`, 301.76 s wall on `b1e402511`).

## Schedule and estimate

### Measured baselines

| id | baseline | source |
|---|---|---|
| B1 | push CI on `feature/0.5.0`, green runs: 7.3–16.3 min; job-branch push CI (`wt/0.5.0-rc10/*`): 11.6–13.9 min | `gh run list --branch feature/0.5.0 --limit 10` (run 37931773740: 7.3 min at `b1e402511`; 37824093322: 16.3 min) and `gh run list --limit 40` |
| B2 | PR CI (full matrix): 13.1 min and 14.5 min; longest job Contract coverage on Windows, 12.2 min | runs 37931779794 (`b1e402511`) and 37824099824, `gh run view --json jobs` |
| B3 | full local suite `pytest -n 2`: 301.76 s wall, junit 301.580 s, 2,989 tests, 7 skipped; rc-11 tracked `ci.py job`: 58.553 s | `futures-audit/junit-b1e402511.xml`; rc-11 PLAN |
| B4 | rc-11: defined 2026-10-08T20:26:37Z → implemented 2026-10-09T04:47:54Z = 8.36 h; measured 14.63 h against the 8.7 h ceiling; forecast 5.4–8.7 h, so actual ÷ forecast high = 1.68 | `_RELEASE.json` log (milestones; main-thread note 2026-10-09T12:14:44Z); rc-11 PLAN |
| B5 | one rc-11 dispatch: 2.6–8.5 min (J1.T7 RED 21:32:24Z → GREEN 21:34:59Z; J1.T8 RED 23:48:34Z → GREEN 23:57:05Z; separator 00:12:11Z → 00:15:09Z); one review: 5.0–7.5 min (GREEN 23:57:05Z → REJECTED 00:04:35Z; 00:15:09Z → APPROVED 00:20:11Z) | handoff stamps under `.dadaia/handoff/dadaia-workspace/` |
| B6 | review rounds per rc-11 job: Job 1 3, Job 3 6 (02:33:04Z → 04:09:48Z), Job 4 2 | same handoffs |
| B7 | one law-9 judge pass: about 19 min (official scores 10:35 → worklists 10:53/10:54 local); one gap-fix pass: about 12 min | file times in `agentic-scorecard/20261009T1335Z/` |
| B8 | at most 5 open task trees per rc (`TASK_CAP`, `_worktree_names.py:13`); at most 2 test-running agents (rc-9 grill ruling); host: 8 CPUs, 15 GiB RAM, load 0.55 at reading | code; ruling; `nproc`, `free`, `uptime` |

### Unit costs

- Dispatch, per task, including the brief, focused tests and the task merge: S 0.10–0.30 h, M 0.30–0.60 h, L 0.50–1.20 h. B5's 2.6–8.5 min is the measured floor for small tasks.
- Job gate, after the last task: 0.60–1.33 h. That is push CI 0.12–0.27 (B1), review 0.08–0.17 (B5), one rework round (fix 0.10–0.30, push CI 0.12–0.27, re-review 0.08–0.17) and the merge with tracked `verify:` 0.10–0.15 (B3). One rework round is in the base because every rc-11 job needed at least one (B6). Rounds 3 and later are contingency.
- AC1.4 loop (J1.T13): two judges in parallel 0.3–0.5 (B7), one fix round in the reopened trees 0.2–0.4, then both re-score 0.3–0.5, for 0.8–1.4 h elapsed.

### Per-task durations (h, low–high)

| task | h | kind | task | h | kind |
|---|---|---|---|---|---|
| J1.T1 | 0.4–0.8 | law | J3.T6 | 0.4–0.8 | test |
| J1.T2 | 0.4–0.7 | law | J4.T1 | 0.5–1.0 | test |
| J1.T3 | 0.3–0.5 | law | J4.T2 | 0.5–1.0 | test |
| J1.T4 | 0.4–0.8 | law | J5.T1 | 0.2–0.4 | test |
| J1.T5 | 0.4–0.8 | law | J5.T2 | 0.3–0.6 | test |
| J1.T6 | 0.4–0.7 | law | J5.T3 | 0.2–0.4 | test |
| J1.T7 | 0.4–0.8 | law | J5.T4 | 0.15–0.3 | test |
| J1.T8 | 0.4–0.8 | law | J5.T5 | 0.5–1.0 | test |
| J1.T9 | 0.4–0.8 | law | J6.T1 | 0.2–0.4 | test |
| J1.T10 | 0.15–0.3 | test | J6.T2 | 0.4–0.7 | test |
| J1.T11 | 0.15–0.3 | test | J6.T3 | 0.3–0.5 | test |
| J1.T12 | 0.3–0.6 | test | J7.T1 | 0.5–1.0 | test |
| J1.T13 | 0.8–1.4 | judges | J7.T2 | 0.6–1.2 | test |
| J2.T1 | 0.15–0.3 | test | J7.T3 | 0.3–0.6 | test |
| J2.T2 | 0.2–0.4 | test | J7.T4 | 0.5–1.0 | test |
| J3.T1–J3.T3, J3.T6 | 0.4–0.8 each | test | J7.T5 | 0.4–0.8 | test |
| J3.T4 | 0.4–0.7 | test | J7.T6 | 0.3–0.6 | test |
| J3.T5 | 0.3–0.6 | test | J7.T7 | 0.4–0.8 | test |
| Reconciliation | 0.8–1.5 | closure | each job gate | 0.60–1.33 | gate |

### Critical path

The schedule is list-scheduled over the DAG edges under B8's two caps (5 open trees; 2 test-running agents; law tasks take a tree slot only). Job end times in hours from PLAN approval:

| point | low | high |
|---|---:|---:|
| Job 1 merged (J1.T1–T12 under the tree cap, J1.T13, gate) | 2.5 | 4.9 |
| Jobs 2–5 merged (wave 2: 10.3–19.9 test-agent hours through 2 slots; Job 5 last) | 5.9 | 11.7 |
| Job 6 merged | 6.3 | 12.6 |
| Job 7 merged (J7.T1 → J7.T2 → J7.T3–T7 in 2 slots → gate) | 8.7 | 17.4 |
| Reconciliation merged; candidate PR CI green (B2 inside the 0.8–1.5 h) | **9.5** | **18.9** |

- **Critical path: 9.5–18.9 h** (Job 1 → wave 2 under the test-agent cap → Job 7 → Reconciliation). Over the 8.7 h ceiling by 0.8–10.2 h. The measured span runs from PLAN approval (`release.py phase IMPLEMENTATION`) to the green candidate PR. Operator latency is excluded.
- **Aggregate: 19.8–39.8 agent-hours.** That is 18.8–37.6 for scheduled tasks and gates (each gate counted at its full elapsed time), plus 0.7–1.6 for the second judge and the reopened fix trees in J1.T13, 0.2–0.5 for the reconciliation reviewer, and 0.1 for the birth suite run.
- **FR7 kept, for disclosure:** 11.4–22.8 h critical, 21.3–42.5 agent-hours (one more job: test actions, the `BUGS.jsonl` query API, the other three ledger APIs with `_release_tree.py`, one subject parser with the rename, and its gate).
- **Uncertainty** is driven by four things. Review rounds ran 2–6 per rc-11 job (B6). The law-9 loop can need more than one fix round. The design of the J7 cycle break is one. The Windows matrix for FR3 is judged only on the candidate PR, because push runs are Linux-only.
- **Contingency, not included:** each review round past the first rework on a critical-path job costs +0.30–0.74 h; each further AC1.4 score/fix round costs +0.5–0.9 h; a Windows red at the candidate PR reopens Job 4 or Job 5 (+0.6–1.5 h). rc-11 ran 1.68× its forecast high (B4). That factor is disclosed but not applied. No contingency fits under the ceiling.

### Operator choice (G1 exceeded after moving FR7)

These options are computed with the same model and FR7 out. None is applied without the operator's ruling.

| option | critical h | agent-h |
|---|---:|---:|
| as planned | 9.5–18.9 | 19.8–39.8 |
| raise the test-agent cap to 3 | 8.3–16.6 | same |
| relax "FR1 first" (only Job 2 waits on Job 1) | 8.7–17.1 | same |
| move FR3 (Jobs 4, 5) to rc-13 | 8.2–16.4 | 15.3–30.3 |
| move FR6 (Job 7) to rc-13 | 7.1–14.1 | 15.2–30.3 |
| move FR3 and FR6 to rc-13 | 6.6–13.0 | 11.7–22.9 |

Only the low bound of a scope cut fits the ceiling. No option brings the high bound under 8.7 h.

## Open seams (need a ruling before approval)

- A1. **The ceiling's span.** It is not defined anywhere. rc-11's "measured 14.63 h" does not match the SPEC's own stamps (defined 2026-10-08T20:26:37Z → integration 2026-10-09T12:56:05Z = 16.49 h). This PLAN measures from approval to the green candidate PR.
- A2. **"FR1 first" is read strictly.** Every job waits on Job 1's merge, including the AC1.4 acceptance.
- A3. **The test-agent cap of 2 binds waves 2 and 3.** It comes from the rc-9 ruling. A 2026-10-06 reading said 3 fits, but that is unruled.
- A4. **G4's 44 `sys.path` mutations include 3 in `scripts/guards/`.** Those are not skill scripts, which is AC6.1's wording. The PLAN lands them in Job 6 (J6.T3) to keep `slop.py` with one owner, so the G4 table's "owner FR6" becomes FR5+FR6.
- A5. **AC4.1 contradicts itself on registry.py.** The PLAN reads "every other listed seam an rc-12 job touches" as code an rc-12 job changes. That adds `registry.py` ×6, `root_whitelist`, `ctx_inject`, `push-gate-check`, `public stage` and `public install` (30 seams in all). But AC4.1 also places the `registry.py` seams in rc-13/rc-14.
- A6. **Job 7 conflicts with G3.** Adding `dd-gitflow-default` to `_SKILL_SCRIPT_SHARED` changes the files `public stage`/`install` write, which conflicts with G3's "files written identical". A ruling is needed on whether the staged-file set is inside G3.
- A7. **The shipped-law REBUILD has no approved design.** J5.T5's `W:` assumes a law spelling change across the 25 AC1.6 law files that carry the CLI form. `public/data/fixed/slop-law.md` also carries it but is outside AC1.6, so it is excluded. A code-only design shrinks `W:` by amendment.
- A8. **J1.T13's `W:` is a placeholder.** It is the scorecard record `.dadaia/reports/…/<UTC>/`, which is outside the repo; `<UTC>` is fixed at dispatch.
- A9. **AC2.2's "a `reconcile` tree is cut before phase CLOSURE" is ambiguous.** J2.T1 asserts that a reconcile tree opens in IMPLEMENTATION. Whether it is refused in CLOSURE needs a ruling.
- A10. **AC8.4's grep counts only explicit constructions.** A spawn without `env=` inherits the parent environment and is not counted.

## Verification and closure

- Each RED task proves its failure for the intended reason. Each source task turns the same focused tests green without touching a test path. Each job gate runs the tracked `verify: python scripts/ci.py job` once and takes one bound reviewer verdict.
- G3/AC4.3: Job 3's net is green on Job 3's base and on the Job 6 and Job 7 heads. `git diff --name-only` over each CP job's range prints no `*__characterization.py` file.
- G4: the main thread re-runs `analyze.py` and the spec-contexts grep unchanged at closure (Jobs 6 and 7 name the commands). `summarize.py` `ledger_parsers_estimated` stays at 8 because FR7 moved.
- Reconciliation (dd-product-engineer): the F123 `ARCHITECTURE.md` line on import-linter contracts after FR5; the dispositions of F003, F004, F005, F009, F018, F048, F051, F123 and F135; the AC8.1 3-day re-bug rate (≤ 30%); the AC8.2 zero-caused rule with the fix-induced share against 37/189; the backlog exit of `skill-scripts-one-kernel`; and the closure entry in `_RELEASE.json`.
