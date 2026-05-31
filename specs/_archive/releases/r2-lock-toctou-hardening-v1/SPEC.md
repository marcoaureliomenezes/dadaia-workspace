# SPEC — Release: r2-lock-toctou-hardening-v1

**Status:** Aprovado
**Release ID:** r2-lock-toctou-hardening-v1
**Owner:** product-engineer
**Opened:** 2026-05-31
**Semver target:** patch (bug-fix only; no new schema version, no new public API)
**Sequencing:** Standalone. No hard external dependency. Can be activated immediately
after `ACTIVE.md` is free.

---

## 1. Problem and context

Three pre-existing defects in the R2 (`spec-context-session-locks-v1`) locking layer were
surfaced by the barrier-based race tests (`K-QA-RACE`, AC-3.5 / AC-3.7 / AC-3.8) written
during R3 (`panel-kanban-v1`). Those tests were filed with the **explicit intent to document
the bugs** — they assert the *currently broken* behaviour and are therefore themselves incorrect
for a corrected system. This release fixes the three defects and rewrites those tests to assert
the correct, hardened behaviour.

**Source material consumed:**
- Backlog candidate: `specs/backlog/r2-lock-toctou-hardening-v1.md`
- Source: `dadaia_workspace/features/spec_context/locking.py` (inspected; key sites at @219,
  @271, @361, @441, @463, @630)
- Source: `dadaia_workspace/cli/commands/context.py` (inspected; `bind()` at @260)
- Tests: `tests/unit/features/spec_context/test_kanban_lock_conflict.py` (AC-3.5, AC-3.7,
  AC-3.8 assert buggy behaviour; must be rewritten)

### Defect 1 — STALE impl lock does not block review bind

`check_impl_xor_review` (locking.py @441) only raises `ReviewBlockedByImplementationError`
when the impl-lock state is `HELD`. When the state is `STALE` (heartbeat timed out or
owning PID dead), the check passes silently and the review bind proceeds. A STALE lock means
an implementation session likely died mid-work; allowing review to race over a half-done
implementation violates the Impl-XOR-Review invariant.

- **Location:** `locking.py:check_impl_xor_review` @463 — `if state == LockState.HELD`
- **Observed:** AC-3.5 (`test_impl_stale_blocks_review_until_reclaim`) asserts the wrong
  outcome (STALE does NOT block); will be rewritten.

### Defect 2 — check_impl_xor_review TOCTOU window

`check_impl_xor_review` is a **check-then-act** sequence: it reads the lock state, decides
whether to raise, and returns. The actual lock acquisition (impl) or session-file write
(review) happens in a separate call. Under concurrent load, two threads can both pass the
check before either acquires, allowing one IMPLEMENTATION bind and one REVIEW bind to both
succeed on the same release.

In the current `bind()` code (context.py @342–@432):
- IMPLEMENTATION path: `check_impl_xor_review` → (outside lock) → `workspace_lock` →
  `create_impl_lock`. The check runs **before** the workspace lock is held.
- REVIEW path: `check_impl_xor_review` → (outside any lock) → `_write_review_session`.
  The check and the write are entirely unguarded.

- **Location:** `locking.py:check_impl_xor_review` + callers in `context.py bind()`
- **Observed:** AC-3.7 (`test_r_impl_xor_review_only_one_binds`) with `threading.Barrier(2)`
  demonstrates the race; test asserts the wrong outcome.

### Defect 3 — create_impl_lock shared `.tmp` filename raises wrong exception

`create_impl_lock` (locking.py @271) and the analogous sites in `reclaim_impl_lock` (@361)
and `renew_heartbeat` (@630) use a **shared** tmp filename: `lock_path.with_suffix(".tmp")`.
When two threads race on the same release, the loser finds the `.tmp` already renamed by the
winner and raises `FileNotFoundError` (from `os.replace`) instead of `LockHeldError`. Callers
that catch `LockHeldError` to signal "already locked" will not see this race manifest cleanly.

- **Location:** `locking.py:create_impl_lock` @271; also `reclaim_impl_lock` @361 and
  `renew_heartbeat` @630
- **Observed:** AC-3.8 (`test_r_two_impl_sessions_race`) documents the wrong exception.

---

## 2. Objective

Fix all three defects in one focused patch release with zero schema or API changes:

1. Make the XOR check-then-act sequence atomic by wrapping it (and the subsequent
   create/write call) inside `workspace_lock()` for both IMPLEMENTATION and REVIEW bind
   paths in `context.py bind()`.
2. Eliminate the shared `.tmp` collision by using a **per-call unique tmp filename** (e.g.
   `<lock_path>.<uuid4>.tmp`) in `create_impl_lock`, `reclaim_impl_lock`, and
   `renew_heartbeat`.
3. Enforce the STALE-blocks-review policy in `check_impl_xor_review` by treating `STALE`
   the same as `HELD` in the REVIEW branch.
4. Rewrite the three K-QA-RACE tests (AC-3.5 / AC-3.7 / AC-3.8) to assert the corrected
   behaviour.

---

## 3. Open questions

