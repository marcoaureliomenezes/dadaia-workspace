# SPEC — Release: spec-context-session-locks-v1

**Status:** Aprovado
**Amended:** 2026-05-30 — added BOUND_REVIEW mode + Impl-XOR-Review exclusion (enables the panel-kanban-v1 Review column + the Review/Quality phase). Amendment ACCEPTED by operator via grill-me 2026-05-30 (R2 scope confirmed to include review-locks). Still Draft (pending overall SPEC approval).
**Release ID:** spec-context-session-locks-v1
**Owner:** product-engineer
**Opened:** 2026-05-30
**Semver target:** 2.0.0 MAJOR (breaking state-model change)
**Sequencing:** Release 2 of 2. Depends on `spec-context-tree-v2` (Release 1) being CLOSED first.

---

## 1. Problem and context — the multi-agent race surface

The `dadaia-workspace` library today has no concurrency control on its most critical
shared resource: `spec_contexts.json`. The state model is built around a single global
primary pointer (`primary_context.json`) and an `ATIVO/INATIVO` enum that assumes a
single writer. As multi-agent workflows become the norm — multiple agentic runtimes
(Claude Code, Codex, OpenCode) running in parallel within the same workspace — this
assumption is actively violated.

**Why the primary must die.** The `is_primary` / `primary_context.json` construct
creates Race R-2 by design: two agents calling `promote A` and `promote B` in parallel
will both read, both demote the current primary, both promote their target, and the
workspace ends with two simultaneous primaries. There is no way to close this race
without eliminating the concept of a "global primary." The operator has decided: full
break. No global primary exists in v2. Session-level binding replaces it.

**Primary research (PM intake 2026-05-30T000000Z, confirmed code-level):**

| Race | Location | Symptom |
|------|----------|---------|
| R-1 | `json_context_store.py:60-63` `update()` load→replace gap | Lost update: concurrent writers on different rows overwrite each other's changes |
| R-2 | `service.py:229-243` `promote()` double read-modify-write | Two primaries in `spec_contexts.json` after concurrent promote calls |
| R-3 | `service.py` clone path | Double-clone of the same slug from two sessions |
| R-4 | `service.py` `dead()`/`shutil.rmtree` | Directory deleted while another agent holds open fds inside the repo |
| R-5 | `doctor.py:122-182` `fix()` + `alive()` interleave | Non-deterministic promote outcome after concurrent fix+activate |
| R-6 | `sdd-spec-gate.sh` reading `TASKS.md` during atomic rewrite | Gate sees blank file → spurious fail-open |
| R-7 | `lock-events.jsonl` concurrent append | Corrupt JSONL line if record > PIPE_BUF |
| R-8 | Two sessions on same release both edit `TASKS.md` | One session's task-marker update overwrites the other's |
| R-9 | SPEC-mode session edits release spec while implementer reads it | Contract changes under the implementer's feet |
| R-10 | Crashed session leaves implementation lock held indefinitely | Future binders permanently blocked on a dead session's lock |

**Zero concurrency tests exist today** (PM intake confirms; QA strategy §1 confirms):
`test_json_context_store.py` is fully sequential; `test_spec_context_service.py` uses
`FakeContextStore` which masks races entirely.

**What this release delivers.** R2 = Thrust B: the concurrency, session-binding, and
race-remediation work (T-10 through T-13). This is the heart of the initiative. It
closes the multi-agent race surface defined as R-1..R-9 (R-6 deferred; see §8).

**Primary source material consumed:**
- Architect ADR (9 decisions): `.dadaia/reports/dadaia-workspace/software-architect/2026-05-30T000000Z-adr-spec-context-v2.html`
- QA test strategy: `.dadaia/reports/dadaia-workspace/qa-engineer/2026-05-30T120000Z-test-strategy-spec-context-v2.html`
- PM intake: `.dadaia/reports/dadaia-workspace/project-manager/2026-05-30T000000Z-spec-context-v2-intake.html`
- Original analysis: `.dadaia/reports/dadaia-workspace/spec-context/2026-05-29T000000Z-spec-context-onboarding-and-race-conditions.html`

---

## 2. Objective

Deliver a genuinely and reliably closed multi-agent race surface for `dadaia-workspace`
by:

1. Replacing the broken `ATIVO/INATIVO` + `is_primary` model with `ALIVE/DEAD` + session
   binding (eliminating R-2 by design).
2. Adding workspace-wide fcntl locking around all `spec_contexts.json` mutations
   (closing R-1, R-5).
3. Adding per-context file locking around clone/rmtree (closing R-3, R-4).
4. Adding a per-release implementation lock with heartbeat, TTL, and audited reclaim
   (closing R-8, R-10).
5. Rewriting the pre-tool hook (RULE E) to enforce session ownership and the
   path-policy matrix, and introducing a post-tool hook for heartbeat renewal
   (closing R-9).
6. Providing a deterministic, consent-gated `dadaia migrate` command for existing
   consumer workspaces.
7. Shipping as semver 2.0.0 MAJOR with a loud migration guard that refuses to load
   `schema_version: 1` data without an explicit `dadaia migrate`.

---

## 3. Scope clusters

### T-10 — State model full break: ALIVE/DEAD; `spec_contexts.json` v2; new CLI verbs

**What this is:** The foundational refactor that every subsequent task depends on. T-10
must land before T-11; the internal ordering is T-10a → T-10b → T-10c → T-10d.

#### T-10a — Models + store: `ContextState`, `SpecContextProject`, `JsonContextStore v2`

**`ContextState` enum (full break — no aliases):**

```python
class ContextState(StrEnum):
    ALIVE = "alive"
    DEAD  = "dead"
```

The values `"ativo"` and `"inativo"` are no longer valid. Any code that references
`ATIVO` or `INATIVO` must be updated in the same commit.

**`SpecContextProject` dataclass changes:**

| Field | Change |
|-------|--------|
| `state: ContextState` | Values change to ALIVE/DEAD |
| `is_primary: bool` | **REMOVED** |
| `activated_at: str` | **REMOVED** (renamed to `alive_since`) |
| `alive_since: str \| None` | **NEW** — ISO-8601; set when moved to ALIVE |
| `dead_since: str \| None` | **NEW** — ISO-8601; set when moved to DEAD; null otherwise |
| All other fields | Unchanged |

**`spec_contexts.json` v2 schema:**

```json
{
  "schema_version": "2",
  "contexts": [
    {
      "name": "dadaia-workspace",
      "state": "alive",
      "repo_slug": "dadaia-workspace",
      "repo_url": "https://github.com/...",
      "created_at": "2026-01-01T00:00:00Z",
      "alive_since": "2026-05-01T10:00:00Z",
      "dead_since": null,
      "current_branch": "main"
    }
  ]
}
```

`primary_context.json` is **deleted** entirely. The file
`.dadaia/states/primary_context.json` must be removed (by `dadaia migrate`) and must
not be recreated by any code path in v2. The gate script's reads of that file (currently
at lines 62-78 of `sdd-spec-gate.sh`) are replaced by session-file reads in T-13.

**`JsonContextStore` changes:**
- `_VERSION` constant at `infrastructure/json_context_store.py:9` changes to `"2"`.
- `_to_dict` / `_from_dict` must handle v1 rows during migration only (not at runtime;
  v1 detection triggers the `dadaia migrate` refusal).
- On load: if `schema_version` is `"1"` OR any context has `state` in `{"ativo", "inativo"}`,
  raise `SchemaVersionError` with the migration prompt. Never silently correct.

