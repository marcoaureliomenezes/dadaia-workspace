---
name: lease-pid-veto-ignores-archived-release-blocks-next-release
status: Open
severity: HIGH
reported: 2026-06-30
surface: SDD lease liveness / pid-veto (core/lock_liveness.py + hooks/sdd_gate.py) vs archived-release lease
session_id: sess_c7ff38d9
---

# A live-but-idle session whose release is ARCHIVED keeps the context MUTATING lease forever (pid-veto ignores release state), deadlocking the next release

**Symptom:** After a release is closed/archived (`ACTIVE.md` → `release: none / phase:
ARCHIVED`), the session that implemented it can stay alive (e.g. an idle Codex terminal
left open). Its lease record for the now-archived release lingers. Because the holder
**pid is still alive**, the pid-veto treats the lease as live **even past TTL**, so:
- every MUTATING write from any other session is blocked with `[SDD LOCK]`, and
- `dadaia lock steal` **correctly refuses** (pid-veto), as designed.

There is **no self-service path** to start the next release: the context is held hostage
by a finished-but-alive session.

**Repro (observed 2026-06-30):**
1. `ACTIVE.md` = `release: none / phase: ARCHIVED` (v0.1.41 closed).
2. `.dadaia/states/ctx_locks/dadaia-workspace.lock.json` still holds
   `{release: v0.1.41, session_id: 019f14b1…, pid: 277232, ttl: 120}` with heartbeat
   **339s stale** (holder idle, no longer renewing — the
   `context-release-leaves-lease-heartbeat-renewing` fix works: it stopped renewing).
3. Holder pid 277232 = a `codex` process, **alive** (~8h elapsed, idle).
4. `dadaia context bind dadaia-workspace --mode implementation --release v0.1.42` → OK.
5. Any MUTATING write (e.g. authoring `specs/releases/v0.1.42/SPEC.md`) →
   `[SDD LOCK] Session '019f14b1…' is actively mutating context 'dadaia-workspace'`.
6. `dadaia lock steal dadaia-workspace` → refuses (pid-veto: holder pid alive).

**Expected:** Lease liveness should consider the **release state**. A lease whose
`release` is archived (no longer the ACTIVE release) is semantically dead and should be
reclaimable regardless of holder-pid liveness — the holder is provably done with that
release. The pid-veto should protect a session mutating the **current** release, not one
pinned to an archived release id. Equivalently: closure/archival should release the lease,
or `lock steal` should treat an archived-release lease as stale despite a live pid.

**Actual:** pid-veto is release-agnostic; an alive pid vetoes reclaim forever, so the
context cannot start its next release without manually terminating the holder process
(destructive) or running `dadaia context release` inside the stale session.

**Impact:** HIGH — blocks the entire next release (release-definition + implementation are
MUTATING) until a human closes the leftover session. Discovered while starting the
`specs-truth-realignment-constitution-memory` release.

**Suggested fix:** In the lease-liveness verdict (and `lock steal`), reclaim a lease whose
`release` != the context's ACTIVE release (or whose release is archived) regardless of pid;
and/or have closure/archival explicitly release the lease. Keep the pid-veto only for a
lease pinned to the live ACTIVE release.

**Relation:** `context-release-leaves-lease-heartbeat-renewing` (Closed) fixed the
*heartbeat-renewal* half (the heartbeat did go stale here); this is the residual
**pid-veto-ignores-archived-release** half. No secrets included; pid is a local process id.
