# Codex for dadaia-workspace

This course teaches Codex as a real engineering harness, not as a Claude Code
clone. The goal is to make the Codex runtime predictable inside
dadaia-workspace: what Codex reads, what it enforces, what it only treats as
guidance, and where explicit operator or dispatcher action is still required.

The course is based on the official OpenAI Codex documentation refreshed on
2026-06-11 and translated into dadaia-workspace operating decisions.

## Learning Outcomes

After this module, you should be able to:

- Place durable instructions in the right `AGENTS.md` layer.
- Decide when to use a skill, plugin, hook, Rule, MCP server, or custom agent.
- Explain why Codex does not automatically execute dadaia workflow markdown.
- Configure Codex custom agents without crossing trust or credential boundaries.
- Audit a Codex projection for common Claude-to-Codex drift.
- Operate the project-manager/project-auditor dispatcher model honestly in Codex.

## Lessons

1. `01_codex_mental_model.md` - surfaces, execution model, and customization map.
2. `02_agents_md_and_scoped_instructions.md` - how Codex discovers scoped guidance.
3. `03_skills_plugins_and_mcp.md` - reusable workflows and distribution.
4. `04_hooks_rules_and_config.md` - lifecycle hooks, command policy, and config trust.
5. `05_subagents_and_dadaia_workflows.md` - explicit delegation and dadaia workflow mapping.

Use `EXAMPLE.md` for a worked mapping and `EXERCISES.md` for review drills.
