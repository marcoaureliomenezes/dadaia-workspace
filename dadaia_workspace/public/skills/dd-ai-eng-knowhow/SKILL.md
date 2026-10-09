---
name: dd-ai-eng-knowhow
description: >
  Use before reading or changing any persona, skill, rule, hook, AGENTS.md or MCP config: harness literacy, Claude Code/Codex deltas, the AUTHORING contract.
compatibility: Standalone Agent Skill. Inside a dadaia-workspace (pip install dadaia-workspace) it also drives the SDD lifecycle — specs, backlog, bugs, releases.
---

# dd-ai-eng-knowhow — Harness Literacy for Everyone, Depth on Demand

## 1. When

- Every agent: reasoning about your own harness configuration (persona, skill, rule,
  hook, AGENTS.md, MCP).
- Authoring or auditing any AI-entity file (the reviewer's AI-surface lens).
- Any other agent needing to CHANGE (not read) a persona/skill/rule/hook: follow
  `AUTHORING.md`, or return the change to the main thread.

## 2. The working model

- Name the primitive before reasoning about it: agent persona
  (`public/agents/*.md`), subagent dispatch, skill, rule, hook, AGENTS.md, MCP.
- Context vs enforcement: persona/skill/rule/AGENTS.md inform; hooks, Codex
  `.rules`, and the SDD gate enforce.
- A Claude Code hook/rule config never transplants verbatim to Codex — the
  deltas (persona serialization, constitution shape, hook firing, skill discovery,
  subagent spawn, config-layer trust) are compiled in
  [`CLAUDE-CODE.md`](CLAUDE-CODE.md) and [`CODEX.md`](CODEX.md).

## 3. Editing an AI-entity file

1. Trace the harness file to its source: the matching `assets[].path` in `.dadaia/agentic/manifest.json` is `dadaia_workspace/public/<path>` —
   every authoring target is the source, never a `.claude/`, `.agents/`, `.codex/`
   projection.
2. Reproject per `.dadaia/AGENTS.md` §4.
3. Author against [`AUTHORING.md`](AUTHORING.md) — the 15-rule
   writing-for-agents contract — and opens the relevant disclosed sibling instead of
   re-deriving harness behavior; then `.dadaia/.venv/bin/dadaia public doctor` must print `[ok] public-privacy` (its scan covers hostnames, IPs, home paths, emails and secrets).

## 4. Done when

- Your output names the primitive and its harness serialization.
- Any AI-entity edit landed in `public/` source and was re-projected and
  doctor-verified.

## 5. Disclosed siblings (authoring depth)

- [`AUTHORING.md`](AUTHORING.md) — the writing-for-agents contract and 15-rule checklist.
- [`CONTEXT-ENGINEERING.md`](CONTEXT-ENGINEERING.md) — token economy, instruction
  hierarchy, model-tier selection.
- [`CLAUDE-CODE.md`](CLAUDE-CODE.md) · [`CODEX.md`](CODEX.md) — per-harness decision
  protocols.
