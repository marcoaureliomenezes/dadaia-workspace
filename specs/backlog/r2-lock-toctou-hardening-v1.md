# Backlog Candidate — r2-lock-toctou-hardening-v1

**Owner:** software-engineer-python
**Surfaced by:** panel-kanban-v1 K-QA-RACE tests (AC-3.1..3.8)
**Affected module:** `dadaia_workspace/features/spec_context/locking.py`
**Status:** Candidate (not approved for any release)

## Problem

Three pre-existing defects in the `spec-context-session-locks-v1` (R2) locking layer
were exposed when K-QA-RACE wrote barrier-based race tests against the real
`JsonContextStore` on `tmp_path`. R3 (panel-kanban-v1) only reads session files for
display — it did not introduce these defects.

### Defect 1 — STALE impl lock does not block review bind

`check_impl_xor_review` only raises `ReviewBlockedByImplementationError` when the impl
lock state is `HELD`. A `STALE` impl lock (session dead, heartbeat timed out) passes
the check silently and allows a review bind to proceed. This violates the intended
semantics: a STALE impl lock should still block review until reclaimed by the operator.

- **Location:** `locking.py:check_impl_xor_review`
- **Observed:** AC-3.5 (`test_impl_stale_blocks_review_until_reclaim`) asserts the
  real behaviour (STALE does NOT block); the test documents but does not fix this.

### Defect 2 — `check_impl_xor_review` TOCTOU window

`check_impl_xor_review` is a check-then-act sequence: it reads lock state, decides
whether to raise, and returns. The actual lock acquisition happens in a separate call.
Under concurrent load, two threads can both pass the check before either acquires,
allowing both an impl and a review bind to succeed on the same release.

- **Location:** `locking.py:check_impl_xor_review` + callers in `create_impl_lock` /
  `create_review_lock`
- **Observed:** AC-3.7 (`test_r_impl_xor_review_only_one_binds`) with
  `threading.Barrier(2)` demonstrates the race; the test asserts the real (flawed)
  outcome.

### Defect 3 — `create_impl_lock` shared `.tmp` filename raises wrong exception

`create_impl_lock` uses a shared `.tmp` filename for the atomic rename pattern. When
two threads race on the same release, the losing thread finds the `.tmp` already gone
(renamed by the winner) and raises `FileNotFoundError` instead of `LockHeldError`.
Callers that catch `LockHeldError` will therefore see the race manifest as an unexpected
`FileNotFoundError`.

- **Location:** `locking.py:create_impl_lock`
- **Observed:** AC-3.8 (`test_r_two_impl_sessions_race`) documents the real exception
  raised.

## Proposed remediation

1. **Lock-1 (workspace flock) wrapping of the XOR check-then-act:** wrap the
   `check_impl_xor_review` + `create_*_lock` sequence in a single critical section
   guarded by the workspace-level fcntl lock (`.dadaia/states/.ws_lock`). This makes
   the check-then-act atomic with respect to the file system.

2. **Per-thread `.tmp` names in `create_impl_lock`:** replace the shared
   `<lock_path>.tmp` with a per-call unique tmp name (e.g.
   `<lock_path>.<uuid4>.tmp`) to eliminate the `FileNotFoundError` race condition.
   The atomic `os.rename` semantics still hold; the tmp file is unique per attempt.

3. **STALE-blocks-review semantics:** decide policy (STALE should block, require
   reclaim) and enforce it in `check_impl_xor_review` by treating `STALE` the same
   as `HELD` for the XOR check.

## Notes

- This candidate does not require a new schema version for session files.
- Existing K-QA-RACE tests (AC-3.5, AC-3.7, AC-3.8) will need to be updated to assert
  the corrected behaviour once the defects are fixed.
- The workspace flock (`.dadaia/states/.ws_lock`) already exists (R2 infrastructure);
  the fix wraps the XOR pair inside it — no new primitives needed.
