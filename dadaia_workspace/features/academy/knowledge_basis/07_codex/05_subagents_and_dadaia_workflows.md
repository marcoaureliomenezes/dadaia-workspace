# 05. Subagents and dadaia Workflows

Codex can spawn subagents, including custom agents defined in TOML. That does not
mean it spawns them automatically. Official Codex behavior is explicit: subagents
are used when the user or parent agent asks for subagents, delegation, or parallel
agent work.

## Custom Agents

Custom agents are TOML files under `~/.codex/agents/` or `.codex/agents/`. Each file
defines one role with:

- `name`;
- `description`;
- `developer_instructions`;
- optional model, reasoning, sandbox, MCP, and skill configuration.

dadaia projects roles such as `project-manager`, `project-auditor`,
`ai-engineer`, `software-engineer`, `qa-engineer`, `security-reviewer`, and
`code-reviewer` into `.codex/agents/*.toml`.

The file makes the role available. It does not by itself make every user prompt
enter that role.

## Subagent Workflows

Subagents help with context control. The main thread keeps requirements,
decisions, and synthesis; subagents handle bounded exploration, verification, or
specialist analysis and return summaries.

Good subagent work is:

- explicit;
- bounded;
- independent enough to run in parallel;
- clear about write scopes;
- clear about the output contract.

Parallel read-heavy work is safest. Parallel write-heavy work needs disjoint path
ownership and careful coordination.

## dadaia Dispatcher Mapping

dadaia's desired architecture is:

| Role | Codex Reality |
|---|---|
| `project-manager` receives demand and dispatches work | Must be explicitly invoked or spawned; not automatic for every prompt |
| `project-auditor` coordinates drift audits | Must be explicitly invoked for audit work |
| Worker agents perform bounded tasks | Spawned only when the active session delegates |
| Workflow markdown describes stage order | Reference/context unless a runtime dispatcher actually executes it |
| Hooks enforce local mechanics | Can block writes or refresh state in interactive sessions; on 0.139.0 hooks never fire under headless `codex exec` |

This is the central Claude-to-Codex drift: Claude Code may feel more naturally
agentic around the existing workflow conventions, while Codex requires explicit
delegation language and custom-agent spawning.

## Prompt Pattern

Weak:

```text
Implement this release.
```

Better:

```text
Act as project-manager for this dadaia release. Resolve the active context, load
SPEC/PLAN/TASKS, then explicitly delegate: spawn qa-engineer for acceptance risk,
security-reviewer for threat review, and software-engineer for the implementation
task. Wait for reports before marking anything complete.
```

For a direct Codex session, the explicit spawn/delegate wording is not ceremony; it
is the trigger that allows subagent workflows to happen.

## Honest System Design

dadaia should not promise that Codex workflow files enforce the whole lifecycle.
They should be presented as dispatch references. Enforcement belongs to hooks,
Rules, tests, and the SDD gate. Delegation belongs to explicit Codex subagent
requests or a real workflow executor if one is later built.

That honesty is what makes Codex usable: the operator can trust that the system is
describing actual runtime behavior, not aspirational architecture.
