#!/usr/bin/env python3
"""The release ledger's ONE writer and validator — `specs/releases/<id>/_RELEASE.json`,
the candidate trio and the append-only ship ledger, stdlib only.

``release.py <verb> --specs <path>``. Every write builds the new state bytes, runs
`check` over them, and only then replaces the file atomically — so this script's writer
and its validator cannot disagree about what a valid release state is.

Three verbs, no aliases: a release is born, it walks its phases, it is checked. Promotion
is the operator merging the release PR — no verb archives anything, because git already
holds every closed candidate trio at its CLOSURE commit.
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

from _release_new import new_release  # noqa: E402
from _release_phase import set_phase  # noqa: E402
from _release_schema import CODE, STATE, find_specs, utc_now  # noqa: E402
from _release_store import Refusal  # noqa: E402
from _release_tree import check  # noqa: E402

_HELP = {
    "new": "mint the one live release: its SPEC.md stub and _RELEASE.json, in one act",
    "phase": "move the live release to IMPLEMENTATION or CLOSURE, stamping its milestone",
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
            command.add_argument("--origin", default="operator-demand",
                                 help="operator-demand | backlog:<id>[,..] | bugs:<id>[,..]")  # fmt: skip
        if verb == "phase":
            command.add_argument("phase", help="IMPLEMENTATION or CLOSURE")
            command.add_argument("--sha", required=True, help="the commit the milestone names")
            command.add_argument("--pr", type=int, default=None,
                                 help="CLOSURE only: the merged release PR number")  # fmt: skip
        if verb == "check":
            command.add_argument("--json", action="store_true", help="emit findings as JSON")
    return parser


def _new(args: argparse.Namespace, specs: Path) -> int:
    release_dir = new_release(specs, args.release_id, utc_now()[:10], args.origin)
    print(f"[ok] created: {release_dir / 'SPEC.md'}")
    print(f"[ok] created: {release_dir / STATE}")
    return 0


def _phase(args: argparse.Namespace, specs: Path) -> int:
    release_id, ts = set_phase(specs, args.phase.upper(), args.sha, args.pr)
    print(f"[ok] release {release_id} -> phase {args.phase.upper()} ({ts})")
    return 0


_VERBS = {"new": _new, "phase": _phase}


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
