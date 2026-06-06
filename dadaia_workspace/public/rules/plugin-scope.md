---
name: plugin-scope
description: Names the three plugin agents (frontend-engineer, design-specialist, devops-engineer) and the [PLUGIN REQUIRED] response core agents give when handed a plugin-domain task.
always_on: true
---

# plugin-scope

This rule is always active in this workspace.

Three agents are **plugins**, not part of the 9-agent core roster (constitution §14).
They ship as thin stubs in the core install and carry no behavior until their plugin is
installed:

| Plugin agent | Domain | Install command |
|---|---|---|
| `frontend-engineer` | Browser HTML/CSS/JS/TS/React surfaces | `dadaia plugin install frontend-design` |
| `design-specialist` | UX/UI, design specs, visual review | `dadaia plugin install frontend-design` |
| `devops-engineer` | CI/CD, GitHub Actions, gitflow, deploy | `dadaia plugin install devops` |

Dispatching any of these requires the corresponding plugin to be installed in the
workspace. When a **core** agent receives a task that falls in a plugin domain, it does
not attempt the work — it responds:

```
[PLUGIN REQUIRED] <agent-name> plugin is not installed in this workspace.
Install with: dadaia plugin install <name>
```

(`<name>` is `frontend-design` for frontend-engineer / design-specialist, `devops` for
devops-engineer.)
