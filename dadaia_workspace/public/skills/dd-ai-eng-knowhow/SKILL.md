---
name: dd-ai-eng-knowhow
description: >
  Harness literacy for every agent (persona, subagent, skill, rule, hook, AGENTS.md,
  MCP — and the Claude-Code/Codex/Kimi-Code deltas), plus ai-engineer's disclosed
  authoring depth. Use when reasoning about your own harness configuration, before
  touching any AI-entity file, or to decide when to defer to ai-engineer.
---

# dd-ai-eng-knowhow — Harness Literacy for Everyone, Depth for `ai-engineer`

## 1. When

- Every agent: reasoning about your own harness configuration (persona, skill, rule,
  hook, AGENTS.md, MCP).
- `ai-engineer` only: authoring or auditing any AI-entity file.
- Any other agent needing to CHANGE (not read) a persona/skill/rule/hook: dispatch
  `ai-engineer` instead.

## 2. The working model

- Name the primitive before reasoning about it: agent persona
  (`public/agents/*.md`), subagent dispatch, skill, rule, hook, AGENTS.md, MCP.
- Context vs enforcement: persona/skill/rule/AGENTS.md inform; hooks, Codex
  `.rules`, and the SDD gate enforce.
- A Claude Code hook/rule config never transplants verbatim to Codex/Kimi — the
  deltas (persona serialization, constitution shape, hook firing, skill discovery,
  subagent spawn, config-layer trust) are compiled in
  [`CLAUDE-CODE.md`](CLAUDE-CODE.md) and [`CODEX.md`](CODEX.md).
- Gate order: root-whitelist → venv-guard → SDD gate, first-block-wins; git
  chokepoints (pre-commit WARN-only, pre-push verdict gate) run independently of any
  harness hook.

## 3. Editing an AI-entity file

1. Trace the harness file to its `dadaia_workspace/public/<type>/<file>` source —
   every authoring target is the source, never a `.claude/`, `.agents/`, `.codex/`,
   `.kimi-code/` projection.
2. Re-project: `dadaia public stage` → `dadaia public install --target all` →
   `dadaia public doctor`.
3. `ai-engineer` authors against [`AUTHORING.md`](AUTHORING.md) — the 15-rule
   writing-for-agents contract — and opens the relevant disclosed sibling instead of
   re-deriving harness behavior; public assets carry no consumer names, hostnames,
   IPs or secrets.

## 4. Done when

- You can name the primitive and its harness-specific serialization before acting.
- Any AI-entity edit landed in `public/` source and was re-projected and
  doctor-verified.
- A non-`ai-engineer` agent needing an AI-entity change dispatched `ai-engineer`.

## 5. Disclosed siblings (`ai-engineer` depth)

- [`AUTHORING.md`](AUTHORING.md) — the writing-for-agents contract and 15-rule
  checklist.
- [`CONTEXT-ENGINEERING.md`](CONTEXT-ENGINEERING.md) — token economy, instruction
  hierarchy, model-tier selection.
- [`CLAUDE-CODE.md`](CLAUDE-CODE.md) · [`CODEX.md`](CODEX.md) — per-harness decision
  protocols.
