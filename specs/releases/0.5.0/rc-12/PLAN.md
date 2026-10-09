# PLAN — Release: 0.5.0, candidate 12

**Status:** Approved
**Release ID:** 0.5.0
**Owner:** dd-software-engineer

The SPEC (Approved at `eb4ce8c93`) says what; this PLAN records the as-is review, the job DAG with exact write ownership, and the critical-path estimate SPEC G1 requires. Paths are repository-relative. Tasks live in `tasks/job1.md`–`tasks/job6.md`.

**Scope moves.** FR7 (CP3) moves to rc-13 as G1 orders first. FR6 (CP1) moves with it by **operator subset ruling 2026-10-09** ("Tirar o CP1 (Recomendado)"). G4's `sys.path` row (44 → 0) and import-cycle row (7 → 0) move with FR6, and the `BUGS.jsonl` reader row moves with FR7; the `ignore_imports` and `spec_contexts.json` writer rows stay with FR5. The Origin backlog ids `skill-scripts-one-kernel`, `one-task-id-subject-grammar` and `origin-findings-renamed-to-the-spec-head` stay active; none exits in rc-12.

**Ceiling verdict (G1): the high bound still exceeds it.** The critical path is 6.9–13.7 h against 8.7 h: the low bound is 1.8 h under the ceiling and the high bound is 5.0 h over. The estimates are not compressed to fit.

## As-is review

Order per row: DELETE → REBUILD → UPDATE → KEEP → ADD. Bug counts are from `cp.json` (futures audit, base `68557c582`, re-measured on `b1e402511`) and `specs/bugs/BUGS.jsonl`.

| unit | today | bugs | verdict | why |
|---|---|---|---|---|
| `public/skills/dd-domain-modeling/`, `dd-codebase-design/`, `dd-architecture-survey/` | three design skills, named by 13 sources, `behavior-map.json`, `CONTEXT.md` and one test (42 grep hits) | — | DELETE | operator ruling (AC1.2); a rule that lived only there moves to its owning skill as a pointer |
| law, skill and persona sources (AC1.6 set) | 288 official cells below 9 at `b1e402511` (scores 7.2/7.3) | — | UPDATE | text edits that delete or correct before they add (PLAN-law9); no mechanism |
| AC1.5 code text and post-score textual consistency | the six planned strings/docstrings plus stale memory-law citations, task-path comments and backlog-writer descriptions | — | UPDATE | strings, comments, docstrings, diagnostics and schema descriptions only; no schema constraint, control flow or behaviour changes |
| `_worktree_new.py:87-95` job gate | opens a job when the rc SPEC is Approved, in phase DEFINITION | 1 (`worktree-new-opens-a-job-outside-implementation`) | REBUILD | its contract contradicts `specs/AGENTS.md` §3; one phase check replaces the status check |
| child-process test environments (12 files, 13 constructions) | each spawning test builds its own env; five Windows units were closed by a CI-selection change (`JB.S9.T11`), not in the test | 6 (`context-show-live-branch-…`, `coverage-line-…`, `fix-line-run-tests-…`, `fix-line-tests-expect-posix-bin-paths-…`, `hook-wrapper-tests-…`, `worktree-script-run-fails-winerror-193-…`) | REBUILD | rc-11 carry (FR3), ≥ 2-fix chain through `J7.S2.T2`; one builder (AC8.4, F018) |
| `hooks/root_whitelist.py` `_root_violation` | early return when the written path exists | 1 (`root-gate-blocks-editing-an-existing-entry`, caused by `sa-gate-allows-root-entries-the-reaper-moves`) | REBUILD | rc-11 carry (FR3) |
| `_worktree_end.py` `_check_approved` | verdict bound by `reviewed_sha` and `diff_sha256`; `ci_run` arm deleted | 3 (`job-merge-accepts-any-ci-run-url`, `job-merge-requires-a-remote-ci-run`, `merge-gate-accepts-verdict-written-by-the-merger`) | REBUILD | three fixes on one unit (FR3) |
| `hooks/ctx_inject.py` `_worktrees`, `ledger_scripts.py` `worktree_rows` | orphan line produced by one module, rendered by another | 1 (`orphan-worktree-line-absent-from-the-bind-block-on-windows`) | REBUILD | rc-11 carry (FR3) |
| `core/workspace_layout.py` `render_registry_tables` + `source_form` | the law's CLI form rendered at stage, then inverted at every comparator | 1 bug, 2 fixes (`51df83007`; `10ebbc4d8` caused by it) | REBUILD | a two-way translation added by consecutive fixes (FR3) |
| `json_context_store.py`, `migrate/state_v2.py`, `reconcile/service.py` | three writers of `spec_contexts.json`, two suppressed import edges | 14 (CP4), 2 regressions | REBUILD | one writer (FR5) |
| skill scripts (`dd-*/scripts/*.py`, 5,440 lines) | 7 `Refusal` classes, 3 commit loops, 9 git wrappers, 6 root finders, 41 `sys.path` mutations, a four-skill import cycle (7 cycles) | 55 (CP1), 32 regressions | REBUILD — moved to rc-13 | operator subset ruling 2026-10-09 (FR6) |
| `scripts/guards/{run,repo,slop}.py` | 3 `sys.path` mutations, counted by G4 | — | UPDATE — moved to rc-13 | move with FR6's `sys.path` row; rc-12 edits only `slop.py`'s ignore cap (AC5.2) |
| ledger readers (`BUGS.jsonl` 8 modules, `_release_tree.py`, three subject parsers) | each ledger parsed by many modules | 42 (CP3), 22 regressions | REBUILD — moved to rc-13 | G1: over the ceiling, CP3 moves first |
| public-seam contract tests | 42 seams without a contract-complete test (`seams-42.txt`) | — | ADD | no unit carries the net (`today` —); 26 of them are written here |

