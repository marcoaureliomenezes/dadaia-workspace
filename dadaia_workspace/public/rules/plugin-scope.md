---
name: plugin-scope
description: Names the three plugin agents (frontend-engineer, design-specialist, devops-engineer) and the [PLUGIN REQUIRED] response core agents give when handed a plugin-domain task whose pack is not installed in this workspace.
always_on: true
---

# plugin-scope

This rule is always active in this workspace.

Three agents are **plugins**, not part of the 9-agent core roster (constitution §14). They
ship as thin stubs in the core install and are enabled per workspace by installing their
plugin pack. The packs are **distributed in-package** and installed with
`dadaia plugin install <pack>`:

| Plugin agent | Domain | Plugin pack | Enable with |
|---|---|---|---|
| `frontend-engineer` | Browser HTML/CSS/JS/TS/React surfaces | `frontend-design` | `dadaia plugin install frontend-design` |
| `design-specialist` | UX/UI, design specs, visual review | `frontend-design` | `dadaia plugin install frontend-design` |
| `devops-engineer` | CI/CD, GitHub Actions, gitflow, deploy | `devops` | `dadaia plugin install devops` |

Until a pack is installed in **this** workspace, its agents remain stubs and carry no
behavior. Installing a pack (`dadaia plugin install <pack>`) records it in the
`.dadaia/states/installed_plugins.json` ledger and projects the pack's real agent bodies +
skills over the stubs — the now-real plugin agent handles the work directly.

When a **core** agent receives a task that falls in a plugin domain whose pack is **not
installed** here, it does not attempt the work — it responds:

```
[PLUGIN REQUIRED] <agent-name> is a plugin agent and its pack is not installed in this
workspace. Enable it with `dadaia plugin install <pack>`, or route this task to the
operator.
```

Once the pack is installed, that same domain task routes to the now-real plugin agent
rather than the operator.

## Notes

- **Feature origin.** The `dadaia plugin install` command and the in-package
  `frontend-design` / `devops` packs ship in **v0.1.60** (consuming the backlog entry
  `plugin-packs-and-install-command`). This rule is the install-gated wording for that
  capability.
- **Retired deviation class.** Before packs were installable, a release that needed a plugin
  agent recorded a plugin-scope deviation (e.g. the v0.1.59 `panel-ux-overhaul` deviation).
  That deviation class is **retired going forward**: because a pack is now installable with
  `dadaia plugin install <pack>`, future releases enable the real agent instead of recording
  a deviation. The past deviation stands as recorded.
