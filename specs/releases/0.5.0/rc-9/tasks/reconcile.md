# TASKS — 0.5.0 rc-9, Reconciliation

**Status:** Approved — operator ruling 2026-10-05 (AskUserQuestion): "Aprovo (Recommended)", on 700217aa3 (recorded in baf8fe6aa).

Paths are relative to `dadaia_workspace/` unless they start with `scripts/`, `tests/`, `specs/`, `.github/`, `pyproject.toml` or `CONTEXT.md`; `gitflow/` is `public/skills/dd-gitflow-default/`, `relimpl/` is `public/skills/dd-release-implementation/`, `bugres/` is `public/skills/dd-bug-resolution/`.

## Stage JR.S1 — RED (none: AC6.1–AC6.4 have no test)

- Contract: no acceptance test exists for AC6.1–AC6.4 (ledger, ADR and memory only); no task rows.

## Stage JR.S2 — (AC6.1–AC6.3)

- Contract: exit tests `bugs.py check`, `backlog.py check`, `release.py check` and `dadaia doctor` (ADR) clean at the stage gate; no test run (ledger, ADR and memory only); envelope `specs/memory/**`, `specs/memory/product/catalog.json`, `specs/audits/20260930-structural-convergence/FINDINGS.jsonl`, `specs/releases/0.5.0/_RELEASE.json`, `specs/ADRs/decisions.jsonl`; ACs AC6.1–AC6.3
- ACs served: AC6.1–AC6.3.
- Envelope: `specs/memory/**`, `specs/memory/product/catalog.json`, `specs/audits/20260930-structural-convergence/FINDINGS.jsonl`, `specs/releases/0.5.0/_RELEASE.json`, `specs/ADRs/decisions.jsonl`.
- Exit tests: `bugs.py check`, `backlog.py check`, `release.py check` and `dadaia doctor` (ADR) clean at the stage gate; no test run (ledger, ADR and memory only).

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| JR.S2.T1 | AC6.1 | `specs/memory/**`, its derived docs and `catalog.json`, in one merge (AC1.5) |  |
| JR.S2.T2 | AC6.1 (F131) | `specs/audits/20260930-structural-convergence/FINDINGS.jsonl` |  |
| JR.S2.T3 | AC6.2 | `specs/releases/0.5.0/_RELEASE.json` (`log`) |  |
| JR.S2.T4 | AC6.3 | `specs/ADRs/decisions.jsonl` (`measured_by` repairs; acceptance is the operator's) |  |

## Stage JR.S3 — bug law per ADR 0206 (corrective)

- Contract: the bugs, releases and worktree laws, the bug skills, RC-FLOW, CONTEXT.md and the memory state ADR 0206's law (no rc closes with an open bug; the bug batch; the next rc's `## Bug window review` judges the fixes), replacing 0201/0204's next-Job-1 clauses; the canon stamp re-recorded.
- ACs served: ADR 0206.
- Envelope: `specs/ADRs/decisions.jsonl`, `public/scaffold/bugs/AGENTS.md`, `specs/bugs/AGENTS.md`, `public/scaffold/releases/AGENTS.md`, `specs/releases/AGENTS.md`, `bugres/SKILL.md`, `relimpl/RC-FLOW.md`, `public/skills/dd-release-definition/SKILL.md`, `public/data/worktrees-AGENTS.md`, `CONTEXT.md`, `specs/memory/**`, `docs/*.md`, `core/specs_version.py`, `public/templates/shipped-hashes.json`, `tests/unit/core/test_specs_version.py`.
- Exit tests: `tests/unit/core/test_specs_version.py`, `tests/unit/features/specs/test_tree5_shipped_history.py`, `tests/contract/test_docs_derived_from_memory.py`, `tests/contract/test_law_states_what_the_code_does.py`, `tests/contract/test_behavior_map.py`, `tests/integration/test_doctor_fix_lines_clear_their_finding.py`; `bugs.py check`, `release.py check`, `dadaia doctor` clean.

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| JR.S3.T1 | ADR 0206 | `specs/ADRs/decisions.jsonl`, `public/scaffold/bugs/AGENTS.md`, `specs/bugs/AGENTS.md`, `public/scaffold/releases/AGENTS.md`, `specs/releases/AGENTS.md`, `bugres/SKILL.md`, `relimpl/RC-FLOW.md`, `public/skills/dd-release-definition/SKILL.md`, `public/data/worktrees-AGENTS.md`, `CONTEXT.md`, `specs/memory/**`, `docs/*.md`, `core/specs_version.py`, `public/templates/shipped-hashes.json`, `tests/unit/core/test_specs_version.py` | the stage's exit tests |

## Stage JR.S4 — (AC6.4)

- Contract: exit tests `bugs.py check`, `backlog.py check`, `release.py check` and `dadaia doctor` (ADR) clean at the stage gate; no test run (ledger, ADR and memory only); envelope `specs/releases/0.5.0/_RELEASE.json`, `specs/releases/0.5.0/rc-10/SPEC.md`; ACs AC6.4
- ACs served: AC6.4.
- Envelope: `specs/releases/0.5.0/_RELEASE.json`, `specs/releases/0.5.0/rc-10/SPEC.md`.
- Exit tests: `bugs.py check`, `backlog.py check`, `release.py check` and `dadaia doctor` (ADR) clean at the stage gate; no test run (ledger, ADR and memory only).

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| JR.S4.T1 | AC6.4 | `specs/releases/0.5.0/_RELEASE.json` (phase), `specs/releases/0.5.0/rc-10/SPEC.md` (Draft, in the `0.5.0-rc10/define` tree) |  |
| JR.S4.T2 | — | generated only: the behavior-map hashes and derived docs | close task: test-audit + mutation-diff over the job diff (Q23), regenerate the behavior map and derived docs (R6), write `done` (Q9) |
- The close task runs last, after every other task of its stage has fast-forwarded onto the job branch; its mutation-diff and test-audit run even in a stage whose gate is validators only (Q23).
