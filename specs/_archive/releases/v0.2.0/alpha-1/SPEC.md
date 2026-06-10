# SPEC: v0.1.6 — State model (locks, race conditions, deadlocks)

**Status:** Aprovado
**Release ID:** v0.1.6
**Milestone within:** v0.2.0 — Agentic Development Lifecycle
**Owner:** product-engineer
**Created:** 2026-06-06

> **Design of record (cite, do not duplicate):**
> - State-model redesign proposal: `.dadaia/reports/dadaia-workspace/project-manager/2026-06-06T043437Z-state-model-redesign-proposal.md`
> - Roadmap validation: `.dadaia/reports/dadaia-workspace/software-architect/2026-06-06T060000Z-roadmap-validation.md`
> - v0.2.0 program SPEC: `specs/releases/v0.2.0/SPEC.md` §6 (v0.1.6 scope)

---

## 1. Problem statement

The SDD gate/semaphore/session machinery **soft-deadlocked the main session on a trivial `pyproject.toml` version bump** and left a **188-file session graveyard** plus orphan locks for every closed release. `doctor --fix` was a no-op on them. Root cause: four desynchronized lock stores (workspace fcntl, per-context fcntl, per-release JSON implementation lock, per-context JSON semaphore) whose intermediate state is visible to other readers, combined with a 1050-line gate that spends ~700 lines resolving which of the four stores applies.

Specific failure modes reproduced in production (from `project_dev_test_review_audit` memory):
- **Force-reclaim race:** two processes both see a stale record, both reclaim, both succeed — double-acquire.
- **Heartbeat-vs-reclaim race:** a process reclaims a lock while the holder is mid-heartbeat-renewal.
- **Gate fail-closed on `RULE E`:** `RULE C` (`[-]` marker requirement) blocked a version bump that had no TASKS entry because the gate treated a missing `[-]` as a hard block instead of a warning.
- **Graveyard accumulation:** 188 `.dadaia/sessions/` files from closed-out releases that `doctor --fix` silently skipped.

---

## 2. Solution — one cross-platform JSON TTL-lease per context

Replace all four stores with **one liveness record per context**:

```
.dadaia/states/ctx_locks/<ctx>.lock.json
```

Record schema (no `pid` field — Windows-safe):

```json
{
  "context":      "<ctx>",
  "release":      "<release-id>",
  "session_id":   "sess_<uuid>",
  "mode":         "IMPLEMENTATION|REVIEW|SPEC",
  "acquired_at":  "<iso8601>",
  "heartbeat":    "<iso8601>",
  "ttl":          120
}
```

Audit entry schema (appended to `.dadaia/logs/lock-events.jsonl` on acquire/release/steal):

```json
{
  "event":       "acquire|release|steal",
  "context":     "<ctx>",
  "session_id":  "sess_<uuid>",
  "at":          "<iso8601>",
  "runtime":     "<claude|codex|opencode|unknown>"
}
```

`runtime` is read from the `DADAIA_RUNTIME` environment variable; defaults to `"unknown"` if unset. No `pid` field.

**Liveness definition:** `(now − heartbeat) ≤ LEASE_TTL_SECONDS`. No `pid`, no `os.kill`, no `/proc/<pid>/stat`. A dead holder becomes reclaimable after the TTL window elapses with no heartbeat renewal. Idle-but-alive holders renew heartbeat on every PreToolUse (any tool call), so the TTL only triggers on truly abandoned sessions.

**`LEASE_TTL_SECONDS = 120`** — a single named constant defined in `dadaia_workspace/features/spec_context/lease.py`. Every liveness comparison references this constant; no inline magic number is permitted anywhere in the codebase. 120 s was chosen over the prior OQ-1 proposal of 1800 s: the freeze root cause was a 30-minute stale window during which a relaunched session's own lease appeared foreign-and-live. With stable `.ptr` identity (FR-P1-15), a relaunched session REWENs rather than self-blocking; the short TTL makes truly abandoned leases reclaimable in ~2 minutes instead of 30 minutes. **OQ-1 was re-opened and resolved by operator decision on 2026-06-06: short heartbeat (~120 s) over 1800 s TTL.**

