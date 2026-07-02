# PLAN — v0.1.51 — E2E Journey Canon

**Status:** Aprovado

## Wave map

- **W0 — definition**: ACTIVE → v0.1.51 DEFINITION; SPEC/PLAN/TASKS authored from the
  definition-time inspection; dual definition review (software-architect REJECT +
  qa-engineer REJECT — FR2 input redefined + `init` restored, residue set extended to
  four surfaces with a stated discriminator, ship-contract single-home rule,
  mutation-sanity AC-7, FR4 pinned journey + verification-first step, AC-5 pair-set
  inventory); `Aprovado`; definition commit.
- **W1 — FR1 master journey**: the narrative lifecycle E2E. Fixture assembly first
  (sandboxed workspace + local bare remote), then the chain
  create→alive→bind→inject→gate with real subprocesses; reuse
  `lease_rendezvous.py` helpers and the `run_hook_subprocess` pattern.
  Mutation-sanity demonstration (AC-7) before the wave commit.
- **W2 — FR2 upgrade E2E**: below-canonical structurally-complete tree →
  real `specs upgrade` → `init` → doctor-green; no-op idempotence scenario.
  Mutation-sanity demonstration (AC-7).
- **W3 — FR3 residue disposition**: confirm the bytecode invariant's existing
  coverage; land the single explicit ship assertion in
  `test_public_source_hygiene.py`; delete the THREE law-violating files; strip
  Assertion 5 (only) from the onboarding acceptance.
- **W4 — FR4 panel journey**: verification-first step (per-request re-read of
  `spec_contexts.json`), then the pinned ALIVE→DEAD badge-delta spec on the Spec
  Context Projects tab. Mutation-sanity demonstration (AC-7).
- **W5 — FR5 parametrization**: top-5 files, true shape-duplicates only;
  `(callable, fixture-state)` pair inventory before/after on the task line.
- **W6 — gates + ship (flat release — single ship gate)**: full local gates; QA
  review commit (verifies AC-7 evidence per new E2E; AC-4 finalized against the
  post-push `e2e-panel` run URL); security push-gate APPROVE keyed to the pushed
  sha; push; CI green (including `e2e-panel`); PR; merge.
- **W7 — closure** (CLOSURE phase): CLOSURE.md (`## Validations` + `## Drifts` —
  SPEC-DOC-006); consumed-backlog removal ×1 with durable copy + ledger; memory
  update (`quality-assurance.md` E2E-coverage description refresh ONLY if its text
  now understates the suite — no law change); catalog + lint; archive; ACTIVE → none;
  candidates.md R3 row marked shipped.

## Write sets (disjoint per wave)

| Wave | Files |
|---|---|
| W1 | `tests/e2e/features/test_lifecycle_journey_e2e.py` (new); additive, signature-compatible helpers in `tests/e2e/lease_rendezvous.py` if needed |
| W2 | `tests/e2e/features/test_specs_upgrade_e2e.py` (new) |
| W3 | `tests/contract/test_retired_model_id_residue.py` (delete), `tests/contract/test_bash_hook_residue.py` (delete), `tests/contract/test_session_bound_context_residue.py` (delete), `tests/integration/test_onboarding_tree_v2_e2e.py` (strip Assertion 5), `tests/contract/test_public_source_hygiene.py` (receive the single ship assertion) |
| W4 | `tests/e2e/panel/spec-context-operation-journey.spec.ts` (new) |
| W5 | `tests/unit/infrastructure/test_public_assets.py`, `tests/unit/features/specs/test_doctor.py`, `tests/unit/features/specs/test_scaffolder.py`, `tests/unit/features/specs/test_doctor_taxonomy_disposition.py`, `tests/unit/features/spec_context/test_session_identity.py` |
| W7 | `specs/releases/v0.1.51/**`, `specs/_archive/**`, `specs/memory/**` (conditional, closure-phase), `specs/backlog/` (removal + candidates row) |

NO `dadaia_workspace/**` path is in any write set (test-only release). A production
defect found by W1/W2/W4 is registered as a bug (ADDITIVE), never fixed inline.

## Test strategy

- W1/W2 run in the existing `E2E Python (pytest)` CI job; locally via plain pytest
  (no network: the clone remote is a local bare repo; upgrade runs on a tmp tree).
- Subprocess actors get explicit env (`WORKSPACE_ROOT`, harness sid vars) — never
  inherited live-workspace state; every actor's stdout/stderr is captured and printed
  on deadline failure.
- **Mutation-sanity (AC-7):** during development each new E2E is run once against a
  deliberate one-line sabotage of its guarded behavior and must FAIL; the evidence
  (sabotage + observed failure) goes on the task line; the sabotage never lands in a
  commit.
- W4 runs in the `e2e-panel` CI job (GH-only in practice); the spec follows the
  existing fixture/server-command harness in `tests/e2e/panel/`.
- W5 is pure refactor: the `(callable, fixture-state)` pair-set before/after is the
  zero-loss proof; identical pass counts alone are NOT sufficient.
- Full-suite + lint + mypy locally before push (pre-push gate re-runs them).

## Rollback

Single feature branch `feature/v0.1.51`; one commit per wave; revert = drop the
branch before merge. No production or state-schema changes at all.
