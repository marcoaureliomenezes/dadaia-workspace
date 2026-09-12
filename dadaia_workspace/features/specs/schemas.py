"""The ONE loader for every packaged public JSON schema (0.4.7 FR6, T-047-03).

Each schema consumer used to carry its own two lines of "resolve the package root,
read the file, cast the JSON" — ``release_tree`` (release-state-v1),
``memory_lint`` (memory-frontmatter-v1) — and every ledger this task validates would
have added another. One loader, one cache, one name space: a schema is addressed by
its path under ``dadaia_workspace/public/schemas/`` without the ``.schema.json``
suffix (``"ADRs/decision-record-v1"``).

``core.handoff_index``'s handoff-schema read is deliberately NOT folded in here: it
reads the PROJECTED copy under a workspace's ``.dadaia/agentic/schemas/``, a
different root resolved per workspace, not packaged data.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from functools import cache
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator

__all__ = ["SCHEMA_ROOT", "load_schema", "schema_errors", "validator_for"]

#: ``dadaia_workspace/public/schemas/`` — packaged data, present in the installed wheel.
SCHEMA_ROOT = Path(__file__).resolve().parents[2] / "public" / "schemas"


def load_schema(name: str) -> dict[str, Any]:
    """Load one packaged schema by its ``<dir>/<id>`` name.

    Raises ``FileNotFoundError`` naming the path when the installed package is
    incomplete — the one diagnostic every consumer used to spell for itself.
    """
    path = SCHEMA_ROOT / f"{name}.schema.json"
    if not path.is_file():
        raise FileNotFoundError(
            f"{name}.schema.json not found at {path} "
            "— the installed dadaia-workspace package is incomplete."
        )
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


@cache
def validator_for(name: str) -> Draft202012Validator:
    """A cached validator for one packaged schema (a doctor run validates hundreds of
    records against the same handful of schemas)."""
    return Draft202012Validator(load_schema(name))


def schema_errors(instance: object, name: str) -> list[str]:
    """Every validation message for one instance, sorted — never a path, never a
    file name: jsonschema error text names the instance property only, so an issue
    built from these strings is safe to paste into a report."""
    errors: Iterable[Any] = validator_for(name).iter_errors(instance)
    return [error.message for error in sorted(errors, key=str)]
