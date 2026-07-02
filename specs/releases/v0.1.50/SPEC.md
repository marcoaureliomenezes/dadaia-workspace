# SPEC — v0.1.50 — Kernel Hardening

**Status:** Aprovado
**Branch:** `feature/v0.1.50` (base: `918589e2`, v0.1.49 closure)
**Origin:** operator-approved release sequence R2 (grill 2026-07-02). Disposes open bug
`bugs-append-bound-session-falls-through-to-cwd-specs`; consumes the two HIGH/MEDIUM
kernel entries below. Audit provenance: 2026-07-01 audit `20260701T201136Z-0bcd6c19`
findings F-1 (HIGH, empirically reproduced self-block), F-3, F-4, F-7.
**Consumes:** lease-kernel-identity-hardening, context-dead-exit-path

## 1. Problem

The spec-context kernel — the single deterministic lock plus the session-identity and
context-exit machinery — has four verified defect clusters:

1. **Lease self-block (F-1, HIGH).** `core/lock_liveness.py#is_stale` has no
   self-recognition: a holder whose recorded **harness pid equals the acquiring
   session's own pid** still raises `LockHeldError` when the session id rotated
   (same live process, new sid) — the holder blocks itself out of its own lease.
   Additionally, callers that read ACTIVE.md fail-soft can pass the *string* `'none'`
   (or an empty read) as `active_release`, which bypasses the pid-veto via the
   release-mismatch reclaim path — an I/O failure must never weaken the no-steal
   invariant (F-3).
2. **Session-id resolution prefers inherited env over harness truth.**
   `hooks/sdd_gate.py` resolves the session id with inherited env sids able to shadow
   the harness payload sid, which is how rotated-sid self-blocks arise; and the
   `.ptr`-match RENEW branch leaves a **dangling by-session index entry** for the
   replaced sid (F-7).
3. **SPEC-DOC-029 false forgery + state bleed (F-4).**
   `session_identity.coherence` compares lease-record session ids against session
   records without resolving the **UUID vs `sess_*` namespace split** through the
   by-session index, so a live holder can be reported as a forgery (ERROR) by
   `specs doctor`; and a `--specs-dir` doctor run does not isolate
   `workspace_state_dir`, letting the live workspace's lock state bleed into
   fixture-tree runs.
4. **`context dead()` exit path broken + resolver cwd fallthrough.**
   (a) `infrastructure/git_subprocess.py#push` runs plain `git push` whenever an
   upstream exists — under `push.default=simple` this fails when the upstream branch
   name differs from the local one; and it pushes even when `@{u}..HEAD` is empty.
   (b) `features/spec_context/service.py#dead` pre-scans `repo_path.rglob("*")` for
   non-writable files and refuses — but git loose objects are **0444 by design**
   (POSIX unlink needs parent-dir write, not file write), so `dead()` fails for any
   repo with at least one local commit; the scan also runs after the push phase, so a
   late refusal strands a half-dead context. (c) The `bugs append` CLI in a bound
   session wrote to a stray workspace-root `specs/` (the open bug): the resolver
   chain (env → session record → bind-epoch ancestry membership → cwd) exists, but
   the CLI call fell through to cwd — root cause to be pinned during implementation
   (candidates: the bugs CLI seam not threading `ancestry_pids`, the 8-pid chain cap
   not reaching the common ancestor, or a feature-level cwd-first default) — and the
   cwd fallback silently accepted a root-law-violating `specs/` dir.

## 2. Goals (what done means)

1. A live holder can NEVER be blocked out of its own lease: same recorded harness pid
   ⇒ RENEW, regardless of sid rotation. The pid-veto survives ACTIVE.md read
   failures.
2. `specs doctor` never reports a live, coherent holder as a forgery; `--specs-dir`
   runs never read the live workspace's lock state; no dangling by-session entries
   after RENEW.
3. `dadaia context dead` works for any repo with local commits: pushes with an
   explicit refspec (or skips when nothing to push) and removes the clone via
   `rmtree` with a chmod-and-retry error handler; all refusal pre-checks run BEFORE
   the push phase.
4. Every resolver-driven CLI (`bugs`, `migrate`, `specs`, `memory`, `newartifacts` —
   via ONE shared ancestry-threading seam) in a bound session resolves the bound
   context's specs dir; the cwd fallback refuses (or loudly warns on) a
   workspace-root `specs/` that violates the root whitelist. Bug
   `bugs-append-bound-session-falls-through-to-cwd-specs` resolved.

## 3. Functional requirements

### FR1 — Lease identity self-recognition + veto preservation

- **Acquire-seam self-recognition** (the acquire ladder in
  `features/spec_context/lease.py` — NOT `is_stale`, which stays a pure
  reclaimability predicate): a third identity rung after the `.ptr` match and the
  sid match — record `pid` equals the acquiring session's harness pid AND that pid
  is alive ⇒ RENEW (update sid/heartbeat, preserve holder state) instead of
  `LockHeldError`. The no-steal invariant for FOREIGN pids is unchanged by
  construction (the rung can only match this very process).
