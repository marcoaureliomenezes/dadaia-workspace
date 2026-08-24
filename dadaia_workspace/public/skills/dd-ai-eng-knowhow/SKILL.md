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
applyTo: "**"
---

# dd-ai-eng-knowhow — Harness Literacy for Everyone, Depth for `ai-engineer`

## The boundary, stated once (A11.3)

Everything from "Part 1 — Literacy" is for **every agent**: a mental model of your own
configuration. Everything under "Part 2 — Depth" is **authoring/auditing** territory,
reached only by `ai-engineer`. If you are not `ai-engineer` and you need to *change* a
persona/skill/rule/hook rather than *read* your own, stop — dispatch `ai-engineer`.

---

# Part 1 — Literacy (every agent)

You run inside an *agentic harness* (Claude Code, Codex, or Kimi Code) — the tooling,
context management, and execution loop that turns a model into a working agent. The
harness supplies file access, shell, permission gating, memory loading, and the
gather-act-verify loop. There is no separate workflow-engine layer: the ordered SDD flow
(`DADAIA.md` §1) is agent-dispatched, never run by an engine.

## Primitive catalog

| Primitive | One-line definition |
|---|---|
| **Agent persona** | Durable identity, scope, write-allowlist of one agent — a prompt loaded as your operating contract. `public/agents/*.md`. |
| **Subagent (dispatch)** | A separate agent invoked for bounded work, reporting back. Dispatch authority is orchestrator-only; a leaf agent never spawns subagents. |
| **Skill** | A reusable instruction module (`SKILL.md`), loaded on demand rather than living in your prompt every turn. Costs listing budget when catalogued, full tokens only when invoked. |
| **Rule (harness-specific)** | Claude Code: a Markdown rule is instruction context. Codex: a `.rules` Starlark file is command approval policy. Same word, different primitive — always check runtime + extension. |
| **Hook** | Executable the harness runs at a fixed lifecycle point (before/after a tool call, end of turn). Unlike a rule, it has real veto power. |
| **AGENTS.md** | A markdown constitution read as an instruction chain, root -> cwd, nearer wins. Durable, area-stable agreements — not per-task instructions. |
| **MCP** | Injects additional tools/resources beyond the built-in set. Widens what actions exist; never changes personas or rules. |

Context vs enforcement: persona/skill/Markdown-rule/AGENTS.md *inform*; hooks, Codex
`.rules`, and the SDD/root-whitelist gates *enforce*. Always-loaded vs on-demand:
AGENTS.md and always-on rules load every session; skills and path-scoped rules load
only when relevant — the cheap place for long shared protocol.

## Claude Code vs Codex vs Kimi Code deltas

| Primitive | Claude Code | Codex | Watch out for |
|---|---|---|---|
| Persona | `.claude/agents/*.md` | `.codex/agents/*.toml` | Same persona, two serializations, one `public/agents/*.md` source. |
| Constitution | `CLAUDE.md` + `.claude/rules/` | `AGENTS.md` chain, nearest wins | Codex leans on proximity; Claude Code leans on CLAUDE.md + rules. |
| **"Rules"** | Markdown, `.claude/rules/` — context, not enforced | `.rules` Starlark under `.codex/rules/*.rules` — gates command execution | **Naming collision.** Only `.rules` files are executable Codex policy. |
| Hooks | PreToolUse/PostToolUse/Stop/Notification, matcher semantics | Fire in TUI + headless on a live-certified CLI (re-probe after upgrades) | Never assume a Claude Code hook config transplants verbatim. |
| Skills | `SKILL.md`, name/description/`applyTo`, listing-budget aware | Native repo discovery from CWD upward; description is the trigger surface | Concept parity; projection path differs per target. |
| Subagents | Agent tool, orchestrator-only | Explicit spawn/delegation required — no auto-spawn from workflow prose | Codex custom-agent TOML makes a role spawnable; it does not route by itself. |
| Config layers | `~/.claude` + project `.claude/` | `~/.codex`/`CODEX_HOME` + project `.codex/`, trust-gated | Never put a secret/host path in either project layer. |

