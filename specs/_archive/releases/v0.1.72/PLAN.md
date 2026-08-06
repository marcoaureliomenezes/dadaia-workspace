# PLAN: Release v0.1.72

**Status:** Aprovado
**Release ID:** v0.1.72
**Owner:** product-engineer

## Approach

Six root-cause fixes, each RED-first with real-consumer evidence, converging on one
architectural correction: every gate has a legal repair path, and the gate the verbs
report is the gate the verbs enforce.

| FR | Surface | Change |
|----|---------|--------|
| FR1 | `features/migrate/agent_tier_frontmatter.py` (new), `registry.py`, `core/specs_version.py` | line-surgery migration step v2→3; canonical version 3; doctor golden regen (msg "canonical 2"→"3") |
| FR2 | `features/spec_context/lease.py`, `container.py`, `cli/commands/context.py` | `holder_in_lineage` + `adopt_if_own_lineage` (CAS); preflight probe lineage discrimination; bind adopts eagerly |
| FR3 | `features/lifecycle/service.py` | `_check_hygiene` blocks on unprotected remainder only |
| FR4 | `cli/commands/context.py` | live `current_branch` for ALIVE repos + `stored_branch` |
| FR5 | `cli/commands/lifecycle.py`, `container.py` | `_pipeline_runtime_factory` seam; `build_lifecycle_pipeline(runtime_factory=…)` |
| FR6 | `cli/commands/lifecycle.py` | `_enforce_preflight_gate` in pipeline + implement-review; `--skip-preflight`; help-text truth fix |

## Pinned substrate versions (bound at approval)
None — no dependency changes.

## Test strategy
- Unit RED-first per FR (real sample-consumer atom fixture for FR1; the reporter's
  exact lock topology for FR2; the reporter's 12/12-protected counters for FR3).
- Executed-path E2E (`test_pipeline_end_to_end_throwaway_context.py`) extended:
  Drive 0 preflight refusal (both verbs, no run created) → Drive 1 fake pipeline
  COMPLETES (inverting the v0.1.68 assertion that codified the bug) → Drive 2
  implement-review completes + handoffs doctor coherent.
- `specs upgrade` driven via the REAL CLI against a copy of the real consumer tree.
- Mutation-sanity per fix; full suite green.
- Remote acceptance: full chain replayed on the operator's remote against live
  sample-consumer v0.2.0.
