"""OrchestrationService — read-only surface over markdown workflow catalog.

Workflow *execution* has moved to the lifecycle engine (``dadaia lifecycle``).
The markdown ``.workflow.md`` files are reference documents only; this service no
longer dispatches any agent. The reference-only ``AgentDispatcher`` layer (which
spawned nothing and only wrote an invocation markdown file before returning
``AWAITING_GATE``) was retired in release ``multiharness-engine-v0116`` (WS-3).

What remains is the read-only catalog/run-status surface consumed by the CLI and
the panel: ``list_workflows``, ``show_workflow``, ``get_run_status``, ``list_runs``.
``start_run``/``resume_run`` are kept as honest no-ops that return a typed
:class:`OrchestrationOutcome` explaining the move, so existing callers (the CLI and
the panel workflow launcher) keep working and exit cleanly.
"""

from dataclasses import dataclass

from dadaia_workspace.core.exceptions import RunNotFoundError
from dadaia_workspace.core.models.run_state import RunManifest
from dadaia_workspace.core.models.workflow import WorkflowDefinition
from dadaia_workspace.core.protocols.run_state_store import RunStateStore
from dadaia_workspace.core.protocols.workflow_store import WorkflowStore

EXECUTION_MOVED_MESSAGE = (
    "Workflow execution has moved to the lifecycle engine. "
    "Run `dadaia lifecycle <verb>` to drive a release. "
    "The markdown `.workflow.md` files are reference documents only and are no "
    "longer executed by `dadaia orchestrate`."
)


@dataclass(frozen=True)
class OrchestrationOutcome:
    """Result of an attempted (now no-op) orchestrate execution call.

    ``dispatched`` is always ``False``: this surface no longer spawns or invokes
    any agent. ``message`` carries the human-readable "moved to lifecycle" note.
    """

    workflow_name: str
    dispatched: bool
    message: str


class OrchestrationService:
    def __init__(
        self,
        workflow_store: WorkflowStore,
        run_state_store: RunStateStore,
    ) -> None:
        self._workflows = workflow_store
        self._runs = run_state_store

    # ---------- read-side ----------

    def list_workflows(self) -> tuple[WorkflowDefinition, ...]:
        return self._workflows.list()

    def show_workflow(self, name: str) -> WorkflowDefinition:
        return self._workflows.get(name)

    def get_run_status(self, run_id: str) -> RunManifest:
        return self._runs.load_run(run_id)

    def list_runs(self) -> tuple[RunManifest, ...]:
        return self._runs.list_runs()

    # ---------- execution (retired — honest no-op) ----------

    def start_run(self, workflow_name: str) -> OrchestrationOutcome:
        """Honest no-op: execution moved to the lifecycle engine.

        Validates the workflow name against the catalog (so an unknown name still
        raises ``WorkflowNotFoundError``), then returns an outcome that dispatches
        nothing. No run state is created.
        """
        workflow = self._workflows.get(workflow_name)
        return OrchestrationOutcome(
            workflow_name=workflow.name,
            dispatched=False,
            message=EXECUTION_MOVED_MESSAGE,
        )

    def resume_run(self, run_id: str) -> OrchestrationOutcome:
        """Honest no-op: there is nothing to resume — execution moved to lifecycle.

        ``run_id`` is accepted for call-site compatibility but no run is advanced.
        """
        return OrchestrationOutcome(
            workflow_name=run_id,
            dispatched=False,
            message=EXECUTION_MOVED_MESSAGE,
        )


__all__ = [
    "EXECUTION_MOVED_MESSAGE",
    "OrchestrationOutcome",
    "OrchestrationService",
    "RunNotFoundError",
]
