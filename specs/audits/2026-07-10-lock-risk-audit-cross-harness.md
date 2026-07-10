# CRITICAL AUDIT: dadaia-workspace lock and lease risk across Codex, PI, and Claude Code

Audit status: source-complete for production lock/lease paths at 7b08beef
Primary context: dd-chain-capture
Audited repository: repos/dadaia-workspace
Priority: P0

## Verdict

The current release lease cannot be considered operationally safe for dd-chain-capture.

The most severe observed failure is a **false live-foreign classification**: rebind rewrites a
lease away from the harness-native identity and the next tool call is blocked by its own live
process. This affects Codex, Claude Code, and PI Layer 1.

PI Layer 1 also has the inverse CRITICAL defect: all sessions fall back to the shared identity
`anon-session`, so two independent PI processes can both mutate the same context while the
lease believes they are one holder.

The workspace therefore currently has both unacceptable failure modes:

- **false exclusion:** the legitimate holder cannot work;
- **false inclusion:** concurrent PI holders are not separated.

The correct goal is not “delete every synchronization primitive.” Workspace/context registry
file mutations and git clone/remove operations need short bounded critical sections. Release
mutation also needs a concurrency invariant if multiple agents can write the same repo. The
non-negotiable requirement is:

> No stale, synthetic, ambiguous, or same-process identity may block useful work. Only a proven
> different live mutator may yield, and that yield must clear automatically and deterministically.

## Lock inventory

| Mechanism | Location | Purpose | Blocking bound | Audit verdict |
|---|---|---|---|---|
| Workspace file lock | `.dadaia/states/.ws_lock` via `workspace_lock()` | Serialize `spec_contexts.json` load/mutate/save | 5 seconds | Acceptable bounded critical section; not the incident. |
| Per-context file lock | `.dadaia/states/ctx_locks/<slug>.lock` via `context_lock()` | Serialize clone/push/remove for one repo | 5 seconds | Acceptable bounded critical section if lock ordering remains enforced. |
| Release mutation lease | `<ctx>.lock.json` + O_EXCL sentinel | Exactly one mutating session | Potentially harness lifetime | P0: identity model is unsound across harnesses. |
| Lease CAS sentinel | `<ctx>.lock.sentinel` | Serialize record/index transitions | About 0.7 seconds + orphan GC | Bounded, but error classification contradicts fail-open documentation. |
| Git pre-commit lease check | installed git hook | Prevent commit by live foreign session | One command | Mostly fail-open, but inherits bad lease identity. |
| Telemetry/file locks | infrastructure adapters | Protect local telemetry/state writes | implementation-specific | Outside reported incident; no unbounded lifecycle dependency found. |

## Findings

### P0-1 CRITICAL: rebind rotates a native lease to an unreachable synthetic ID

Detailed in `20260710T0116Z-layer1-codex-session-lock-mismatch-blocks-file-tools-after-bind.md`.

Root chain:

```text
native hook ID owns lease
  -> context bind mints sess_*
  -> adoption rewrites record/pointer to sess_*
  -> next hook reports native ID
  -> pointer mismatch + record mismatch + PID-proof mismatch
  -> live holder called foreign
  -> permanent self-block while harness stays alive
```

Affected: Codex Layer 1, Claude Code Layer 1, PI Layer 1 after an existing lease.

### P0-2 CRITICAL: PI Layer 1 collapses all sessions to `anon-session`

The PI extension sends no `session_id`. Python defaults to `anon-session` for a mutating write.

Consequence:

```text
PI process A acquires anon-session, pid=111
PI process B writes as anon-session, pid=222
same-session renewal branch accepts B
lease pid becomes 222
A and B can both write
```

This was reproduced directly against `lease.acquire()` with live PIDs. It violates the central
exactly-one-mutator guarantee.

Required invariant: an anonymous/fallback identity may never acquire or renew a mutating lease.

### P0-3 CRITICAL: session identity has no single owner at runtime

At least six identifiers/records participate:

1. CLI-minted `sess_*`;
2. hook stdin `session_id`;
3. harness environment ID;
4. incumbent pointer;
5. lease record holder;
6. by-session index.

