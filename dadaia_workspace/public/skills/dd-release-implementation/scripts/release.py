#!/usr/bin/env python3
"""The release ledger's ONE writer and validator — `specs/releases/<id>/_RELEASE.json`,
the candidate trio and the append-only ship ledger, stdlib only.

``release.py <verb> --specs <path>``. Every write builds the new state bytes, runs
`check` over them, and only then replaces the file atomically — so this script's writer
and its validator cannot disagree about what a valid release state is.

`archive` is all-or-nothing and runs NO git: it validates, writes, moves, births the next
release, appends the one histo record, and PRINTS the git commands the operator runs
next. Ageing the bug ledger is a numbered step in `RC-FLOW.md`, not a call from here —
one writer per ledger, and scripts never call each other.
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

from _release_archive import archive_release  # noqa: E402
from _release_fold import fold_release  # noqa: E402
from _release_new import new_release  # noqa: E402
from _release_phase import set_phase  # noqa: E402
from _release_rc import rc_archive  # noqa: E402
from _release_schema import CODE, STATE, find_specs, utc_now  # noqa: E402
from _release_store import Refusal  # noqa: E402
from _release_tree import check  # noqa: E402

_HELP = {
    "new": "mint the one live release: its SPEC.md stub and _RELEASE.json, in one act",
    "phase": "move the live release to IMPLEMENTATION or CLOSURE, stamping its milestone",
    "rc-archive": "archive the completed candidate trio into the next rc-N/",
    "archive": "ship the live release: archive it, birth the next, record the histo line",
    "fold": "fold a wrongly archived release into rc-N/ of the version that published it",
    "check": "validate every _RELEASE.json under releases/ and the ship ledger",
}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="verb", required=True)
    for verb, help_text in _HELP.items():
        command = sub.add_parser(verb, help=help_text)
        command.add_argument("--specs", type=Path, default=None, help="path to the specs/ tree")
        if verb == "new":
            command.add_argument("release_id", help="the new release's bare SemVer id")
        if verb == "phase":
            command.add_argument("phase", help="IMPLEMENTATION or CLOSURE")
            command.add_argument("--sha", required=True, help="the commit the milestone names")
        if verb == "archive":
            command.add_argument("release_id", help="the live release being shipped")
            command.add_argument("--shipped", required=True, help="develop -> main merge sha")
            command.add_argument("--pr", required=True, type=int, help="the ship PR's number")
            command.add_argument("--next", required=True, dest="next_release",
                                 help="the next release version, bare SemVer M.m.p")  # fmt: skip
        if verb == "fold":
            command.add_argument("release_id", help="the wrongly archived release id")
            command.add_argument("--into", required=True, help="the version that published it")
            command.add_argument("--shipped", help="its publication sha, when born here")
            command.add_argument("--pr", type=int, help="its ship PR number, when born here")
            command.add_argument("--shipped-ts", help="its publication timestamp (default: now)")
            command.add_argument("--final", action="store_true",
                                 help="place the trio at the target's root")  # fmt: skip
        if verb == "check":
            command.add_argument("--json", action="store_true", help="emit findings as JSON")
    return parser


def _new(args: argparse.Namespace, specs: Path) -> int:
    release_dir = new_release(specs, args.release_id, utc_now()[:10])
    print(f"[ok] created: {release_dir / 'SPEC.md'}")
    print(f"[ok] created: {release_dir / STATE}")
    return 0


def _phase(args: argparse.Namespace, specs: Path) -> int:
    release_id, ts = set_phase(specs, args.phase.upper(), args.sha)
    print(f"[ok] release {release_id} -> phase {args.phase.upper()} ({ts})")
    return 0


def _rc_archive(_: argparse.Namespace, specs: Path) -> int:
    release_id, rc, rc_dir = rc_archive(specs)
    print(
        f"[ok] candidate {rc} of release {release_id} archived -> {rc_dir} — root is "
        "ready for the next candidate's SPEC/PLAN/TASKS."
    )
    return 0


def _archive(args: argparse.Namespace, specs: Path) -> int:
    """The verb PRINTS the git lines and runs none of them: the operator owns the branch
    contract, and a script that pushed would be running it for them."""
    release_id, next_release = args.release_id, args.next_release
    destination = archive_release(specs, release_id, args.shipped, args.pr, next_release)
    print(f"[ok] archived: {destination}")
    print(f"[ok] created: {specs / 'releases' / next_release / STATE}")
    print(f"[ok] histo record: {release_id} (delivered)")
    print(
        "next: git add -A specs/releases specs/bugs && git commit -m "
        f'"chore(specs): archive release {release_id} — shipped {args.shipped} '
        f'(PR #{args.pr}); {next_release} born"'
    )
    print(f"next: git push origin --delete feature/{release_id}")
    print(f"next: git checkout -b feature/{next_release} main && git merge -s ours origin/develop")
    return 0


def _fold(args: argparse.Namespace, specs: Path) -> int:
    placed_at = fold_release(
        specs, args.release_id, args.into, sha=args.shipped, pr=args.pr,
        shipped_ts=args.shipped_ts, final=args.final,
    )  # fmt: skip
    print(f"[ok] {args.release_id} folded into {args.into} at {placed_at}")
    return 0


_VERBS = {"new": _new, "phase": _phase, "rc-archive": _rc_archive, "archive": _archive,
          "fold": _fold}  # fmt: skip


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    specs = args.specs if args.specs is not None else find_specs(Path.cwd())
    if args.verb == "check":
        findings = check(specs)
        print(json.dumps(findings, indent=2)) if args.json else [
            print(f"{CODE} error {f['path']}:{f['line']} {f['message']}") for f in findings
        ]
        return 1 if findings else 0
    try:
        return _VERBS[args.verb](args, specs)
    except Refusal as refusal:
        print(f"[error] {refusal}", file=sys.stderr)
        print(f"fix: {refusal.fix}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
