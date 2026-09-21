#!/usr/bin/env python3
"""The memory catalog's ONE writer and validator — `specs/memory/product/index.md`,
`catalog.json` and the atoms they are generated from, stdlib only.

``memory.py <verb> --specs <path>``. `catalog generate` rewrites both generated files
from the atoms' frontmatter in one act, so the pair cannot drift apart; `product add`
writes one complete atom; `check` validates every atom's five-field frontmatter and
then that the two generated files say what the atoms say.
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

import _memory_add as add  # noqa: E402
import _memory_catalog as cat  # noqa: E402
import _memory_index as idx  # noqa: E402
from _memory_check import check  # noqa: E402
from _memory_schema import CATALOG, INDEX, find_specs  # noqa: E402


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="verb", required=True)
    catalog = sub.add_parser("catalog", help="the generated catalog pair").add_subparsers(
        dest="noun", required=True
    )
    generate = catalog.add_parser("generate", help="rewrite catalog.json and index.md")
    product = sub.add_parser("product", help="the product memory atoms").add_subparsers(
        dest="noun", required=True
    )
    new = product.add_parser("add", help="write one new atom under its area")
    new.add_argument("area", help="the canon area directory under memory/product/")
    new.add_argument("slug", help="the atom slug, which is also its filename stem")
    for option in ("--title", "--tldr", "--summary"):
        new.add_argument(option, required=True)
    new.add_argument("--tags", help="comma-separated tags (default: the area)")
    validate = sub.add_parser("check", help="validate the atoms and the generated pair")
    validate.add_argument("--json", action="store_true", help="emit findings as JSON")
    for command in (generate, new, validate):
        command.add_argument("--specs", type=Path, default=None, help="path to the specs/ tree")
    return parser


def _generate(specs: Path) -> str:
    """Rewrite BOTH generated files from the atoms — one act, no half-refresh."""
    catalog = cat.generate(specs)
    (specs / CATALOG).write_text(cat.serialize(catalog), encoding="utf-8")
    (specs / INDEX).write_text(idx.render(specs, catalog), encoding="utf-8")
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
        if args.verb == "catalog":
            print(_generate(specs))
        else:
            values = {name: getattr(args, name) for name in ("title", "tldr", "summary", "tags")}
            print(add.add(specs, args.area, args.slug, values))
    except cat.Refusal as refusal:
        print(f"[error] {refusal}", file=sys.stderr)
        print(f"fix: {refusal.fix}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
