#!/usr/bin/env python3
"""The bug ledger's ONE writer and validator — `specs/bugs/BUGS.jsonl`, stdlib only."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

import _bugs_transition as tr
import _bugs_write as wr
import _findings
import _jsonl
from _atomic import SymlinkRefusedError
from _bugs_check import LEDGER, OPEN, STATUS_BY_VERB, check
from _bugs_store import Refusal, archived_plain_ids, commit, history, read_records
from _git import GitError, fix_commit, git
from _platform import act, use_utf8_stdio
from _refusal import report
from _specs import context_repos, find_specs, refuse

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
    "resolve": ("--cause", "--caused-by", "--solution"),
    "supersede": ("--by",),
    "reject": ("--reason",),
}
_CORRELATES = "an earlier bug id; repeat the flag, or comma-separate the ids, or none"
_HELP = {
    "append": "register a brand-new open record",
    "status": "list records, open only by default",
    "stats": "aggregate counts by status and severity",
    "update": "write a governance field other than status/closed_at",
    "resolve": "close a record as resolved, with its cause and solution; its fix is the commit holding its fix(bugs) or refactor(bugs) id line",
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


def _due(
    past: list[dict[str, Any]], fixed: dict[str, dict[str, str]], repo: Path
) -> dict[str, list[str]]:
    """The ONE REBUILD-due decider over *fixed* (`by_file`'s paths): each path with a child, a fix whose bug's `caused_by` names an earlier fix of the path and that lands after the path's last REBUILD (a `refactor(bugs):` commit), -> the ids of those children and their causes. Fixes are ordered by *repo*'s log; a fix of another repo of the context sorts as the oldest."""
    log = git(repo, "log", "--format=%H%x00%s", check=False).splitlines()
    age = {ln.split("\0")[0]: len(log) - n for n, ln in enumerate(log)}
    rebuilt = {ln.split("\0")[0] for ln in log if ln.split("\0")[1].startswith("refactor(bugs):")}
    causes = {str(r["id"]): str(r.get("caused_by")) for r in past}
    due: dict[str, list[str]] = {}
    for path, fixes in fixed.items():
        last = max((age.get(s, 0) for s in fixes.values() if s in rebuilt), default=-1)
        kids = {
            b for b, s in fixes.items()
            if age.get(s, 0) > last and causes[b] in fixes and age.get(fixes[causes[b]], 0) < age.get(s, 0)
        }  # fmt: skip
        if kids:
            due[path] = sorted(kids | {causes[b] for b in kids})
    return due


def _read(args: argparse.Namespace, specs: Path) -> int:
    records = read_records(specs / LEDGER)
    if args.verb == "stats":
        _stats(args, records, specs)
        return 0
    selected = [r for r in records if args.include_closed or r.get("status") == OPEN]
    for record in sorted(selected, key=lambda r: str(r["id"])):
        print(f"{record['id']}\t{record['status']}\t{record.get('severity') or '-'}")
    print(f"[ok] {len(selected)} {'all' if args.include_closed else 'open'} bug(s).")
    return 0


def _stats(args: argparse.Namespace, records: list[dict[str, Any]], specs: Path) -> None:
    print(f"total\t{len(records)}")
    for label, values in (
        ("status", [r["status"] for r in records]),
        ("severity", [r["severity"] for r in records if r.get("severity")]),
    ):
        for value, count in sorted(Counter(values).items()):
            print(f"{label}:{value}\t{count}")
    past = history(specs)
    due = _due(past, wr.by_file(past, specs.parent), specs.parent)
    for path, ids in due.items():
        print(f"rebuild-due:{path}\t{','.join(ids)}")
    if args.closed_after or args.closed_until:
        _closed_window(past, due, args.closed_after, args.closed_until)


def _closed_window(
    past: list[dict[str, Any]], due: dict[str, list[str]], after: str | None, until: str | None
) -> None:
    closed = [r for r in past if str(r.get("closed_at") or "") > (after or "")
              and (not until or str(r["closed_at"]) <= until)]  # fmt: skip
    shut = {str(r["id"]) for r in closed}
    print(f"closed\t{len(shut)}")
    print(f"fix-induced\t{sum(r.get('caused_by') not in (None, 'none') for r in closed)}")
    print(f"rebuild-due\t{len(shut & {i for v in due.values() for i in v})}")


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
        due = _due(past, fixed, specs.parent)
        for path in wr.named_paths(values["component"], tracked):
            under = [m for p, m in fixed.items() if wr.under(p, path)]
            for bug in sorted({i for m in under for i in m}):
                print(f"earlier bug on {path}: {bug}")
            if any(wr.under(p, path) for p in due):
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
            lambda records: wr.apply_update(
                records, args.bug_id, changes, {str(r["id"]) for r in history(specs)}
            ),
        )
        print(f"[ok] updated {', '.join(sorted(changes))} for {args.bug_id}")
        return 0
    values = _jsonl.values(args, _OPTIONS[args.verb])
    if args.verb == "resolve":
        found = fix_commit(context_repos(specs.parent), [args.bug_id])
        if args.bug_id not in found:
            raise Refusal(
                f"no commit of HEAD holds the line `fix(bugs): {args.bug_id} — …` or `refactor(bugs): {args.bug_id} — …`",
                act("agent", f"commit the fix with the line `fix(bugs): {args.bug_id} — …`, or `refactor(bugs): {args.bug_id} — REBUILD <unit>: …` when its caused_by names a culprit, in its message, then resolve again"),
            )  # fmt: skip
        _, sha = found[args.bug_id]
        values["fix_sha"] = sha
    commit(ledger, lambda records: tr.transition(records, args.bug_id, args.verb, values, specs))
    print(f"[ok] {STATUS_BY_VERB[args.verb]} {args.bug_id}")
    return 0


def main(argv: list[str] | None = None) -> int:
    use_utf8_stdio()
    args = _parser().parse_args(argv)
    reads = args.verb in ("check", "status", "stats")
    specs = find_specs(args.specs, ledger=None if reads else f"specs/{LEDGER}")
    try:
        if args.verb == "check":
            return _findings.run_check(check(specs), as_json=args.json)
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
