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
| JR.S7.T2 | AC6.1, AC6.2 | `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_freeze.py` (REBUILD of the RED anchor: a RED stage is a stage group whose commits touch tests only, derived from the commits, wherever it sits; the "no commit names its RED stage" refusal leaves), `dadaia_workspace/public/skills/dd-gitflow-default/scripts/_worktree_end.py` (`_declared` reads a line after a UTF-8 BOM) | JR.S6.T2's rows and JR.S6.T1's `_declared` row; resolves `freeze-cannot-see-a-red-amendment-stage`; commit `refactor(bugs): … — REBUILD …` |
| JR.S7.T3 | AC4.5 | `specs/memory/QUALITY.md` (`## Bugs`'s written review states its causes, verdicts and lessons with no release or candidate id) | `dadaia doctor` clean of MEM-NARRATIVE-1; resolves `quality-bugs-review-names-release-ids` |
| JR.S7.T4 | — | `dadaia_workspace/public/entities/behavior-map.json` (re-recorded after T1 and T2 land) | `tests/infrastructure/test_entity_doctor.py` |

## Stage JR.S8 — the eval and closure

- Contract: exit tests `release.py check` in CLOSURE, `bugs.py status` `0 open`, eval.yml green on `feature/0.5.0` (AC11.6); envelope `specs/memory/QUALITY.md`, `specs/releases/0.5.0/_RELEASE.json`, `specs/backlog/**`, this rc's job files; ACs AC10.2, AC10.4, AC11.6

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| JR.S8.T1 | AC11.6, AC10.4 | `specs/memory/QUALITY.md` (the eval verdict line of the rerun), `specs/releases/0.5.0/_RELEASE.json` (the rerun's note), `specs/backlog/**` (`agent-behavior-evals` exits `delivered --release 0.5.0`; ADR 0220 cited where the multi-platform entry says its ADR has no id) | `release.py check`, `backlog.py check` |
| JR.S8.T2 | — | this file | close task, last: behavior map and derived docs; `test-audit: no test touched`, `mutation: skipped — no Python source`; `done` |
