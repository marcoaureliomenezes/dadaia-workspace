# CLAUDE-CODE.md — Claude Code Harness Mastery

Sibling of [`SKILL.md`](SKILL.md) (`dd-ai-eng-knowhow`, `ai-engineer`-only depth). A
reasoned decision surface, not a documentation mirror: it compiles how the Claude Code
harness actually behaves so an authoring decision (CLAUDE.md vs rule vs skill vs hook vs
subagent vs MCP) can be made from protocol, not from re-derivation. The official docs are
an on-demand reference index at the end (§9) — consult, never transcribe.

The one law everything else hangs from: **the model decides; the harness enforces.**
CLAUDE.md, memory, rules, and skill bodies *shape* behavior — they are context, not
guarantees. Only hooks and permission rules are guarantees. Every decision below is an
application of that line.

---

## 1. Agentic loop model — and the compaction boundary

The harness runs a repeating loop: gather context -> take action -> verify -> repeat.
Each tool call returns a result that feeds the next decision; a turn ends when the model
stops emitting tool calls (or the operator interrupts). `Stop` hooks fire at that
boundary.

The context window holds conversation history, file contents, command outputs,
CLAUDE.md, auto memory, loaded skill bodies, and system instructions. As it fills, the
harness **compacts**: it clears older tool outputs first, then summarizes the
conversation.

| What survives compaction | What is discarded |
|---|---|
| Project-root CLAUDE.md (re-read from disk) | Detailed instructions given only in conversation |
| Auto memory index (re-read from disk) | Old tool outputs (cleared first) |
| Path-scoped rules (re-loaded on matching file access) | Conversation detail (summarized lossily) |
| Most-recent skill invocation (partially re-attached, capped) | Earlier skill invocations beyond the re-attach budget |

**Authoring implication (load-bearing).** If a behavior must hold across a long session,
it cannot live in a one-time chat instruction or rely on a skill body staying resident —
both evaporate at the compaction boundary. A standing rule belongs in CLAUDE.md / a rule
file (survives) or, if it must hold *every time*, in a hook (deterministic, zero context
cost). A skill whose guidance is lost at compaction was placed at the wrong layer;
promote it to a rule or re-invoke it. Subagents sidestep the problem entirely: a big
exploration runs in an isolated window and returns only a summary, so it never bloats —
or survives in — the parent context.

---

## 2. Context hierarchy decision protocol (ADR-style)

Four layers carry standing instruction, ordered by *when they load*. Pick the cheapest
layer that still loads when the instruction is needed.

| Need | Layer | Loads | Cost | Pick when |
|---|---|---|---|---|
| Core convention every session needs | Project `CLAUDE.md` (`./CLAUDE.md` or `./.claude/CLAUDE.md`) | Full, every session; survives compaction | Every request | "Always do X" law, build commands, entry-point pointers |
| Personal cross-project preference | User memory (`~/.claude/CLAUDE.md`) | Full, every session, all projects | Every request, only on your machine | Machine-local prefs that should not ship to the team |
| Topic law, possibly directory-specific | Rule (`.claude/rules/*.md`) | Every session if unscoped; on matching-file access if `paths:` scoped | Every request (unscoped) or zero until matched | Standing law you want modular; scope by `paths:` when it governs only one subtree |
| Sometimes-needed reference or workflow | Skill (`.claude/skills/<name>/SKILL.md`) | Description every session; body on invoke | Description tax only until used | Multi-step protocol, deep reference, or knowledge needed occasionally |

Decision rules:
- CLAUDE.md growing past ~200 lines? Move reference material to skills or split topics
  into rules. Long CLAUDE.md consumes context and *lowers* adherence.
- A "see X" prose pointer loads nothing. In Claude Code, only an `@import` or a symlink
  actually pulls a file in. If you intend a file to be read, import it.
- Personal machine-local content goes to `~/.claude/` and `CLAUDE.local.md` (gitignored),
  never into team-shared `public/` source — that ships open-source (privacy gate).

---

## 3. Rules enforcement model — always-on vs path-scoped

A rule is a modular instruction file that loads alongside CLAUDE.md. Its scope is set by
frontmatter:

| Frontmatter | Activation | Use for |
|---|---|---|
| No `paths:` | Always-on; loads every session for every task | Truly global law (workspace protocol, tmp-file guardrail) |
| `paths: [glob, ...]` | Loads only when the model works with a matching file | Directory- or language-specific law (e.g. game rules -> one subtree) |

A rule **fires** by being present in context — the model reads it and is expected to
comply, but compliance is *advisory* (it is still just context). A **skill** is *invoked*
(its body enters context on demand and the model acts on it). Rule of separation:
standing law that should color all reasoning -> rule; a procedure the model runs when a
specific task arises -> skill; a guarantee that must hold regardless of model choice ->
hook.