Renewal mechanism: renew-on-tool-use (every PreToolUse on any tool). No background thread — cross-platform.

### 2a. O_EXCL CAS — MUST-NOT-SHIP red line

`acquire()` uses an atomic sentinel via `open(sentinel, 'x')` (Python equivalent of `O_CREAT|O_EXCL`) to close the read→stale-check→write TOCTOU gap that caused the double-acquire race:

```python
acquire():
    fd = open(sentinel_path, 'x')   # FileExistsError if concurrent — retry with backoff
    try:
        rec = read_record()
        if rec is None or is_stale(rec):
            write_new_record(); audit()
        elif rec["session_id"] == my_session:
            renew_heartbeat()
        else:
            raise LockHeldError(rec)   # live conflict — the ONLY block
    finally:
        unlink(sentinel_path)
```

**No implementation may ship without this CAS path.** Any read-then-write acquire path is a security reviewer red line.

### 2b. Subagent model (architect resolution A-2)

The lease `session_id` is always PM's coordinator session. Product-engineer and software-engineer run as PM sub-agents (Claude Code Task tool) under that single lease. They do not independently acquire the lease. There is no lease handoff between sub-agents — PM dispatches the next one; the `session_id` field never changes hands. This makes "hold semaphore but not release lock" structurally impossible.

---

## 3. Functional requirements

### FR-P1-01 — Single record
One `.dadaia/states/ctx_locks/<ctx>.lock.json` per context is the sole liveness record. The per-context semaphore (`.semaphore.json`), Lock-3 per-release implementation lock (`.dadaia/locks/implementation/<ctx>__<release>.json`), and session-writer files (`.dadaia/sessions/<id>.json`) are fully retired. `ACTIVE.md` remains the sole source of which release is active.

### FR-P1-02 — O_EXCL atomic acquire
`acquire()` uses `open(path, 'x')` CAS via a sentinel file. A `FileExistsError` triggers retry with exponential backoff (max 3 retries, 0.1 s initial delay). No read-then-write acquire path exists anywhere in the codebase.

**The gate is the SINGLE acquisition point.** On every MUTATING write where the lease is absent or stale, the gate shell script calls `$PYTHON_BIN -m dadaia_workspace.features.spec_context.lease acquire <ctx> <session_id> <release> <mode>`. If `acquire()` raises `LockHeldError`, the gate BLOCKS. If `acquire()` succeeds, the gate ALLOWS. There is no separate "acquire on first Python write" path — all language to that effect is deleted from this spec.

### FR-P1-03 — Cross-platform TTL-lease liveness
Liveness = `(now − heartbeat) ≤ LEASE_TTL_SECONDS`. `LEASE_TTL_SECONDS = 120` is the single named constant (defined in `lease.py`); no inline `120` or `1800` appears anywhere in the liveness path. No `pid` field in the record. No calls to `os.kill`, `/proc/<pid>/stat`, or any OS-specific process inspection. The `is_stale` predicate is injected with a `clock: Callable[[], datetime]` parameter and contains zero direct `datetime.now()` calls.

### FR-P1-04 — Heartbeat renewal on tool use
The lease holder renews `heartbeat` field on every PreToolUse (any tool). Renewal is a conditional write: if `session_id == my_session` and lease is not stale, update `heartbeat` field via `os.replace` (atomic). A holder that stops issuing tool calls expires after `LEASE_TTL_SECONDS` (120 s). Because renewal fires on every tool call, an active session will never expire in practice — only a truly abandoned session (no tool calls for 2 minutes) becomes reclaimable.

### FR-P1-05 — Fail-safe gate — block ONLY on live conflict
The PreToolUse gate classifies every write target by path:

