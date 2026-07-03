---
slug: sdd-gate-v3
title: sdd-gate-v3
category: product
tldr: "SDD gate: merged pre_gate PreToolUse (root-whitelist→venv-guard→SDD); git chokepoints pre-commit/pre-push; lease O_EXCL CAS + pid veto + self-recognition."
summary: >-
  Two-layer enforcement. (1) Python hooks: PreToolUse runs through ONE merged
  entrypoint — `dadaia_workspace.hooks.pre_gate` — which reads stdin once and
  evaluates the policies in fixed order root-whitelist → venv-guard → SDD gate,
  first-block-wins, each policy fail-open (PROTECTED is the only fail-closed path).
  The SDD classifier is context-relative (ADDITIVE allows with no lease, MEMORY gated
  by phase, FROZEN blocks — incl. the per-artifact _archives matched BEFORE ADDITIVE
  (R-2), MUTATING acquires the TTL-lease via O_EXCL CAS with PID veto); a multi-file
  apply_patch classifies ALL headers (most restrictive verdict wins); READ is
  non-acquiring. PostToolUse renews the heartbeat via the by-session index (no full
  scan) and runs the advisory reconciler (never blocks). (2) Git chokepoints: the
  pre-commit lease gate (DP-4 chain, zero-false-block, advisory ALLOW+WARN
  degradation) and the mechanical pre-push security-verdict gate (metrics.commit_sha
  per pushed sha) — they run independently of harness hooks. Tunables in
  core/kernel_tunables.py; hook latency in .dadaia/logs/hook-latency.jsonl.
tags:
- sdd
- gate
- hooks
- enforcement
- chokepoints
token_estimate: 3425
last_updated: '2026-07-03'
release_origin: v0.1.53
---

Assets: `python -m dadaia_workspace.hooks.pre_gate` (PreToolUse, single entrypoint) · `python -m dadaia_workspace.hooks.sdd_post_gate` (PostToolUse, heartbeat + advisory reconciler) · `python -m dadaia_workspace.hooks.ctx_inject` · git hooks `pre-commit-lease-gate.sh` + `pre-push-ci-gate.sh` (installed via `dadaia ci install-hook`; backends `dadaia ci pre-commit-check` / `dadaia ci push-gate-check`). The `sdd_gate` and `root_whitelist` modules are thin policy modules consumed by `pre_gate` (`evaluate_payload()`); their legacy `main()`s are kept for one release.

## Purpose

Deterministic enforcement of the SDD lifecycle in two complementary layers.

**Layer 1 — harness hooks (file-write tools + narrow Bash).** A single PreToolUse
entrypoint (`dadaia_workspace.hooks.pre_gate`) intercepts tool invocations in Claude
Code and interactive Codex: it reads the stdin envelope **once**, and evaluates the
registered policies in fixed order, **first-block-wins**:

1. **root-whitelist** — classifies by the **first component of the root-relative
   path**: blocks any write whose first component would create a new top-level entry
   outside the canonical whitelist — including writes NESTED under a new
   non-whitelisted top-level (e.g. `foo/bar/baz.txt` blocks if `foo/` does not exist
   and is not whitelisted). Existing entries and globs from
   `.dadaia/states/root_exceptions.txt` pass.
2. **venv-guard** (Bash events only) — a narrow first-token check: `dadaia`,
   `pip`/`pip3`, or `python -m dadaia_workspace` commands not rooted in
   `.dadaia/.venv/bin/` are blocked with the corrected command in the message.
   pytest/ruff/mypy are NOT covered; `$DADAIA_BIN` and the workspace-absolute form are
   allowed. No general shell parsing — only fixed leading-token patterns.
3. **SDD gate** — the policy in `features/spec_context/gate_policy.py`; the hook
   delegates, never re-derives.

Allow requires every policy to allow; each policy is fail-open — a crashing policy
never blocks the harness, and a MUTATING write with no resolvable context also passes
fail-open; PROTECTED follows the only fail-closed path. One interpreter
spawn per tool call (seed-5: one registered PreToolUse command per runtime).

