---
name: harness-primitives
description: >
  Shared literacy for ALL agents. A working mental model of the AI-entity
  primitives every dadaia agent runs on (persona, subagent, skill, rule, hook,
  AGENTS.md, MCP), the Claude-Code-vs-Codex naming/behavior deltas, how dadaia
  projects public/ source to every runtime, and when to defer harness depth to
  ai-engineer. Middle-depth literacy, not mastery.
applyTo: "**"
---

# harness-primitives — A Shared Mental Model of the Harness

You run inside an *agentic harness* — the tooling, context management, and
execution loop that turn a model into a working agent. The harness (Claude Code,
Codex, or PI) is not the model; it supplies your file access, shell,
permission gating, memory loading, and the gather→act→verify loop. This skill gives
every agent a working mental model of the primitives that harness exposes, so you can
read your own configuration intelligently and know when a question is beyond your
remit.

**Two agentic layers** (constitution §0 "The two agentic layers"). dadaia runs agents at
**Layer 1** — the entry harness a human launches in a terminal (`claude`, `codex`,
`pi`) — and **Layer 2** — a bounded worker driven inside a Python
`dadaia lifecycle` workflow behind the `AgentRuntimePort` seam, selectable per step as
Codex headless or PI headless. FAKE is an internal test adapter; Claude Code is
Layer-1-only. This literacy
skill describes the Layer-1 entry-harness primitives; the Layer-2 worker-runtime model is
deep harness depth — defer to `ai-engineer`.

This is **literacy, not mastery.** For deep reasoning about *why* a primitive
behaves a certain way — or to author/diagnose one — defer to `ai-engineer`
(see the last section).

## Primitive catalog

Each primitive answers a different question the harness asks before and during a
task. Knowing which is which keeps you from looking for enforcement where there is
only context, or for behavior change where there is only documentation.

| Primitive | One-line definition |
|---|---|
| **Agent persona** | The durable identity, scope, and write-allowlist of a single agent. It is a prompt loaded as your operating contract: who you are, what you write, what you refuse. In dadaia, personas live in `public/agents/*.md`. |
| **Subagent (dispatch)** | A separate agent invoked to do bounded work and report back. Dispatch authority is reserved to orchestrator tiers; a leaf agent does not spawn subagents. In Codex, custom-agent files make roles spawnable, but an explicit spawn/delegation request is still required. |
| **Skill (on-demand module)** | A reusable instruction module (`SKILL.md`) loaded when its name/`applyTo` is relevant, rather than living in your prompt every turn. Skills compress shared protocols (this file is one). They cost listing budget when catalogued and full tokens only when invoked. |
| **Rule (harness-specific)** | In Claude Code, a Markdown rule is instruction context. In Codex, a `.rules` Starlark file is command approval policy using `prefix_rule(...)`. Same word, different primitive; always check the runtime and extension. |
| **Hook (PreToolUse / PostToolUse / Stop)** | An executable that the harness runs at a fixed point in the loop: *before* a tool call (can block it), *after* a tool call, or at the *end of a turn*. Unlike a rule, a hook is real code with real veto power — it is the only primitive that can deterministically stop an action. |
| **AGENTS.md (scoped constitution)** | A markdown constitution the harness reads as an instruction chain from repo root down to the working directory; nearer files win on conflict. It holds durable, area-stable agreements (build commands, conventions, definition of done) — not per-task instructions. |
| **MCP (tool injection)** | Model Context Protocol servers inject *additional tools* (and resources) into the harness beyond the built-in file/shell set — e.g. a docs server or a browser driver. MCP widens what actions exist; it does not change personas or rules. |

Mental shortcuts:
- **Context vs enforcement:** persona, skill, Claude-style Markdown rule, and
  AGENTS.md are *context* (they inform). Hooks, Codex `.rules`, and the SDD/root-
  whitelist gates are *enforcement* (they can block).
- **Always-loaded vs on-demand:** AGENTS.md and `always_on` rules load every
  session; skills and path-scoped rules load only when relevant — that is why
  skills are the cheap place to put long shared protocols.

## Claude Code vs Codex deltas

The same word can mean different things across harnesses. The most dangerous
collision is "rules". Read this table before assuming a primitive behaves the same
way in both runtimes. (PI is the third Layer-1 projection target — under `.pi/`
(post-trust executable); it reads `AGENTS.md` natively up-tree, with an advisory +
git-chokepoint posture. Deep PI protocol is out of scope for this literacy skill.)

