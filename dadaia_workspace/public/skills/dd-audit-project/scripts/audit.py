#!/usr/bin/env python3
"""The audit ledger's ONE writer and validator — `specs/audits/<dir>/FINDINGS.jsonl`
and its append-only archive, stdlib only.

``audit.py <verb> --specs <path>``. A finding is APPENDED by an agent's file tools
(immutable core, like an ADR); this script owns the two acts that CHANGE one: the
governance triple, and the all-or-nothing close that archives the audit and deletes its
directory. Every write builds the new bytes, runs `check` over them, and only then
replaces the file — so this script's writer and its validator cannot disagree.
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

import _audit_verbs as vb  # noqa: E402
from _audit_check import check  # noqa: E402
from _audit_schema import DISPOSITIONS, find_specs  # noqa: E402
from _audit_store import Refusal  # noqa: E402

_HELP = {
    "disposition": "rewrite one finding's disposition, release and reason, in place",
    "close": "archive one fully dispositioned audit: one histo record, then the directory is gone",
    "check": "validate every live FINDINGS.jsonl and audits_histo.jsonl",
}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="verb", required=True)
    for verb, help_text in _HELP.items():
        command = sub.add_parser(verb, help=help_text)
        command.add_argument("--specs", type=Path, default=None, help="path to the specs/ tree")
        if verb in ("disposition", "close"):
            command.add_argument("audit", help="the audit directory name under specs/audits/")
        if verb == "disposition":
            command.add_argument("finding", help="the finding id, e.g. 20260101-slug-F003")
            command.add_argument("--disposition", required=True,
                                 help=f"one of {'|'.join(DISPOSITIONS)}")  # fmt: skip
            command.add_argument("--release", help="the remediation release that closed it")
            command.add_argument("--reason", help="why the finding was not fixed")
        if verb == "close":
            command.add_argument("--sha", required=True, help="the window-end commit sha")
        if verb == "check":
            command.add_argument("--json", action="store_true", help="emit findings as JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    specs = args.specs if args.specs is not None else find_specs(Path.cwd())
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
        if args.verb == "disposition":
            values = {name: getattr(args, name) for name in ("disposition", "release", "reason")}
            print(vb.disposition(specs, args.audit, args.finding, values))
        else:
            print(vb.close(specs, args.audit, args.sha))
    except Refusal as refusal:
        print(f"[error] {refusal}", file=sys.stderr)
        print(f"fix: {refusal.fix}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
