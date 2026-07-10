# TASKS — Release v0.1.75

**Status:** Aprovado

> Write sets are per-cluster test trees + the named config/script files. Production code
> is OUT of scope for every task (test-only release, except T-8's script/config wiring).

- [x] **T-1** Panel cluster per `plan-panel.md` (496→81).
  Write set: `tests/unit/features/panel/**`, `tests/e2e/panel/**` (goldens only)
- [x] **T-2** Infrastructure cluster per `plan-infrastructure.md` (622→~150; split
  `test_public_assets.py` by concern).
  Write set: `tests/unit/infrastructure/**`
- [x] **T-3** Contract+e2e cluster per `plan-contract-e2e.md` (294→~120).
  Write set: `tests/contract/**`, `tests/e2e/**` (python only), `tests/performance/**`
- [x] **T-4** Core+hooks+cli + unit-root adjacency per `plan-core-hooks-cli.md`
  (~854→~324).
  Write set: `tests/unit/core/**`, `tests/unit/hooks/**`, `tests/unit/cli/**`,
  `tests/unit/*.py`, `tests/unit/helpers/**`, `tests/unit/public/**`,
  `tests/unit/scripts/**`
- [x] **T-5** Lifecycle cluster per `plan-lifecycle.md` (515→~185).
  Write set: `tests/unit/features/lifecycle/**`
- [x] **T-6** Unit-features-rest incl. spec_context per `plan-unit-features-rest.md`
  (1,035→250) + **FR2 frozen-suite re-baseline** (successor baseline named; QA
  adjudication recorded in the task commit + CLOSURE).
  Write set: `tests/unit/features/**` (excluding `panel/`, `lifecycle/`)
- [x] **T-7** Integration cluster per `plan-integration.md` (574→~145; shared
  session-scoped workspace template + panel-server factory; relocations to unit; dead
  live files deleted).
  Write set: `tests/integration/**`, `tests/unit/**` (relocation targets only)
- [-] **T-8** Speed wiring + reconciliation: pre-push hook → `ci preflight --quick`;
  pytest-xdist dep + `-n auto` on unit tiers (preflight + CI unit jobs; 3 consecutive
  randomized green runs); `tests/tmp/` gitignored; `pytest --collect-only -q` count in
  [1,000, 1,200] (apply secondary-squeeze lists if over); full suite green.
  Write set: `dadaia_workspace/public/scripts/pre-push-ci-gate.sh`,
  `dadaia_workspace/features/ci_preflight/**`, `.github/workflows/*.yml`,
  `pyproject.toml`, `poetry.lock`, `.gitignore`, `tests/**`
