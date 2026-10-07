# TASKS — 0.5.0 rc-10, Reconciliation

**Status:** Approved
**Approval:** by operator delegation 2026-10-06 ("Delego: APPROVED do revisor basta (Recommended)", handoff 2026-10-06T044815Z-main-thread-overnight-delegation); dd-code-reviewer APPROVED d1f1b01b1.

Paths are relative to the repo root; aliases as in `PLAN.md` (`f/`, `pub/`, `S/`, `bugres/`, `relimpl/`, `GF/`, `evals:`). Gates: task — `verify-task:` on the touched files plus `Owner-tests:`; stage — `verify-stage:`; job — CI matrix + one review + `verify:`. Bound by the freeze; it writes no test.

## Stage JR.S1 — RED (none: AC10.1–AC10.5 have no test)

- Contract: no acceptance test exists for AC10.1–AC10.5 (memory, ledgers, ADRs, release state); no task rows.

## Stage JR.S2 — memory and ledgers

- Contract: exit tests `bugs.py check`, `backlog.py check`, `release.py check`, `dadaia doctor` clean; `test_docs_derived_from_memory.py` green; envelope `specs/memory/**`, `docs/*.md`, `specs/audits/20260930-structural-convergence/FINDINGS.jsonl`, `specs/ADRs/decisions.jsonl`, `specs/backlog/**`; ACs AC10.1, AC10.3, AC10.4

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| JR.S2.T1 | AC10.1 | `specs/memory/**` (each atom with its derived sections), `docs/*.md`; every `tests/…py` path in `QUALITY.md`/`ARCHITECTURE.md` exists (Job 7 moved them); `RELEASE-TREE-MEMORY` gone | checks: the SPEC's greps |
| JR.S2.T2 | AC10.1 | `specs/audits/20260930-structural-convergence/FINDINGS.jsonl` (F098, F128 `resolved`, by `audit.py disposition`) | `audit.py` |
| JR.S2.T3 | AC10.3 | `specs/ADRs/decisions.jsonl` (`measured_by` repairs of 0208, 0209, 0210, the 0138 lane; and ADR 0220, multi-platform by construction, accepted by the operator 2026-10-07T02:37:54Z, "Aceito, com essa divisão (Recommended)", landed as `docs(JR.S2.T5)` bd18b7d3b: one writer of this file per stage, LEDGER-RELEASE-SCHEMA) | `dadaia doctor`, `tests/features/specs/test_doctor_adr.py` |
| JR.S2.T4 | AC10.4 | `specs/backlog/**` (each Origin entry and the three rc-9 deliveries exit once, `delivered --release 0.5.0`; `agent-behavior-evals` after AC11.6 is logged) | `backlog.py check` |
| JR.S2.T6 | AC10.1 | `specs/releases/0.5.0/rc-10/tasks/job9.md` (Status line and the `done` shas: each task's sha as it landed on `feature/0.5.0`, by subject, since the rebase rewrote them) | `tests/features/specs/test_doctor_release.py` |

## Stage JR.S3 — the balance and closure

- Contract: exit tests `release.py check` in CLOSURE (AC4.4's block current), `bugs.py status` `0 open`; envelope `specs/memory/**`, `docs/bug-ledger-lessons.md`, `CONTEXT.md`, `specs/releases/0.5.0/_RELEASE.json`, this rc's job files; ACs AC4.5, AC9.1, AC10.2, AC10.5
- AC10.5's rc-11 SPEC is drafted in its own `0.5.0-rc11/define` tree, an act outside this job.

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| JR.S3.T1 | AC4.5, AC10.2 | `specs/memory/QUALITY.md` (`## Bugs`: the first block by `bugs.py balance --write` after the sweep, then the written review with the latest evals verdict line), `specs/memory/product/**/bug-ledger.md` and `specs/memory/product/catalog.json` (the atom move), `docs/bug-ledger-lessons.md` (re-derived from `## Bugs`, one merge, 0192), `CONTEXT.md` (the SPEC's Terms) | `release.py check`, `test_docs_derived_from_memory.py` |
| JR.S3.T2 | AC10.2, AC10.5 | `specs/releases/0.5.0/_RELEASE.json` (readouts, AC8.1's readout, each job's merge entry and bug-surface delta; phase) | `release.py check` |

## Stage JR.S4 — RED amendment (eval run 37652269562, bug `onboarding-writes-no-tests-line`)

- Contract: a RED-stage amendment (ADR 0209), approved on the reviewer's APPROVED by operator delegation ("Delego: APPROVED do revisor basta (Recommended)", 2026-10-06: TASKS and test amendments); the bug is registered by delegation ("Registra e corrige se o revisor reproduzir (Recommended)"): the eval grader reproduced it 3/3. ADR 0216 says onboarding writes the `tests:` line; no code does, so a repo whose `AGENTS.md` predates onboarding refuses every merge (`this repo declares no tests: line`) and `t2-block-list-bug` scored 0/3 against 3/3. Exit: the new rows fail by assertion at HEAD; ACs AC6.0, AC11.6

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| JR.S4.T1 | AC6.0 | `tests/features/specs/test_canon__scaffold_repo_law.py` (new rows only: a present `AGENTS.md` with no `tests:` line gains the template's `tests:` line, appended, its own text kept byte for byte; a present `tests:` line, empty or not, is left alone; the shipped template's `tests:` line is non-empty), `tests/cli/` specs-init owner file if `specs init` needs its own row (a repo whose `AGENTS.md` lacks `tests:` leaves `specs init` declaring a non-empty `tests:` line; and the amendment ADR 0216 forces: `test_an_existing_scoped_law_is_never_overwritten`'s own law declares a `tests:` line, so it still proves a present law is kept byte for byte — its assert's literal gains that same line, nothing else) | RED: each new row fails by assertion at HEAD; the one amended row stays green at HEAD and after the fix |
| JR.S4.T2 | AC4.1 | `scripts/guards/repo.py` (`_SECTIONS`: QUALITY.md's order is Principles, Test architecture, Gates, Bugs — the section AC4.1 requires; any other order still refuses) | bug `canonical-shape-guard-refuses-the-bugs-section` (the JR.S4 stage gate red: JR.S3.T1 wrote `## Bugs`), registered by delegation; RED: the guard's own `control` planted case, NOISY at HEAD; a stage-gate repair, so it lands in this stage |

## Stage JR.S5 — onboarding declares the tests: line

- Contract: exit the JR.S4 rows green and `test_present_law_is_never_overwritten` unchanged and green; envelope `dadaia_workspace/features/specs/canon.py`, `dadaia_workspace/cli/commands/specs.py`, `dadaia_workspace/public/templates/repo-AGENTS.md`, `dadaia_workspace/public/entities/behavior-map.json`; ACs AC6.0, AC11.6

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| JR.S5.T1 | AC6.0 | `dadaia_workspace/public/templates/repo-AGENTS.md` (its `tests:` line carries the one default, language-neutral glob set — the only place the default lives), `dadaia_workspace/features/specs/canon.py` (one function, called by `specs init` beside `scaffold_repo_law`, appends the template's `tests:` line to a present `AGENTS.md` that has none; `scaffold_repo_law` keeps "never overwritten"), `dadaia_workspace/cli/commands/specs.py` (the call and its `[created]`/`[declared]` line), `dadaia_workspace/public/entities/behavior-map.json` (re-recorded) | JR.S4.T1's rows; bug `onboarding-writes-no-tests-line` resolved by this task; sweep `git grep -n '^tests:' -- dadaia_workspace` names one default | — reverted (dd5e6e03a): review REJECTED 1dedca22b HIGH 2 (four newline rows were born in this GREEN commit, ADR 0209); redone as JR.S6.T1 + JR.S7.T1 |

## Stage JR.S6 — RED amendment (review REJECTED 1dedca22b)

- Contract: a RED-stage amendment (ADR 0209), approved on the reviewer's APPROVED by operator delegation ("Delego: APPROVED do revisor basta (Recommended)", 2026-10-06); bugs registered by delegation ("Registra e corrige se o revisor reproduzir (Recommended)"): the reviewer reproduced each. Tests only, every new row `xfail(strict=True, raises=AssertionError)` failing by assertion at HEAD; no existing assert changes. Exit: the rows xfail at HEAD; ACs AC6.0, AC6.1, AC6.2

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| JR.S6.T1 | AC6.0 | `tests/features/specs/test_canon__scaffold_repo_law.py`, `tests/cli/commands/test_specs.py` (new rows: the declared line keeps the law's own newline style — CRLF, no final newline, empty law; a law that is not UTF-8 gains the line, its bytes kept; an unreadable law leaves `specs init` exiting 0 with the rest of onboarding done; a law whose first line is `tests:` after a UTF-8 BOM is left alone; the shipped default freezes `src/test/java/a/FooTest.java`, `spec/foo_spec.rb`, `web/__tests__/a.js`, `pkg/tests/conftest.py`), `tests/public/skills/dd_gitflow_default/scripts/test__worktree_end.py` (the `tests:` line after a UTF-8 BOM is declared) | bug `onboarding-writes-no-tests-line` (redo), review MEDIUM 1, MEDIUM 2, LOW 1 |
| JR.S6.T2 | AC6.1, AC6.2 | `tests/public/skills/dd_gitflow_default/scripts/test__worktree_freeze.py` (new rows: a stage whose commits touch tests only is RED wherever it sits — a range with an empty `S1` and a test-only `S4` merges; a test-only stage may amend an old assert; a stage that also writes source still refuses an added or changed test line; a range with stage ids and no test-only stage is judged, never refused for lacking a stage 1) | bug `freeze-cannot-see-a-red-amendment-stage` |

## Stage JR.S7 — fixes (review REJECTED 1dedca22b)

- Contract: exit the JR.S6 rows green, `dadaia doctor` clean, CI green; envelope as the rows; ACs AC4.5, AC6.0, AC6.1, AC6.2

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| JR.S7.T1 | AC6.0 | `dadaia_workspace/public/templates/repo-AGENTS.md` (the one default glob set: `**/tests/** **/test/** **/spec/** **/__tests__/** **/test_*.* **/*_test.* **/*_spec.* **/*.test.* **/*.spec.* **/*Test.*`), `dadaia_workspace/features/specs/canon.py` (`declare_tests_line` reads and appends bytes, never decodes; a BOM never hides a `tests:` line; an unreadable law is skipped), `dadaia_workspace/cli/commands/specs.py` (the call after the gitflow write, its `[declared]` line) | JR.S6.T1's canon and specs rows; resolves `onboarding-writes-no-tests-line` |
| JR.S7.T2 | AC6.1, AC6.2 | `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_freeze.py` (REBUILD of the RED anchor, by deletion: a range with stage ids and no stage-1 commit is judged from its base instead of refused — the "no commit names its RED stage" refusal leaves; every other judgement stays, so an old assert changed past the anchor still refuses, as ADR 0209 sends a wrong test to an operator-approved amendment; JR.S6.T2's `test_a_test_only_stage_may_amend_an_old_assert` contradicts ADR 0209 and leaves, and `test_a_job_with_no_commit_naming_its_red_stage_refuses` becomes the judged-from-base row — test amendments by the delegation, in this REBUILD commit), `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_end.py` (`_declared` reads a line after a UTF-8 BOM) | JR.S6.T2's rows and JR.S6.T1's `_declared` row; resolves `freeze-cannot-see-a-red-amendment-stage`; commit `refactor(bugs): … — REBUILD …` |
| JR.S7.T3 | AC4.5 | `specs/memory/QUALITY.md` (`## Bugs`'s written review states its causes, verdicts and lessons with no release or candidate id), `docs/bug-ledger-lessons.md` (its sections derived from QUALITY re-derived, their `derived-from` hashes re-recorded) | `dadaia doctor` clean of MEM-NARRATIVE-1, `tests/contract/test_docs_derived_from_memory.py` green; resolves `quality-bugs-review-names-release-ids` |
| JR.S7.T4 | — | `dadaia_workspace/public/entities/behavior-map.json` (re-recorded after T1 and T2 land) | `tests/infrastructure/test_entity_doctor.py` |

## Stage JR.S8 — RED amendment (review APPROVED 142cf04c7, the non-blocking findings)

- Contract: a RED-stage amendment (ADR 0209) approved by operator delegation ("Delego: APPROVED do revisor basta (Recommended)", 2026-10-06); bugs registered from the reviewer's findings by delegation ("Registra e corrige se o revisor reproduzir (Recommended)"). Tests only; new RED rows `xfail(strict=True, raises=AssertionError)`; the one assert amendment is the adversary row's literal. Exit: the rows xfail at HEAD; ACs AC6.0, AC6.2

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| JR.S8.T1 | AC6.0 | `tests/public/skills/dd_gitflow_default/scripts/test__worktree_end.py` (a `tests:` line after a UTF-8 BOM is declared when git's output decodes under a non-UTF-8 locale; an agreement row: `_worktree_end._declared` and `canon.declare_tests_line` judge the same law fixtures alike — present, absent, empty, BOM, CRLF), `tests/features/specs/test_canon__scaffold_repo_law.py` (the shipped default freezes no `src/ui/ABTest.tsx`, `docs/LoadTest.md`), `tests/cli/commands/test_specs.py` (the `[declared]` line names the default and asks to narrow it) | bugs `declared-bom-strip-depends-on-locale-decoding`, `tests-line-predicate-lives-in-two-readers`, `default-tests-globs-over-match-source` |
| JR.S8.T2 | AC6.2 | `tests/public/skills/dd_gitflow_default/scripts/test__worktree_freeze.py` (`test_a_source_stage_after_a_test_only_stage_refuses_an_added_or_changed_test_line` asserts the literal `(path, anchor)`) | bug `freeze-adversary-row-asserts-not-none`; resolved by this task (an assert amendment, the delegation) |

## Stage JR.S9 — fixes (the non-blocking findings)

- Contract: exit the JR.S8 rows green, CI green; envelope as the rows; ACs AC6.0

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| JR.S9.T1 | AC6.0 | `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_end.py` (`_declared` reads the law as UTF-8 whatever the locale), `dadaia_workspace/public/templates/repo-AGENTS.md` (the default drops `**/*Test.*`; `**/test/**` keeps Maven's `src/test/`), `dadaia_workspace/cli/commands/specs.py` (the `[declared]` line names the default and asks to narrow it), `dadaia_workspace/public/entities/behavior-map.json` (re-recorded in this task) | JR.S8.T1's rows; resolves the three bugs |

## Stage JR.S10 — RED amendment (review REJECTED 90ca2c78c)

- Contract: a RED-stage amendment (ADR 0209) approved by operator delegation ("Delego: APPROVED do revisor basta (Recommended)", 2026-10-06); bugs registered from the reviewer's reproduced findings by delegation. Tests only; new RED rows `xfail(strict=True, raises=AssertionError)`; the amendments are named. Exit: the rows xfail at HEAD; ACs AC6.0

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| JR.S10.T1 | AC6.0 | `tests/public/skills/dd_gitflow_default/scripts/test__worktree_end.py` (`test_a_tests_line_after_a_bom_is_declared_when_git_output_decodes_as_cp1252` is replaced by a row at the subprocess boundary: real git, the text decoding of a call that names no encoding forced to cp1251 and to cp932, `_declared` returns the literal `x/**`), `tests/features/specs/test_canon__scaffold_repo_law.py` (the shipped default freezes `Foo.Tests/FooTest.cs` and `app/src/androidTest/a/FooTest.kt`), `tests/cli/commands/test_specs.py` (a latin-1 law: `specs init` exits 0 and the law gains the line; the `'narrow' in echo` text assert leaves, the `default in echo` assert stays) | bugs `skill-git-output-decodes-with-the-locale`, `declared-echo-rereads-the-law`, `default-tests-globs-under-match-dotnet-android`; the replaced row and the dropped text assert are amendments by the delegation |

## Stage JR.S11 — fixes (review REJECTED 90ca2c78c)

- Contract: exit the JR.S10 rows green, CI green; envelope as the rows; ACs AC6.0

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| JR.S11.T1 | AC6.0 | `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_git.py` (`git()` decodes UTF-8, the one seam), `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_end.py` (`_declared` drops the cp1252 strip), every other `text=True` subprocess call without an encoding under `dadaia_workspace/public/skills/*/scripts/` (the class sweep) | JR.S10.T1's boundary row; resolves `skill-git-output-decodes-with-the-locale` and reopens nothing; sweep `grep -rn 'text=True' dadaia_workspace/public/skills/*/scripts/*.py \| grep -v encoding` prints nothing |
| JR.S11.T2 | AC6.0 | `dadaia_workspace/features/specs/canon.py` (one reader of the template's default `tests:` line, used by `declare_tests_line` and named for the CLI), `dadaia_workspace/cli/commands/specs.py` (the echo prints that default and never reads the law), `dadaia_workspace/public/templates/repo-AGENTS.md` (the default adds `**/*.Tests/** **/androidTest/**`) | JR.S10.T1's canon and specs rows; resolves `declared-echo-rereads-the-law`, `default-tests-globs-under-match-dotnet-android` |
| JR.S11.T3 | — | `dadaia_workspace/public/entities/behavior-map.json` (re-recorded after T1 and T2 land, in its own task tree) | `tests/infrastructure/test_entity_doctor.py` |

## Stage JR.S12 — the eval and closure

- Contract: exit tests `release.py check` in CLOSURE, `bugs.py status` `0 open`, eval.yml green on `feature/0.5.0` (AC11.6); envelope `specs/memory/QUALITY.md`, `specs/releases/0.5.0/_RELEASE.json`, `specs/backlog/**`, this rc's job files; ACs AC10.2, AC10.4, AC11.6

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| JR.S12.T1 | AC11.6, AC10.4 | `specs/memory/QUALITY.md` (the eval verdict line of the rerun; the `## Bugs` review bullets restated as standing facts — causes and verdicts, no relative time, no pending line), `docs/bug-ledger-lessons.md` (its QUALITY-derived sections re-derived, hashes re-recorded), `specs/releases/0.5.0/_RELEASE.json` (the rerun's note, appended as JR.S3.T2's notes were: `release.py` has no note verb), `specs/backlog/**` (`agent-behavior-evals` exits `delivered --release 0.5.0`; the multi-platform entry's stale "no id yet" sentence stays — `backlog.py` has no verb that edits an entry, the known one-writer gap) | `release.py check`, `backlog.py check`, `tests/contract/test_docs_derived_from_memory.py` |
| JR.S12.T3 | AC4.5, AC11.6 | `specs/memory/QUALITY.md` (the `## Bugs` bullets restate no number the generated block owns; the rc-10 records include 3 deferred; the direction counts read from `bugs.py stats` or leave; the eval bullet names both earlier runs, 37629005413 and 37652269562, before the green rerun), `specs/releases/0.5.0/_RELEASE.json` (a note correcting "the first run" in the rerun note: the BLOCK run was the second), `docs/bug-ledger-lessons.md` (the four QUALITY-derived hashes re-recorded) | review REJECTED 726c61aa9 HIGH and LOW; `tests/contract/test_docs_derived_from_memory.py`, `release.py check`, memory_lint |
| JR.S12.T2 | — | this file | close task, last: behavior map and derived docs; `test-audit: no test touched`, `mutation: skipped — no Python source`; `done` |

- done: Reconciliation — JR.S2 memory and ledgers; JR.S3 the bug balance, the lessons, the release readouts; the eval's BLOCK registered and fixed inside the job (`onboarding-writes-no-tests-line`: RED JR.S4.T1 and JR.S6.T1, fix JR.S5.T1 reverted for a test born in GREEN, redone JR.S7.T1); the stage-gate repair JR.S4.T2; the freeze's no-stage-1 refusal deleted (JR.S7.T2, REBUILD); QUALITY without release ids (JR.S7.T3); the review's findings JR.S8–JR.S11 (the literal adversary row, the agreement row, `git()` decoding UTF-8 at every skill-script seam, one reader of the default `tests:` line); the eval rerun green, t2 3/3 against 3/3 (JR.S12.T1); CLOSURE at 7326a198e with the memory entry (JR.S12.T2). Reviews: REJECTED 1dedca22b, APPROVED 142cf04c7, REJECTED 90ca2c78c, APPROVED 7326a198e. Landed on `feature/0.5.0` by the operator's fast-forward to 7326a198e: `worktree.py merge` refused two commits the main thread made on the job branch directly (dd5e6e03a, 142cf04c7). Bugs: 0 open; deferred `freeze-has-no-lane-for-an-approved-amendment` (an operator ruling on ADR 0209's amendment lane), `git-errors-replace-has-no-row`, `subprocess-text-encoding-has-no-guard`. Bug surface: the freeze shrank (one refusal and its decider gone); onboarding grew by the writer ADR 0216 names; the skill scripts decode at one seam each.
