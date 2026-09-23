#!/usr/bin/env python3
"""The bug ledger's ONE writer and validator — `specs/bugs/BUGS.jsonl`, stdlib only.

``bugs.py <verb> --specs <path>``. Every write builds the new ledger bytes, runs
`check` over them, and only then replaces the file atomically — so this script's writer
and its validator cannot disagree about what a valid record is.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

# A projected skill folder is not a package dir to litter: the sibling modules below
# import without leaving a `__pycache__` beside them.
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

import _bugs_transition as tr  # noqa: E402
import _bugs_write as wr  # noqa: E402
from _bugs_check import CODE, HISTO, LEDGER, check, find_specs  # noqa: E402
from _bugs_store import Refusal, append_raw, commit, read_records  # noqa: E402

_OPTIONS: dict[str, tuple[str, ...]] = {
    "append": ("--bug-id", "--reported-by", "--ts", "--title", "--severity", "--surface",
               "--component", "--context", "--symptom", "--repro", "--expected"),
    "resolve": tuple(f"--{name.replace('_', '-')}" for name in tr.REQUIRED_BY_VERB["resolve"]),
    "supersede": ("--by",), "defer": ("--reason",), "reject": ("--reason",),
}  # fmt: skip
_HELP = {
    "append": "register a brand-new open record",
    "status": "list records, open only by default",
    "stats": "aggregate counts by status and by severity",
    "update": "write a governance field other than status/closed_at/caused_by",
    "resolve": "close a record as resolved, with its lineage and evidence triple",
    "supersede": "close a record as superseded by another slug",
    "defer": "close a record as deferred, with a reason",
    "reject": "close a record as rejected, with a reason",
    "archive": "move long-closed terminal records into bugs_histo.jsonl",
    "check": "validate every BUGS.jsonl record",
}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="verb", required=True)
    for verb, help_text in _HELP.items():
        command = sub.add_parser(verb, help=help_text)
        command.add_argument("--specs", type=Path, default=None, help="path to the specs/ tree")
        if verb in ("update", *tr.REQUIRED_BY_VERB):
            command.add_argument("bug_id", help="the record id to change")
        for option in _OPTIONS.get(verb, ()):
            command.add_argument(option)
        if verb == "status":
            command.add_argument("--all", dest="include_closed", action="store_true")
        if verb == "update":
            command.add_argument("--set", dest="sets", action="append", required=True,
                                 metavar="FIELD=VALUE", help="a 'field=value' pair (repeatable)")  # fmt: skip
        if verb == "archive":
            command.add_argument("--now", help="ISO-8601 UTC instant to treat as now")
            command.add_argument("--threshold-days", type=int, default=90)
        if verb == "check":
            command.add_argument("--json", action="store_true", help="emit findings as JSON")
    return parser


def _values(args: argparse.Namespace, names: tuple[str, ...]) -> dict[str, Any]:
    keys = [name.lstrip("-").replace("-", "_") for name in names]
    return {key: getattr(args, key) for key in keys}


def _read(args: argparse.Namespace, specs: Path) -> int:
    records = read_records(specs / LEDGER)
    if args.verb == "stats":
        print(f"total\t{len(records)}")
        for label, key in (("status", "status"), ("severity", "severity")):
            counts = Counter(str(r[key]) for r in records if r.get(key))
            for value, count in sorted(counts.items()):
                print(f"{label}:{value}\t{count}")
        return 0
    selected = [r for r in records if args.include_closed or r.get("status") == "open"]
    for record in sorted(selected, key=lambda r: str(r["id"])):
        print(f"{record['id']}\t{record['status']}\t{record.get('severity') or '-'}")
    print(f"[ok] {len(selected)} {'all' if args.include_closed else 'open'} bug(s).")
    return 0


def _archive(args: argparse.Namespace, specs: Path) -> int:
    moment = _dt.datetime.fromisoformat(args.now.replace("Z", "+00:00")) if args.now else None
    cutoff = (moment or _dt.datetime.now(tz=_dt.UTC)) - _dt.timedelta(days=args.threshold_days)
    ledger = specs / LEDGER
    moving = wr.archivable(read_records(ledger), cutoff.strftime("%Y-%m-%dT%H:%M:%SZ"))
    if moving:
        append_raw(specs / HISTO, [r for r in read_records(ledger) if r["id"] in moving])
        kept = commit(ledger, lambda records: [r for r in records if r["id"] not in moving])
    else:
        kept = read_records(ledger)
    print(f"[ok] archived {len(moving)} record(s), {len(kept)} kept.")
    return 0


def _write(args: argparse.Namespace, specs: Path) -> int:
    ledger = specs / LEDGER
    if args.verb == "append":
        values = _values(args, _OPTIONS["append"])
        values["id"] = values.pop("bug_id")
        values["ts"] = values["ts"] or wr.now_iso()
        values["reported_by"] = values["reported_by"] or "dd-software-engineer"
        commit(ledger, lambda records: wr.append(records, values))
        print(f"[ok] registered {values['id']} -> {specs}")
        return 0
    if args.verb == "update":
        changes = wr.parse_set_options(args.sets)
        commit(ledger, lambda records: wr.apply_update(records, args.bug_id, changes))
        print(f"[ok] updated {', '.join(sorted(changes))} for {args.bug_id}")
        return 0
    values = _values(args, _OPTIONS[args.verb])
    known = {str(r["id"]) for r in read_records(ledger)}
    commit(ledger, lambda records: tr.transition(records, args.bug_id, args.verb, values, known))
    print(f"[ok] {tr.STATUS_BY_VERB[args.verb]} {args.bug_id}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    specs = args.specs if args.specs is not None else find_specs(Path.cwd())
    if args.verb == "check":
        findings = check(specs)
        print(json.dumps(findings, indent=2)) if args.json else [
            print(f"{CODE} error {LEDGER}:{f['line']} {f['message']}") for f in findings
        ]
        return 1 if findings else 0
    try:
        if args.verb in ("status", "stats"):
            return _read(args, specs)
        return _archive(args, specs) if args.verb == "archive" else _write(args, specs)
    except Refusal as refusal:
        print(f"[error] {refusal}", file=sys.stderr)
        print(f"fix: {refusal.fix}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