**Raw store access invariant:** `_load` and `_dump` must not be called outside
`SpecContextService` methods. Calling them directly bypasses the fcntl lock (introduced
in T-11) and re-opens R-1. This is enforced by naming convention and must be noted in
code comments.

**Acceptance criteria:**
- AC-T10a-1: `ContextState` has exactly two members: `ALIVE` and `DEAD`.
- AC-T10a-2: `SpecContextProject` has no `is_primary` or `activated_at` fields.
- AC-T10a-3: `SpecContextProject` has `alive_since: str | None` and `dead_since: str | None`.
- AC-T10a-4: `JsonContextStore._VERSION` is `"2"`.
- AC-T10a-5: Loading a `schema_version: "1"` file raises `SchemaVersionError` with a
  message containing `"dadaia migrate"`.
- AC-T10a-6: Loading a file with `state: "ativo"` also raises `SchemaVersionError`.
- AC-T10a-7: `spec_contexts.json` written by the store contains no `is_primary` or
  `activated_at` fields.

#### T-10b — Service methods: `alive()`, `dead()` (replace `activate()`, `deactivate()`, `promote()`)

The three methods `activate()`, `deactivate()`, and `promote()` are removed and replaced:

- `SpecContextService.alive(name: str)` — transitions a context from DEAD to ALIVE.
  Sets `alive_since` to now, clears `dead_since`. Clones the repo if not present.
  Must acquire the workspace fcntl lock (T-11) for the `spec_contexts.json` mutation.
- `SpecContextService.dead(name: str)` — transitions a context from ALIVE to DEAD.
  Sets `dead_since` to now. Calls `shutil.rmtree` OUTSIDE the workspace lock but INSIDE
  the per-context file lock (T-11). Blocked if an implementation lock exists for the
  context (raises `ContextLockedError`).

The concept of "global primary" has no replacement. The session-binding mechanism
(T-11: `context bind --mode`) fills this role per-session.

**Acceptance criteria:**
- AC-T10b-1: `service.alive("ctx")` sets `state=ALIVE`, `alive_since=<now>`, `dead_since=null`.
- AC-T10b-2: `service.dead("ctx")` sets `state=DEAD`, `dead_since=<now>`.
- AC-T10b-3: `service.alive("ctx")` on an already-ALIVE context is idempotent (no error).
- AC-T10b-4: `service.dead("ctx")` when a HELD implementation lock exists raises `ContextLockedError`.
- AC-T10b-5: `activate()`, `deactivate()`, `promote()` are removed (no import, no dead code).

#### T-10c — `dadaia migrate` command (state-file migration, idempotent, consent-required)

```
dadaia migrate [--dry-run] [--yes]
```

**Actions (in order):**
1. Detect `schema_version` in `.dadaia/states/spec_contexts.json`.
2. If `schema_version == "1"`:
   a. Show what will change (`--dry-run` shows diff without writing).
   b. Map states: `"ativo"` → `"alive"`, `"inativo"` → `"dead"`.
   c. Rename field: `"activated_at"` → `"alive_since"`.
   d. Remove field: `"is_primary"`.
   e. Add field: `"dead_since": null` for all contexts.
   f. Set `schema_version = "2"`.
   g. Write atomically (`tmp → os.replace()`).
   h. Delete `primary_context.json` if it exists.
   i. Create `.dadaia/sessions/` directory.
   j. Create `.dadaia/locks/implementation/` directory.
   k. Create `.dadaia/states/ctx_locks/` directory.
   l. Append migration event to `.dadaia/logs/lock-events.jsonl`.
3. If `schema_version == "2"`: no-op (idempotent).
4. If `schema_version` is unknown: error (manual intervention required).

Without `--yes`, the command prints a diff-like summary and asks for confirmation before
any write. The `--dry-run` flag shows the planned changes without writing anything.

**Loud migration guard:** The v2 library loader detects `schema_version: "1"` or old enum
values on ANY `dadaia` command and exits non-zero with:

```
[MIGRATION REQUIRED] This workspace uses spec_contexts.json v1.
Run: dadaia migrate
After migration, all v2 commands will work normally.
```

This guard is non-negotiable: silent corruption of 1000+ PyPI installs is not acceptable.

**Acceptance criteria:**
- AC-T10c-1: `dadaia migrate --dry-run` on a v1 file prints the planned changes, exits 0, writes nothing.
- AC-T10c-2: `dadaia migrate --yes` on a v1 file performs all 12 actions, exits 0.
- AC-T10c-3: `dadaia migrate` on a v2 file is a no-op (idempotent).
- AC-T10c-4: Any `dadaia context` command on a v1 workspace exits non-zero with the migration prompt.
- AC-T10c-5: After migration, `primary_context.json` does not exist.
- AC-T10c-6: After migration, `.dadaia/sessions/`, `.dadaia/locks/implementation/`, `.dadaia/states/ctx_locks/` exist.

#### T-10d — New CLI verbs: `context alive`, `context dead`, `context bind --mode`, `context release`

Four new CLI verbs replace the old verbs. **No deprecation aliases. Hard cutover.**

| New verb | Replaces | Semantics |
|----------|---------|-----------|
| `dadaia context alive <name>` | `activate` | Transition context to ALIVE; clone repo if absent |
| `dadaia context dead <name>` | `deactivate` | Transition context to DEAD; rmtree (if no lock held) |
| `dadaia context bind <name> --mode read\|spec\|implementation\|review [--release <id>]` | `use` + `promote` | Session-level binding; outputs eval-compatible `export` lines |
| `dadaia context release` | (new) | Release the current session's binding and implementation lock |

The old verbs `activate`, `deactivate`, `promote`, and `use` are removed. Any documentation
or help text that references them must be updated.

`dadaia context bind --mode implementation` requires `--release <id>`. It:
1. Generates a UUID v4, prefixes with `sess_`, creating the session identifier.
2. Writes `.dadaia/sessions/<session_id>.json` (D-2 schema).
3. Acquires the workspace fcntl lock and creates `.dadaia/locks/implementation/<ctx>__<release>.json` if FREE (D-4 Lock 3). Raises `LockHeldError` if HELD.
4. Before creating the implementation lock: checks for any non-stale `BOUND_REVIEW` session files for the same `context/release` pair (scan `.dadaia/sessions/*.json`). If any exist, raises `ImplementationBlockedByReviewError`.
5. Outputs for eval:
   ```
   export DADAIA_CONTEXT=<name>
   export DADAIA_SESSION_ID=<session_id>
   export DADAIA_MODE=IMPLEMENTATION
   ```

`dadaia context bind --mode review --release <id>` creates a `BOUND_REVIEW` session. It:
1. Generates a UUID v4, prefixes with `sess_`, creating the session identifier.
2. Checks whether an implementation lock is currently HELD (non-stale) for the same `context/release` pair by reading `.dadaia/locks/implementation/<ctx>__<release>.json`. If HELD: raises `ReviewBlockedByImplementationError(context, release, owner_session_id)`. Mutual exclusion: Implementation and Review are MUTUALLY EXCLUSIVE per context/release pair.
3. If FREE: writes `.dadaia/sessions/<session_id>.json` with `mode: "BOUND_REVIEW"`. Review sessions do NOT create or own an implementation lock file — they are read-consistent sessions that can read production code and specs but cannot write production code or TASKS.md.
4. Outputs for eval:
   ```
   export DADAIA_CONTEXT=<name>
   export DADAIA_SESSION_ID=<session_id>
   export DADAIA_MODE=REVIEW
   ```

