---
name: layer1-hooks-create-repo-pycache
status: Open
severity: MEDIUM
reported: 2026-06-29
surface: Layer-1 hooks / dadaia CLI execution environment
session_id: null
---

# Layer-1 hook and CLI invocations recreate forbidden repo-local `__pycache__` trees

**Symptom:** After removing repo-local Python cache directories, subsequent tool/CLI activity recreated many `__pycache__/` directories under `repos/dadaia-workspace/dadaia_workspace/**`. This violates the repo-hygiene contract that no tool-generated cache/state/artifact directories may appear inside a repo working tree.

**Repro:**

```bash
find repos/dadaia-workspace -type d \( -name __pycache__ -o -name .ruff_cache -o -name .pytest_cache -o -name .mypy_cache -o -name .hypothesis -o -name test-results -o -name playwright-report -o -name coverage -o -name .dadaia -o -name .venv \) -prune -exec rm -rf {} +
PYTHONDONTWRITEBYTECODE=1 .dadaia/.venv/bin/dadaia public doctor
find repos/dadaia-workspace -type d -name __pycache__ -print
```

**Expected:** dadaia workspace tooling and Layer-1 hooks must run with bytecode disabled or redirected outside repository working trees; the final `find` should print no forbidden repo-local cache directories.

**Actual:** `__pycache__/` directories reappear under the source repo package tree after tool/CLI activity, even when commands are invoked with `PYTHONDONTWRITEBYTECODE=1`.

**Notes:** Direct Markdown fallback used because the default `dadaia lifecycle bug report --harness fake` path is currently known to discard operator-provided bug fields (`bug-report-fake-bug-write-emits-stub-and-discards-fields`). No secrets or operator-local absolute paths are included.
