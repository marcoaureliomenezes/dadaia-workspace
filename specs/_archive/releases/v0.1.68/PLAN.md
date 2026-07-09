# PLAN — Release v0.1.68 — Lifecycle Evidence/Handoff Engine Correctness

> **Status:** Aprovado
> **Release ID:** v0.1.68
> **Owner:** product-engineer

## Strategy

Three independent engine defects, each fixed RED-first, then a single
full-pipeline E2E (FR4) that exercises all three invariants together on a
throwaway context — the operator-workflow test whose absence let these ship.
Waves are ordered only by review dependency, not by shared code:

- **Wave A — FR1 (remove run-unscopable disk-glob enrichment).** Touches
  `container.py` + `agent_runner.py` + the v0.1.66 FR8 repro test. RED seeds a
  stale role handoff and proves current code surfaces it; GREEN **removes** the
  `_build_handoff_lookup` disk-glob (never run-scopable — handoff files carry no
  run_id, the step-payload ledger is a different data plane) and replaces it with
  a `no_current_artifact` detail, inverting the FR8 test that encoded the defect.
- **Wave B — FR2 (terminal payload consumer).** Touches `pipeline.py`
  `run_implement_review_loop` only. RED proves `handoffs doctor` fails after an
  APPROVED run; GREEN declares `()` consumers on the terminal round.
- **Wave C — FR3 (TASKS write-scope derivation).** New resolver module +
  `pipeline.py` `_scope`/CLI wiring. RED proves implement `allowed_paths` lacks
  the task write set; GREEN adds the resolver and unions it.
- **Wave D — FR4 (full-pipeline E2E) + FR5 (validation).** The marquee E2E on a
  throwaway context; qa-engineer validates the whole suite + gates.

Waves A/B/C have disjoint write sets (`container.py`+`agent_runner.py` vs
`pipeline.py` review-loop vs new resolver module) and MAY proceed in parallel;
FR3's `_scope` edit and FR2's review-loop edit are in the same file
(`pipeline.py`) but different functions — serialize those two if a single
implementer holds both, or declare disjoint function-level write sets.

## Test plan
- Unit/integration RED proofs per FR (executed-path — drive the real engine
  functions / CLI, not helpers), each committed FAILING first.
- FR4 E2E provisions a real `tmp_path` context and drives the actual
  `dadaia lifecycle pipeline` + `implement-review` CLI on the fake harness.
- Full `pytest -p no:cacheprovider`, `ruff format --check`, `ruff check --no-cache`,
  `mypy --strict`, `lint-imports` (9 contracts).

## Rollback / risk
- FR1 changes an observability enrichment only — lowest risk; the no-op BLOCK
  invariant is unchanged.
- FR2 is a one-line conditional on `declared_consumers` — verdict already known
  at produce time; REJECTED path behavior preserved (AC2.2 guards it).
- FR3 adds a resolver; empty-tuple fallback keeps prior behavior when no TASKS.md
  / no reserved task (AC3.2 guards regression).

## Review gate
- software-architect REVIEW (anti-slop / root-cause) on SPEC+PLAN before implementation.
- qa-engineer on the picked set (grill-me) before SPEC approval.
- Post-implementation: qa-engineer suite/pyramid validation + security-reviewer
  push-cycle handoff keyed to the pushed sha.
