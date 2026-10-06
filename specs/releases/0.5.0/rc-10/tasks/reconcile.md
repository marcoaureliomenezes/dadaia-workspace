# TASKS — 0.5.0 rc-10, Reconciliation

**Status:** Draft

Paths are relative to the repo root; aliases as in `PLAN.md` (`f/`, `pub/`, `S/`, `bugres/`, `relimpl/`, `GF/`, `evals:`). Gates: task — `verify-task:` on the touched files plus `Owner-tests:`; stage — `verify-stage:`; job — CI matrix + one review + `verify:`. Bound by the freeze; it writes no test.

## Stage JR.S1 — RED (none: AC10.1–AC10.5 have no test)

- Contract: no acceptance test exists for AC10.1–AC10.5 (memory, ledgers, ADRs, release state); no task rows.

## Stage JR.S2 — memory and ledgers

- Contract: exit tests `bugs.py check`, `backlog.py check`, `release.py check`, `dadaia doctor` clean; `test_docs_derived_from_memory.py` green; envelope `specs/memory/**`, `docs/*.md`, `specs/audits/20260930-structural-convergence/FINDINGS.jsonl`, `specs/ADRs/decisions.jsonl`, `specs/backlog/**`; ACs AC10.1, AC10.3, AC10.4

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| JR.S2.T1 | AC10.1 | `specs/memory/**` (each atom with its derived sections), `docs/*.md`; every `tests/…py` path in `QUALITY.md`/`ARCHITECTURE.md` exists (Job 7 moved them); `RELEASE-TREE-MEMORY` gone | checks: the SPEC's greps |
| JR.S2.T2 | AC10.1 | `specs/audits/20260930-structural-convergence/FINDINGS.jsonl` (F098, F128 `resolved`, by `audit.py disposition`) | `audit.py` |
| JR.S2.T3 | AC10.3 | `specs/ADRs/decisions.jsonl` (`measured_by` repairs of 0208, 0209, 0210, the 0138 lane) | `dadaia doctor` |
| JR.S2.T4 | AC10.4 | `specs/backlog/**` (each Origin entry and the three rc-9 deliveries exit once, `delivered --release 0.5.0`; `agent-behavior-evals` after AC3.1 is logged) | `backlog.py check` |

## Stage JR.S3 — the balance and closure

- Contract: exit tests `release.py check` in CLOSURE (AC4.4's block current), `bugs.py status` `0 open`; envelope `specs/memory/**`, `docs/bug-ledger-lessons.md`, `CONTEXT.md`, `specs/releases/0.5.0/_RELEASE.json`, this rc's job files; ACs AC4.5, AC9.1, AC10.2, AC10.5
- AC10.5's rc-11 SPEC is drafted in its own `0.5.0-rc11/define` tree, an act outside this job.

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| JR.S3.T1 | AC4.5, AC10.2 | `specs/memory/QUALITY.md` (`## Bugs`: the first block by `bugs.py balance --write` after the sweep, then the written review with the latest evals verdict line), `specs/memory/product/**/bug-ledger.md` and `specs/memory/product/catalog.json` (the atom move), `docs/bug-ledger-lessons.md` (re-derived from `## Bugs`, one merge, 0192), `CONTEXT.md` (the SPEC's Terms) | `release.py check`, `test_docs_derived_from_memory.py` |
| JR.S3.T2 | AC10.2, AC10.5 | `specs/releases/0.5.0/_RELEASE.json` (readouts, AC8.1's readout, each job's merge entry and bug-surface delta; phase) | `release.py check` |
| JR.S3.T4 | — | this file, `specs/releases/0.5.0/rc-10/tasks/job2.md`, `specs/releases/0.5.0/rc-10/tasks/job3.md` (their `done` lines: evals trees cannot write them) | close task, last: behavior map and derived docs; `test-audit: no test touched`, `mutation: skipped — no Python source`; `done` |
