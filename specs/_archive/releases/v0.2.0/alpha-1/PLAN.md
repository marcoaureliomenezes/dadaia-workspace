# PLAN: v0.1.6 — State model (locks, race conditions, deadlocks)

**Status:** Em revisão
**Release ID:** v0.1.6
**Milestone within:** v0.2.0
**Owner:** product-engineer
**Created:** 2026-06-06

---

## Strategy

Replace four desynchronized lock stores with one cross-platform JSON TTL-lease record
and collapse the 1050-line gate to ≤175 lines. Execution order is dependency-strict:
the pure `core/` predicate comes first (no I/O dependencies); the `lease.py` I/O
module depends on it; all deletion and gate work depends on `lease.py` being green
before anything is torn out.

**Branch:** `feature/0.2.0` (all v0.1.6 commits land here).

**Commit discipline:** the gate-path migration from `*.semaphore.json` → `*.lock.json`
must be ONE atomic commit that updates both `lease.py` and `sdd-spec-gate.sh`. No
half-state window is acceptable.

---

## Module map

### New: `dadaia_workspace/core/` — `is_stale` predicate

**Purpose:** pure model layer; zero I/O; injectable seams for all time/process/session
checks. This is the only place `(now − heartbeat) ≤ ttl` is evaluated.

**Public surface:**
```python
def is_stale(
    data: dict | None,
    *,
    clock: Callable[[], datetime] = _utcnow,
    pid_probe: Callable[[int], bool] | None = None,   # not used; kept for sig compat
    session_exists: Callable[[str], bool] | None = None,
) -> bool: ...
```

Rules encoded:
- `data is None` → stale (no record → treat as absent → acquirable)
- `data` missing required fields (corrupt) → stale, logged as WARN
- `(clock() - parse(data["heartbeat"])).total_seconds() > data["ttl"]` → stale
- Otherwise → not stale

`pid_probe` parameter accepted but not used (OQ-1: no PID). Present for injection
signature compatibility only. `session_exists` may be used to fast-path an existing
holder's identity check.

**Layer rule:** `core/` imports stdlib only. Zero `features/` or `infrastructure/`
imports. DI via parameter injection, not module-level globals.

---

### New: `dadaia_workspace/features/spec_context/lease.py`

**Purpose:** single-record I/O module; wraps `is_stale` from `core/`; owns the
`ctx_locks/` directory.

**Public surface (~120 lines):**

| Function | Signature | Notes |
|---|---|---|
| `acquire(workspace, ctx, session_id, release, mode)` | raises `LockHeldError` on live conflict | O_EXCL CAS via sentinel file; heals stale inline |
| `renew_heartbeat(workspace, ctx, session_id)` | no-op if not held by session_id | `os.replace` atomic write |
| `release(workspace, ctx, session_id)` | no-op if not held by session_id | deletes file + audit entry |
| `is_held(workspace, ctx)` | `-> bool` | pure read; no mutation |
| `read_record(workspace, ctx)` | `-> dict \| None` | pure read; returns None if absent or corrupt |

**Lock dir:** `.dadaia/states/ctx_locks/`, created `0700` on first use.

**Sentinel file:** `.dadaia/states/ctx_locks/<ctx>.lock.sentinel` — created with
`open(path, 'x')`, deleted in `finally`. `FileExistsError` → exponential backoff
retry (max 3, initial 0.1 s).

**Sentinel orphan GC (F-06):** at the start of `acquire()`, before attempting
`open(sentinel_path, 'x')`, check: if sentinel exists and its mtime is older than 30 s,
unlink it (missing_ok=True) and proceed. This prevents a permanent deadlock if the
process was killed between CAS and unlink (SIGKILL cannot run `finally`).

**Path safety:** `context` and `session_id` validated against `re.fullmatch(r'[A-Za-z0-9_-]+', value)` before path construction. Raises `ValueError` on violation.

**Audit:** `acquire`, `release`, and `steal` each append one JSON line to
`.dadaia/logs/lock-events.jsonl` via `open(path, 'a')` (POSIX O_APPEND, atomic
under PIPE_BUF). `renew_heartbeat` does NOT audit (too frequent).

**Injectable clock:** `acquire` and `renew_heartbeat` accept optional
`clock: Callable[[], datetime] = _utcnow`. All TTL comparisons delegate to
`is_stale(data, clock=clock)`.

**`_before_write` hook:** a module-level `Optional[Callable[[], None]]` attribute
`_before_write = None`. `acquire()` calls `_before_write()` immediately after the
sentinel CAS succeeds and before writing the record. Used only in tests to simulate
TOCTOU interleaving. Never set in production.