**Residual TOCTOU window:** the review→impl blocking check reads session files without an
fcntl lock (a directory scan). A BOUND_REVIEW session could theoretically be created
between the scan and the implementation lock creation. This is accepted: the race window
is sub-millisecond; the worst outcome is that an implementation bind succeeds while a
review session is active — the review session will appear stale at next heartbeat and the
operator sees both in the Kanban. This is lower-severity than R-8 (fully closed by Lock 3).

`dadaia context show --json` gains a `session` sub-object (null if no binding for the
current `DADAIA_SESSION_ID`). The `mode` field in the session sub-object accepts:
`"BOUND_IMPLEMENTATION"` or `"BOUND_REVIEW"` (and `"READ"`, `"SPEC"` for non-lock modes):

```json
{
  "name": "dadaia-workspace",
  "state": "alive",
  "session": {
    "session_id": "sess_8f3a2c01",
    "mode": "BOUND_IMPLEMENTATION",
    "release": "spec-context-tree-v2",
    "runtime": "claude-code",
    "pid": 18423,
    "bound_at": "2026-05-30T10:00:00Z",
    "last_seen_at": "2026-05-30T10:04:30Z",
    "ttl_seconds": 300,
    "is_stale": false
  }
}
```

The `mode` field accepts `"BOUND_IMPLEMENTATION"` or `"BOUND_REVIEW"` (or `"READ"`, `"SPEC"`
for non-lock modes). Example with BOUND_REVIEW:

```json
{
  "name": "dadaia-workspace",
  "state": "alive",
  "session": {
    "session_id": "sess_9c5d4e02",
    "mode": "BOUND_REVIEW",
    "release": "spec-context-tree-v2",
    "runtime": "claude-code",
    "pid": 19001,
    "bound_at": "2026-05-30T11:00:00Z",
    "last_seen_at": "2026-05-30T11:04:30Z",
    "ttl_seconds": 300,
    "is_stale": false
  }
}
```

**Acceptance criteria:**
- AC-T10d-1: `dadaia context alive <name>` transitions the context to ALIVE and clones the repo.
- AC-T10d-2: `dadaia context dead <name>` transitions the context to DEAD and removes the repo.
- AC-T10d-3: `eval $(dadaia context bind proj --mode implementation --release v1)` sets
  `DADAIA_CONTEXT`, `DADAIA_SESSION_ID`, and `DADAIA_MODE` in the shell.
- AC-T10d-4: A second `context bind` on the same context/release while HELD raises `LockHeldError`
  with the current owner's `session_id` and `last_seen_at` in the error message.
- AC-T10d-5: `dadaia context release` deletes the session file and the implementation lock.
- AC-T10d-6: `dadaia context show --json` contains a `session` sub-object when `DADAIA_SESSION_ID`
  is set and the session file is fresh.
- AC-T10d-7: The old verbs `activate`, `deactivate`, `promote`, `use` exit non-zero with a
  "command not found" message pointing to the new verbs.
- AC-T10d-8: `eval $(dadaia context bind proj --mode review --release v1)` sets `DADAIA_CONTEXT`,
  `DADAIA_SESSION_ID`, and `DADAIA_MODE=REVIEW` in the shell; no implementation lock file is created.
- AC-T10d-9: `context bind --mode review` when an implementation lock is HELD for the same
  context/release raises `ReviewBlockedByImplementationError` with the owner session_id.
- AC-T10d-10: `context bind --mode implementation` when a non-stale BOUND_REVIEW session
  exists for the same context/release raises `ImplementationBlockedByReviewError` with the
  review session IDs listed.

---

### T-11 — Lock architecture (ADR D-4): three-layer locking

T-11 depends on T-10 (model + service methods must exist). It introduces all three lock
types defined in ADR D-4.

#### Lock 1 — Workspace-wide fcntl lock

```
Path:    .dadaia/states/.ws_lock      (new file; gitignored)
Impl:    fcntl.flock(fd, LOCK_EX | LOCK_NB) with 5-second timeout
Timeout: fail-fast on timeout; raise WorkspaceLockTimeoutError with current holder PID
Scope:   ALL mutations to spec_contexts.json
```

Every method that mutates `spec_contexts.json` must acquire Lock 1 before loading and
release it after dumping. The lock is held for the minimum time: acquire → load →
mutate → dump → release. Scaffolding (clone, copytree) happens OUTSIDE this lock.

Methods that must hold Lock 1:
- `SpecContextService.alive()`
- `SpecContextService.dead()` (for the `spec_contexts.json` write only; rmtree is outside)
- `SpecContextService.create()`
- `SpecContextService.delete()`
- `DoctorService.fix()`
- `context bind` and `context release` (write session + lock files)

**Rationale for dropping the revision field (ADR D-5):** The fcntl lock makes the
read-modify-write sequence atomic at the OS level. A `revision` field on
`spec_contexts.json` would only catch bugs in the locking code itself — not a real
concurrency scenario. The fcntl lock is sufficient; the revision field is redundant and
adds migration complexity. Raw `_load`/`_dump` access outside the service layer is
forbidden as the compensating control (see T-10a invariant note).

#### Lock 2 — Per-context file lock

```
Path:    .dadaia/states/ctx_locks/<repo_slug>.lock   (new; gitignored)
Impl:    fcntl.flock, same 5-second timeout
Scope:   git clone, shutil.rmtree, git push for a single context
Purpose: Two different contexts can be cloned/removed in parallel;
         the same context cannot be cloned and rmtree'd simultaneously
```

#### Lock 3 — Per-release implementation lock (JSON file, not fcntl)

```
Path:    .dadaia/locks/implementation/<context>__<release>.json
         (double underscore separates context and release to avoid ambiguity)
Scope:   The BOUND_IMPLEMENTATION right for one context/release pair
Writer:  context bind --mode implementation (creates)
Deleter: context release (deletes own lock); doctor --fix (marks STALE, enables reclaim)
```

**Implementation lock schema:**

```json
{
  "lock_type":    "implementation",
  "context":      "dadaia-workspace",
  "release":      "spec-context-tree-v2",
  "session_id":   "sess_8f3a2c01d3e4f567",
  "runtime":      "claude-code",
  "pid":          18423,
  "mode":         "BOUND_IMPLEMENTATION",
  "started_at":   "2026-05-30T10:00:00Z",
  "last_seen_at": "2026-05-30T10:04:30Z",
  "ttl_seconds":  300,
  "task_path":    "repos/dadaia-workspace/specs/releases/spec-context-tree-v2/TASKS.md",
  "owner_note":   "Implementing T-1: remove foundation/ from scaffold"
}
```

**Lock state machine (FREE → HELD → STALE → RECLAIMED):**

```
FREE          No lock file exists for this context/release pair.

HELD          Lock file exists AND last_seen_at is within ttl_seconds.
              → FREE via "context release" (delete file)
              → STALE via TTL expiry (no heartbeat for ttl_seconds seconds)
              → STALE via PID liveness check (runtime PID no longer running)

STALE         Lock file exists AND last_seen_at is older than ttl_seconds.
              The session crashed or did not renew.
              → RECLAIMED via "context bind --force --reason <text>"
              → FREE via "dadaia doctor --fix" (after logging reclaim event)

RECLAIMED     Intermediate state during forced acquisition:
              1. New session calls "context bind --force --reason ..."
              2. Reclaim event written to .dadaia/logs/lock-events.jsonl
              3. Old lock file overwritten by new session's lock
              End state: HELD (new owner)
```

