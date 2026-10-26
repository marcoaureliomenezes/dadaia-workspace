#!/usr/bin/env python3
"""What a valid memory tree is HERE: the catalog says what the atoms say.

The atoms' schema is the library lint's (the doctor's LINT-1, over this skill's one
grammar) — this module is the catalog decider, and `catalog generate` validates
its own result against it, so the renderer and the checker cannot disagree.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import _findings
import _memory_catalog as cat
from _memory_schema import CODE, INDEX, PRODUCT
from _platform import Undecodable, act, read_text
from _refusal import Refusal
from _specs import CATALOG, script

Finding = dict[str, Any]


@_findings.decodable(CODE)
def check(specs: Path) -> list[Finding]:
    """The catalog and index as they would be regenerated, against what is on disk."""
    try:
        catalog = cat.generate(specs)
    except Undecodable:
        raise  # `decodable` names the file; it is no atom or catalog fault
    except (Refusal, json.JSONDecodeError) as exc:  # the missing tree's fix makes it
        fix = getattr(exc, "fix", "")
        if (specs / PRODUCT).is_dir():
            fix = act("agent", f"correct the source atom — {exc} (specs/memory/AGENTS.md: "
                      f"fix findings at the source atom, never in {CATALOG})")  # fmt: skip
        return [_findings.finding(CODE, CATALOG, 0, str(exc), fix)]
    # the catalog is regenerated, never hand-fixed: the fix line clears it
    fix = script(Path(__file__).with_name("memory.py"))(
        "catalog", "generate", specs=specs.resolve()
    )
    out: list[Finding] = []
    for name, rendered in (
        (CATALOG, cat.catalog_text(catalog)),
        (INDEX, cat.render(specs, catalog)),
    ):
        path = specs / name
        if not path.is_file():
            out.append(_findings.finding(CODE, name, 0, f"{path.name} does not exist", fix))
        elif read_text(path) != rendered:
            out.append(
                _findings.finding(
                    CODE, name, 0, f"the catalog in {path.name} does not match the atoms", fix
                )
            )
    return out
