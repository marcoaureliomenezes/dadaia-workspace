#!/usr/bin/env python3
"""The backlog's ONE writer and validator — `specs/backlog/BACKLOG.json` and its
append-only exit ledger, stdlib only.

``backlog.py <verb> --specs <path>``. Every write builds the new document bytes, runs
`check` over them, and only then replaces the file atomically — so this script's writer
and its validator cannot disagree about what a valid backlog is.

``subjects`` lists what this script can see bound: the operator alias map and the
subjects the live document already carries. Deriving the ~5k code/doc/cli anchors from
the source tree stays where its reader lives — the doctor's `BL-SCHEMA` registry — so
there is one derivation, not a second copy of it inside a skill script.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# A projected skill folder is not a package dir to litter: the sibling modules below
# import without leaving a `__pycache__` beside them.
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

import _backlog_exit as ex  # noqa: E402
import _backlog_subjects as sj  # noqa: E402
import _backlog_write as wr  # noqa: E402
from _backlog_check import check  # noqa: E402
from _backlog_schema import CODE, DISPOSITIONS, HISTO, LEDGER, find_specs  # noqa: E402
from _backlog_store import Refusal, append_histo, commit, read_active  # noqa: E402

_HELP = {
    "new": "append one brand-new active[] entry, born at status 'idea'",
    "exit": "retire one live entry and append its one terminal histo record",
    "subjects": "list the bindable canonical subjects, or resolve one",
    "check": "validate BACKLOG.json and backlog_histo.jsonl",
}
_ALIAS_DEFAULT = ".dadaia/states/backlog_subject_aliases.txt"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="verb", required=True)
    for verb, help_text in _HELP.items():
        command = sub.add_parser(verb, help=help_text)
        command.add_argument("--specs", type=Path, default=None, help="path to the specs/ tree")
        if verb in ("new", "exit"):
            command.add_argument("slug", help="the backlog entry's slug")
        if verb == "new":
            for option in ("--title", "--description", "--provenance"):
                command.add_argument(option)
            command.add_argument("--intent", action="append", metavar="KIND:REF=CHANGE",
                                 help="one typed intent (repeatable)")  # fmt: skip
        if verb == "exit":
            command.add_argument("--disposition", required=True,
                                 help=f"one of {'|'.join(DISPOSITIONS)}")  # fmt: skip
            for option in ("--release", "--reason", "--summary", "--ts"):
                command.add_argument(option)
        if verb == "subjects":
            command.add_argument("--alias-map", type=Path, default=None,
                                 help=f"alias map (default: <workspace>/{_ALIAS_DEFAULT})")  # fmt: skip
            command.add_argument("--kind", help="filter to one subject kind")
            command.add_argument("--resolve", help="resolve one proposed subject ref and exit")
        if verb == "check":
            command.add_argument("--json", action="store_true", help="emit findings as JSON")
    return parser


def _values(args: argparse.Namespace, names: tuple[str, ...]) -> dict[str, Any]:
    return {name: getattr(args, name) for name in names}


def _new(args: argparse.Namespace, specs: Path) -> int:
    values = _values(args, ("title", "description", "provenance", "intent"))
    commit(specs / LEDGER, lambda active: wr.new_entry(active, args.slug, values))
    print(f"[ok] appended {args.slug!r} -> {specs / LEDGER}")
    return 0


def _exit(args: argparse.Namespace, specs: Path) -> int:
    """The atomic pair: the terminal record, then the removal. Every refusal has already
    run, so the only ordering left is the one whose crash is recoverable — a record with
    the entry still live is a re-runnable exit; a removal with no record is a lost item.
    """
    values = _values(args, ("disposition", "release", "reason", "summary", "ts"))
    entry = ex.check_exit(specs, read_active(specs / LEDGER), args.slug, values)
    append_histo(specs / HISTO, ex.histo_record(entry, values))
    commit(specs / LEDGER, lambda active: [i for i in active if i.get("id") != args.slug])
    print(f"[ok] exited {args.slug!r} ({values['disposition']}) -> {specs / HISTO}")
    return 0


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
        if args.verb == "subjects":
            return sj.subjects(args, specs, _ALIAS_DEFAULT)
        return _new(args, specs) if args.verb == "new" else _exit(args, specs)
    except Refusal as refusal:
        print(f"[error] {refusal}", file=sys.stderr)
        print(f"fix: {refusal.fix}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