**Audit log schema (`.dadaia/logs/lock-events.jsonl` — one JSON object per line):**

```json
{
  "ts":         "2026-05-30T10:06:00Z",
  "event":      "ACQUIRED | RELEASED | STALE_DETECTED | RECLAIMED | HEARTBEAT | BLOCKED_ATTEMPT",
  "context":    "dadaia-workspace",
  "release":    "spec-context-tree-v2",
  "session_id": "sess_8f3a2c01d3e4f567",
  "runtime":    "claude-code",
  "pid":        18423,
  "reason":     "Session crashed (TTL expired; PID 18423 not alive)",
  "reclaim_by": "sess_9b4d3e02",
  "fpath":      "repos/.../file.py"
}
```

Lines are written with `O_APPEND`. Individual records are under 1 KB (well under
`PIPE_BUF` on Linux = 4096 bytes), so atomicity of individual append writes is
guaranteed.

**Impl-XOR-Review mutual exclusion (Lock 3 extension):**

A HELD implementation lock for context `C` / release `R` blocks any attempt to bind with
`--mode review` for the same `C/R` pair: raises `ReviewBlockedByImplementationError`.
Conversely, if a non-stale `BOUND_REVIEW` session exists for the same `C/R` pair,
a new `--mode implementation` bind raises `ImplementationBlockedByReviewError`.

The review→impl blocking direction uses session files (not the implementation lock file)
because review sessions do not create lock files. The implementation lock file remains
the single source of truth for Lock 3 HELD state.

Two new exception classes (inherit from a common `LockConflictError` base):
- `ReviewBlockedByImplementationError(context, release, owner_session_id)`
- `ImplementationBlockedByReviewError(context, release, review_session_ids: list[str])`

Two `BOUND_REVIEW` sessions for the SAME `C/R` pair are allowed (reviews do not conflict
with each other — only with implementation binds).

**Acceptance criteria (lock tests per QA strategy §3):**
- AC-T11-1: `bind("proj", "v1", mode=IMPLEMENTATION)` creates lock file with `state=HELD`.
- AC-T11-2: Second `bind` on same context/release (HELD) raises `LockHeldError` with owner session_id.
- AC-T11-3: Two binds on different releases for the same context coexist (both HELD).
- AC-T11-4: `release_lock("proj", "v1", session)` deletes the lock file.
- AC-T11-5: `bind` on a context with `state=DEAD` raises `ContextNotAliveError`.
- AC-T11-6: Concurrent `alive()` calls holding Lock 1 do not produce a lost-update (R-1 closed).
- AC-T11-7: Concurrent `alive()` + `doctor.fix()` do not produce a non-deterministic state (R-5 closed).
- AC-T11-8: Per-context lock prevents concurrent clone and rmtree of the same slug (R-3/R-4 closed).
- AC-T11-9: `dead()` raises `ContextLockedError` when an implementation lock is HELD for the context.
- AC-T11-10: `bind("proj", "v1", mode=BOUND_REVIEW)` when impl lock HELD raises `ReviewBlockedByImplementationError`.
- AC-T11-11: `bind("proj", "v1", mode=IMPLEMENTATION)` when non-stale BOUND_REVIEW session exists raises `ImplementationBlockedByReviewError`.
- AC-T11-12: Two BOUND_REVIEW sessions for the same C/R pair coexist (no mutual exclusion between reviews).

---

### T-12 — Heartbeat + TTL (300 s) + audited reclaim; doctor LOCK-1..LOCK-5

#### Heartbeat protocol

- **Source:** post-tool hook `sdd-post-gate.sh` (new in T-13) renews `last_seen_at` on
  every write operation.
- **Fallback:** `dadaia context heartbeat` CLI command for long-running read-only sessions.
- **Renewal:** atomic JSON overwrite of the lock file via `tmp → os.replace()`.
- **Concurrency:** the workspace fcntl lock (Lock 1) is NOT held during heartbeat renewal
  (heartbeat is idempotent; the stale window is acceptable vs. lock contention).

TTL default is **300 seconds**. A lock with `last_seen_at` older than `ttl_seconds` is
STALE regardless of PID liveness. PID check is an additional fast-path: if PID is no
longer alive, mark STALE immediately.

Reclaim requires explicit reason. Forced reclaim without reason string is rejected.
Every reclaim event is appended to `lock-events.jsonl`.

#### Doctor LOCK invariants

| Invariant | Trigger | Auto-fix policy |
|-----------|---------|-----------------|
| LOCK-1 | Two `.json` files for the same `<context>__<release>` key | Keep freshest by `last_seen_at`; rename others `.conflicted`; append audit record; require human review |
| LOCK-2 | Implementation lock exists for a context with `state=DEAD` | AUTO-FIX: delete lock file; append audit record. Context remains DEAD. |
| LOCK-3 | HELD lock with `last_seen_at` older than `ttl_seconds` | Update `state` field to STALE; do NOT delete. Reclaim requires explicit operator command. |
| LOCK-4 | A production-file mutation in `lock-events.jsonl` lacks `task_id` field | NO AUTO-FIX: report; block closure until reconciled. |
| LOCK-5 | `lock-events.jsonl` contains a `BLOCKED_ATTEMPT` event (non-owner tried to write) | NO AUTO-FIX: surface as audit signal in doctor report; no automatic action. |
| LOCK-6 | A BOUND_REVIEW session file in `.dadaia/sessions/` belongs to a context with `state=DEAD` | AUTO-FIX: delete the stale session file; append audit record. Extends LOCK-2 coverage to review-mode session files. |

UX note: when a lock is STALE or the gate blocks a write, the error message must show
the owner's runtime, session ID, and `last_seen_at` so the operator can decide whether
to reclaim.

**Acceptance criteria (per QA strategy §3):**
- AC-T12-1: `check_lock_state("proj", "v1")` returns STALE for a lock with `last_seen_at` 10 min ago and `ttl_seconds=180`.
- AC-T12-2: `reclaim("proj", "v1", reason="...", new_session="sess_3")` when STALE: updates owner, appends `RECLAIMED` audit record, new state = HELD.
- AC-T12-3: `reclaim` on a HELD (fresh) lock raises `LockActiveError`.
- AC-T12-4: `renew_heartbeat("proj", "v1", "sess_1")` updates `last_seen_at`; state stays HELD.
- AC-T12-5: Doctor LOCK-3 sets `state=STALE` on an expired lock; does NOT delete the file.
- AC-T12-6: Doctor LOCK-2 deletes a lock for a DEAD context; appends audit record.
- AC-T12-7: `lock-events.jsonl` schema test — every line produced by bind/release/reclaim contains `ts`, `event`, `context`, `release`, `session_id`, `runtime`.

---

### T-13 — Deterministic pre/post-tool hooks (RULE E + `sdd-post-gate.sh`); T-8 completion

T-13 depends on T-11 (lock files must exist) and T-12 (heartbeat/staleness check must
exist). This task completes the per-release gate (T-8) by resolving the active release
from the implementation lock rather than from `ACTIVE.md` for IMPLEMENTATION-mode sessions.

#### Session identity resolution order (explicit AC)

The session ID must be resolved in this order:

1. **Native runtime ID** — Claude Code's hook stdin payload carries `session_id`. If
   present and non-empty, it is used for correlation logging but is NOT the primary key
   (it is runtime-specific and not portable to Codex/OpenCode).
