# TASKS — 0.5.0 rc-9, Job 2 — the bug window, executed

**Status:** Approved — operator ruling 2026-10-05 (AskUserQuestion): "Aprovo (Recommended)", on 700217aa3 (recorded in baf8fe6aa).

Paths are relative to `dadaia_workspace/` unless they start with `scripts/`, `tests/`, `specs/`, `.github/`, `pyproject.toml` or `CONTEXT.md`; `gitflow/` is `public/skills/dd-gitflow-default/`, `relimpl/` is `public/skills/dd-release-implementation/`, `bugres/` is `public/skills/dd-bug-resolution/`.

## Stage J2.S1 — RED (AC2.1–AC2.7)

- Contract: exit tests every acceptance test of the ACs served RED as strict xfail; test files only (R10); envelope `tests/integration/test_ci_script.py`, `tests/unit/hooks/test_ctx_inject.py`, `tests/integration/cli/test_registry_version_grammar.py`, `tests/integration/cli/test_push_gate_gitflow_resolution.py`, `tests/integration/test_cli_init.py`, `tests/unit/skills/test_release_implementation_release_script.py`, `tests/unit/skills/test_bug_resolution_bugs_script.py`; ACs AC2.1–AC2.7
- ACs served: AC2.1–AC2.7.
- Envelope: `tests/integration/test_ci_script.py`, `tests/unit/hooks/test_ctx_inject.py`, `tests/integration/cli/test_registry_version_grammar.py`, `tests/integration/cli/test_push_gate_gitflow_resolution.py`, `tests/integration/test_cli_init.py`, `tests/unit/skills/test_release_implementation_release_script.py`, `tests/unit/skills/test_bug_resolution_bugs_script.py`.
- Exit tests: every acceptance test of the ACs served RED as strict xfail; test files only (R10).

| task | AC | `W:` (as landed) | owner tests / RED | landed |
|---|---|---|---|---|
| J2.S1.T1 | AC2.1 | `tests/integration/test_ci_script.py` | RED: the AC's acceptance test (strict xfail) | af62c0785 |
| J2.S1.T2 | AC2.2 | `tests/unit/hooks/test_ctx_inject.py` | RED: the AC's acceptance test (strict xfail) | 7932a8d6d |
| J2.S1.T3 | AC2.3 | `tests/integration/cli/test_registry_version_grammar.py` | RED: the AC's acceptance test (strict xfail) | d8099f5c2 |
| J2.S1.T4 | AC2.4 | `tests/integration/cli/test_push_gate_gitflow_resolution.py` | RED: the AC's acceptance test (strict xfail) | 2b255cffa |
| J2.S1.T5 | AC2.5 | `tests/integration/test_cli_init.py` | RED: the AC's acceptance test (strict xfail) | 9b3061b78 |
| J2.S1.T6 | AC2.6 | `tests/unit/skills/test_release_implementation_release_script.py` | RED: the AC's acceptance test (strict xfail) | db725e048 |
| J2.S1.T7 | AC2.7 | `tests/unit/skills/test_bug_resolution_bugs_script.py` | RED: the AC's acceptance test (strict xfail) | 6a39ae24f |

## Stage J2.S2 — carried-in code (AC2.8: 210 and 212 as-is)

- Contract: exit tests the stage's owner tests green at the task gates; unit + integration green at the stage gate; no xfail left for the ACs served (R5); envelope `bugres/scripts/`, `scripts/ci.py`, `bug-ledger.md`, `BUGS.jsonl`; ACs AC2.8: 210 and 212 as-is
- ACs served: AC2.8: 210 and 212 as-is.
- Envelope: `bugres/scripts/`, `scripts/ci.py`, `bug-ledger.md`, `BUGS.jsonl`.
- Exit tests: the stage's owner tests green at the task gates; unit + integration green at the stage gate; no xfail left for the ACs served (R5).

| task | AC | `W:` (as landed) | owner tests / RED | landed |
|---|---|---|---|---|
| J2.S2.T1 | AC2.8 | the carried shas' own paths: `features/specs/{doctor,doctor_governance,rules}.py`, `public/schemas/bugs/bug-record-v1.schema.json`, `bugres/scripts/`, `bug-ledger.md`, `README.md`, `docs/*.md`, `BUGS.jsonl`; widened: `public/entities/behavior-map.json`, `specs/memory/product/catalog.json` | no test | f4f12be05, a8241476d, 0e3d2bc42, 006f23efb (210); 2e090b960 (212); ee6727047, e94cebc12 |

