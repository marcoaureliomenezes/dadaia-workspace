---
name: sdd-gate-lease-blocks-pm-dispatched-subagent-writes
status: Closed
severity: HIGH
reported: 2026-06-11
surface: dadaia_workspace.hooks.sdd_gate (lease identity + heartbeat renewal)
---

**Symptom:** A `product-engineer` sub-agent dispatched by `project-manager` via the
Agent tool is blocked by `[SDD LOCK]` when writing the release's own spec artifacts
(`specs/releases/v0.1.12/SPEC.md`, a MUTATING path). The lease holder is reported as
session `019eb52a-…` with a fresh heartbeat. The heartbeat renewal timestamps advance
in lockstep with the *sub-agent's own* tool calls (observed three consecutive
PreToolUse rejections at heartbeats 06:02:18Z → 06:03:54Z → 06:04:44Z, each renewal
coinciding with the sub-agent's intervening Read/Grep batches), suggesting the
match-all PostToolUse heartbeat renews the holder's lease using the parent
harness-session identity while the PreToolUse gate attributes the sub-agent's writes
to a different session identity. Net effect: the more the sub-agent works, the
fresher the foreign lease — a potential live-lock where the dispatched writer can
never acquire.

**Repro:** In a workspace with an active coordinator session holding the
`dadaia-workspace` context lease, dispatch a sub-agent (Agent tool) instructed to
Edit a MUTATING path under `specs/releases/<id>/`. The sub-agent's Edit is rejected
with `[SDD LOCK]`; interleave Read calls and retry — the reported "last heartbeat"
advances with each retry batch while the holder session is nominally blocked waiting
on the Agent tool result.

**Expected:** Per constitution §9 and the product-engineer persona contract
("`project-manager`'s release lease covers your writes throughout"), a sub-agent
dispatched by the lease-holding session must be able to perform MUTATING writes —
either by sharing the holder's session identity in PreToolUse classification, or by
an explicit dispatch-coverage mechanism. At minimum, PostToolUse heartbeat renewal
and PreToolUse identity attribution must use the SAME session identity, so a
blocked-on-dispatch holder's lease can go stale and be reclaimed (~120s) instead of
being indefinitely refreshed by the very sub-agent it blocks.

**Notes:** Observed on Linux, Claude Code harness, self-hosting workspace, context
`dadaia-workspace`, release v0.1.12 DEFINITION phase (PE folding architect review
findings into SPEC/PLAN/TASKS). Related prior art: the v0.1.7
`gate-cross-context-lock-contamination` finding (lease renewal attributed to the
wrong session/context) and the v0.1.7 rc-3 "lock with no key" persona-gate removal.
Identity fields in the lease record (session id vs harness pid) should be audited
for the sub-agent case on both harnesses.

**Confirmation (live-lock):** Six consecutive blocked MUTATING attempts; reported
"last heartbeat" each time was within seconds of the attempt itself: 06:02:18,
06:03:54, 06:04:44, 06:06:19, 06:07:20, 06:07:30 (the last two are 10s apart,
exactly matching two back-to-back blocked Edit attempts with NO successful tool call
in between). The holder's heartbeat is therefore renewed BY the blocked sub-agent's
own attempt path (gate evaluation or denied-call PostToolUse), while the deny
decision attributes the sub-agent to a different session. The lease can never go
stale while the blocked writer retries — a deterministic live-lock. Severity should
arguably be CRITICAL: any PM-dispatched sub-agent tasked with MUTATING writes in the
dispatching session's context is hard-deadlocked, and the gate's own remediation
advice ("auto-reclaims after ~120s") is unsatisfiable.


---

**FORENSIC RESOLUTION (2026-06-11, coordinator):** Misdiagnosis — the gate behaved
per contract. The lease holder `019eb52a-…` was NOT a phantom renewed by the blocked
sub-agent's own attempts: it is a **live foreign Codex session** (recorded pid probed
alive, `codex` binary, ~40 min uptime, bound `BOUND_IMPLEMENTATION`), i.e. a second
operator session concurrently mutating the same context (it created release v0.1.13
and re-pointed ACTIVE.md while this session was defining v0.1.12). The heartbeat
renewals that coincided with the blocked attempts were the Codex session's own tool
activity. Single-session-per-context + no-steal-from-live-holder is exactly the
designed behavior (the gate working correctly is not a bug — bug-registration
guardrail). The PE-side observation that earlier same-harness sub-agent writes
succeeded confirms the lease covers sub-agents of the holding session. Closed as
invalid; the real issue (two concurrent implementation sessions / two ACTIVE
releases on one context) is an operator-coordination decision, not a gate defect.
