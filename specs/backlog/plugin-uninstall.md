---
name: plugin-uninstall
status: candidate
opened: 2026-07-04
owner: project-manager (curates)
source: v0.1.60 closure (Ruling ADR-2 — additive-only install this release)
intents:
  - subject: { kind: code, ref: "dadaia_workspace/infrastructure/public_assets.py#FileSystemPublicAssetManager" }
    change: "add the inverse of install_plugin: remove a pack from installed_plugins.json and restore the projected core stub over the pack agent body (profile-scoped, idempotent, doctor-clean)"
---

# BACKLOG — `dadaia plugin uninstall`

**Priority:** MEDIUM. v0.1.60's `dadaia plugin install` is **additive-only** (Ruling ADR-2,
mirroring the v0.1.58 no-harness-removal precedent): there is no way to disable a pack once
installed except re-running core `public install` after hand-editing the ledger.

Add `dadaia plugin uninstall <pack>` (the inverse of `install_plugin`): drop the pack from
`.dadaia/states/installed_plugins.json` and re-project the core stub over the pack agent body
(profile-scoped, idempotent, `plugin doctor`-clean afterwards). Decide the semantics for a
pack whose files were hand-edited (restore vs `[foreign]`). Anchored at
`infrastructure/public_assets.py#install_plugin`.