**Gotcha — an unscoped rule inflates every context.** A rule with no `paths:` loads for
every session even when irrelevant (a game rule polluting a Python task). When authoring
a rule that governs only one subtree, add a `paths:` glob so it stays out of unrelated
contexts. Reserve always-on for genuinely global law.

---

## 4. Skills mechanics — and the listing-budget tax

A skill is a `SKILL.md` (frontmatter + body) the model adds to its toolkit. The body
loads only when the skill is invoked, so long reference material is nearly free until
used — but the **description is not free**.

Frontmatter levers that matter for authoring:

| Field | Effect | Authoring lever |
|---|---|---|
| `name` | Listing label | Keep stable; it is the scope-rule and reference target |
| `description` (folded `>`) | Matched to decide auto-load; loaded *every session* | Key use case first; keep tight — this is the recurring tax |
| `paths:` (native) | Limits when the skill auto-activates | The real path-scoping field |
| `disable-model-invocation: true` | Only the operator can invoke; description leaves context | Zero listing cost; use for side-effect or operator-only workflows |
| `user-invocable: false` | Only the model can invoke; hidden from the `/` menu | Pure background protocol with no meaningful operator action |

**Gotcha — the listing-budget tax is N skills x description tokens.** Descriptions of all
model-invocable skills load every session, capped near 1% of the context window. On
overflow, the least-used descriptions are dropped first, stripping the keywords the
model needs and causing mis-triggering. Adding skills is not free: each new
model-invocable skill raises the fixed per-session tax. **Split-vs-merge protocol:**
split a skill only when the two halves are invoked in genuinely different situations
(distinct triggers); otherwise merge to spend one description instead of two (this skill
folder is the worked example — four skills merged to one description). For
agent-internal protocols nobody types as a command, prefer `user-invocable: false` (or
name-only) to keep the body available while shrinking listing pressure.

**Gotcha — `applyTo` is silently ignored by Claude Code.** The native path-scoping field
is `paths:`, not `applyTo:`. A skill scoped with `applyTo:` is governed *only* by its
description and stays model-invocable everywhere — the intended scoping does nothing.
When path-scoping is the goal, use `paths:`. (dadaia's skills carry `applyTo:` in
frontmatter as a listing convention consumed by the projection toolchain, not as a
Claude Code activation lever — do not mistake it for native scoping.)

---

## 5. Hooks lifecycle — the determinism primitive

A hook is a handler that fires at a fixed lifecycle point. Unlike a rule or skill body,
which the model interprets, a hook **always** fires on its event — this is how an
advisory rule becomes a guarantee. Config shape: **event -> matcher -> handler**.

| Event | Fires | Can block? | Matcher tests |
|---|---|---|---|
| `UserPromptSubmit` | Prompt submitted, before processing | Yes | none (every prompt) |
| `PreToolUse` | Before a tool runs | Yes | tool name |
| `PostToolUse` | After a tool succeeds | Yes (feeds reason back; cannot undo side effects) | tool name |
| `Stop` | Model finishes a turn | Yes (tells the model to keep going) | none |
| `Notification` | Harness raises a notification | No | notification context |

PreToolUse decision flow: **deny** (block, reason fed back) -> **ask** (force a prompt)
-> **allow** (optionally with `updatedInput` to rewrite the call) -> **defer** (let
normal flow decide). Command-hook decision is carried by exit code (`0` success / `2`
blocking error) plus stdout JSON.

Matcher semantics — the detail that bites:

| Matcher | Means |
|---|---|
| `""`, `"*"`, or omitted | **Match every tool** — not a safe default |
| `Edit\|Write` (letters/`_`/`\|`) | Exact tool name or `\|`-list |
| anything else | JavaScript regex (e.g. `^Notebook`, `mcp__.*`) |

**Gotcha — an empty matcher fires on every tool.** A write-gate wired with
`"matcher": ""` runs on `Read`, `Grep`, `Glob`, `WebFetch`, `TaskCreate` — taxing every
call and making enforcement hard to reason about. Scope write-gates to
`"Edit|Write|MultiEdit|NotebookEdit"` (add `Bash` only if the gate genuinely inspects
shell-side writes). Leave `UserPromptSubmit` context-injection unmatched — the hook
*should* fire every prompt, but inject the **full** static context only **once per
logical session** (a session-keyed sentinel makes every later prompt a silent no-op).
Never wire a hook that re-injects the whole bootstrap on each prompt — that is token
waste and drift.

Failure modes and the right primitive:
- PreToolUse is a guardrail, not a hard boundary: a script that writes files itself can
  slip past it. Keep a server-side backstop (e.g. a `doctor` check) for true
  enforcement.