The SDD classifier is **context-relative**: for a path under `repos/<slug>/...`, the
`repos/<slug>/` prefix is stripped and the ordered `specs/` taxonomy is applied to the
remainder — the same one that governs workspace-root paths. An in-repo remainder with
no class is MUTATING (never UNGATED). A multi-file `apply_patch` has **all** its
`*** Add/Update/Delete File:` headers classified (`_common.target_paths()`); the most
restrictive verdict wins — one FROZEN/PROTECTED/blocked file blocks the whole patch.

| Class | Paths | Decision |
|-------|-------|----------|
| PROTECTED | `.dadaia/sessions/**` (workspace-root) | Block always — the only fail-closed path (SEC-01); evaluated first; the subtree is CLI-owned and the unconditional block protects the `.ptr` from forgery |
| FROZEN (R-2: before ADDITIVE) | `specs/backlog/_archive/`, `specs/audits/_archive/`, `specs/bugs/_archive/` (root **and** in-repo; trailing `/` load-bearing) | Block always for file tools — the per-artifact `_archive`s are matched BEFORE the ADDITIVE prefixes (otherwise `specs/bugs/` would swallow `specs/bugs/_archive/` as ADDITIVE); archive moves run via `git mv` (Bash), outside the file-tool envelope |
| ADDITIVE | `specs/backlog/**`, `specs/bugs/**`, `specs/audits/**` (root **and** in-repo); `.dadaia/reports/**`, `.dadaia/handoff/**`, `.dadaia/tmp/**` (root) | Allow — zero lease read/write |
| MEMORY | `specs/memory/**` (root **and** in-repo) | Allow only in DEFINITION or CLOSURE phase; block otherwise |
| FROZEN | `specs/_archive/**` (root **and** in-repo) | Block always |
| MUTATING | `specs/releases/**`, production tree, and every unclassed in-repo path | READ-mode ⇒ block non-acquiring; otherwise lease acquire (O_EXCL CAS + pid veto); block on live-lease conflict |
| UNGATED | Other workspace-root paths (e.g. outside specs/.dadaia) | Allow |

**Layer 2 — git chokepoints (an envelope that does NOT depend on harness hooks).**
Arbitrary writes via Bash remain outside the file-tool envelope (the gate never parses
shell command strings), but the lifecycle outcomes that matter are gated
deterministically in git hooks, which run even when no harness hook fired:

- **pre-commit lease gate** — a `git commit` into a Spec Context repo from a session
  that does not hold the context's MUTATING lease is blocked with an actionable
  message. Holder identity chain (DP-4): (1) no lease, or a stale lease with a dead
  holder pid ⇒ allow (ADDITIVE work commits freely; zero-false-block);
  (2) `DADAIA_SESSION_ID` equal to the holder's sid ⇒ allow; (3) the holder's recorded
  pid is an ancestor of the invoking process — via the read-only `ProcessAncestry`
  port (Linux `/proc` walk; macOS `ps -o ppid=`; Windows Toolhelp32 read-only; NEVER
  `os.kill`) ⇒ allow; (4) ancestry unavailable/indeterminate, **or holder pid dead**
  (one cannot descend from a dead process — pid-veto canon) ⇒ **ALLOW with a logged
  WARN** — zero-false-block dominates; the chokepoint degrades to advisory on that
  platform. Block ONLY on a live foreign lease with a positive non-match.
  Context derived from the repo's path, never first-ALIVE. The same
  `dadaia ci pre-commit-check` backend also runs the scoped BL-* backlog doctor on
  staged `specs/backlog/` paths ([[sdd-bug-backlog-governance]]).
- **pre-push gate** — the same pre-push hook runs the CI preflight AND the mechanical
  security-verdict check: for each non-zero `<local-sha>` of the stdin ref lines,
  there must exist a `security-reviewer` handoff with `"verdict": "APPROVED"` whose
  `metrics.commit_sha` equals that sha (single canonical field; no `scope` fallback;
  never `rev-parse HEAD`). Branch deletions (zero sha) and tag-only pushes pass with
  no verdict; a stale APPROVE (old sha) does not pass; commits are never
  review-blocked.
