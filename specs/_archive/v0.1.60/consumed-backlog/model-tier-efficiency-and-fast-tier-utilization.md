---
name: model-tier-efficiency-and-fast-tier-utilization
status: candidate
intents:
  - subject: { kind: code, ref: "dadaia_workspace/core/model_registry.py#Tier" }
    change: "assign mechanical Layer-1 sub-task classes (catalog regen, report validation, formatting, handoff emission) to the currently-unused `fast` tier"
  - subject: { kind: catalog, ref: "agent-orchestration" }
    change: "tier the 9-core personas off uniform claude-opus-4-8 so mechanical work runs on a cheap fast tier (persona frontmatter or dispatch-time tiering)"
---

# BACKLOG — Layer-1 model-tier efficiency + fast-tier utilization (P2)

**ID:** FEAT-MODEL-TIER-EFFICIENCY-01
**Reported:** 2026-06-11 (full-platform review).
**Owner:** project-manager (curates) → ai-engineer (execution when picked).
**Status:** OPEN — candidate.

> **Layer correction (2026-06-26):** v0.1.24's LAW-2 discrete per-harness GPT model catalog
> is the **Layer-2 worker** model axis (the model each Python lifecycle step drives a pi/codex
> worker on). **This entry is the Layer-1 axis** — the model assigned to the entry-harness
> custom-agent personas (`{claude, codex, pi}`). The two axes are independent; this item does
> not touch the Layer-2 catalog.

## Problem

1. **The `fast` Layer-1 tier has zero agent assignments.** All 9 core personas resolve to
   `claude-opus-4-8` (and its registry-mapped GPT equivalent). Mechanical work — catalog
   regeneration, report validation, formatting passes, handoff emission — runs on the top
   tier instead of a cheap fast tier.
2. **No recurring efficiency-audit trigger.** The ai-engineer persona defines a
   prompt-efficiency audit rubric (inventory, cost-per-output, redundancy, tier-move
   recommendations) but it fires only on demand, so persona/skill token bloat and tier
   misassignments accrue silently.

## Direction (to be grilled when picked)

- Identify the mechanical sub-task classes safe for a Layer-1 fast tier and assign them
  (persona frontmatter, or dispatch-time tiering by the coordinator).
- Add a recurring efficiency-audit trigger — candidate mechanisms: a CLOSURE-phase
  checkpoint item, or a panel/doctor staleness indicator on `last_efficiency_audit`.

## Acceptance seed

- At least one production Layer-1 workflow demonstrably runs on the fast tier with equal
  output quality.
- An efficiency-audit report exists with a dated cadence contract.
