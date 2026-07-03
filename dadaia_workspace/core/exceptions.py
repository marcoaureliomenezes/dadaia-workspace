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


class SchemaVersionError(DadaiaError):
    """Raised when spec_contexts.json uses an incompatible schema version (v1 or legacy values).

    The message always contains "dadaia migrate" so the user knows what to run.
    Callers must never silently correct v1 data — raise this instead.
    """


class ContextLockedError(DadaiaError):
    """Raised when an operation on a context is blocked because a lock is held.

    E.g. calling dead() on a context that has an active implementation lock.
    """


class LockConflictError(DadaiaError):
    """Base class for all lock-conflict errors.

    Raised when two sessions attempt mutually-exclusive operations on the same
    context/release pair.
    """


class LockHeldError(LockConflictError):
    """Raised when a second bind --mode implementation is attempted while a lock is already HELD.

    The message includes the owner session_id and last_seen_at.
    """


class WorkspaceLockTimeoutError(DadaiaError):
    """Raised when the workspace-wide fcntl lock cannot be acquired within the timeout.

    Includes the holder PID if discoverable from the lock file content.
    """


class ContextNotAliveError(DadaiaError):
    """Raised when bind is attempted on a context whose state is DEAD.

    AC-T11-5: bind on a DEAD context must raise this instead of proceeding.
    """


class LockActiveError(DadaiaError):
    """Raised when a forced reclaim is attempted on a HELD (non-stale) lock.

    AC-T12-3 (T-12): reclaim() on a fresh HELD lock raises this.
    Also used in T-11 reclaim path.
    """


class PlatformSecurityError(DadaiaError):
    """Raised when a security control cannot be enforced on the current platform.

    Tier 1 — FAIL LOUD. This error signals a hard security violation: the
    platform cannot satisfy the requested security guarantee (e.g. restricting
    a file to owner-only). Silent no-ops or warnings are forbidden for Tier 1
    controls. Callers must propagate this error without suppression.

    Attributes:
        feature_name: Logical name of the security feature that failed
                      (e.g. ``"token_file_protection"``).
        platform:     The ``sys.platform`` value at the point of failure
                      (e.g. ``"win32"``).
    """

    def __init__(self, message: str, *, feature_name: str, platform: str) -> None:
        self.feature_name = feature_name
        self.platform = platform
        super().__init__(message)


class PlatformCapabilityError(DadaiaError):
    """Raised when an OS capability required by a feature is absent on the current platform.

    Tier 2/3 — DEGRADE WITH LOG or UNSUPPORTED PLATFORM at construction.
    This error signals that the platform lacks the OS primitive needed
    (e.g. ``fcntl`` on Windows, ``msvcrt`` on non-Windows). Consumers should
    either degrade gracefully (Tier 2: log INFO and return a safe default)
    or propagate (Tier 3: unsupported-platform at construction time).

    Attributes:
        feature_name: Logical name of the capability that is absent
                      (e.g. ``"fcntl_file_lock"``).
        platform:     The ``sys.platform`` value at the point of failure
                      (e.g. ``"win32"``).
    """

    def __init__(self, message: str, *, feature_name: str, platform: str) -> None:
        self.feature_name = feature_name
        self.platform = platform
        super().__init__(message)
