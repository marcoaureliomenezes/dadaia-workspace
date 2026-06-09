---
title: codex-dispatched-agent-persona-not-propagated-to-sdd-gate
severity: Critical / Blocker
opened: 2026-06-09
session_id: null
status: Open
---

# Bug: codex-dispatched-agent-persona-not-propagated-to-sdd-gate

## Escalation (2026-06-09)

**Severity escalated to maximum: Critical / Blocker.**

This is not a minor Codex inconvenience and not an operator setup issue. It is an
architectural blocker in the dadaia-workspace development lifecycle:

- The workflow says backlog is PM-owned.
- The lead Codex session can spawn a `project-manager`.
- The spawned `project-manager` still cannot satisfy the SDD gate.
- The gate suggests manual environment/pointer workarounds.
- The operator cannot proceed fluidly from backlog -> release -> implementation -> review.

Any design that requires the operator or lead agent to manually bind environment variables per
agent is invalid for dadaia-workspace. The root cause must be traced and replaced with a
proper dispatcher/session/persona authority model.

This bug blocks the backlog item that should track the broader harness architecture work:

- intended backlog path:
  `repos/dadaia-workspace/specs/backlog/harness-agentic-entities-and-determinism-parity.md`
- intended candidates entry:
  `repos/dadaia-workspace/specs/backlog/candidates.md`

That backlog could not be registered because the very mechanism that should route the write
through `project-manager` cannot propagate PM identity into the gate.

## Claude Code handoff note (2026-06-09)

This bug is ready for Claude Code or another correctly-authorized harness to pick up.

What failed in this Codex session:

1. The operator requested a backlog entry for cross-harness agentic entity architecture and
   deterministic enforcement.
2. The lead Codex agent created the required analysis reports:
   - `.dadaia/reports/dadaia-workspace/software-architect/2026-06-09T012255Z-scaffold-agentic-entities-supported-harnesses.html`
   - `.dadaia/reports/dadaia-workspace/ai-engineer/2026-06-09T012255Z-dadaia-workspace-determinism-enforcements.html`
3. The lead Codex agent correctly identified `specs/backlog/**` as `project-manager`-owned.
4. The lead Codex agent spawned a `project-manager` subagent.
5. The spawned `project-manager` could not write backlog because `sdd-spec-gate.sh` still saw
   `writer persona unresolved`.
6. The lead Codex agent retried a minimal backlog placeholder without forging persona; the gate
   blocked it again with the same error.
7. Therefore the backlog item was **not created** and the production fix was **not implemented**.

The intended backlog that remains blocked:

- `repos/dadaia-workspace/specs/backlog/harness-agentic-entities-and-determinism-parity.md`
- an entry at the top of `repos/dadaia-workspace/specs/backlog/candidates.md`

The `project-manager` subagent returned a complete patch for those backlog files in the Codex
conversation, but applying it from the current Codex lead session would require either:

- forging/setting `DADAIA_AGENT_PERSONA=project-manager`, or
- writing a `.dadaia/sessions/runtime/<session>.persona` pointer manually.

Both are invalid as product workflow solutions. They may be useful diagnostic facts, but must
not be accepted as the normal architecture.

Claude Code should investigate the cause root-to-leaf:

1. How Codex subagents/custom agents are spawned in this harness.
2. Whether the spawned agent identity is available to hooks at all.
3. Why `CODEX_AGENT_PERSONA` or an equivalent trusted marker is not set for spawned dadaia
   agents.
4. Whether `.dadaia/sessions/runtime/<session>.persona` is the right authority bridge or
   whether a safer dispatcher-owned session protocol is needed.
5. How to preserve the security property that ordinary Write/Edit tools cannot forge persona
   authority while still allowing legitimate dispatched owner agents to pass the gate.
6. How to test this with one positive and one negative case:
   - dispatched `project-manager` writes backlog successfully;
   - non-PM write to backlog remains blocked.

This is not fixed by documenting a workaround. This is only fixed when the normal PM-owned
backlog workflow works fluidly from Codex without operator env manipulation.

## Description

In a Codex session, the operator asked to define a backlog item from two reports. The lead
agent correctly identified that `specs/backlog/**` is owned by `project-manager` and spawned a
`project-manager` subagent. The workflow still failed: both the lead agent and the spawned
`project-manager` were blocked by `sdd-spec-gate.sh` with `writer persona unresolved`.

This is a critical workflow/enforcement bug. The correct user experience is not to ask the
operator to export `DADAIA_AGENT_PERSONA=project-manager` or manually create a runtime persona
pointer. If the harness can spawn the owning agent, the dadaia runtime must propagate a
machine-readable persona/authority identity that the gate can verify. Manual environment
binding per agent is not a viable architecture.

## Impact

- PM-owned backlog intake cannot flow naturally from a Codex conversation.
- A correct dispatch to `project-manager` does not satisfy the SDD gate.
- The operator is forced into low-level runtime workarounds (`DADAIA_AGENT_PERSONA` or
  `.dadaia/sessions/runtime/<session>.persona`), which contradicts the dadaia-workspace
  workflow model.
- The product claim that owner-only artifacts can be routed through the owning agent is only
  partially true in Codex: dispatch exists, but ownership identity is not propagated to the
  deterministic gate.
- This blocks backlog -> release -> implementation -> review flow and undermines
  multi-agent SDD orchestration.

## Evidence

Observed on 2026-06-09 in a Codex session:

