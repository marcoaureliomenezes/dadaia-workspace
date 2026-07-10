---
name: lock-lease-session-identity-kernel
status: candidate
opened: 2026-07-10
owner: project-manager (curates)
priority: P0
source: "2026-07-10 remote-user CRITICAL bug `layer1-rebind-adopts-lease-to-synthetic-session-self-block` + P0 audit `specs/audits/2026-07-10-lock-risk-audit-cross-harness.md`; absorbs backlog `platform-seam-todo-retirement` (same locking surface, operator-ratified fold 2026-07-10)"
absorbs:
  - bug: layer1-rebind-adopts-lease-to-synthetic-session-self-block (CRITICAL, open)
  - audit: 2026-07-10-lock-risk-audit-cross-harness (P0-1, P0-2, P0-3, P1-1..P1-5, P2-1, P2-2, P3-1)
  - backlog: platform-seam-todo-retirement (superseded)
intents:
  - subject: { kind: code, ref: "dadaia_workspace/features/spec_context/lease.py#adopt_if_own_lineage" }
    change: "ONE canonical SessionIdentity as the sole holder identity across the whole lock kernel. Today six identifiers participate (CLI-minted sess_*, hook stdin session_id, harness env id, incumbent pointer, lease record holder, by-session index) and are reconciled after the fact — the root architectural condition behind the recurrence family (audit P0-3). Redesign: the harness-native id (when one exists) is the bound session id, pointer, adoption target, index key, heartbeat key, and release key; `context bind` may update context/mode/release but NEVER silently rotates session_id (kills P0-1: rebind mints sess_<uuid8> at context.py:428, adopt_if_own_lineage rewrites the native lease to it at lease.py:786, and the next hook self-blocks). Process provenance = long-lived harness pid + process-start token (pid alone is not identity — P1-2 PID-reuse). Non-blocking recovery contract per the audit: same identity renews; same process with rotated legacy id normalizes atomically once with audit trail; dead holder reclaims after TTL/terminal proof; live foreign yields with owner + deterministic clear condition; unknown/corrupt fails open for tools; anonymous identity can NEVER acquire or renew a mutating lease."
  - subject: { kind: code, ref: "dadaia_workspace/hooks/sdd_gate.py#evaluate_payload" }
    change: "prohibit anonymous acquisition (P0-2): the `anon-session` default (sdd_gate.py:264) must never reach lease.acquire() for a MUTATING write — PI L1 sends no session_id today, so two PI processes both mutate the same context as one 'holder' (reproduced live). The PI extension must emit one stable unique session id + long-lived pid to BOTH pre- and post-tool hooks (P1-4 heartbeat parity), plus a session-stop release event where the PI API supports it. Split CAS contention from live-foreign conflict (P2-1): distinct LeaseContentionError retried/failed-open at the hook boundary; only a proven live foreign mutator blocks. Mode resolution keyed to canonical session identity so a foreign READ bind can no longer impose READ on another session's write (P1-1)."
  - subject: { kind: code, ref: "dadaia_workspace/features/spec_context/lease.py#acquire" }
    change: "ONE liveness verdict consumed by gate, doctor pointer-GC, and pre-commit chokepoint (P1-5: doctor fix() TTL-only GC can delete a live holder's pointer today). Release becomes discoverable and automatic (P1-3): `context release` resolves from the current harness-native id without --session/DADAIA_SESSION_ID; idempotent; holder/owner/release surfaced in one diagnostic command. Closure explicitly releases the old lease before advancing ACTIVE so release-aware reclaim can't override a live pid via ACTIVE.md edit alone (P2-2). Acceptance rides the audit's mandatory matrix: 10 harness-parity scenarios × {Codex, Claude Code, PI}, identity set-equality assertions after every transition, and the negative-safety set (no anon lease record, two PI sessions never share an id, live foreign never stolen, dead holder never needs manual steal, PID reuse never preserves a lease, CAS contention never a live-foreign block). Real interactive executed-path probes on all three L1 harnesses — direct unit tests are insufficient at this boundary (audit law)."
  - subject: { kind: code, ref: "dadaia_workspace/features/spec_context/locking.py#_default_workspace_lock" }
    change: "folded platform-seam retirement (supersedes backlog `platform-seam-todo-retirement`): replace the in-body sys.platform == 'win32' checks carrying stale TODOs in _default_workspace_lock + _default_context_lock, and in telemetry/service.py#_default_refresh_lock, with the PLATFORM.has_fcntl capability flag (container.py's sole authorized platform gate). Rides inside this redesign because the lock kernel rewrite touches these exact factories anyway — one frozen-suite adjudication instead of two. The short bounded file locks themselves (5s workspace/context locks) stay narrow per audit P3-1 — they are NOT the incident and must never become release-lifetime locks."
---

# BACKLOG — Lock/lease/session-identity kernel redesign (P0)

**Priority: P0 — the operator's #1 mandate.** The current release lease is not
operationally safe: it exhibits BOTH unacceptable failure modes at once —
**false exclusion** (a legitimate live holder permanently self-blocks after rebind:
CRITICAL bug, all three L1 harnesses) and **false inclusion** (all PI sessions collapse
to the shared `anon-session` identity, so two live PI processes mutate the same context
concurrently). Root condition: session identity has no single owner at runtime; six
identifiers are reconciled by after-the-fact heuristics (audit P0-3).

**Non-negotiable invariant (audit):** no stale, synthetic, ambiguous, or same-process
identity may block useful work. Only a proven different live mutator may yield, and that
yield clears automatically and deterministically. Every block names the canonical
holder, runtime, process generation, context, release, and the condition that clears it.

**Also evaluate (audit "prefer scoped work"):** narrowing the context-lifetime lease to
deterministic phase boundaries with automatic release after each mutating workflow —
an idle TUI process should not remain a PID-vetoed holder indefinitely.

**Exit criteria = the audit's "locks mitigated" list**, headlined by: zero confirmed
self-blocks on any supported L1 harness; no anonymous or shared holder identity; no
manual lock steal anywhere in normal recovery; one identity model + one liveness verdict
across gate/doctor/chokepoints.

**Disposition note:** resolving this entry dispositions the CRITICAL bug
`layer1-rebind-adopts-lease-to-synthetic-session-self-block` and every P0/P1/P2 finding
of `specs/audits/2026-07-10-lock-risk-audit-cross-harness.md` (audit-disposition law:
each finding gets fixed/superseded/deferred-with-reason; the audit archives only when
fully dispositioned and the disposing release is approved).