| Primitive | Claude Code | Codex | Watch out for |
|---|---|---|---|
| Persona | `.claude/agents/*.md` (Markdown + YAML frontmatter) | `.codex/agents/*.toml` | Same persona, two serializations; both projected from one `public/agents/*.md` source. |
| Constitution | `CLAUDE.md` + `.claude/rules/` loaded as context | `AGENTS.md` instruction chain, root → cwd, nearest wins | Codex leans on AGENTS.md proximity; Claude Code leans on CLAUDE.md + rules. |
| **Rules** | `always_on` or path-scoped **Markdown** instruction files in `.claude/rules/` — *context*, not auto-enforced | Official Codex **Rules** are Starlark `.rules` files under `.codex/rules/*.rules` that gate whether a command may run | **Naming collision.** Markdown protocols are guidance; only `.rules` files are executable Codex command policy. |
| Hooks | Lifecycle events: PreToolUse, PostToolUse, Stop, Notification, with matcher semantics | Hook mechanism exists with its own lifecycle and config surface; fires only in the interactive TUI on 0.139.0 — never under headless `codex exec` | Hook event names and matcher semantics differ; never assume a Claude Code hook config transplants verbatim to Codex — Codex harness-hook enforcement is interactive-only today; the headless gap is covered by the git chokepoints (pre-commit, WARN-only; pre-push security-verdict gate), which fire independently of harness hooks. |
| Skills | `SKILL.md` with name/description/`applyTo`; listing-budget aware | Skills as reusable modules under the Codex tree | Concept parity; projection path and frontmatter handling differ per target. |
| Subagents | Dispatch via the Agent tool, orchestrator-only | Explicit subagent workflows; custom agents in `.codex/agents/*.toml` | Codex does not auto-spawn from workflow markdown; ask for delegation/parallel agents explicitly. |
| Config layers | `~/.claude` (global) + project `.claude/` | `CODEX_HOME` / `~/.codex` (global) + project `.codex/`; trust model on project-local config | What is safe project-local differs; never put a secret or host-specific path in either project layer. |

If you need to *act on* a delta in this table — not just know it exists — that is
ai-engineer's call.

## dadaia projection mechanics

You almost never edit a harness file directly. Every runtime tree is a
**projection** of a single canonical source. The chain is one-directional:

```
dadaia_workspace/public/<type>/<file>     # canonical source — the ONLY editable copy
        │
        ▼  dadaia public stage             # snapshots source, writes SHA256 to manifest.json
        │
        ▼  dadaia public install --target all
        │
        ├─ .claude/    (agents, rules, skills)
        ├─ .agents/    (skills)
        ├─ .codex/     (agents .toml, config, hooks, rules, Codex-only skills)
        └─ .pi/        (SYSTEM.md, settings.json, prompts — post-trust executable)
        │
        ▼  dadaia public doctor            # verifies every projection matches the staged SHA256
```

Rules that follow directly from this chain:

- **Never hand-edit a projection.** Files under `.claude/`, `.agents/`, `.codex/`,
  `.pi/`, and projected `AGENTS.md` are lib-originated and manifest-tracked.
  Editing them in place is overwritten on the next install and is a guardrail
  violation. Edit the `public/` source, then stage + install.
- **`dadaia public doctor`** compares each projection against the staged hash and
  reports per-file status: `[ok]` (matches), `[drift]` (differs — needs
  `--force` reinstall), `[missing]` (absent — needs install),
  `[unsupported]`/`[not-applicable]` (no action). It does NOT compare git HEAD vs
  working tree, so an uncommitted source edit can still show `[ok]`.
- **Gates are the enforcement layer** on top of projections: a single merged
  PreToolUse entrypoint (`pre_gate`) evaluates root-whitelist (no stray files at the
  workspace root) → venv-guard (workspace commands rooted in `.dadaia/.venv/bin/`,
  fixed patterns only) → the SDD gate (path-class × presence × phase × mode — it reads
  no TASKS.md markers; `[-]` reservation is agent discipline), first-block-wins.
  Under the NO-LOCKS DOCTRINE (v0.1.76) the gate never blocks on another session's
  presence — races are accepted and surfaced, never prevented. Git chokepoints
  (pre-commit, WARN-only detection; pre-push security-verdict gate) gate commits and
  pushes independently of harness hooks. Rules and personas inform; gates, chokepoints,
  and hooks block.

## When to defer to ai-engineer

`ai-engineer` owns the AI-entity surface (`public/agents`, `skills`, `rules`,
`workflows`, `commands`, `hooks`). Use this checklist: if any line is true, hand
the question to ai-engineer rather than guessing.

| Situation | Action |
|---|---|
| You need to reason about *why* a primitive behaves a certain way (e.g. why a rule loaded but did not block) | Defer to ai-engineer. |
| You are diagnosing a hook/skill/rule interaction or a projection drift you do not understand | Defer to ai-engineer (drift *repair* via `--force` is operator/devops-only). |
| You want to design, author, or modify any AI-entity file (persona, skill, rule, hook) | Defer to ai-engineer — product-engineer specs it, ai-engineer implements it. |
| You want the deep decision protocol for any Layer-1 harness (Claude Code, Codex, PI), the Layer-2 worker-runtime model, or context engineering | Defer to ai-engineer. Those deep skills (`ai-harness-claude-code`, `ai-harness-codex`, `ai-context-engineering`) are restricted to ai-engineer by the `harness-skill-scope` rule — do not attempt to invoke them. |
| You just need to *read* your own persona/rule/skill to do your task | No deferral — that is normal literacy, which is what this skill is for. |

In one sentence: know the primitives well enough to read your own configuration
and respect the projection chain; route every *why*, *diagnose*, or *design*
question about the harness to `ai-engineer`.