- `active_release` hygiene — **primary fix on the `is_stale` side**: treat non-SemVer
  sentinel strings (`'none'`, `''`) as `None` so the release-mismatch reclaim branch
  never fires on an I/O-failure sentinel (today `hooks/sdd_gate.py` does
  `_active_field(...) or "none"`, and that string bypasses the pid-veto). Reader-seam
  note: the hook's `release` variable is DUAL-USE (it is also the new lease record's
  `release` field) — any reader-side change must preserve a written record-release;
  the sentinel tolerance in `is_stale` is the load-bearing half.
- **Sid resolution seam = `hooks/_common.resolve_session_id`** (NOT `sdd_gate.py`,
  which merely calls it): exact precedence becomes `DADAIA_SESSION_ID` (explicit
  eval-flow override, stays first) > **harness payload sid** >
  `CLAUDE_CODE_SESSION_ID` > `CODEX_SESSION_ID`. Blast radius (deliberate): the same
  seam serves the PostToolUse heartbeat (`sdd_post_gate.py`) and ctx-inject — fixing
  it ONCE keeps gate, heartbeat, and injection sid-consistent by construction;
  duplicating sid logic in `sdd_gate.py` is forbidden (it would let the heartbeat
  renew a different sid than the lease records).
- Tests (unit, fixture-based): rotated-sid ⇒ RENEW never self-block; foreign live pid
  ⇒ still blocked; unreadable ACTIVE ⇒ veto intact; `'none'` string ⇒ veto intact;
  **pid-reuse edge**: record pid == acquirer pid BUT heartbeat stale + record.release
  ≠ active release ⇒ TAKEOVER semantics (holder state reset), never a RENEW that
  adopts stale foreign release/mode — self-recognition must not weaken the
  release-aware reclaim path; the frozen no-steal suite (§5 AC-1 list) stays green
  unchanged.

### FR2 — Coherence + by-session index hygiene

- `session_identity.coherence` — **holder-confirmation rule** (the by-session index
  carries no cross-namespace alias and its schema does NOT change — PLAN §Rollback):
  a live lock-holder that is CONFIRMED the true holder of the context (its own lease
  record + liveness evidence) is coherent even when the incumbent `.ptr` drifted
  (e.g. a later read-bind moved it); only a live holder with NO legitimizing
  evidence yields the SPEC-DOC-029 forgery ERROR.
- The `.ptr`-match RENEW branch removes (or rewrites) the replaced sid's by-session
  index entry — no dangling entries.
- Doctor `--specs-dir` runs receive an isolated `workspace_state_dir` (fixture runs
  never read `.dadaia/states/ctx_locks` of the live workspace).
- Tests: confirmed-live-holder coherence despite `.ptr` drift (no false forgery
  ERROR); genuine no-evidence holder still ERRORs; dangling-entry regression;
  `--specs-dir` isolation.

### FR3 — `context dead()` exit path

- `git_subprocess.push`: parse the upstream tracking ref and push with the explicit
  refspec `HEAD:<upstream-branch>`; skip the push entirely when
  `rev-list @{u}..HEAD` is empty. First-push (`-u origin <branch>`) behavior
  unchanged.
- `service.dead()`: delete the non-writable `rglob` pre-scan; use
  `shutil.rmtree(repo_path, onexc=<chmod-and-retry handler>)` (0444 git objects are
  normal); any surviving refusal pre-check (e.g. secret scan) runs BEFORE the push
  phase so a refusal leaves the context fully intact.
- Tests: fixture repo with a 0444 file under `.git/objects/` ⇒ `dead()` succeeds;
  upstream-name-mismatch push (fixture remote) ⇒ succeeds via refspec; nothing-to-push
  ⇒ no push call; refusal ordering regression (a failing pre-check leaves no push).

### FR4 — Bound-session resolution + cwd fallback guard

- **Root cause (pinned at definition review, 2026-07-02):** `cli/commands/bugs.py`
  calls the shared `resolve_specs_dir(specs_dir)` WITHOUT `ancestry_pids`, so the
  resolver degrades to single-`getppid()` equality and never matches the bind-epoch
  marker's ancestry chain; `cli/commands/newartifacts.py:94` is the correct reference
  seam (threads `ancestry_pids=_current_ancestry_pids()`). W4 verifies the pinned
  cause empirically before the fix commit (red integration test on the bound-session
  fixture).
- **Defect-class centralization (architecture review 2026-07-02):** FIVE per-command
  `_resolve_specs_dir` wrappers exist and FOUR omit `ancestry_pids` (`bugs.py`,
  `migrate.py`, `specs.py`, `memory.py`; only `newartifacts.py` is correct). The fix
  centralizes ancestry-threading in ONE shared CLI seam consumed by all five
  wrappers, so no command can forget it — eliminating the copy-paste class, not the
  single symptom.
