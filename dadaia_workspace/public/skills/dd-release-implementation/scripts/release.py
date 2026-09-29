#!/usr/bin/env python3
"""The release ledger's ONE writer and validator — `_RELEASE.json`, the candidate trio and
the ship ledger, stdlib only. Every write is validated by `check` before an atomic
replace; `ship` records the merged promote PR (git is the archive).
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

# No `__pycache__` beside a projected skill; `_ledger.py` is staged beside this script
# (the source tree keeps it in dd-bug-resolution).
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.append(str(Path(__file__).resolve().parents[2] / "dd-bug-resolution" / "scripts"))

from _release_check import histo_findings  # noqa: E402
from _release_new import new_release  # noqa: E402
from _release_phase import set_phase  # noqa: E402
from _release_schema import CODE, HISTO, SHA_RE, STATE, utc_now  # noqa: E402
from _release_store import Refusal, commit, live_release, window_start  # noqa: E402
from _release_tree import check, drift, memory_errors  # noqa: E402
from _specs import find_specs, refuse  # noqa: E402

_HELP = {
    "new": "mint the one live release: its SPEC.md stub and _RELEASE.json, in one act",
    "phase": "move the live release to IMPLEMENTATION or CLOSURE, stamping its milestone",
    "drift": "the closure worklist over the live release's memory window (memory.py drift)",
    "memory": "append the closure's one structured `kind: memory` entry to the live log",
    "ship": "record the merged promote PR: shipped, a delivered histo line, the dir removed",
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
        if verb in ("phase", "ship"):
            command.add_argument("--sha", required=True, help="the commit the milestone names")
        if verb == "ship":
            command.add_argument("--pr", required=True, help="the merged promote PR number")
        if verb == "memory":
            for name in ("--reviewed", "--changed"):
                command.add_argument(name, default="", help="comma-separated worklist entries")
        if verb in ("check", "drift"):
            command.add_argument("--json", action="store_true", help="emit findings as JSON")
    return parser


def _new(args: argparse.Namespace, specs: Path) -> int:
    release_dir = new_release(specs, args.release_id, utc_now()[:10], args.origin)
    print(f"[ok] created: {release_dir / 'SPEC.md'}\n[ok] created: {release_dir / STATE}")
    return 0


def _phase(args: argparse.Namespace, specs: Path) -> int:
    release_id, ts = set_phase(specs, args.phase.upper(), args.sha)
    print(f"[ok] release {release_id} -> phase {args.phase.upper()} ({ts})")
    return 0


def _drift(args: argparse.Namespace, specs: Path) -> int:
    """The worklist over the window `memory` records: last memory entry's until, else defined.sha."""
    report = drift.report(specs, window_start(live_release(specs).state))
    print(json.dumps(report, indent=2) if args.json else drift.render(report))
    return 1 if report["atoms"] or report["uncovered"] else 0


def _memory(args: argparse.Namespace, specs: Path) -> int:
    """Append the record over the ledger-derived window, refused unless its worklist was worked."""
    live, ts = live_release(specs), utc_now()
    since = window_start(live.state)
    lists = [[s for s in getattr(args, n).split(",") if s] for n in ("reviewed", "changed")]
    try:
        until = drift.git(specs.parent, "rev-parse", "HEAD")[0]
        entry = {"ts": ts, "agent": "release.py memory", "kind": "memory",
                 "text": f"Memory reconciled over {since}..{until[:12]}: {len(lists[0])} "
                 f"reviewed, {len(lists[1])} changed.", "since": since, "until": until,
                 "reviewed": lists[0], "changed": lists[1]}  # fmt: skip
        errors = memory_errors(specs, str(live.state.get("phase")), entry)
    except drift.Refusal as refusal:
        raise Refusal(str(refusal), refusal.fix) from refusal
    if errors:
        raise Refusal(errors[0], f"{Path(__file__)} memory --help")
    commit(live.release_dir / STATE, f"releases/{live.release_id}/{STATE}",
           lambda state: {**state, "log": [*(state.get("log") or []), entry]})  # fmt: skip
    print(f"[ok] release {live.release_id} log <- kind memory {since}..{until[:12]} ({ts})")
    return 0


def _ship(args: argparse.Namespace, specs: Path) -> int:
    """CLOSURE -> shipped {sha, pr, ts}, one `delivered` histo line, the directory gone."""
    live, ts, fix = live_release(specs), utc_now(), f"{Path(__file__)} check"
    if not (SHA_RE.match(args.sha) and args.pr.isdigit() and int(args.pr) > 0):
        raise Refusal(f"--sha {args.sha!r} / --pr {args.pr!r}: a hex sha and a PR number",
                      f"{Path(__file__)} ship --sha $(git rev-parse --short HEAD) --pr <n>")  # fmt: skip
    if live.state.get("phase") != "CLOSURE":
        raise Refusal(f"release {live.release_id} is in phase {live.state.get('phase')!r} — "
                      "only a CLOSURE release ships", fix)  # fmt: skip
    line = json.dumps({"id": live.release_id, "ts": ts, "disposition": "delivered",
                       "release": live.release_id, "reason": None, "entry": None,
                       "summary": f"shipped {args.sha} PR #{args.pr}"}) + "\n"  # fmt: skip
    histo = specs / HISTO
    if errors := histo_findings((histo.read_text("utf-8") if histo.is_file() else "") + line):
        raise Refusal(f"the ship ledger would not pass check: {errors[-1]['message']}", fix)
    commit(live.release_dir / STATE, f"releases/{live.release_id}/{STATE}",
           lambda s: {**s, "shipped": {"sha": args.sha, "pr": int(args.pr), "ts": ts}})  # fmt: skip
    with histo.open("a", encoding="utf-8") as ledger:
        ledger.write(line)
    shutil.rmtree(live.release_dir)
    print(f"[ok] release {live.release_id} shipped at {args.sha} (PR #{args.pr})")
    return 0


_VERBS = {"new": _new, "phase": _phase, "drift": _drift, "memory": _memory, "ship": _ship}


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    specs = find_specs(args.specs)
    if args.verb == "check":
        findings = check(specs)
        print(json.dumps(findings, indent=2)) if args.json else [
            print(f"{CODE} error {f['path']}:{f['line']} {f['message']}") for f in findings
        ]
        return 1 if findings else 0
    try:
        return _VERBS[args.verb](args, specs)
    except (Refusal, drift.Refusal) as refusal:
        return refuse(refusal, specs)


if __name__ == "__main__":
    raise SystemExit(main())