| Class | Path pattern | Gate action |
|---|---|---|
| ADDITIVE | `specs/backlog/**`, `specs/bugs/**`, `.dadaia/reports/**`, `.dadaia/handoff/**`, `.dadaia/tmp/**` | ALLOW always |
| MEMORY | `specs/memory/**` | RULE A: phase==CLOSURE or phase==DEFINITION → ALLOW; else BLOCK |
| FROZEN | `specs/_archive/**` | RULE B: BLOCK always |
| MUTATING | `specs/releases/<id>/**`, `repos/<ctx>/` | gate calls `$PYTHON_BIN -m dadaia_workspace.features.spec_context.lease acquire <ctx> <session_id> <release> <mode>`; that Python call performs the O_EXCL CAS: absent/stale → creates record + ALLOW; `session_id==mine` → renew heartbeat + ALLOW; else → LockHeldError → BLOCK with unblock message |
| UNGATED | Everything else | ALLOW |

No `specs/releases/<id>/evidence/**` path exists. Evidence is ADDITIVE (`.dadaia/handoff/` + `.dadaia/reports/`). Architect resolution A-1 is encoded as law.

### FR-P1-06 — Unblock message (always printed on the one block that fires)
When a live-conflict BLOCK occurs, the gate prints exactly:

```
[SDD LOCK] Release-mutation on '<ctx>' is held by session <session_id>
           acquired_at=<acquired_at>, last_heartbeat=<heartbeat>.
           One serialized release session at a time.
           To reclaim: dadaia lock steal <ctx>
           Backlog / audit / research writes are never blocked.
```

The `dadaia lock steal <ctx>` command must be present and functional at the time this message is printed. This is a **fail-safe property** — no input state leaves an agent without a working unblock path.

### FR-P1-07 — GC — never 188 again
Three GC triggers:
1. On every `acquire()` — stale existing record is reclaimed inline before write (after CAS succeeds). Additionally, at the start of `acquire()`, before attempting `open(sentinel_path, 'x')`, check if the sentinel file exists and its mtime is older than 30 s; if so, unlink it and retry (orphan sentinel GC — prevents permanent deadlock after SIGKILL between CAS and unlink).
2. On every `dadaia context show <ctx>` and `dadaia context list` — stale record for the queried context is deleted on read.
3. `dadaia doctor --fix` — sweeps `ctx_locks/*.lock.json`; **actually deletes** expired records (current no-op is fixed); also GCs `.dadaia/sessions/` orphans (TTL-expired session files); also removes orphan sentinel files (`ctx_locks/<ctx>.lock.sentinel`) older than 30 s.

There is no graveyard directory, no `RECLAIMED` state, no per-release lock directory.

### FR-P1-08 — Gate collapse: 1050 → ≤175 lines
`sdd-spec-gate.sh` is collapsed to ≤175 lines:
- RULE E (semaphore enforcement, ~400 lines) **deleted** (not disabled; `SDD_RULE_E_DISABLED` flag fully removed).
- RULE C (`[-]` marker requirement) **demoted to PostToolUse WARN** — no longer a PreToolUse block.
- RULE D (write-allowlist parse, ~196 lines inline) **moved to pre-compiled `agents.index.json` lookup** at `.dadaia/agentic/agents.index.json`; maps EVERY agent to its full `paths.write_allowlist` (not a mutating-only subset); generated by `dadaia public stage` from `public/agents/*.md` frontmatter; committed to the workspace.
- RULE A (memory phase gate) survives at ≤20 lines.
- RULE B (archive frozen gate) survives at ≤10 lines.
- RULE A2 (backlog-ownership persona check) survives, trimmed.

### FR-P1-09 — Keep fcntl Lock-1 and Lock-2
fcntl Lock-1 (workspace `.ws_lock`, guards `spec_contexts.json`) and Lock-2 (per-context `<slug>.lock`, guards git clone/rmtree/push) are untouched. They serialize short synchronous same-process operations where OS releases on death — correct semantics for their scope.

### FR-P1-10 — `dadaia lock steal <ctx>` CLI verb
New CLI verb: reads lease record; verifies no heartbeat renewal within TTL window (confirms stale); rewrites record with new `session_id` via the same O_EXCL sentinel CAS used in `acquire()` (not raw `os.replace`); writes audit entry to `.dadaia/logs/lock-events.jsonl`. Refuses to steal a live lease (heartbeat fresh within TTL). Exits 0 on success, non-zero on refusal, with a clear message. The CAS prevents a double-steal race when two operators concurrently attempt to steal the same stale lease.

