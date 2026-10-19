#!/usr/bin/env python3
"""The bug ledger's ONE writer and validator — `specs/bugs/BUGS.jsonl`, stdlib only."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from functools import reduce
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

import _bugs_transition as tr
import _bugs_write as wr
import _findings
import _jsonl
from _atomic import SymlinkRefusedError
from _bugs_check import LEDGER, OPEN, STATUS_BY_VERB, check
from _bugs_store import Refusal, archived_plain_ids, commit, history, read_records
from _git import GitError, fix_files, git
from _platform import act, use_utf8_stdio
from _refusal import report
from _specs import find_specs, refuse

_OPTIONS: dict[str, tuple[str, ...]] = {
    "append": (
        "--bug-id",
        "--reported-by",
        "--title",
        "--severity",
        "--component",
        "--context",
        "--symptom",
        "--repro",
        "--expected",
        "--correlates",
    ),
    "resolve": ("--cause", "--caused-by", "--solution", "--fix-sha"),
    "supersede": ("--by",),
    "reject": ("--reason",),
}
_CORRELATES = "an earlier bug id; repeat the flag, or comma-separate the ids, or none"
_HELP = {
    "append": "register a brand-new open record",
    "status": "list records, open only by default",
    "stats": "aggregate counts by status and severity",
    "update": "write a governance field other than status/closed_at",
    "resolve": "close a record as resolved, with its cause, solution and fix sha",
    "supersede": "close a record as superseded by another slug",
    "reject": "close a record as rejected, with a reason",
    "archive": "move named terminal records into bugs_histo.jsonl",
    "check": "validate every BUGS.jsonl record",
}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="verb", required=True)
    for verb, help_text in _HELP.items():
        command = sub.add_parser(verb, help=help_text)
        command.add_argument("--specs", type=Path, default=None, help="path to the specs/ tree")
        if verb in ("update", *tr.REQUIRED_BY_VERB):
            command.add_argument(
                "bug_id", nargs="+" if verb == "update" else None, help="the record id to change"
            )
        for option in _OPTIONS.get(verb, ()):
            if option == "--correlates":
                command.add_argument(option, action="append", help=_CORRELATES)
            else:
                command.add_argument(option)
        if verb == "status":
            command.add_argument("--all", dest="include_closed", action="store_true")
        if verb == "update":
            command.add_argument(
                "--set", dest="sets", action="append", required=True, metavar="FIELD=VALUE"
            )
        if verb == "stats":
            command.add_argument("--closed-after", help="count what closed after this stamp")
            command.add_argument("--closed-until", help="count what closed up to this stamp")
        if verb == "archive":
            command.add_argument("bug_ids", nargs="+", help="the terminal records to move")
        if verb == "check":
            command.add_argument("--json", action="store_true", help="emit findings as JSON")
    return parser


def _ordinal(n: int) -> str:
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def _read(args: argparse.Namespace, specs: Path) -> int:
    records = read_records(specs / LEDGER)
    if args.verb == "stats":
        print(f"total\t{len(records)}")
        for label, values in (
            ("status", [r["status"] for r in records]),
            ("severity", [r["severity"] for r in records if r.get("severity")]),
        ):
            for value, count in sorted(Counter(values).items()):
                print(f"{label}:{value}\t{count}")
        past = history(specs)
        due = {path: list(m) for path, m in wr.by_file(past, specs.parent).items() if len(set(m.values())) > 1}  # fmt: skip
        for path, ids in due.items():
            print(f"rebuild-due:{path}\t{','.join(ids)}")
        if args.closed_after or args.closed_until:
            closed = [r for r in past if str(r.get("closed_at") or "") > (args.closed_after or "")
                      and (not args.closed_until or str(r["closed_at"]) <= args.closed_until)]  # fmt: skip
            shut = {str(r["id"]) for r in closed}
            print(f"closed\t{len(shut)}")
            print(f"fix-induced\t{sum(r.get('caused_by') not in (None, 'none') for r in closed)}")
            print(f"rebuild-due\t{len(shut & {i for v in due.values() for i in v})}")
        return 0
    selected = [r for r in records if args.include_closed or r.get("status") == OPEN]
    for record in sorted(selected, key=lambda r: str(r["id"])):
        print(f"{record['id']}\t{record['status']}\t{record.get('severity') or '-'}")
    print(f"[ok] {len(selected)} {'all' if args.include_closed else 'open'} bug(s).")
    return 0


def _archive(args: argparse.Namespace, specs: Path) -> int:
    kept = commit(
        specs / LEDGER,
        lambda records: wr.archive(records, args.bug_ids),
        archive=True,
    )
    print(f"[ok] archived {len(args.bug_ids)} record(s), {len(kept)} kept.")
    return 0


def _write(args: argparse.Namespace, specs: Path) -> int:
    ledger = specs / LEDGER
    if args.verb == "append":
        values = _jsonl.values(args, _OPTIONS["append"])
        values["id"] = values.pop("bug_id")
        values["ts"] = wr.now_iso()
        values["reported_by"] = values["reported_by"] or "dd-sw-engineer-sr"
        try:
            tracked = git(specs, "ls-files", "-z", "--full-name", ":/").split("\0")
        except (OSError, GitError) as exc:
            raise Refusal(
                f"cannot list the repo's tracked directories: {getattr(exc, 'stderr', exc)}",
                act("agent", "point --specs at a specs tree inside a git repo"),
            ) from None
        past = history(specs)
        fixed = wr.by_file(past, specs.parent)
        for path in wr.named_paths(values["component"], tracked):
            under = [m for p, m in fixed.items() if wr.under(p, path)]
            earlier = sorted({i for m in under for i in m})
            for bug in earlier:
                print(f"earlier bug on {path}: {bug}")
            if earlier:
                print(f"REBUILD due: {_ordinal(len({s for m in under for s in m.values()}) + 1)} bug on {path}")  # fmt: skip
        known = {str(r["id"]) for r in past}
        commit(
            ledger,
            lambda records: wr.append(records, values, tracked, known, archived_plain_ids(specs)),
        )
        print(f"[ok] registered {values['id']} -> {specs}")
        return 0
    if args.verb == "update":
        changes = wr.parse_set_options(args.sets)
        commit(
            ledger,
            lambda records: reduce(
                lambda rs, i: wr.apply_update(
                    rs, i, changes, {str(r["id"]) for r in history(specs)}
                ),
                args.bug_id,
                records,
            ),
        )
        print(f"[ok] updated {', '.join(sorted(changes))} for {', '.join(args.bug_id)}")
        return 0
    values = _jsonl.values(args, _OPTIONS[args.verb])
    if args.verb == "resolve" and (files := fix_files(specs.parent, [sha := values["fix_sha"]]).get(sha)):  # fmt: skip
        values["fix_files"] = files
    commit(ledger, lambda records: tr.transition(records, args.bug_id, args.verb, values))
    print(f"[ok] {STATUS_BY_VERB[args.verb]} {args.bug_id}")
    return 0


def main(argv: list[str] | None = None) -> int:
    use_utf8_stdio()
    args = _parser().parse_args(argv)
    reads = args.verb in ("check", "status", "stats")
    specs = find_specs(args.specs, ledger=None if reads else f"specs/{LEDGER}")
    if args.verb == "check":
        findings = check(specs)
        if args.json:
            print(json.dumps(findings, indent=2))
        else:
            _findings.print_text(findings)
        return 1 if findings else 0
    try:
        if args.verb in ("status", "stats"):
            return _read(args, specs)
        return _archive(args, specs) if args.verb == "archive" else _write(args, specs)
    except Refusal as refusal:
        return refuse(refusal, specs)
    except SymlinkRefusedError as exc:
        report(
            f"{exc} — nothing was written",
            act("agent", f"replace {exc.path} with a regular file holding its content"),
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
