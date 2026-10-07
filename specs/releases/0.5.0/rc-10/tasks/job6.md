# TASKS — 0.5.0 rc-10, Job 6 — the test freeze

**Status:** Approved
**Approval:** by operator delegation 2026-10-06 ("Delego: APPROVED do revisor basta (Recommended)", handoff 2026-10-06T044815Z-main-thread-overnight-delegation); dd-code-reviewer APPROVED d1f1b01b1.

Paths are relative to the repo root; aliases as in `PLAN.md` (`f/`, `pub/`, `S/`, `bugres/`, `relimpl/`, `GF/`, `evals:`). Gates: task — `verify-task:` on the touched files plus `Owner-tests:`; stage — `verify-stage:`; job — CI matrix + one review + `verify:`. Job 6 itself runs under today's law; its freeze binds every job opened after it merges and the instance is re-projected.

- F-3 ruled (a) (PLAN): the one test diff past the anchor that lands is a diff whose only change deletes a RED-marker line matching the repo's `tests-red:` line (agent default 9, unruled).

- Edges: Jobs 1–5, 7, 8. Test paths below are today's; the driver rewrites them to Job 7's mirror paths when the job opens. Readings: PLAN agent defaults 4 and 5 (5 is the reviewer's literal reading: anchor from subjects, fail closed, pre-anchor test lines frozen, new tests only in a tests-only stage); F-1 and F-3 resolved; amendment visibility per agent default 10.

## Stage J6.S1 — RED

- Contract: exit tests every AC6.0–AC6.2 row and the public-source guard row RED as strict xfail; envelope `tests/integration/test_worktree_lifecycle.py`, `tests/helpers/worktree_ws.py`, `tests/contract/test_public_source_hygiene.py`; ACs AC6.0–AC6.2, AC9.1

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J6.S1.T1 | AC6.0–AC6.2 | `tests/integration/test_worktree_lifecycle.py`, `tests/helpers/worktree_ws.py` | RED: a worktree editing its own `tests:` line still has a test edit refused; no `tests:` line refuses with `Operator action: commit the tests: line on <work>'s AGENTS.md`, and after that commit the same merge lands; past the RED anchor any modified or deleted test line, in any file, refuses with one `Operator action:` line; a pure rename lands; added test lines land only in a group touching test paths alone; a commit with no stage id is its own group; a test file born after the anchor and then edited refuses; a hotfix's RED commit followed by a fix commit with a marker-only deletion lands; an underivable anchor refuses (fail closed); a marker-only deletion (a line matching `tests-red:`) lands; a deletion of the marker plus any other line, an assert included, refuses; a deletion of a marker line in a form `tests-red:` does not declare refuses; a RED stage whose new test errors cannot close |
| J6.S1.T2 | public law leaks (bug `public-law-teaches-the-private-pipeline`) | `tests/contract/test_public_source_hygiene.py` (mirror path after Job 7: one new row in its table, reusing `_denied_lines`) | RED: shipped text under `public/**/*.{md,json,py,sh}` and `features/chokepoints/*.py` names no remote-CI, GitHub, dependency-alert or one-stack tool (the pattern and globs are the bug's, no spare); a stage-1 path `pkg/x_test.go` is accepted — only if the release-script work of the bug batch has not landed it |

## Stage J6.S2 — the freeze

- Contract: exit tests J6.S1 green, unit + integration green; envelope `GF/_worktree_freeze.py`, `GF/_worktree_end.py`, `AGENTS.md`, `tests/conftest.py`, `pub/scaffold/releases/AGENTS.md`, `specs/releases/AGENTS.md`, `pub/data/worktrees-AGENTS.md`, `S/dd-release-definition/SKILL.md`, `relimpl/RC-FLOW.md`, the canon pin; ACs AC6.0–AC6.3

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J6.S2.T1 | AC6.0, AC6.2 | `GF/_worktree_freeze.py` (new: pure judge over diff rows and stage ids; one git read), `GF/_worktree_end.py` (the `AGENTS.md` line reader lifted out of `_gate`, shared by `verify*:` and `tests:`; one call in `merge` for task and job merges) | `test_worktree_lifecycle.py` |
| J6.S2.T2 | AC6.0 | `AGENTS.md` (`tests: tests/**` and `tests-red: ^\s*@pytest\.mark\.xfail\(strict=True` beside the verify lines; this repo's pytest form of the RED marker — one decorator line, never `marks=` inside `pytest.param`, never a module constant, a parametrized RED row becomes its own decorated function, the `reason` short enough to stay on one line after ruff format at 100 columns — lives here and nowhere in the public law) | `test_worktree_lifecycle.py` |
| J6.S2.T3 | AC6.1 | `tests/fixtures/red_marker.py` (new pytest plugin: every strict xfail gets `raises=AssertionError`), `tests/conftest.py` (`pytest_plugins`) | `test_worktree_lifecycle.py` |
| J6.S2.T4 | AC6.1–AC6.3 | `pub/scaffold/releases/AGENTS.md` (§3's same-task rewrite clause leaves; tests born in RED stages, frozen at the anchor; a REBUILD keeps the fix's tests; the RED marker stated generically (inside ruling (a)): one line matching the repo's `tests-red:` pattern, and the RED stage's test fails for its reason — no language or framework named; AC6.1's test-audit and the RED-stage review check the form, no code does; the freeze's residual — an added line (an inserted skip) — is caught by the RED review and test-audit), `specs/releases/AGENTS.md` (by `specs upgrade`), `pub/data/worktrees-AGENTS.md` (the freeze in gate 1 and 4), `S/dd-release-definition/SKILL.md` §5 (the same generic RED-marker statement), `relimpl/RC-FLOW.md` step 2, `S/dd-gitflow-default/SKILL.md` §3a and `bugres/SKILL.md` (shape 3 under the freeze: a RED commit in a RED stage, then a fix commit holding the code, the `BUGS.jsonl` line and the marker-line deletion — derived from 0209 + F-3 (a)), `core/specs_version.py` (gains the public `CANON_AT`: the pin moves here), `tests/unit/core/test_specs_version.py` (imports `CANON_AT` under the old name; the assert stays byte-identical), `pub/templates/shipped-hashes.json` | `test_specs_version.py`, `test_tree5_shipped_history.py`, `test_law_states_what_the_code_does.py` |

## Stage J6.S3 — the public law stops teaching the private pipeline

- Contract: exit tests J6.S1's guard row green, unit + integration green; envelope the law files below, `pub/templates/shipped-hashes.json`, `core/specs_version.py` (`CANON_AT` re-pin), `scripts/`; ACs AC9.1. Operator ruling 2026-10-06: "para os usuários do dadaia-workspace CI em repo remoto não deve ser de forma alguma obrigatorio" (ADR 0190 amended); every law commit cites the ADR it follows.

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J6.S3.T1 | AC9.1 | `pub/data/AGENTS.md` (both PRs need the repo's `verify:` line; the evals clause leaves), `pub/entities/registry.json` (the CI PR gate clause; tool caches), `relimpl/MEMORY-UPDATE.md`, `S/dd-gitflow-default/CICD-AUTOMATION.md` (the `gh api` line), `pub/data/CONTEXT-MAP.md`, `pub/data/states-AGENTS.md` (library citations) | `test_context_map.py`, `test_law_states_what_the_code_does.py` |
| J6.S3.T2 | AC9.1 | `pub/agents/dd-code-reviewer.md` (`git diff <base>...<target>`, the verify output, `## Verify`), `pub/agents/dd-software-engineer.md` (the repo's own commands; the package-path and workflow allowlist and the one-stack bullets leave) | `test_core_persona_names.py`, `test_agent_tier_taxonomy.py` |
| J6.S3.T3 | AC9.1 | `pub/scaffold/bugs/AGENTS.md` and `specs/bugs/AGENTS.md` (block list: `verify:` red, a security finding), `pub/scaffold/memory/QUALITY.md`, `S/dd-audit-project/PILLAR-MEMORY.md`, `S/dd-audit-project/FINDINGS-FORMAT.md`, `S/dd-code-review/SKILL.md`, `S/dd-code-review/SLOP.md`, `core/specs_version.py` (`CANON_AT`), `pub/templates/shipped-hashes.json` | `test_specs_version.py`, `test_tree5_shipped_history.py`, `test_law_states_what_the_code_does.py` |
| J6.S3.T4 | AC9.1 | `S/dd-gitflow-default/SKILL.md` (the PR gate section, the CI wording, the stage trailer), `pub/data/worktrees-AGENTS.md` (the gate-2 parenthetical), `relimpl/SKILL.md` and `relimpl/RC-FLOW.md` (the verify: line for CI wording; "RED" and "the repo's quarantine mechanism" for the strict-xfail and quarantine wording), `S/dd-release-definition/SKILL.md`, the consumer validation recipe moved out of `pub/data/` and its test path, `pub/scripts/pre-push-ci-gate.sh` (the toolchain-specific runner fallback) (its law texts carry no shipped hash and leave the canon pin as T3 set it) | the guard row, `test_pre_push_gate_venv_probe.py`, `test_certify_invocation_flags_exist.py` |
| J6.S3.T8 | AC6.0 | `GF/_worktree_freeze.py` (the exec bit every skill-owner script carries) | `test_public_assets__public_scripts_thin_wrapper.py` |
| J6.S3.T9 | AC9.1 | `tests/public/scripts/test_pre_push_ci_gate__pre_push_gate_venv_probe.py` (the `poetry_on_path` row leaves with the fallback J6.S3.T7 deleted) | the file |
| J6.S3.T10 | AC9.1 | `pub/skills/dd-cli-library/SKILL.md` (cites `init`, `specs upgrade`, `migrate`, the verbs the moved recipe cited) | `tests/cli/commands/test_help.py` |
| J6.S3.T11 | AC9.1 | `specs/memory/product/platform/consumer-agent-support.md`, `specs/memory/product/platform/pypi-distribution.md` (`sources` and text follow the recipe to `scripts/`; dd-product-engineer) | doctor LINT-1 and MEM-DRIFT-2 clean |
| J6.S3.T5 | — | this file | close task, last: regenerates `pub/entities/behavior-map.json` (the skills' hashes T4 moved); `test-audit:`, `mutation:`; `done` |

- done: Job 6 — every task landed on `wt/0.5.0-rc10/job6` through its task merge: J6.S1.T1 f327dda3b and J6.S1.T2 9f1c9f80a (RED, strict xfail); J6.S2.T1 6e99f6a52 and 26f7e5635 (the freeze judge and the shared `AGENTS.md` line reader; the RED markers lift), T2 35dd0450d, T3 a8c2fbf60, T4 6e857ff2f and fc6640798 (the freeze in the law) and 5e71ce92a (shipped history), T5 e01ddf995 (the repo law template's empty `tests:` line); J6.S3.T1 565fc4b50, T2 320ef632d, T3 4f6cc6b98, T4 f0d5436c9 (the consumer recipe moves to `scripts/`), T6 be615e848 and 81752a87f (`CICD-AUTOMATION.md`), T7 24dddd3e2 (the pre-push runner drops the poetry fallback), T8 ea6cfd0af (the exec bit), T9 0d15072fe (REBUILD of the runner-resolution table); the job file's stage rows 1192e55d2, d77e386de, 8a8b26fff; closed by J6.S3.T5.
- done: Job 6 review repair — S3 repairs 3f3cf7020 (T10 `dd-cli-library`), 591af0ce2 (T11 platform atoms), ee2449ff9 (T5 derived docs); S4 618677797 (T2 RED) and 6fe0486e5 (T1, whole hunks and adjacent hunks); S5 d9546e432 (the freeze judges the job's own range, first-parent diffs); S6 55d6c1e9a (T1, killing rows for the four fail-open mutants) and 05c056521 (T2, the law line); closed by J6.S6.T3.

## Stage J6.S4 — RED for the review's findings (CHANGES_REQUESTED on 8f8da611d)

- Contract: exit tests the rows below RED as strict xfail for an AssertionError;  envelope `tests/public/skills/dd_gitflow_default/scripts/test__worktree_freeze.py`, `tests/public/skills/dd_gitflow_default/scripts/test__worktree_end__worktree_freeze.py`; ACs AC6.0–AC6.2.
- AC9.1's guard row (`test_public_law_names_no_private_pipeline`) cannot end green in this job: its remaining hits are the merge gate's `ci_run` (bug job-merge-accepts-any-ci-run-url) and lie outside every J6 `W:`; the exit moves to the bug batch.

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J6.S4.T1 | AC6.0, AC6.2 | `tests/public/skills/dd_gitflow_default/scripts/test__worktree_freeze.py` | RED (pure judge): a hunk of several lines and two adjacent hunks are each read whole; a binary test file edit refuses; the anchor's first commit is inside the frozen range (off-by-one); an invalid `tests-red:` pattern refuses with its fix line |
| J6.S4.T2 | AC6.0, AC6.2 | `tests/public/skills/dd_gitflow_default/scripts/test__worktree_end__worktree_freeze.py` | RED (merge): a merge commit carrying a test edit refuses; an operator commit on the work branch the job lacks is not judged as the job's; an underivable anchor refuses; a hotfix RED commit then a no-id fix commit with a marker-only deletion lands |

## Stage J6.S5 — the freeze judges the job's own range

- Contract: exit tests J6.S4's rows green, unit + integration green, no kept fail-open survivor; envelope `GF/_worktree_freeze.py`; ACs AC6.0–AC6.2.

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J6.S5.T1 | AC6.0, AC6.2 | `GF/_worktree_freeze.py` (range `<merge-base>..HEAD`; a range commit with two parents refuses, or each commit diffs against its first parent; the hunk loop reads whole hunks) and the J6.S4 marker lines | `tests/public/skills/dd_gitflow_default/scripts/test__worktree_freeze.py`, `tests/public/skills/dd_gitflow_default/scripts/test__worktree_end__worktree_freeze.py` |

## Stage J6.S6 — the freeze's fail-open survivors and its law line

- Contract: exit tests unit + integration green, mutation-diff on `GF/_worktree_freeze.py` keeps no fail-open survivor; envelope `tests/public/skills/dd_gitflow_default/scripts/test__worktree_freeze.py`, `pub/data/worktrees-AGENTS.md`, the close's generated files; ACs AC6.0, AC6.2.

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J6.S6.T1 | AC6.0 | `tests/public/skills/dd_gitflow_default/scripts/test__worktree_freeze.py` (rows that kill the four fail-open mutants J6.S5.T1 named: a marker-first several-line hunk in a tests-only group refuses; a binary edit in a tests-only group refuses; a new binary test file beside code refuses; a range whose first row edits a test and whose last row is clean refuses) | the file; mutation-diff shows the four killed |
| J6.S6.T2 | AC6.0 | `pub/data/worktrees-AGENTS.md` (the freeze judges `<merge-base>..HEAD` first-parent diffs, not `<work>...HEAD`) | `tests/contract/test_law_states_what_the_code_does.py` and the guard rows |
| J6.S6.T3 | — | this file | close, last: behavior map, shipped hashes, derived docs regenerated for S3–S6; `test-audit:`, `mutation:`; `done` |
