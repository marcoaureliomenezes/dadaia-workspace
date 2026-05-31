# PLAN — Release: r2-lock-toctou-hardening-v1

**Status:** Aprovado
**Release ID:** r2-lock-toctou-hardening-v1
**Owner:** product-engineer
**Opened:** 2026-05-31

---

## 1. Strategy

Three focused, non-overlapping changes in two source files plus one test-file rewrite:

1. **locking.py** — fix the shared `.tmp` surface in three functions
   (`create_impl_lock`, `reclaim_impl_lock`, `renew_heartbeat`) and fix the STALE policy
   in `check_impl_xor_review`.
2. **context.py `bind()`** — wrap both check-then-act sequences (IMPLEMENTATION and REVIEW
   paths) inside `workspace_lock()` to make them atomic.
3. **test_kanban_lock_conflict.py** — rewrite AC-3.5 / AC-3.7 / AC-3.8 to assert the
   corrected behaviour; AC-3.1 / 3.2 / 3.3 / 3.4 / 3.6 are unchanged.

These three changes can be delivered as a single commit by one engineer. There are no
parallel work streams — the write sets partially overlap (T-1 covers both locking.py and
context.py) and the test rewrite (T-2) depends on T-1's fixed behaviour.

---

## 2. Execution order

```
T-1: Fix locking.py + context.py bind()
  └─► T-2: Rewrite AC-3.5 / 3.7 / 3.8 tests
        └─► T-3: Full-suite + gates validation (qa-engineer)
              └─► CLOSURE: PE updates context-management.html (one-line note, if OQ-1 = Option A)
```

