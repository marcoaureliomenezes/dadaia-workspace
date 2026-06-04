# SPEC: v0.1.4.5 — gate-env-free-session-resolution

**Status:** Aprovado
**Release ID:** v0.1.4.5
**Owner:** product-engineer
**Created:** 2026-06-04

> CRITICAL deploy-blocker hotfix (R1 of FEAT-SESSION-SEMAPHORE-01). Minimal,
> surgical fix to SDD enforcement so the implement+review flow never dead-ends in
> a state whose only escape is relaunching the agent runtime. `pyproject` stays at
> `0.1.4`; no version bump. Lands before the parked v0.1.4.6 harness-mastery.

---

## 1. Objective

Eliminate the **env-as-channel** deploy-blocker in the SDD gate. Today
`sdd-spec-gate.sh` RULE E reads the active session identity **only** from the
`DADAIA_SESSION_ID` process environment variable. A running agent runtime cannot
inject that variable into its own (parent) environment, so any runtime launched
without the export is **hard-blocked from all production writes with no in-session
recovery** — the operator must relaunch the runtime. This breaks every real
multi-phase release.

This release makes the gate resolve the active session **from on-disk state** when
the env var is absent, using the implementation lock that `dadaia context bind`
already writes. Result: `dadaia context bind` from **any** shell — including an
in-session `! dadaia context bind …` — unblocks production writes with **no
relaunch, ever**.

This is the minimal R1 fix. The full per-context semaphore + PM-coordinated phase
progression (root causes #2–4) remains `FEAT-SESSION-SEMAPHORE-01` R2.

---

## 2. Problem and Context

Reproduced 2026-06-04 on release v0.1.4.6:

- `dadaia context bind dadaia-workspace --mode implementation --release v0.1.4.6`
  wrote a valid session (`.dadaia/sessions/<id>.json`, `mode:
  BOUND_IMPLEMENTATION`) and a valid lock
  (`.dadaia/locks/implementation/dadaia-workspace__v0.1.4.6.json`,
  carrying `session_id`, `release`, `mode`, `last_seen_at`, `ttl_seconds`).
- The running Claude Code runtime's environment was nonetheless empty
  (`DADAIA_SESSION_ID` unset), because a child process (Bash tool / hook) cannot
  inject env into the live parent runtime.
- `sdd-spec-gate.sh` RULE E Step 1 reads `DADAIA_SESSION_ID` from env only and
  fails closed: `[RULE E] DADAIA_SESSION_ID is not set.`
- Net: an approved release (ACTIVE = IMPLEMENTATION, TASKS Aprovado) could not be
  implemented without relaunching the runtime.

Root cause #1 of `specs/backlog/session-orchestration-semaphore.md`: there is no
runtime→session resolution that does not depend on the env var.

### Bootstrap note (break-glass)

The gate blocks writes to its own source (`dadaia_workspace/public/scripts/
sdd-spec-gate.sh` is a production path). Operator authorized a **one-time bash
break-glass** (2026-06-04) to land T-SEMA-01: the gate-source edit is applied via
a Bash command (not the Write/Edit tool, which the PreToolUse hook intercepts),
then projected via `dadaia public stage && dadaia public install`. This break-glass
is used exactly once, to fix the mechanism that would otherwise block its own fix.

---

## 3. Scope (in)

### SCOPE-01 — Env-free session resolution in `sdd-spec-gate.sh` RULE E

When `DADAIA_SESSION_ID` is **absent** from the environment, RULE E resolves the
active session from the **non-stale** implementation lock for the resolved context
(`.dadaia/locks/implementation/<context>__*.json`). The lock already records
`session_id`; the gate adopts it (and exports it for the rest of the hook run) and
proceeds with the existing staleness / mode / lock-ownership checks unchanged.

- A **stale** lock is never adopted (honors "avoid race at any cost").
- When the env var **is** present it still wins (backward-compatible).
- When the env var is absent **and** no non-stale lock exists, the gate blocks with
  a message that points to `dadaia context bind` **from any shell — no relaunch**.

Write target: `dadaia_workspace/public/scripts/sdd-spec-gate.sh`

### SCOPE-02 — Durable lock heartbeat in the gate's inline renewal

The gate's existing inline heartbeat (fired on every allowed write) currently
renews only the **session** file. Extend it to also renew the **implementation
lock** owned by that session (matched by `context__release` + `session_id`). This
keeps the lock non-stale across a long agent session so the SCOPE-01 fallback keeps
working between write bursts.

Write target: `dadaia_workspace/public/scripts/sdd-spec-gate.sh` (same file)

### SCOPE-B — RULE C marker-format compatibility (Bug B, operator-authorized expansion 2026-06-04)

Discovered while validating SCOPE-01 live: with a resolvable session the gate
reached RULE C and blocked, because its marker regex
`^[[:space:]]*-[[:space:]]*\[-\][[:space:]]+` only matches the inline form
`- [-] T-xxx`, while **every** real release writes `- **Status:** [-]`. RULE C
therefore never matched a real release marker — the gate had never gated a real
production write end-to-end. Broaden the regex to accept **both** forms:

```
GREP_PAT='^[[:space:]]*-[[:space:]]*(\*\*Status:\*\*[[:space:]]*)?\[-\]'
```

Still rejects `[ ]` and `[x]`; no trailing-space requirement (the Status form ends
the line at the marker). Backward-compatible with the gate's own test fixtures.

Write target: `dadaia_workspace/public/scripts/sdd-spec-gate.sh` (same file)

> **Bug C (deferred to R2):** `dadaia context heartbeat` renews the implementation
> lock but NOT the session file, while RULE E checks session staleness — so the
> documented idle keep-alive cannot keep a long session alive on its own. Mitigated
> for active work by the gate's inline heartbeat (SCOPE-02 now renews both on every
> allowed write). Full fix (make every renewal point renew both, or unify on one
> liveness record) belongs to the FEAT-SESSION-SEMAPHORE-01 R2 design.

