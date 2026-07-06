---
name: tier-taxonomy-rename
status: candidate
opened: 2026-07-04
owner: project-manager (curates)
source: v0.1.60 closure (Ruling 17 — FR6 documents + machine-guards but does not rename)
intents:
  - subject: { kind: code, ref: "tests/contract/test_agent_tier_taxonomy.py#test_core_agents_carry_numeric_tier_and_pinned_model_effort" }
    change: "rename the numeric frontmatter `tier:` key to `dispatch_band:` across all agent bodies + the parsers/renderers that read it, and update the taxonomy contract test so the two 'tier' axes no longer collide on the word"
---

# BACKLOG — Tier-taxonomy source rename (`tier:` → `dispatch_band:`)

**Priority:** LOW. Agent frontmatter carries two unrelated `tier`-named concepts: the numeric
`tier: 1/2/3` (Layer-1 dispatch band) and the registry `Tier` (model-cost class resolved from
`model:`). v0.1.60 FR6 (Ruling 17) **documented** the two axes and added the mandatory
`tests/contract/test_agent_tier_taxonomy.py` machine-guard, but explicitly did **not** rename
the frontmatter key (renaming all 9 core + 3 plugin agents is churn/risk for a mandate-tail
release).

Do the source-level rename `tier:` → `dispatch_band:` across every agent body plus the parsers
and renderers that read it (e.g. the Codex frontmatter parser) and update the contract test, so
the collision is resolved at source rather than only documented. Anchored at the taxonomy
contract test `tests/contract/test_agent_tier_taxonomy.py#test_core_agents_carry_numeric_tier_and_pinned_model_effort`.