Sequential. No parallel tasks — write sets are not disjoint (T-1 and T-2 both touch the
`features/spec_context/` surface; T-2 imports from T-1's fixed functions).

---

## 3. Per-task technical approach

### T-1 — Fix locking.py + context.py bind()

**Affected files:**
- `dadaia_workspace/features/spec_context/locking.py`
- `dadaia_workspace/cli/commands/context.py`

#### 3.1 STALE-blocks-review (Defect 1, locking.py)

In `check_impl_xor_review` REVIEW branch (currently @463):

```python
# BEFORE (buggy):
if state == LockState.HELD:
    ...raise ReviewBlockedByImplementationError(...)

# AFTER (fixed, Option A):
if state in (LockState.HELD, LockState.STALE):
    ...raise ReviewBlockedByImplementationError(
        f"Context '{context}' release '{release}' has an active implementation lock "
        f"(state={state}) held by session '{owner_id}'. "
        "Review cannot proceed. Reclaim or release the implementation lock first "
        "('dadaia context bind --mode implementation --force --reason ...' or "
        "'dadaia context release' in the owning session)."
    )
```

The existing error-message construction (reading the lock file for `owner_id`) applies to
both states. For `STALE`, `owner_id` is the session that owned the lock before it timed
out — still informative.

#### 3.2 Per-call UUID tmp names (Defect 3, locking.py — three sites)

Replace `lock_path.with_suffix(".tmp")` with a unique per-call tmp path at all three
sites: `create_impl_lock` (@271), `reclaim_impl_lock` (@361), `renew_heartbeat` (@630).

Pattern:

```python
import uuid  # add to locking.py imports

# Per-call unique tmp filename
tmp = lock_path.parent / f"{lock_path.stem}.{uuid.uuid4().hex}.tmp"
tmp.write_text(json.dumps(lock_data, indent=2))
os.replace(tmp, lock_path)
```

`uuid` is stdlib; no new dependency. The `os.replace` atomic rename is unchanged. If
`os.replace` fails (e.g. due to a concurrent winner already renaming the lock), the
exception path must remove the orphaned `.tmp` (AC-REG-5). Add a `try/except` around
`os.replace` that calls `tmp.unlink(missing_ok=True)` on failure.

#### 3.3 Atomic check-then-act in context.py bind() (Defect 2)

The IMPLEMENTATION path currently (context.py @338–@378):

```python
# CURRENT (has gap between check and workspace_lock):
check_impl_xor_review(workspace_root, name, release, "IMPLEMENTATION", session_id)
if force:
    reclaim_impl_lock(...)
else:
    with workspace_lock(workspace_root):
        create_impl_lock(...)
audit_acquired(...)
```

**Fixed:** move `check_impl_xor_review` inside the `workspace_lock` critical section:

```python
# FIXED (IMPLEMENTATION path):
if force:
    check_impl_xor_review(workspace_root, name, release, "IMPLEMENTATION", session_id)
    reclaim_impl_lock(...)  # reclaim is force-write; workspace_lock not required for atomicity here
else:
    with workspace_lock(workspace_root):
        check_impl_xor_review(workspace_root, name, release, "IMPLEMENTATION", session_id)
        create_impl_lock(...)
audit_acquired(...)  # non-critical; stays outside lock
```

The REVIEW path currently (context.py @380–@432):

```python
# CURRENT (entirely unguarded):
check_impl_xor_review(workspace_root, name, release, "REVIEW", session_id)
...
with workspace_lock(workspace_root):
    session_file.write_text(...)
```

**Fixed:** merge into one critical section:

```python
# FIXED (REVIEW path):
with workspace_lock(workspace_root):
    check_impl_xor_review(workspace_root, name, release, "REVIEW", session_id)
    session_file.write_text(json.dumps(session_data, indent=2))
```

The `audit_blocked` call in the `except ReviewBlockedByImplementationError` handler
remains outside the lock (same as for IMPLEMENTATION).

**Deadlock check (AC-REG-4):** The `workspace_lock` context manager uses `fcntl.flock`
with `LOCK_NB` poll. Python's `fcntl.flock` is per-fd, per-process: acquiring the same
lock a second time on a different fd succeeds (it is not re-entrant in the pthread sense).
The `bind()` function opens a new fd for each `workspace_lock()` call. As long as a
single `bind()` call path never enters two nested `workspace_lock()` blocks on the **same
file descriptor**, there is no deadlock. The implementer must verify this holds after the
change — the simplest verification is a code audit confirming that `workspace_lock()` is
not called inside the expanded `workspace_lock()` block.

---

### T-2 — Rewrite AC-3.5 / AC-3.7 / AC-3.8 tests

**Affected file:**
- `tests/unit/features/spec_context/test_kanban_lock_conflict.py`

Only the three K-QA-RACE test functions that document buggy behaviour are rewritten. The
AC-3.1 / 3.2 / 3.3 / 3.4 / 3.6 test functions are unchanged (they already assert correct
behaviour that survives the fix).

**AC-3.5 rewrite** — STALE impl lock blocks review:

```python
# BEFORE (documents the bug — STALE does NOT block):
# test asserts check_impl_xor_review does NOT raise for STALE

# AFTER (asserts the fix):
def test_impl_stale_blocks_review_until_reclaim(ws):
    # Create a STALE impl lock
    create_impl_lock(ws, context="ctx-a", release="rel-1",
                     session_id="sess_impl_stale", runtime="test", pid=99999)
    # Force the lock stale (expired ttl)
    lock_path = _impl_lock_path(ws, "ctx-a", "rel-1")
    data = json.loads(lock_path.read_text())
    data["last_seen_at"] = (datetime.now(tz=UTC) - timedelta(seconds=400)).isoformat()
    lock_path.write_text(json.dumps(data, indent=2))
    assert check_lock_state(ws, "ctx-a", "rel-1") == LockState.STALE

    with pytest.raises(ReviewBlockedByImplementationError):
        check_impl_xor_review(ws, "ctx-a", "rel-1", "REVIEW", "sess_review_stale")

    # After reclaim, review is unblocked
    reclaim_impl_lock(ws, context="ctx-a", release="rel-1",
                      new_session_id="sess_reclaim", runtime="test",
                      pid=os.getpid(), reason="test reclaim")
    release_impl_lock(ws, "ctx-a", "rel-1", "sess_reclaim")
    # Now REVIEW bind passes without raising
    check_impl_xor_review(ws, "ctx-a", "rel-1", "REVIEW", "sess_review_after")
```

**AC-3.7 rewrite** — XOR race: exactly one success:

```python
# AFTER: barrier race must yield exactly one success + one LockConflictError subclass
def test_r_impl_xor_review_only_one_binds(ws):
    barrier = threading.Barrier(2, timeout=5)
    results = {}

    def impl_bind():
        barrier.wait()
        try:
            _bind_impl(ws, "ctx-r", "rel-r", "sess_impl_r7")
            results["impl"] = "ok"
        except (LockHeldError, ReviewBlockedByImplementationError,
                ImplementationBlockedByReviewError) as e:
            results["impl"] = type(e).__name__

    def review_bind():
        barrier.wait()
        try:
            _bind_review(ws, "ctx-r", "rel-r", "sess_review_r7")
            results["review"] = "ok"
        except (LockHeldError, ReviewBlockedByImplementationError,
                ImplementationBlockedByReviewError) as e:
            results["review"] = type(e).__name__

    t1, t2 = threading.Thread(target=impl_bind), threading.Thread(target=review_bind)
    t1.start(); t2.start()
    t1.join(timeout=10); t2.join(timeout=10)

    successes = sum(1 for v in results.values() if v == "ok")
    assert successes == 1, f"Expected exactly 1 success, got: {results}"
```

**AC-3.8 rewrite** — two concurrent impl binds: loser raises LockHeldError, not FileNotFoundError:

```python
# AFTER: loser must raise LockHeldError (never FileNotFoundError)
def test_r_two_impl_sessions_race(ws):
    barrier = threading.Barrier(2, timeout=5)
    results = {}

    def impl_bind_1():
        barrier.wait()
        try:
            create_impl_lock(ws, "ctx-r2", "rel-r2", "sess_impl_r8a",
                             runtime="test", pid=os.getpid())
            results["t1"] = "ok"
        except LockHeldError:
            results["t1"] = "LockHeldError"
        except Exception as e:
            results["t1"] = type(e).__name__

    def impl_bind_2():
        barrier.wait()
        try:
            create_impl_lock(ws, "ctx-r2", "rel-r2", "sess_impl_r8b",
                             runtime="test", pid=os.getpid())
            results["t2"] = "ok"
        except LockHeldError:
            results["t2"] = "LockHeldError"
        except Exception as e:
            results["t2"] = type(e).__name__

    t1, t2 = threading.Thread(target=impl_bind_1), threading.Thread(target=impl_bind_2)
    t1.start(); t2.start()
    t1.join(timeout=10); t2.join(timeout=10)

    assert "ok" in results.values(), f"Expected one success: {results}"
    assert "LockHeldError" in results.values(), f"Expected LockHeldError for loser: {results}"
    assert "FileNotFoundError" not in results.values(), (
        f"Loser must not raise FileNotFoundError: {results}"
    )
```

Note: the `_bind_impl` helper in the test file calls `check_impl_xor_review` +
`create_impl_lock` **without** `workspace_lock`. For AC-3.7, the test is exercising
`context.py bind()` semantics; the test helper should be updated to wrap the sequence in
`workspace_lock` to mirror the fixed `bind()` behaviour, or the test can call the
real `bind()` CLI function via a subprocess/mock for end-to-end fidelity. The implementer
decides the appropriate level of coupling; the invariant tested must match what `bind()`
actually does after the fix.

---

### T-3 — Full-suite + gates validation (qa-engineer)

Run:
```
cd repos/dadaia-workspace
poetry run ruff check dadaia_workspace/ tests/
poetry run mypy --strict dadaia_workspace/ (161 files)
poetry run pytest -x -p randomly tests/
grep -r 'time\.sleep' tests/unit/features/spec_context/test_kanban_lock_conflict.py
```

Expected: 0 ruff errors, 0 mypy errors, 0 pytest failures, 0 `time.sleep` hits in the
race tests.

---

## 4. Risk register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Double-acquire deadlock in `bind()` after expanding `workspace_lock` scope | Low | High | AC-REG-4: code audit; implementer confirms before marking T-1 done |
| Orphaned `.uuid4.tmp` files if `os.replace` raises unexpectedly | Low | Medium | AC-REG-5: `try/except` with `tmp.unlink(missing_ok=True)` on all three sites |
| AC-3.7 rewrite: helper `_bind_impl` doesn't use `workspace_lock` → test passes pre-fix | Medium | Medium | Update helper OR call real `bind()` — implementer must ensure test validates the lock, not a bare sequence |
| Ruff/mypy strict: new `uuid` import in locking.py must satisfy `__all__` or import hygiene | Low | Low | Add `import uuid` alongside existing stdlib imports; mypy strict will flag any missed annotation |

---

## 5. Validation strategy

| Gate | Command | When |
|------|---------|------|
| Ruff lint | `poetry run ruff check dadaia_workspace/ tests/` | T-1 + T-2 done |
| Mypy strict | `poetry run mypy --strict dadaia_workspace/` | T-1 + T-2 done |
| Full pytest suite | `poetry run pytest -p randomly` | T-3 |
| No-sleep grep gate | `grep -r 'time\.sleep' tests/unit/features/spec_context/test_kanban_lock_conflict.py` → empty | T-3 |
| AC-3.5 passes | pytest `test_impl_stale_blocks_review_until_reclaim` | T-3 |
| AC-3.7 passes | pytest `test_r_impl_xor_review_only_one_binds` | T-3 |
| AC-3.8 passes | pytest `test_r_two_impl_sessions_race` | T-3 |
| AC-3.1..3.4, 3.6 no regression | All five tests still pass | T-3 |

---

## 6. Out of scope (PLAN level)

- No changes to `sdd-spec-gate.sh`, `public/` assets, or any lib-originated file.
- No `dadaia public stage` / `dadaia public install` step required (no lib-originated
  changes in this release).
- No panel or CLI command surface changes.
- Memory atom update (`context-management.html`) is a one-line CLOSURE deliverable only.

---

*Product Engineer — dadaia-workspace | 2026-05-31*