1. The operator asked to consume reports and create an explicit backlog item.
2. The lead agent spawned a `project-manager` subagent for the PM-owned backlog write.
3. The lead agent attempted a direct backlog write and was blocked:

```text
[BACKLOG OWNERSHIP ERROR] writer persona unresolved — only project-manager may write
specs/backlog/. Set DADAIA_AGENT_PERSONA=project-manager (the owning role), or record it in
the session pointer .dadaia/sessions/runtime/<session>.persona, and retry
(rule: backlog-ownership).
```

4. The spawned `project-manager` was redirected to write the backlog directly.
5. The spawned `project-manager` also reported the same gate failure:

```text
[BACKLOG OWNERSHIP ERROR] writer persona unresolved — only project-manager may write
specs/backlog/.
```

6. The subagent returned a patch instead of completing the backlog write.

7. A later controlled retry attempted to create even a minimal backlog placeholder at
   `repos/dadaia-workspace/specs/backlog/harness-agentic-entities-and-determinism-parity.md`
   without forging persona identity. It was blocked again with the same error:

```text
[BACKLOG OWNERSHIP ERROR] writer persona unresolved — only project-manager may write
specs/backlog/. Set DADAIA_AGENT_PERSONA=project-manager (the owning role), or record it in
the session pointer .dadaia/sessions/runtime/<session>.persona, and retry
(rule: backlog-ownership).
```

Related reports that triggered the backlog request:

- `.dadaia/reports/dadaia-workspace/software-architect/2026-06-09T012255Z-scaffold-agentic-entities-supported-harnesses.html`
- `.dadaia/reports/dadaia-workspace/ai-engineer/2026-06-09T012255Z-dadaia-workspace-determinism-enforcements.html`

## Steps to reproduce

1. Start a Codex session in the dadaia workspace with an active Spec Context Project.
2. Ask the lead agent to create a backlog item from reports.
3. Ensure the lead agent dispatches/spawns `project-manager`.
4. Ask the spawned `project-manager` to write `repos/dadaia-workspace/specs/backlog/<slug>.md`
   and update `repos/dadaia-workspace/specs/backlog/candidates.md`.
5. Observe that `sdd-spec-gate.sh` blocks the write because the runtime persona is unresolved.

## Expected behavior

- Dispatching the `project-manager` agent should create a verifiable runtime identity that the
  SDD gate recognizes as `project-manager`.
- The `project-manager` should be able to write `specs/backlog/**` without operator-provided
  environment variables.
- The lead agent should not need to ask the operator to bind a persona manually.
- The gate should continue to block non-PM backlog writes, but allow PM writes from a genuine
  PM-dispatched session.

## Actual behavior

- The gate blocks the spawned `project-manager` because no recognized persona reaches the gate.
- The system suggests manual env/pointer workarounds.
- The backlog flow stops and returns a patch instead of producing the backlog artifact.

## Root cause hypothesis

The gate's backlog ownership rule trusts these identity channels:

- `DADAIA_AGENT_PERSONA`
- `CLAUDE_AGENT_PERSONA`
- `CODEX_AGENT_PERSONA`
- `OPENCODE_AGENT_PERSONA`
- `.dadaia/sessions/runtime/<session>.persona`
- the `persona` field in `.dadaia/sessions/<session>.json`

Codex subagent dispatch in the current harness does not automatically set any of those
channels for a spawned dadaia agent. The static `project-manager` persona exists as an
instruction/config surface, but it is not bridged into the deterministic gate's runtime
identity model.

There is also a broader architectural gap: the workflow layer can request/perform dispatch,
but the SDD gate only sees environment/session identity. These two systems must be connected
by a trusted dispatcher/session protocol.

## Acceptance criteria for fix

- This bug is not closed by documentation, advice, or manual environment setup. It is closed
  only by a working architecture where dispatched owner agents carry trusted, gate-visible
  authority.
- A Codex-dispatched `project-manager` can write `specs/backlog/**` without manual operator
  env vars.
- A Codex-dispatched non-PM agent remains blocked from `specs/backlog/**`.
- The dispatch mechanism writes or propagates a trusted persona marker that
  `sdd-spec-gate.sh` can verify.
- The persona marker cannot be forged by ordinary agent Write/Edit operations; the existing
  `.dadaia/sessions/**` protected-path rule remains intact or is replaced by an equally safe
  mechanism.
- There is a smoke/integration test for:
  operator request -> Codex lead -> `project-manager` dispatch -> backlog write allowed.
- There is a negative test for:
  operator request -> Codex lead/non-PM -> backlog write blocked.
- Documentation and memory stop suggesting manual env binding as the normal operational path
  for multi-agent ownership. Manual env binding may remain a diagnostic escape hatch only.
- If a harness cannot provide trustworthy subagent persona propagation, the workflow must fail
  with a product-level error and a registered bug, not with an operator-facing workaround.
- The previously blocked backlog item
  `specs/backlog/harness-agentic-entities-and-determinism-parity.md` can be registered
  through the normal PM-owned workflow after the fix.

## Related

- `specs/bugs/codex-workflow-dispatch-not-deterministically-enforced.md` — previously closed
  as fixed to the maximum deterministic extent, but this incident shows the dispatch-to-gate
  identity bridge is still missing.
- `specs/backlog/codex-context-hook-and-workflow-enforcement-hotfix.md`
- `specs/backlog/full-codex-compatibility.md`
- `.dadaia/reports/dadaia-workspace/ai-engineer/2026-06-09T012255Z-dadaia-workspace-determinism-enforcements.html`
