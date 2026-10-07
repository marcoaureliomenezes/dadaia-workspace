#!/usr/bin/env python3
"""The bug ledger's ONE writer and validator — `specs/bugs/BUGS.jsonl`, stdlib only.

``bugs.py <verb> --specs <path>``. Every write builds the new ledger bytes, runs
`check` over them, and only then replaces the file atomically — so this script's writer
and its validator cannot disagree about what a valid record is. `append`, `resolve` and
`window` read which candidate held an instant from `dd-release-implementation`'s
`_release_schema.candidate_at`, a skill-level dependency as `_specs` has on
`dd-gitflow-default`.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

# A projected skill folder is not a package dir to litter: the sibling modules below
# import without leaving a `__pycache__` beside them.
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.append(str(Path(__file__).resolve().parents[2] / "dd-release-implementation" / "scripts"))

import _bugs_fix as fx  # noqa: E402
import _bugs_quality as qa  # noqa: E402
import _bugs_transition as tr  # noqa: E402
import _bugs_write as wr  # noqa: E402
from _bugs_check import CODE, HISTO, LEDGER, accepted_adrs, check, tasks  # noqa: E402
from _bugs_fix import git as _git  # noqa: E402
from _bugs_store import Refusal, commit, read_records  # noqa: E402
from _release_schema import (  # noqa: E402
    ShallowClone,
    Unreadable,
    candidate_adds,
    candidate_at,
    live_id,
    releases,
)
from _specs import find_specs, git_line, refuse, script  # noqa: E402

_OPTIONS: dict[str, tuple[str, ...]] = {
    "append": ("--bug-id", "--reported-by", "--ts", "--title", "--severity", "--surface",
               "--component", "--context", "--symptom", "--repro", "--expected", "--correlates"),
    "resolve": (*(f"--{name.replace('_', '-')}" for name in tr.REQUIRED_BY_VERB["resolve"]), "--lineage-reason"),
    "supersede": ("--by",), "defer": ("--reason",), "reject": ("--reason",),
}  # fmt: skip
_HELP = {
    "append": "register a brand-new open record",
    "status": "list records, open only by default",
    "stats": "aggregate counts by status and by severity",
    "update": "write a governance field other than status/closed_at",
    "resolve": "close a record as resolved, with its lineage and red loop",
    "supersede": "close a record as superseded by another slug",
    "defer": "close a record as deferred, with a reason",
    "reject": "close a record as rejected, with a reason",
    "archive": "move named terminal records into bugs_histo.jsonl under an accepted ADR",
    "check": "validate every BUGS.jsonl record",
    "fix": "derive each resolved record's fix commits, numstat, direction, rework and settledness",
    "window": "list the records found in or born in the live or the last shipped release",
    "balance": "print QUALITY.md's `## Bugs` block from the ledger; --write or --check it there",
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
            command.add_argument("--found-in", metavar="RELEASE/RC", help="refuse while a record found there is open or deferred")  # fmt: skip
        if verb == "update":
            command.add_argument("--set", dest="sets", action="append", required=True,
                                 metavar="FIELD=VALUE", help="a 'field=value' pair (repeatable)")  # fmt: skip
        if verb == "archive":
            command.add_argument("--adr", required=True, help="the accepted ADR moving them")
            command.add_argument("bug_ids", nargs="+", help="the terminal records to move")
        if verb == "fix":
            command.add_argument("bug_ids", nargs="*", help="default: every resolved record")
        if verb == "balance":
            command.add_argument("--write", action="store_true", help="rewrite the block in place")
            command.add_argument("--check", action="store_true", help="refuse a stale block")
        if verb == "check":
            command.add_argument("--json", action="store_true", help="emit findings as JSON")
    return parser


def _values(args: argparse.Namespace, names: tuple[str, ...]) -> dict[str, Any]:
    keys = [name.lstrip("-").replace("-", "_") for name in names]
    return {key: getattr(args, key) for key in keys}


def _candidates(specs: Path, bug_id: str) -> list[str]:
    """The bugs whose fix, and the tasks whose `<type>(<task-id>)` commit, wrote a line the
    staged diff removes: `git blame` past `(#n)`-subject squashes, `tests/` included."""
    fixes = fx.fixes(specs)
    top = Path(_git(specs, "rev-parse", "--show-toplevel").strip())
    subjects = fx.subjects(top)
    blamed = fx.removed(top, ("--cached",), "HEAD", subjects, ("specs/",))
    # check's one answer to "what is a task": never propose a task check refuses
    known = tasks(specs)
    named = {m[1] for b in blamed if (m := re.match(r"\w+\(([^)]+)\)", subjects.get(b, ""))) and m[1] in known}  # fmt: skip
    return sorted(
        ({bug for bug, fix in fixes.items() if blamed & set(fix.commits)} | named) - {bug_id}
    )


def _placed[T](read: Callable[[], T], specs: Path) -> T:
    """One release read, its refusal carried over with its act (and choice) intact."""
    try:
        return read()
    except ShallowClone as exc:
        raise Refusal(str(exc), git_line(specs, "fetch", "--unshallow")) from None
    except Unreadable as exc:
        vars(refusal := Refusal(*exc.args)).update(vars(exc))  # the act's choice, if any
        raise refusal from None


def _tracked(specs: Path, path: str) -> str | None:
    """The text git tracks at *path* (repo-relative, from the index), None when untracked."""
    try:
        return _git(_git(specs, "rev-parse", "--show-toplevel").strip(), "show", f":{path}")
    except subprocess.CalledProcessError:
        return None


def _held_at(specs: Path, instant: str) -> dict[str, str]:
    return _placed(lambda: candidate_at(specs, instant), specs)


def _culprits(cause: object, fixes: dict[str, fx.Fix], tasks: dict[str, list[str]]) -> list[str]:
    """The commits of the bug fix or task a record's `caused_by` names, newest first."""
    if cause in (None, "none"):
        return []
    return list(fixes[str(cause)].commits) if cause in fixes else tasks.get(str(cause), [])[::-1]


