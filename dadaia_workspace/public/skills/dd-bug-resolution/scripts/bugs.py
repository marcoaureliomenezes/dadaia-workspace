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
import re
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

# A projected skill folder is not a package dir to litter: the sibling modules below
# import without leaving a `__pycache__` beside them.
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

import _bugs_transition as tr  # noqa: E402
import _bugs_write as wr  # noqa: E402
from _bugs_check import CODE, LEDGER, check  # noqa: E402
from _bugs_store import Refusal, commit, read_records  # noqa: E402
from _specs import find_specs, refuse  # noqa: E402

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
    "archive": "move long-closed terminal records into bugs_histo.jsonl",
    "check": "validate every BUGS.jsonl record",
    "fix": "derive each resolved record's fix commit, numstat and direction",
}
#: Shapes 3 and 4 share one id list; shape 4 names its task commit(s) as `(<sha>[, <sha>])` (ADR 0164 (1)).
_SHAPE = re.compile(r"@(\w+) (fix\(bugs\): |chore\(bugs\): resolve )(.+?) — (.*)$")
_TASK_SHAS = re.compile(r"\((\w+(?:, \w+)*)\)$")
#: Never a fix's own lines: tests (metric 6) and specs; `_own` adds the generated files.
_NOT_PRODUCTION = ("tests/", "specs/")


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
        if verb == "fix":
            command.add_argument("bug_ids", nargs="*", help="default: every resolved record")
        if verb == "check":
            command.add_argument("--json", action="store_true", help="emit findings as JSON")
    return parser


def _values(args: argparse.Namespace, names: tuple[str, ...]) -> dict[str, Any]:
    keys = [name.lstrip("-").replace("-", "_") for name in names]
    return {key: getattr(args, key) for key in keys}


def _fixes(specs: Path) -> dict[str, dict[str, list[list[str]] | None]]:
    """Bug id -> {fix sha: numstat rows}, grepped from history, never stored; a shape-4
    task commit is counted, never diffed (rows None)."""
    git = ["git", "-C", str(specs)]
    head = subprocess.run([*git, "rev-parse", "-q", "--verify", "HEAD"], stdout=subprocess.DEVNULL, check=False)  # fmt: skip
    if head.returncode == 1:  # a repo with no commit yet links nothing
        return {}
    log = subprocess.run([*git, "log", "-E", r"--grep=^(fix|chore)\(bugs\): ", "--numstat", "--format=@%H %s"],
                         stdout=subprocess.PIPE, text=True, check=False)  # fmt: skip
    if log.returncode:
        raise Refusal("cannot read the repo's history", "Operator action: point --specs at a specs tree inside a git repo")  # fmt: skip
    found: dict[str, dict[str, list[list[str]] | None]] = {}
    rows: list[list[str]] = []
    for line in log.stdout.splitlines():
        if not line.startswith("@"):
            rows += [line.split("\t")] if line else []
            continue
        rows, shape = [], _SHAPE.match(line)
        task = _TASK_SHAS.search(shape[4]) if shape and shape[2].startswith("chore") else None
        if shape is None or (task is None and shape[2].startswith("chore")):
            continue
        for bug in shape[3].split(", "):
            for sha in task[1].split(", ") if task else [shape[1]]:
                found.setdefault(bug, {})[sha] = None if task else rows
    return found


def _git(cwd: Path | str, *argv: str, stdin: str | None = None) -> str:
    return subprocess.run(["git", "-c", "core.quotePath=false", "-C", str(cwd), *argv], input=stdin, capture_output=True, encoding="utf-8",
                          errors="replace", check=True).stdout  # fmt: skip


def _own(specs: Path, paths: set[str]) -> set[str]:
    """The paths a fix writes: not tests (metric 6), not specs, not a file `.gitattributes`
    marks `dadaia-generated` (ADR 0183) — one predicate for the blame and the direction."""
    top = _git(specs, "rev-parse", "--show-toplevel").strip()
    out = _git(top, "check-attr", "--stdin", "dadaia-generated", stdin="\n".join(paths))
    generated = {path for path, _, value in (ln.rsplit(": ", 2) for ln in out.splitlines()) if value in ("set", "true")}  # fmt: skip
    return {p for p in paths if not p.startswith(_NOT_PRODUCTION)} - generated


