# SPEC — Release v0.1.75 — Test-suite rearchitecture (1,000–1,200 high-value tests)

**Status:** Aprovado
**Source:** backlog `20260709-test-suite-remediation-waves` (operator mandate 2026-07-09);
grill: 2026-07-09 software-architect 5-release-plan grill (verdict + obligations recorded
in `specs/backlog/candidates.md`).

## Problem

~4,450 python test fns (~13 min serial) for a product whose behavior needs 1,000–1,200
well-designed tests. Growth since June is legitimate executed-path coverage, but the
suite carries: one-assert-per-facet fan-outs, unparametrized decision tables,
copy-pasted contract templates, JS/CSS/HTML string-greps shadowed by Playwright/goldens,
cross-tier duplicates, and dead always-skipped tests. Every push pays the full tax twice
(pre-push + CI).

**High-value test definition (operator-ratified):** the unique failure detector for one
real behavior/contract, asserting outcomes through the executed path — never
implementation strings, never a duplicate of another tier's coverage.

## FRs

- **FR1 — Cluster rearchitecture.** Execute the 7 per-cluster classification plans in
  `.dadaia/tmp/claude/20260709/test-rearch/plan-*.md` (every test file read and
  classified KEEP/MERGE/DELETE, only-coverage risks named). Cluster budgets: panel 81,
  lifecycle ~185, unit-features-rest 250, infrastructure ~150, core+hooks+cli 149,
  unit-root/helpers/public/scripts ~175, integration ~145 (+5 opt-in live), contract+e2e
  ~120. Target total: 1,000–1,200 collected python test fns.
- **FR2 — Frozen-suite re-baseline (grill CRITICAL).** The spec_context consolidation
  merges files of the frozen v0.1.50 no-steal suite — an explicit, QA-ship-gate
  adjudicated re-baseline, never silent. Deliverable: the SUCCESSOR frozen baseline =
  surviving parametrized decision tables + the verbatim-kept concurrency/property files,
  named in CLOSURE; every no-steal invariant (TTL-stale-but-pid-alive never reclaimed,
  foreign live holder never stolen, CAS/TOCTOU proofs) survives as a named test or param
  row. v0.1.79's platform-seam zero-diff gate re-keys to this successor baseline.
- **FR3 — Speed wiring (no engine work).** `public/scripts/pre-push-ci-gate.sh` invokes
  `ci preflight --quick` (e2e stays CI-sharded); pytest-xdist added and `-n auto` on the
  unit tiers (preflight pytest check + CI unit jobs; verify pytest-randomly interplay);
  `tests/tmp/` gitignored (README exception).
- **FR4 — Shared fixtures.** One session-scoped workspace template (stage+install once,
  copytree per test) replacing ~40 per-test `WorkspaceService.init` runs; one
  package-scoped panel-server factory conftest replacing 6 hand-rolled
  ThreadingHTTPServer copies; panel tab list single-sourced in one fixture (v0.1.77
  rides it).

## Coordination obligations (from the plan grill)

- Bind-resolution integration cluster (`test_cli_bound_session_resolution`,
  `test_codex_thread_id_bind`, `test_context_show_reflects_bind`) stays minimally
  merged — v0.1.76 rewrites it into the all-verbs contract test.
- CRITICAL machinery keeps consolidated-never-weakened coverage: pre_gate policy
  matrix, lease pid-lineage, redaction (incl. v0.1.73 `evidence` field), git
  chokepoints, migrations, push-gate `commit_sha` keying, doctor + workflow goldens.

## Acceptance

1. Authored python test fns between 1,000 and 1,200 (`grep -rh "def test_" tests
   --include="*.py" | wc -l`) — the operator's unit of "a designed test"; a
   parametrized table is ONE designed test over named rows, so the pytest collected
   count is naturally higher and is reported transparently alongside.
2. Full suite green; CI 80% coverage job green; Playwright suite untouched and green.
3. No behavior loses its ONLY coverage — each cluster plan's "only-coverage" list is
   verified present in the surviving suite.
4. FR2 successor baseline named and QA-adjudicated at the ship gate.
5. Pre-push wall-clock materially down (target ≥50%: --quick + xdist).
