#!/usr/bin/env python3
"""Canonical worktrees `worktrees/<repo>/<name>` on branch `wt/<name>`, stdlib
only: `new` opens one, `merge` lands it after its checks, `clean` drops an empty one,
`hash` prints a verdict's binding, `sync` rebases a tree and those below it, `list` reads ours from git.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
#: One bootstrap statement: this folder and the kernel, at the front.
sys.path[:0] = [
    str(Path(__file__).resolve().parent),
    str(Path(__file__).resolve().parents[2] / "dd-bug-resolution" / "scripts"),
]

from _git import GitError
from _platform import act, inline, use_utf8_stdio
from _refusal import report, spell_fix
from _worktree_end import clean, digest, merge
from _worktree_git import rows, workspace_of
from _worktree_names import LAUNCH, Refusal
from _worktree_new import new
from _worktree_pause import pause, resume
from _worktree_sync import sync

__all__ = ["main"]


def main(argv: list[str] | None = None) -> int:
    use_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    verbs = parser.add_subparsers(dest="verb", required=True)
    make = verbs.add_parser("new", help="open an rc, main, task, backlog or hotfix worktree")
    make.add_argument("repo")
    make.add_argument(
        "name",
        help="<M.m.p>/rc-<N>/wt-rc, <M.m.p>/rc-<N>/job-<n>/wt-main or wt-task-<kkk>, <M.m.p>/wt-backlog-<slug>, <M.m.p>/wt-hotfix-<bug-id>",
    )

    def end_args(end: argparse.ArgumentParser) -> None:
        end.add_argument("path")
        end.add_argument(
            "--keep", nargs="+", default=[], help="ignored files to copy into the repo"
        )
        end.add_argument("--drop", action="store_true", help="discard the other ignored files")

    end_args(verbs.add_parser("merge", help="land a worktree on its parent after its gate"))
    end_args(verbs.add_parser("clean", help="remove a merged or commit-less worktree"))
    verbs.add_parser(
        "sync", help="rebase a tree and the trees below it, parents first"
    ).add_argument("path")
    verbs.add_parser("pause", help="bundle a lane or wt-rc tree, then remove it").add_argument(
        "path"
    )
    verbs.add_parser("resume", help="recreate a paused tree from its bundle").add_argument("path")
    seal = verbs.add_parser("hash", help="the diff_sha256 binding a verdict carries for a sha")
    seal.add_argument("path")
    seal.add_argument("--sha", required=True)
    verbs.add_parser("list", help="our worktrees and the leftovers git does not list").add_argument(
        "--json", action="store_true"
    )
    args = parser.parse_args(argv)
    try:
        if (root := workspace_of(Path.cwd(), Path(__file__))) is None:  # projected inside one
            raise Refusal(
                "no workspace root above the cwd or this script", "uvx dadaia-workspace init"
            )
        if args.verb == "new":
            print(f"[ok] {new(root, args.repo, args.name)}")
            return 0
        if args.verb == "sync":
            print(f"[ok] {sync(root, args.path)}")
            return 0
        if args.verb == "pause":
            print(f"[ok] {pause(root, args.path)}")
            return 0
        if args.verb == "resume":
            print(f"[ok] {resume(root, args.path)}")
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
        report(refusal, refusal.fix)
        return 1
    except GitError as failure:  # no check named it: an agent act, then the same call
        words = sys.argv[1:] if argv is None else argv
        path = getattr(args, "path", None)
        again = inline(*LAUNCH, *(str(Path(w).resolve()) if w == path else w for w in words))
        report(failure, act("agent", f"clear the git failure above, then rerun {again}"))
        return 1
    if args.json:
        print(json.dumps(found, indent=2))
    for row in [] if args.json else found:
        print(
            f"{row['state']}  {row['path']}"
            + (f"  {spell_fix(str(row['fix']))}" if row["fix"] else "")
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
