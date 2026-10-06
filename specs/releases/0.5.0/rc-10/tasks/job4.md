# TASKS — 0.5.0 rc-10, Job 4 — QUALITY.md's bug balance and the convergence readouts

**Status:** Draft

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

## Stage J4.S3 — memory and close

- Contract: exit tests `test_docs_derived_from_memory.py`, `test_behavior_map.py`, `release.py check`, `dadaia doctor` clean; envelope `specs/memory/QUALITY.md`, `specs/memory/product/**/bug-ledger.md`, `specs/memory/product/catalog.json`, `docs/bug-ledger-lessons.md`, `CONTEXT.md`, this file; ACs AC4.1, AC4.5

| task | AC | `W:` | owner tests / RED |
|---|---|---|---|
| J4.S3.T1 | AC4.1, AC4.5 | `specs/memory/QUALITY.md` (`## Bugs`: the generated block, then the written review with the latest evals verdict line), `specs/memory/product/**/bug-ledger.md`, `specs/memory/product/catalog.json`, `docs/bug-ledger-lessons.md` (re-derived from `## Bugs`, one merge, 0192) | `test_docs_derived_from_memory.py` |
| J4.S3.T2 | AC4.5 | `CONTEXT.md` (the SPEC's Terms) | no test |
| J4.S3.T3 | — | this file | close task, last: behavior map; `test-audit:`, `mutation:`; `done` |
