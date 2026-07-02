---
title: semaphore-no-liveness-reclaim
severity: Medium
status: Closed
opened: 2026-06-05
session_id: null
resolved_in: v0.1.5/rc-2
superseded_by: v0.2.0/v0.1.6
---

# Bug: semaphore-no-liveness-reclaim

## Description

The per-context semaphore (`.dadaia/states/ctx_locks/<context>.semaphore.json`,
added in v0.1.5/rc-1 T-R1-02) is only reclaimable on **TTL expiry** (300s). It
has **no liveness check**: a semaphore held by a session whose owning process is
provably dead (PID not alive) and/or whose session file is missing is NOT
reclaimed until the full TTL elapses. `dadaia doctor --fix` reclaims orphan/stale
*implementation locks* (LOCK-3/LOCK-7) but does **not** touch the *semaphore*
surface at all.

Impact: a new session cannot acquire the context semaphore behind a dead holder
for up to TTL seconds, with no `doctor --fix` escape hatch — a stop-the-flow
delay of the kind R1 set out to eliminate. Observed live 2026-06-05: a bind was
forced to poll-wait ~5 minutes for the TTL of a dead holder (PID 3722142,
session sess_6ed21475) before acquiring.

## Steps to reproduce

1. Acquire the context semaphore from a process, then kill that process
   (leaving the semaphore file with a dead owner PID / no live session).
2. From a new session, `dadaia context bind <ctx> --mode implementation`.
3. Acquisition is refused until the 300s TTL elapses. `dadaia doctor --fix`
   does not reclaim the semaphore.

## Environment

- dadaia version: v0.1.4 (pyproject); working tree on `feature/0.1.5`
- OS: Linux
- Python: 3.12

## Root cause hypothesis

`semaphore.py` staleness is `_is_stale()` = heartbeat-age > ttl only. It should
also treat a semaphore as reclaimable when the owner PID is not alive OR the
owner session file is absent (liveness), mirroring the impl-lock orphan check
(doctor LOCK-7). Additionally `doctor`/`doctor --fix` should extend its lock
invariants to the `*.semaphore.json` surface (an orphan/stale semaphore code).
Relates to T-R1-02 (semaphore) and T-R1-06 (doctor lock invariants).

## Resolution

Fixed in v0.1.5/rc-2 via T-SEMA-01 and T-SEMA-02:

- **T-SEMA-01**: `_is_stale()` in `semaphore.py` now checks dead PID and missing
  session file in addition to TTL; `acquire_context_semaphore` silently reclaims
  stale-by-liveness semaphores on acquire.
- **T-SEMA-02**: `DoctorService.check()` now includes the SEM-1 invariant that
  scans `ctx_locks/*.semaphore.json` for orphan (context not alive) and stale
  (dead PID / missing session / TTL) semaphores and emits `[orphan-semaphore]` /
  `[stale-semaphore]` diagnostics. `DoctorService.fix()` reclaims flagged
  semaphores and appends audit entries to
  `.dadaia/states/audit/semaphore-reclaims.jsonl`.
