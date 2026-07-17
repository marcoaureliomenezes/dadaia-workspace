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


class ReleaseNotFoundError(DadaiaError):
    """Raised when a lifecycle verb targets a ``--release-id`` that has no release directory.

    ``lifecycle audit`` runs against an EXISTING release; accepting an undefined id would
    synthesize a bogus ``specs/releases/<id>/`` tree by writing its handoff there (bug
    ``audit-accepts-undefined-release-and-creates-release-tree``). The CLI maps this to a
    non-zero exit with an orienting message — never a traceback.
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


class ContextNotAliveError(DadaiaError):
    """Raised when bind is attempted on a context whose state is DEAD.

    AC-T11-5: bind on a DEAD context must raise this instead of proceeding.
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


class WorkspaceVenvBootstrapError(RuntimeError):
    """Workspace venv bootstrap could not install the running distribution."""


class CodexConfigError(DadaiaError, ValueError):
    """Invalid Codex adapter configuration (e.g. an unknown ``DADAIA_CODEX_SANDBOX`` value).

    Inherits ``ValueError`` (back-compat: existing callers catch ValueError) AND
    ``DadaiaError`` so the CLI entrypoint surfaces it as one concise line instead of a raw
    traceback (bug doctor-uninitialized-workspace-traceback class). A stale dadaia that
    predates a newer sandbox value must fail cleanly, not crash.
    """