def _window_keys(specs: Path) -> list[str]:
    """The live release and the last shipped one, read after a shallow clone is refused."""
    live = _placed(lambda: live_id(specs), specs)
    _held_at(specs, wr.now_iso())
    shipped = sorted((end, r) for r, (_, end) in releases(specs).items() if end)
    return sorted({live, *(r for _, r in shipped[-1:])})


def _window(specs: Path) -> int:
    """Every live and archived record found in or born in the live or the last shipped
    release; a `release` `unknown` one apart (AC13.3). `introduced_in` is read from
    `caused_by`'s culprit, its oldest fix or `<type>(<task-id>)` commit, else stored."""
    keys = _window_keys(specs)
    fixes, tasks, rows, apart = fx.fixes(specs), fx.tasked(specs), [], []
    # --all: a repo with no commit yet lists nothing instead of failing
    when = dict(ln.split(" ", 1) for ln in _git(specs, "log", "--all", "--format=%H %cI").splitlines())  # fmt: skip
    tracked = set(_git(specs, "ls-files", "--full-name", ":/").splitlines())
    for record in [*read_records(specs / LEDGER), *(r for r in read_records(specs / HISTO) if "id" in r)]:  # fmt: skip
        shas = _culprits(record.get("caused_by"), fixes, tasks)
        culprit = when.get(shas[-1]) if shas else None
        found, born = record.get("found_in"), _held_at(specs, culprit) if culprit else record.get("introduced_in")  # fmt: skip
        seen = [c for c in (found, born) if c]
        cells = (f"{c['release']}/{c['rc']}" if c else "-" for c in (found, born))
        seam = str(record.get("evidence_seam") or "").split("::")[0]
        line = "\t".join((record["id"], record["status"], *cells, *(["seam gone"] if seam and seam not in tracked else [])))  # fmt: skip
        if any(c["release"] in keys for c in seen):
            rows.append(line)
        elif any(c["release"] == "unknown" for c in seen):
            apart.append(line)
    print(*sorted(rows), "release unknown:", *sorted(apart), sep="\n")
    print(f"[ok] {len(rows)} in the window ({', '.join(keys)}), {len(apart)} release unknown.")
    return 0


def _balance(args: argparse.Namespace, specs: Path) -> int:
    """Print the block, rewrite it (`--write`) or judge it (`--check`); whatever the ledgers,
    the release log or git cannot give is one refusal, here and nowhere deeper."""
    me = script(Path(__file__))
    try:
        if args.write:
            print(f"[ok] wrote the `## Bugs` block of {_placed(lambda: qa.write(specs), specs)}")
        elif args.check:
            if _placed(lambda: qa.stale(specs), specs):
                why = "the `## Bugs` block differs from its regeneration"
                raise Refusal(why, f"{me} balance --write")
        else:
            print(_placed(lambda: qa.body(specs), specs), end="")
    except (LookupError, TypeError, ValueError, OSError, subprocess.CalledProcessError) as error:
        raise Refusal(f"cannot render the bug balance: {error}", f"{me} check") from None
    return 0


