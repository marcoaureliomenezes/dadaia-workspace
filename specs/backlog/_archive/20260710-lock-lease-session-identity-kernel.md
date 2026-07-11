---
name: lock-lease-session-identity-kernel
status: delivered
delivered_in: v0.1.76
opened: 2026-07-10
owner: project-manager (curates)
priority: P0
source: "2026-07-10 remote-user CRITICAL bug `layer1-rebind-adopts-lease-to-synthetic-session-self-block` + P0 audit `specs/audits/2026-07-10-lock-risk-audit-cross-harness.md`; absorbs backlog `platform-seam-todo-retirement`. REDEFINED 2026-07-10 under the operator-ratified NO-LOCKS DOCTRINE (4 decisions, see body) — remediation is REMOVAL of blocking, not repair of identity"
absorbs:
  - bug: layer1-rebind-adopts-lease-to-synthetic-session-self-block (CRITICAL, open)
  - audit: 2026-07-10-lock-risk-audit-cross-harness (all findings — dispositioned by removal, see mapping)
  - backlog: platform-seam-todo-retirement (superseded)
intents:
  - subject: { kind: code, ref: "dadaia_workspace/features/spec_context/gate_policy.py#evaluate" }
    change: "REMOVE every concurrency block from the write path. The MUTATING+lease-acquiring branch (gate_policy.py:294-316) no longer calls lease.acquire() and can no longer emit a LockHeldError block: a MUTATING write upserts a lightweight session-PRESENCE record (never fails, never blocks) and — when another live session's presence exists on the same context — the gate ALLOWS and surfaces a one-line advisory WARNING in the tool output naming the other session (runtime, age). Races between concurrent sessions are ACCEPTED and SURFACED, never prevented: the operator ratified that a blocked user is strictly worse than a rare merge conflict. Path-class policy is NOT concurrency and stays: PROTECTED (.dadaia/sessions fail-closed), FROZEN, MEMORY-phase, and READ-mode blocks survive — but mode resolution becomes STRICTLY SELF-SCOPED (env -> own session record -> IMPLEMENTATION default; the context-incumbent fallback is deleted, killing audit P1-1 where a foreign READ bind imposed READ on another session)."
  - subject: { kind: code, ref: "dadaia_workspace/features/spec_context/lease.py#acquire" }
    change: "DELETE the blocking lease machinery: acquire()'s six-rung decision tree, LockHeldError, the O_EXCL sentinel CAS, adopt_if_own_lineage(), the by-session index, the incumbent pointer as an authority object, and the `lock steal` CLI verb. REPLACE with session presence: .dadaia/states/presence/<ctx>/<session>.json records (harness-native session id, runtime, long-lived pid, heartbeat) upserted on write, renewed by the existing PostToolUse hook, TTL-expired, GC'd by doctor — consumed ONLY by the advisory warning, the panel, and doctor. Simplicity is the acceptance bar: no adoption, no lineage probes, no steal, no rungs — a presence upsert can never fail another session's work. PI L1 extension gains presence parity: emits one stable unique session id + long-lived pid to BOTH pre- and post-tool hooks (fixes audit P1-4 and the PI anon-session facet of the CRITICAL bug — with no lease to corrupt, anon identity degrades presence accuracy only, and this fixes that too)."
  - subject: { kind: code, ref: "dadaia_workspace/features/chokepoints/service.py#pre_commit_decision" }
    change: "pre-commit becomes WARN-ONLY: pre_commit_decision() keeps its detection (another live session's presence on this context) but ALWAYS returns ALLOW, printing a clear advisory when concurrent mutation is detected (chokepoints/service.py:161-282 — the BLOCK verdict at the live-foreign rung is deleted; all WARN-allow degradation rungs collapse into the one advisory path). The pre-push security-verdict gate and CI preflight are UNTOUCHED — they gate quality, not concurrency. Zero commit blocks, zero write blocks: after this release NO path in dadaia-workspace can block an agent or operator because of another session."
  - subject: { kind: code, ref: "dadaia_workspace/features/spec_context/locking.py#_default_workspace_lock" }
    change: "the millisecond-bounded internal file locks STAY (operator-ratified): the 5s workspace lock serializing spec_contexts.json writes and the per-context lock serializing clone/remove are integrity-protecting critical sections invisible to users, per audit P3-1 — they must never grow into lifecycle-scoped locks. Folded platform-seam retirement applies here: replace the in-body sys.platform=='win32' checks in _default_workspace_lock/_default_context_lock and telemetry/service.py#_default_refresh_lock with PLATFORM.has_fcntl (supersedes backlog `platform-seam-todo-retirement`)."