### FR-P1-11 — Path safety (CWE-22/CWE-59)
`context` and `session_id` values are validated against `[A-Za-z0-9_-]` allowlist at every Python path-construction site. Lock dir created `0700`, owner-pinned, no symlink traversal.

### FR-P1-12 — Cross-harness honesty
Gate behavior is documented honestly by harness:

| Harness | Block real? | Honest claim |
|---|---|---|
| Claude Code | Yes — native `decision: block` | Full enforcement |
| Codex | Yes in trusted workspace; hooks run in parallel (must be idempotent) | Guardrail, not boundary |
| opencode | No — plugin-based JSON PreToolUse unsupported | Advisory only; record + doctor are enforcement |

The gate source file contains a comment block stating this explicitly.

### FR-P1-13 — RULE A: product-engineer memory write in DEFINITION + CLOSURE
RULE A allows product-engineer memory writes in both `DEFINITION` and `CLOSURE` phases (not CLOSURE-only). This enables v0.1.7 `quality-assurance.md` creation. Gate checks `ACTIVE.md` phase field. The T-016-04 done criteria MUST include a test row for MEMORY + DEFINITION → ALLOW in the 16-cell activity-class exemption table; absence of this row means v0.1.7 will be blocked at runtime.

### FR-P1-14 — ADDITIVE classification for `specs/audits/**` (D2 soul-fold)
`specs/audits/**` is classified ADDITIVE in the path-classifier (same as `specs/backlog/**` and `specs/bugs/**`). Parallel sessions are allowed to write audit markdown without a MUTATING lease. This enables project-auditor to run concurrently with an in-flight release (concurrent audit does not interfere with the release lease). The path pattern is: `specs/audits/**` → ALLOW always (no lease check, no phase check). Add to gate path-classifier between the existing ADDITIVE block and the MEMORY block.

### FR-P1-15 — Stable session identity (D1 soul-fold correction)
The freeze fix made `lease.acquire` always-takeover, allowing two live sessions to both hold a MUTATING lease. The correct model restores exactly-one-mutating via stable session identity:

1. **Stable session identity:** A coordinator's session_id is derived from and stored in `.dadaia/sessions/runtime/<ctx>.ptr` — a pointer file containing the session_id for this (operator, context) pairing. On every `acquire()` call, if the `.ptr` file exists and matches the session_id in the lock record, treat it as "mine" → RENEW (not conflict). This persists across relaunches of the same session environment.
2. **Reclaim-iff-stale:** Foreign session_id + stale heartbeat → auto-reclaim (current behavior: correct).
3. **Yield-iff-live-foreign:** Foreign session_id + live heartbeat → yield with informative message (do NOT takeover; do NOT fail-dead). Message: `"[SDD LOCK] Session <id> is actively mutating context <ctx> (last heartbeat: <ts>). This session will not mutate to avoid a race. Additive writes (backlog/audit/reports/handoff) are still allowed. Wait for the other session to finish, or run 'dadaia lock steal <ctx>' only if you are certain it is dead."` This is the only BLOCK that fires; it is always escapable.
4. **HARD CONSTRAINT (forbidden law):** No instruction anywhere in the codebase, persona, or skill may tell the operator to `bind --mode write`, relaunch a session, or `lock steal` as a routine step. `dadaia lock steal` is an emergency escape for truly dead sessions only — never a normal workflow step. The yield-iff-live-foreign message must never instruct the operator to steal; it must offer the steal only as a conditional ("only if you are certain it is dead").

**Implementation:** `.ptr` file creation: on first acquire for a (context, session_id) pair, write `session_id` to `.dadaia/sessions/runtime/<ctx>.ptr`. On subsequent acquires: read `.ptr`; if `.ptr` contains current session_id → RENEW regardless of what the lock record's session_id says (self-recognition). If `.ptr` is absent or stale → proceed with normal stale/foreign check. The `.ptr` file is never a lock; it is a stable identity hint. GC: `dadaia doctor --fix` removes orphan `.ptr` files for contexts with no active lock record.