**Teardown safety (F-11):** module import includes `assert _before_write is None or os.environ.get("DADAIA_TESTING") == "1"` at load time. Test fixtures that set `_before_write` MUST restore it to `None` via `monkeypatch` (not manual reset) — `monkeypatch` teardown is guaranteed even on test failure, preventing a dangling hook from corrupting subsequent tests in the same process.

---

### Modified: `dadaia_workspace/features/spec_context/locking.py`

**Change:** delete Lock-3 functions. Keep Lock-1/Lock-2 fcntl wrappers exactly as-is.

**Functions deleted (~346 lines):**
- `create_impl_lock`
- `release_impl_lock`
- `reclaim_impl_lock`
- `check_lock_state`
- `has_implementation_lock`
- `find_review_sessions`
- `_session_is_stale`
- `LockState` (enum)
- `check_impl_xor_review`

**Functions kept (untouched):**
- `workspace_lock` (fcntl Lock-1)
- `context_lock` (fcntl Lock-2)
- All their helpers, imports, and tests

**Verification:** `ruff check dadaia_workspace/features/spec_context/locking.py` must
pass after deletion (zero dead imports from removed functions).

---

### Retired: `dadaia_workspace/features/spec_context/semaphore.py`

**Change:** file deleted. Three good primitives migrated:
- `_atomic_write` → replaced by `os.replace` usage directly in `lease.py`
- TTL check logic → migrated to `is_stale` in `core/`
- `_is_pid_alive` → dropped entirely (OQ-1: no PID)

All `semaphore.py` imports in `service.py`, `doctor.py`, `context.py`, and gate must
be removed before this deletion.

---

### Modified: `dadaia_workspace/features/spec_context/service.py`

**Changes:**
1. Remove call to `acquire_context_semaphore` from `context bind` path.
2. Add lease GC call on `context_show(ctx)` and `context_list()`: if
   `is_stale(read_record(workspace, ctx))` → delete record (inline, no CAS needed
   for GC — only the holder acquires, GC only deletes stale).
3. Lease acquisition is NOT triggered by `service.py`. The gate shell script is the
   SINGLE acquisition point: on every MUTATING write it calls `$PYTHON_BIN -m
   dadaia_workspace.features.spec_context.lease acquire ...`. `service.py` does not
   call `acquire()` — it only uses `read_record` for GC purposes on show/list.

---

### Modified: `dadaia_workspace/features/spec_context/doctor.py`

**Changes:**
1. Collapse LOCK-2 through LOCK-7 invariant checks into one single-record check:
   - `ctx_locks/<ctx>.lock.json` exists and is valid JSON with required fields → OK
   - `ctx_locks/<ctx>.lock.json` exists and is stale (by `is_stale`) → warn unless `--fix`
2. Remove semaphore-specific SEM-1 invariant.
3. `--fix` path: **actually delete** `ctx_locks/*.lock.json` files where `is_stale` returns True. Current no-op behaviour is the bug being fixed.
4. `--fix` path: scan `.dadaia/sessions/` for files where the session has no live heartbeat (TTL-expired); delete them. This kills the 188-file graveyard.
5. `--fix` path: scan `ctx_locks/` for orphan sentinel files (`*.lock.sentinel`) older than 30 s; delete them. Prevents permanent deadlock after SIGKILL between CAS and unlink.

---

### Modified: `dadaia_workspace/cli/commands/context.py`

**Changes:**
1. Remove `acquire_context_semaphore` call from `context bind` subcommand.
2. Remove runtime `.ptr` file creation from `context bind` (Lock-3-era artifact).
3. Add `dadaia lock steal <ctx>` subcommand:
   - Reads `.dadaia/states/ctx_locks/<ctx>.lock.json`
   - Confirms stale via `is_stale(data)` — refuses if fresh within TTL
   - Rewrites record with caller's new `session_id` via the same O_EXCL sentinel CAS as `acquire()` (not raw `os.replace`) — prevents double-steal race on concurrent `steal` calls
   - Appends audit entry to `.dadaia/logs/lock-events.jsonl` (includes `runtime` field from `DADAIA_RUNTIME` env var)
   - Exits 0 on success; exits 1 with message if live lease refused

---

### Modified: `dadaia_workspace/public/scripts/sdd-spec-gate.sh`

**Target: ≤175 lines.** This is a hard acceptance criterion (AC-01).

**Algorithm:**