- **advisory reconciler (PostToolUse)** — flags out-of-lease dirty MUTATING paths in
  the bound context's repo (`RECONCILER_FLAG` event in
  `.dadaia/logs/lock-events.jsonl`); NEVER blocks, exit 0 on all branches
  (incl. `git status` failure); per-session throttle
  (`.dadaia/tmp/reconciler-last-<sid>`, TTL from `kernel_tunables`).
- **Escape-hatch honesty:** chokepoints are git hooks — `--no-verify` bypasses them.
  The posture is deterministic-at-the-chokepoint, not unbypassable; the doctor's
  lease↔session coherence (SPEC-DOC-029) remains the post-hoc backstop.

**What is NOT gate mechanism (agent/PM discipline):** the gate does not read
`TASKS.md`, does not check `**Status:** Aprovado`, does not check `[-]` markers, and
does not validate persona `paths.write_allowlist`. Those laws are coordinated
discipline (workspace-protocol, dadaia-task-manager) with post-hoc verification by
reviewers and `dadaia specs doctor`.

**Mode-resolution chain (READ non-acquiring):** a session whose resolved mode is
READ/BOUND_READ is non-acquiring — a MUTATING write is blocked **before** any lease
call; ADDITIVE flows. Resolution order: `DADAIA_MODE` env (operator escape) → the
session record's `mode` keyed by the harness-native sid → the **context incumbent's**
mode (`sessions/runtime/<ctx>.ptr`, refreshed by `bind`; ignored when a live lease
names another sid — anti-downgrade guard) → default `IMPLEMENTATION`. The gate
classifies by **path** only, never by format/extension; each path-class decision is
stated once in the table above.

**ctx-inject with session attribution:** the `ctx_inject` hook (same package) honors a
bind-epoch marker (`.dadaia/states/bind_epoch/<ctx>`) only when the marker's recorded
**ancestry pid chain** — written by `dadaia context bind` as one decimal pid per line,
nearest-first, capped at 8 (`session_identity.write_bind_epoch`) — **CONTAINS the hook's
own harness pid** (membership test, `hooks/ctx_inject.py`). The chain replaced the old
single-pid content, whose ephemeral-shell gap caused cross-session contamination. A bind
from another session never steals this session's injection; an empty/legacy marker
(empty chain) is non-attributable ⇒ ignored (generic preflight, never another session's
context). Bind/injection mechanics: [[context-management]].

**Tunables and telemetry:** all kernel constants (lease TTL, GC TTLs, CAS retries,
sentinel TTL, reconciler throttle) live in `core/kernel_tunables.py` (pure constants,
zero I/O); hooks and lease import them from there directly — the transitional
`lease.LEASE_TTL_SECONDS` re-export is gone; `kernel_tunables.LEASE_TTL_SECONDS` is the single name. Each `pre_gate` invocation appends a
`{ts, hook, event, duration_ms}` record to `.dadaia/logs/hook-latency.jsonl`
(best-effort, fail-open — a missing/non-writable logs dir never changes the verdict or
the exit code; no payload, paths, or session ids).

## Lease acquire (O_EXCL CAS + stable-session-identity)

For lease-taking MUTATING writes, the gate calls `lease.acquire(ctx, session_id,
release, mode, pid_probe)` (in-process; the `OsProcessProbe` pid-probe is injected by
the hook — `features/lease.py` never imports the adapter). Acquire uses an O_EXCL
sentinel file (the only path — no read-then-write TOCTOU); `renew_heartbeat` runs
inside the same CAS. The record carries `pid` — that of the **long-lived harness
process**, resolved by `sdd_gate._resolve_holder_pid` (`harness_pid`/`parent_pid`/
`ppid` from the stdin payload, else `os.getppid()`) and threaded down to
`lease.acquire`; never the hook's ephemeral subprocess pid. Decision tree:

1. `.ptr` match → unconditional **RENEW** (the incumbent, even after a relaunch); the
   replaced sid's by-session index entry is removed in the same transition (v0.1.50
   index hygiene — no dangling entry).
