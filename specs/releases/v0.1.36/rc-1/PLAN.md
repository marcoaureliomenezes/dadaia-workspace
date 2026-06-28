# PLAN: v0.1.36 rc-1 - PI Layer-2 Release-Definition Ship Gate

**Status:** Aprovado
**Release ID:** v0.1.36
**Segment:** rc-1
**Owner:** product-engineer
**Created:** 2026-06-28

---

## Approach

1. Treat `alpha-1` as the implementation segment and `rc-1` as a validation/ship segment.
2. Re-run focused deterministic checks covering the code paths touched by alpha:
   PI command construction, per-step model routing, active-worker state, release-definition
   artifact gates, and the opt-in PI live-test skip behavior.
3. Run specs and public doctors to confirm SDD and projected public assets remain coherent.
4. Confirm no generated test artifacts or cache/state directories remain in the repository.
5. Write `rc-1/CLOSURE.md` with validation evidence and keep the release ready for archive
   or push workflow.

## Commands

```bash
.dadaia/.venv/bin/python -m ruff check --no-cache <changed python/test files>
.dadaia/.venv/bin/python -m pytest -p no:cacheprovider \
  repos/dadaia-workspace/tests/integration/cli/test_release_definition_workflow.py \
  repos/dadaia-workspace/tests/contract/test_headless_runtime_security.py \
  repos/dadaia-workspace/tests/unit/core/test_lifecycle_models.py \
  repos/dadaia-workspace/tests/integration/pi_live/test_real_layer2_worker_workflow_e2e.py -q
.dadaia/.venv/bin/dadaia specs doctor --specs-dir repos/dadaia-workspace/specs
.dadaia/.venv/bin/dadaia public doctor
find repos/dadaia-workspace -type d \( -name .dadaia -o -name .venv -o -name .pytest_cache -o -name .mypy_cache -o -name .hypothesis -o -name .ruff_cache -o -name test-results -o -name playwright-report -o -name coverage \) -print
```

## Risk

The only substantive risk is live PI variability. `rc-1` does not need to spend more live
PI credits because `alpha-1` already captured the real PI review-gate pass; the rc gate
must preserve that evidence and make sure default non-live CI remains deterministic.