```
on PreToolUse(Edit|Write|MultiEdit|NotebookEdit|apply_patch):  # NOT empty matcher
  fpath = parse_target(payload)
  if unparseable → ALLOW + log   # fail-safe

  class = classify(fpath)
  # Path classifier (ordered; first match wins):
  # ADDITIVE: specs/backlog/**, specs/bugs/**, .dadaia/reports/**, .dadaia/handoff/**, .dadaia/tmp/**
  # MEMORY:   specs/memory/**
  # FROZEN:   specs/_archive/**
  # MUTATING: specs/releases/**/*, repos/<ctx>/**  [excl. archive prefix]
  # UNGATED:  everything else

  ADDITIVE|UNGATED → ALLOW
  MEMORY  → RULE A: [phase in CLOSURE,DEFINITION] → ALLOW; else → BLOCK
  FROZEN  → RULE B: BLOCK
  MUTATING:
    ctx = extract_ctx(fpath)
    # Gate is the SINGLE acquisition point — calls Python to perform O_EXCL CAS:
    result = $PYTHON_BIN -m dadaia_workspace.features.spec_context.lease acquire \
               <ctx> $DADAIA_SESSION_ID <release> <mode>
    # acquire() returns one of:
    #   exit 0 + "ACQUIRED"   — was absent/stale; new record written
    #   exit 0 + "RENEWED"    — session_id matches; heartbeat renewed
    #   exit 1 + "HELD:<session_id>:<acquired_at>:<heartbeat>"  — live conflict
    ACQUIRED|RENEWED → ALLOW
    HELD → BLOCK with unblock message (FR-P1-06; no pid — see OQ-1)
```

**Rule disposition (mandatory):**
- RULE E: **deleted** — zero lines remain; `SDD_RULE_E_DISABLED` variable absent.
- RULE C: **PostToolUse WARN** — `sdd-post-gate.sh` emits a warning if TASKS.md has no `[-]` for the current context, but does NOT block.
- RULE D: write-allowlist check uses pre-compiled `agents.index.json` at `.dadaia/agentic/agents.index.json`; no inline YAML parse.
- RULE A: memory phase gate survives (≤20 lines); updated to allow DEFINITION phase (FR-P1-13).
- RULE B: archive frozen gate survives (≤10 lines).
- RULE A2: backlog-ownership persona check survives, trimmed.

**Cross-harness honesty comment block** in gate source (required per AC-13):
```bash
# Cross-harness enforcement honesty:
# Claude Code: real PreToolUse block (decision: block)
# Codex:       real block in trusted workspace; hooks parallel — must be idempotent
# opencode:    advisory only — JSON PreToolUse unsupported; record + doctor are enforcement
```

---

## Test strategy

### Unit tests (~35 tests in `tests/unit/features/spec_context/`)

**`test_lease_stale.py`** — `is_stale` branch table:

| Row | Input | Expected |
|---|---|---|
| 1 | `data=None` | `True` |
| 2 | `data={}` (missing fields) | `True` |
| 3 | `data` with non-ISO `heartbeat` | `True` (logged WARN) |
| 4 | heartbeat 1 s ago, TTL=120 | `False` |
| 5 | heartbeat exactly TTL ago | `True` (boundary inclusive) |
| 6 | heartbeat TTL+1 s ago | `True` |
| 7 | `clock` injected to return fixed time | returns deterministic result |
| 8 | `ttl=0` with any heartbeat | `True` |

All rows use `FakeClock(fixed_dt)`. Zero real `datetime.now()` calls in assertions.

**`test_lease_property.py`** — 9-row fail-safe property table:

| Row | Lease state | Write class | Phase | Expected gate output |
|---|---|---|---|---|
| 1 | absent | MUTATING | any | ALLOW (acquire inline via Python call) |
| 2 | stale | MUTATING | any | ALLOW (reclaim inline via Python call) |
| 3 | live-mine | MUTATING | any | ALLOW + heartbeat renewed |
| 4 | live-other | MUTATING | any | BLOCK + unblock message with `dadaia lock steal` |
| 5 | absent | ADDITIVE | any | ALLOW |
| 6 | live-other | ADDITIVE | any | ALLOW |
| 7 | any | FROZEN | any | BLOCK |
| 8 | any | MEMORY | non-CLOSURE non-DEFINITION | BLOCK |
| 9 | any | MEMORY | DEFINITION | ALLOW (FR-P1-13; enables v0.1.7 T-017-02) |

Property invariant asserted for every row: output is one of {allow, actionable-error}; zero unhandled exceptions; every BLOCK contains the string `dadaia lock steal`.

**`test_lease_activity_exemption.py`** — 16-cell exemption matrix:

