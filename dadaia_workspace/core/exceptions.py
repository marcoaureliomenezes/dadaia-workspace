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


class GitOperationError(DadaiaError):
    """Raised when a git operation (clone, commit, push) fails."""


class PublicAssetError(DadaiaError):
    """Raised when installing public assets fails."""


class RepoCatalogError(DadaiaError):
    """Raised when reading the repos catalog fails."""
