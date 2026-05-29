"""Domain exceptions for dadaia-workspace."""


class DadaiaError(Exception):
    """Base class for all dadaia-workspace domain errors."""


class WorkspaceNotInitializedError(DadaiaError):
    """Raised when an operation requires an initialized workspace (.dadaia/) that does not exist."""


class ContextAlreadyExistsError(DadaiaError):
    """Raised when attempting to create a context with a name that already exists."""


class ContextNotFoundError(DadaiaError):
    """Raised when a named context is not found in the database."""


class ContextStateError(DadaiaError):
    """Raised when an operation is invalid for the context's current state."""


class PublicAssetError(DadaiaError):
    """Raised when installing public assets fails."""


class RepoCatalogError(DadaiaError):
    """Raised when reading the repos catalog fails."""


class GitCloneError(DadaiaError):
    """Raised when cloning a repository fails."""


class GitSyncError(DadaiaError):
    """Raised when committing or pushing changes before deactivate fails."""


class WorkflowSchemaError(DadaiaError):
    """Raised when a workflow file fails schema validation."""


class WorkflowCycleError(WorkflowSchemaError):
    """Raised when stage dependencies form a cycle."""


class WorkflowNotFoundError(DadaiaError):
    """Raised when a workflow name is not present in the workflow store."""


class RunNotFoundError(DadaiaError):
    """Raised when a run_id is not present under .dadaia/runs/."""


class OrchestrationUnsupportedError(DadaiaError):
    """Raised when the selected runtime cannot execute a workflow's required capability."""


class PortConflictError(DadaiaError):
    """Raised when a port is already registered as active by a different project."""


class PortNotRegisteredError(DadaiaError):
    """Raised when an operation targets a port not present in the registry."""


class HandoffSchemaError(DadaiaError):
    """Raised when the schema file itself is invalid or contains unsupported keywords.

    Example: StdlibHandoffValidator.__init__ encounters 'oneOf' which is outside
    the supported keyword subset. This forces conscious schema evolution decisions
    rather than silent misses.
    """


class HandoffValidationError(DadaiaError):
    """Raised when a handoff document instance fails schema validation.

    Carries structured information about the field that failed and why.
    Returned (not raised) by ``ValidatorPort.validate()`` as a sequence of
    per-violation descriptors; raised by higher-level code when strict mode is on.
    """

    def __init__(self, field_path: str, message: str) -> None:
        self.field_path = field_path
        self.message = message
        super().__init__(f"{field_path}: {message}")


class NoActiveReleaseError(DadaiaError):
    """Raised when ``reports next`` cannot resolve an active release.

    Covers a missing/``none`` ``releases/ACTIVE.md`` in the active context's specs dir.
    The CLI maps this to exit code 3 with an orienting message.
    """


class NoAgentSequenceError(DadaiaError):
    """Raised when the active release's PLAN.md declares no identifiable agent owners.

    The CLI maps this to exit code 3, instructing the operator to declare owners via
    the ``(owner: <agent>)`` / ``**Owner:** <agent>`` / ``owner: <agent>`` patterns.
    """
