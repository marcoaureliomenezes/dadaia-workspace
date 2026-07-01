---
title: codex-workflow-dispatch-not-deterministically-enforced
severity: High
opened: 2026-06-07
session_id: null
status: Closed
resolved_in: 0.1.7 (rc-2, T-017-20)
---

# Bug: codex-workflow-dispatch-not-deterministically-enforced

## Resolution (0.1.7 rc-2, T-017-20)

Closed to the maximum **deterministic** extent the harness allows. Two of the
three acceptance layers are now enforced, not advisory; the third is an inherent
harness limitation now documented truthfully (the bug's own acceptance #6).

1. **Deterministic ownership enforcement (gate).** `sdd-spec-gate.sh` runs on
   `PreToolUse` for every harness (Codex `.codex/hooks.json`, Claude, OpenCode).
   A non-owner write to `specs/backlog/**` is **blocked, not advised** — and
   0.1.7 T-017-15/SEC-01 hardened exactly this path (persona session-pointer
   fallback + `.dadaia/sessions/**` PROTECTED against pointer forgery). Verified
   by `tests/integration/gate/test_protected_sessions.py` and
   `tests/integration/gate/test_backlog_ownership.py`.
2. **Deterministic dispatcher preflight (context injection).** `ctx-inject.sh`
   now injects a harness-neutral dispatcher-preflight block at SessionStart when
   a context is bound: resolve the active context + the OWNING role for the
   artifact class, and — when multi-agent / AI-surface work is requested —
   DISCOVER the subagent/dispatch tool (e.g. `tool_search`) **before** proceeding
   instead of acting as a generic single agent. This makes role-routing a
   deterministic instruction rather than relying on the lead model's memory of
   `specs/AGENTS.md`. Verified by `tests/integration/test_hooks.py`
   (`test_ctx_inject_emits_dispatcher_preflight`,
   `test_ctx_inject_preflight_in_valid_codex_json`).
3. **Inherent limitation, documented truthfully (acceptance #6).** No harness
   auto-spawns subagents from static `.codex`/`.claude` workflow files — workflow
   files are reference docs; explicit dispatcher/operator fan-out is required.
   Stated in `specs/memory/product/agents/agent-orchestration.md` ("Runtime
   dispatch honesty") and now echoed in the preflight injection itself.

The broad codex-compatibility program (FEAT-CODEX-COMPAT-100: custom agents,
hooks, Starlark `.rules`, D-CX-1..10 doctor, golden tests) was delivered in
0.1.6 and is verified green on `feature/0.1.7` (50 codex tests + full suite).
Backlog status-header reconciliation for `full-codex-compatibility.md` and
`codex-context-hook-and-workflow-enforcement-hotfix.md` is a `project-manager`
action (backlog is PM-owned; the SDD gate blocks non-PM backlog writes).

---

## Description

dadaia-workspace's product workflow expects role-scoped orchestration: backlog intake is
owned by `project-manager`, AI-entity surfaces are audited by `ai-engineer`, release
definition is owned by `product-engineer`, and implementation/review phases dispatch
specialists. In the observed Codex session, this behavior was not deterministically
enforced. The lead Codex agent proceeded as a generic coding assistant until the operator
challenged the workflow.

The operator had explicitly asked for deep research and agent spawning earlier, but the
Codex lead did not discover/use the subagent tool until manually searching for it later.
That means the workflow currently depends on model judgment rather than a deterministic
runtime protocol.

## Impact

- Backlog ownership can be missed unless the model remembers `specs/AGENTS.md`.
- Required specialist fan-out can be skipped even when the operator expects it.
- The same task can be handled differently by Claude Code vs Codex.
- Release-definition flow can be bypassed or delayed.
- The product promise of a multi-agent SDD workspace becomes advisory instead of enforced.

## Evidence

- `specs/AGENTS.md:48` states `backlog/**` is `project-manager` only.
- `specs/memory/product/sdd/sdd-bug-backlog-governance.md:43-47` describes PM-only
  backlog ownership and hard gate enforcement.
- `specs/memory/product/agents/agent-orchestration.md` and the public orchestration skill
  describe dispatcher/leaf boundaries.
- The Codex subagent tool existed but was not visible in the initial tool set; it required
  explicit deferred discovery through `tool_search`.
- The lead agent did not search for the multi-agent tool when the operator first asked for
  spawned agents and ai-engineer participation.
- The correction only happened after the operator asked why agents were not being spawned.

## Steps to reproduce

1. In a Codex session, ask for a dadaia-workspace audit requiring ai-engineer and
   multi-agent research.
2. Observe whether the lead agent automatically resolves role ownership and discovers
   subagent tooling.
3. Ask it to create backlog/spec artifacts.
4. Observe whether it routes through PM/product-engineer authority or treats the workflow
   as manual/advisory.

## Root cause hypothesis

Codex custom agents/subagents are real only when explicitly invoked through the harness
tool surface. dadaia-workspace currently documents orchestration expectations, but Codex
does not automatically transform those expectations into deterministic routing. The
project needs a Codex-native workflow gate or dispatcher preflight that forces:

- role resolution,
- artifact ownership checks,
- required specialist dispatch,
- and clear refusal/block messages when a generic session attempts owner-only writes.

## Acceptance criteria for fix

- A Codex session handling dadaia-workspace work has a deterministic preflight for:
  active context, requested artifact class, owning role, and required dispatch.
- If the operator requests multi-agent/deep AI-surface work, Codex discovers or exposes
  the subagent tool before continuing the main task.
- If a non-PM attempts to author `specs/backlog/**`, the workflow blocks or reroutes
  through PM authority with an explicit message.
- If a task touches hooks/agents/skills/rules/workflows, the workflow requires ai-engineer
  audit or a documented operator override.
- Tests or harness smoke checks prove the route for backlog intake:
  operator prompt -> PM intake -> ai-engineer audit for hook surface -> PE release
  definition after mandatory grill.
- Documentation clarifies that Codex does not auto-spawn subagents from static workflow
  files; explicit dispatcher/operator fan-out is required unless a future deterministic
  dispatcher is implemented.

## Related

- `specs/backlog/codex-context-hook-and-workflow-enforcement-hotfix.md`
- `specs/bugs/repeated-visible-userpromptsubmit-memory-injection.md`
- Existing historical bug: `specs/bugs/codex-agent-orchestration-mismatch.md`
