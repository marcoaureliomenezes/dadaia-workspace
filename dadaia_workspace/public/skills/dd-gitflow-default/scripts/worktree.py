#!/usr/bin/env python3
"""Canonical worktrees `worktrees/<repo>/<name>` on branch `wt/<name>`, stdlib
only: `new` opens one, `merge` lands it after its gate, `stage` runs a job's stage gate,
`clean` drops an empty one, `hash` prints a verdict's binding, `list` reads ours from git.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _worktree_end import clean, digest, merge, stage  # noqa: E402
from _worktree_git import find_root, rows  # noqa: E402
from _worktree_names import Refusal  # noqa: E402
from _worktree_new import new  # noqa: E402

__all__ = ["main"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    verbs = parser.add_subparsers(dest="verb", required=True)
    make = verbs.add_parser("new", help="open a worktree: a job, a task, define or backlog")
    make.add_argument("repo")
    make.add_argument(
        "name",
        help="<M.m.p>-rc<N>/<job>[--<task-id>], <M.m.p>-rc<N>/define, backlog/<slug>, hotfix/<bug-id>",
    )
    verbs.add_parser(
        "stage", help="close a job's stage: its stage gate, no task open"
    ).add_argument("path")

    def end_args(end: argparse.ArgumentParser) -> None:
        end.add_argument("path")
        end.add_argument(
            "--keep", nargs="+", default=[], help="ignored files to copy into the repo"
        )
        end.add_argument("--drop", action="store_true", help="discard the other ignored files")

    end_args(verbs.add_parser("merge", help="land a worktree on its branch after its gate"))
    end_args(verbs.add_parser("clean", help="remove a merged or commit-less worktree"))
    seal = verbs.add_parser("hash", help="the diff_sha256 binding a verdict carries for a sha")
    seal.add_argument("path")
    seal.add_argument("--sha", required=True)
    verbs.add_parser("list", help="our dadaia:-locked worktrees").add_argument(
        "--json", action="store_true"
    )
    args = parser.parse_args(argv)
    try:
        root = find_root()
        if args.verb == "new":
            print(f"[ok] {new(root, args.repo, args.name)}")
            return 0
        if args.verb == "stage":
            print(f"[ok] {stage(root, args.path)}")
            return 0
        if args.verb == "hash":
            print(digest(root, args.path, args.sha))
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