### OQ-1 — STALE-blocks-review policy — RESOLVED 2026-05-31: **Option A** (operator)

> **RESOLUTION (operator, 2026-05-31): Option A — STALE blocks review until explicit reclaim.**
> `check_impl_xor_review` treats `STALE` the same as `HELD` in the REVIEW branch. AC-STALE-1 is active.

**Question:** When a review bind is attempted and the impl lock state is `STALE`, should
the review be blocked (requiring explicit reclaim first) or allowed (treating STALE as
equivalent to FREE)?

**Option A — STALE blocks review (RECOMMENDED):**
`check_impl_xor_review` raises `ReviewBlockedByImplementationError` for both `HELD` and
`STALE` impl lock states. The reviewer must wait for either:
  - the impl owner to run `dadaia context release` (clean exit), or
  - the operator to run `dadaia context bind --mode implementation --force --reason "..."` 
    (explicit reclaim), after which the lock transitions to FREE/HELD-by-new-session.

Rationale: A STALE impl lock indicates the implementation session died mid-work. An
implementation may have left the release in an inconsistent state (partially committed
tasks, in-progress writes). Letting a review proceed over that risks a reviewer certifying
a half-done implementation. The `--force` reclaim path already exists (R2 infrastructure)
and is the documented recovery procedure. This option preserves the Impl-XOR-Review
invariant in the strongest possible sense and matches the R2 design intent.

**Option B — STALE is treated as FREE (auto-allow review):**
`check_impl_xor_review` only blocks for `HELD`. A `STALE` impl lock is silently ignored
and review proceeds. Simpler UX — reviewer is not blocked by a dead session. Weaker
guarantee: a STALE lock might reflect only a transient heartbeat hiccup (e.g. the impl
agent was temporarily paused); review would proceed over a transiently stale but
substantively active implementation.

**PE recommendation:** Option A. The `--force` reclaim is a low-friction operator action.
The risk of a reviewer certifying a half-complete implementation outweighs the friction
of requiring an explicit reclaim for a stale lock.

**Acceptance criterion (if Option A is chosen):** AC-STALE-1 — after fix, a STALE impl
lock raises `ReviewBlockedByImplementationError` on a review bind attempt, with an error
message that names the stale session and instructs the operator to reclaim.

**Acceptance criterion (if Option B is chosen):** The existing AC-3.5 assertion (STALE
does NOT block) remains correct. Defect 1 is not a defect; only Defects 2 and 3 are fixed.

> Operator: please approve Option A or Option B before implementation begins. This is the
> only design-level decision in this release; all other fixes are unambiguous.

---

## 4. Product deltas

| Component | Delta |
|-----------|-------|
| `locking.py:check_impl_xor_review` | Treat `STALE` same as `HELD` in REVIEW branch (if OQ-1 = Option A) |
| `locking.py:create_impl_lock` | Replace shared `.tmp` with per-call UUID-based tmp filename |
| `locking.py:reclaim_impl_lock` | Same per-call UUID tmp fix (same pattern, same defect) |
| `locking.py:renew_heartbeat` | Same per-call UUID tmp fix (same pattern, same defect) |
| `context.py:bind()` — IMPLEMENTATION path | Wrap `check_impl_xor_review` + `create_impl_lock` inside `workspace_lock()` (single critical section) |
| `context.py:bind()` — REVIEW path | Wrap `check_impl_xor_review` + session-file write inside `workspace_lock()` (single critical section) |
| `test_kanban_lock_conflict.py` — AC-3.5 | Rewrite to assert `ReviewBlockedByImplementationError` on STALE (Option A) |
| `test_kanban_lock_conflict.py` — AC-3.7 | Rewrite to assert exactly one success + one `LockConflictError` subclass from barrier race |
| `test_kanban_lock_conflict.py` — AC-3.8 | Rewrite to assert loser raises `LockHeldError` (never `FileNotFoundError`) |

---

## 5. Architecture deltas

No new modules, no new public API, no new schema version. All changes are within
existing functions in two files.

The `workspace_lock()` context manager (Lock 1, fcntl) already exists at locking.py @104.
This release expands its usage scope in `context.py bind()` to cover the check-then-act
pair — this is an additive application of existing infrastructure, not a new primitive.

**Deadlock guard:** The IMPLEMENTATION path in `bind()` already wraps `create_impl_lock`
in `workspace_lock` (context.py @361). The expanded critical section must cover
`check_impl_xor_review` as well. The implementer must verify that `bind()` does not already
hold `workspace_lock` at the call site before entering the expanded section (i.e., no
double-acquisition of the fcntl lock on the same fd). The audit `audit_acquired` call
(context.py @371) is non-critical and must remain **outside** the lock.

For the REVIEW path, `bind()` currently does not hold `workspace_lock` at the XOR check
site (@385). The session-file write at @430 uses a separate `workspace_lock` block. The
expanded critical section must wrap both XOR check and session-file write as a single
atomic unit.

---

## 6. Tech-stack deltas

No new PyPI dependencies. `uuid` is stdlib (already imported in `context.py`). The
`uuid4()` call for per-call tmp names is added to `locking.py` (stdlib import, no new
dependency).

