---
name: lease-pid-veto-records-ephemeral-hook-pid
status: Closed
severity: HIGH
session_id: null
reported: 2026-06-10
surface: features/spec_context/lease.py acquire() + hooks/sdd_gate.py (WS-R2 FR-R2-03 pid veto)
---

**Resolution (v0.1.10 rc-2):** `hooks/sdd_gate.py::_resolve_holder_pid` records a LONG-LIVED pid (payload harness_pid/parent_pid/ppid, else `os.getppid()`) threaded as `holder_pid` through `gate_policy.evaluate` -> `lease.acquire`; heartbeat renew preserves the holder pid. Regression: `tests/e2e/test_two_actor_lease.py::test_hook_acquired_holder_no_steal_while_driver_alive_then_takeover` (hook-acquired holder, real driver process) + unit pid-resolution tests in `tests/unit/hooks/test_sdd_gate.py`.

**Symptom:** The v0.1.10 no-steal pid veto (FR-R2-03) is inert in harness-real
operation. `lease.acquire` records `pid = os.getpid()` by default (lease.py:328) and
`gate_policy.evaluate` passes no pid (gate_policy.py:262). In production the acquiring
process is the `python -m dadaia_workspace.hooks.sdd_gate` PreToolUse subprocess, which
exits milliseconds after writing the record — so the recorded pid is dead by the time
any foreign session probes it. `renew_heartbeat` never refreshes `pid` (lease.py:449-455).
Result: when the holder's heartbeat goes TTL-stale during a single long tool call
(>120 s, e.g. a long pytest — the exact reproduced lease-theft incident shape),
`lock_liveness.is_stale` probes a dead pid, the veto never fires, and a foreign session
TAKEOVERs a live session's lease.

**Repro:** Session A (any harness) holds the lease; run one Bash tool call lasting
>120 s (no PostToolUse fires mid-call, so no renewal). Session B performs a MUTATING
write: `is_stale` → TTL-stale → `pid_probe(record.pid)` where record.pid is the dead
sdd_gate hook subprocess → reclaimable → TAKEOVER. A's `.ptr` is overwritten; A is
blocked on its next write.

**Expected:** SPEC v0.1.10 WS-R2: "may never TAKEOVER from a live-probed holder
(FR-R2-03 supplies the no-steal half)". Surface text claims it in `data/AGENTS.md`
("pid demonstrably alive — is never stolen"), `workspace-protocol.md:18`, lease.py
docstring (:16-27), `dadaia-workspace-manager` skill (:92, :201).

**Notes:** The e2e proof (`tests/e2e/test_two_actor_lease.py:85-89`) has the holder
acquire IN-PROCESS and stay alive — a topology production never exhibits — so
AC-R2-04(i)/(ii) are proven for the wrong process model. Fix direction: record a
long-lived pid — the hook's parent (`os.getppid()` = the harness process) or a pid
threaded from the CLI-owned session record — and add a harness-real-topology e2e
(holder acquires via a short-lived subprocess, stays busy in the parent). Relabel the
four overclaiming text sites until fixed. Found by the 2026-06-10T052944Z ai-engineer
re-audit.
