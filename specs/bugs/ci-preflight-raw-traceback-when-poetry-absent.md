---
name: ci-preflight-raw-traceback-when-poetry-absent
status: Closed
severity: LOW
reported: 2026-06-09
surface: dadaia ci preflight (features/ci_preflight/service.py)
session_id: null
resolved_in: 0.1.7 (rc-4, T-017-34)
---

**Resolution (0.1.7 rc-4, T-017-34):** `subprocess_runner._run` catches `FileNotFoundError` and returns `(127, 'command not found: <bin> …')` so a missing `poetry` yields a clean failure, not a raw traceback. Unit test `test_subprocess_runner_missing_binary_returns_127_not_traceback`.


**Symptom:** `dadaia ci preflight` invokes its checks as `("poetry", "run", ...)`
(`features/ci_preflight/service.py:42-48`). On a host where `poetry` is not on `PATH`
(e.g. a venv-only environment using `.dadaia/.venv/bin/python`), the command dies with a
raw Python traceback ending in `FileNotFoundError: [Errno 2] No such file or directory:
'poetry'`, and exits non-zero — instead of a clean, actionable message.

**Repro:**
```
# In an environment without poetry on PATH:
dadaia ci preflight
# -> Rich-rendered traceback through subprocess.run / _execute_child
# -> FileNotFoundError: ... 'poetry'   (exit 1)
```

**Expected:** A graceful preflight failure that names the missing dependency, e.g.
`[fail] ci preflight: 'poetry' not found on PATH — install poetry or run the checks
directly (ruff/mypy/pytest)`, with a non-zero exit but no stack trace. Bonus: detect
`poetry` (via `shutil.which`) and fall back to the active interpreter
(`python -m ruff` / `-m mypy` / `-m pytest`) when poetry is absent, so the
CI-equivalent gate still runs in venv-only environments.

**Impact:** LOW — cosmetic/robustness. The underlying checks (ruff format/check,
mypy --strict, pytest) all pass when run directly with the venv interpreter; only the
`poetry`-wrapped convenience entry point crashes ungracefully. Surfaced while validating
release 0.1.7 rc-3 in a venv-only environment.

**Notes:** No operator-local secrets. The CI-equivalent checks were verified green
manually for rc-3 (`ruff` clean, `mypy --strict dadaia_workspace/` clean, full `pytest`
2291 passed).