### SCOPE-03 — Regression tests

In `tests/integration/test_gate_session_locks.py`:
- Update `AC-T13-1` (no session + **no lock** → still blocks; assert the new
  no-relaunch block reason).
- Add: env absent + **non-stale lock present** → write **ALLOWED** (env-free
  resolution; the core regression guard).
- Add: env absent + **stale lock** → **BLOCKED** (stale never adopted).
- Add: inline-heartbeat renews the lock `last_seen_at` (SCOPE-02).

Write target: `tests/integration/test_gate_session_locks.py`

### SCOPE-04 — Propagation

`dadaia public stage && dadaia public install --target all && dadaia public doctor`
(exit 0). The patched gate must be projected to `.dadaia/scripts/sdd-spec-gate.sh`
(the path the active hook references).

---

## 4. Out of Scope

- Per-context semaphore mutex, PM-coordinated phase progression, queueing,
  `dadaia doctor` lock invariants, migration — these are `FEAT-SESSION-SEMAPHORE-01`
  R2 (full design).
- `dadaia context bind` / CLI Python changes — the lock already carries
  `session_id`; no CLI change is required for R1.
- TTL/heartbeat TOCTOU hardening beyond SCOPE-02 (`r2-lock-toctou-hardening-v1`).
- The v0.1.4.6 harness-mastery release (parked; unblocked once R1 lands).
- Any version bump.

---

## 5. Constraints

- **Break-glass scope:** the Bash break-glass is authorized for the
  `sdd-spec-gate.sh` source edit only (SCOPE-01/02). All other writes go through
  normal tools under the (now-fixed) gate.
- **Backward compatibility:** existing RULE E behavior with `DADAIA_SESSION_ID`
  set must be unchanged. All pre-existing `test_gate_session_locks.py` assertions
  that set a session id must still pass.
- **Fail-safe, not fail-stop:** ambiguity (no non-stale lock) still blocks
  implement/review writes; read/spec and reports/tmp paths are unaffected.
- **Tests before push:** `pytest -q -p no:cacheprovider` green locally before any
  push.

---

## 6. Acceptance Criteria

- **AC-1:** With `DADAIA_SESSION_ID` unset, a non-stale implementation lock for the
  resolved context present, and a `[-]` task marker active, a production write is
  **ALLOWED** (gate adopts the lock's session). Proven by integration test + a live
  end-to-end write through the projected gate.
- **AC-2:** With `DADAIA_SESSION_ID` unset and **no** non-stale lock, the gate
  **blocks** with a message instructing `dadaia context bind` from any shell and
  explicitly stating no relaunch is required.
- **AC-3:** A **stale** lock is never adopted (env unset + stale lock → block).
- **AC-4:** With `DADAIA_SESSION_ID` set, RULE E behavior is byte-for-byte
  unchanged (all prior session-set tests pass).
- **AC-5:** The inline heartbeat renews the owning lock's `last_seen_at` on an
  allowed write (SCOPE-02 test passes).
- **AC-6:** `dadaia public doctor` exits 0; `.dadaia/scripts/sdd-spec-gate.sh`
  matches the patched source.
- **AC-7:** Full `pytest -q -p no:cacheprovider` passes (no regression).
- **AC-8:** code-reviewer + security-reviewer approve the same commit (enforcement
  core change — security pairing required).
- **AC-9 (SCOPE-B):** RULE C matches the canonical release marker form
  `- **Status:** [-]` (and still the inline `- [-] T-xxx` form), and still rejects
  `[ ]`/`[x]`. Proven by integration test + the live end-to-end write that
  succeeded against a real `- **Status:** [-]` TASKS.md.
