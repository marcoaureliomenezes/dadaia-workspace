# CLAUDE-CODE.md — Claude Code Harness Mastery

Sibling of [`SKILL.md`](SKILL.md) (`dd-ai-eng-knowhow`, authoring depth).
A decision surface, not a doc mirror — official docs are an on-demand index at "Official reference index"; consult, never transcribe.

- Governing law: the model decides, the harness enforces.
- CLAUDE.md, memory, rules, skill bodies shape behavior — context, not guarantee.
- Only hooks and permission rules guarantee.

---

## 1. Agentic loop model and the compaction boundary

- Loop: gather context -> act -> verify -> repeat.
- A turn ends when the model stops emitting tool calls or the operator interrupts; `Stop` hooks fire at that boundary.
- Context window holds: conversation history, file contents, command outputs, CLAUDE.md, auto memory, loaded skill bodies, system instructions.
- Compaction, as the window fills: clears older tool outputs first, then summarizes the conversation.

| What survives compaction | What is discarded |
|---|---|
| Project-root CLAUDE.md (re-read from disk) | Detailed instructions given only in conversation |
| Auto memory index (re-read from disk) | Old tool outputs (cleared first) |
| Path-scoped rules (re-loaded on matching file access) | Conversation detail (summarized lossily) |
| Most-recent skill invocation (partially re-attached, capped) | Earlier skill invocations beyond the re-attach budget |

- A behavior that must hold across a long session belongs in an `AGENTS.md` line (law) or a hook (deterministic).
- A skill whose guidance is lost at compaction is placed at the wrong layer — promote it to an `AGENTS.md` line, or re-invoke it.
- Subagents isolate a big exploration in its own context window and return only a summary.

---

## 2. Context hierarchy decision protocol (ADR-style)

- Four layers carry standing instruction, ordered by when they load.
- Pick the cheapest layer that still loads when the instruction is needed.

| Need | Layer | Loads | Pick when |
|---|---|---|---|
| Core convention every session needs | Project `CLAUDE.md` | Full every session; survives compaction | Build commands, the harness bootstrap; law lives in `AGENTS.md` |
| Personal cross-project preference | User memory (`~/.claude/CLAUDE.md`) | Full every session, all projects, local only | Machine-local prefs |
| Topic instructions, maybe directory-specific | Rule (`.claude/rules/*.md`) | Every session (unscoped) or on match (`paths:`) | Harness-only modular instructions; law lives in `AGENTS.md` |
| Sometimes-needed reference | Skill (`SKILL.md`) | Description every session; body on invoke | Multi-step protocol, deep reference |

- CLAUDE.md past ~200 lines lowers adherence: move reference material to skills, split law into scoped `AGENTS.md` files.
- A "see X" prose pointer loads nothing in Claude Code — only an `@import` or a symlink pulls a file in.
- Personal machine-local content goes to `~/.claude/` and `CLAUDE.local.md` (gitignored).

---

## 3. Rules enforcement model — always-on vs path-scoped

- A rule is a modular instruction file that loads alongside CLAUDE.md; scope is set by frontmatter.

| Frontmatter | Activation | Use for |
|---|---|---|
| No `paths:` | Always-on; loads every session for every task | Instructions for every task |
| `paths: [glob, ...]` | Loads only on a matching-file access | Directory- or language-specific instructions |

- A rule fires by presence in context — advisory, the model is expected to comply.
- A skill is invoked — its body enters context on demand and the model acts on it.
- Add `paths:` for subtree-only instructions; reserve always-on for genuinely global instructions.

---

## 4. Skills mechanics — and the listing-budget tax

- A skill's body loads only on invoke — long reference material is nearly free until used; a subagent's `skills:` grants preload the full body at every dispatch.
- The description is not free: it loads every session.

| Field | Effect | Authoring lever |
|---|---|---|
| `name` | Listing label | Keep stable; scope-rule and reference target |
| `description` (folded `>`) | Matched to decide auto-load; loaded every session | Key use case first; keep tight |
| `paths:` (native) | Limits when the skill auto-activates | The real path-scoping field |
| `disable-model-invocation: true` | Only the operator can invoke | Zero listing cost; side-effect/operator-only |
| `user-invocable: false` | Only the model can invoke, hidden from `/` menu | Background protocol, no operator action |

- Gotcha: listing-budget tax = N skills x description tokens, capped near 1% of context window.
- Overflow drops least-used descriptions first, causing mis-triggering.
- Split-vs-merge: split a skill only on genuinely distinct triggers; otherwise merge to one description.
- Prefer `user-invocable: false` for agent-internal protocols nobody types as a command.

---

## 5. Hooks lifecycle — the determinism primitive

- A hook fires on its event always, unlike a rule/skill body the model interprets.
- This is how an advisory rule becomes a guarantee. Shape: event -> matcher -> handler.

| Event | Fires | Can block? | Matcher tests |
|---|---|---|---|
| `UserPromptSubmit` | Prompt submitted, before processing | Yes | none (every prompt) |
| `PreToolUse` | Before a tool runs | Yes | tool name |
| `PostToolUse` | After a tool succeeds | Yes (feeds reason back; cannot undo) | tool name |
| `Stop` | Model finishes a turn | Yes (tells model to keep going) | none |
| `Notification` | Harness raises a notification | No | notification context |

- PreToolUse decision flow: deny (block, reason fed back) -> ask (force a prompt) -> allow -> defer.
- `allow` optionally carries `updatedInput` to rewrite the call.
- Command-hook decision: exit code (`0` success / `2` blocking) + stdout JSON.

