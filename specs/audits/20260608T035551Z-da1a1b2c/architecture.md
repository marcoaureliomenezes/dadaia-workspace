---
audit_id: 20260608T035551Z-da1a1b2c
dimension: architecture
score: 7
drift_items: 3
---

# Architecture Audit

## Summary

The three-ring architecture (cli → features → infrastructure) with `core/` for pure models and `container.py` for DI wiring is well-executed overall. Layering holds in the vast majority of feature packages. Three structural problems exist: cross-feature concrete imports in the panel, a god module in infrastructure, and a stray `panel/views/api.py` with direct concrete imports in the views layer.

---

## Finding A-01 — Panel service imports concrete feature types (MEDIUM)

**Memory claim (`architecture.md`):** "Features are isolated service units. They communicate via interfaces/protocols, never by importing each other's concrete classes."

**Actual code:**

```python
# dadaia_workspace/features/panel/service.py:45-48
from dadaia_workspace.features.agents.reader import AgentDTO, read_canonical_agents
from dadaia_workspace.features.server_registry.service import ServerRegistryService
from dadaia_workspace.features.spec_context.service import SpecContextService
from dadaia_workspace.features.workflows.service import WorkflowsService, WorkflowSummaryDTO
```

**Evidence:** `dadaia_workspace/features/panel/service.py:45-48`

**Assessment:** The constructor signature does use dependency injection — each of these is received as a constructor argument, which is positive. The violation is at the import level: `panel` now has a compile-time hard dependency on the concrete types from three sibling feature packages. If `SpecContextService` is refactored or renamed, `panel/service.py` breaks at import time.

**Fix direction:** Define protocols in `core/protocols/` (e.g. `IContextProvider`, `IServerRegistryProvider`, `IWorkflowProvider`). Wire the concrete implementations in `container.py`. Type-annotate `panel/service.py` constructor arguments against those protocols, not the concrete classes.

---

## Finding A-02 — `panel/views/api.py` imports concrete types from four feature packages (MEDIUM)

**Actual code:**

```python
# dadaia_workspace/features/panel/views/api.py:93-101
from dadaia_workspace.features.agents.reader import read_canonical_agents, AgentDTO
from dadaia_workspace.features.reports_retention.service import ReportsRetentionService
from dadaia_workspace.features.telemetry.aggregator.models import TelemetrySnapshot
from dadaia_workspace.features.telemetry.aggregator.runtimes import RuntimeMetrics
```

**Evidence:** `dadaia_workspace/features/panel/views/api.py:93-101`

**Assessment:** Same layering violation as A-01, but in the views layer. The views layer should only see what the `PanelService` (already DI-wired) exposes.

**Fix direction:** Move the telemetry and reports-retention concerns into `PanelService` or a dedicated `PanelCompositeService`, and inject the result through the existing DI container path. The views layer should only import DTOs, not service classes.

---

## Finding A-03 — `infrastructure/public_assets.py` is a 2446-line god module (MEDIUM)

**Evidence:** `dadaia_workspace/infrastructure/public_assets.py` — file line count confirmed by `wc -l`.

**Contents mixed in a single module:**
- Asset staging and SHA256 hashing
- Asset installation (install + force-overwrite logic)
- Doctor checks (7+ `_check_*` functions)
- Privacy denylist loading and pattern scanning
- Codex config generation (`_render_codex_config`)
- OpenCode `opencode.json` generation
- AGENTS.md / CLAUDE.md workspace guardrail pair installation
- Agent frontmatter TOML character escaping
- Consumer-repo discovery
- `source_root_hygiene_guard` sub-check

**Assessment:** Any single change anywhere in the public-asset pipeline requires navigating nearly 2500 lines. High-blast-radius changes are not isolated to a logical concern. The module already has comments like "# ---- staging ----", "# ---- installation ----", "# ---- doctor ----" that signal the internal structure exists mentally but has not been extracted.

**Fix direction:** Multi-release decomposition:
1. `infrastructure/runtime_transforms/codex_assets.py` — Codex config generation (already has a `runtime_transforms/` sub-package to absorb it).
2. `infrastructure/workspace_guardrail.py` — AGENTS.md/CLAUDE.md pair logic.
3. `infrastructure/privacy_check.py` — denylist + scan.
4. Residual core staging/install/doctor stays in `public_assets.py` (now <600 lines).

This is a two-release backlog item, not a hotfix.

---

## Positive Observations

- `core/` package is genuinely pure: only models, protocols, exceptions — no I/O, no framework calls.
- `container.py` correctly wires every non-panel feature via protocols.
- `cli/` commands are thin: they validate input, call services, format output — no business logic.
- `infrastructure/` sub-packages (`git_subprocess.py`, `os_process.py`, `runtime_transforms/`) are correctly isolated.
- The three-ring law holds for 13 of the 15 feature packages. Only `panel/` systematically violates it.