- The cwd fallback: when resolution falls through to `cwd/specs` AND that directory
  sits at a workspace root whose whitelist forbids `specs/`, the CLI refuses with an
  actionable message (or requires `--specs-dir` explicitly) instead of writing there.
- Tests: bound-session fixture (bind marker + session record + ancestry chain) ⇒
  `bugs append` resolves the bound context's specs; stray root `specs/` fixture ⇒
  refusal/warning path; explicit `--specs-dir` always wins (unchanged).
- Closure: `resolved --release v0.1.50` event for the bug.

## 4. Non-goals

- No lease TTL/heartbeat semantics changes beyond self-recognition; no new lock
  kinds; kernel tunables untouched.
- No gate policy/path-class changes (v0.1.49 froze that surface).
- The `workflows ↔ lifecycle` cycle, import contracts, and CI wiring are R6
  (`import-boundary-enforcement`) — out of scope.
- No consumer-visible CLI surface changes beyond the FR4 refusal message.

## 5. Acceptance criteria

- **AC-1** Rotated-sid self-block reproduced by a RED test landed as its own commit
  PRECEDING the fix commit (git-log-verifiable TDD ordering); after the fix: RENEW
  (same pid), foreign live holder still never stolen. The **frozen no-steal suite**
  stays green with ZERO edits (`git diff --stat` empty on these paths):
  `tests/unit/features/spec_context/test_lease_pid_liveness.py`,
  `tests/unit/features/spec_context/test_doctor_lock_gc.py`,
  `tests/unit/features/spec_context/test_lease_main_probe.py`,
  `tests/unit/features/spec_context/test_lock_steal.py`,
  `tests/unit/features/spec_context/test_lease_toctou.py`,
  `tests/unit/cli/test_lock_steal.py`,
  `tests/unit/core/test_lock_liveness_session.py`,
  `tests/unit/core/test_lock_liveness_release_aware.py`,
  `tests/e2e/test_two_actor_lease.py`.
  (`tests/unit/features/spec_context/test_lease_by_session_index.py` is excluded
  from the frozen set — FR2's dangling-entry fix legitimately extends it.)
- **AC-2** SPEC-DOC-029: live coherent holder ⇒ silent; fixture forgery ⇒ still
  ERROR; `--specs-dir` run touches zero live `ctx_locks` files (assert via isolated
  state dir); no dangling by-session entry after RENEW.
- **AC-3** `dead()` succeeds on a fixture repo containing 0444 git objects and a
  mismatched-upstream branch; refusal pre-checks demonstrably run before any push.
- **AC-4** In a bound-session fixture, `bugs append` writes to the bound context's
  `specs/bugs/`; with only a root-law-violating cwd `specs/`, it refuses/warns
  (refusal message redaction-safe — no absolute operator-local paths echoed); the
  open bug carries a `resolved --release v0.1.50` event at closure. **Halt path
  (expected unused — root cause already pinned):** if the true seam somehow falls
  outside the W4 write set, the bug is re-`deferred` with the pinned root cause
  routed to backlog for the next release, this AC's `resolved`-event clause is
  explicitly waived, and closure proceeds only if all other ACs hold — never a
  silent drop (release-governance).
- **AC-5** `ruff format --check`, `ruff check`, `mypy --strict`, full `pytest` green
  locally and all CI jobs green on the PR.
- **AC-6** At closure: consumed entries removed with durable copies + ledger; memory
  updates (`sdd-gate-v3` self-recognition + veto hygiene; `context-management`
  dead-exit + resolution facts; `workspace-doctor` SPEC-DOC-029 refinement if its
  table changes) in CLOSURE phase; catalog + lint clean.

## 6. Risks

- Lease-kernel changes risk breaking the no-steal invariant — mitigated: the FOREIGN
  branch is untouched by design, the frozen no-steal suite must stay green with zero
  diffs, and self-recognition keys on pid equality + liveness only (it can only match
  this very process; two sessions sharing one harness pid serialize coarsely, per the
  NF-1 design).
- Sid-seam blast radius: `hooks/_common.resolve_session_id` also serves the
  PostToolUse heartbeat and ctx-inject — the shared single fix keeps all three
  consistent by construction; tests must cover the eval-flow `DADAIA_SESSION_ID`
  override staying first.
- `rmtree(onexc=…)` on Windows: the chmod-and-retry handler is the documented
  cross-platform pattern; the `-cross` CI jobs cover it.
- FR4's root cause is pinned (bugs CLI seam missing `ancestry_pids`; empirical,
  definition-review verified) — the HALT branch in AC-4 is a low-probability safety
  valve with a defined bug disposition (re-`deferred` with reason), never a silent
  drop or a silent scope widening.
