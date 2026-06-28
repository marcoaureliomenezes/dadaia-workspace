# TASKS: v0.1.34 alpha-1 - behavior-first test architecture

**Status:** Aprovado
**Release ID:** v0.1.34
**Segment:** alpha-1
**Owner:** product-engineer
**Created:** 2026-06-28

Marks: `[ ]` OPEN, `[-]` IN PROGRESS, `[x]` DONE.

---

## Tasks

### T-34-01 — Rewrite QA memory schema

- **Status:** [x]
- **Owner:** product-engineer
- **Write set:**
  - `specs/memory/quality-assurance.md`
- **Acceptance:** QA memory defines the behavior-first test law, suite budgets,
  residue exception rule, and validation profiles for current dadaia-workspace.

### T-34-02 — Remove residue-map governance ratchet

- **Status:** [x]
- **Owner:** software-engineer
- **Write set:**
  - `tests/contract/README.md`
  - `tests/contract/test_lifecycle_asymmetry_map.py`
  - `specs/bugs/test-governance-conflict-normalizes-residue-slop.md`
- **Acceptance:** Contract-test governance no longer blesses residue grep as the
  canonical delete/orphan strategy and no meta-test forces every feature package into a
  coverage map.

### T-34-03 — Delete or convert obvious residue-only tests

- **Status:** [x]
- **Owner:** software-engineer
- **Write set:**
  - `tests/contract/test_plugin_install_residue.py`
  - `tests/contract/test_bash_hook_residue.py`
  - `tests/contract/test_retired_model_id_residue.py`
  - `specs/backlog/plugin-packs-and-install-command.md`
- **Acceptance:** Deleted-code history pins are gone; any retained checks assert current
  registry/security/public-contract behavior.

### T-34-04 — Move synthetic performance out of pre-push

- **Status:** [x]
- **Owner:** software-engineer
- **Write set:**
  - `pyproject.toml`
  - `dadaia_workspace/features/ci_preflight/service.py`
  - `tests/performance/test_lifecycle_hygiene_scan.py`
  - `tests/unit/features/ci_preflight/test_service.py`
  - `specs/bugs/prepush-gate-blocked-by-loadsensitive-perf-test-wallclock-bound.md`
- **Acceptance:** Default/pre-push pytest deselects performance tests while a dedicated
  marker still allows explicit performance validation.

### T-34-05 — Validate focused behavior suite and counts

- **Status:** [x]
- **Owner:** software-engineer
- **Write set:**
  - `specs/releases/v0.1.34/alpha-1/TASKS.md`
- **Acceptance:** Focused contract/spec-context/panel/lifecycle tests pass; collection
  count is lower than the baseline; specs doctor reports 0 errors.