2. **`DADAIA_SESSION_ID` env var** — set by `eval $(dadaia context bind ...)`. This is
   the primary stable key, portable across all three runtimes. The hook reads this first.
3. **Fail-open** — if `DADAIA_SESSION_ID` is absent, the hook logs a warning to
   `/tmp/sdd-gate.log` and exits 0 (does not block). Lock enforcement only activates
   when the session identity is established.

This ordering must be documented in code comments and in the RULE E algorithm.

#### RULE E — Session and lock enforcement (new in `sdd-spec-gate.sh`)

RULE E is inserted after RULE D (path-scope check) and before RULE C (task marker).
Algorithm:

```
1. If DADAIA_SESSION_ID is unset → FAIL-OPEN (log warning, return 0)
2. Load session file .dadaia/sessions/$DADAIA_SESSION_ID.json
   If absent → BLOCK with "Session file missing. Run: eval $(dadaia context bind ...)"
3. Check staleness: if last_seen_at + ttl_seconds < now → BLOCK with "Session STALE. Re-bind."
4. Classify path:
   a. .dadaia/reports/** or .dadaia/tmp/** → ALLOW (always writable)
   b. specs/memory/** → REQUIRE mode ≥ SPEC; READ mode → BLOCK
   c. Production code (repos/<slug>/ outside specs/) → REQUIRE IMPLEMENTATION mode
      + verify lock ownership → BLOCK if wrong owner (show owner session_id)
   d. releases/<id>/SPEC.md, PLAN.md (when impl lock HELD for that release) → BLOCK
      even in SPEC mode (R-9 closure)
   e. All other paths → fall through to RULE C (task marker check)
5. For IMPLEMENTATION mode: resolve active release from the implementation lock file
   (not from ACTIVE.md). Pass resolved release ID to RULE C for TASKS.md check.
   ACTIVE.md is still consulted for SPEC/READ mode sessions.
```

RULE E uses inline Python snippets for JSON parsing (same pattern as current gate rules).

#### Path-policy matrix

| Session mode | Production code | `specs/memory/**` | `specs/releases/<id>/SPEC.md` (impl lock HELD) | `specs/releases/<id>/TASKS.md` (impl lock HELD) | `.dadaia/reports/**` |
|---|---|---|---|---|---|
| No session (fail-open) | Allowed (gate falls through to RULE C) | Allowed | Allowed | Allowed | Allowed |
| READ | BLOCK | BLOCK | BLOCK | BLOCK | Allowed |
| SPEC | BLOCK | Allowed | BLOCK (R-9) | BLOCK (R-9) | Allowed |
| IMPLEMENTATION (owns lock) | Allowed | Allowed | BLOCK (read-only once impl starts) | Allowed | Allowed |
| IMPLEMENTATION (does not own lock) | BLOCK | Allowed | BLOCK | BLOCK | Allowed |
| BOUND_REVIEW (owns release match) | BLOCK (read-only) | BLOCK (read-only) | BLOCK (read-only) | BLOCK | Allowed |

Note: gate only intercepts write tool calls. BOUND_REVIEW sessions can **read** everything
(production code, specs, memory) but cannot **write** production code, specs/memory, or
TASKS.md. Writing to `.dadaia/reports/**` and `.dadaia/tmp/**` is allowed because the
reviewer's job is to produce reports. This policy enables qa-engineer and security-reviewer
to execute their review duties without the ability to modify implementation artefacts.

#### Post-tool hook: `sdd-post-gate.sh` (new public asset)

A new script `dadaia_workspace/public/scripts/sdd-post-gate.sh` runs as the PostToolUse
hook across all three runtimes. Its responsibilities:

1. Read `DADAIA_SESSION_ID` from env; if absent, exit 0 (no-op).
2. Load the session file; if absent, exit 0.
3. Renew `last_seen_at` atomically (`tmp → os.replace()`).
4. Append a `HEARTBEAT` event to `.dadaia/logs/lock-events.jsonl`.

The post-tool hook must be added to the manifest and propagated via
`dadaia public stage && dadaia public install --target all`.

#### Hook injection (all three runtimes)

| Runtime | Pre-tool hook | Post-tool hook | Injection |
|---------|--------------|----------------|-----------|
| Claude Code | `.claude/settings.json` `hooks.PreToolUse[*]` | `hooks.PostToolUse[*]` | `dadaia public install --target claude` |
| Codex | `.codex/hooks.json` `pre_tool_call` | `post_tool_call` | `dadaia public install --target codex` |
| OpenCode | `opencode.json` `hooks.before_tool_call` | `hooks.after_tool_call` | `dadaia public install --target opencode` |

Devops-engineer must verify that each runtime's hook JSON schema supports multiple
hooks (pre and post simultaneously) and that the install script writes both.

**Cross-reference (T-8 completion):** T-8a in R1 removed the legacy root-TASKS.md
fallback. T-13 completes T-8 by rewriting the gate's context resolution: for
IMPLEMENTATION-mode sessions the active release comes from the implementation lock
file, not from `ACTIVE.md`. Both changes are required together for the full per-release
gate guarantee.

**Acceptance criteria (per QA strategy §4.3):**
- AC-T13-1: Session-ID resolution: `DADAIA_SESSION_ID` absent → gate exits 0 (fail-open) with warning in gate log.
- AC-T13-2: `DADAIA_SESSION_ID` present, session file absent → gate blocks with "Session file missing" message.
- AC-T13-3: Session present and fresh, no implementation lock → gate blocks write to production file.
- AC-T13-4: Session present and fresh, owns implementation lock → gate allows write to production file.
- AC-T13-5: SPEC-mode session → gate blocks write to `releases/<id>/SPEC.md` when impl lock is HELD for `<id>`.
- AC-T13-6: READ-mode session → gate blocks all writes (production, memory, releases).
- AC-T13-7: IMPLEMENTATION-mode session resolves active release from lock file, not ACTIVE.md.
- AC-T13-8: `sdd-post-gate.sh` renews `last_seen_at` in the session file after each tool call.
- AC-T13-9: `sdd-post-gate.sh` appends a HEARTBEAT event to `lock-events.jsonl`.
- AC-T13-10: Both hooks are installed in Claude Code, Codex, and OpenCode via `dadaia public install`.

---

## 4. Race remediation — R-1..R-10 closing-mechanism table

This is the explicit mapping required by the operator. Every HIGH-severity race must be
traceable to a specific mechanism in this release.