Kimi Code (third Layer-1 target, `.kimi-code/`) reads `AGENTS.md` natively up-tree, with
an advisory + git-chokepoint posture. Deep Kimi protocol: defer to `ai-engineer`.

## dadaia projection mechanics

You almost never edit a harness file directly — every runtime tree is a **projection**:

```
dadaia_workspace/public/<type>/<file>   (canonical source, only editable copy)
  -> dadaia public stage                (snapshot + SHA256 into manifest.json)
  -> dadaia public install --target all -> .claude/  .agents/  .codex/  .kimi-code/
  -> dadaia public doctor               (verifies every projection against staged hash)
```

Never hand-edit a projection — `.claude/`, `.agents/`, `.codex/`, `.kimi-code/`, and a
projected `AGENTS.md` are lib-originated and manifest-tracked; the next install
overwrites a hand-edit. `dadaia public doctor` reports `[ok]`/`[drift]`/`[missing]` per
file — it does not diff git HEAD vs working tree, so an uncommitted source edit can still
read `[ok]`.

Gates enforce on top of projections: one merged PreToolUse entrypoint (`pre_gate`)
evaluates root-whitelist -> venv-guard -> the SDD gate (path-class x presence x phase x
mode; it never reads TASKS.md — `[-]` reservation is agent discipline), first-block-wins.
Under the NO-LOCKS DOCTRINE (v0.1.76) the gate never blocks on another session's
presence — races surface, never prevent. Git chokepoints (pre-commit WARN-only; pre-push
security-verdict gate) gate commits/pushes independently of harness hooks.

## When to defer to `ai-engineer`

| Situation | Action |
|---|---|
| Reasoning about *why* a primitive behaves a certain way | Defer. |
| Diagnosing a hook/skill/rule interaction or projection drift you do not understand | Defer (drift *repair* via `--force` is operator/devops-only). |
| Designing, authoring, or modifying any AI-entity file | Defer — product-engineer specs it, ai-engineer implements it. |
| The deep decision protocol for a harness, or context engineering | Defer — this skill's siblings are `ai-engineer`-only depth. |
| You just need to *read* your own persona/rule/skill to do your task | No deferral — that is this Part. |

---

# Part 2 — Authoring/auditing depth (`ai-engineer` only)

Restricted to `ai-engineer` by `DADAIA.md` §2 (skill scope). Four disclosed siblings,
each a compiled decision-protocol reference — never a copy of vendor docs (A11.2:
consult official docs via each sibling's own link index, on demand, cite the URL, do not
transcribe it).

| Sibling | Purpose |
|---|---|
| `CLAUDE-CODE.md` | Claude Code harness model — agentic loop/compaction, context hierarchy, rules/skills/hooks/subagents/tools/MCP decision protocols. |
| `CODEX.md` | Codex harness model — AGENTS.md stacking, the Rules naming collision, config-layer trust model, skills/subagents/hooks deltas. |
| `CONTEXT-ENGINEERING.md` | Harness-agnostic craft — token economy, instruction hierarchy, persona-consistency invariants, model-tier selection, scope-drift detection. |
| `AUTHORING.md` | The writing-for-agents authoring contract for every AI-entity file this workspace ships: pointer quality, the two loads, information hierarchy, completion criteria, leading words over negation, pruning. |

## Authoring guardrails (apply every time)

- All authoring targets are `dadaia_workspace/public/...` source. Never hand-edit
  `.claude/`, `.codex/`, `.agents/`, `.kimi-code/` projections; propagate via
  `dadaia public stage && dadaia public install`.
- No consumer-specific names, hostnames, IPs, private repo slugs, secrets, or
  operator-private data in any authored asset.
- Tables over prose for enumerable rules. Compiled protocol over doc transcription.