### Authorities

| question | authority | consults | deleted |
|---|---|---|---|
| may a release job open | `_worktree_new.py` phase check via `_release_schema` | `worktree.py new` | the SPEC-status check (`worktree-new-opens-a-job-outside-implementation`) |
| who writes `spec_contexts.json` | `infrastructure/json_context_store.py` | `migrate/state_v2.py`, `reconcile/service.py` | their direct writes and both `ignore_imports` edges |
| a child-process test environment | `tests/fixtures/harness_env.py` | every spawning test | 11 ad-hoc constructions |
| the workspace CLI spelling in shipped law | one spelling, read alike by stage, shipped history and TREE-5 | `template_history.was_shipped`, `doctor_structural._tree5_check` | `workspace_layout.source_form` (`shipped-law-hardcodes-the-posix-venv-path`) |
| law ≥ 9 | two fresh independent `dd-code-reviewer` judges | main thread records | main-thread scoring |

## DAG

| job | waits on | wave | `W:` | why |
|---|---|---:|---|---|
| Job 1 | — | 1 | `dadaia_workspace/public/data/AGENTS.md`, `dadaia_workspace/public/data/dadaia-AGENTS.md`, `dadaia_workspace/public/data/states-AGENTS.md`, `dadaia_workspace/public/data/handoff-AGENTS.md`, `dadaia_workspace/public/data/tmp-AGENTS.md`, `dadaia_workspace/public/data/worktrees-AGENTS.md`, `dadaia_workspace/public/data/CONTEXT-MAP.md`, `dadaia_workspace/public/templates/repo-AGENTS.md`, `dadaia_workspace/public/templates/specs-AGENTS.md`, `dadaia_workspace/public/scaffold/ADRs/AGENTS.md`, `dadaia_workspace/public/scaffold/audits/AGENTS.md`, `dadaia_workspace/public/scaffold/backlog/AGENTS.md`, `dadaia_workspace/public/scaffold/bugs/AGENTS.md`, `dadaia_workspace/public/scaffold/memory/AGENTS.md`, `dadaia_workspace/public/scaffold/releases/AGENTS.md`, `dadaia_workspace/public/agents/dd-code-reviewer.md`, `dadaia_workspace/public/agents/dd-product-engineer.md`, `dadaia_workspace/public/agents/dd-software-engineer.md`, `AGENTS.md`, `dadaia_workspace/public/skills/dd-ai-eng-knowhow/SKILL.md`, `dadaia_workspace/public/skills/dd-ai-eng-knowhow/AUTHORING.md`, `dadaia_workspace/public/skills/dd-ai-eng-knowhow/CLAUDE-CODE.md`, `dadaia_workspace/public/skills/dd-ai-eng-knowhow/CODEX.md`, `dadaia_workspace/public/skills/dd-ai-eng-knowhow/CONTEXT-ENGINEERING.md`, `dadaia_workspace/public/skills/dd-handoff-emitter/SKILL.md`, `dadaia_workspace/public/skills/dd-cli-library/SKILL.md`, `dadaia_workspace/public/skills/dd-audit-project/SKILL.md`, `dadaia_workspace/public/skills/dd-audit-project/FINDINGS-FORMAT.md`, `dadaia_workspace/public/skills/dd-audit-project/PILLAR-BUGS.md`, `dadaia_workspace/public/skills/dd-audit-project/PILLAR-MEMORY.md`, `dadaia_workspace/public/skills/dd-audit-project/PILLAR-SPECS.md`, `dadaia_workspace/public/skills/dd-backlog-definition/SKILL.md`, `dadaia_workspace/public/skills/dd-bug-registration/SKILL.md`, `dadaia_workspace/public/skills/dd-bug-resolution/SKILL.md`, `dadaia_workspace/public/skills/dd-bug-resolution/LINEAGE.md`, `dadaia_workspace/public/skills/dd-bug-resolution/RED-LOOP.md`, `dadaia_workspace/public/skills/dd-grill-me/SKILL.md`, `dadaia_workspace/public/skills/dd-grill-me/EMISSION-FORMAT.md`, `dadaia_workspace/public/skills/dd-grill-me/PROBLEM-TAXONOMY.md`, `dadaia_workspace/public/skills/dd-code-review/SKILL.md`, `dadaia_workspace/public/skills/dd-code-review/SLOP.md`, `dadaia_workspace/public/skills/dd-gitflow-default/SKILL.md`, `dadaia_workspace/public/skills/dd-manager-orchestration/SKILL.md`, `dadaia_workspace/public/skills/dd-release-definition/SKILL.md`, `dadaia_workspace/public/skills/dd-release-implementation/SKILL.md`, `dadaia_workspace/public/skills/dd-release-implementation/MEMORY-UPDATE.md`, `dadaia_workspace/public/skills/dd-release-implementation/RC-FLOW.md`, `dadaia_workspace/public/skills/dd-release-implementation/RELEASE-EVENTS.md`, `dadaia_workspace/public/skills/dd-spec-navigator/SKILL.md`, `tests/infrastructure/test_public_assets.py`, `tests/public/skills/dd_release_implementation/scripts/test_release.py`, `dadaia_workspace/features/chokepoints/push_gate.py`, `dadaia_workspace/features/specs/canon.py`, `dadaia_workspace/cli/commands/ci.py`, `dadaia_workspace/public/skills/dd-release-implementation/scripts/release.py`, `dadaia_workspace/core/invocation.py`, `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_end.py`, `dadaia_workspace/features/specs/memory_canon.py`, `dadaia_workspace/features/specs/memory_lint.py`, `dadaia_workspace/public/skills/dd-bug-resolution/scripts/_bugs_check.py`, `dadaia_workspace/public/skills/dd-release-implementation/scripts/_release_schema.py`, `dadaia_workspace/public/skills/dd-backlog-definition/scripts/backlog.py`, `dadaia_workspace/public/skills/dd-backlog-definition/scripts/_backlog_check.py`, `dadaia_workspace/public/schemas/backlog/backlog-v1.schema.json`, `dadaia_workspace/public/skills/dd-domain-modeling/SKILL.md`, `dadaia_workspace/public/skills/dd-domain-modeling/CONTEXT-FORMAT.md`, `dadaia_workspace/public/skills/dd-codebase-design/SKILL.md`, `dadaia_workspace/public/skills/dd-codebase-design/DEEPENING.md`, `dadaia_workspace/public/skills/dd-codebase-design/DESIGN-IT-TWICE.md`, `dadaia_workspace/public/skills/dd-architecture-survey/SKILL.md`, `dadaia_workspace/public/skills/dd-architecture-survey/HTML-REPORT.md`, `dadaia_workspace/public/entities/behavior-map.json`, `CONTEXT.md`, `dadaia_workspace/public/templates/shipped-hashes.json`, `dadaia_workspace/core/specs_version.py`, `specs/AGENTS.md`, `specs/ADRs/AGENTS.md`, `specs/audits/AGENTS.md`, `specs/backlog/AGENTS.md`, `specs/bugs/AGENTS.md`, `specs/memory/AGENTS.md`, `specs/releases/AGENTS.md`, `specs/releases/0.5.0/rc-12/PLAN.md`, `specs/releases/0.5.0/rc-12/tasks/job1.md`, `.dadaia/reports/dadaia-workspace/agentic-scorecard/<UTC>/` | FR1 first: every later agent works under the law it lands |
| Job 2 | Job 1 | 2 | `tests/public/skills/dd_gitflow_default/scripts/test__worktree_new.py`, `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_new.py`, `dadaia_workspace/public/data/worktrees-AGENTS.md`, `specs/bugs/BUGS.jsonl` | FR2 alone (the one behaviour change) |
| Job 3 | Job 1 | 2 | `tests/cli/commands/test_reconcile__characterization.py`, `tests/cli/commands/test_context__characterization.py`, `tests/public/skills/dd_spec_navigator/scripts/test_memory__characterization.py`, `tests/public/skills/dd_gitflow_default/scripts/test_worktree__characterization.py`, `tests/public/skills/dd_handoff_emitter/scripts/test_verdict__characterization.py`, `tests/public/skills/dd_bug_resolution/scripts/test_bugs__characterization.py`, `tests/public/skills/dd_release_implementation/scripts/test_release__characterization.py`, `tests/hooks/test_root_whitelist__characterization.py`, `tests/hooks/test_ctx_inject__characterization.py`, `tests/cli/commands/test_ci__characterization.py`, `tests/cli/commands/test_public__characterization.py`, `tests/cli/commands/test_init__characterization.py` | FR4 before every CP job |
| Job 4 | Job 1 | 2 | `tests/fixtures/harness_env.py`, `tests/fixtures/test_harness_env.py`, `tests/fixtures/stores.py`, `tests/scripts/test_ci.py`, `tests/cli/commands/test_doctor.py`, `tests/cli/commands/test_doctor__workspace_fix_lines_clear_their_finding.py`, `tests/infrastructure/runtime_transforms/test_hook_wrappers.py`, `tests/infrastructure/runtime_transforms/test_hook_wrappers__hook_interpreter.py`, `tests/cli/commands/test_context__context_show_live_branch.py`, `tests/cli/commands/test_init__init_with_repo.py`, `tests/infrastructure/test_ledger_scripts.py`, `tests/cli/commands/test_specs.py`, `tests/cli/commands/test_ci__push_gate_gitflow_resolution.py`, `tests/features/certification/test_service.py`, `tests/core/test_invocation__one_bind.py`, `tests/e2e/test_one_line_bootstrap.py`, `tests/helpers/worktree_ws.py`, `tests/public/skills/dd_bug_resolution/scripts/test__specs__workspace_root.py`, `tests/public/skills/dd_handoff_emitter/scripts/test_verdict.py`, `tests/public/skills/dd_release_implementation/scripts/test__release_schema.py`, `tests/public/skills/dd_release_implementation/scripts/test_release__lean_state.py` | FR3 test-side units with AC8.4 |
| Job 5 | Job 1 | 2 | `dadaia_workspace/hooks/root_whitelist.py`, `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_end.py`, `dadaia_workspace/hooks/ctx_inject.py`, `dadaia_workspace/infrastructure/ledger_scripts.py`, `tests/core/test_workspace_layout.py`, `tests/core/test_template_history.py`, `dadaia_workspace/core/workspace_layout.py`, `dadaia_workspace/core/template_history.py`, `dadaia_workspace/features/specs/doctor_structural.py`, `dadaia_workspace/infrastructure/runtime_transforms/codex_assets.py`, `dadaia_workspace/public/templates/shipped-hashes.json`, `specs/releases/0.5.0/rc-12/PLAN.md`, `specs/releases/0.5.0/rc-12/tasks/job5.md` | FR3 production units; after Job 1; J5.T5 takes A7's code-only forward-render alternative |
| Job 6 | Job 3 | 3 | `tests/features/migrate/test_state_v2.py`, `tests/features/reconcile/test_service.py`, `dadaia_workspace/infrastructure/json_context_store.py`, `dadaia_workspace/features/migrate/state_v2.py`, `dadaia_workspace/features/reconcile/service.py`, `dadaia_workspace/container.py`, `dadaia_workspace/cli/commands/reconcile.py`, `dadaia_workspace/cli/commands/init.py`, `dadaia_workspace/cli/commands/migrate.py`, `setup.cfg`, `scripts/guards/slop.py` | FR5 (CP4) after the net |
| Reconciliation | Job 2, Job 3, Job 4, Job 5, Job 6 | 4 | `specs/memory/ARCHITECTURE.md`, `specs/memory/product/catalog.json`, `specs/audits/20260930-structural-convergence/FINDINGS.jsonl`, `specs/releases/0.5.0/_RELEASE.json` | closure: memory pass, finding dispositions, G4/F004/F009 measurement |