---

## 7. Security and operations deltas

No new attack surface. The change narrows the race window (reduces exposure) and makes
error semantics deterministic. No network access, no credential handling, no new file
paths.

Unique tmp filenames (`<lock_path>.<uuid4>.tmp`) are always cleaned up by `os.replace`
(winner) or by the exception path if `os.replace` fails before the rename. The
implementation must ensure no orphaned `.tmp` files are left on failure paths.

---

## 8. Memory files affected at CLOSURE

- `specs/memory/product/context-management.html` — add one-line note in the
  Impl-XOR-Review subsection: STALE impl locks block review until reclaimed (if OQ-1 =
  Option A). No other content change; this is a one-line semantic clarification.

All other memory atoms are unaffected — no architecture change, no new tech-stack
dependencies, no new features.

---

## 9. Acceptance criteria

### AC-STALE-1 (Defect 1 — requires OQ-1 = Option A)
After fix, a review bind attempted against a STALE impl lock raises
`ReviewBlockedByImplementationError`. The error message names the stale session and
instructs the operator to reclaim. AC-3.5 in `test_kanban_lock_conflict.py` must be
rewritten to assert this behaviour.

### AC-XOR-1 (Defect 2 — TOCTOU)
Two threads racing on `_bind_impl` and `_bind_review` for the same context/release via
`threading.Barrier(2)` yield **exactly one success and one `LockConflictError` subclass**
— never two successes. AC-3.7 in `test_kanban_lock_conflict.py` must be rewritten to
assert this. (`LockConflictError` is the common base; acceptable subtypes include
`LockHeldError`, `ReviewBlockedByImplementationError`, `ImplementationBlockedByReviewError`.)

### AC-TMP-1 (Defect 3 — shared `.tmp`)
Two concurrent `create_impl_lock` calls on the same context/release via
`threading.Barrier(2)` yield **exactly one success and one `LockHeldError`** — the loser
never raises `FileNotFoundError`. AC-3.8 in `test_kanban_lock_conflict.py` must be
rewritten to assert this.

### AC-REG-1 (no regression)
Full pytest suite green (0 failed). `ruff` and `mypy --strict` clean (161 files). No new
failures in AC-3.1, AC-3.2, AC-3.3, AC-3.4, AC-3.6 (those tests assert behaviour that
is already correct and must continue to pass).

### AC-REG-2 (test hygiene)
No `time.sleep` call in any race test (CI grep gate). All threads joined with timeout
(no hanging threads). Test outcomes are order-independent (pytest-randomly compatible).

### AC-REG-3 (no schema version bump)
No change to session file schema, no change to impl lock file schema, no change to any
public Python API (function signatures in `locking.py` are unchanged).

### AC-REG-4 (deadlock-free)
`bind()` does not double-acquire `workspace_lock` on the same fd. Implementer must verify
and confirm in the CLOSURE.md validation evidence.

### AC-REG-5 (no orphaned .tmp files)
On any exception path inside the expanded `workspace_lock` critical section, no
`<lock_path>.<uuid4>.tmp` file is left on disk. Either `os.replace` succeeded (tmp gone
into the target) or the tmp file is cleaned up in the except/finally path.

---

## 10. Out of scope

- `reclaim_impl_lock` deadlock semantics with the workspace lock: `reclaim_impl_lock` does
  **not** need to be wrapped in `workspace_lock` for the TOCTOU fix because reclaim is
  force-write by definition (it always overwrites). The per-call UUID tmp fix applies there
  only for the `FileNotFoundError` surface, not for XOR atomicity.
- Heartbeat renewal (`renew_heartbeat`) TOCTOU: heartbeat is idempotent and its stale
  window is acceptable per R2 design decision (locking.py @608 comment). Only the UUID
  tmp fix applies to `renew_heartbeat`, not workspace lock wrapping.
- Any changes to the Kanban view, panel, or any non-locking code.
- Any changes to `specs/memory/` atoms other than the one-line CLOSURE note in
  `context-management.html`.
- New session file fields or any schema version bump.

---

## 11. Dependencies and risks

### 11.1 Dependencies

No hard external release dependency. This release can be activated as soon as `ACTIVE.md`
is free.

### 11.2 Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Deadlock: `bind()` already holds `workspace_lock` at the expanded call site | Low | High | AC-REG-4: implementer must audit all `bind()` call paths and confirm no prior `workspace_lock` acquisition before the expanded section. |
| Orphaned `.tmp` files on exception paths inside the critical section | Low | Medium | AC-REG-5: explicit cleanup in except/finally; test with forced exception injection if needed. |
| Unique tmp names cause `ls` noise in `.dadaia/locks/implementation/` | Low | Low | Filenames use `.tmp` extension; lock layer ignores non-`.json` files. |
| Rewriting AC-3.7/3.8 to use real `workspace_lock` may slow tests (fcntl on tmp_path) | Low | Low | Barrier-based tests already touch the real FS; fcntl overhead on tmp_path is negligible. |

---

*Product Engineer — dadaia-workspace | 2026-05-31*
