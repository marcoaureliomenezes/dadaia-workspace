---
name: fast-tier-persona-validation
status: rejected
rejected_in: v0.1.64
reason: "premise-dead post-2026-07-06 retier — the off-uniform cost lever already ships operator-live (5x fable-5 with effort bands + 4x opus + 3x sonnet plugin); no Layer-1 lane in the 12-agent roster is honestly mechanical; the fast tier stays registry-defined for historical haiku telemetry pricing. PM-ratified per v0.1.64 SPEC §8 (operator present, override not exercised); an operator revival re-dispositions DEFERRED and MUST carry the recorded AC-OPCHECK."
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

---

## Disposition — REJECTED at v0.1.64 (premise-dead; PM-ratified)

Picked into v0.1.64 and dispositioned **`REJECTED — premise-dead post-2026-07-06 retier`**
(SPEC §9 ADR-5 / FR6; no code change). The dossier premise ("all 9 core forced to opus") went
stale at the 2026-07-06 operator retier: 5 core agents run `claude-fable-5` (registry `deep`)
with pinned per-agent `effort` bands and 4 keep opus — the off-uniform cost lever this item
sought already ships operator-live. The v0.1.60 read-fact re-verified: the named "mechanical
sub-task classes" are deterministic CLI calls carrying no model, and Layer-1 has only
whole-persona `model:` assignment. `fast` remains registry-defined for telemetry pricing of
historical haiku events — defined-but-unassigned is an honest state, not a defect.

**Operator checkpoint (SPEC §8 protocol):** the REJECT was surfaced in the definition
handoff's `decisions_required`; the operator was present in-session when the queue definition
and the v0.1.64 implementation were reported and did not exercise the override — the
disposition stands as **PM-ratified**. **Override path (stays open):** an operator revival
re-dispositions this item `DEFERRED`, and the reviving release MUST carry the AC-OPCHECK
recorded in the archived v0.1.64 SPEC §8 (operator-live equal-quality side-by-side checkpoint,
non-self-approvable; ships only behind `equal-quality: yes`).