2. Record with the same `session_id` → **RENEWED**, even past-TTL (holder-safe: a holder never loses its own lease to its own staleness).
3. **Self-recognition** (v0.1.50, rotated-sid fix): record pid == the acquiring
   session's harness pid **AND** the recorded old sid's session record
   (`.dadaia/sessions/<old_sid>.json` — PROTECTED, CLI-owned) names that **same** pid
   (lineage evidence) → **RENEW** under the new sid; the old sid's index entry is
   removed. Both conjuncts are required — pid equality alone never renews, so a test
   or process that models a foreign holder with its own pid still blocks.
4. Record absent, or TTL-stale with the holder pid dead/absent → **ACQUIRED** (takeover).
5. Live foreign record — TTL-fresh **or** TTL-stale with a live pid (**PID veto**, `core/lock_liveness.is_stale`) → **LockHeldError**; the gate blocks with a yield message. The message reports holder and heartbeat and **never** instructs rebind, relaunch, or steal.

**Veto tri-state (v0.1.50):** the hook's `_active_field` reader distinguishes a
readable phase/release (str) from a legitimately absent `ACTIVE.md`
(`FileNotFoundError` → `""` → `veto_release = "none"`, release-aware reclaim between
releases still fires) from an **unreadable** one (`OSError` → `None` →
`veto_release = None`, which SKIPS the release-mismatch reclaim in `is_stale` and
preserves the pid veto — an I/O failure can never bypass the no-steal invariant). The
`veto_release` is threaded gate → `gate_policy.evaluate` → `lease.acquire`
(`_UNSET_RELEASE` sentinel decouples it from the record's own release field).

**Session-id resolution (v0.1.50):** `hooks/_common.resolve_session_id` order is
`DADAIA_SESSION_ID` (operator override) → **stdin payload `session_id`**
(harness live-truth) → inherited `CLAUDE_CODE_SESSION_ID` → `CODEX_SESSION_ID` — the
payload now outranks possibly-stale inherited env, so a harness relaunch inside the
same shell resolves its own sid instead of the previous session's.

**By-session index (structural atomicity):** `acquire`/`steal`/`release` write and
remove the `ctx_locks/by-session/<sid>.json` entry **inside the SAME O_EXCL sentinel
CAS** that writes the lock record — one atomic unit per transition; record-write and
index-write cannot diverge (a lost entry would starve renewal and reopen the
lease-theft class). Fallback: full scan when the by-session directory is absent
(migration window).

**Heartbeat (PostToolUse):** `sdd_post_gate` resolves the session id from the **stdin
payload** (harness-native; `DADAIA_SESSION_ID` is operator override only) and renews
the heartbeat of the leases that sid holds, via the by-session index — **no full scan
of the lock dir** when the session holds nothing, and never via
`DADAIA_CONTEXT`→first-ALIVE. `renew_heartbeat` never recreates an absent or
foreign-sid record — after a `context release` deletes the record, resurrection is
structurally impossible (DP-3: no session-record-based renewal guard exists; an
unbound holder with no session record keeps renewing — v0.1.10 invariant FR-R2-01
preserved). Runs fail-open exit 0. On Claude Code the matcher is match-all `*`; on
Codex the PostToolUse block comes **without** a matcher (canonical match-all form) —
heartbeat after **every** tool, incl. Bash; a single call above the TTL is covered by
the PID veto (live harness pid ⇒ block, not steal).

**Steal and GC:** a TTL-stale lease whose holder pid is dead/absent is reclaimed
automatically by the next acquire (reclaim-iff-stale). `dadaia lock steal <ctx>` is the
manual emergency reclaim, **probe-gated**: it refuses while the holder's recorded pid is
alive, even past-TTL (a pre-`pid` record follows the pure TTL rule; `lease._main`
threads the same probe — no probe-less acquire/steal path exists). `dadaia doctor --fix`
reclaims via **LOCK-GC** the TTL-expired leases whose holder is dead or unprobeable —
a holder with a live pid is NEVER reclaimed — and cleans orphan sentinel files.

**Canonical unblock:** if the gate blocks on a live foreign lease, the session waits
for the holder to finish or die — a dead holder is freed by TTL+probe on the next
acquire. No manual action is needed; ADDITIVE writes keep flowing.

## Usage flow

1. An agent invokes a write tool (e.g. `Write` on `repos/<slug>/src/foo.py`) or a Bash command.
2. The harness executes `python -m dadaia_workspace.hooks.pre_gate` passing JSON on stdin with `tool_name`, `file_path`/`command`, and `session_id`.
3. `pre_gate` reads stdin once and runs root-whitelist → venv-guard (Bash) → SDD gate; first-block-wins.
4. The SDD policy resolves the workspace root, derives the context slug **PATH-first** from the write target, reads the context's `releases/ACTIVE.md` for the phase, resolves sid and mode, and classifies context-relative (all headers in `apply_patch`).
5. For MUTATING: READ-mode blocks non-acquiring; otherwise `lease.acquire` with the pid-probe.
6. Allow → exit 0 (silent); Block → STDOUT JSON `{"decision":"block","reason":"..."}`; latency appended to `hook-latency.jsonl`.
7. After each tool call (PostToolUse), `sdd_post_gate` renews the heartbeat via the by-session index and runs the advisory reconciler (throttled).
8. At the chokepoints: `git commit` goes through the pre-commit lease gate (DP-4 chain); `git push` goes through the CI preflight + push-gate-check (security verdict per sha).

```mermaid
sequenceDiagram
    participant T as Tool Write/Edit/Bash
    participant PreH as PreToolUse Hook
    participant PG as hooks/pre_gate.py (single entrypoint)
    participant C as gate_policy.py (context-relative)
    participant L as lease.py (O_EXCL CAS + pid veto)
    participant PostH as PostToolUse Hook (all tools)
    participant GitC as git pre-commit (lease gate DP-4)
    participant GitP as git pre-push (preflight + security verdict)
    T->>PreH: tool call
    PreH->>PG: stdin JSON (read once)
    PG->>PG: root-whitelist
    PG->>PG: venv-guard (Bash only)
    PG->>C: SDD gate: classify (strip repos/<slug>/; all headers)
    alt PROTECTED
        PG-->>PreH: block (fail-closed)
    else ADDITIVE
        C-->>PG: allow (no lease I/O)
    else MEMORY outside DEFINITION/CLOSURE
        PG-->>PreH: block
    else FROZEN
        PG-->>PreH: block
    else MUTATING lease-taking
        PG->>L: acquire(ctx, sid, release, mode, pid_probe)
        alt ACQUIRED or RENEWED
            PG-->>PreH: exit 0 (allow)
        else LockHeldError (TTL-fresh or live pid)
            PG-->>PreH: block with yield message
        end
    end
    PreH-->>T: allow/block (first-block-wins)
    T->>PostH: tool completed
    PostH->>L: renew heartbeat (by-session index, CAS)
    PostH->>PostH: advisory reconciler (never blocks)
    T->>GitC: git commit
    GitC->>GitC: DP-4 (no-lease/env-sid/ancestry/indeterminate⇒ALLOW+WARN)
    T->>GitP: git push
    GitP->>GitP: preflight + APPROVED security handoff per pushed sha
```

## Typical trigger

Automatically invoked on every Write/Edit/MultiEdit/NotebookEdit/Bash in agent sessions (PreToolUse via `pre_gate`), after every tool call (PostToolUse), and on every `git commit`/`git push` in Spec Context repos (chokepoints, harness-independent). The operator rarely interacts directly — only when receiving a `{"decision":"block"}` or a chokepoint block that needs to be understood.

## Differentiator

Without this kernel, agents can write anywhere at any time — memory becomes a changelog, the archive gets accidental edits, two agents mutate the same context simultaneously, and the Bash hole would leave commits/pushes ungoverned. Context-relative classification makes the classes hold where the real specs live; the PID veto guarantees a live holder never has its lease stolen; the by-session index makes renewal O(1) and structurally lossless; the git chokepoints close the Bash hole at the outcomes that matter (commit/push) without shell parsing and without depending on harness hooks (covering even headless Codex); and the zero-false-block requirement (ADR-G1) is binding — in doubt, the chokepoint degrades to advisory (ALLOW+WARN) rather than blocking the legitimate holder.

## Runtime state touched

  * Read-only by the PreToolUse gate: the context's `releases/ACTIVE.md` (phase/release), `.dadaia/sessions/<id>.json` (mode via `session_identity`).
  * Read-write (in-process via `lease.py`): `.dadaia/states/ctx_locks/<ctx>.lock.json`, `.dadaia/states/ctx_locks/<ctx>.lock.sentinel`, `.dadaia/states/ctx_locks/by-session/<sid>.json` (same CAS transaction), `.dadaia/sessions/runtime/<ctx>.ptr`.
  * Written by PostToolUse: heartbeat renewal of this sid's lock records (via the by-session index); best-effort refresh of `last_seen_at` in the session record; `RECONCILER_FLAG` events; throttle marker `.dadaia/tmp/reconciler-last-<sid>`.
  * Logs: `.dadaia/logs/lock-events.jsonl` (append-only; acquire, release, steal, HEARTBEAT, RECONCILER_FLAG) · `.dadaia/logs/hook-latency.jsonl` (telemetry `{ts, hook, event, duration_ms}`).
  * Git hooks: `.git/hooks/pre-commit` + `.git/hooks/pre-push` (installed by `dadaia ci install-hook`; fail-closed runner resolution: `$DADAIA_BIN` → workspace venv → poetry → repo venv → fail).
  * Output: STDOUT JSON when blocking; exit 0 (silent) when allowing.

## Dependencies

  * Depends on [[context-management]] (session record persisted by `dadaia context bind`; lease records created by the inline acquire; `context release` releases the lease).
  * `core/kernel_tunables.py` — single home of the kernel constants (leaf: imports from no layer).
  * `features/spec_context/session_identity.py` — single owner of the pointers and session records the gate and post-gate consume.
  * `infrastructure/process_probe_adapter.OsProcessProbe` (platform seam `has_os_kill_liveness`) — injected by the hook; TTL-only fallback when unavailable.
  * `ProcessAncestry` port (core protocol; Linux `/proc` / macOS `ps` / Windows Toolhelp32 read-only adapters, selected at the composition root) — consumed by the pre-commit lease gate and by the `context release` default flow.
  * Depends on [[agent-orchestration]] indirectly (active releases produced by the product-engineer during orchestration).
  * Environment variables (operator overrides only; none is required in a real harness): `WORKSPACE_ROOT`, `DADAIA_CONTEXT`, `DADAIA_SESSION_ID`, `DADAIA_MODE`, `DADAIA_BIN`.

### Hook injection per runtime (per-harness enforcement matrix)

Runtime| PreToolUse (`pre_gate`)| PostToolUse| Git chokepoints| Posture
---|---|---|---|---
Claude Code| `.claude/settings.json` matcher `Edit\|Write\|MultiEdit\|NotebookEdit\|Bash` → `python -m dadaia_workspace.hooks.pre_gate` (single command)| matcher `*` (all tools)| yes| deterministic: hooks + chokepoints
Codex interactive (TUI)| `.codex/hooks.json` matcher `^(apply_patch\|Edit\|Write\|Bash)$` → `pre_gate`| **no matcher** (canonical match-all)| yes| deterministic: hooks + chokepoints
Codex headless (`codex exec`)| **no — exec fires no hooks** (upstream codex-cli 0.139.0 defect; live-verified, `tests/integration/codex_live/`, opt-in `DADAIA_CODEX_LIVE=1`)| no| yes| **chokepoints only**
PI (`pi`) — Layer 1 interactive| TS extension `.pi/extensions/dadaia-sdd-gate.ts` registers the `tool_call` hook; maps write→Write/edit→Edit and delegates to `pre_gate` via subprocess (venv-path resolution); **active post-trust** (WS-PI-4)| no post-hook (Ring-1 effect is pre-disk only via tool_call)| yes| deterministic post-trust + chokepoints; `.pi/**` is post-trust executable
PI — Layer 2 worker (`PI_HEADLESS`)| n/a — headless `pi --mode json` worker, no entry hook| n/a| yes| Ring-2 (git-diff) + chokepoints (no Ring-1; distinct from Layer 1)