Wave 2 has disjoint `W:` sets (checked by `release.py check`). FR6 and FR7 have no job; both move to rc-13. Job 3's net keeps CP1's 5 and CP3's 9 seams, because AC4.1 names them by owner and they then guard the rc-13 refactors from their first commit.

## Write ownership

Each overlap the SPEC names is written once per edit, ordered by a DAG edge:

- `_worktree_new.py`: J2.T2 only.
- `_worktree_end.py`: J1.T11 (AC1.5 docstring, wave 1), then J5.T2 (REBUILD of `_check_approved`, wave 2).
- `release.py`: J1.T11 only (AC1.5 `--origin` help).
- The public law edit of `shipped-law-hardcodes-the-posix-venv-path`: J5.T5 alone (wave 2, after Job 1). No Job 1 task makes it.
- `scripts/guards/slop.py`: J6.T3 only, for the ignore cap (AC5.2).
- `canon.py`, the repo `specs/**/AGENTS.md` copies and the law files carrying the CLI form: Job 1 only; `shipped-hashes.json`: Job 1, then J5.T5 records the forward Win32 forms.
- Generated projections (`.agents/`, `.claude/`, `.codex/`, `.kimi-code/`) are never in `W:`; public sources are staged and installed after their job merges.
- Every behaviour task is two dispatches in separate task trees (RED, then source-only): J1.T10, then J1.T11 and J1.T12; J2.T1, then J2.T2; J5.T4, then J5.T5; J6.T1, then J6.T2. REBUILD and characterization tasks are single dispatches that keep their tests. The CP task (Job 6) never edits a `*__characterization.py` file (AC4.3).
- The Job-0 RED batch is empty (SPEC §5). The main thread re-runs the full suite once at rc-12 birth, before Job 1 (`pytest -n 2`, 301.76 s wall on `b1e402511`).

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
| J1.T1 | 0.4–0.8 | law | J3.T4 | 0.4–0.7 | test |
| J1.T2 | 0.4–0.7 | law | J3.T5 | 0.5–1.0 | test |
| J1.T3 | 0.3–0.5 | law | J4.T1 | 0.5–1.0 | test |
| J1.T4 | 0.4–0.8 | law | J4.T2 | 0.5–1.0 | test |
| J1.T5 | 0.4–0.8 | law | J5.T1 | 0.2–0.4 | test |
| J1.T6 | 0.4–0.7 | law | J5.T2 | 0.3–0.6 | test |
| J1.T7 | 0.4–0.8 | law | J5.T3 | 0.2–0.4 | test |
| J1.T8 | 0.4–0.8 | law | J5.T4 | 0.15–0.3 | test |
| J1.T9 | 0.4–0.8 | law | J5.T5 | 0.5–1.0 | test |
| J1.T10 | 0.15–0.3 | test | J6.T1 | 0.2–0.4 | test |
| J1.T11 | 0.15–0.3 | test | J6.T2 | 0.4–0.7 | test |
| J1.T12 | 0.3–0.6 | test | J6.T3 | 0.1–0.2 | test |
| J1.T13 | 0.8–1.4 | judges | Reconciliation | 0.8–1.5 | closure |
| J2.T1 | 0.15–0.3 | test | each job gate | 0.60–1.33 | gate |
| J2.T2 | 0.2–0.4 | test | | | |
| J3.T1–J3.T3 | 0.4–0.8 each | test | | | |

