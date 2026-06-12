---
title: panel-subprocess-in-features-layer
severity: High
opened: 2026-06-07
session_id: null
status: Closed
shipped_in: 0.1.5
resolved_in: main (post-v0.1.5, T-016-P0x)
---

**Resolution (verified 2026-06-09, code-reviewer root-cause investigation):** fixed in current `main` (T-016-P0x pass). Source evidence cited in handoff `.dadaia/handoff/dadaia-workspace/2026-06-09T032430Z-code-reviewer-panel-bug-cluster-root-cause.handoff.json`; named E2E regression tests present (E2E-GUARD-01/02, E2E-SCP-03..06, E2E-THM-10). Closed; E2E suite is the standing guard.


# Bug: panel-subprocess-in-features-layer

## Description

`PanelService.run_workflow` shells out via `subprocess.Popen` and probes
liveness with `os.kill(pid, 0)` directly inside the `features/` layer, violating
the architecture rule "NÃO chamar `os.system`/`subprocess` fora de
`infrastructure/`". Additionally, the running-workflow set is tracked in an
in-memory dict, so it is **lost on panel restart** — a still-running workflow
appears "not running" after restart and can be double-started.

## Location

- `dadaia_workspace/features/panel/service.py:~257-268` — `subprocess.Popen([...,
  "orchestrate", workflow_name])`, `os.kill(pid, 0)`, `self._running_workflows`
  in-memory dict.

## Impact

- Layer-boundary violation (I/O/system calls leak into `features/`).
- State loss on restart → duplicate workflow launches.

## Environment

- dadaia version: 0.1.5 + current `main`
- Python: 3.12

## Fix direction

Define a `WorkflowLauncher` protocol in `core/protocols/`, implement it in
`infrastructure/` (the `Popen`), inject into `PanelService`. Persist running
PIDs to a JSON state file under `.dadaia/states/` (or delegate to
`OrchestrationService`'s run-state store) so restart does not lose state.
