# TASKS — Release: spec-context-session-locks-v1

**Status:** Aprovado
**Release ID:** spec-context-session-locks-v1
**Owner:** product-engineer
**Opened:** 2026-05-30

> **Activation gate:** Implementation must NOT begin until `spec-context-tree-v2` phase =
> ARCHIVED AND `go-open-source` phase = ARCHIVED AND SPEC.md + PLAN.md both have
> `**Status:** Aprovado`.
>
> **OQ-3 gate (T-13):** `devops-engineer` must confirm OpenCode post-tool hook
> compatibility before T-13 starts. If a runtime lacks post-tool hook support, the
> heartbeat must be inlined. Report to product-engineer before T-13 is opened.

---

## T-10a — Models + store: `ContextState`, `SpecContextProject`, `JsonContextStore v2`

**Owner:** [software-engineer-python]
**Depends on:** activation gate (must be first task; T-10b, T-10c depend on this)
**SPEC cluster:** §3 T-10a

Replace `ContextState` enum with `ALIVE/DEAD` only — no aliases; remove all `"ativo"` /
`"inativo"` references from the entire codebase in the same commit. Update
`SpecContextProject`: remove `is_primary` and `activated_at`; add `alive_since: str |
None` and `dead_since: str | None`. Bump `JsonContextStore._VERSION` to `"2"`. Implement
`SchemaVersionError` on v1 load (triggers on `schema_version: "1"` or `state: "ativo"`).
Implement `_to_dict`/`_from_dict` v1 detection (migration-only path; not at runtime).
Add the raw-store-access invariant comment. Remove doctor INV-1, INV-2, INV-3, INV-6
(guard `is_primary` logic that no longer exists); rename INV-4/INV-5 for ALIVE/DEAD.

**Done criterion:** AC-T10a-1..7 all pass. All code references to ATIVO/INATIVO/
is_primary/activated_at removed. `JsonContextStore._VERSION == "2"`.

[x] T-10a

---

## T-10b — Service methods: `alive()`, `dead()` replacing `activate()`, `deactivate()`, `promote()`

**Owner:** [software-engineer-python]
**Depends on:** T-10a (models + store must exist)
**SPEC cluster:** §3 T-10b

Remove `SpecContextService.activate()`, `deactivate()`, and `promote()` — no dead code.
Add `alive(name: str)` (transitions DEAD → ALIVE, sets `alive_since`, clears `dead_since`,
clones repo if absent; idempotent on already-ALIVE) and `dead(name: str)` (transitions
ALIVE → DEAD, sets `dead_since`, calls `shutil.rmtree` outside workspace lock but inside
per-context lock; raises `ContextLockedError` when implementation lock held). Note: Lock
1 and Lock 2 (from T-11) are not yet present here — this task implements the service
logic; locking is wired in T-11.

**Done criterion:** AC-T10b-1..5 all pass. No `activate`, `deactivate`, `promote`
imports or dead code anywhere.

[x] T-10b

---

## T-10c — `dadaia migrate` command (state-file migration, idempotent, consent-required)

**Owner:** [software-engineer-python]
**Depends on:** T-10a (must ship in the SAME release increment as T-10a — not separable)
**SPEC cluster:** §3 T-10c

Implement `dadaia migrate [--dry-run] [--yes]` performing the 12-step migration sequence
in SPEC §3 T-10c: detect schema_version, map states (`"ativo"` → `"alive"`,
`"inativo"` → `"dead"`), rename `activated_at` → `alive_since`, remove `is_primary`,
add `dead_since: null`, set `schema_version = "2"`, write atomically (`tmp →
os.replace()`), delete `primary_context.json`, create `.dadaia/sessions/`,
`.dadaia/locks/implementation/`, `.dadaia/states/ctx_locks/`, append migration event to
`lock-events.jsonl`. Implement the loud migration guard that intercepts ANY `dadaia
context` command on a v1 workspace and prints the migration prompt (non-zero exit).

**Done criterion:** AC-T10c-1..6 all pass. Guard message contains `"dadaia migrate"`.
Migration idempotent on v2 (no-op). All 12 directories/files created by migration exist
post-run.

[x] T-10c

---

## T-10d — New CLI verbs: `context alive`, `context dead`, `context bind --mode`, `context release`

**Owner:** [software-engineer-python]
**Depends on:** T-10b, T-10c (service methods and migration command must exist)
**SPEC cluster:** §3 T-10d