Rows: MUTATING, ADDITIVE, MEMORY, FROZEN.
Columns: lease-absent, lease-live-mine, lease-live-other, lease-expired.
All 16 expected outcomes asserted as exact match.
Additional named test: `test_memory_definition_allow` and `test_memory_closure_allow` (RULE A exemptions per FR-P1-13).

**`test_lease_steal.py`**:
- Stale record → `steal` returns 0; new `session_id` in record.
- Fresh record (heartbeat < TTL ago) → `steal` returns non-zero.

**`test_doctor_gc.py`**:
- Stale `ctx_locks/*.lock.json` present before `doctor --fix` → absent after.
- Orphan `.dadaia/sessions/<id>.json` (TTL-expired) present before → absent after.
- Orphan sentinel `ctx_locks/myctx.lock.sentinel` older than 30 s present before `doctor --fix` → absent after.
- `doctor --fix` with no stale records → exits 0, no files deleted.

### TOCTOU interleave test

**`tests/unit/features/spec_context/test_lease_toctou.py`** — sequential, no real threads:
1. Set `lease._before_write = lambda: second_acquire_attempt()`.
2. First caller begins `acquire()`: CAS sentinel succeeds, `_before_write` fires.
3. Inside `_before_write`, second caller attempts `open(sentinel, 'x')` — gets `FileExistsError`.
4. First caller completes write. Second caller retries (backoff); succeeds on retry after sentinel removed.
5. Asserts: exactly one record written; both callers eventually hold the lock in sequence; zero data corruption.

### Integration tests (~5 tests in `tests/integration/`)

**`test_lease_additive_concurrent.py`**:
- Hold a MUTATING lease in session A (`tmp_path`).
- Session B writes to an ADDITIVE path (`specs/backlog/`) — ALLOW confirmed.
- Asserts: session B write succeeds; session A lease unchanged.

**`test_doctor_gc_integration.py`**:
- Write stale `ctx_locks/*.lock.json` directly to `tmp_path`.
- Run `doctor --fix` on that workspace root.
- Assert: stale file deleted; doctor exits 0.

### E2E test (exactly 1)

**`tests/e2e/test_two_process_denial.py`**:
- Spawns two real subprocesses targeting the same `ctx` in a `tmp_path` workspace.
- Process A acquires MUTATING lease via a Python call to `lease.acquire`.
- Process B (started after A) attempts a MUTATING write (simulated via a small Python script calling the gate logic directly, with file-based rendezvous).
- File-based rendezvous: A writes a sentinel file after acquiring; B polls until sentinel exists using `for _ in range(100): if os.path.exists(sentinel): break; time.sleep(0.01)` — deterministic, low-overhead, no CPU spin. No repo-root writes.
- Asserts: Process B's output contains `dadaia lock steal`; Process B exits non-zero.
- Asserts: Process A's lease record is unchanged.
- Existing `threading.Barrier` test moved from `tests/unit/` to `tests/e2e/` in this task.

---

## In-workspace validation (operator)

After all tasks `[x]` DONE and gate reviews passed:

1. Operator opens a real session on this workspace, makes any edit under `repos/dadaia-workspace/` (MUTATING class).
2. Confirms: edit succeeds; lease record created at `.dadaia/states/ctx_locks/dadaia-workspace.lock.json`.
3. Operator manually sets `heartbeat` to an expired timestamp (simulate stale).
4. Runs `dadaia lock steal dadaia-workspace` — confirms exit 0 and audit entry in `.dadaia/logs/lock-events.jsonl`.
5. Runs `dadaia doctor --fix` — confirms zero expired records remain; doctor exits 0.
6. Confirms: backlog write (ADDITIVE) succeeds while MUTATING lease held.
7. Confirms: `wc -l dadaia_workspace/public/scripts/sdd-spec-gate.sh ≤ 175`.
8. Confirms: `grep -r SDD_RULE_E_DISABLED` returns zero results.

---

## Technical risks

| Risk | Mitigation |
|---|---|
| Gate-path migration half-state window | Single atomic commit: `lease.py` exists and tested → then ONE commit updates both `locking.py` (Lock-3 delete) and `sdd-spec-gate.sh` (RULE E delete + new path classifier) |
| `semaphore.py` import remnants causing `ImportError` at runtime | `ruff check` and `grep -r semaphore` in CI before merge |
| `_before_write` hook accidentally set in production | `_before_write = None` is the module default; set only in tests via `monkeypatch`; never set in `__init__.py` |
| TTL boundary off-by-one (≤ vs <) | Explicit boundary test row in `test_lease_stale.py` (row 5) |