---

# BACKLOG — Lock liberation: advisory presence replaces the blocking lease (P0)

**Priority: P0 — the operator's #1 mandate, REDEFINED.** Original framing (fix the
lease's identity model so blocking is correct) is REPLACED by the ratified doctrine:

> **Locks are not allowed.** Users stop using dadaia-workspace after experiencing
> locks. The trade-off between locks and race conditions is settled: races are
> accepted and *surfaced*; blocking is forbidden at any cost.

## The four ratified decisions (2026-07-10)

1. **Advisory presence** replaces the blocking lease — the signal survives (warning,
   panel, doctor), the block dies.
2. **Pre-commit is WARN-only** — detection kept, ALLOW always.
3. **Millisecond micro-locks stay** — registry-JSON/clone serialization is file
   integrity, not user-facing locking.
4. **READ mode survives, strictly self-scoped** — opt-in self-protection only; a
   foreign session's bind can never change your mode.

## Audit disposition mapping (audit-disposition law)

- **P0-1 (rebind self-block), P0-3 (six-identity reconciliation):** fixed by removal —
  with no blocking verdict there is nothing for a rotated identity to falsely block;
  the presence record uses the harness-native id with no adoption/reconciliation.
- **P0-2 (PI anon-session dual-writer):** the exactly-one-mutator guarantee is
  deliberately RETIRED (superseded by doctrine); the residual harm (presence/telemetry
  accuracy) is fixed by PI emitting a stable unique id.
- **P1-1 (foreign READ imposes mode):** fixed — mode resolution self-scoped.
- **P1-2 (PID reuse):** moot for blocking; presence-warning accuracy may optionally
  carry a start-token — decide in SPEC, LOW stakes now.
- **P1-3 (release not discoverable):** moot — nothing to release; presence expires by
  TTL and dies with the session.
- **P1-4 (PI heartbeat parity):** fixed — presence parity on both hooks.
- **P1-5 (TTL-only doctor GC):** fixed — one advisory liveness helper shared by
  gate/doctor/panel; GC of a presence record can no longer harm anyone.
- **P2-1 (CAS contention blocks):** moot — no acquisition CAS on the write path.
- **P2-2 (ACTIVE-based takeover):** moot — no takeover exists.
- **P3-1 (bounded file locks):** kept as-is by decision 3.

## Blast-radius notes for the SPEC

- The **frozen no-steal suite descendants** (v0.1.75 successor baseline rows covering
  lease/no-steal invariants) are RETIRED WITH the machinery they pin — an explicit
  QA-ship-gate-adjudicated re-baseline, never a silent drop. New invariant tests:
  presence upsert never raises; concurrent-session write always ALLOWS + warns once;
  pre-commit always allows; READ self-scope; PI unique ids.
- Surfaces reading lease state (panel, doctor, `context show`, lock-events audit log)
  repoint to presence records.
- `.dadaia/sessions/` PROTECTED class stays (session records remain lease-free
  identity/mode storage).
- Bug `layer1-rebind-adopts-lease-to-synthetic-session-self-block` is resolved with
  evidence = the removal diff + the new invariant tests + executed-path probes on all
  three L1 harnesses (bind -> write -> rebind -> write never blocks).
