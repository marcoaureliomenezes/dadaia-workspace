# Closure: Release - v0.2.9

> **Status:** Aprovado
> **Release ID:** v0.2.9
> **Owner:** product-engineer
> **Closed:** 2026-07-19

## Summary

v0.2.9 converges the consumer × dadaia-workspace loop to **zero failures on a full
real-use round** — the declared gate for package 0.4.1. The work started from a
directed discovery with the consumer agent itself (task tg-1784485392): its full
day-to-day inventory became the validation contract, and every finding was fixed
by root-cause CLASS, never by instance patch.

The four shipped classes: (1) the `backlog_author` deliverable gate now proves a
disk DELTA (NEW or hash-CHANGED item), not zone existence; (2) placeholder atoms
from old scaffolds are flagged fixable (`MEM-PLACEHOLDER-1`) and repaired by both
`specs doctor --fix` and `specs upgrade` (current-version trees included); (3)
rejection/retry digests are bounded so retries can no longer exceed the Codex
context window; (4) bounded revisions are OBSERVABLE — the run record carries
`revision_note` on both retry mechanisms (fragment-gate revision and pipeline
review retry), so a watcher can never mistake a healthy retry for a stall. The
consumer recipe gained the **Real-use matrix (R-01…R-08)**: the live Codex chain
with per-link artifact proofs is now required for every release, and deterministic
certification alone never approves one.

Consumer verdict for the 0.4.1 candidate: **CERTIFIED_100 — 35 PASS / 0 FAIL /
0 EXCEPTION** (`<consumer-root>/.val/matrix-verdict/consumer-certification-0.4.1.json`).

## Scope and task completion

| Task ID | Planned scope | Final state | Evidence |
|---|---|---|---|
| T1 | backlog_author acceptance requires an authored delta | Implemented | `tests/unit/features/lifecycle/test_backlog_materialization.py` (4 tests); consumer R1: live backlog materialized |
| T2 | scaffold placeholder repair (init/upgrade/--fix) | Implemented | `tests/unit/features/specs/test_scaffold_placeholder_repair.py` (7 tests); consumer R1: both real contexts reach specs doctor 0/0 |
| T3 | release-definition honest terminal state | Dispositioned: old-version record; class fixed in 0.3.x line | consumer diagnostics task tg-1784488200; R-05 re-run passes |
| T4 | bounded rejection-correction digest | Implemented | `tests/unit/features/lifecycle/test_rejection_digest_budget.py` (4 tests) |
| T5 | release-id canon, skills/CLI audit, root-exceptions guidance | Verified already covered on main | `_require_canonical_release_id` at intake; doctor error text; skills audit clean |
| T6 | Recipe v2: real-use matrix | Implemented | `public/data/CONSUMER_VALIDATION_RECIPE.md` R-01…R-08 shipped in the wheel |
| T7 | Consumer convergence rounds until zero | **ACHIEVED** | 3 rounds → CERTIFIED_100 (35/35) |
| T8 | Docs, memory, 0.4.1 gates, deploy | Implemented (this file + gates below) | — |

## Validations

| Description | Command / Artifact | Evidence |
|---|---|---|
| Full pytest suite | `pytest -p no:cacheprovider tests/unit tests/contract tests/integration tests/e2e` | `2811 passed, 10 skipped` |
| ruff + mypy | `ruff format/check dadaia_workspace/ tests/`; `mypy --strict` changed files | clean |
| Consumer convergence round 1 | candidate 0.4.1 | 10 PASS / 1 FAIL (revision observability bug) |
| Consumer convergence round 2 | candidate 0.4.1 | 7 PASS / 1 FAIL (pipeline retry observability + plan-author flake) |
| Consumer convergence round 3 | candidate 0.4.1 | **CERTIFIED_100 — 35 PASS / 0 FAIL / 0 EXCEPTION** |

## Bugs registered and dispositioned (consumer loop)

| Bug | Disposition |
|---|---|
| `codex-backlog-author-no-materialization-regression-040` | resolved (T1 delta gate) |
| `scaffold-repair-cannot-remediate-invalid-placeholder-atom` | resolved (T2 repair) |
| `lifecycle-release-define-stalls-before-worker` | deferred→confirmed: old-layout record (2026-07-12); class fixed in 0.3.x; consumer R-05 re-run passes |
| `impl-reviews-retry-prompt-exceeds-codex-window` | resolved (T4 bounded digests) |
| `release-definition-retry-stalls-with-empty-workflow-steps-041` | resolved (`revision_note` on the run record) |
| `implementation-reviews-hangs-after-worker-output-041` | resolved (pipeline retry `revision_note`, sibling surface) |
| `live-release-definition-plan-author-blocks-041` | **refuted** — model emitted an EMPTY mandatory dependency table twice; the gate blocked honestly with reason + resume path; sibling run completed after one healthy revision |
| `certification-misses-live-codex-backlog-regression-040` | resolved (T6 Real-use matrix) |

## Memory updates

- `specs/memory/product/platform/consumer-agent-support.md` — NEW atom declaring
  consumer a supported consumer environment, with the support contract and the
  convergence posture.
- `specs/memory/product/catalog.json` + `index.md` — regenerated (29 features).
- `README.md` — Consumer agent declared a supported consumer alongside the harness
  table.

## Drifts

### Plan-author block was a model flake, not a product defect

The round-2 `live-release-definition-plan-author-blocks-041` finding was
investigated to the artifact level: the live model wrote an EMPTY
`Validation Dependency Table` twice (the fragment marks it MANDATORY with the
exact WS-row shape). The Python gate blocked honestly with a precise reason and a
resume path — the intended behavior. Refuted with evidence and closed.

## Backlog returns

Candidate future work (not commitments): the consumer runtime's own F-statement
fixtures (its local runner's F-08/F-10/F-11/F-13/F-26 predicates) belong to
sample-consumer maintenance, not this repo.

## Archive decision

Archive `specs/releases/v0.2.9/` to `specs/_archive/releases/` after the operator
confirms the PyPI deploy of 0.4.1.