**Note on TTL:** TTL = `LEASE_TTL_SECONDS` = **120 s** (operator decision 2026-06-06, OQ-1 re-opened and resolved). The stable-identity mechanism (`.ptr` file) eliminates false-conflict from session identity instability — a relaunched session recognises its own `.ptr` and RENEWs instead of self-blocking. The short 120 s TTL makes truly abandoned leases reclaimable in ~2 minutes. The 1800 s value proposed in the original OQ-1 binding is superseded by this decision.

### FR-P1-16 — Collision-safe naming for `specs/audits/` (D6 soul-fold)
Define the naming convention for parallel-session audit directories and files: `specs/audits/<YYYYMMDDTHHMMSSZ>-<session_id_8chars>/` where `session_id_8chars` is the first 8 characters of the `session_id` UUID (or `DADAIA_SESSION_ID` env var). This guarantees uniqueness even when two audits start within the same second. The naming convention is enforced by the `project-auditor` persona (docced in v0.1.7 constitution §8/§12) and by any audit scaffolding tool. Files within an audit dir follow the standard naming of their content. The gate classifies `specs/audits/**` as ADDITIVE (FR-P1-14) — no collision risk at the gate level; the naming convention prevents file-level collision for parallel audits.

---

## 4. Architecture deltas

**New modules:**
- `dadaia_workspace/features/spec_context/lease.py` — single-record module: `acquire / heartbeat / release / is_held / read` (~120 lines)
- `dadaia_workspace/core/` — `is_stale(data, *, clock, pid_probe, session_exists)` pure predicate; injectable clock; zero direct `datetime.now()`

**Modified modules:**
- `dadaia_workspace/features/spec_context/locking.py` — delete Lock-3 functions (~346 lines removed); keep fcntl Lock-1/Lock-2 wrappers untouched
- `dadaia_workspace/features/spec_context/service.py` — GC stale lease record on `context show/list` (inline delete, no CAS); does NOT call `acquire()` — acquisition is exclusively the gate's responsibility
- `dadaia_workspace/features/spec_context/doctor.py` — collapse LOCK-2..LOCK-7 into single-record invariant; `--fix` actually deletes; GC `.dadaia/sessions/` orphans
- `dadaia_workspace/cli/commands/context.py` — remove semaphore acquisition from `context bind`; add `dadaia lock steal <ctx>`
- `dadaia_workspace/public/scripts/sdd-spec-gate.sh` — collapse to ≤175 lines (path-classifier + single-record check)

**Retired modules:**
- `dadaia_workspace/features/spec_context/semaphore.py` — retired entirely; three good primitives (`_atomic_write`, `_is_pid_alive` → dropped, TTL check → migrated to `is_stale` in `core/`) migrate to `lease.py` / `core/`

**Net code delta:** approximately −330 lines.

---

## 5. Non-goals

- No change to fcntl Lock-1 or Lock-2.
- No PyPI publish (milestone only; v0.2.0 deploys).
- No persona changes (v0.1.8 scope).
- No constitution changes (v0.1.7 scope).
- No memory tree restructure (v0.1.9 scope).
- No new features beyond the lock subsystem, gate collapse, and GC.
- No distributed/multi-machine liveness (this is a single-host workspace; clock skew is a non-issue).
- No UI changes to the panel.

---

## 6. Security and operations deltas

- **CWE-22/CWE-59 mitigation:** path construction guarded by `[A-Za-z0-9_-]` allowlist on `context` and `session_id` values.
- **Fail-safe boundary:** corrupt timestamp or undeterminable staleness → `is_stale` returns `True` (treat as STALE/reclaimable, fail-OPEN). This is the operator's overriding never-deadlock mandate: a corrupt record must never permanently lock a session. The reclaim is auditable, and `doctor --fix` + inline GC sweep corrupt records. (Resolved 2026-06-06 per security gate T-016-09: the earlier "treat as HELD" wording contradicted the tested branch table row 3 and FR-P1-05; the implementation and tests are authoritative.)
- **Audit trail:** every `acquire`, `release`, and `steal` writes one JSON line to `.dadaia/logs/lock-events.jsonl` via `O_APPEND` (atomic under POSIX PIPE_BUF). Each entry includes `runtime` field (from `DADAIA_RUNTIME` env var, fallback `"unknown"`) for harness-aware debugging. No `pid` field per OQ-1.
- **Lock dir permissions:** `.dadaia/states/ctx_locks/` created `0700`, owner-pinned.

