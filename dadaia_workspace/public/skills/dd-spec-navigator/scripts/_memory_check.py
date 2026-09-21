#!/usr/bin/env python3
"""What a valid memory tree is: every atom's five-field frontmatter against
`memory-frontmatter-v1`, and the two generated files agreeing with the atoms.

This is what `memory.py check` reports and what `catalog generate` validates its own
result against — one definition of valid, so the renderer and the validator cannot
disagree about what the catalog should say.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _memory_catalog as cat  # noqa: E402
import _memory_index as idx  # noqa: E402
from _memory_schema import CATALOG, CODE, INDEX, load_schema, parse, validate  # noqa: E402

Finding = dict[str, Any]


def _atom_findings(specs: Path) -> list[Finding]:
    schema = load_schema()
    out: list[Finding] = []
    # An ATOM is `memory/product/<area>/<slug>.md` (specs canon): `memory/`'s own
    # AGENTS.md and the three Part-1/Part-2 documents carry no atom frontmatter, and a
    # walk that read them called every scaffolded tree invalid.
    for path in sorted((specs / "memory" / "product").rglob("*.md")):
        if path.name == "index.md":
            continue
        rel = path.relative_to(specs).as_posix()
        data, _, error = parse(path.read_text(encoding="utf-8"))
        if error is not None or data is None:
            out.append({"path": rel, "line": 1, "message": error or "unreadable frontmatter"})
            continue
        out.extend(
            {"path": rel, "line": 1, "message": message}
            for message in validate(data, schema, "frontmatter")
        )
        if str(data.get("slug", "")) != path.stem:
            out.append({
                "path": rel, "line": 1,
                "message": f"slug {data.get('slug')!r} is not the filename stem {path.stem!r}",
            })  # fmt: skip
    return out


def _generated_findings(specs: Path) -> list[Finding]:
    """The catalog and index as they would be regenerated, against what is on disk."""
    catalog = cat.generate(specs)
    out: list[Finding] = []
    path = specs / CATALOG
    if not path.is_file():
        out.append({"path": CATALOG, "line": 0, "message": "catalog.json does not exist"})
    elif path.read_text(encoding="utf-8") != cat.serialize(catalog):
        out.append({
            "path": CATALOG, "line": 0,
            "message": "catalog.json does not match the atoms it is generated from",
        })  # fmt: skip
    index = specs / INDEX
    if not index.is_file():
        out.append({"path": INDEX, "line": 0, "message": "index.md does not exist"})
    elif index.read_text(encoding="utf-8") != idx.render(specs, catalog):
        out.append({
            "path": INDEX, "line": 0,
            "message": "index.md's catalog section does not match the atoms",
        })  # fmt: skip
    return out


def check(specs: Path) -> list[Finding]:
    """Every atom finding, then the two generated-file findings, in path order.

    A tree whose atoms do not parse is reported on the atoms alone: the generated files
    cannot be compared against a catalog that cannot be built.
    """
    out = _atom_findings(specs)
    if not out:
        try:
            out = _generated_findings(specs)
        except (cat.Refusal, json.JSONDecodeError) as exc:
            out = [{"path": CATALOG, "line": 0, "message": str(exc)}]
    for finding in out:
        finding["code"] = CODE
    return out
