---
name: plugin-scope
description: Enforces that the frontend-design plugin is restricted to frontend-engineer and design-specialist only.
always_on: true
---

# plugin-scope

This rule is always active in this workspace.

The `frontend-design` plugin is restricted to `frontend-engineer` and `design-specialist`. No other agent may invoke its skills or tools.

If you are not one of those agents and receive a task involving `frontend-design`, respond:

```
[PLUGIN SCOPE ERROR] frontend-design plugin is restricted to frontend-engineer + design-specialist. Dispatch the correct agent.
```
