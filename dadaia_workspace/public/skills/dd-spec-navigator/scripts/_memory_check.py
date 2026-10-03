#!/usr/bin/env python3
"""What a valid memory tree is HERE: the two generated files say what the atoms say.

The atoms' schema is the library lint's (the doctor's LINT-1, over this skill's one
grammar) — this module is the generated-pair decider, and `catalog generate` validates
its own result against it, so the renderer and the checker cannot disagree.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _memory_catalog as cat  # noqa: E402
from _memory_schema import CATALOG, CODE, INDEX  # noqa: E402
from _specs import script, with_specs  # noqa: E402

Finding = dict[str, Any]


def check(specs: Path) -> list[Finding]:
    """The catalog and index as they would be regenerated, against what is on disk."""
    try:
        catalog = cat.generate(specs)
    except (cat.Refusal, json.JSONDecodeError) as exc:  # the missing tree's fix makes it
        fix = getattr(exc, "fix", "")
        if not fix.startswith("mkdir"):
            fix = (f"Operator action: correct the source atom — {exc} (specs/memory/AGENTS.md: "
                   f"fix findings at the source atom, never in {CATALOG})")  # fmt: skip
        return [{"code": CODE, "verdict": "error", "path": CATALOG, "line": 0,
                 "message": str(exc), "fix": fix}]  # fmt: skip
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
    fix = with_specs(
        f"{script(Path(__file__).with_name('memory.py'))} catalog generate", specs.resolve()
    )
    for finding in out:  # the pair is regenerated, never hand-fixed: the fix line clears it
        finding |= {"code": CODE, "fix": fix}
    return out
