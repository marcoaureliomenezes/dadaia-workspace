# TASKS — 0.5.0 rc-9, Job 2 — the bug window, executed

**Status:** Approved — operator ruling 2026-10-05 (AskUserQuestion): "Aprovo (Recommended)", on 700217aa3 (recorded in baf8fe6aa).

Paths are relative to `dadaia_workspace/` unless they start with `scripts/`, `tests/`, `specs/`, `.github/`, `pyproject.toml` or `CONTEXT.md`; `gitflow/` is `public/skills/dd-gitflow-default/`, `relimpl/` is `public/skills/dd-release-implementation/`, `bugres/` is `public/skills/dd-bug-resolution/`.

## Stage J2.S1 — RED (AC2.1–AC2.7)

- Contract: exit tests every acceptance test of the ACs served RED as strict xfail; test files only (R10); envelope `tests/integration/test_ci_script.py`, `tests/unit/hooks/test_ctx_inject.py`, `tests/integration/cli/test_registry_version_grammar.py`, `tests/integration/cli/test_push_gate_gitflow_resolution.py`, `tests/integration/test_cli_init.py`, `tests/unit/skills/test_release_implementation_release_script.py`, `tests/unit/skills/test_bug_resolution_bugs_script.py`; ACs AC2.1–AC2.7
- ACs served: AC2.1–AC2.7.
- Envelope: `tests/integration/test_ci_script.py`, `tests/unit/hooks/test_ctx_inject.py`, `tests/integration/cli/test_registry_version_grammar.py`, `tests/integration/cli/test_push_gate_gitflow_resolution.py`, `tests/integration/test_cli_init.py`, `tests/unit/skills/test_release_implementation_release_script.py`, `tests/unit/skills/test_bug_resolution_bugs_script.py`.
- Exit tests: every acceptance test of the ACs served RED as strict xfail; test files only (R10).

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J2.S1.T1 | AC2.1 | `tests/integration/test_ci_script.py` | RED: the ACs' acceptance tests |
| J2.S1.T2 | AC2.2 | `tests/unit/hooks/test_ctx_inject.py` | RED: the ACs' acceptance tests |
| J2.S1.T3 | AC2.3 | `tests/integration/cli/test_registry_version_grammar.py` | RED: the ACs' acceptance tests |
| J2.S1.T4 | AC2.4 | `tests/integration/cli/test_push_gate_gitflow_resolution.py` | RED: the ACs' acceptance tests |
| J2.S1.T5 | AC2.5 | `tests/integration/test_cli_init.py` | RED: the ACs' acceptance tests |
| J2.S1.T6 | AC2.6 | `tests/unit/skills/test_release_implementation_release_script.py` | RED: the ACs' acceptance tests |
| J2.S1.T7 | AC2.7 | `tests/unit/skills/test_bug_resolution_bugs_script.py` | RED: the ACs' acceptance tests |

## Stage J2.S2 — carried-in code (AC2.8: 210 and 212 as-is)

- Contract: exit tests the stage's owner tests green at the task gates; unit + integration green at the stage gate; no xfail left for the ACs served (R5); envelope `bugres/scripts/`, `scripts/ci.py`, `bug-ledger.md`, `BUGS.jsonl`; ACs AC2.8: 210 and 212 as-is
- ACs served: AC2.8: 210 and 212 as-is.
- Envelope: `bugres/scripts/`, `scripts/ci.py`, `bug-ledger.md`, `BUGS.jsonl`.
- Exit tests: the stage's owner tests green at the task gates; unit + integration green at the stage gate; no xfail left for the ACs served (R5).

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J2.S2.T1 | AC2.8 | the five shas' own paths (`bugres/scripts/`, `scripts/ci.py`, `bug-ledger.md`, its derived docs, `BUGS.jsonl`) | no test |

## Stage J2.S3 — fixes (AC2.1–AC2.7; AC3.1's last `base_env` callers)

