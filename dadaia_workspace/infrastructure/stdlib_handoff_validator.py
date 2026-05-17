"""stdlib-only handoff document validator (NFR3 — zero external dependencies).

Implements ``ValidatorPort`` using only Python standard library modules:
``json``, ``re``, ``datetime``, ``pathlib``.  Any JSON Schema keyword outside
the explicit whitelist ``SUPPORTED_KEYWORDS`` causes ``HandoffSchemaError`` at
construction time — failing loudly rather than silently accepting unsupported
constraints.

Supported keywords
------------------
``$schema``, ``type``, ``required``, ``enum``, ``pattern``, ``properties``,
``items``, ``additionalProperties``, ``format``, ``minimum``, ``minItems``,
``title``, ``description``

Keyword support in ``validate()``
----------------------------------
- ``type`` — checks Python type (str, int, float, bool, list, dict, None).
- ``required`` — emits an error per missing property.
- ``enum`` — membership check.
- ``pattern`` — ``re.fullmatch`` on the value string.
- ``format: date-time`` — ``datetime.fromisoformat`` (trailing Z replaced).
- ``additionalProperties: false`` — rejects unknown keys.
- ``properties`` — recurses into nested object schemas.
- ``items`` — recurses into each array element.
- ``minItems`` — integer lower-bound on array length.
- ``minimum`` — numeric lower-bound.
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

from dadaia_workspace.core.exceptions import HandoffSchemaError, HandoffValidationError

# ---------------------------------------------------------------------------
# Whitelist of supported JSON Schema keywords
# ---------------------------------------------------------------------------

SUPPORTED_KEYWORDS: frozenset[str] = frozenset(
    {
        "$schema",
        "type",
        "required",
        "enum",
        "pattern",
        "properties",
        "items",
        "additionalProperties",
        "format",
        "minimum",
        "minItems",
        "title",
        "description",
    }
)

# Mapping from JSON Schema type names to Python types
_TYPE_MAP: dict[str, type | tuple[type, ...]] = {
    "string": str,
    "integer": int,
    "number": (int, float),
    "object": dict,
    "array": list,
    "boolean": bool,
    "null": type(None),
}


def _walk_schema(schema: Any, path: str = "") -> None:
    """Recursively walk schema and raise HandoffSchemaError on unsupported keywords."""
    if not isinstance(schema, dict):
        return
    for key in schema:
        if key not in SUPPORTED_KEYWORDS:
            raise HandoffSchemaError(f"Unsupported schema keyword: {key}")
    # Recurse into sub-schemas
    for prop_schema in schema.get("properties", {}).values():
        _walk_schema(prop_schema, path)
    items_schema = schema.get("items")
    if isinstance(items_schema, dict):
        _walk_schema(items_schema, path)
    elif isinstance(items_schema, list):
        for sub in items_schema:
            _walk_schema(sub, path)


def _validate_node(
    value: Any,
    schema: dict[str, Any],
    path: str,
    errors: list[HandoffValidationError],
) -> None:
    """Validate ``value`` against ``schema``, appending to ``errors``."""

    # --- type ---
    type_name = schema.get("type")
    if type_name is not None:
        expected_py = _TYPE_MAP.get(str(type_name))
        if expected_py is not None:
            # Special case: JSON integers are valid "number"; Python booleans
            # are subclasses of int but are NOT valid "integer"/"number".
            if type_name == "boolean":
                if not isinstance(value, bool):
                    errors.append(
                        HandoffValidationError(path, f"expected boolean, got {type(value).__name__}")
                    )
                    return
            elif type_name in ("integer", "number"):
                if isinstance(value, bool) or not isinstance(value, expected_py):
                    errors.append(
                        HandoffValidationError(
                            path, f"expected {type_name}, got {type(value).__name__}"
                        )
                    )
                    return
            else:
                if isinstance(value, bool) and type_name != "boolean":
                    # bool is a subclass of int — reject for non-boolean schemas
                    if type_name == "integer":
                        errors.append(
                            HandoffValidationError(
                                path, f"expected {type_name}, got bool"
                            )
                        )
                        return
                if not isinstance(value, expected_py):
                    errors.append(
                        HandoffValidationError(
                            path, f"expected {type_name}, got {type(value).__name__}"
                        )
                    )
                    return

    # --- enum ---
    enum_values = schema.get("enum")
    if enum_values is not None:
        if value not in enum_values:
            errors.append(
                HandoffValidationError(path, f"{value!r} is not one of {enum_values!r}")
            )
            return

    # --- pattern ---
    pattern = schema.get("pattern")
    if pattern is not None and isinstance(value, str):
        if not re.fullmatch(pattern, value):
            errors.append(HandoffValidationError(path, f"{value!r} does not match pattern {pattern!r}"))

    # --- format: date-time ---
    fmt = schema.get("format")
    if fmt == "date-time" and isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        try:
            datetime.fromisoformat(normalized)
        except ValueError:
            errors.append(HandoffValidationError(path, f"{value!r} is not a valid date-time"))

    # --- minimum ---
    minimum = schema.get("minimum")
    if minimum is not None and isinstance(value, (int, float)):
        if value < minimum:
            errors.append(HandoffValidationError(path, f"{value} is less than minimum {minimum}"))

    # --- minItems ---
    min_items = schema.get("minItems")
    if min_items is not None and isinstance(value, list):
        if len(value) < min_items:
            errors.append(
                HandoffValidationError(path, f"array has {len(value)} items, minimum is {min_items}")
            )

    # --- object-specific checks ---
    if isinstance(value, dict):
        # required
        required_fields: list[str] = schema.get("required", [])
        for field in required_fields:
            if field not in value:
                child_path = f"{path}.{field}" if path else field
                errors.append(HandoffValidationError(child_path, "required field missing"))

        # additionalProperties: false
        if schema.get("additionalProperties") is False:
            allowed_keys = set(schema.get("properties", {}).keys())
            for extra_key in value:
                if extra_key not in allowed_keys:
                    child_path = f"{path}.{extra_key}" if path else extra_key
                    errors.append(
                        HandoffValidationError(child_path, f"additional property '{extra_key}' is not allowed")
                    )

        # properties
        properties = schema.get("properties", {})
        for prop_name, prop_schema in properties.items():
            if prop_name in value:
                child_path = f"{path}.{prop_name}" if path else prop_name
                _validate_node(value[prop_name], prop_schema, child_path, errors)

    # --- array-specific checks ---
    elif isinstance(value, list):
        items_schema = schema.get("items")
        if isinstance(items_schema, dict):
            for idx, element in enumerate(value):
                child_path = f"{path}[{idx}]"
                _validate_node(element, items_schema, child_path, errors)


class StdlibHandoffValidator:
    """Stdlib-only validator implementing ``ValidatorPort``.

    Loads and validates the JSON Schema at ``schema_path`` at construction time.
    Raises ``HandoffSchemaError`` if:

    - ``schema_path`` does not exist.
    - The schema file is invalid JSON.
    - The schema uses any keyword outside ``SUPPORTED_KEYWORDS``.

    ``validate(doc)`` returns an empty list for valid documents and a list of
    ``HandoffValidationError`` instances for each structural violation found.
    """

    def __init__(self, schema_path: Path) -> None:
        if not schema_path.exists():
            raise HandoffSchemaError(
                f"Schema file not found: {schema_path}"
            )
        try:
            raw = schema_path.read_text(encoding="utf-8")
            self._schema: dict[str, Any] = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise HandoffSchemaError(f"Schema is not valid JSON: {exc}") from exc

        # Walk the schema and reject unsupported keywords
        _walk_schema(self._schema)

    def validate(self, doc: dict[str, object]) -> Sequence[HandoffValidationError]:
        """Validate ``doc`` against the loaded schema.

        Returns:
            An empty list if valid; a list of ``HandoffValidationError`` otherwise.
        """
        errors: list[HandoffValidationError] = []
        _validate_node(doc, self._schema, "", errors)
        return errors
