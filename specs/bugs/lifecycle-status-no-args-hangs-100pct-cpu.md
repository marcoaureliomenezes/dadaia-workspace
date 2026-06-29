---
name: lifecycle-status-no-args-hangs-100pct-cpu
status: Closed
severity: MEDIUM
reported: 2026-06-28
resolved: 2026-06-29
release: v0.1.37
surface: dadaia lifecycle status (CLI)
session_id: sess_8cdf6cce
---

# `dadaia lifecycle status` (no args) hangs at 100% CPU and never returns

**Symptom:** `.dadaia/.venv/bin/dadaia lifecycle status` with no arguments spins at ~100%
CPU indefinitely and produces no output. Killed manually after ~2.5 minutes; a clean
re-run under `timeout 25` exited 124 (still running at the deadline) having printed nothing.

**Repro:**

```bash
.dadaia/.venv/bin/dadaia lifecycle status            # hangs, 100% CPU, no output
timeout 25 .dadaia/.venv/bin/dadaia lifecycle status # -> "Terminated", exit 124
```

`--help` works normally and shows the command takes only `--json` / `--help` (no required
args), so the hang is in the status computation itself, not arg parsing.

**Expected:** `lifecycle status` should print the lifecycle status (or a "no active run /
specify context" message) and exit promptly.

**Actual:** Pegs one core at 100% and never terminates; no stdout/stderr. Reproduced twice
on 2026-06-28 from the workspace root.

**Severity rationale:** MEDIUM — a read-only inspection command is unusable (must be killed),
but there is no state corruption and other lifecycle inspection commands
(`workflow policy show`, `workflow profiles list`, `release define --json`) work.

**Notes:** Likely an unbounded loop or a blocking scan over run/handoff state. Discovered
while grounding the lifecycle state before running release-definition on PI. Registered via
direct-Markdown fallback (the `bug report` workflow's default `--harness fake` writes a
stub — see `bug-report-fake-bug-write-emits-stub-and-discards-fields`). No secrets included.

## Resolution

Closed in `v0.1.37/alpha-1`.

Root cause: the top-level `dadaia lifecycle status` command was wired to the lifecycle
hygiene cleanup status path, which performs cleanup/handoff-oriented scanning. That made
the no-arg lifecycle status command much heavier than a status read should be and could
hang on large/stale runtime state.

Fix: top-level `lifecycle status` now reads the persisted lifecycle run store and reports
bounded run counters (`run_count`, `running`, `blocked`, `completed`). The heavier cleanup
scan remains available under `dadaia lifecycle hygiene status`.

Validation:

- `pytest -p no:cacheprovider tests/integration/cli/test_lifecycle_cli.py -q` -> `13 passed`.
- `timeout 10 .dadaia/.venv/bin/dadaia lifecycle status --json` returned `status=OK` in the live workspace.
- Included in focused v0.1.37 deterministic suite -> `41 passed`.
