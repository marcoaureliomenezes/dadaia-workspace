---
name: plugin-pack-content-libraries
status: delivered
delivered_in: v0.1.63
opened: 2026-07-04
owner: project-manager (curates)
source: v0.1.60 closure (Ruling ADR-5 / 12 minimal-viable-content ceiling)
intents:
  - subject: { kind: code, ref: "dadaia_workspace/core/models/plugin_pack.py#PluginPack" }
    change: "author the full frontend-design + devops skill corpora beyond the two enumerated minimal-viable skills, populating each PluginPack's skills set with a complete, reviewable library"
---

# BACKLOG — Plugin pack content libraries (full skill corpora)

**Priority:** MEDIUM. v0.1.60 shipped the plugin-install **machinery** + minimal-viable content
under Ruling ADR-5: 3 real agent bodies + exactly ONE skill per pack
(`browser-frontend-implementation` for `frontend-design`, `github-actions-cicd` for `devops`)
+ zero new rules. Full skill libraries (comprehensive React/CSS/design-system and
GitHub-Actions/gitflow/deploy corpora) were deferred as an unbounded authoring surface unfit
for a mandate-tail release.

Grow each pack's skill set to a complete, reviewable library, authored by `ai-engineer` under
the public-privacy law (generic content only), each skill referenced by the pack agents and
resolvable by `check_agent_skill_refs`. Anchored at `core/models/plugin_pack.py#PluginPack`
(the model whose `skills` tuple the packs populate).
