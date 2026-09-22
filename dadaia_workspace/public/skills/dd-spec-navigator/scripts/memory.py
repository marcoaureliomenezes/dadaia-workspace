#!/usr/bin/env python3
"""The memory catalog's ONE writer — `specs/memory/product/{catalog.json,index.md}` and
the atoms they are generated from, stdlib only.

``memory.py <verb> --specs <path>``. `catalog generate` rewrites both generated files
from the atoms' frontmatter in one act, so the pair cannot drift apart; `check` reports
where the pair stopped saying what the atoms say. Writing an atom is the closure
reconciliation's own act and validating one is the library lint's fact: this script does
neither.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# A projected skill folder is not a package dir to litter: the sibling modules below
# import without leaving a `__pycache__` beside them.
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

import _memory_catalog as cat  # noqa: E402
from _memory_check import check  # noqa: E402
from _memory_schema import CATALOG, INDEX, find_specs  # noqa: E402


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="verb", required=True)
    catalog = sub.add_parser("catalog", help="the generated catalog pair").add_subparsers(
        dest="noun", required=True
    )
    generate = catalog.add_parser("generate", help="rewrite catalog.json and index.md")
    validate = sub.add_parser("check", help="validate the generated pair against the atoms")
    validate.add_argument("--json", action="store_true", help="emit findings as JSON")
    for command in (generate, validate):
        command.add_argument("--specs", type=Path, default=None, help="path to the specs/ tree")
    return parser


def _generate(specs: Path) -> str:
    """Rewrite BOTH generated files from the atoms — one act, no half-refresh."""
    catalog = cat.generate(specs)
    (specs / CATALOG).write_text(cat.serialize(catalog), encoding="utf-8")
    (specs / INDEX).write_text(cat.render(specs, catalog), encoding="utf-8")
    count = len(catalog["features"])
    return f"[ok] {CATALOG} and {INDEX} written ({count} feature{'s' if count != 1 else ''})"


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    # Resolved: the catalog's `context` is the specs tree's parent directory name, so a
    # relative `--specs specs` must name the same context an absolute path does.
    specs = args.specs.resolve() if args.specs is not None else find_specs(Path.cwd())
    if args.verb == "check":
        findings = check(specs)
        if args.json:
            print(json.dumps(findings, indent=2))
        else:
            for finding in findings:
                print(f"{finding['code']} error {finding['path']}:{finding['line']} "
                      f"{finding['message']}")  # fmt: skip
        return 1 if findings else 0
    try:
        print(_generate(specs))
    except cat.Refusal as refusal:
        print(f"[error] {refusal}", file=sys.stderr)
        print(f"fix: {refusal.fix}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
