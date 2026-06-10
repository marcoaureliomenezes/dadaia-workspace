---
name: ci-preflight-checks-hardcode-poetry-run
status: Open
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
