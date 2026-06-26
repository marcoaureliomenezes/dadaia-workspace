---
release: none
phase: ARCHIVED
---

No active release.

Last shipped: **v0.1.27 — wire the consumed_backlog PRODUCER at release-definition**
(CLOSED + Aprovado; closure at `specs/_archive/releases/v0.1.27/CLOSURE.md` once the
coordinator runs `git mv specs/releases/v0.1.27 specs/_archive/releases/v0.1.27`). v0.1.27
resolved the v0.1.26 R2 producer residual: removal-on-release now fires end-to-end
(producer at `dadaia lifecycle release define` via the `**Consumes:**` SPEC line, consumer
at `dadaia lifecycle close`).

Next step: **workflow-model-governance-panel-control-plane**.
