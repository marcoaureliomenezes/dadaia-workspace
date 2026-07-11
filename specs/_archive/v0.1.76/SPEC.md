# SPEC — Release v0.1.76 — Lock liberation (advisory presence)

**Status:** Aprovado
**Source:** backlog `20260710-lock-lease-session-identity-kernel` (P0); CRITICAL bug
`layer1-rebind-adopts-lease-to-synthetic-session-self-block`; P0 audit
`specs/audits/2026-07-10-lock-risk-audit-cross-harness.md`; NO-LOCKS DOCTRINE
(4 operator-ratified decisions, 2026-07-10 — recorded in `specs/backlog/candidates.md`).
Grill: 2026-07-10 lock-architecture research (full blocking-path map) + operator Q&A.

## Problem

The release-mutation lease produces both unacceptable failure modes: **false
exclusion** (a live legitimate holder self-blocks after rebind — CRITICAL bug, all
three L1 harnesses) and **false inclusion** (PI sessions collapse to `anon-session`).
The operator ratified that the lock↔race trade-off is settled product-side: a blocked
user is strictly worse than a rare, surfaced race. Blocking concurrency control is
removed; the signal survives as advisory presence.

## Doctrine (binding)

Races between sessions are ACCEPTED and SURFACED, never prevented. After this release
NO path in dadaia-workspace may block an agent or operator because of another session.
Quality gates (pre-push security verdict, CI preflight) and non-concurrency path-class
policy (PROTECTED/FROZEN/MEMORY-phase/READ-mode) are NOT locks and stay.

## FRs

- **FR1 — Gate never blocks on concurrency.** The MUTATING branch of
  `gate_policy.evaluate` no longer calls `lease.acquire()` and cannot emit a
  `LockHeldError` block. Instead it upserts a session presence record (never fails —
  any presence I/O error is swallowed, write ALLOWED) and, when another live session's
  presence exists on the same context, ALLOWS with a one-line advisory warning naming
  the other session (session id, runtime, heartbeat age), throttled to avoid warn-spam.
- **FR2 — Presence replaces the lease.** New module
  `features/spec_context/presence.py`: records at
  `.dadaia/states/presence/<ctx>/<session_id>.json` carrying
  `{session_id, runtime, pid, started_at, last_seen_at}`; upsert on MUTATING write;
  renewed by the existing PostToolUse hook; stale = heartbeat older than
  `LEASE_TTL_SECONDS` (reuse the tunable, renamed semantics: presence TTL); GC by
  doctor + opportunistic sweep on upsert. DELETE from `lease.py`: `acquire()` and its
  six-rung tree, `LockHeldError` blocking semantics, the O_EXCL sentinel CAS,
  `adopt_if_own_lineage()`, the by-session index, incumbent-pointer authority, and the
  `lock steal` CLI verb. `context release` deletes the session's own presence records
  (idempotent, no --session required — resolves from harness-native id when present).
- **FR3 — Pre-commit WARN-only.** `chokepoints.pre_commit_decision` keeps detection
  (another live session's presence on the context) but ALWAYS returns ALLOW; the
  live-foreign BLOCK verdict is deleted; on detection it prints one advisory line.
  Pre-push security-verdict gate and CI preflight untouched.
- **FR4 — Mode strictly self-scoped.** Mode resolution: `DADAIA_MODE` env → the
  session's OWN record → IMPLEMENTATION default. The context-incumbent `.ptr` fallback
  is deleted (kills audit P1-1). READ mode still blocks the session's own MUTATING
  writes (opt-in self-protection).
- **FR5 — PI presence parity.** The PI L1 extension emits a stable unique session id
  and long-lived pid to both pre- and post-tool hooks; `anon-session` never appears in
  a presence record (hook-side guard: anonymous identity gets presence-skipped, write
  still allowed).
- **FR6 — Platform seam.** `PLATFORM.has_fcntl` replaces the in-body
  `sys.platform == "win32"` checks in `locking.py#_default_workspace_lock`,
  `#_default_context_lock`, `telemetry/service.py#_default_refresh_lock`. The 5s
  micro-locks themselves stay (doctrine decision 3).
- **FR7 — Surfaces repoint.** Panel, doctor, `context show`, lock-events audit log,
  and preflight lease checks read presence instead of lease state. Lifecycle preflight
  `_check_lease` becomes presence-advisory (never a blocked reason). Doctor GC uses the
  one shared liveness helper.

## Acceptance

- **AC1 (CRITICAL-bug proof):** executed-path test: bind → MUTATING write → rebind
  (same and different mode) → MUTATING write → commit: NEVER blocked, on a workspace
  where the old flow self-blocked. Plus a two-live-session test: both sessions'
  MUTATING writes ALLOW; exactly one advisory warning each; no `anon-session` presence.
- **AC2:** grep-level: no `LockHeldError` raised anywhere in production; no
  `acquire(` blocking call sites; `lock steal` verb gone.
- **AC3:** pre-commit returns ALLOW in every scenario of its decision matrix (the old
  BLOCK rung's test flips to ALLOW+advisory).
- **AC4:** frozen no-steal descendant rows retired via explicit QA-adjudicated
  re-baseline (named in CLOSURE); successor invariants: presence upsert never raises;
  concurrent writes always allowed; READ self-scope; foreign bind never changes my mode.
- **AC5:** full suite green; `mypy --strict`; doctor 0 errors; per-sha security APPROVE
  on every push.
