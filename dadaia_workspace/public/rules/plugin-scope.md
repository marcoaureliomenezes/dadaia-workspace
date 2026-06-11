---
name: plugin-scope
description: Names the three plugin agents (frontend-engineer, design-specialist, devops-engineer) and the [PLUGIN REQUIRED] response core agents give when handed a plugin-domain task.
always_on: true
---

# plugin-scope

This rule is always active in this workspace.

Three agents are **plugins**, not part of the 9-agent core roster (constitution §14).
They ship as thin stubs in the core install and carry no behavior until their plugin
pack is available:

| Plugin agent | Domain | Plugin pack |
|---|---|---|
| `frontend-engineer` | Browser HTML/CSS/JS/TS/React surfaces | `frontend-design` (not yet distributed) |
| `design-specialist` | UX/UI, design specs, visual review | `frontend-design` (not yet distributed) |
| `devops-engineer` | CI/CD, GitHub Actions, gitflow, deploy | `devops` (not yet distributed) |

**Plugin packs are not yet distributed** and there is no install command — the feature
is tracked by the backlog entry `plugin-packs-and-install-command`. Until it ships,
plugin agents cannot be enabled. When a **core** agent receives a task that falls in a
plugin domain, it does not attempt the work — it responds:

```
[PLUGIN REQUIRED] <agent-name> is a plugin agent and its plugin pack is not yet
distributed (no install command exists). Route this task to the operator.
Tracking: backlog entry `plugin-packs-and-install-command`.
```

The operator decides how the work proceeds (e.g. authoring it directly, or deferring
until the plugin packs ship).