| Race | Description | Severity | Closing mechanism | Task |
|------|-------------|----------|-------------------|------|
| R-1 | Concurrent `update()` on different rows — second writer overwrites first writer's row | HIGH | Workspace-wide fcntl lock (Lock 1) wraps the full load→mutate→dump cycle in `alive()` and `dead()`. Both callers must acquire the lock; the second waits or times out with `WorkspaceLockTimeoutError`. | T-11 |
| R-2 | Concurrent `promote A` + `promote B` → two primaries | HIGH | **Eliminated by design.** `promote` is removed. No global primary exists in v2. The concept that created R-2 is deleted in T-10. | T-10 |
| R-3 | Concurrent `alive X` from two sessions racing to `git clone` the same slug | MED | Per-context file lock (Lock 2) at `.dadaia/states/ctx_locks/<slug>.lock` serializes clone for a single context. Two different contexts can still clone in parallel. | T-11 |
| R-4 | `dead()` calls `shutil.rmtree` while another agent holds open fds inside the repo | HIGH | Per-context file lock (Lock 2) wraps rmtree. Additionally, RULE E (Lock 1 check-and-create during bind) verifies the session owns the implementation lock before any write to `repos/<slug>/`. A session with a live implementation lock blocks `dead()` via `ContextLockedError`. | T-11 |
| R-5 | `alive()` races with `doctor.fix()` — non-deterministic promote outcome | MED | Workspace-wide fcntl lock (Lock 1) wraps both `alive()` and `doctor.fix()`. The second caller waits. | T-11 |
| R-6 | Gate reads partial TASKS.md during atomic rewrite — spurious fail-open | LOW | **Deferred to backlog.** Individual TASKS.md writes use `os.replace()` (atomic rename). The gate may see a blank file momentarily. Acceptable: fail-open means the gate allows on blank read; no data corruption. A short retry loop in the hook would fix this. Deferred as LOW severity. | backlog |
| R-7 | Concurrent `O_APPEND` writes to `lock-events.jsonl` interleaving lines > PIPE_BUF | LOW | Records are designed to stay under 1 KB (well under 4096-byte PIPE_BUF on Linux). Atomicity of individual append writes is guaranteed by POSIX. Not a concern with the designed schema. | T-11 (by design) |
| R-8 | Two sessions implementing the same release both edit `TASKS.md` | HIGH | Per-release implementation lock (Lock 3): only one session holds BOUND_IMPLEMENTATION for a given context/release pair. Second `context bind --mode implementation` on the same context/release sees HELD and raises `LockHeldError`. RULE E additionally blocks production writes from a session that does not own the lock. | T-11 + T-13 |
| R-9 | SPEC-mode session edits release SPEC.md while implementation session reads it | HIGH | Path-policy matrix in RULE E: when an implementation lock is HELD for context/release `X`, SPEC-mode sessions are blocked from writing to `releases/X/SPEC.md` and `releases/X/PLAN.md`. | T-13 |
| R-10 | Stale lock from crashed session blocks future binders indefinitely | MED | TTL heartbeat (300 s, renewed by post-tool hook) + doctor LOCK-3 (marks STALE). Stale lock → RECLAIMED via `context bind --force --reason <text>`. PID liveness check is an additional fast-path. | T-12 |

---

## 5. Migration — `dadaia migrate`

The operator chose a full break (ADR D-8 Option C: detect-and-prompt). This is the
highest-impact consequence: every consumer workspace that upgrades to 2.0.0 must run
`dadaia migrate` before any CLI command works.

**Why full break is correct:**
- The additive-compat path (retaining `ATIVO/INATIVO` as derived fields) permanently
  pollutes the model with two parallel lifecycle concepts and defers technical debt.
- The full break makes the contract clean: one migration, then v2 semantics everywhere.
- The migration is idempotent and consent-gated; risk of data loss is minimal.

**`dadaia migrate` spec:** See T-10c above. The command is part of T-10.

**PyPI strategy (ADR D-8):**
- R1 (`spec-context-tree-v2`) ships as `1.(x+1).0` MINOR.
- R2 (`spec-context-session-locks-v1`) ships as `2.0.0` MAJOR.
- A `2.0.0rc1` pre-release is recommended for early adopters to test migration before GA.
- The CHANGELOG and release notes for 2.0.0 must document the migration path. This is a
  product-engineer deliverable at CLOSURE.

**Consumer CI pipelines:** Any CI that runs `dadaia doctor` must add `dadaia migrate --yes`
to the setup step after upgrading to 2.0.0. This must be called out explicitly in the
2.0.0 release notes.

---

## 6. Session identity resolution order

This section makes the resolution order an explicit acceptance criterion (operator
requirement from the dispatch briefing).

**Resolution order (in priority):**

1. `DADAIA_SESSION_ID` environment variable — set by `eval $(dadaia context bind ...)`.
   This is the primary stable key. UUID v4 format, prefixed `sess_`.
2. Fail-open — if `DADAIA_SESSION_ID` is not set, the hook logs a warning and exits 0.
   Lock enforcement only activates when the session identity is established.

**What is NOT used as the primary key:**
- The native `session_id` from the Claude Code hook stdin payload — it is runtime-specific,
  not portable to Codex/OpenCode, and is used only for correlation logging.
- PID alone — PIDs are recycled by the OS; stale PID → stale session risk. PID is recorded
  in the session file as a fast-path liveness probe (if PID is dead, mark STALE
  immediately), but is never the session identity.

**Cross-runtime portability (ADR D-3):**

| Runtime | `DADAIA_SESSION_ID` source | Hook env | Works? |
|---------|---------------------------|----------|--------|
| Claude Code | `eval` output; Claude's own `session_id` used for logging only | Inherits shell env from the terminal where `eval` ran | YES |
| Codex | `eval` output | Codex hooks run in the same shell context | YES |
| OpenCode | `eval` output; `ctx-inject.sh` already propagates `DADAIA_CONTEXT` (same pattern) | Hook inherits env | YES |

**UX cost and mitigation:** The operator must run `eval $(dadaia context bind ...)` rather
than just `dadaia context bind`. The CLI output must make this unmistakable — it must print
the full `eval` command and a one-line reminder:

```
# Run the following command to bind this session:
eval $(dadaia context bind dadaia-workspace --mode implementation --release my-release-v1)
```

Sessions started without `eval` lack `DADAIA_SESSION_ID` and get fail-open behavior (no
lock enforcement). They cannot own an implementation lock.

**Acceptance criteria:**
- AC-SES-1: `eval $(dadaia context bind ...)` exports `DADAIA_CONTEXT`, `DADAIA_SESSION_ID`, and `DADAIA_MODE` in the shell.
- AC-SES-2: Gate with `DADAIA_SESSION_ID` absent → exits 0 with warning in gate log (fail-open).
- AC-SES-3: Gate with `DADAIA_SESSION_ID` present but session file absent → exits 2 with blocking message.
- AC-SES-4: Gate with `DADAIA_SESSION_ID` present, session file fresh → proceeds to path classification.

---

## 7. Architecture deltas

All architecture deltas are confined to `repos/dadaia-workspace/dadaia_workspace/`.

| Layer | What changes |
|-------|-------------|
| `core/models/spec_context.py` | `ContextState` → ALIVE/DEAD; `SpecContextProject` drops `is_primary`, `activated_at`; gains `alive_since`, `dead_since` |
| `infrastructure/json_context_store.py` | `_VERSION = "2"`; schema migration detection; fcntl lock (Lock 1) around all write methods; `SchemaVersionError` on v1 load |
| `features/spec_context/service.py` | Remove `activate()`, `deactivate()`, `promote()`; add `alive()`, `dead()`, `bind()`, `bind_review()`, `release_lock()`, `renew_heartbeat()`, `check_lock_state()`, `reclaim()`; new exceptions `ReviewBlockedByImplementationError`, `ImplementationBlockedByReviewError` (both inherit `LockConflictError`) |
| `features/spec_context/doctor.py` | Remove INV-1..INV-3, INV-6 (guard `is_primary` logic that no longer exists); rename INV-4/INV-5 for ALIVE/DEAD enum; add LOCK-1..LOCK-5 |
| `cli/commands/context.py` | Remove `activate`, `deactivate`, `promote`, `use`; add `alive`, `dead`, `bind --mode`, `release`, `heartbeat`; update `show --json` |
| `cli/commands/migrate.py` | Add `dadaia migrate [--dry-run] [--yes]` command |
| `public/scripts/sdd-spec-gate.sh` | Add RULE E (session/lock enforcement, inserted after RULE D); replace primary_context.json reads with session-file reads |
| `public/scripts/sdd-post-gate.sh` | **NEW** — post-tool hook; heartbeat renewal + HEARTBEAT audit log |
| `.dadaia/sessions/` | **NEW** — session file directory (created by migrate + dadaia init) |
| `.dadaia/locks/implementation/` | **NEW** — per-release implementation lock directory |
| `.dadaia/states/ctx_locks/` | **NEW** — per-context file lock directory |
| `.dadaia/logs/lock-events.jsonl` | **NEW** — append-only audit log |
| `.dadaia/agentic/manifest.json` | Updated to track `sdd-post-gate.sh` as a new lib-originated asset |

