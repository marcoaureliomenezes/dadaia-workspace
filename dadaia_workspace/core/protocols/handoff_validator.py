"""Protocol definition for handoff document validators.

Defines the ``ValidatorPort`` contract that infrastructure adapters must implement.
Keeps the feature layer ``reports.validation`` decoupled from any concrete validator.

Per constitution L69: all dependencies used by ``features/`` must pass through a
Protocol defined in ``core/``.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from dadaia_workspace.core.exceptions import HandoffValidationError


@runtime_checkable
class ValidatorPort(Protocol):
    """Port for validating a handoff document dict against the schema.

    Implementations (adapters in ``infrastructure/``) load the schema at
    construction time and validate instances via ``validate()``.

    An empty return sequence means the document is valid.
    A non-empty sequence means the document has one or more violations —
    each represented as a ``HandoffValidationError`` carrying the field path and
    a human-readable message.
    """

    def validate(self, doc: dict[str, object]) -> Sequence[HandoffValidationError]:
        """Validate a handoff document dict against the schema.

        Args:
            doc: The raw dictionary to validate (typically deserialized from JSON).

        Returns:
            An empty sequence if the document is valid.
            A non-empty sequence of ``HandoffValidationError`` instances if not.
        """
        ...
