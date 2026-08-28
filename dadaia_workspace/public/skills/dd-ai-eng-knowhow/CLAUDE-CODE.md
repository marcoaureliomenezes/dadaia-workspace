# CLAUDE-CODE.md — Claude Code Harness Mastery

Sibling of [`SKILL.md`](SKILL.md) (`dd-ai-eng-knowhow`, `ai-engineer`-only depth).
A decision surface, not a doc mirror — official docs are an on-demand index at §9; consult, never transcribe.

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

- A behavior that must hold across a long session belongs in CLAUDE.md/a rule (survives) or a hook (deterministic).
- Never a one-time chat instruction or a resident skill body for a must-hold behavior.
- A skill whose guidance is lost at compaction is placed at the wrong layer — promote it to a rule, or re-invoke it.
- Subagents isolate a big exploration in its own context window and return only a summary.

---

## 2. Context hierarchy decision protocol (ADR-style)

- Four layers carry standing instruction, ordered by when they load.
- Pick the cheapest layer that still loads when the instruction is needed.

| Need | Layer | Loads | Pick when |
|---|---|---|---|
| Core convention every session needs | Project `CLAUDE.md` | Full every session; survives compaction | "Always do X" law, build commands |
| Personal cross-project preference | User memory (`~/.claude/CLAUDE.md`) | Full every session, all projects, local only | Machine-local prefs |
| Topic law, maybe directory-specific | Rule (`.claude/rules/*.md`) | Every session (unscoped) or on match (`paths:`) | Modular standing law |
| Sometimes-needed reference | Skill (`SKILL.md`) | Description every session; body on invoke | Multi-step protocol, deep reference |

- CLAUDE.md past ~200 lines: move reference material to skills, split topics into rules.
- A long CLAUDE.md lowers adherence.
- A "see X" prose pointer loads nothing in Claude Code — only an `@import` or a symlink pulls a file in.
- Personal machine-local content goes to `~/.claude/` and `CLAUDE.local.md` (gitignored).
- Never put machine-local content in team-shared `public/` source, which ships open-source.

---

## 3. Rules enforcement model — always-on vs path-scoped

- A rule is a modular instruction file that loads alongside CLAUDE.md; scope is set by frontmatter.

| Frontmatter | Activation | Use for |
|---|---|---|
| No `paths:` | Always-on; loads every session for every task | Truly global law |
| `paths: [glob, ...]` | Loads only on a matching-file access | Directory- or language-specific law |

- A rule fires by presence in context — advisory, the model is expected to comply.
- A skill is invoked — its body enters context on demand and the model acts on it.
- Rule of separation: standing law coloring all reasoning -> rule.
- A procedure run on a specific task -> skill.
- A guarantee that must hold regardless of model choice -> hook.
- Gotcha: an unscoped rule loads every session even when irrelevant.
- Add `paths:` for subtree-only law; reserve always-on for genuinely global law.

---

## 4. Skills mechanics — and the listing-budget tax

- A skill's body loads only on invoke — long reference material is nearly free until used.
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
- This folder is the worked example — four skills merged to one description.
- Prefer `user-invocable: false` for agent-internal protocols nobody types as a command.
- Gotcha: `applyTo` is silently ignored by Claude Code — the native path-scoping field is `paths:`.
- dadaia's `applyTo:` is a listing convention for the projection toolchain, not a Claude Code activation lever.

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

- Gotcha: an empty matcher fires on every tool (`Read`, `Grep`, `Glob`, `WebFetch`, `TaskCreate` too).
- Scope write-gates to `Edit|Write|MultiEdit|NotebookEdit`.
- Add `Bash` to that matcher only when the gate inspects shell-side writes.
- Inject full static context once per logical session (session-keyed sentinel), never every prompt.
- `UserPromptSubmit` may fire every prompt but must stay a silent no-op after the first injection.
- PreToolUse is a guardrail, not a hard boundary — a script that writes files itself can slip past it.
- Keep a server-side backstop (a `doctor` check) for true enforcement.
- Hooks run unsandboxed on the operator's machine, only after project-trust is accepted.
- Treat any new hook as privileged-code review.

| If the constraint must... | Use |
|---|---|
| hold every time, regardless of model choice | a **hook** (deterministic) |
| color all reasoning but tolerate interpretation | a **rule** (advisory) |
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

- Never add the `Agent` tool to a Tier-3 persona.
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
- Prune dead/stale permission entries.
- Gotcha: nothing enforces the per-persona write-allowlist.
- Native frontmatter (`name`, `description`, `model`, `tools`, `skills`, `maxTurns`) is honored.
- dadaia extras (`dispatch_band`, `input_contract`, `paths.write_allowlist`) are ignored by the runtime.
- dadaia's PreToolUse gate is persona-blind: path-class x presence x phase x mode only.
- `write_allowlist` is a convention checked by tooling/tests/reviewers — no runtime or hook polices it.

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
      |         |- yes -> RULE with paths: (never always-on for subtree law).
      |         `- no  -> always-on RULE, or a line in CLAUDE.md if core+global.
      |                   (A "see X" prose pointer loads nothing — @import it).
      `- no -> Is it a procedure / reference needed only sometimes?
         |- yes -> SKILL. Path-scope with paths:, not applyTo:.
         |         Mind the listing tax: tight description, split only on distinct
         |         triggers, user-invocable:false for internal protocols.
         `- no -> Does a side task flood the main window with output?
            |- yes -> SUBAGENT (isolated window, returns a summary).
            |         Never grant the Agent tool to a Tier-3 worker.
            `- no -> It is probably a one-off; just say it in the turn (but know it
                    will not survive compaction — promote to CLAUDE.md/rule if it
                    must).
```

- Prune stale/dead permission entries and machine-specific paths from settings before they mislead.
- Never project a `.claude/workflows/` reference directory — no workflow engine exists.
- The ordered SDD flow is agent-dispatched, never a declarative workflow file Claude Code executes.

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
