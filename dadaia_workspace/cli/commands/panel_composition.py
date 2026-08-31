"""Panel composition — the panel CLI's own wiring (F001, 20260830 audit).

Moved out of ``container.py``: the 20-route views dict, the panel service, the
telemetry boot and the agent-model-policy service have exactly ONE production
consumer (``dadaia panel``), so the single consumer composes them directly
(ADR-0001). Cross-feature composition is legal here — a cli-side composition
module, like the container, sits above the features-no-cross-feature contract.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from dadaia_workspace.container import (
    build_academy_service,
    build_public_service,
    build_server_registry_service,
    build_spec_context_service,
)
from dadaia_workspace.features.agents.reader import FileSystemAgentsProvider
from dadaia_workspace.features.panel.service import PanelService
from dadaia_workspace.features.panel.views.academy import render_academy_lesson
from dadaia_workspace.features.panel.views.agent_policy import (
    render_api_agent_model_policy,
    render_api_agent_model_templates,
    render_post_agent_model_policy_validate,
    render_put_agent_model_policy,
)
from dadaia_workspace.features.panel.views.api_academy import render_api_academy
from dadaia_workspace.features.panel.views.api_agents import (
    render_api_agent_prompt,
    render_api_agent_sessions,
    render_api_agents_canonical,
)
from dadaia_workspace.features.panel.views.api_contexts import render_api_contexts
from dadaia_workspace.features.panel.views.api_health import render_health
from dadaia_workspace.features.panel.views.api_reports import (
    delete_report_file,
    mark_report_important,
    render_api_reports,
    serve_report_file,
    unmark_report_important,
)
from dadaia_workspace.features.panel.views.api_servers import render_api_servers
from dadaia_workspace.features.panel.views.api_sessions import render_api_sessions
from dadaia_workspace.features.panel.views.index import render_index
from dadaia_workspace.features.panel.views.memory import render_memory
from dadaia_workspace.features.panel.views.static import render_static
from dadaia_workspace.features.panel.views.wrapper import render_memory_wrapper
from dadaia_workspace.features.reports.retention import ReportRetentionService
from dadaia_workspace.features.telemetry.aggregator.runtimes import ADAPTER_REGISTRY
from dadaia_workspace.infrastructure.markdown_agent_store import MarkdownAgentStore

if TYPE_CHECKING:
    from dadaia_workspace.features.agents.model_policy import AgentModelPolicyService

logger = logging.getLogger(__name__)


def build_telemetry_service(workspace_root: Path) -> object | None:
    """Best-effort ``TelemetryService`` construction for the panel boot (K8).

    Plain wiring — no nested class, no factory-of-factories. Returns ``None``
    (never raises) when telemetry cannot be wired (root uid, permission/OS/
    SQLite error) so the panel starts regardless; telemetry endpoints degrade
    to 503 when this returns ``None``.
    """
    import sqlite3
    from pathlib import Path as _Path

    from dadaia_workspace.core.exceptions import PlatformSecurityError
    from dadaia_workspace.features.telemetry import pricing as _pricing
    from dadaia_workspace.features.telemetry.aggregator.queries import TelemetryAggregator
    from dadaia_workspace.features.telemetry.reader.adapters import DEFAULT_READERS
    from dadaia_workspace.features.telemetry.service import TelemetryService
    from dadaia_workspace.features.telemetry.store import TelemetryStore

    state_dir = _Path("~/.dadaia/state/telemetry").expanduser()
    db_path = state_dir / "telemetry.sqlite"
    store = TelemetryStore(db_path)

    try:
        state_dir.mkdir(parents=True, exist_ok=True)
        # Materialise + migrate the store once at boot so the per-request
        # read-only factory always has a database to open (mode=ro cannot
        # create a file); this store instance is also what the service ingests
        # into on each refresh.
        store.open_write().migrate()
        store.close()

        spec_context = build_spec_context_service(workspace_root)
        aggregator = TelemetryAggregator(
            connection_factory=store.open_read,
            spec_context_service=spec_context,
            pricing_module=_pricing,
            workspace_root=workspace_root,
        )

        return TelemetryService(
            store,
            DEFAULT_READERS,
            time.monotonic,
            aggregator=aggregator,
            pricing_module=_pricing,
            workspace_root=workspace_root,
            state_dir=state_dir,
            spec_context_service=spec_context,
        )
    except ImportError as exc:
        logger.warning("Telemetry unavailable (missing dependency): %s", exc)
        return None
    except PermissionError as exc:
        logger.warning("Telemetry unavailable (permission denied on telemetry state dir): %s", exc)
        return None
    except PlatformSecurityError as exc:
        # Tier-2: telemetry dir permission restriction failed on this platform.
        # The panel continues without telemetry (503 on telemetry endpoints).
        logger.warning(
            "Telemetry unavailable (platform security error restricting state dir): %s", exc
        )
        return None
    except OSError as exc:
        logger.warning("Telemetry unavailable (OS error initialising telemetry state): %s", exc)
        return None
    except sqlite3.OperationalError as exc:
        logger.warning("Telemetry unavailable (SQLite database error): %s", exc)
        return None


def build_panel_service(
    workspace_root: Path,
    telemetry: object | None = None,
    academy: object | None = None,
) -> PanelService:
    return PanelService(
        registry=build_server_registry_service(workspace_root),
        spec_context=build_spec_context_service(workspace_root),
        workspace_root=workspace_root,
        telemetry=telemetry,
        academy=academy,
        report_retention=ReportRetentionService(workspace_root),
        adapter_registry=dict(ADAPTER_REGISTRY),
        agents_provider=FileSystemAgentsProvider(store_factory=MarkdownAgentStore),
    )


def build_agent_model_policy_service(workspace_root: Path) -> AgentModelPolicyService:
    """Compose the panel-facing L1 agent-model-policy service (v0.1.65 FR8 / T-65-10).

    Injects (D-4 — the features module carries no infrastructure import):

    - the concrete :class:`JsonAgentModelPolicyStore` (typed to the feature's store
      port), whose valid override targets are the 9 core agents;
    - the **re-render callable** — the agents-only ``public install`` path over both
      L1 projections (G-2 Apply semantics; profile-scoped like every install).
    """
    from dadaia_workspace.features.agents.model_policy import AgentModelPolicyService
    from dadaia_workspace.infrastructure.json_agent_model_policy_store import (
        JsonAgentModelPolicyStore,
    )

    def _rerender_agents() -> list[str]:
        return build_public_service().install(workspace_root, target="all", only="agents")

    store = JsonAgentModelPolicyStore(workspace_root)
    return AgentModelPolicyService(store=store, rerender=_rerender_agents)


def build_panel_views(
    workspace_root: Path,
    telemetry: object | None = None,
) -> dict[str, Callable[..., tuple[int, str, bytes]]]:
    """Compose all panel view callables for injection into make_handler_class().

    Returns a dict mapping route names to view callables as required by
    ``features/panel/handler.py::make_handler_class(views)``.

    Parameters
    ----------
    workspace_root:
        Absolute path to the workspace root directory.
    telemetry:
        Optional TelemetryService instance.  When provided, it is injected
        into PanelService so that ``render_api_agents_canonical`` can overlay
        telemetry data on the canonical agent catalog (PR3-08).
    """
    academy = build_academy_service(workspace_root)
    service = build_panel_service(workspace_root, telemetry=telemetry, academy=academy)

    # L1 agent model-governance (v0.1.65 FR8): store + re-render injected via the
    # dedicated factory (D-4 — the feature service never imports infrastructure).
    agent_policy_service = build_agent_model_policy_service(workspace_root)

    return {
        "index": render_index(service),
        "api_panel_status": render_api_servers(service),
        "health": render_health(),
        "api_contexts": render_api_contexts(service),
        "api_academy": render_api_academy(service),
        "academy_lesson": render_academy_lesson(academy),
        "api_reports": render_api_reports(service),
        "reports_serve": serve_report_file(service),
        "api_report_delete": delete_report_file(service),
        "api_report_mark_important": mark_report_important(service),
        "api_report_unmark_important": unmark_report_important(service),
        "api_agents": render_api_agents_canonical(service),
        "api_agent_prompt": render_api_agent_prompt(service),
        "api_agent_sessions": render_api_agent_sessions(service),
        # L1 agent model-governance control plane (v0.1.65 FR8 — T-65-11).
        "api_agent_model_policy": render_api_agent_model_policy(agent_policy_service),
        "api_agent_model_templates": render_api_agent_model_templates(agent_policy_service),
        "api_agent_model_policy_validate": render_post_agent_model_policy_validate(
            agent_policy_service
        ),
        "api_agent_model_policy_put": render_put_agent_model_policy(agent_policy_service),
        "api_sessions": render_api_sessions(service),
        "memory": render_memory(workspace_root),
        "memory_view": render_memory_wrapper(workspace_root),
        "static": render_static(),
    }