The system attempts to reconcile them after the fact through pointer matching, PID equality,
session-record PID proof, and ancestry membership. That complexity is the root architectural
condition behind repeated regressions (`bind-mode-session-record-keyed-by-cli-sid`,
`codex-thread-id-bind-resolution-breaks-cli`, `rebind-does-not-adopt-same-process-lease`, and
the current recurrence).

Mitigation requires one canonical holder ID established before acquisition. Recovery heuristics
must not be the normal path.

### P1-1 HIGH: a foreign READ bind can impose READ mode on another session

Mode resolution falls back from the current hook's absent/self record to the context-global
incumbent pointer. With no live divergent lease, a READ bind by session A can cause session B's
mutating write to resolve READ and block before acquisition.

This is a false cross-session mode coupling. The constitution states that context memory follows
the session's own bind, but mode fallback deliberately treats bind as context-global. That choice
is operationally surprising in a multi-session workspace.

Mitigation: mode must be keyed to canonical session identity. A context-wide default may exist,
but it must not override an unbound foreign session without an explicit policy decision and clear
diagnostic attribution.

### P1-2 HIGH: PID liveness lacks process-start identity and is vulnerable to PID reuse

Lease liveness stores only integer PID. A stale record whose PID has been recycled by an unrelated
long-lived process can remain non-stale indefinitely for the same active release. The system has no
boot ID/process start-time token to prove that the live PID is the original holder.

Mitigation: store and probe a process identity tuple, for example `(pid, start_time, boot_id)` on
Linux and the platform-equivalent creation token elsewhere. PID alone is not identity.

### P1-3 HIGH: normal release is not reliably discoverable or automatic

`context release` documentation describes a default-flow latest bind, but implementation requires
`--session` or `DADAIA_SESSION_ID`; without either it exits “No active session.” Bare bind does not
export `DADAIA_SESSION_ID`.

This encourages leases to persist until process death/TTL logic. A live but idle harness remains a
PID-vetoed holder and blocks genuinely foreign work.

Mitigation:

- resolve release from the current harness-native canonical ID;
- add Stop/session-end release hooks where supported;
- make release idempotent and exact;
- expose holder/owner/release action in one diagnostic command.

### P1-4 HIGH: PI Layer 1 has no PostToolUse heartbeat/session refresh path

The PI extension implements only `tool_call -> pre_gate`. It does not invoke
`sdd_post_gate`. Writes renew during acquire, and PID veto protects a live process, but session
records, audit heartbeat, and by-session observability do not have parity with Codex/Claude.

Combined with `anon-session`, this makes PI lock telemetry misleading and deterministic release
impossible.

Mitigation: PI extension must send one stable ID and long-lived PID to both pre- and post-tool
hooks, plus a session-stop release event if the PI extension API supports it.

### P1-5 HIGH: doctor pointer GC applies TTL-only liveness

Workspace doctor `fix()` checks pointer orphaning with `is_stale(lock_data)` without the PID probe.
It can delete an incumbent pointer after heartbeat TTL even while the holder PID is alive. A stable
same-ID holder can recover via record equality, but a rotated/native mismatch loses an important
self-recognition rung and can self-block.

Mitigation: pointer GC and lease GC must consume one canonical liveness function with the same
process-identity probe and active-release semantics. No TTL-only shadow verdict.

### P2-1 MEDIUM: CAS contention is documented fail-open but implemented as block

`lease.acquire()` raises `LockHeldError` after sentinel retries. Its docstring says the gate treats
sentinel contention as fail-open, but `gate_policy.evaluate()` blocks every `LockHeldError`, without
distinguishing live-foreign ownership from transient CAS contention.

This is bounded and retryable, not a permanent deadlock, but it violates the zero-false-block
contract and can surface as another “lock” during simultaneous tools.

Mitigation: use a distinct `LeaseContentionError` and either retry at the hook boundary or fail open
with an advisory. Only `LiveForeignLeaseError` should block.

### P2-2 MEDIUM: release-aware reclaim can override a live PID based on ACTIVE.md

When a stale lease's recorded release differs from current ACTIVE, `is_stale()` bypasses the PID
veto. This prevents archived-release deadlocks, but it assumes ACTIVE changes prove the old process
is done. If ACTIVE is advanced while the old holder is still mutating, a new holder can take over a
live process.