---

## 7. Memory files affected at closure

- `specs/memory/product/sdd-gate-v3.md` — gate model section updated (path-classifier, single-record, ≤175 lines)
- `specs/memory/product/context-management.md` — semaphore-based lock references removed; TTL-lease model documented
- `specs/memory/architecture.md` — lock model section updated (single-record replaces four-store)

---

## 8. Acceptance criteria

| # | Criterion | Testable via |
|---|---|---|
| AC-01 | Gate ≤175 lines (`wc -l sdd-spec-gate.sh ≤ 175`) | `wc -l` assertion in test or CI |
| AC-02 | `O_EXCL` CAS is the ONLY acquire path; zero read-then-write acquire paths in codebase | security-reviewer code inspection; grep for `open(.*'x')` as ONLY acquire call |
| AC-03 | `is_stale` contains zero direct `datetime.now()` calls | `grep -n datetime.now` in `core/` shows zero hits on hot path |
| AC-04 | Fail-safe property: for every input state the gate produces one of {allow, actionable-error, never-unhandled-exception} — no silent failure, no unblock-less block | 8-row property table unit test |
| AC-05 | Activity-class exemption: ADDITIVE writes always pass; MEMORY blocked outside DEFINITION+CLOSURE; FROZEN blocked always; MUTATING blocked only on live-other lease | 16-cell exemption table unit test |
| AC-06 | TOCTOU blocked: concurrent O_EXCL acquirers — exactly one wins, the other retries | `test_lease_toctou.py` using `_before_write` hook |
| AC-07 | Two real processes — one holds MUTATING lease, second is denied and receives unblock message containing `dadaia lock steal <ctx>` | `tests/e2e/test_two_process_denial.py` |
| AC-08 | `dadaia doctor --fix` deletes expired `.lock.json` records and `.dadaia/sessions/` orphans (not a no-op) | `test_doctor_gc.py`: stale record present before → absent after |
| AC-09 | `SDD_RULE_E_DISABLED` flag fully absent from codebase | `grep -r SDD_RULE_E_DISABLED` → 0 results |
| AC-10 | fcntl Lock-1/Lock-2 existing tests pass with zero regressions | `pytest tests/unit/test_spec_context_locking.py` |
| AC-11 | `dadaia lock steal <ctx>`: stale record → succeeds; live record (heartbeat < TTL ago) → refuses with non-zero exit | unit tests in `test_lock_steal.py` |
| AC-12 | Operator: mutate→edit→commit cycle + forced stale-lease reclaim via `dadaia lock steal` → doctor GC exit 0 | operator in-workspace validation sign-off |
| AC-13 | Cross-harness honesty comment block present in gate source | code-reviewer inspection |
| AC-14 | `specs/audits/**` classified ADDITIVE in path-classifier (gate allows without lease check) | unit test row in exemption matrix + gate source inspection (D2) |
| AC-15 | Stable-session-identity: `.dadaia/sessions/runtime/<ctx>.ptr` created on first acquire; matching session_id → RENEW (not conflict); non-matching + live → yield-iff-live-foreign message (never fail-dead, never instructs operator to steal as routine step) | unit test `test_stable_session_identity.py`; D1 integration test |
| AC-16 | Two concurrent sessions: session A holds live MUTATING lease; session B (different session_id) is denied with informative yield message; session B's additive writes are not blocked | `tests/e2e/test_yield_iff_live_foreign.py` or extension of `test_two_process_denial.py` (D1) |
| AC-17 | Yield-iff-live-foreign message does NOT contain "bind --mode write" / "relaunch" / "lock steal" as routine instruction | code-reviewer and security-reviewer text inspection (D1 forbidden-law) |
| AC-18 | `dadaia doctor --fix` removes orphan `.ptr` files for contexts with no active lock record | `test_doctor_gc.py` extension: orphan `.ptr` file present → absent after `--fix` (D1) |
| AC-19 | **Short-heartbeat E2E triad (OQ-1 operator decision):** (a) relaunched same-identity session (`session_id` matches `.ptr` content) → RENEW; no freeze, no block; (b) abandoned foreign lease (heartbeat set to `now − LEASE_TTL_SECONDS − 1` via `FakeClock`) → reclaimed by new session; reclaim completes within ~120 s of the last heartbeat in real time; (c) live foreign lease (heartbeat fresh) → yield-iff-live-foreign message; message does NOT contain "bind --mode write" / "relaunch" / routine "lock steal" instruction | `tests/e2e/test_short_heartbeat_triad.py` (new file); all three behaviors asserted with `FakeClock` for (b); real-time bound for (a)/(c) requires no sleep > 1 s in test body; test uses `tmp_path` workspace |

