---
name: harness-skill-scope
description: Restricts ai-harness-* and ai-context-engineering skills to ai-engineer only.
always_on: true
---

# harness-skill-scope

This rule is always active.

The skills `ai-harness-claude-code`, `ai-harness-codex`, and `ai-context-engineering` are restricted to `ai-engineer`. No other agent may invoke them.

`harness-primitives` is the approved all-agent literacy skill and is NOT restricted by this rule.

If you are not `ai-engineer` and receive a task that requires invoking an `ai-harness-*` or `ai-context-engineering` skill, respond:

```
[SCOPE ERROR] harness-skill-scope: these skills are restricted to ai-engineer.
Use harness-primitives for general harness literacy.
Dispatch ai-engineer for deep harness questions.
```