Mitigation: closure should explicitly release the old lease before changing ACTIVE, and takeover
should require terminal release evidence or a holder generation token, not only a mutable pointer
file.

### P3-1 LOW: short file locks are bounded and ordered

The POSIX/Windows workspace and context file locks use non-blocking polling with a five-second
timeout. Doctor documents a single L1->L2 nesting direction and other flows release context lock
before requesting workspace lock. No unbounded AB-BA path was identified in the audited code.

These primitives should remain narrow and never be reused as release-lifetime locks.

## Required redesign

### Canonical session identity

Define one `SessionIdentity` issued by the harness boundary:

```text
session_id: unique stable ID per interactive harness session
runtime: codex | claude | pi
process: pid + process-start token
context: bound context
mode: read | implementation | review
release: active release
generation: monotonic bind/acquire generation
```

All session record, incumbent view, lease record, by-session index, hook payload, heartbeat, commit
check, and release operations must use this identity. Bind may update context/mode/release, but must
not silently rotate `session_id`.

### Non-blocking recovery contract

1. Same identity: renew immediately.
2. Same process identity with a rotated legacy ID: atomically normalize once, with explicit audit.
3. Different identity, dead process: reclaim immediately after TTL/terminal proof.
4. Different identity, live process: yield with owner and automatic retry guidance.
5. Unknown/corrupt state: fail open for tool execution but block commit with an actionable repair
   only if ownership can be proven; never create a permanent opaque hold.
6. Anonymous identity: cannot acquire mutating lease.

### Prefer scoped work over a context-lifetime lease

The current coordinator lease spans release definition through implementation and closure. That
maximizes blast radius of any identity bug. Evaluate narrowing ownership to explicit workflow/task
transactions with durable task claims and optimistic commit validation. At minimum, the lease
should have deterministic phase boundaries and automatic release after each mutating workflow,
not remain tied to an idle TUI process.

## Mandatory test matrix

### Harness parity

Run every scenario on interactive Codex, Claude Code, and PI:

1. first bind -> first write;
2. write -> rebind same mode -> next write;
3. write -> rebind different mutating mode -> next write;
4. process restart with same logical session;
5. session stop/release;
6. dead holder takeover;
7. two live sessions, same context;
8. two live sessions, different contexts;
9. READ session plus foreign IMPLEMENTATION session;
10. heartbeat gap longer than TTL with holder still alive.

### Identity assertions

After every transition assert set equality across:

```text
lease.session_id
incumbent pointer
by-session index key
session record key
hook payload session_id
heartbeat session_id
release caller session_id
```

Also assert the stored process token matches the long-lived harness, never a shell/hook/CLI child.

### Negative safety assertions

- Two PI sessions never share an ID.
- No lease record contains `anon-session`.
- A live foreign holder is never stolen.
- A dead/stale holder never requires manual steal/rebind/relaunch.
- A READ session never acquires or renews a mutating lease.
- Foreign READ bind does not silently change another session's mode.
- Doctor/check/fix and gate use the same liveness verdict.
- PID reuse does not preserve an old lease.
- CAS contention does not become a live-foreign block.

### Real executed-path tests

Direct Python unit tests are insufficient because the current bug sits at the boundary between CLI
PID, harness payload ID, and hook parent PID. CI/release evidence must include real interactive
executed-path probes for all three Layer-1 harnesses.

## Remediation priority

1. P0: remove synthetic/native split and prohibit PI anonymous acquisition.
2. P0: add cross-harness rebind and two-process tests before any further lock feature work.
3. P1: exact automatic release and PI heartbeat parity.
4. P1: process-start identity and unified doctor/gate liveness.
5. P2: split CAS contention from live-foreign conflict.
6. P2: narrow lease lifetime or replace it with transactional task ownership.

## Exit criteria for “locks mitigated”

- No confirmed self-block on any supported Layer-1 harness.
- No anonymous or shared holder identity.
- No manual lock steal in normal recovery documentation or acceptance tests.
- All parity matrix scenarios pass on real harnesses.
- Only a proven different live mutator can produce a blocking verdict.
- Every block names the canonical holder, runtime, process generation, context, release, and the
  deterministic condition that will clear it.
- The lock kernel has one identity model and one liveness verdict, not per-surface heuristics.
