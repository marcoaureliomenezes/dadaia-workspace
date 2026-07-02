---
name: lease-kernel-identity-hardening
status: candidate
opened: 2026-07-01
owner: project-manager (curates)
source: audit 2026-07-01 specs/audits/_archive-pending 20260701T201136Z-0bcd6c19 (A-3, B/gate)
intents:
  - subject: { kind: code, ref: "dadaia_workspace/core/lock_liveness.py#is_stale" }
    change: "process-identity self-recognition: a holder whose recorded pid equals the acquiring session's harness pid RENEWs instead of raising LockHeldError (self-block root fix); pass veto-preserving None (never 'none') as active_release when ACTIVE.md is unreadable so an I/O failure cannot bypass the pid veto"
  - subject: { kind: code, ref: "dadaia_workspace/hooks/sdd_gate.py#_resolve_holder_pid" }
    change: "prefer the harness payload sid over inherited env sids in session-id resolution; add a rotated-sid regression test (same harness pid, new sid => RENEW, never self-block)"
  - subject: { kind: code, ref: "dadaia_workspace/features/spec_context/session_identity.py#coherence" }
    change: "SPEC-DOC-029 namespace-aware lease<->session coherence (resolve UUID vs sess_* ids via the by-session index before asserting forgery); --specs-dir doctor runs isolate workspace_state_dir; remove the dangling by-session index entry left by the .ptr-match RENEW branch"
---

# BACKLOG — Lease-kernel identity hardening

**Priority:** HIGH. Defers audit findings F-1 (HIGH self-block, empirically reproduced:
same recorded harness pid + rotated sid => LockHeldError against the holder's own live
process), F-3 (pid-veto bypassed when ACTIVE.md is unreadable), F-7 (dangling by-session
index entry), F-4 (SPEC-DOC-029 live-holder false forgery + --specs-dir state bleed).
Bugs deferred here: `gate-self-blocks-lease-holder-own-session`,
`spec-doc-029-false-forgery-harness-uuid-vs-session-record-id`.
