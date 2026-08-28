---
name: dd-ai-eng-knowhow
description: >
  Two audiences share this skill. ANY agent: a working mental model of the AI-entity
  primitives this workspace runs on (persona, subagent, skill, rule, hook, AGENTS.md,
  MCP), the Claude-Code/Codex/Kimi-Code deltas, dadaia's projection mechanics, and when
  to defer to ai-engineer. ai-engineer alone: the authoring/auditing depth — per-harness
  decision protocols, token economy, instruction hierarchy, persona-consistency
  invariants, model-tier selection, and the writing-for-agents authoring contract — held
  in this skill's disclosed siblings.
tldr: "Every agent: harness primitive literacy. ai-engineer only: 4 disclosed siblings for authoring/auditing depth."
applyTo: "**"
---

# dd-ai-eng-knowhow — Harness Literacy for Everyone, Depth for `ai-engineer`

## 1. When

- Every agent: reasoning about your own harness configuration (persona, skill, rule, hook, AGENTS.md, MCP).
- `ai-engineer` only: authoring or auditing any AI-entity file.
- Not `ai-engineer` and need to change (not read) a persona/skill/rule/hook: dispatch `ai-engineer` instead.

## 2. Steps

1. Identify your harness: Claude Code, Codex, or Kimi Code.
2. Name the primitive you are touching using the catalog table (§4) before reasoning about it.
3. Never assume a Claude Code hook/rule config transplants verbatim to Codex/Kimi — check the delta table (§4).
4. Trace any harness file to its `dadaia_workspace/public/<type>/<file>` source before editing.
5. Never hand-edit `.claude/`, `.agents/`, `.codex/`, `.kimi-code/` projections directly.
6. Re-project via `dadaia public stage && dadaia public install --target all && dadaia public doctor`.
7. Remember gate order: root-whitelist -> venv-guard -> SDD gate, first-block-wins.
8. Remember git chokepoints (pre-commit WARN-only, pre-push verdict gate) run independently of harness hooks.
9. `ai-engineer` only: open the relevant disclosed sibling (§4) instead of re-deriving harness behavior.
10. `ai-engineer` only: apply the authoring guardrails (§4) on every edit.

## 3. Done when

- You can name the primitive and its harness-specific serialization before acting.
- Any AI-entity edit lands in `public/` source, then is re-projected and doctor-verified.
- A non-`ai-engineer` agent needing to change an AI-entity file has dispatched `ai-engineer` instead.

## 4. References

- Primitive catalog: agent persona (`public/agents/*.md`), subagent dispatch, skill, rule, hook, AGENTS.md, MCP.
- Context vs enforcement: persona/skill/rule/AGENTS.md inform; hooks, Codex `.rules`, SDD gate enforce.
- Claude Code vs Codex vs Kimi Code deltas: persona serialization, constitution shape, Rules naming collision.
- Deltas (continued): hook firing, skill discovery, subagent spawn, config-layer trust — compiled in `CLAUDE-CODE.md`/`CODEX.md`.
- Defer to `ai-engineer` for: reasoning about *why* a primitive behaves a way, diagnosing hook/skill/rule drift.
- Defer to `ai-engineer` for (continued): designing/authoring/modifying any AI-entity file, per-harness decision depth, context engineering.
- Disclosed siblings (`ai-engineer` only, `DADAIA.md` §2 scope): `CLAUDE-CODE.md`, `CODEX.md`, `CONTEXT-ENGINEERING.md`, `AUTHORING.md`.
- Authoring guardrails: all authoring targets are `dadaia_workspace/public/...` source.
- Authoring guardrails (continued): no consumer-specific names/hostnames/IPs/secrets; tables over prose for enumerable rules.