- Contract: exit tests the stage's owner tests green at the task gates; unit + integration green at the stage gate; no xfail left for the ACs served (R5); envelope `scripts/ci.py`, `tests/README.md`, `tests/AGENTS.md`, `hooks/ctx_inject.py`, `hooks/sdd_post_gate.py`, `pyproject.toml`, `core/context_registry.py`, `tests/integration/cli/test_registry_version_grammar.py`, `cli/commands/ci.py`, `features/reconcile/service.py`, `cli/commands/init.py`, `relimpl/scripts/release.py`, `bugres/scripts/_ledger.py`, `tests/integration/test_worktree_lifecycle.py`, `tests/fixtures/harness_env.py`; ACs AC2.1–AC2.7; AC3.1's last `base_env` callers
- ACs served: AC2.1–AC2.7; AC3.1's last `base_env` callers.
- Envelope: `scripts/ci.py`, `tests/README.md`, `tests/AGENTS.md`, `hooks/ctx_inject.py`, `hooks/sdd_post_gate.py`, `pyproject.toml`, `core/context_registry.py`, `tests/integration/cli/test_registry_version_grammar.py`, `cli/commands/ci.py`, `features/reconcile/service.py`, `cli/commands/init.py`, `relimpl/scripts/release.py`, `bugres/scripts/_ledger.py`, `tests/integration/test_worktree_lifecycle.py`, `tests/fixtures/harness_env.py`.
- Exit tests: the stage's owner tests green at the task gates; unit + integration green at the stage gate; no xfail left for the ACs served (R5).

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J2.S3.T1 | AC2.1 | `scripts/ci.py`, `tests/README.md`, `tests/AGENTS.md` | `test_ci_script.py` |
| J2.S3.T2 | AC2.2 | `hooks/ctx_inject.py`, `hooks/sdd_post_gate.py`, `pyproject.toml` | `test_ctx_inject.py` |
| J2.S3.T3 | AC2.3, AC3.1 (`base_env` caller) | `core/context_registry.py`, `tests/integration/cli/test_registry_version_grammar.py` | `test_registry_version_grammar.py` |
| J2.S3.T4 | AC2.4 | `cli/commands/ci.py` | `test_push_gate_gitflow_resolution.py` |
| J2.S3.T5 | AC2.5 | `features/reconcile/service.py`, `cli/commands/init.py` | `test_cli_init.py` |
| J2.S3.T6 | AC2.6 | `relimpl/scripts/release.py` | `test_release_implementation_release_script.py` |
| J2.S3.T7 | AC2.7 | `bugres/scripts/_ledger.py` | `test_bug_resolution_bugs_script.py` |
| J2.S3.T8 | AC3.1 (contract) | `tests/integration/test_worktree_lifecycle.py`, `tests/fixtures/harness_env.py` (`base_env` deleted) | `test_worktree_lifecycle.py` |

## Stage J2.S4 — ledger and ADR proposals (AC2.9–AC2.11)

- Contract: exit tests `bugs.py check`, `backlog.py check`, `release.py check` and `dadaia doctor` (ADR) clean at the stage gate; no test run (ledger, ADR and memory only); envelope `specs/bugs/BUGS.jsonl`, `specs/bugs/_archive/`, `specs/ADRs/decisions.jsonl`; ACs AC2.9–AC2.11
- ACs served: AC2.9–AC2.11.
- Envelope: `specs/bugs/BUGS.jsonl`, `specs/bugs/_archive/`, `specs/ADRs/decisions.jsonl`.
- Exit tests: `bugs.py check`, `backlog.py check`, `release.py check` and `dadaia doctor` (ADR) clean at the stage gate; no test run (ledger, ADR and memory only).

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J2.S4.T1 | AC2.9–AC2.11 | `specs/bugs/BUGS.jsonl`, `specs/bugs/_archive/`, `specs/ADRs/decisions.jsonl` (`proposed` only) | no test |

## Stage J2.S5 — the 211 REBUILD and the archive (AC2.8's 211, AC2.11); opens only after the operator accepts S4's ADRs, since `bugs.py archive --adr` needs an accepted one

- Contract: exit tests `bugs.py check`, `backlog.py check`, `release.py check` and `dadaia doctor` (ADR) clean at the stage gate; no test run (ledger, ADR and memory only); envelope `specs/bugs/BUGS.jsonl`, `specs/bugs/_archive/`; ACs AC2.8's 211, AC2.11
- ACs served: AC2.8's 211, AC2.11.
- Envelope: `specs/bugs/BUGS.jsonl`, `specs/bugs/_archive/`.
- Exit tests: `bugs.py check`, `backlog.py check`, `release.py check` and `dadaia doctor` (ADR) clean at the stage gate; no test run (ledger, ADR and memory only).

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J2.S5.T1 | AC2.8, AC2.11 | `specs/bugs/BUGS.jsonl`, `specs/bugs/_archive/` | no test; `V33_ORPHANS ≤ 31` after the stage |
| J2.S5.T2 | — | generated only: the behavior-map hashes and derived docs | close task: test-audit + mutation-diff over the job diff (Q23), regenerate the behavior map and derived docs (R6), write `done` (Q9) |
- The close task runs last, after every other task of its stage has fast-forwarded onto the job branch; its mutation-diff and test-audit run even in a stage whose gate is validators only (Q23).
