#!/usr/bin/env python3
"""Canonical worktrees `worktrees/<repo>/<name>` on branch `wt/<name>`, stdlib
only: `new` opens one, `merge` lands it after its gate, `clean` drops an empty one, `list` reads ours from git.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _worktree_end import clean, merge  # noqa: E402
from _worktree_git import find_root, rows  # noqa: E402
from _worktree_names import Refusal  # noqa: E402
from _worktree_new import new  # noqa: E402

__all__ = ["main"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    verbs = parser.add_subparsers(dest="verb", required=True)
    make = verbs.add_parser("new", help="open a worktree: a job, define or backlog")
    make.add_argument("repo")
    make.add_argument("name", help="<M.m.p>-rc<N>-<job>, <M.m.p>-rc<N>-define, backlog-<slug>")
    for verb, text in (("merge", "land a worktree on the work branch after its gate"),
                       ("clean", "remove a merged or commit-less worktree")):  # fmt: skip
        end = verbs.add_parser(verb, help=text)
        end.add_argument("path")
        end.add_argument(
            "--keep", nargs="+", default=[], help="ignored files to copy into the repo"
        )
        end.add_argument("--drop", action="store_true", help="discard the other ignored files")
    verbs.add_parser("list", help="our dadaia:-locked worktrees").add_argument(
        "--json", action="store_true"
    )
    args = parser.parse_args(argv)
    try:
        root = find_root()
        if args.verb == "new":
            print(f"[ok] {new(root, args.repo, args.name)}")
            return 0
        if args.verb in ("merge", "clean"):
            end_verb = merge if args.verb == "merge" else clean
            print(f"[ok] {end_verb(root, args.path, args.keep, args.drop)}")
            return 0
        found = rows(root)
    except Refusal as refusal:
        print(f"[error] {refusal}", f"fix: {refusal.fix}", sep="\n", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(found, indent=2))
    for row in [] if args.json else found:
        print(f"{row['state']}  {row['path']}" + (f"  fix: {row['fix']}" if row["fix"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
