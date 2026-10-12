"""The one loader for every packaged public JSON schema.

A schema is addressed by its path under ``dadaia_workspace/public/schemas/`` without the
``.schema.json`` suffix (``"memory/memory-frontmatter-v1"``). A ledger schema is never
validated here: ``_ledger.validate`` is the one ledger engine.

``core.handoff_index``'s handoff-schema read is deliberately NOT folded in here: it
reads the PROJECTED copy under a workspace's ``.dadaia/agentic/schemas/``, a
different root resolved per workspace, not packaged data.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

__all__ = [
    "SCHEMA_ROOT",
    "load_schema",
]

#: ``dadaia_workspace/public/schemas/`` — packaged data, present in the installed wheel.
SCHEMA_ROOT = Path(__file__).resolve().parents[2] / "public" / "schemas"


def load_schema(name: str) -> dict[str, Any]:
    """Load one packaged schema by its ``<dir>/<id>`` name.

    Raises ``FileNotFoundError`` naming the path when the installed package is
    incomplete.
    """
    path = SCHEMA_ROOT / f"{name}.schema.json"
    if not path.is_file():
        raise FileNotFoundError(
            f"{name}.schema.json not found at {path} "
            "— the installed dadaia-workspace package is incomplete."
        )
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
