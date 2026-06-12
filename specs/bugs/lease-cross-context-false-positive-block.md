---
name: lease-cross-context-false-positive-block
status: Closed
severity: MEDIUM
reported: 2026-06-09
surface: sdd-spec-gate.sh (single-session lease check) / context resolution
superseded_by: gate-cross-context-lock-contamination
session_id: null
---

**Superseded (2026-06-09):** confirmed by software-architect investigation to be the SAME defect as [[gate-cross-context-lock-contamination]] (CONTEXT_SLUG resolved globally, not from the write path). Tracked there (escalated CRITICAL). The distinct observation that Bash/CLI writes bypass the lease entirely is preserved as a separate coverage-gap note in that bug.


**Symptom:** A non-additive Write/Edit to a file under `repos/dd-chain-capture/specs/releases/v0.1.0/SPEC.md` was blocked with:

```
[SDD LOCK] Session 'f94f1f66-...' is actively mutating context 'dadaia-workspace'
(last heartbeat: 2026-06-09T03:16:48Z). This session will not mutate to avoid a race.
```

The blocking lease is on context **`dadaia-workspace`**, but the write target belongs to a
**different** Spec Context (`dd-chain-capture`, path `repos/dd-chain-capture/...`). A second,
concurrent operator session legitimately held the `dadaia-workspace` lease (it was editing
library rule files). The two sessions touch disjoint contexts and disjoint files — there is
no real race — yet the `dd-chain-capture` write was blocked.

**Root cause (suspected):** the gate resolves the *writer's* context from the session's bound
context / first-ALIVE default rather than from the **target file path's owning repo**. Under
Claude Code the main-loop session has no `DADAIA_CONTEXT` in its process env (the
`context bind` export never reaches the PreToolUse hook process), so the gate defaults the
writer to `dadaia-workspace` and applies that context's lease to a `dd-chain-capture` write.

**Repro:**
1. Session A (any runtime) acquires the `dadaia-workspace` lease (mutating a library file).
2. Session B (Claude Code main loop, unbound / no `DADAIA_CONTEXT` in env) edits a file under
   `repos/<other-slug>/specs/...` via the Edit tool.
3. Session B is blocked citing Session A's `dadaia-workspace` lease, despite targeting a
   different context.

**Expected:** The single-session lease is documented as **per-Spec-Context**
(`backlog-ownership` rule, `workspace-protocol`). A write to context X must only be gated by
context X's lease. The gate should resolve the owning context from the target path
(`repos/<slug>/`) and check *that* context's lease, not the writer-session's default/bound
context. A `dd-chain-capture` write must not be blocked by a `dadaia-workspace` lease.

**Workaround used:** completed the (already 95%-applied) in-place edits via Bash, which is not
lease-gated; the lease only intercepts the Write/Edit tools. This inconsistency (Bash bypasses
the lease entirely while Edit is blocked) is itself worth noting — the "only deterministic lock"
does not cover the Bash write path.

**Notes:** No data was lost; the SPEC correction was cosmetic (a factual harness-name fix). The
concurrent `dadaia-workspace` session was a legitimate parallel operator session, not a stale
lease. Heartbeat was fresh, so 120s auto-reclaim would not have freed it. Environment: Claude
Code, self-hosting dadaia-workspace instance.