Add four new CLI verbs — `dadaia context alive <name>`, `dadaia context dead <name>`,
`dadaia context bind <name> --mode read|spec|implementation|review [--release <id>]`,
`dadaia context release` — per the full semantics in SPEC §3 T-10d. Remove old verbs
`activate`, `deactivate`, `promote`, `use` (exit non-zero with pointer to new verbs).
Implement `dadaia context bind --mode implementation` (requires `--release`; generates
`sess_<uuid4>` session ID; writes session file; acquires Lock 3 if FREE; raises
`LockHeldError` if HELD; checks for non-stale BOUND_REVIEW sessions and raises
`ImplementationBlockedByReviewError`). Implement `dadaia context bind --mode review`
(writes session file with `mode: BOUND_REVIEW`; no Lock 3 file created; raises
`ReviewBlockedByImplementationError` if impl lock HELD for same context/release). Update
`dadaia context show --json` to include `session` sub-object (null if no binding).
Print the unmistakable `eval` command reminder in bind output. Note: Lock 1 is wired in
T-11; this task implements the CLI surface and session-file creation logic.

**Done criterion:** AC-T10d-1..10 all pass. AC-SES-1..4 (session identity ACs) pass.
`eval $(dadaia context bind ...)` exports `DADAIA_CONTEXT`, `DADAIA_SESSION_ID`,
`DADAIA_MODE` correctly.

[x] T-10d

---

## T-11 — Lock architecture (ADR D-4): three-layer locking

**Owner:** [software-engineer-python]
**Depends on:** T-10d (full T-10 cluster must be complete)
**SPEC cluster:** §3 T-11

Wire Lock 1 (workspace-wide fcntl on `.dadaia/states/.ws_lock`, 5-second timeout,
`WorkspaceLockTimeoutError`) around ALL `spec_contexts.json` mutations: `alive()`,
`dead()` (for JSON write only), `create()`, `delete()`, `DoctorService.fix()`, `context
bind`, `context release`. Wire Lock 2 (per-context fcntl on
`.dadaia/states/ctx_locks/<slug>.lock`) around `git clone` and `shutil.rmtree`.
Implement Lock 3 state machine (FREE → HELD → STALE → RECLAIMED) with the JSON lock
file at `.dadaia/locks/implementation/<ctx>__<release>.json`. Implement Impl-XOR-Review
mutual exclusion at Lock 3 level: `ReviewBlockedByImplementationError` and
`ImplementationBlockedByReviewError` (both inherit `LockConflictError`). Implement audit
log (`lock-events.jsonl`, `O_APPEND`, events: ACQUIRED/RELEASED/STALE_DETECTED/
RECLAIMED/HEARTBEAT/BLOCKED_ATTEMPT). Add `.dadaia/states/.ws_lock` and
`ctx_locks/*.lock` to `.gitignore`.

**Done criterion:** AC-T11-1..12 all pass (lock state machine, concurrent alive tests,
BOUND_REVIEW mutual exclusion). R-1, R-3, R-4, R-5, R-8 closed (concurrency tests
demonstrate). AC-AUDIT-1 (audit log schema) passes.

[x] T-11

---

## T-12 — Heartbeat + TTL (300 s) + audited reclaim; doctor LOCK-1..LOCK-6

**Owner:** [software-engineer-python]
**Depends on:** T-11 (lock files and Lock 3 state machine must exist)
**SPEC cluster:** §3 T-12

Implement heartbeat renewal protocol: `renew_heartbeat(ctx, release, session_id)` renews
`last_seen_at` atomically (`tmp → os.replace()`); does NOT hold Lock 1 (heartbeat is
idempotent). Implement TTL staleness check: lock with `last_seen_at` older than
`ttl_seconds` (default 300 s) is STALE regardless of PID. PID liveness check as fast-
path (dead PID → STALE immediately). Implement `check_lock_state()` and audited
`reclaim()` (requires non-empty reason string; appends RECLAIMED event; raises
`LockActiveError` on HELD fresh lock). Add `dadaia context heartbeat` CLI command.
Implement doctor LOCK-1..LOCK-6 invariants per the table in SPEC §3 T-12: LOCK-1
(duplicate lock files → keep freshest, rename others `.conflicted`), LOCK-2 (lock for
DEAD context auto-delete), LOCK-3 (expired lock mark STALE, no delete), LOCK-4
(production mutation missing `task_id` — no fix, block closure), LOCK-5 (BLOCKED_ATTEMPT
event — surface, no fix), LOCK-6 (stale BOUND_REVIEW session for DEAD context auto-
delete). Error messages for STALE/blocked must include owner runtime, session ID, and
`last_seen_at`.

**Done criterion:** AC-T12-1..7 all pass. Doctor LOCK-1..6 tests pass (AC-DOC-L1..12).
R-10 closed (stale lock test demonstrates heartbeat expiry → STALE → reclaim cycle).

[x] T-12

---

