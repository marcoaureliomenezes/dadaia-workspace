---
name: ci-preflight-checks-hardcode-poetry-run
status: Closed
closed: 2026-06-11
fixed_by: v0.1.11
severity: MEDIUM
reported: 2026-06-10
session_id: sess_b973c3e4
surface: dadaia ci preflight / features/ci_preflight/service.py check argv
---

**Symptom:** the pre-push hook (v0.1.10 probe) correctly resolves the workspace
venv runner without poetry, but every preflight check it then runs is built as
`("poetry", "run", "ruff", ...)` — so on a host where poetry is not on PATH the
gate fails with `command not found: poetry` even though all tools exist in the
resolved venv.

**Repro:** from a workspace-managed clone with poetry off PATH:
`git push` (hook resolves `<ws>/.dadaia/.venv/bin/dadaia` via walk-up) →
`Pre-push gate FAILED: ruff format --check / command not found: poetry`.

**Expected:** the checks must inherit the runner resolution the hook already
performed — invoke tools from the same environment as the resolved `dadaia`
(e.g. sibling executables of `sys.executable`, or a `DADAIA_BIN`-derived bin
dir), with `poetry run` as fallback only.

**Notes:** found during the v0.1.10 ship push; the T-010-26 probe and T-010-25
self-pollution fixes are sound — this is the remaining seam between them.
Workaround: put the workspace venv bin on PATH for the push.

**Resolution (v0.1.11, 2026-06-11):** `_resolve_tool` with pinned order — venv sibling of
`sys.executable` (symlink-safe, fix `774a076`) → `DADAIA_BIN` bin dir → `poetry run`
fallback only; no `shutil.which` (T-011-06). Named regression tests:
`tests/unit/features/ci_preflight/test_resolve_tool.py` —
`test_resolve_tool_prefers_venv_sibling_of_python`,
`test_resolve_tool_sibling_of_python_symlink_not_its_target`,
`test_resolve_tool_falls_back_to_dadaia_bin_when_no_venv_sibling`,
`test_resolve_tool_poetry_fallback_when_missing_everywhere`,
`test_resolve_tool_never_calls_shutil_which`,
`test_all_five_checks_built_through_resolve_tool`,
`test_preflight_works_with_poetry_off_path`. Real-tree repro proof:
`env PATH=/usr/bin:/bin dadaia ci preflight` → 4/4 PASS with poetry absent (final-gate
item 7, `feature/v0.1.11 @ e1f2de3`).
