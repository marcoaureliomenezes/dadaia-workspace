#!/usr/bin/env python3
"""The bug ledger's ONE writer and validator — `specs/bugs/BUGS.jsonl`, stdlib only."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.append(str(Path(__file__).resolve().parents[2] / "dd-release-implementation" / "scripts"))

import _bugs_transition as tr  # noqa: E402
import _bugs_write as wr  # noqa: E402
from _bugs_check import CODE, LEDGER, check  # noqa: E402
from _bugs_store import Refusal, commit, read_records  # noqa: E402
from _specs import find_specs, refuse  # noqa: E402

_OPTIONS: dict[str, tuple[str, ...]] = {
    "append": (
        "--bug-id",
        "--reported-by",
        "--ts",
        "--title",
        "--severity",
        "--surface",
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
            command.add_argument("bug_id", help="the record id to change")
        for option in _OPTIONS.get(verb, ()):
            command.add_argument(option)
        if verb == "status":
            command.add_argument("--all", dest="include_closed", action="store_true")
        if verb == "update":
            command.add_argument(
                "--set", dest="sets", action="append", required=True, metavar="FIELD=VALUE"
            )
        if verb == "archive":
            command.add_argument("bug_ids", nargs="+", help="the terminal records to move")
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
        for label, values in (
            ("status", [r["status"] for r in records]),
            ("severity", [r["severity"] for r in records if r.get("severity")]),
        ):
            for value, count in sorted(Counter(values).items()):
                print(f"{label}:{value}\t{count}")
        return 0
    selected = [r for r in records if args.include_closed or r.get("status") == "open"]
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
        values = _values(args, _OPTIONS["append"])
        values["id"] = values.pop("bug_id")
        values["ts"] = values["ts"] or wr.now_iso()
        values["reported_by"] = values["reported_by"] or "dd-software-engineer"
        try:
            listed = subprocess.run(
                ["git", "-C", str(specs), "ls-files", "--full-name", ":/"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=True,
            ).stdout
        except (OSError, subprocess.CalledProcessError) as exc:
            cause = getattr(exc, "stderr", "") or str(exc)
            raise Refusal(
                f"cannot list the repo's tracked directories: {cause.strip()}",
                "Operator action: point --specs at a specs tree inside a git repo",
            ) from None
        dirs = {part for path in listed.splitlines() for part in path.split("/")[:-1]}
        near = wr.candidates(read_records(ledger), values["surface"])
        print(f"correlation candidates on {values['surface']!r}: {', '.join(near) or 'none'}")
        commit(ledger, lambda records: wr.append(records, values, dirs))
        print(f"[ok] registered {values['id']} -> {specs}")
        return 0
    if args.verb == "update":
        changes = wr.parse_set_options(args.sets)
        commit(ledger, lambda records: wr.apply_update(records, args.bug_id, changes))
        print(f"[ok] updated {', '.join(sorted(changes))} for {args.bug_id}")
        return 0
    values = _values(args, _OPTIONS[args.verb])
    commit(ledger, lambda records: tr.transition(records, args.bug_id, args.verb, values))
    print(f"[ok] {tr.STATUS_BY_VERB[args.verb]} {args.bug_id}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    reads = args.verb in ("check", "status", "stats")
    specs = find_specs(args.specs, ledger=None if reads else f"specs/{LEDGER}")
    if args.verb == "check":
        findings = check(specs)
        if args.json:
            print(json.dumps(findings, indent=2))
        else:
            for finding in findings:
                print(f"{CODE} error {finding['path']}:{finding['line']} {finding['message']}")
        return 1 if findings else 0
    try:
        if args.verb in ("status", "stats"):
            return _read(args, specs)
        return _archive(args, specs) if args.verb == "archive" else _write(args, specs)
    except Refusal as refusal:
        return refuse(refusal, specs)


if __name__ == "__main__":
    raise SystemExit(main())
