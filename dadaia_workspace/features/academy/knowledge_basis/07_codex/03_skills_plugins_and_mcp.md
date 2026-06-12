# 03. Skills, Plugins, and MCP

Skills are Codex's reusable workflow unit. A skill is a directory with `SKILL.md`
and optional scripts, references, or assets. Codex initially sees only skill
metadata, especially `name` and `description`; it reads the full `SKILL.md` only
when it decides to use that skill.

## Skill Discovery

Codex can load skills from repository, user, admin, and system locations. The repo
locations that matter for dadaia are `.agents/skills` directories from the current
working directory up to the repository root. User skills usually live under
`$HOME/.agents/skills`.

The description is the trigger. Write it as an operational signal:

```yaml
---
name: ai-harness-codex
description: Use when authoring or auditing Codex-facing AGENTS.md, Rules, skills, hooks, custom agents, or workflow integration.
---
```

Good skills are focused. They do not replace a SPEC, carry broad product truth, or
duplicate an entire docs site. They teach a repeatable procedure.

## Skills in dadaia

dadaia uses skills for protocols that multiple agents need:

- `dadaia-workspace-spec-navigator` loads active release context.
- `dadaia-task-manager` defines task marker discipline.
- `ai-harness-codex` teaches Codex-specific AI-surface decisions.
- `harness-primitives` gives all agents a lighter shared vocabulary.

`ai-engineer` should use `ai-harness-codex` when changing Codex-facing agents,
skills, hooks, rules, config, or workflow projection. Other agents usually use the
lighter shared skill unless they are explicitly auditing AI entities.

## Plugins

Plugins are the distribution unit. A plugin can bundle:

- one or more skills;
- app integrations;
- MCP server configuration;
- lifecycle hooks;
- presentation assets.

Use a local skill while iterating in one repository. Build a plugin when the
workflow needs to be installed by other developers, shared across a workspace, or
distributed with MCP/app configuration.

## MCP

MCP connects Codex to external tools and context providers. Codex can use MCP
servers over stdio or streamable HTTP. Servers can expose tools, resources, and
prompts.

Use MCP when the workflow needs something outside the local repo:

- official docs search;
- GitHub operations beyond local `git`;
- browser automation;
- design tools;
- issue trackers;
- internal knowledge systems.

Skills and MCP pair well: the skill defines the workflow, and MCP supplies live
capabilities. If a skill requires an MCP server, declare that dependency through
Codex metadata where appropriate so installation is clear.

## Boundary Rules

| Need | Use |
|---|---|
| Repeatable local procedure | Skill |
| Reusable installable bundle | Plugin |
| External live context or action | MCP |
| Persistent repo instruction | `AGENTS.md` |
| Command approval policy | Codex Rule |
| Lifecycle enforcement | Hook |

Avoid pretending one primitive does the job of another. In particular, a skill can
tell Codex how to dispatch; it does not itself spawn subagents unless the active
Codex session is instructed to do so.
