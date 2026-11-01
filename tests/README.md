# Tests

Architecture, sizes and cost: `tests/AGENTS.md`; test basics: the workspace root map §1 —
read both before adding or editing a test.

## Commands

```bash
pytest -q -m "small and not slow" tests
python -m pytest -q -p scripts.covdata -m "small" --cov=dadaia_workspace --cov-report=term-missing --cov-fail-under=80
pytest -q -m medium tests --durations=30
pytest -q -m e2e tests/e2e/features --durations=30
npm run test:e2e
```
