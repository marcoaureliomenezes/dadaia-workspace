# Exercises

## 1. Pick the Primitive

For each need, choose the Codex primitive.

1. "Always run the SDD gate before file writes."
2. "Teach agents how to audit Codex projections."
3. "Prompt before `git push`."
4. "Make repo-specific test commands persistent."
5. "Let Codex read current OpenAI docs."
6. "Run security and QA reviews in parallel."

Expected answers:

1. Hook.
2. Skill.
3. Codex Rule.
4. `AGENTS.md`.
5. MCP.
6. Explicit subagent delegation.

## 2. Scope the Instruction

Where should each instruction live?

1. "Do not create `.dadaia/` inside any repo."
2. "Tests in this package use a fake clock fixture."
3. "Use this seven-step release closure checklist."
4. "For this one task, do not edit CSS."

Expected answers:

1. Workspace or repo `AGENTS.md`.
2. Nested package `AGENTS.md` or test docs.
3. Skill.
4. Current prompt or task.

## 3. Find the Drift

You inspect a Codex projection and find:

```text
.codex/agents/project-auditor.toml
.codex/skills/dadaia-cli/SKILL.md
```

The operator says: "Why did the audit not fan out automatically?"

Answer: projected agents and skills make roles and operating guidance available; they
do not trigger execution. Explicitly ask Codex to spawn/delegate `project-auditor`, or
have the operator dispatch it, to start the audit stage of the SDD flow.

## 4. Review a Rule

Which file shape is correct for current documented Codex command policy?

```python
def command_allowed(cmd):
    return True
```

or:

```python
prefix_rule(
    pattern=["git", "push"],
    decision="prompt",
    justification="Publishing requires operator approval.",
)
```

Expected answer: `prefix_rule(...)`.

## 5. Design a Dispatcher Prompt

Write a prompt that asks Codex to use `project-manager` and three reviewers
explicitly. It must name the agents, say whether to wait, and define the expected
summary.
