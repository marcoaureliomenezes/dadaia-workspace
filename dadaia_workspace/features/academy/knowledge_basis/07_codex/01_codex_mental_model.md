# 01. Codex Mental Model

Codex is OpenAI's coding agent across CLI, IDE, app, and cloud surfaces. In
dadaia-workspace, the local CLI/runtime projection matters most: Codex reads the
repository, follows instructions, uses tools, can run hooks, can load skills, and
can spawn custom agents when explicitly asked.

The first correction is simple: Codex is not a workflow daemon. It does not watch
`public/workflows/*.workflow.md` and automatically route every user demand through
`project-manager`. It follows instructions in the current session. If the task
needs subagents, the operator or dispatcher must explicitly ask Codex to spawn or
delegate to them.

## The Surfaces That Matter

| Surface | What It Is | dadaia Use |
|---|---|---|
| Prompt/thread | One-off intent and constraints | Current operator demand, exact task, temporary exceptions |
| `AGENTS.md` | Durable scoped guidance | Workspace law, repo rules, path-specific behavior |
| Skill | Reusable workflow package | SDD navigation, Codex harness audit, report emission |
| Plugin | Installable bundle | Share skills, MCP, hooks, apps, and assets across users |
| MCP | External context/actions | Docs servers, GitHub, Figma, browser tools |
| Hook | Lifecycle command | SDD gate, context injection, heartbeat, root whitelist |
| Codex Rule | Command approval policy | Allow/prompt/forbid shell command prefixes |
| Custom agent | Spawnable role profile | `ai-engineer`, `qa-engineer`, `security-reviewer`, etc. |

The practical question is always: "Does this need to be remembered, reused,
enforced, delegated, or connected to another system?" That answer chooses the
primitive.

## What Codex Enforces vs What It Reads

Codex reads many text surfaces, but only some are mechanical enforcement:

- `AGENTS.md` influences model behavior. It is durable guidance, not a filesystem
  lock.
- Skills influence model behavior after activation. Their descriptions are the
  trigger surface; full bodies are loaded only when selected.
- Hooks execute host commands at lifecycle events. They can block or mutate state
  depending on the hook implementation.
- Codex Rules are Starlark command policy. They decide whether a command may run
  outside the sandbox.
- Sandbox and approval policy are runtime controls. They are stronger than text.

In dadaia terms, the SDD gate is a hook, so it can mechanically block file-write
tools. The rule "reserve a TASKS.md marker before implementation" is a discipline
contract unless a hook checks it. Treat that distinction as a design constraint,
not a weakness.

## The Correct Build Order

1. Put stable repo expectations in the closest `AGENTS.md`.
2. Put repeatable procedures in skills.
3. Use hooks for lifecycle checks that must run automatically.
4. Use Codex Rules for command approval policy only.
5. Use MCP when the workflow needs external systems.
6. Use custom agents/subagents when work should be delegated explicitly.
7. Package reusable bundles as plugins only when distribution is the goal.

## Why This Matters for dadaia

dadaia-workspace has a dispatcher architecture: `project-manager` and
`project-auditor` coordinate, while leaf agents perform specialized work. Claude
Code and Codex expose different runtime affordances around that architecture. The
Codex projection must therefore be honest:

- Custom agents can exist as `.codex/agents/*.toml`.
- Workflow markdown can describe the process.
- Skills can teach the dispatcher how to operate.
- Hooks can enforce local mechanics.
- But no Codex workflow file automatically launches the whole agent graph.

The operator experience improves when the projection says exactly where manual or
explicit delegation is required.
