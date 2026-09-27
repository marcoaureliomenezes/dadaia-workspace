"""Domain exceptions for dadaia-workspace."""

from __future__ import annotations


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


class InvalidContextNameError(DadaiaError, ValueError):
    """A context name or repo slug fails the ``CONTEXT_NAME_RE`` allowlist.

    Raised at ``SpecContextService.register``/``add_repo`` — the one place every registry
    insert passes — so ``context create``, ``context repo add`` and ``dadaia import`` refuse
    the same names (bug import-registers-unvalidated-slugs-that-doctor-fix-inv5-rmtrees).
    """


class AssociatedRepoConflictError(DadaiaError):
    """The registry already has an opinion about this slug that the write will not override.

    The slug is the context's own main repo slug, is already an associated repo registered
    with a *different* URL, or is owned by ANOTHER context (its main repo or one of its
    associated repos — ``repos/<slug>`` is a namespace every context shares).
    """


class AssociatedRepoNotFoundError(DadaiaError):
    """``remove_repo``: the slug is not a registered associated repo of the context."""


class PublicAssetError(DadaiaError):
    """Raised when installing public assets fails."""


class RepoUrlMissingError(DadaiaError):
    """A repo slug is registered with neither a clone URL nor a ``repos/<slug>`` checkout."""


class GitCloneError(DadaiaError):
    """Raised when cloning *url* fails; the CLI names the failed URL from ``url``."""

    def __init__(self, message: str, url: str) -> None:
        self.url = url
        super().__init__(message)


class GitSyncError(DadaiaError):
    """Raised when committing or pushing changes before deactivate fails."""


class HandoffSchemaError(DadaiaError):
    """Raised when the schema file itself is invalid or contains unsupported keywords.

    Example: ``core.handoff_index._load_schema`` encounters 'oneOf' which is outside
    the supported keyword subset. This forces conscious schema evolution decisions
    rather than silent misses.
    """


class HandoffValidationError(DadaiaError):
    """Raised when a handoff document instance fails schema validation.

    Carries structured information about the field that failed and why.
    Returned (not raised) by ``core.handoff_index.Handoff.validate()`` as part of a
    ``ValidationResult``'s ``errors`` tuple; raised by higher-level code when strict
    mode is on.
    """

    def __init__(self, field_path: str, message: str) -> None:
        self.field_path = field_path
        self.message = message
        super().__init__(f"{field_path}: {message}")


class SchemaVersionError(DadaiaError):
    """Raised when spec_contexts.json uses an incompatible schema version (v1 or legacy values).

    The message always contains "dadaia migrate" so the user knows what to run.
    Callers must never silently correct v1 data — raise this instead.
    """


class WorkspaceVenvBootstrapError(DadaiaError, RuntimeError):
    """Workspace venv bootstrap could not create the venv or install the distribution.

    Inherits ``DadaiaError`` so the CLI entrypoint renders it as ONE operator-facing
    line (bug r3b-portability-import-venv-permission, F-22 class): as a bare
    ``RuntimeError`` it slipped past ``cli/main``'s ``except DadaiaError`` and every
    venv-bootstrap failure — ``init``, ``import``, ``certify``, ``reconcile`` alike —
    reached the operator as a raw traceback. ``RuntimeError`` is kept in the bases so
    existing ``except RuntimeError`` call sites keep working.
    """


class WorkspaceVenvNewerError(WorkspaceVenvBootstrapError):
    """The workspace venv carries a NEWER dadaia-workspace than the running one (AC2.3).

    A downgrade is refused before any write; *installed* names the version to run
    ``init`` with instead.
    """

    def __init__(self, installed: str, running: str) -> None:
        self.installed = installed
        super().__init__(
            f"the workspace venv carries dadaia-workspace {installed}, newer than the "
            f"running {running}; init never downgrades."
        )


class BootstrapPackageError(DadaiaError, ValueError):
    """``DADAIA_BOOTSTRAP_PACKAGE`` does not name an existing local wheel.

    A dangling value is the normal state after a candidate wheel is replaced, so the
    message must name the offending value and what is required of it — a bare
    ``ValueError`` said neither and (before the CLI boundary landed) tracebacked
    (bug f22-cli-boundary-is-a-whitelist-not-a-boundary). ``ValueError`` is kept in the
    bases so existing ``except ValueError`` call sites keep working.
    """

    @classmethod
    def for_value(cls, raw: str) -> BootstrapPackageError:
        return cls(
            f"DADAIA_BOOTSTRAP_PACKAGE={raw!r} does not name an existing local wheel. "
            "It must be a path to an existing .whl file; unset it to resolve the "
            "distribution normally instead."
        )


class CiPreflightScopeError(DadaiaError):
    """``ci preflight`` was invoked outside the dadaia-workspace source tree.

    Its checks target the library's own paths, so anywhere else it could only report a
    lint failure for a path that does not exist
    (bug ci-preflight-unusable-outside-the-source-repo).
    """