### Critical path

The schedule is list-scheduled over the DAG edges under B8's two caps (5 open trees; 2 test-running agents; law tasks take a tree slot only). Job end times are in hours from PLAN approval:

| point | low | high |
|---|---:|---:|
| Job 1 merged (J1.T1–T12 under the tree cap, then J1.T13, then the gate) | 2.5 | 4.9 |
| Jobs 2–5 merged (wave 2: 4.8–9.5 task-hours through 2 test slots, plus gates; Job 5 last; 3.2–6.4 h after Job 1) | 5.7 | 11.4 |
| Job 6 merged | 6.1 | 12.2 |
| Reconciliation merged; candidate PR CI green (B2 is inside the 0.8–1.5 h) | **6.9** | **13.7** |

- **Critical path: 6.9–13.7 h** (Job 1 → wave 2 under the test-agent cap → Job 6 → Reconciliation). The span is PLAN approval (`release.py phase IMPLEMENTATION`) to the green candidate PR, with operator latency excluded (A1). The high bound exceeds the 8.7 h ceiling by 5.0 h; the low bound is 1.8 h under it.
- **Aggregate: 15.8–31.8 agent-hours.** That is 14.8–29.6 for the scheduled tasks and gates (each gate counted at its full elapsed time), plus 0.7–1.6 for the second judge and the reopened fix trees in J1.T13, 0.2–0.5 for the reconciliation reviewer, and 0.1 for the birth suite run.
- **Before the define-review correction (A5), for the record:** 6.7–13.4 h and 15.6–31.4 agent-hours.
- **Before the subset ruling, for the record:** with FR6 kept, the critical path was 9.5–18.9 h and the aggregate 19.8–39.8 agent-hours; with FR7 also kept, 11.4–22.8 h.
- **Uncertainty** comes from four sources:
  - review rounds, which ran 2–6 per job in rc-11 (B6);
  - a second fix round in the law-9 loop;
  - the shipped-law REBUILD design, which J5.T4 decides;
  - the Windows matrix for FR3, which only the candidate PR judges because push runs are Linux-only.