**Doctor invariants removed in R2:** INV-1, INV-2, INV-3, INV-6 (they guard `is_primary`
logic that no longer exists). INV-4 and INV-5 are renamed to align with ALIVE/DEAD enum
values.

**No changes to:**
- `public/scaffold/` (scaffold changes belong to R1)
- `public/templates/` (template changes belong to R1)
- `cli/commands/` beyond the context + migrate commands

---

## 8. Tech-stack deltas

| Item | Delta |
|------|-------|
| `fcntl` (Python stdlib) | Used for Lock 1 and Lock 2. No new PyPI dependency. |
| `uuid` (Python stdlib) | Used for session ID generation. Already available. |
| `filelock` (PyPI) | **Considered and rejected.** The stdlib `fcntl.flock` is sufficient for Linux/macOS. Adding a new PyPI dependency for a stdlib-equivalent is unwarranted. |
| No other new dependencies | All implementation in Python + Bash (existing stack). |

---

## 9. Security and operations deltas

- **Audit trail:** Every lock state transition (ACQUIRED, RELEASED, STALE_DETECTED,
  RECLAIMED, HEARTBEAT, BLOCKED_ATTEMPT) is appended to `.dadaia/logs/lock-events.jsonl`.
  This provides forensic evidence of which session held which lock and when.
- **Lock reclaim requires explicit reason:** `context bind --force --reason <text>` — the
  reason string is mandatory and appended to the audit log. Anonymous reclaim is rejected.
- **Fail-open philosophy preserved:** The gate exits 0 (allows) when the session identity
  is absent. This is intentional: the lock enforcement only activates when the session is
  bound. Unbound sessions continue to work as before R2, with the trade-off that they
  receive no lock protection.
- **Primary context gone:** Removing `primary_context.json` eliminates the split-primary
  attack surface (R-2) and reduces the number of files that must be kept consistent.

---

## 10. Memory files affected at CLOSURE

At R2 CLOSURE, the following memory atoms must be updated to reflect the v2 state model:

- `specs/memory/architecture.html` — Update to describe the three-layer lock architecture,
  the session-binding model, and the audit log. Remove references to `primary_context.json`
  and `ATIVO/INATIVO`.
- `specs/memory/tech-stack.html` — Note: `fcntl` (stdlib) now used for workspace-wide
  and per-context locking. No new PyPI dependencies.
- `specs/memory/product/index.html` — Update the spec-context feature entry to reflect
  the new ALIVE/DEAD lifecycle and session-binding model.
- `specs/memory/product/spec-context.html` (or equivalent feature slug) — Full rewrite of
  the feature description to cover ALIVE/DEAD, session modes, implementation lock,
  heartbeat/TTL, reclaim, and the hook enforcement model.

---

## 11. Acceptance criteria summary

### 11.1 Race remediation (primary operator bar)

- AC-RACE-1: 6 deterministic race reproduction tests ship (R-1, R-2, R-4, R-5, R-8, R-9)
  using `threading.Event`/`Barrier` at the load→replace seam. No `time.sleep()` in any
  concurrency test.
- AC-RACE-2: CI check `grep -r "time.sleep" tests/` returns no matches (or exits non-zero
  if matches found without `# allowed-sleep` comment). This is a hard CI gate.
- AC-RACE-3: All 6 race tests pass (not xfail) after R2 implementation — they document
  R-1..R-9 closures, not known bugs.
- AC-RACE-4: `threading.Barrier(2)` / `threading.Event` pattern used (not OS timing).
  All threads joined with `timeout=5`; test fails if any thread is still alive after join.
- AC-RACE-5: Tests use real `JsonContextStore` on `tmp_path` (never `FakeContextStore`)
  for concurrency scenarios.
- AC-RACE-6: All tests pass with `pytest --randomly-seed=last` (order-independent).

### 11.2 Lock state machine (9 tests per QA strategy §3.1)

- AC-LOCK-1: FREE → HELD on bind.
- AC-LOCK-2: Second bind on same context/release (HELD, fresh) → `LockHeldError`.
- AC-LOCK-3: Two binds on different releases for same context → both HELD (coexist).
- AC-LOCK-4: Heartbeat renewal updates `last_seen_at`, state stays HELD.
- AC-LOCK-5: Expired `last_seen_at` → state reported as STALE.
- AC-LOCK-6: Reclaim of STALE lock → HELD (new owner) + audit record appended.
- AC-LOCK-7: Reclaim of HELD (fresh) lock → `LockActiveError`.
- AC-LOCK-8: Release → lock file deleted + audit record.
- AC-LOCK-9: Bind on DEAD context → `ContextNotAliveError`.

### 11.3 Audit log schema (1 test)

- AC-AUDIT-1: Every entry produced by bind/release/reclaim contains `ts`, `event`,
  `context`, `release`, `session_id`, `runtime` fields.

### 11.4 Session-mode hook tests (4 tests per QA strategy §4.3)

- AC-HOOK-1: No lock → IMPLEMENTATION write blocked.
- AC-HOOK-2: Owned lock → IMPLEMENTATION write allowed.
- AC-HOOK-3: SPEC mode + HELD impl lock for same release → TASKS.md write blocked.
- AC-HOOK-4: READ mode → all writes blocked (production, memory, releases).

### 11.5 Doctor LOCK invariant tests (12 tests per QA strategy §5)

- AC-DOC-L1..AC-DOC-L10: 2 tests per invariant (LOCK-1..LOCK-5): violating fixture +
  expected post-fix or no-fix guarantee. End-to-end on real `tmp_path`.
- AC-DOC-L11..AC-DOC-L12: 2 tests for LOCK-6: (a) stale BOUND_REVIEW session file for
  a DEAD context is auto-deleted + audit record appended; (b) fresh BOUND_REVIEW session
  file for a DEAD context is also auto-deleted (no TTL grace for DEAD context sessions).

### 11.6 Coverage thresholds (per QA strategy §7.2)

- AC-COV-1: `infrastructure/json_context_store.py` — new lock code ≥ 95% branch coverage.
- AC-COV-2: `features/spec_context/service.py` — new lock methods ≥ 90% branch coverage.
- AC-COV-3: `features/spec_context/doctor.py` — new LOCK check/fix branches ≥ 90% branch coverage.

### 11.7 Session identity and migration

- AC-SES-1..AC-SES-4: Per §6 (session identity resolution order ACs).
- AC-MIG-1..AC-MIG-6: Per T-10c (migration command ACs).

### 11.8 BOUND_REVIEW mode (added 2026-05-30)