- Hooks run unsandboxed on the operator's machine and load only after project-trust is
  accepted — treat any new hook as privileged-code review.

Hook vs rule vs skill-body guard:

| If the constraint must... | Use |
|---|---|
| hold *every time*, regardless of model choice | a **hook** (deterministic) |
| color all reasoning but tolerate interpretation | a **rule** (advisory, survives if always-on/path-matched) |
| be applied only while a specific procedure runs | a **guard in the skill body** (interpreted, scoped to invocation) |

---

## 6. Subagents and dispatch authority

The `Agent` tool spawns a subagent in its **own** context window with a custom system
prompt, narrowed tools, and independent permissions; it works a delegated task and
returns a single summary. dadaia's agent personas *are* Claude Code subagents — isolated
context, scoped `tools:` frontmatter.

Dispatch authority follows from this: a persona that holds the `Agent` tool can spawn
other agents. Granting dispatch to a worker breaks the topology — workers must not
recursively spawn workers.

| Tier | Role | `Agent` (dispatch) tool |
|---|---|---|
| Tier 1 | Orchestrators / dispatchers | Allowed |
| Tier 2 | Synthesis / review with delegated sub-work | Allowed only when the brief justifies it |
| Tier 3 | Implementers / workers | **Never** — would let a worker spawn workers |

Authoring rule: never add the `Agent` tool to a Tier-3 persona. Dispatch authority is
reserved to dispatchers and must be justified by an operator-approved brief.

---

## 7. Tools and permission model

Tools are the model's agency; the *exact tool-name strings* are the vocabulary of
permission rules, subagent tool lists, and hook matchers. Read-only tools (`Read`,
`Glob`, `Grep`, `Agent`, `AskUserQuestion`) run without prompting; mutating tools
(`Edit`, `Write`, `Bash`, `WebFetch`, `Skill`, `Workflow`) require permission.

Two distinct layers:
- **Permission rules** (`ToolName(specifier)` in settings, `--allowedTools`/
  `--disallowedTools`, subagent `tools:`, skill `allowed-tools`). Evaluated
  **deny -> ask -> allow, first match wins**. An `Edit(path)` allow also grants read of
  that path.
- **Hook matchers** use *bare* tool names (`Edit|Write`), **not** the parenthesized rule
  format. Do not confuse the two syntaxes.

Restrict-vs-trust protocol:
- Narrow a subagent's surface with `tools:`/`disallowedTools:` rather than relying on
  broad global allows. Background subagents auto-deny anything that would prompt.
- A blanket-allow permission layer is acceptable *only* when real enforcement lives in
  correctly-scoped hooks: blanket allows plus an unscoped or stale rule set means almost
  no friction on writes. If hooks are the enforcement boundary, keep them scoped; prune
  dead/stale permission entries.

**Gotcha — NOTHING enforces the per-persona write-allowlist.** Native frontmatter fields
(`name`, `description`, `model`, `tools`, `skills`, `maxTurns`) are honored; dadaia
extras (`dispatch_band`, `input_contract`, `paths.write_allowlist`) are silently ignored
by the runtime — and dadaia's PreToolUse gate does NOT read them either (no hook can
resolve persona identity). The gate enforces path-class x presence x phase x mode,
persona-blind. `paths.write_allowlist` is an agent-instruction convention checked by
tooling/tests and reviewers, nothing else. Never assume any runtime or hook polices a
persona's write scope.

---

## 8. MCP and tool-search

An MCP server connects the harness to external systems and **injects tools** (matched in
hooks as `mcp__<server>__<tool>`). **Tool Search** defers MCP tool schemas: only tool
names load at startup; the full schema loads on demand — so idle servers cost almost
nothing.

Prefer-MCP-vs-native protocol:
- A built-in tool covers the job -> use native; do not add an MCP server for what
  `Bash`, `Read`, or `WebFetch` already do.
- The need is a *connection* to an external system the model cannot otherwise see (a DB,
  an issue tracker, a docs service) -> MCP provides the connection and tools; a skill
  provides the *knowledge* of how to use them well. They pair: MCP = capability, skill =
  know-how.
- Rely on tool-search so enabling a server does not tax every session; the schema cost
  is paid only when a tool is actually used.

---

## Composition decision tree

Given a new harness need, walk this tree. Every branch is one of the gotchas above,
applied.

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

Standing reminders: prune stale/dead permission entries and machine-specific paths from
settings before they mislead; do not project a `.claude/workflows/` reference
directory — there is no workflow engine, and the ordered SDD flow is agent-dispatched,
never a declarative workflow file Claude Code executes.

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