- **Contingency is not included.** Each review round past the first rework on a critical-path job costs +0.30–0.74 h. Each further AC1.4 score/fix round costs +0.5–0.9 h. A Windows red at the candidate PR reopens Job 4 or Job 5 for +0.6–1.5 h. rc-11 ran 1.68× its forecast high (B4); that factor is disclosed and not applied.

### Remaining levers (not applied; ruled out or unruled)

| lever | critical h |
|---|---:|
| as planned | 6.9–13.7 |
| test-agent cap 3 (A3 keeps 2) | 6.4–12.7 |
| relax "FR1 first" (A2 keeps strict) | 6.1–11.2 |

No lever brings the high bound under 8.7 h.

## Open seams

Each seam was ruled on 2026-10-09 by the main thread as a conservative default, under operator delegation.

- A1. **Ceiling span.** It runs from PLAN approval to the green candidate PR, excluding operator latency.
- A2. **FR1 first, read strictly.** Every job waits on Job 1's merge, including AC1.4, because the operator ordered the law first.
- A3. **Test-agent cap.** It stays at 2, the standing ruling.
- A4. **Moot.** The three `scripts/guards/` `sys.path` mutations move with FR6 to rc-13. FR5 still needs `slop.py` for the ignore cap, so J6.T3 keeps that one edit and nothing else.
- A5. **Net scope** (ruled 2026-10-09, main thread, conservative default; corrected at define review). The net covers AC4.1's 19 owned seams plus every listed seam whose code an rc-12 job changes. That is 26 seams. The operator's order is "não quebrar nada".
  - `hook root_whitelist` and `hook ctx_inject` (Job 5).
  - `dadaia ci push-gate-check` (J1.T11 strings).
  - `dadaia public stage`, `dadaia public install` and `dadaia public doctor`: J5.T5 rebuilds `workspace_layout.render_registry_tables`/`source_form` and `codex_assets.py`, and `public_assets._staged_bytes` (`infrastructure/public_assets.py:116-121`) runs `render_registry_tables` both for stage and for the doctor's comparison.
  - `dadaia init`: J5.T5 rebuilds `template_history.was_shipped`, which `init` reaches through `print_next_step` → `onboarding._first_pass`.
  - Only the six `registry.py` seams leave with FR6.
  - `was_shipped` is also reached by `context create`, `context alive`, `context list` and `dadaia doctor`. None of those is on the 42-seam list, so the net does not add them.
