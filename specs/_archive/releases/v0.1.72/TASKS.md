# TASKS: Release v0.1.72

**Status:** Aprovado
**Release ID:** v0.1.72
**Owner:** product-engineer

> RED-first, executed-path, real-consumer fixtures. Acceptance for the release includes
> the full-chain remote replay (T-7.1).

### T-1.1 — FR1 agent-tier-frontmatter migration `[x]`
- **Write set:** `dadaia_workspace/features/migrate/agent_tier_frontmatter.py`,
  `dadaia_workspace/features/migrate/registry.py`, `dadaia_workspace/core/specs_version.py`,
  `tests/unit/features/migrate/test_agent_tier_frontmatter.py`,
  `tests/fixtures/memory-agent-tier/s3-delivery.md`,
  `tests/unit/features/specs/_golden/` (doctor golden: canonical 2→3)
- Done: real consumer tree upgrades v1→3, 8 atoms healed, doctor clean.

```
[x] T-1.1
```

### T-2.1 — FR2 lease lineage adoption `[x]`
- **Write set:** `dadaia_workspace/features/spec_context/lease.py`,
  `dadaia_workspace/container.py`, `dadaia_workspace/cli/commands/context.py`,
  `tests/unit/features/spec_context/test_lease_lineage_adoption.py`,
  `tests/integration/test_preflight_lease_lineage.py`
- Done: own-lineage holder adopted at bind + never foreign in preflight; live
  non-lineage holder still foreign.

```
[x] T-2.1
```

### T-3.1 — FR3 hygiene unprotected-remainder predicate `[x]`
- **Write set:** `dadaia_workspace/features/lifecycle/service.py`,
  `tests/unit/features/lifecycle/test_preflight_service.py`
- Done: all-protected passes; one unprotected still blocks.

```
[x] T-3.1
```

### T-4.1 — FR4 live current_branch in context show `[x]`
- **Write set:** `dadaia_workspace/cli/commands/context.py`,
  `tests/integration/cli/test_context_show_live_branch.py`
- Done: live branch reported for ALIVE repo; stored_branch exposed; absent-repo fallback.

```
[x] T-4.1
```

### T-5.1 — FR5 driving fake for pipeline `[x]`
- **Write set:** `dadaia_workspace/cli/commands/lifecycle.py`,
  `dadaia_workspace/container.py`,
  `tests/e2e/features/test_pipeline_end_to_end_throwaway_context.py`
- Done: fake pipeline COMPLETES in the E2E (assertion inverted from the v0.1.68 BLOCKED).

```
[x] T-5.1
```

### T-6.1 — FR6 preflight enforcement + --skip-preflight `[x]`
- **Write set:** `dadaia_workspace/cli/commands/lifecycle.py`,
  `tests/e2e/features/test_pipeline_end_to_end_throwaway_context.py`
- Done: unbound ⇒ both verbs refuse (exit 3, no run dir); flag overrides visibly;
  --json stays machine-pure; stale --write-scope help corrected.

```
[x] T-6.1
```

### T-7.1 — Full-chain remote replay acceptance `[ ]`
- **Write set:** none (acceptance evidence in CLOSURE)
- Done: on the operator's remote against live sample-consumer v0.2.0 — upgrade heals
  memory → bind adopts lease → preflight PASSES → fake pipeline completes → blocked
  preflight refuses verbs.

```
[x] T-7.1
```

## Task summary
| Task | FR | Status |
|------|----|--------|
| T-1.1..T-6.1 | FR1–FR6 | done |
| T-7.1 | acceptance | reserved |
