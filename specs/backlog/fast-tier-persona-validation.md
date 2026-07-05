---
name: fast-tier-persona-validation
status: candidate
opened: 2026-07-04
owner: project-manager (curates)
source: v0.1.60 closure (Ruling ADR-6 — fast/haiku reasoning-persona downgrade deferred)
intents:
  - subject: { kind: code, ref: "dadaia_workspace/core/model_registry.py#Tier" }
    change: "assign at least one mechanical Layer-1 lane to the currently-unused registry `fast` (haiku) tier and validate equal output quality with a live operator, so the fast tier stops being defined-but-unassigned"
---

# BACKLOG — Fast-tier persona validation (P2)

**Priority:** MEDIUM. v0.1.60 shipped the demonstrable off-opus Layer-1 assignment via the 3
plugin agents on the `plugin`/sonnet tier, but **deferred** moving any of the 9 reasoning-heavy
core personas to the `fast` (haiku) tier (Ruling ADR-6): the deep tier (`claude-fable-5`) is
region-locked, forcing all 9 core to opus, and there was no live operator to validate the
acceptance seed's "equal output quality" of a downgraded SDD-role persona.

Identify a genuinely mechanical Layer-1 lane safe for the `fast` (haiku) registry tier and
assign it, validated for equal output quality **with the operator live** — so the `fast` tier
(defined and cost-priced in the registry but assigned by no agent) becomes a real production
assignment. Anchored at `core/model_registry.py#Tier`.
