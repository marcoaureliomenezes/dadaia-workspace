---
slug: agentic-entities
title: agentic-entities
tldr: One registry names three personas, five deterministic behaviors and two abstract rules; a behavior map assigns each shipped skill and scoped law to an owner.
summary: The harness-neutral entity registry, its projected implementations, the universal authored surface and the structural ownership and citation checks that keep agentic law complete.
tags: [agents, entities, derivation, governance]
sources:
  - dadaia_workspace/public/entities/**
  - dadaia_workspace/public/schemas/behavior-map-v1.schema.json
  - dadaia_workspace/public/data/CONTEXT-MAP.md
  - dadaia_workspace/public/skills/**
  - dadaia_workspace/infrastructure/entity_doctor.py
---

## Registry

- `dadaia_workspace/public/entities/registry.json` is the harness-neutral inventory of three personas, five deterministic behaviors, two abstract rules and the universal surface.
- Persona source files and registry personas form a bijection. Wired hook entrypoints map to registered behaviors, and projected core rules map to registered rules.
- The five behaviors are root-whitelist, SDD gate, context-memory injection, git chokepoints and workspace-level tool-cache placement. Root-whitelist and SDD gate share the pre-tool entrypoint; context injection covers session start and prompt submission; git chokepoints are repository hooks; harnesses with an environment surface point supported tool caches at `.dadaia/tmp/` ([[sdd-gate-v3]]).
- Every BLOCK emits one fix line. Hook wrappers fail open when the workspace venv is absent and tell the operator how to initialize the workspace.
- Operator-created entities are outside derivation; the registry governs what the library ships.

## Universal surface

- The root map, scoped `AGENTS.md` sources, `.agents/skills/dd-*` and `.agents/agents/dd-*.md` are authored once and consumed natively or through harness projections.
- Every skill that operates in a governed area opens that area's scoped law as its first procedural step.
- `CONTEXT-MAP.md` records each surface, purpose and load trigger. Size is a review signal; only the behavior map's skill ceiling is mechanical.

## Structural behavior map

- `behavior-map.json` rows contain `section`, optional `anchor`, `skill` and `scoped_agents_md`. It carries no content hashes, recorder or date fields.
- Every shipped skill and scoped law source appears in exactly one row; every mapped law section has an owner. Declared overlaps are explicit, standalone skills are enumerated, and skills disabled for model invocation appear in no persona grant.
- `tests/infrastructure/test_entity_doctor.py` validates the map schema, member coverage, unique mapping, section ownership, overlap declarations, skill ceiling, persona grants, path and CLI citations, body pointers and projected-law references.
- `dadaia public doctor` separately checks installed entity derivation and reports projection drift ([[public-asset-distribution]]).

## Dependencies

[[agent-orchestration]], [[public-asset-distribution]], [[sdd-gate-v3]], [[workspace-doctor]], [[ARCHITECTURE]], [[QUALITY]].