## Stage J2.S3 — fixes (AC2.1–AC2.7; AC3.1's last `base_env` callers)

- Contract: exit tests the stage's owner tests green at the task gates; unit + integration green at the stage gate; no xfail left for the ACs served (R5); envelope `scripts/ci.py`, `tests/README.md`, `tests/AGENTS.md`, `hooks/ctx_inject.py`, `hooks/sdd_post_gate.py`, `pyproject.toml`, `core/context_registry.py`, `tests/integration/cli/test_registry_version_grammar.py`, `cli/commands/ci.py`, `features/reconcile/service.py`, `cli/commands/init.py`, `relimpl/scripts/release.py`, `bugres/scripts/_ledger.py`, `tests/integration/test_worktree_lifecycle.py`, `tests/fixtures/harness_env.py`; ACs AC2.1–AC2.7; AC3.1's last `base_env` callers
- ACs served: AC2.1–AC2.7; AC3.1's last `base_env` callers.
- Envelope: `scripts/ci.py`, `tests/README.md`, `tests/AGENTS.md`, `hooks/ctx_inject.py`, `hooks/sdd_post_gate.py`, `pyproject.toml`, `core/context_registry.py`, `tests/integration/cli/test_registry_version_grammar.py`, `cli/commands/ci.py`, `features/reconcile/service.py`, `cli/commands/init.py`, `relimpl/scripts/release.py`, `bugres/scripts/_ledger.py`, `tests/integration/test_worktree_lifecycle.py`, `tests/fixtures/harness_env.py`.
- Exit tests: the stage's owner tests green at the task gates; unit + integration green at the stage gate; no xfail left for the ACs served (R5).