## T-13 — RULE E in `sdd-spec-gate.sh` + `sdd-post-gate.sh` + hook injection (T-8 completion)

**Owner:** [software-engineer-python] (gate script + post-gate script)
**Owner (hook injection):** [devops-engineer] (inject into Claude Code, Codex, OpenCode
after scripts are finalized; blocked until software-engineer-python confirms scripts done)
**Depends on:** T-12 (heartbeat/staleness check must exist; RULE E checks staleness
before lock ownership); T-8a from `spec-context-tree-v2` (legacy root-TASKS.md fallback
already removed)
**SPEC cluster:** §3 T-13

**software-engineer-python:** Add RULE E to `sdd-spec-gate.sh` (after RULE D, before
RULE C) implementing the session identity resolution order (SPEC §6: `DADAIA_SESSION_ID`
env var first; fail-open if absent), session file staleness check, and the path-policy
matrix (SPEC §3 T-13 table: NO_SESSION fail-open / READ / SPEC / IMPLEMENTATION /
BOUND_REVIEW). For IMPLEMENTATION-mode sessions: resolve active release from the
implementation lock file (not `ACTIVE.md`) — this completes T-8 (ADR D-9). Implement
`sdd-post-gate.sh` (new public asset): read `DADAIA_SESSION_ID`; if absent, exit 0;
load session file; renew `last_seen_at` atomically; append HEARTBEAT event to
`lock-events.jsonl`. Register `sdd-post-gate.sh` in `manifest.json`.

**devops-engineer:** After scripts are confirmed by software-engineer-python, verify
that Claude Code (`hooks.PostToolUse[*]`), Codex (`post_tool_call`), and OpenCode
(`hooks.after_tool_call`) all support shell-script post-tool hooks. Wire both pre and
post hooks via `dadaia public install --target all`. If any runtime lacks post-tool hook
support, implement the fallback (inline heartbeat in pre-tool hook exit path) and report
to product-engineer.

**Done criterion:** AC-T13-1..10 all pass (session identity, path-policy matrix,
heartbeat). AC-REV-1..5 (BOUND_REVIEW gate behaviour) pass. Both hooks installed in all
three runtimes (`dadaia public doctor` exit 0 after install).

[x] T-13 [software-engineer-python]
[ ] T-13-hooks [devops-engineer]

---

## T-QA — Race tests, lock state machine tests, hook integration tests, LOCK doctor tests

**Owner:** [qa-engineer]
**Depends on:** T-13 and T-13-hooks (all implementation complete)
**SPEC cluster:** §11 (all acceptance criteria)

Write and run the full test suite per QA strategy (`.dadaia/reports/dadaia-workspace/
qa-engineer/2026-05-30T120000Z-test-strategy-spec-context-v2.html` §3, §4.3, §5, §7.2):
(1) 6 deterministic race reproduction tests using `threading.Barrier`/`threading.Event`
— no `time.sleep`; all threads joined with `timeout=5`; real `JsonContextStore` on
`tmp_path` (never `FakeContextStore`); must pass (not xfail) after R2 (AC-RACE-1..6);
(2) 9 lock state machine tests (AC-LOCK-1..9); (3) 12 lock architecture tests incl.
BOUND_REVIEW mutual exclusion (AC-T11-1..12); (4) 7 heartbeat/TTL tests (AC-T12-1..7);
(5) 10 hook integration tests (AC-T13-1..10); (6) 12 doctor LOCK invariant tests on real
`tmp_path` (AC-DOC-L1..12); (7) 5 BOUND_REVIEW mode tests (AC-REV-1..5). Enforce
coverage thresholds: `json_context_store.py` ≥ 95%, `service.py` ≥ 90%, `doctor.py` ≥
90% (AC-COV-1..3). Add CI check: `grep -r "time.sleep" tests/` returns no matches
without `# allowed-sleep` comment (AC-RACE-2). All tests pass with
`pytest --randomly-seed=last` (AC-RACE-6). Report green CI run as evidence.

**Done criterion:** `poetry run pytest` green; all ACs in §11 pass; coverage thresholds
met; `--randomly-seed=last` green.

[ ] T-QA

---

## Cross-release note

**This release (R2) depends on `spec-context-tree-v2` (R1) being ARCHIVED first.**
Both releases also depend on `go-open-source` being ARCHIVED. The internal ordering
within R2 is strictly sequential: T-10a → T-10b → T-10c → T-10d → T-11 → T-12 →
T-13/T-13-hooks → T-QA. T-10c must ship in the same commit or PR as T-10a (the MAJOR
break cannot exist without the migration command). T-13-hooks (devops-engineer) depends
on T-13 (software-engineer-python) being finalized — this is the only inter-agent
sequencing dependency within R2.
