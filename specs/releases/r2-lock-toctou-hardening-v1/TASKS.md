# TASKS — Release: r2-lock-toctou-hardening-v1

**Status:** Aprovado
**Release ID:** r2-lock-toctou-hardening-v1
**Owner:** product-engineer
**Opened:** 2026-05-31

> Gate note: Strictly sequential — T-2 depends on T-1 (tests assert fixed behaviour),
> T-3 depends on T-2 (full suite validation). Maximum one `[-]` at a time; tasks are
> NOT parallelisable (write sets overlap: T-1 and T-2 both touch `spec_context/`).
> OQ-1 (STALE policy) must be resolved (operator approves SPEC) before T-1 begins.
>
> CLOSURE note: After T-3 is `[x]`, product-engineer updates
> `specs/memory/product/context-management.html` during the CLOSURE phase to add
> a one-line note in the Impl-XOR-Review subsection reflecting the STALE-blocks-review
> semantics (if OQ-1 = Option A). No other memory atoms are affected.

---

## T-1 — Fix locking.py + context.py bind() atomicity

- **Owner:** software-engineer-python
- **Preconditions:** SPEC `**Status:** Aprovado` (OQ-1 resolved); PLAN `**Status:** Aprovado`
- **Write set:**
  - `repos/dadaia-workspace/dadaia_workspace/features/spec_context/locking.py`
  - `repos/dadaia-workspace/dadaia_workspace/cli/commands/context.py`
- **Done criterion:**
  - `check_impl_xor_review` REVIEW branch raises `ReviewBlockedByImplementationError` for
    both `HELD` and `STALE` lock states (Defect 1, if OQ-1 = Option A).
  - `create_impl_lock`, `reclaim_impl_lock`, and `renew_heartbeat` each use a per-call
    UUID-based tmp filename (`<lock_path>.<uuid4().hex>.tmp`) instead of the shared
    `lock_path.with_suffix(".tmp")` (Defect 3).
  - Each of the three tmp sites has a `try/except` around `os.replace` that calls
    `tmp.unlink(missing_ok=True)` on failure (AC-REG-5).
  - `bind()` IMPLEMENTATION path (normal, non-force): `check_impl_xor_review` +
    `create_impl_lock` are both inside a single `workspace_lock()` critical section
    (Defect 2).
  - `bind()` REVIEW path: `check_impl_xor_review` + session-file write are both inside a
    single `workspace_lock()` critical section (Defect 2).
  - `audit_acquired` and `audit_blocked` calls remain outside the lock.
  - Code audit confirms `bind()` does not double-acquire `workspace_lock` on the same fd
    anywhere (AC-REG-4); implementer documents this finding in the commit message.
  - `ruff check` and `mypy --strict` pass on the changed files.
- **Parallelism:** none; single task only.
- **Marker:** `[ ]`

---

## T-2 — Rewrite AC-3.5 / AC-3.7 / AC-3.8 tests + add race coverage

- **Owner:** software-engineer-python
- **Preconditions:** T-1 `[x]`
- **Write set:**
  - `repos/dadaia-workspace/tests/unit/features/spec_context/test_kanban_lock_conflict.py`
- **Done criterion:**
  - `test_impl_stale_blocks_review_until_reclaim` (AC-3.5) is rewritten to assert that a
    STALE impl lock raises `ReviewBlockedByImplementationError` on review bind, and that
    review succeeds after the impl lock is reclaimed and released.
  - `test_r_impl_xor_review_only_one_binds` (AC-3.7) is rewritten to assert that a
    `threading.Barrier(2)` race between one `_bind_impl` and one `_bind_review` yields
    **exactly one success and one `LockConflictError` subclass**. The `_bind_impl` helper
    (or a new helper) must wrap `check_impl_xor_review` + `create_impl_lock` inside
    `workspace_lock()` to mirror the fixed `bind()` behaviour.
  - `test_r_two_impl_sessions_race` (AC-3.8) is rewritten to assert that two concurrent
    `create_impl_lock` calls via `threading.Barrier(2)` yield exactly one success and one
    `LockHeldError` — never `FileNotFoundError`.
  - All threads in race tests are joined with a timeout (no hanging threads).
  - No `time.sleep` call exists in this file (CI grep gate: `grep -r 'time\.sleep'`).
  - AC-3.1 / AC-3.2 / AC-3.3 / AC-3.4 / AC-3.6 test functions are **unchanged** and
    still pass (no regression on previously-correct tests).
  - All 8 AC-3.x tests pass with 0 failures.
  - `ruff check` and `mypy --strict` pass on the changed file.
- **Parallelism:** none; sequential after T-1.
- **Marker:** `[ ]`

---

## T-3 — Full-suite + gates validation

- **Owner:** qa-engineer
- **Preconditions:** T-2 `[x]`
- **Write set:** `.dadaia/reports/dadaia-workspace/qa-engineer/` (QA report HTML)
- **Done criterion:**
  - `poetry run ruff check dadaia_workspace/ tests/` → exit 0, 0 errors.
  - `poetry run mypy --strict dadaia_workspace/` → exit 0, 0 errors (161 files clean).
  - `poetry run pytest -p randomly tests/` → 0 failed, full suite green.
  - `grep -r 'time\.sleep' tests/unit/features/spec_context/test_kanban_lock_conflict.py`
    → no output (no sleep calls in race tests).
  - All three rewritten tests (AC-3.5, AC-3.7, AC-3.8) pass.
  - All five unchanged tests (AC-3.1, AC-3.2, AC-3.3, AC-3.4, AC-3.6) pass.
  - QA handoff verdict: `APPROVED` in the emitted `.handoff.json` sidecar.
- **Parallelism:** none; sequential final task before CLOSURE.
- **Marker:** `[x]`

---

## Task summary

| Task ID | Owner | What | Preconditions | Marker |
|---------|-------|------|---------------|--------|
| T-1 | software-engineer-python | Fix locking.py + context.py bind() | SPEC+PLAN Aprovado | `[x]` |
| T-2 | software-engineer-python | Rewrite AC-3.5/3.7/3.8 tests | T-1 `[x]` | `[x]` |
| T-3 | qa-engineer | Full-suite + gates validation | T-2 `[x]` | `[x]` |

**Total: 3 tasks** — 2 software-engineer-python, 1 qa-engineer.

---

*Product Engineer — dadaia-workspace | 2026-05-31*
