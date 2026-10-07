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
| JR.S4.T1 | AC6.0 | `tests/features/specs/test_canon__scaffold_repo_law.py` (new rows only: a present `AGENTS.md` with no `tests:` line gains the template's `tests:` line, appended, its own text kept byte for byte; a present `tests:` line, empty or not, is left alone; the shipped template's `tests:` line is non-empty), `tests/cli/` specs-init owner file if `specs init` needs its own row (a repo whose `AGENTS.md` lacks `tests:` leaves `specs init` declaring a non-empty `tests:` line) | RED: each new row fails by assertion at HEAD; no existing assert changes |

## Stage JR.S5 — onboarding declares the tests: line

- Contract: exit the JR.S4 rows green and `test_present_law_is_never_overwritten` unchanged and green; envelope `dadaia_workspace/features/specs/canon.py`, `dadaia_workspace/cli/commands/specs.py`, `dadaia_workspace/public/templates/repo-AGENTS.md`, `dadaia_workspace/public/entities/behavior-map.json`; ACs AC6.0, AC11.6

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| JR.S5.T1 | AC6.0 | `dadaia_workspace/public/templates/repo-AGENTS.md` (its `tests:` line carries the one default, language-neutral glob set — the only place the default lives), `dadaia_workspace/features/specs/canon.py` (one function, called by `specs init` beside `scaffold_repo_law`, appends the template's `tests:` line to a present `AGENTS.md` that has none; `scaffold_repo_law` keeps "never overwritten"), `dadaia_workspace/cli/commands/specs.py` (the call and its `[created]`/`[declared]` line), `dadaia_workspace/public/entities/behavior-map.json` (re-recorded) | JR.S4.T1's rows; bug `onboarding-writes-no-tests-line` resolved by this task; sweep `git grep -n '^tests:' -- dadaia_workspace` names one default |

## Stage JR.S6 — the eval and closure

- Contract: exit tests `release.py check` in CLOSURE, `bugs.py status` `0 open`, eval.yml green on `feature/0.5.0` (AC11.6); envelope `specs/memory/QUALITY.md`, `specs/releases/0.5.0/_RELEASE.json`, `specs/backlog/**`, this rc's job files; ACs AC10.2, AC10.4, AC11.6

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| JR.S6.T1 | AC11.6, AC10.4 | `specs/memory/QUALITY.md` (the eval verdict line of the rerun), `specs/releases/0.5.0/_RELEASE.json` (the rerun's note), `specs/backlog/**` (`agent-behavior-evals` exits `delivered --release 0.5.0`; ADR 0220 cited where the multi-platform entry says its ADR has no id) | `release.py check`, `backlog.py check` |
| JR.S6.T2 | — | this file | close task, last: behavior map and derived docs; `test-audit: no test touched`, `mutation: skipped — no Python source`; `done` |