---

## 9. Dependencies and risks

| Risk | Severity | Mitigation |
|---|---|---|
| Gate-path migration (`*.semaphore.json` → `*.lock.json`) must be one atomic commit | HIGH | `lease.py` must exist and be tested before gate migration commit; single-commit rule enforced |
| `semaphore.py` enforcement remnants left behind | HIGH | `grep -r semaphore` on write-set after T-016-03; RULE E code deleted not disabled; `SDD_RULE_E_DISABLED` absent (AC-09) |
| Double-acquire on concurrent reclaim | HIGH | O_EXCL CAS (FR-P1-02, AC-02) — red line |
| Corrupt/undeterminable timestamp treated as stale (fail-open) | MEDIUM | Fail-safe boundary: corrupt → HELD (FR-P1-05, §6) |
| TTL too short: idle-but-alive holder falsely reclaimed | LOW | `LEASE_TTL_SECONDS`=120 s + renew-on-every-tool-use; holder must stop issuing tool calls for 2 min to expire; in practice an active agent renews on every tool call — only a dead/killed process misses renewals |
| E2E test flakiness | LOW | File-based rendezvous under `tmp_path` (no `sleep`, no repo-root writes) |

---

## 10. Out of scope

- `context bind` mode semantics (v0.1.8 coordinator architecture governs dispatch).
- Per-release `evidence/` subtree — eliminated; evidence is ADDITIVE in `.dadaia/handoff/` + `.dadaia/reports/` per architect resolution A-1.
- Any Python version gate or dependency version change.
- Panel UI changes.
- Constitution edits (v0.1.7 scope). The D2/D6 naming LAW is encoded in constitution §8/§12 by v0.1.7; this milestone encodes only the gate-level ADDITIVE classification (FR-P1-14) and the implementation convention (FR-P1-16).
- `specs/audits/` directory creation (that is the project-auditor's responsibility when it first writes an audit; the gate merely classifies the path ADDITIVE).

## 11. Soul-fold addendum (audit D1/D2/D6 — folded by v0.2.0 pre-deploy hold)

This section records the fold of audit findings D1, D2, and D6 into this milestone, authorized by the v0.2.0 pre-deploy hold decision (`backlog/v0.2.0-soul-and-correctness-fold.md` §2). The constitution-level encoding of D2/D6 belongs in v0.1.7; the gate-level code belongs here.

**D1 (stable-session-identity):** FR-P1-15 adds the stable identity mechanism that restores exactly-one-mutating without reintroducing the freeze. The always-takeover interim behavior (freeze fix) is retired by this implementation. New tasks T-016-11 through T-016-14 cover implementation and tests.

**D2 (gate ADDITIVE classification for specs/audits/**):** FR-P1-14 adds `specs/audits/**` to the ADDITIVE path list in `sdd-spec-gate.sh`. No new Python code; purely a gate path-classifier change. New task T-016-15 covers gate update + tests.

**D6 (naming convention for audit dirs):** FR-P1-16 defines the `<ts>-<session_id_8chars>/` naming convention. No new Python code; the convention is documented in the gate source comment and in v0.1.7 constitution. Covered by T-016-15 (gate-comment documentation).

No existing tasks (T-016-00..10) are re-opened. The new tasks are sequenced after T-016-04 (gate) and before the review gate tasks (T-016-08..10 remain unchanged; they are already DONE).
