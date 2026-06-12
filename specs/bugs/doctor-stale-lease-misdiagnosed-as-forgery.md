---
name: doctor-stale-lease-misdiagnosed-as-forgery
status: Closed
closed: 2026-06-11
fixed_by: v0.1.11
severity: MEDIUM
session_id: null
reported: 2026-06-10
surface: specs doctor (SPEC-DOC-029) + lease lifecycle (ctx_locks GC)
---

**Symptom:** `dadaia specs doctor` emits `[ERR] SPEC-DOC-029: session-identity incoherence ... lease↔session incoherence (possible out-of-band lock/ptr forgery)` for a context whose lock file is simply a **stale lease left by a dead session**. In the observed case the lock record's `heartbeat` was ~36 hours old with `ttl: 120` (seconds), the recorded harness session no longer existed, and the incumbent pointer + session record correctly referenced a freshly bound READ session. No forgery occurred; the lease was just never garbage-collected.

**Repro:**
1. A session binds a context in IMPLEMENTATION mode and acquires the per-context lease (`.dadaia/states/ctx_locks/<context>.lock.json`).
2. That harness session ends without the lease being released; TTL (120s) expires; no GC reclaims the file.
3. A new session runs `dadaia context bind <context>` (READ) — incumbent ptr and session record now point at the new session.
4. `DADAIA_CONTEXT=<context> dadaia specs doctor` → `[ERR] SPEC-DOC-029` "possible out-of-band lock/ptr forgery", exit non-zero.

**Expected:** The lease contract is TTL + pid-veto liveness. A lock record whose heartbeat is orders of magnitude past TTL and whose holder is demonstrably dead should be (a) reclaimable/GC'd (or at least flagged as `stale lease — safe to reclaim` with a remediation command), and (b) NOT reported as possible forgery. Doctor should distinguish "expired stale lease from a dead session" from "live lock-holder ≠ incumbent" before alleging forgery, and should suggest the remediation path.

**Notes:** Observed on a consumer context in a self-hosting workspace, dadaia-workspace v0.1.10 line. The stale record carried no `pid` field (older record shape?), so the pid-veto/liveness check may also be skipping records that predate the pid field, leaving them permanently un-reclaimable and permanently failing doctor. Two sub-issues: (1) no GC/reclaim path for expired leases outside a MUTATING-write acquisition; (2) SPEC-DOC-029 message conflates staleness with forgery and offers no remediation. Paths redacted; lock file at `.dadaia/states/ctx_locks/<context>.lock.json`.

**Resolution (v0.1.11, 2026-06-11):** Both sub-issues fixed. (1) GC/reclaim path:
`LOCK-GC` under `dadaia doctor --fix` reclaims TTL-expired leases whose holder is dead or
unprobeable (pre-pid records ⇒ TTL-only reclaimable); a live-pid holder is NEVER
reclaimed (T-011-02 + container probe wiring fix `62e8db5`); `dadaia lock steal` is
probe-gated (T-011-01). (2) SPEC-DOC-029 three-state triage: dead-stale ⇒ WARN "stale
lease from a dead session — safe to reclaim" naming `dadaia doctor --fix` /
`dadaia lock steal <ctx>`; live + genuinely incoherent ⇒ ERR (forgery wording only
there); coherent ⇒ silent (T-011-03). Named regression tests:
`tests/unit/features/spec_context/test_doctor_lock_gc.py` —
`test_ttl_expired_dead_pid_reported_and_reclaimed`,
`test_ttl_expired_pidless_record_reported_and_reclaimed`,
`test_ttl_expired_alive_pid_never_reclaimed`, `test_reclaim_helper_decision_table`;
`tests/unit/features/specs/test_doctor_ledger_invariants.py` —
`test_stale_dead_holder_lease_reports_doc_029_warning_with_remediation`,
`test_stale_pidless_lease_with_fresh_read_bind_warns_not_err`. Live proof at the final
gate: SPEC-DOC-029 WARNs in other contexts carried GC remediation wording, zero forgery
wording (`feature/v0.1.11 @ e1f2de3`).
