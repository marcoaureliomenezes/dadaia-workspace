#!/usr/bin/env python3
"""Canonical worktrees `worktrees/<repo>/<M.m.p><letter>-<kind>` on branch `wt/<same>`,
stdlib only: `new` derives one from the repo's work branch, `list` reads ours from git.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _worktree_git import find_root, rows  # noqa: E402
from _worktree_kinds import KINDS, Refusal, allows, kind_for  # noqa: E402
from _worktree_new import new  # noqa: E402

__all__ = ["KINDS", "allows", "kind_for", "main"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    verbs = parser.add_subparsers(dest="verb", required=True)
    make = verbs.add_parser("new", help="create a worktree from the repo's work branch")
    make.add_argument("repo")
    make.add_argument("--kind", required=True, choices=sorted(KINDS))
    verbs.add_parser("list", help="our dadaia:-locked worktrees").add_argument(
        "--json", action="store_true"
    )
    args = parser.parse_args(argv)
    try:
        root = find_root()
        if args.verb == "new":
            print(f"[ok] {new(root, args.repo, args.kind)}")
            return 0
        found = rows(root)
    except Refusal as refusal:
        print(f"[error] {refusal}", f"fix: {refusal.fix}", sep="\n", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(found, indent=2))
    for row in [] if args.json else found:
        print(
            f"{row['path']}  {row['kind']}  {row['age_hours']}h  +{row['ahead']}  {'dirty' if row['dirty'] else 'clean'}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
