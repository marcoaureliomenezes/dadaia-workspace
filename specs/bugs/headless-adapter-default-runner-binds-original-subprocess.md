---
name: headless-adapter-default-runner-binds-original-subprocess
status: Closed
severity: HIGH
reported: 2026-06-29
surface: lifecycle pipeline / PI and Codex headless adapter test seam
session_id: codex-goal-v0.1.36-push
---

# Headless adapters bind the original `subprocess.run`, so monkeypatched PI/Codex tests can leak to real workers

**Symptom:** The pre-push gate failed in `test_pipeline_runs_first_step_on_pi_harness_end_to_end`.
The test intended to fake the `pi --mode json` stream by monkeypatching
`dadaia_workspace.infrastructure.pi_runtime.subprocess.run`, but the pipeline accepted the
implementation step and blocked later instead of blocking on the fake plain-text PI output.

**Repro:**

```bash
.dadaia/.venv/bin/python -m pytest -p no:cacheprovider \
  repos/dadaia-workspace/tests/integration/cli/test_lifecycle_pipeline_cli.py::test_pipeline_runs_first_step_on_pi_harness_end_to_end -q
```

Before the fix:

```text
FAILED ... assert payload["steps"][0]["accepted"] is False
E       assert True is False
```

The isolated test took about 101 seconds, which is far too slow for a hermetic fake stream
test and indicates the fake runner was not the runner actually used by the adapter.

**Expected:** A monkeypatched or injected runner must be the runner used by the headless
adapter. A hermetic test stream must not call the real `pi` or `codex` CLI, spend operator
credits, or depend on live provider behavior.

**Actual:** `PiHeadlessAdapter.__init__` and `CodexExecAdapter.__init__` declared
`runner: Runner = subprocess.run`. Python evaluates default argument objects at function
definition time, so the default runner held the original `subprocess.run` function even
after tests monkeypatched the module attribute. The same seam leak existed in both headless
CLI adapters.

**Root cause:** Import-time binding of `subprocess.run` in adapter constructor defaults.

## Resolution — v0.1.36 rc-1 follow-up

Both headless adapters now take `runner: Runner | None = None` and resolve
`self._runner = runner or subprocess.run` inside `__init__`. That keeps explicit runner
injection unchanged and makes module-level monkeypatching effective for default-runner
tests.

Validation:

```bash
.dadaia/.venv/bin/python -m pytest -p no:cacheprovider \
  repos/dadaia-workspace/tests/integration/cli/test_lifecycle_pipeline_cli.py::test_pipeline_runs_first_step_on_pi_harness_end_to_end -q
# 1 passed in 1.93s

.dadaia/.venv/bin/python -m pytest -p no:cacheprovider \
  repos/dadaia-workspace/tests/contract/test_headless_runtime_security.py \
  repos/dadaia-workspace/tests/integration/cli/test_lifecycle_pipeline_cli.py -q
# 13 passed in 2.51s
```

**Bug-report workflow note:** This record was written by direct Markdown fallback because
`bug-report-fake-bug-write-emits-stub-and-discards-fields` is still open; the documented
workflow-first bug report path is known to discard operator-provided fields under the fake
runtime.