def _candidates(specs: Path, bug_id: str) -> list[str]:
    """The bugs whose fix wrote a line the staged diff removes: `git blame` past `(#n)`-subject
    squashes and `refactor(T-…)` commits, over `_own` paths only (ADR 0164 (2))."""
    fixes, blamed = _fixes(specs), set[str]()
    if not fixes:
        return []
    top = Path(_git(specs, "rev-parse", "--show-toplevel").strip())
    staged = {f[1]: f[1:] for f in (ln.split("\t") for ln in _git(top, "diff", "--cached", "--name-status", "--diff-filter=MDR").splitlines())}  # fmt: skip
    subjects = (ln.partition(" ") for ln in _git(top, "log", "--format=%H %s").splitlines())
    skip = [h for h, _, s in subjects if re.search(r"\(#\d+\)$", s) or s.startswith("refactor(T-")]
    with tempfile.TemporaryDirectory() as tmp:
        (revs := Path(tmp) / "revs").write_text("\n".join(skip), encoding="utf-8")
        for path in _own(top, set(staged)):  # a rename is blamed at its old path
            hunks = [ln.split()[1][1:].partition(",") for ln in _git(top, "diff", "--cached", "-U0", "--", *staged[path]).splitlines() if ln.startswith("@@ ")]  # fmt: skip
            ranges = [arg for start, _, n in hunks if n != "0" for arg in ("-L", f"{start},+{n or 1}")]  # fmt: skip
            blame = _git(top, "blame", "--porcelain", "--ignore-revs-file", str(revs), *ranges, "HEAD", "--", path) if ranges else ""  # fmt: skip
            blamed |= {ln[:40] for ln in blame.splitlines()}
    return sorted({bug for bug, shas in fixes.items() for sha in shas for b in blamed if b.startswith(sha)} - {bug_id})  # fmt: skip


def _direction(commits: dict[str, list[list[str]] | None], own: set[str]) -> str:
    if all(rs is None for rs in commits.values()):
        return "-"
    rows = [r for rs in commits.values() for r in rs or []]
    net = sum(
        int(a) - int(d) for a, d, path in rows
        if a != "-" and path in own
    )  # fmt: skip
    return "net-negative" if net < 0 else "net-positive" if net > 0 else "net-neutral"


def _read(args: argparse.Namespace, specs: Path) -> int:
    records = read_records(specs / LEDGER)
    fixes = _fixes(specs) if args.verb in ("fix", "stats") else {}
    own = _own(specs, {r[2] for c in fixes.values() for rs in c.values() for r in rs or []}) if fixes else set()  # fmt: skip
    if args.verb == "fix":
        ids = args.bug_ids or [str(r["id"]) for r in records if r["status"] == "resolved"]
        for bug in ids:
            commits = fixes.get(bug, {})
            print(f"{bug}\t{','.join(commits)}\t{_direction(commits, own)}" if commits else f"{bug}\tunlinked")  # fmt: skip
            for row in (r for rows in commits.values() for r in rows or []):
                print("\t" + "\t".join(row))
        linked = sum(b in fixes for b in ids)
        print(f"[ok] {linked} linked, {len(ids) - linked} unlinked.")
        return 0
    if args.verb == "stats":
        print(f"total\t{len(records)}")
        directions = [_direction(fixes[r["id"]], own) for r in records if r["id"] in fixes]
        for label, values in (
            ("status", [r["status"] for r in records]),
            ("severity", [r["severity"] for r in records if r.get("severity")]),
            ("direction", [d for d in directions if d != "-"]),
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
    moment = _dt.datetime.fromisoformat(args.now.replace("Z", "+00:00")) if args.now else None
    cutoff = (moment or _dt.datetime.now(tz=_dt.UTC)) - _dt.timedelta(days=args.threshold_days)
    ledger = specs / LEDGER
    moving = wr.archivable(read_records(ledger), cutoff.strftime("%Y-%m-%dT%H:%M:%SZ"))
    if moving:
        kept = commit(ledger, lambda rs: [r for r in rs if r["id"] not in moving], archive=True)  # fmt: skip
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
        try:
            listed = subprocess.run(["git", "-C", str(specs), "ls-files", "--full-name", ":/"],
                                    capture_output=True, text=True, check=True).stdout  # fmt: skip
        except (OSError, subprocess.CalledProcessError) as exc:
            cause = getattr(exc, "stderr", "") or str(exc)
            raise Refusal(f"cannot list the repo's tracked directories: {cause.strip()}",
                          "Operator action: point --specs at a specs tree inside a git repo") from None  # fmt: skip
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
    near = _candidates(specs, args.bug_id) if args.verb == "resolve" else []
    if near:
        print(f"blame candidates: {', '.join(near)}")
    commit(ledger, lambda rs: tr.transition(rs, args.bug_id, args.verb, values, near))
    print(f"[ok] {tr.STATUS_BY_VERB[args.verb]} {args.bug_id}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    reads = args.verb in ("check", "status", "stats", "fix")
    specs = find_specs(args.specs, ledger=None if reads else f"specs/{LEDGER}")
    if args.verb == "check":
        findings = check(specs)
        print(json.dumps(findings, indent=2)) if args.json else [
            print(f"{CODE} error {LEDGER}:{f['line']} {f['message']}") for f in findings
        ]
        return 1 if findings else 0
    try:
        if args.verb in ("status", "stats", "fix"):
            return _read(args, specs)
        return _archive(args, specs) if args.verb == "archive" else _write(args, specs)
    except Refusal as refusal:
        return refuse(refusal, specs)


if __name__ == "__main__":
    raise SystemExit(main())
