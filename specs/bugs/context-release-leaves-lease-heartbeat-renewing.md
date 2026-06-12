---
name: context-release-leaves-lease-heartbeat-renewing
status: Open
severity: HIGH
reported: 2026-06-12
session_id: null
surface: dadaia context release / context dead / PostToolUse heartbeat hook
---

**Symptom:** `dadaia context dead <ctx>` is permanently blocked with
"Context '<ctx>' has an active implementation lock" even after the holding
session runs `dadaia context release`. `release` removes the session binding
record but leaves `.dadaia/states/ctx_locks/<ctx>.lock.json` in place, and the
PostToolUse heartbeat hook keeps renewing that lease's `heartbeat` on every
subsequent tool call of the same harness session — observed a renewal ~30s
*after* a successful `✓ Session ... released`. The lease therefore never goes
TTL-stale while the operator's session is active, so the very session
coordinating the shutdown can never call `dead()`.

**Repro:**
1. Bind a context in implementation mode; do work (lease + heartbeat active).
2. `DADAIA_SESSION_ID=<sid> dadaia context release` → `✓ Session released`.
3. Inspect `ctx_locks/<ctx>.lock.json` → still present; make any tool call →
   `heartbeat` timestamp renews again.
4. `dadaia context dead <ctx>` → "active implementation lock" error, forever.

**Expected:** `release` must drop (or stop renewing) the implementation lease
held by the released session — the lock record's `session_id` matches the
releasing session, so this is the holder releasing its own lease, not a steal.
After release, `dead()` from the same harness session must proceed. At minimum
the heartbeat hook must not renew a lease whose session record no longer exists.

**Notes:** Recorded lease pid was not alive (harness pid churn — see
lease-pid-veto-records-ephemeral-hook-pid), so liveness rested on heartbeat
alone, which the hook itself kept refreshing — a self-sustaining orphan.
Workaround used: manually remove `ctx_locks/<ctx>.lock.json` and run
`context dead` in the same shell command (no intervening tool call → no
renewal). TTL 120s, mode BOUND_IMPLEMENTATION, observed on Claude Code harness.