- A6. **Moot.** FR6 left rc-12.
- A7. **Shipped-law design.** J5.T5's design for `shipped-law-hardcodes-the-posix-venv-path` is decided by J5.T4's RED test inside the job. Its `W:` is the full law-edit set; a code-only design shrinks it by PLAN amendment. `public/data/fixed/slop-law.md` carries the CLI form but is outside AC1.6 and stays out of `W:`.
- A8. **Acceptable.** J1.T13's `W:` is the scorecard record outside the repo (`.dadaia/reports/…/<UTC>/`).
- A9. **Behaviour-preserving.** A `reconcile` tree opens in IMPLEMENTATION and in CLOSURE, as today. Only job and task trees need IMPLEMENTATION; J2.T1 asserts both.
- A10. **Acceptable as stated.** The AC8.4 grep is the F018 measure. Spawns without `env=` are out of scope.
- A11. **Job 6 composition scope.** J6.T2 includes `container.py` plus the `reconcile`, `init` and `migrate` CLI callers. They are the existing production call sites that must supply AC5.1's injected store and AC5.2's migration/version dependencies after the two cross-feature imports are deleted; this is wiring for the approved behaviour-preserving FR5 refactor, with no new behaviour or AC.

## Verification and closure

- Each RED task proves its failure for the intended reason. Each source task turns the same focused tests green without touching a test path. Each job gate runs the tracked `verify: python scripts/ci.py job` once and takes one bound reviewer verdict.
- G3/AC4.3: Job 3's net is green on Job 3's base and on Job 6's head. `git diff --name-only` over Job 6's range prints no `*__characterization.py` file.
- G4 rows kept in rc-12: `ignored_imports` 2 → 0 and `spec_contexts.json` writers 3 → 1 (Job 6 names the commands). The `sys.path`, cycle and `BUGS.jsonl` reader rows are re-measured in rc-13.
- Reconciliation (dd-product-engineer) covers:
  - the F123 `ARCHITECTURE.md` line on import-linter contracts after FR5;
  - the dispositions of F003, F004, F005, F009, F018, F048, F051, F123 and F135;
  - the AC8.1 3-day re-bug rate (≤ 30%);
  - the AC8.2 zero-caused rule, with the fix-induced share reported against 37/189;
  - the closure entry in `_RELEASE.json`.

  No backlog id exits in rc-12.
