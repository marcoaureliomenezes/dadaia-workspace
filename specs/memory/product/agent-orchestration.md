---
slug: agent-orchestration
title: agent-orchestration
category: product
tldr: Generic multi-agent orchestration over public default agents and workflows, with runtime-specific dispatch for Claude Code, Codex, OpenCode, and CLI.
summary: Defines the public default agent topology, workflow inventory, dispatcher boundaries, path-scope ownership, and report/handoff expectations.
tags:
- orchestration
- agents
- workflows
- dispatch
agent_tier: self-pull
token_estimate: 370
last_updated: '2026-06-03'
release_origin: public-agentic-hygiene-codex-readiness
---

## Propósito

`dadaia-workspace` orchestrates specialist agents through SDD-aware workflows and
project-manager playbooks. The public default topology is generic and safe for
all consumers; project-specific, game-specific, data-vendor-specific, or private
agents belong in optional packs or local overlays.

## Fluxo de uso

The public default has 15 agents in 3 tiers:

- Tier 1 dispatchers: `project-manager`, `project-auditor`.
- Tier 2 curator: `product-engineer`.
- Tier 3 leaf specialists: `ai-engineer`, `backend-engineer`, `code-reviewer`,
  `design-specialist`, `devops-engineer`, `frontend-engineer`, `qa-engineer`,
  `researcher`, `security-reviewer`, `software-architect`,
  `software-engineer-node`, `software-engineer-python`.

Dispatchers classify work, coordinate specialists, and synthesize reports. The
curator owns SPEC/PLAN/TASKS/CLOSURE and memory updates. Leaf specialists do not
chain further dispatch unless a runtime-specific orchestration layer explicitly
assigns that responsibility.

Seven workflows ship by default:

- `spec-refinement`
- `cross-cutting-feature`
- `onboarding-new-repo`
- `hotfix-release`
- `audit-cycle`
- `code-review-fan-out`
- `design-first-implementation`

Domain workflows such as game development, dashboard publication, or
vendor-specific data pipelines are not part of the default public install.

Claude Code uses Claude-native agent/tool semantics. Codex uses Codex-native
configuration and tool discovery; Codex personas must reference `tool_search`
and deferred multi-agent tools when that capability is available, not a fake
literal `subagent` tool. OpenCode uses its own agent and plugin projection.

The dispatcher layer is best-effort across runtimes: it must report unsupported
runtime capabilities honestly instead of simulating success.

## Estado runtime tocado

`ai-engineer` owns public AI entities under
`dadaia_workspace/public/{agents,skills,rules,workflows,commands,hooks}/**`.
Python/Node implementation agents own implementation code and tests, not public
agentic assets. `product-engineer` owns specs and memory according to SDD phase.

The SDD gate validates write allowlists, task ownership, active context, and
memory phase rules. Reports are emitted under `.dadaia/reports/<context>/<agent>/`
with machine-readable handoff sidecars where required.
