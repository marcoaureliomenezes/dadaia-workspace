---
name: features-import-infrastructure-direct-debt
status: candidate
intents:
  - subject: { kind: code, ref: "dadaia_workspace/features/workflows/service.py#WorkflowsService" }
    change: "stop importing infrastructure.markdown_workflow_store directly; depend on a core/protocols port injected via container.py; remove its ignore_imports entry"
  - subject: { kind: code, ref: "dadaia_workspace/features/agents/reader.py#read_canonical_agents" }
    change: "stop importing infrastructure.markdown_agent_store directly; depend on a core/protocols port injected via container.py; remove its ignore_imports entry"
  - subject: { kind: code, ref: "dadaia_workspace/features/panel/service.py#PanelService" }
    change: "stop importing infrastructure.workflow_launcher_adapter directly; depend on an injected port; remove its ignore_imports entry"
---

# BACKLOG — features/ imports infrastructure/ directly (layering debt)

**Reported:** 2026-06-09 (discovered during 0.1.8 T-018-07 import-linter introduction).
**Severity:** LOW (architectural hygiene; no runtime defect).
**Owner:** project-manager (curates) → product-engineer (release definition when picked).
**Status:** CANDIDATE — not picked.

## Problem

The 0.1.8 import-linter contract `features must not import infrastructure directly` is KEPT
only because three pre-existing direct imports are listed in `setup.cfg`'s `ignore_imports`:

- `dadaia_workspace.features.workflows.service` → `infrastructure.markdown_workflow_store` (module top)
- `dadaia_workspace.features.agents.reader` → `infrastructure.markdown_agent_store` (module top)
- `dadaia_workspace.features.panel.service` → `infrastructure.workflow_launcher_adapter` (function-level)

These predate the cross-platform release and were out of its scope. They violate the layering
law (features depend on `core/protocols`, container.py injects the concrete adapter).

## Scope when picked

Introduce `core/protocols` ports for the markdown stores + workflow launcher (if not already
present), inject the concrete adapters via `container.py`, and remove the three `ignore_imports`
entries from `setup.cfg` so the contract holds with zero exceptions for non-platform code.

## Note

The platform lock/telemetry lazy-adapter `ignore_imports` (the ADR-1 transitional defaults) are
a SEPARATE follow-up tracked within the cross-platform work (full container DI of the lock/perm
adapters), not part of this item.