| task | AC | `W:` (as landed) | owner tests / RED | landed |
|---|---|---|---|---|
| J2.S3.T1 | AC2.1 | `scripts/ci.py`, `tests/README.md`, `tests/AGENTS.md`; widened: `tests/integration/test_ci_script.py` (xfail removed) | `test_ci_script.py` | a6fadcdde |
| J2.S3.T2 | AC2.2 | `pyproject.toml`; widened: `core/invocation.py` (the per-context registry read, ruled 2026-10-05), `tests/unit/hooks/test_ctx_inject.py` (xfail removed); `hooks/ctx_inject.py`, `hooks/sdd_post_gate.py` unchanged | `test_ctx_inject.py` | 2299ce56b |
| J2.S3.T3 | AC2.3, AC3.1 (`base_env` caller) | `core/context_registry.py`, `tests/integration/cli/test_registry_version_grammar.py`; widened: `infrastructure/json_context_store.py` (option (a), ruled 2026-10-05) | `test_registry_version_grammar.py` | 7c494c568, c0acfac91 |
| J2.S3.T4 | AC2.4 | `infrastructure/git_subprocess.py` (the gitflow reader; `cli/commands/ci.py` unchanged), `tests/integration/cli/test_push_gate_gitflow_resolution.py` | `test_push_gate_gitflow_resolution.py` | 84ed78453 |
| J2.S3.T5 | AC2.5 | `features/reconcile/service.py`, `tests/integration/test_cli_init.py`, `tests/unit/features/reconcile/test_reconcile_service.py`; `cli/commands/init.py` unchanged | `test_cli_init.py` | 00824a1ee |
| J2.S3.T6 | AC2.6 | `relimpl/scripts/release.py`, `tests/unit/skills/test_release_implementation_release_script.py`, `public/entities/behavior-map.json` | `test_release_implementation_release_script.py` | 9888c647b, 9b026aef0, a9108723f, 88930ebd6 |
| J2.S3.T7 | AC2.7 | `bugres/scripts/_ledger.py`; widened: `core/redaction.py`, `features/chokepoints/denylist_scan.py`, `infrastructure/git_objects.py`, `public/entities/behavior-map.json`, `tests/e2e/test_push_denylist_journey.py`, `tests/unit/skills/test_bug_resolution_bugs_script.py` | `test_bug_resolution_bugs_script.py` | 5029ae91d, 599af4890 |
| J2.S3.T8 | AC3.1 (contract) | `tests/integration/test_worktree_lifecycle.py`, `tests/fixtures/harness_env.py` (`base_env` deleted) | `test_worktree_lifecycle.py` | 5c3ab2b56 |
| J2.S3.T9 | AC2.4 (born at review) | `infrastructure/git_subprocess.py`, `tests/integration/cli/test_push_gate_gitflow_resolution.py` | `test_push_gate_gitflow_resolution.py` (RED rebuilt to ADR 0045's absolute fix line) | 91c0f2189, d55cf2399 |

## Stage J2.S4 — ledger and ADR proposals (AC2.9–AC2.11)

- Contract: exit tests `bugs.py check`, `backlog.py check`, `release.py check` and `dadaia doctor` (ADR) clean at the stage gate; no test run (ledger, ADR and memory only); envelope `specs/bugs/BUGS.jsonl`, `specs/bugs/_archive/`, `specs/ADRs/decisions.jsonl`; ACs AC2.9–AC2.11
- ACs served: AC2.9–AC2.11.
- Envelope: `specs/bugs/BUGS.jsonl`, `specs/bugs/_archive/`, `specs/ADRs/decisions.jsonl`.
- Exit tests: `bugs.py check`, `backlog.py check`, `release.py check` and `dadaia doctor` (ADR) clean at the stage gate; no test run (ledger, ADR and memory only).

| task | AC | `W:` (as landed) | owner tests / RED | landed |
|---|---|---|---|---|
| J2.S4.T1 | AC2.9–AC2.11 | `specs/bugs/BUGS.jsonl`, `specs/ADRs/decisions.jsonl` (`proposed` only) | no test | 5d721ba6e (report); 854d7daed, a7fb49ddc, cdf589bde, 338e4fa84, de3eed1d1, 62065c166, fb336054b, a11702eb2, 69d2f2197, a9e346216, bc81b28bc, 468adebe8 (sha rows, retro); 627cdaf35, d33bf3dd9, e30a49825, e86fcb601, 5cbac9b66 (0195–0199 proposed) |
| J2.S4.T2 | AC2.9 (AC rows) | `specs/bugs/BUGS.jsonl` | no test | 8e1d683a4, ff841294e, c60729504, e244ed44c, 12c0693dc, e85dd232c, 7022d6a31, f50702dc3, 532a52e69, d7ced2de5, 1c719532a, 3513b7ade, db386777e, 23d7fe5a4, 85b692626 |

## Stage J2.S5 — the 211 REBUILD and the archive (AC2.8's 211, AC2.11); opens only after the operator accepts S4's ADRs, since `bugs.py archive --adr` needs an accepted one

- Contract: exit tests `bugs.py check`, `backlog.py check`, `release.py check` and `dadaia doctor` (ADR) clean at the stage gate; no test run (ledger, ADR and memory only); envelope `specs/bugs/BUGS.jsonl`, `specs/bugs/_archive/`; ACs AC2.8's 211, AC2.11
- ACs served: AC2.8's 211, AC2.11.
- Envelope: `specs/bugs/BUGS.jsonl`, `specs/bugs/_archive/`.
- Exit tests: `bugs.py check`, `backlog.py check`, `release.py check` and `dadaia doctor` (ADR) clean at the stage gate; no test run (ledger, ADR and memory only).

| task | AC | `W:` (as landed) | owner tests / RED | landed |
|---|---|---|---|---|
| J2.S5.T1 | AC2.8's 211, AC2.11 | `specs/bugs/BUGS.jsonl`, `specs/bugs/_archive/` | no test; `V33_ORPHANS` 31 ≤ 31 | cbc4c5b31 (restore); 3d13c8a82, ba758c013, 6d704595b, 7ec757b0b, 54a3facf3 (0195–0199), df07bf12b (0016) |
| J2.S5.T2 | AC2.10 | none: the accepted classification needs no ledger write | no test | — (ruled, no write) |
| J2.S5.T3 | — | `public/entities/behavior-map.json` | `test_behavior_map.py` | — (dropped, see below) |
- The close task runs last, after every other task of its stage has fast-forwarded onto the job branch; its mutation-diff and test-audit run even in a stage whose gate is validators only (Q23).
- The first close (the resolves, `done` and close commits after S5.T3) was dropped by the review reset; S5.T4 left no commit; the second close (J2.S6.T6) was dropped with the next rebase; the close runs as J2.S6.T8.
- ae19c4b3e (J2.S5.T3) dropped by the job-merge stray check (a commit made straight onto the job branch); its hashes were already re-recorded later (J2.S6.T1, J2.S6.T5, J2.S6.T7).

## Stage J2.S6 — review rework (the Job 2 review, REJECTED)

- Contract: exit tests the owner tests below at the task gates; unit + integration at the stage gate (green at 846d5fc94); envelope the S6 `W:` union; ACs AC2.1, AC2.3, AC2.4, AC2.6, AC2.7 and the close.

| task | finding | `W:` (as landed) | owner tests / RED | landed |
|---|---|---|---|---|
| J2.S6.T1 | F2, F10 (AC2.7) | `bugres/scripts/_ledger.py`, `bugres/scripts/_bugs_store.py`, `public/skills/dd-backlog-definition/scripts/_backlog_store.py`, `core/redaction.py`, `public/entities/behavior-map.json`, `tests/unit/skills/test_bug_resolution_bugs_script.py`, `tests/unit/features/chokepoints/test_push_denylist_scan.py` | RED: the failed rev-list row | 7e75c490d, 6ebe02029, dc4d2f5a5, 9b41d5d18 |
| J2.S6.T2 | F3, LOW (AC2.3) | `infrastructure/json_context_store.py`, `core/context_registry.py`, `tests/unit/test_json_context_store.py` | RED: `test_a_row_missing_name_is_unreadable_at_every_method` | 30b32e623, b19f9541c |
| J2.S6.T3 | F4 (AC2.4) | `infrastructure/git_subprocess.py`, `tests/integration/cli/test_push_gate_gitflow_resolution.py` | the AC2.4 assert REBUILT | 5b0e3b5f8, 1c5494f10 |
| J2.S6.T4 | F5, F6 (AC2.1; ADR 0200 item 1) | `scripts/ci.py`, `scripts/covdata.py`, `tests/README.md`, `tests/AGENTS.md`, `tests/integration/test_ci_script.py` | `test_ci_script.py` (the literal doc line, the temp dir removed) | 67d8ed1e5 |
| J2.S6.T5 | F7, F8, F9 (AC2.6) | `core/invocation.py`, `features/reconcile/service.py`, `relimpl/scripts/release.py`, `public/entities/behavior-map.json`, `tests/unit/core/test_invocation.py`, `tests/unit/skills/test_release_implementation_release_script.py` | RED: `test_the_first_memory_run_at_the_definition_sha_records_its_entry` | 9dcc36e1b, ac4b18094, 5f7146e1d, f74d123de, 846d5fc94 |
| J2.S6.T6 | — (close, dropped) | `tests/unit/test_json_context_store.py` (pins the S6.T2 row-name survivors) | `test_a_refused_row_is_named_by_its_name` | 3cb6639e3 (its resolves, `done` and close dropped with the rebase) |
| J2.S6.T7 | H1, H2, M1 (the close review) | `tests/contract/test_every_block_carries_a_fix.py`, `tests/unit/skills/test_bug_resolution_bugs_script.py`, `public/skills/dd-backlog-definition/scripts/_backlog_store.py`, `public/skills/dd-backlog-definition/scripts/_backlog_check.py`, `tests/unit/skills/test_backlog_definition_backlog_script.py`, `public/entities/behavior-map.json` | RED (M1): `test_the_backlog_seam_amnesties_a_term_origin_already_holds` | c494158a5, bc2991569, 398f0bc06, 25298e7e3, 7c8a0e97d, 4db3cc2cf, 33d0d7054 |
| J2.S6.T8 | — (close) | `specs/bugs/BUGS.jsonl` (the 7 AC2.1–AC2.7 records), this file | test-audit + mutation evidence over the job | the 7 resolves, this commit, the close commit |

## Operator rulings (2026-10-05, AskUserQuestion)

- ADRs 0195–0199 accepted ("Aceito as cinco (Recommended)", 9ff0d81b6); ADR 0200 accepted (1b908fe44).
- AC2.8's 211: the two caused_by cycles restored as `none` ("Restaura com os 4 em none (Recommended)"); the REBUILD verdict's "caused_by intact" withdrawn for those 4.
- AC2.10: the classification accepted ("Aceito as regras e a tabela (Recommended)"), at agent error 3, release-born 46, dev-tooling 27, doubtful 0, product 148; no ledger write.
- Co-writes, each in sequence and never in one stage: `core/invocation.py` (J2.S3.T2, J2.S6.T5); `core/context_registry.py` and `infrastructure/json_context_store.py` (J2.S3.T3, J2.S6.T2); `infrastructure/git_subprocess.py` (J2.S3.T4, J2.S3.T9, J2.S6.T3); `scripts/ci.py` and the two test docs (J2.S3.T1, J2.S6.T4); `relimpl/scripts/release.py` (J2.S3.T6, J2.S6.T5); `bugres/scripts/_ledger.py` (J2.S3.T7, J2.S6.T1); `tests/unit/skills/test_bug_resolution_bugs_script.py` (J2.S3.T7, J2.S6.T1, J2.S6.T7); `_backlog_store.py` (J2.S6.T1, J2.S6.T7).

- Done: Job 2 closed by J2.S6.T8 (2026-10-05).
