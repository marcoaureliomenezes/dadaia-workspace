#!/usr/bin/env python3
"""What a valid memory tree is HERE: the two generated files say what the atoms say.

The atoms' own frontmatter is validated by the library lint (`features/specs/
memory_lint.py`, the doctor's LINT-1) and by nothing else — this module is the
generated-pair decider, and `catalog generate` validates its own result against it, so
the renderer and the checker cannot disagree about what the pair should contain.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _memory_catalog as cat  # noqa: E402
from _memory_schema import CATALOG, CODE, INDEX  # noqa: E402

Finding = dict[str, Any]


def check(specs: Path) -> list[Finding]:
    """The catalog and index as they would be regenerated, against what is on disk."""
    try:
        catalog = cat.generate(specs)
    except (cat.Refusal, json.JSONDecodeError) as exc:
        return [{"code": CODE, "path": CATALOG, "line": 0, "message": str(exc)}]
    out: list[Finding] = []
    for name, rendered in ((CATALOG, cat.serialize(catalog)), (INDEX, cat.render(specs, catalog))):
        path = specs / name
        if not path.is_file():
            out.append({"path": name, "line": 0, "message": f"{path.name} does not exist"})
        elif path.read_text(encoding="utf-8") != rendered:
            out.append({
                "path": name, "line": 0,
                "message": f"{path.name} does not match the atoms it is generated from",
            })  # fmt: skip
    for finding in out:
        finding["code"] = CODE
    return out
