#!/usr/bin/env python3
"""The release ledger's ONE writer and validator — `specs/releases/<id>/_RELEASE.json`,
the candidate trio and the append-only ship ledger, stdlib only.

``release.py <verb> --specs <path>``. Every write builds the new state bytes, runs
`check` over them, and only then replaces the file atomically — so this script's writer
and its validator cannot disagree about what a valid release state is.

Promotion is the operator merging the release PR — no verb archives anything.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

# A projected skill folder is not a package dir to litter: the sibling modules below
# import without leaving a `__pycache__` beside them.
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _release_check import memory_refusals  # noqa: E402
from _release_new import new_release  # noqa: E402
from _release_phase import set_phase  # noqa: E402
from _release_schema import CODE, STATE, find_specs, utc_now  # noqa: E402
from _release_store import Refusal, State, commit, live_release, window_start  # noqa: E402
from _release_tree import check  # noqa: E402

# The worklist has ONE decider, the spec navigator's drift function, projected beside
# this skill: importing a pure function is not a script calling a script (SPEC D6).
sys.path.insert(1, str(Path(__file__).resolve().parents[2] / "dd-spec-navigator" / "scripts"))
import _memory_drift as drift  # noqa: E402

_HELP = {
    "new": "mint the one live release: its SPEC.md stub and _RELEASE.json, in one act",
    "phase": "move the live release to IMPLEMENTATION or CLOSURE, stamping its milestone",
    "memory": "append the closure's one structured `kind: memory` entry to the live log",
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
        if verb == "memory":
            for name in ("--reviewed", "--changed"):
                command.add_argument(name, default="", help="comma-separated worklist entries")
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


def _memory(args: argparse.Namespace, specs: Path) -> int:
    """Append the record over the ledger-derived window, refused unless its worklist was worked."""
    live = live_release(specs)
    since = window_start(live.state)
    try:
        worklist = drift.report(specs, since)
        until = drift.git(specs.parent, "rev-parse", "HEAD")[0]
    except drift.Refusal as refusal:
        raise Refusal(str(refusal), refusal.fix) from refusal
    lists = [[s for s in getattr(args, n).split(",") if s] for n in ("reviewed", "changed")]
    errors = memory_refusals(str(live.state.get("phase")), worklist, *lists)
    errors = errors or _unmoved(specs.parent, since, worklist, lists[1])
    if errors:
        raise Refusal(errors[0], f"{Path(__file__).name} memory --help")
    ts = utc_now()
    entry = {"ts": ts, "agent": "release.py memory", "kind": "memory",
             "text": f"Memory reconciled over {since}..{until[:12]}: {len(lists[0])} reviewed, "
             f"{len(lists[1])} changed.", "since": since, "until": until,
             "reviewed": lists[0], "changed": lists[1]}  # fmt: skip

    def apply(state: State) -> State:
        state.setdefault("log", []).append(entry)
        return state

    commit(live.release_dir / STATE, f"releases/{live.release_id}/{STATE}", apply)
    print(f"[ok] release {live.release_id} log <- kind memory {since}..{until[:12]} ({ts})")
    return 0


def _unmoved(repo: Path, since: str, worklist: dict[str, Any], changed: list[str]) -> list[str]:
    """A `changed` atom git says did not move over since..HEAD changed nothing."""
    paths = {str(atom["slug"]): str(atom["path"]) for atom in worklist["atoms"]}
    return [
        f"--changed names {slug!r}, whose atom did not move since {since}"
        for slug in changed
        if slug in paths
        # git decides "moved": it normalises line endings a byte compare would not.
        and subprocess.run(
            ["git", "diff", "--quiet", since, "HEAD", "--", paths[slug]],
            cwd=repo,
            capture_output=True,
            check=False,
        ).returncode
        == 0  # fmt: skip
    ]


_VERBS = {"new": _new, "phase": _phase, "memory": _memory}


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
