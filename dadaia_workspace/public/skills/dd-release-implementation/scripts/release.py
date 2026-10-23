#!/usr/bin/env python3
"""Validate and write a release's `_RELEASE.json` and SPEC stub, stdlib only.

Also validates the candidate's SPEC/PLAN/job files and the ship ledger. Every write is validated by `check`
before an atomic replace; `ship` records the merged promote PR and moves the release to `_archive/<v>/`.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# No `__pycache__` beside a projected skill.
sys.dont_write_bytecode = True
#: One bootstrap statement: this folder and the kernel, at the front.
sys.path[:0] = [
    str(Path(__file__).resolve().parent),
    str(Path(__file__).resolve().parents[2] / "dd-bug-resolution" / "scripts"),
]

import _bugs_store as store
import _findings
import _ledger
from _clock import now_iso as utc_now
from _grammar import STATE
from _platform import Undecodable, act, read_text, use_utf8_stdio
from _platform import replace as move
from _refusal import Refusal, report
from _release_check import ship_histo_findings
from _release_new import new_release
from _release_phase import SHIP_PR, set_phase
from _release_schema import (
    _ORIGIN_GRAMMAR,
    HISTO,
    ORIGIN_KINDS,
    SCRIPT,
    closure_summary,
    origin,
)
from _release_store import (
    Live,
    commit,
    live_release,
    window_start,
)
from _release_tree import check, drift, memory_errors, ship_findings
from _specs import choice, find_specs, refuse

_HELP = {
    "new": "open the next candidate: its rc-<N+1>/SPEC.md stub and _RELEASE.json, in one act",
    "phase": "move the live release to IMPLEMENTATION or CLOSURE, stamping its milestone",
    "drift": "the closure worklist over the live release's memory window (memory.py drift)",
    "memory": "append a structured `kind: memory` entry to the live log",
    "ship": "record the merged promote PR: shipped, a delivered histo line, the dir archived",
    "origin": "print the ids a SPEC's **Origin:** line carries, one `<kind> <id>` per line",
    "check": "validate every _RELEASE.json under releases/ and the ship ledger",
}


def _mentions(text: str, bug_id: str) -> bool:
    """Whether *text* names one whole slug-like bug id, not a longer id."""
    return re.search(rf"(?<![a-z0-9-]){re.escape(bug_id)}(?![a-z0-9-])", text) is not None


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="verb", required=True)
    for verb, help_text in _HELP.items():
        command = sub.add_parser(verb, help=help_text)
        if verb == "origin":
            command.add_argument("spec", type=Path, help="the SPEC.md to read")
            continue
        command.add_argument("--specs", type=Path, default=None, help="path to the specs/ tree")
        if verb == "new":
            command.add_argument("release_id", help="the new release's bare SemVer id")
            command.add_argument("--origin", default="operator-demand", help=_ORIGIN_GRAMMAR)
        if verb == "phase":
            command.add_argument("phase", help="IMPLEMENTATION or CLOSURE")
        if verb == "ship":
            command.add_argument("--pr", help="the merged promote PR number, when the host has one")
            command.add_argument(
                "--allow-open",
                action="append",
                default=[],
                metavar="ID",
                help="carry one operator-authorized open bug (repeat once per id)",
            )
        if verb == "memory":
            for name in ("--reviewed", "--changed"):
                command.add_argument(name, default="", help="comma-separated worklist entries")
        if verb in ("check", "drift"):
            command.add_argument("--json", action="store_true", help="emit findings as JSON")
    return parser


def _new(args: argparse.Namespace, specs: Path) -> int:
    candidate = new_release(specs, args.release_id, utc_now()[:10], args.origin)
    print(f"[ok] created: {candidate / 'SPEC.md'}\n[ok] wrote: {candidate.parent / STATE}")
    return 0


def _origin(spec: Path) -> int:
    try:
        carried = origin(read_text(spec))
    except Undecodable as bad:
        report(bad, bad.fix)
        return 1
    except (OSError, ValueError) as error:
        what = (
            "pass the path of an existing SPEC.md"
            if isinstance(error, OSError)
            else "edit its `**Origin:**` line"
        )
        report(f"{spec} {error}", act("agent", what))
        return 1
    print(
        *(f"{kind} {i}" for kind in ORIGIN_KINDS for i in carried.get(kind, [])),
        sep="\n",
        end="\n" if carried else "",
    )
    return 0


def _subject(live: Live, tail: str) -> None:
    """Print the subject the milestone commit carries (the one reader of it is `_memory_drift.by_subject`)."""
    if live.candidate:
        print(f"commit subject: chore(release): {live.candidate.name} {tail}")


def _phase(args: argparse.Namespace, specs: Path) -> int:
    release_id, ts = set_phase(specs, args.phase.upper())
    print(f"[ok] release {release_id} -> phase {args.phase.upper()} ({ts})")
    _subject(live_release(specs), f"phase {args.phase.upper()}")
    return 0


def _drift(args: argparse.Namespace, specs: Path) -> int:
    """The worklist over the window `memory` records: from the newest recorded bound HEAD reaches, else the root commit."""
    report = drift.report(
        specs, drift.reach(specs.parent, window_start(specs.parent, live_release(specs)))
    )
    print(json.dumps(report, indent=2) if args.json else drift.render(report))
    return 1 if report["atoms"] or report["uncovered"] else 0


def _memory(args: argparse.Namespace, specs: Path) -> int:
    """Append the record over the ledger-derived window, refused unless its worklist was worked."""
    live, ts = live_release(specs), utc_now()
    since = drift.reach(specs.parent, window_start(specs.parent, live))
    lists = [[s for s in getattr(args, n).split(",") if s] for n in ("reviewed", "changed")]
    try:
        until = drift.git(specs.parent, "rev-parse", "HEAD")[0]
        records = [e for e in live.state.get("log") or [] if e.get("kind") == "memory"]  # fmt: skip
        if records and records[-1].get("until") == until:  # a rerun at HEAD appends nothing
            print(f"[ok] release {live.release_id} memory already reconciled to {until[:12]}")
            return 0
        entry = {"ts": ts, "agent": "release.py memory", "kind": "memory",
                 "text": f"Memory reconciled over {since}..{until[:12]}: {len(lists[0])} "
                 f"reviewed, {len(lists[1])} changed.", "since": since, "until": until,
                 "reviewed": lists[0], "changed": lists[1]}  # fmt: skip
        errors = memory_errors(specs, str(live.state.get("phase")), entry)
    except drift.Refusal as refusal:
        raise Refusal(str(refusal), refusal.fix) from refusal
    if errors:
        raise Refusal(errors[0], SCRIPT("memory", "--help"))
    commit(live.release_dir / STATE, f"releases/{live.release_id}/{STATE}",
           lambda state: {**state, "log": [*(state.get("log") or []), entry]})  # fmt: skip
    print(f"[ok] release {live.release_id} log <- kind memory {since}..{until[:12]} ({ts})")
    _subject(live, "memory pass recorded")
    return 0


def _allowed_open_bugs(args: argparse.Namespace, specs: Path) -> list[str]:
    """The `--allow-open` ids, once each, matching the open bugs exactly; refuses otherwise."""
    open_ids = store.open_ids(specs)
    allowed = sorted(set(args.allow_open))
    if len(allowed) != len(args.allow_open):
        raise Refusal(
            "--allow-open repeats an id — supply exactly one flag per open bug",
            act("agent", "remove the duplicate --allow-open flag"),
        )
    if missing := sorted(set(open_ids) - set(allowed)):
        fix = (
            act("agent", f"resolve {', '.join(missing)} before shipping")
            if not allowed
            else act("operator", f"authorize carrying {', '.join(missing)}")
        )
        raise Refusal(
            f"open bug(s) require one --allow-open flag each: {', '.join(missing)}",
            fix,
        )
    if extra := sorted(set(allowed) - set(open_ids)):
        raise Refusal(
            f"--allow-open names bug(s) not open: {', '.join(extra)}",
            act("agent", f"remove --allow-open for {', '.join(extra)}"),
        )
    return allowed


def _refuse_unauthorized(allowed: list[str], state: dict[str, Any]) -> None:
    """Each carried open bug needs a verbatim authorization note and a closure-summary carry."""
    log = state.get("log") or []
    summary = closure_summary(state).get("carried", "")
    for bug_id in allowed:
        authorized = any(
            entry.get("kind") == "note"
            and "Operator authorization verbatim:" in str(entry.get("text", ""))
            and _mentions(str(entry.get("text", "")), bug_id)
            for entry in log
        )
        carried = _mentions(summary, bug_id)
        if not authorized:
            raise Refusal(
                f"--allow-open {bug_id} has no authorization note",
                act("operator", f"authorize carrying {bug_id}"),
            )
        if not carried:
            raise Refusal(
                f"--allow-open {bug_id} has no closure summary carry",
                act("agent", f"add {bug_id} to the carried field of the kind: summary entry"),
            )


def _record_ship(args: argparse.Namespace, specs: Path, live: Live, ts: str) -> None:
    """Write `shipped`, the `delivered` histo line and move the directory to `_archive/<v>/`."""
    line = json.dumps({"id": live.release_id, "ts": ts, "disposition": "delivered",
                       "release": live.release_id, "reason": None, "entry": None,
                       "summary": None}) + "\n"  # fmt: skip
    histo = specs / HISTO
    kept = read_text(histo) if histo.is_file() else ""
    if errors := ship_histo_findings(kept + line):
        raise Refusal(f"the ship ledger would not pass check: {errors[-1]['message']}",
                      SCRIPT("check"))  # fmt: skip
    commit(live.release_dir / STATE, f"releases/{live.release_id}/{STATE}",
           lambda s: {**s, "shipped": {"pr": int(args.pr) if args.pr else None, "ts": ts}})  # fmt: skip
    _ledger.replace(histo, kept + line)
    move(live.release_dir, specs / "releases" / "_archive" / live.release_id)


def _ship(args: argparse.Namespace, specs: Path) -> int:
    """CLOSURE -> shipped {pr, ts}, one `delivered` histo line, the whole directory
    moved to `_archive/<v>/`, never deleted; refused on any `ship_findings`."""
    live, ts = live_release(specs), utc_now()
    if not (args.pr is None or args.pr.isdigit() and int(args.pr) > 0):
        raise choice(Refusal(f"--pr {args.pr!r}: a PR number, when the host has one", SCRIPT("ship")), SHIP_PR)  # fmt: skip
    if found := ship_findings(specs):
        raise Refusal(found[0]["message"], found[0]["fix"])
    _refuse_unauthorized(_allowed_open_bugs(args, specs), live.state)
    _record_ship(args, specs, live, ts)
    print(f"[ok] release {live.release_id} shipped" + (f" (PR #{args.pr})" if args.pr else ""))
    return 0


_VERBS = {"new": _new, "phase": _phase, "drift": _drift, "memory": _memory, "ship": _ship}


def main(argv: list[str] | None = None) -> int:
    use_utf8_stdio()
    args = _parser().parse_args(argv)
    if args.verb == "origin":
        return _origin(args.spec)
    reads = args.verb in ("check", "drift")
    specs = find_specs(args.specs, ledger=None if reads else f"specs/releases/{STATE}")
    if args.verb == "check":
        findings = check(specs)
        origin_rows = [f for f in findings if f["message"].startswith("Origin ")]
        publish_origin = bool(origin_rows) and all(
            f["verdict"] == "info" and f["message"].endswith(" traced") for f in origin_rows
        )
        # JSON adds Origin trace information; only errors control the exit status.
        _findings.run_check(
            [
                f
                for f in findings
                if f["verdict"] == "error" or (publish_origin and f in origin_rows)
            ]
            if args.json
            else findings,
            as_json=args.json,
        )
        return int(any(f["verdict"] == "error" for f in findings))
    try:
        return _VERBS[args.verb](args, specs)
    except (Refusal, drift.Refusal) as refusal:
        return refuse(refusal, specs)


if __name__ == "__main__":
    raise SystemExit(main())
