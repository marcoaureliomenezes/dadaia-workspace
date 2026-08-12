# Tests

Rules for architecture, intent, admission, deletion and cost live in `tests/AGENTS.md` —
read it before adding or editing a test.

## Commands

```bash
pytest -q -m "unit and not slow" tests/unit
pytest -q -m "contract and not slow" tests/contract
pytest -q -m "unit or contract" --cov=dadaia_workspace --cov-report=term-missing --cov-fail-under=80
pytest -q -m integration tests/integration --durations=30
pytest -q -m e2e tests/e2e/features --durations=30
npm run test:e2e
```