- AC-REV-1: `context bind --mode review --release R` when an implementation lock is HELD for the same context/release raises `ReviewBlockedByImplementationError` with the owner session_id.
- AC-REV-2: `context bind --mode implementation --release R` when a non-stale `BOUND_REVIEW` session exists for the same context/release raises `ImplementationBlockedByReviewError` with the review session IDs listed.
- AC-REV-3: A BOUND_REVIEW session triggers the gate to BLOCK write tool calls to production code files (`repos/<slug>/` outside `specs/`).
- AC-REV-4: A BOUND_REVIEW session allows write tool calls to `.dadaia/reports/**` (reviewer can emit reports without gate blockage).
- AC-REV-5: Two simultaneous BOUND_REVIEW sessions for the same context/release are allowed (reviews do not conflict with each other; only implementation binds are blocked).

---

## 12. Out of scope

### 12.1 All of Thrust A (Release 1 — `spec-context-tree-v2`)

T-1 through T-9 (scaffold, HTML memory, CLI commands, doctor TREE invariants, migration
of tree layout) are Release 1 deliverables. They must not be re-implemented in R2.

### 12.2 Race R-6 (gate reads partial TASKS.md)

R-6 is LOW severity: the gate's fail-open behavior on a blank TASKS.md is safe (allows
the write rather than blocking it). The correct fix is a short retry loop in the hook.
This is deferred to backlog. It must NOT be introduced in R2 as it adds complexity to
the gate with minimal safety benefit.

### 12.3 Multi-host lock aggregation

The lock architecture is single-machine only. Multiple machines sharing a workspace via
NFS or a distributed filesystem are not in scope. A future `schema_version: "3"` can
add a revision field for multi-machine scenarios.

### 12.4 R1 scaffold / CLI commands already in `spec-context-tree-v2`

`dadaia release new`, `dadaia backlog new`, `dadaia bug new`, `dadaia migrate tree-v2`,
and all TREE doctor invariants are R1 deliverables. R2 depends on them being present
(the `releases/` directory structure must exist) but does not re-implement them.

---

## 13. Dependencies and sequencing

### 13.1 Release dependencies

- **`spec-context-tree-v2` (R1) must close first.** T-10 in this release assumes the
  canonical `releases/` directory structure from R1's T-4 is present in the scaffold.
  The `context bind` command writes lock files; those paths assume `releases/` exists.
- **`go-open-source` must close first.** R2 modifies `sdd-spec-gate.sh`, which R1's
  T-8a also touched. `go-open-source` is already complete at the code level (all tasks
  `[x]`; only T-GOS-OPS1 operator action pending). R2 implementation must not begin
  until `go-open-source` ACTIVE.md phase = ARCHIVED.

### 13.2 Internal task ordering (hard)

```
T-10a (models + store)
  ↓
T-10b (service methods: alive/dead)
  ↓
T-10c (migrate command)   ← must ship simultaneously with T-10a (cannot be separate)
  ↓
T-10d (CLI verbs: alive/dead/bind/release)
  ↓
T-11 (three-layer lock architecture)
  ↓
T-12 (heartbeat + TTL + doctor LOCK-*)
  ↓
T-13 (RULE E + sdd-post-gate.sh + hook injection)
```

T-10c (migrate command) must ship in the same release increment as T-10a (model change).
They are not separable — a v2 model without a migration command breaks all existing
consumers immediately.

T-13 depends on T-12 (heartbeat / staleness check must exist) because RULE E checks
session staleness before verifying lock ownership.

### 13.3 Implementer breakdown

| Work area | Implementer |
|-----------|-------------|
| T-10a,b,c,d — state model, service, CLI, migrate | `software-engineer-python` |
| T-11 — three-layer lock architecture | `software-engineer-python` |
| T-12 — heartbeat, TTL, doctor LOCK-* | `software-engineer-python` |
| T-13 — RULE E, sdd-post-gate.sh, hook injection (3 runtimes) | `software-engineer-python` (gate script) + `devops-engineer` (injection into settings.json, hooks.json, opencode.json) |
| Race reproduction tests, lock state machine tests, hook integration tests, LOCK doctor tests | `qa-engineer` |

Devops-engineer cannot complete hook injection until T-13's hook scripts are finalized
by software-engineer-python. This is the only inter-agent sequencing dependency.

---

## 14. Open questions

### OQ-1 — `context bind` fail-open scope [RESOLVED by ADR D-3]

**Question:** Should the gate fail-closed when no `DADAIA_SESSION_ID` is set, forcing all
users to bind before any write?

**Resolution:** Fail-open. The gate exits 0 (allows) when `DADAIA_SESSION_ID` is absent.
This preserves backward compatibility for existing workflows that do not yet use session
binding. Lock enforcement activates progressively as users adopt `context bind`. The
operator accepted this trade-off in the dispatch briefing.

### OQ-2 — Workspace lock timeout behavior [RESOLVED by ADR D-4]

**Question:** On a workspace fcntl lock timeout (5 s), should the CLI retry or fail-fast?

**Resolution:** Fail-fast. Raise `WorkspaceLockTimeoutError` with the current holder PID
(from the lock file). The operator or script can decide to retry.

### OQ-3 — `sdd-post-gate.sh` runtime compatibility [DEFERRED to PLAN — operator-confirmed]

**Operator decision (grill-me 2026-05-30):** Defer to PLAN. Keep the working assumption
below; devops-engineer must verify per-runtime post-tool hook support before PLAN is
finalized, and fall back to the inline-into-gate mechanism only if a runtime fails. This
is a conscious deferral, not an unresolved gap — it does not block SPEC approval.

**Question:** Do Claude Code, Codex, and OpenCode all support a separate post-tool hook
file registered in the same settings JSON as the pre-tool hook? Specifically: does
OpenCode's `opencode.json` `hooks.after_tool_call` work with a shell script path (vs.
inline command)?

**Working assumption:** Yes, per ADR D-6 (devops-engineer is instructed to verify).
If a runtime does not support a separate post-tool hook, the heartbeat renewal must be
handled by an alternative mechanism (e.g., inlining the heartbeat logic into
`sdd-spec-gate.sh` as an exit hook rather than a separate post hook). Devops-engineer
must confirm before PLAN is finalized.

### OQ-4 — `dadaia migrate --yes` in CI [RESOLVED by ADR D-8]

**Question:** Is it safe to run `dadaia migrate --yes` non-interactively in CI pipelines?

**Resolution:** Yes. The `--yes` flag bypasses interactive confirmation; the migration is
idempotent on v2 workspaces (no-op). CI pipelines must add `dadaia migrate --yes` to
their setup step after upgrading to 2.0.0. This is documented in the 2.0.0 release notes
(product-engineer CLOSURE deliverable).

---

## 15. Concurrency note

This release directory (`specs/releases/spec-context-session-locks-v1/`) is disjoint from
all active releases:

- `go-open-source` — all code complete; T-GOS-OPS1 is an operator action (no file
  writes). Zero write-set overlap.
- `spec-context-tree-v2` — writes to `public/scaffold/`, `public/templates/`,
  `features/spec_context/doctor.py`, `cli/commands/`, and `sdd-spec-gate.sh`.
  R2 writes to `core/models/`, `infrastructure/json_context_store.py`,
  `features/spec_context/service.py`, and adds `sdd-post-gate.sh`. The overlap in
  `features/spec_context/doctor.py` and `sdd-spec-gate.sh` is expected: R1 adds TREE
  invariants and removes the legacy root-TASKS.md fallback; R2 adds LOCK invariants and
  RULE E. These are additive, non-conflicting changes, but they must not be implemented
  in parallel — R2 must start only after R1 is CLOSED.
- `agent-monitoring-r2-v1` — agent monitoring; no overlap with spec_context or hooks.

---

*Product Engineer — dadaia-workspace | 2026-05-30*