| Matcher | Means |
|---|---|
| `""`, `"*"`, or omitted | Match every tool — not a safe default |
| `Edit\|Write` (letters/`_`/`\|`) | Exact tool name or `\|`-list |
| anything else | JavaScript regex (e.g. `^Notebook`, `mcp__.*`) |

- A gate's matcher is its harness's entry in `hook_wrappers.HOOK_DIALECTS`: scope it to the tools the gate judges.
- Context injection: the rule is `decide_injection` in `injection_policy.py`, not restated here.
- PreToolUse is a guardrail, not a hard boundary — a script that writes files itself can slip past it.
- Keep a server-side backstop (a `doctor` check) for true enforcement.
- Hooks run unsandboxed on the operator's machine, only after project-trust is accepted.
- Treat any new hook as privileged-code review.

| If the constraint must... | Use |
|---|---|
| hold every time, regardless of model choice | a **hook** (deterministic) |
| color all reasoning but tolerate interpretation | standing law: the root map or a scoped `AGENTS.md`; harness-only advisory instructions: a **rule** |
| apply only while a specific procedure runs | a **guard in the skill body** (interpreted) |

---

## 6. Subagents and dispatch authority

- The `Agent` tool spawns a subagent in its own context window — custom system prompt, narrowed tools.
- It works a delegated task and returns one summary. dadaia's agent personas are Claude Code subagents.
- A persona holding the `Agent` tool can spawn other agents.
- Granting dispatch to a worker breaks the topology — workers must not recursively spawn workers.

| Tier | Role | `Agent` (dispatch) tool |
|---|---|---|
| Tier 1 | Orchestrators / dispatchers | Allowed |
| Tier 2 | Synthesis / review with delegated sub-work | Allowed only when the brief justifies it |
| Tier 3 | Implementers / workers | Never — would let a worker spawn workers |

- Dispatch authority is reserved to dispatchers and justified by an operator-approved brief.

---

## 7. Tools and permission model

- Tool names are the vocabulary of permission rules, subagent tool lists, hook matchers.
- Read-only tools (`Read`, `Glob`, `Grep`, `Agent`, `AskUserQuestion`) run unprompted.
- Mutating tools (`Edit`, `Write`, `Bash`, `WebFetch`, `Skill`, `Workflow`) require permission.
- Permission rules (`ToolName(specifier)`, `--allowedTools`, subagent `tools:`) evaluate deny -> ask -> allow, first match wins.
- An `Edit(path)` allow also grants read of that path.
- Hook matchers use bare tool names (`Edit|Write`), not the parenthesized rule format — do not confuse them.
- Narrow a subagent's surface with `tools:`/`disallowedTools:` rather than broad global allows.
- Background subagents auto-deny anything that would prompt.
- A blanket-allow layer is acceptable only when real enforcement lives in correctly-scoped hooks.
- Gotcha: nothing enforces the per-persona write-allowlist.
- Native frontmatter (`name`, `description`, `model`, `tools`, `skills`, `maxTurns`) is honored.
- dadaia's PreToolUse gate is persona-blind: path-class x scope only.

---

## 8. MCP and tool-search

- An MCP server connects the harness to external systems and injects tools (`mcp__<server>__<tool>`).
- Tool Search defers schemas: only tool names load at startup, the full schema loads on demand.
- An idle server costs almost nothing.
- A built-in tool covers the job -> use native; do not add an MCP server for what `Bash`/`Read`/`WebFetch` already do.
- The need is a connection to an external system the model can't otherwise see -> MCP provides connection and tools.
- A skill provides the know-how to use MCP tools well — MCP = capability, skill = know-how.

---

## Composition decision tree

```
Must it hold EVERY time, regardless of what the model decides?
|- yes -> HOOK (deterministic). Scope the matcher to the real tools — never "".
|         Keep a server-side backstop; PreToolUse is a guardrail, not a boundary.
`- no -> Does it connect to an external system the model cannot see?
   |- yes -> MCP server (capability) + a skill (know-how). Lean on tool-search.
   `- no -> Is it standing law that should color reasoning?
      |- yes -> Does it govern only one subtree?
      |         |- yes -> a scoped `AGENTS.md` (never always-on for subtree law).
      |         `- no  -> the root `AGENTS.md` map.
      `- no -> Is it a procedure / reference needed only sometimes?
         |- yes -> SKILL. Path-scope with paths:.
         |         Mind the listing tax: tight description, split only on distinct
         |         triggers, user-invocable:false for internal protocols.
         `- no -> Does a side task flood the main window with output?
            |- yes -> SUBAGENT (isolated window, returns a summary).
            |         Never grant the Agent tool to a Tier-3 worker.
            `- no -> It is probably a one-off; just say it in the turn (but know it
                    will not survive compaction — promote to an `AGENTS.md` line if it
                    must).
```

- Prune stale/dead permission entries and machine-specific paths from settings before they mislead.

---

## 9. Official reference index (on-demand links — no content copied)

Consult these only when a specific detail is needed; cite the URL, do not transcribe.

| Topic | URL |
|---|---|
| How Claude Code works | https://code.claude.com/docs/en/how-claude-code-works |
| Glossary | https://code.claude.com/docs/en/glossary |
| Memory (CLAUDE.md, auto memory, rules) | https://code.claude.com/docs/en/memory |
| Tools reference | https://code.claude.com/docs/en/tools-reference |
| Permissions | https://code.claude.com/docs/en/permissions |
| Skills | https://code.claude.com/docs/en/skills |
| Hooks reference | https://code.claude.com/docs/en/hooks |
| Extend Claude Code (features overview) | https://code.claude.com/docs/en/features-overview |
| Sandboxing | https://code.claude.com/docs/en/sandboxing |
| Worktrees | https://code.claude.com/docs/en/worktrees |
