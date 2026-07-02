---
name: plugin-packs-and-install-command
status: candidate
opened: 2026-07-02
owner: project-manager (curates)
source: plugin-scope rule (tracking pointer) + candidates.md index entry with no file (drift, fixed 2026-07-02)
intents:
  - subject: { kind: catalog, ref: "public-asset-distribution" }
    change: "ship a real `dadaia plugin install <pack>` CLI command and distribute the frontend-design pack (frontend-engineer + design-specialist) and the devops pack (devops-engineer) so the three stub plugin agents carry real behavior (agents + skills + rules projections)"
---

# BACKLOG — Plugin packs distribution + `dadaia plugin install`

**Priority:** MEDIUM. The `plugin-scope` rule and the three stub agents
(`frontend-engineer`, `design-specialist`, `devops-engineer`) both point at this
entry as the tracking item, and the `panel-ux-overhaul` plugin-scope deviation is
authorized only because no install command exists yet. Until this ships, plugin
agents remain stubs and plugin-domain work routes to the operator.

Note: this file was created 2026-07-02 to repair index drift — the entry existed
only as a `candidates.md` line while an always-active rule referenced it by name.