def _read(args: argparse.Namespace, specs: Path) -> int:
    records = read_records(specs / LEDGER)
    fixes = fx.fixes(specs) if args.verb in ("fix", "stats") else {}
    if args.verb == "fix":
        ids = args.bug_ids or [str(r["id"]) for r in records if r["status"] == "resolved"]
        born = [t.timestamp() for t, _, _ in _placed(lambda: candidate_adds(specs), specs)]
        for bug in ids:
            if (fix := fixes.get(bug)) is None:
                print(f"{bug}\tunlinked")
                continue
            print(f"{bug}\t{','.join(fix.commits)}\t{fx.direction(fix)}")
            for row in (r for rows in fix.commits.values() for r in rows):
                print("\t" + "\t".join(row))
            rework, last = fix.rework()
            if rework:
                print(f"\trework\t{rework['planned']} planned, {rework['overfitting']} overfitting")
            if born:  # Terms: settled once 2 candidates were born with the surface untouched
                untouched = sum(t > last for t in born)
                print(
                    f"\t{'settled' if untouched >= 2 else 'unsettled'}\t{untouched} rcs untouched"
                )
        linked = sum(b in fixes for b in ids)
        print(f"[ok] {linked} linked, {len(ids) - linked} unlinked.")
        return 0
    if args.verb == "stats":
        print(f"total\t{len(records)}")
        directions = [fx.direction(fixes[r["id"]]) for r in records if r["id"] in fixes]
        for label, values in (
            ("status", [r["status"] for r in records]),
            ("severity", [r["severity"] for r in records if r.get("severity")]),
            ("direction", directions),
        ):
            for value, count in sorted(Counter(values).items()):
                print(f"{label}:{value}\t{count}")
        return 0
    if args.found_in:  # the one reader of found_in x status
        release, _, rc = args.found_in.partition("/")
        for bug in records:
            if bug.get("status") in ("open", "deferred") and bug.get("found_in") == {"release": release, "rc": rc}:  # fmt: skip
                raise Refusal(f"{rc} of release {release} holds {bug['status']} bug {bug['id']}", f"Operator action: resolve {bug['id']} in {rc}'s bug batch")  # fmt: skip
        return 0
    selected = [r for r in records if args.include_closed or r.get("status") == "open"]
    for record in sorted(selected, key=lambda r: str(r["id"])):
        print(f"{record['id']}\t{record['status']}\t{record.get('severity') or '-'}")
    print(f"[ok] {len(selected)} {'all' if args.include_closed else 'open'} bug(s).")
    return 0


def _archive(args: argparse.Namespace, specs: Path) -> int:
    accepted = accepted_adrs(specs)
    kept = commit(specs / LEDGER, lambda rs: wr.archive(rs, args.bug_ids, args.adr, accepted), archive=True)  # fmt: skip
    print(f"[ok] archived {len(args.bug_ids)} record(s) by ADR {args.adr}, {len(kept)} kept.")
    return 0


def _write(args: argparse.Namespace, specs: Path) -> int:
    ledger = specs / LEDGER
    if args.verb == "append":
        values = _values(args, _OPTIONS["append"])
        values["id"] = values.pop("bug_id")
        values["ts"] = values["ts"] or wr.now_iso()
        values["reported_by"] = values["reported_by"] or "dd-software-engineer"
        try:
            listed = subprocess.run(["git", "-C", str(specs), "ls-files", "--full-name", ":/"],
                                    capture_output=True, text=True, check=True).stdout  # fmt: skip
        except (OSError, subprocess.CalledProcessError) as exc:
            cause = getattr(exc, "stderr", "") or str(exc)
            raise Refusal(f"cannot list the repo's tracked directories: {cause.strip()}",
                          "Operator action: point --specs at a specs tree inside a git repo") from None  # fmt: skip
        dirs = {part for path in listed.splitlines() for part in path.split("/")[:-1]}
        try:
            values["found_in"] = _held_at(specs, values["ts"])
        except ValueError:  # a bad --ts: the schema check below names it
            values["found_in"] = None
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
    if args.verb == "resolve":
        values["resolved_release"] = _held_at(specs, wr.now_iso())["release"]
    near = _candidates(specs, args.bug_id) if args.verb == "resolve" else []
    if near:
        print(f"blame candidates: {', '.join(near)}")
    commit(ledger, lambda rs: tr.transition(rs, args.bug_id, args.verb, values, near, lambda p: _tracked(specs, p)))  # fmt: skip
    print(f"[ok] {tr.STATUS_BY_VERB[args.verb]} {args.bug_id}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    reads = args.verb in ("check", "status", "stats", "fix", "window", "balance")
    specs = find_specs(args.specs, ledger=None if reads else f"specs/{LEDGER}")
    if args.verb == "check":
        findings = check(specs)
        print(json.dumps(findings, indent=2)) if args.json else [
            print(f"{CODE} error {f['path']}:{f['line']} {f['message']}") for f in findings
        ]
        return 1 if findings else 0
    try:
        if args.verb in ("status", "stats", "fix"):
            return _read(args, specs)
        if args.verb == "window":
            return _window(specs)
        if args.verb == "balance":
            return _balance(args, specs)
        return _archive(args, specs) if args.verb == "archive" else _write(args, specs)
    except Refusal as refusal:
        return refuse(refusal, specs)


if __name__ == "__main__":
    raise SystemExit(main())
