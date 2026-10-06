# TASKS — 0.5.0 rc-10, Job 4 — QUALITY.md's bug balance and the convergence readouts

**Status:** Approved
**Approval:** by operator delegation 2026-10-06 ("Delego: APPROVED do revisor basta (Recommended)", handoff 2026-10-06T044815Z-main-thread-overnight-delegation); dd-code-reviewer APPROVED d1f1b01b1.

Paths are relative to the repo root; aliases as in `PLAN.md` (`f/`, `pub/`, `S/`, `bugres/`, `relimpl/`, `GF/`, `evals:`). Gates: task — `verify-task:` on the touched files plus `Owner-tests:`; stage — `verify-stage:`; job — CI matrix + one review + `verify:`. Every stage before Job 6 merges runs under today's law (SPEC.md Job 6): stage 1 RED as strict xfail.

- Edge: Job 1 (`bugs.py`, the bug-script tests). AC4.4's LINT-1 half holds today (`f/specs/memory_lint.py:90`, PLAN KEEP).

## Stage J4.S1 — RED

- Contract: exit tests every AC4.1–AC4.4 row RED as strict xfail; envelope `tests/unit/skills/test_bug_resolution_balance.py`, `tests/contract/test_release_script.py`; ACs AC4.1–AC4.4

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J4.S1.T1 | AC4.1–AC4.3 | `tests/unit/skills/test_bug_resolution_balance.py` | RED: a literal ledger renders a literal block, a rerun byte-equal; dev-tooling surfaces print apart; `unknown` out of recurrences; t=[1,2,3], T=10 → `u = -1.80`, "no trend"; release-`unknown` and no-`found_in` records counted apart; an rc-`unknown` record of a known release counts; literal defective-fix rates per rc |
| J4.S1.T2 | AC4.4 | `tests/contract/test_release_script.py` | RED: a stale block refuses `release.py check` in CLOSURE with one fix line naming the regenerating command, passes in IMPLEMENTATION |

## Stage J4.S2 — the generator and the closure check

- Contract: exit tests J4.S1's rows green, unit + integration green; envelope `bugres/scripts/_bugs_balance.py`, `bugres/scripts/bugs.py`, `.gitattributes`, `relimpl/scripts/_release_tree.py`; ACs AC4.1–AC4.4

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J4.S2.T1 | AC4.1–AC4.3 | `bugres/scripts/_bugs_balance.py` (pure: records → block text; Laplace u; defective-fix rate), `bugres/scripts/bugs.py` (verb `balance`, `--write`), `.gitattributes` (`dadaia-dev-tooling` on the dev-tooling surfaces) | `test_bug_resolution_balance.py` |
| J4.S2.T2 | AC4.4 | `relimpl/scripts/_release_tree.py` (CLOSURE only: the block equals its regeneration, else one refusal + fix line) | `test_release_script.py` |

## Stage J4.S3 — the law and close

- Contract: exit tests `test_specs_version.py`, `test_tree5_shipped_history.py`, `test_behavior_map.py` green; envelope `pub/scaffold/memory/AGENTS.md`, the canon pin, this file; ACs AC4.1
- The first block, the written review, the atom move and `CONTEXT.md`'s Terms are Reconciliation's (AC4.5, `reconcile.md` JR.S3).

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J4.S3.T1 | AC4.1 | `pub/scaffold/memory/AGENTS.md` (`QUALITY.md` holds `## Bugs`: the generated block and the written review), `specs/memory/AGENTS.md` (by `specs upgrade`), `core/specs_version.py`, `pub/templates/shipped-hashes.json`, `tests/unit/core/test_specs_version.py` (pin re-record) | `test_specs_version.py` |
| J4.S3.T2 | — | this file | close task, last: behavior map; `test-audit:`, `mutation:`; `done` |

## Stage J4.S4 — the job gate's rework

- Contract: `ci.py job` green; envelope `bugres/scripts/_bugs_quality.py`, `relimpl/scripts/_release_tree.py`, `tests/contract/test_public_scripts_thin_wrapper.py`, the scripts' exec bits, `pub/entities/behavior-map.json`, this file; ACs AC4.4

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J4.S4.T1 | AC4.4 | `_bugs_quality.py` (`stale`: the one comparison, so `_release_tree.py` imports one module), `_release_tree.py`, `tests/contract/test_public_scripts_thin_wrapper.py` (the one cross-skill edge declared), the exec bit of `_bugs_balance.py` and `_bugs_quality.py`, `pub/entities/behavior-map.json` (scripts hashes), this file | no RED: the job gate's `test_public_scripts_thin_wrapper.py` was the red; `test_release_script.py` keeps AC4.4's case |

- done: Job 4 — every task landed on `wt/0.5.0-rc10/job4` through its task merge: J4.S1.T1 5577759a8 and J4.S1.T2 1bf985be4 (RED, strict xfail); J4.S2.T1 232a245dc (`_bugs_balance.py`, the `balance` verb, `.gitattributes`; W widened to `_bugs_fix.py`, whose `marked` is the one check-attr reader); J4.S2.T2 450006447 (the CLOSURE check; W widened to `bugs.py` and the new `_bugs_quality.py`, the one reader of ledgers and release spans that `release.py check` cannot get by importing `bugs.py`); J4.S2.T3 15cb09d43 (added: the hand-mutation survivors' rows); J4.S3.T1 3435bf23c (law, pin re-record); J4.S3.T2 (the first close); J4.S4.T1 (the job gate's red: exec bits, one cross-skill edge, `stale`), the close commit's behavior-map re-record.
