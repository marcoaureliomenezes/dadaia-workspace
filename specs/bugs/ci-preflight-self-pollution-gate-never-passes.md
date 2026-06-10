---
name: ci-preflight-self-pollution-gate-never-passes
status: Open
severity: HIGH
reported: 2026-06-10
session_id: sess_d7f127f8
surface: dadaia ci preflight / pre-push hook / tests/conftest.py session-pollution guard
---

**Symptom:** `dadaia ci preflight` (and therefore the pre-push hook) can never
pass on a clean tree. The pytest check always fails with `[SESSION POLLUTION]`
listing `.ruff_cache` and `.mypy_cache`, even though all 2511 tests pass.

**Repro:**
1. Clean repo root (no cache dirs present).
2. `poetry run dadaia ci preflight` (or `git push` with the hook installed).
3. `ruff format --check` and `ruff check` (invoked without `--no-cache`,
   `features/ci_preflight/service.py:46-47`) create `.ruff_cache/`;
   `mypy --strict` creates `.mypy_cache/` despite `incremental = false` in
   `[tool.mypy]` (the dir is still created).
4. The pytest check then runs; `tests/conftest.py::pytest_sessionfinish`
   checks the EXISTENCE of those dirs (not creation-during-session) and sets
   `exitstatus = 1`. Gate reports `Pre-push gate FAILED: pytest`.

**Expected:** The preflight gate's own earlier checks must not create the
pollution its final check rejects. Either invoke ruff with `--no-cache` and
redirect/suppress the mypy cache dir, or scope the session guard to
directories created during the pytest session.

**Notes:**
- Self-defeating invariant: the gate is unusable as shipped; every push is
  forced through the `--no-verify` emergency bypass, defeating the
  release-governance "never push red" mechanism.
- Related (distinct) open bug: `pre-push-gate-cannot-locate-workspace-venv`
  (hook discovery). This bug reproduces even when the hook finds poetry.
- `mypy` creates `.mypy_cache/` even with `incremental = false`; the fix needs
  an explicit `cache_dir` redirect (e.g. under the workspace tmp zone) or
  `MYPY_CACHE_DIR` in the check invocation.
- Verified manually that the underlying checks are green on a clean tree:
  ruff format/check OK, mypy --strict OK (215 files), pytest 2511 passed
  exit 0 with clean root afterwards.
