#!/usr/bin/env python3
"""The release TREE walk `release.py check` runs: every state document under
``releases/``, the ship ledger, and the live CLOSURE's memory entry.

Split from `_release_check`, which judges DOCUMENT bytes every write validates against;
this one judges a tree on disk and the history beside it.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import _bugs_store as store
import _findings
import _memory_drift as drift
from _grammar import SEMVER_RE, STATE, sole_live
from _ledger import records
from _platform import act, read_text
from _refusal import Refusal
from _release_check import candidate_errors, ship_histo_findings, state_findings
from _release_phase import NEXT
from _release_schema import (
    CANDIDATE_DOCS,
    CLOSURE,
    CODE,
    HISTO,
    MEMORY_WRITE,
    SCRIPT,
    TRIO_PHASES,
    closure_summary,
    current_candidate,
    origin,
    origin_line,
)
from _release_store import Live, live_release
from _specs import script

__all__ = ["check", "drift", "memory_errors", "ship_findings", "tree_findings"]

_SKILLS = Path(__file__).resolve().parents[2]
#: The verb writing a LIVE record's pointer back to the release (`{i}` the id, `{r}` it).
_POINTER = {
    "backlog": ("dd-backlog-definition/scripts/backlog.py",
                ("exit", "{i}", "--disposition", "delivered", "--release", "{r}")),
    "findings": ("dd-audit-project/scripts/audit.py",
                 ("disposition", "{a}", "{i}", "--disposition", "resolved", "--release", "{r}")),
}  # fmt: skip
#: The one operator act for a record no verb can point back alone (no placeholder).
_ACT = {
    "backlog": "backlog entry {i} already exited naming another release",
    "bugs": "resolve bug {i} (`bugs.py resolve {i}` "
            "with --cause, --caused-by and --solution)",
    "findings": "finding {i}'s audit closed without naming release {r}",
}  # fmt: skip


def _trace(
    specs: Path, release: str, carried: dict[str, list[str]], summary: str = ""
) -> list[tuple[str, str, str, bool]]:
    """Each carried id as ``(kind, id, standing, live)``, asked of its OWNING ledger,
    live or archived: ``traced`` when its record points back to *release* (a delivered or
    superseded exit naming it, a to-bug exit whose bug stands, a bug resolved in it,
    rejected, or superseded by a bug that traces, a finding dispositioned to it, live or in
    its closed audit's record), ``untraced`` while it does not yet, else why it is wrong;
    ``live`` when a verb can still write its pointer (an active entry, an open audit's finding)."""
    document = specs / "backlog" / "BACKLOG.json"
    active = json.loads(read_text(document)) if document.is_file() else {}
    exits = records(specs / "backlog/_archive/backlog_histo.jsonl")
    bugs = {r.get("id"): r for r in store.history(specs)}
    closed = {r.get("id"): {"release": r.get("release"), "status": r.get("disposition")}
              for r in records(specs / "audits/_archive/audits_histo.jsonl")}  # fmt: skip
    found = {r.get("id"): r for p in sorted(specs.glob("audits/*/FINDINGS.jsonl"))
             for r in records(p)}  # fmt: skip
    ledgers = {
        "backlog": {**{e.get("id"): {} for e in active.get("active") or []},
                    **{r.get("id"): r for r in exits}},
        "findings": found,
    }  # fmt: skip

    def standing(kind: str, i: str, seen: frozenset[str] = frozenset()) -> str:
        if summary and re.search(rf"(?<![\w-]){re.escape(i)}(?![\w-])", summary):
            return "traced"
        if kind == "bugs":
            return store.standing(specs, i, release)
        record = ledgers[kind].get(
            i, closed.get(i.rpartition("-F")[0]) if kind == "findings" else None
        )
        if record is None:
            return f"names no record under {kind}/"
        if record.get("disposition") == "to-bug":
            if bugs.get(record.get("reason"), {}).get("status") in (None, "rejected"):
                return f"exited to-bug {record.get('reason')!r}, a bug rejected or unknown"
            return "traced"
        if (by := record.get("superseded_by")) and by not in seen:
            return standing(kind, by, seen | {i})
        back = record.get("release")
        declined = "rejected" in (record.get("status"), record.get("disposition"))
        return "traced" if back == release or declined else "untraced"

    live = {
        "backlog": {e.get("id") for e in active.get("active") or []},
        "bugs": set(),
        "findings": set(found),
    }
    return [
        (kind, i, standing(kind, i), i in live[kind]) for kind, ids in carried.items() for i in ids
    ]


#: The first `## ` heading of every live candidate's SPEC.
BUG_WINDOW = "## Bug window review"


def _window_findings(
    spec: Path, text: str, state: dict[str, Any], rel: str
) -> list[dict[str, Any]]:
    """The SPEC's first `## ` heading is :data:`BUG_WINDOW` — an error only in
    DEFINITION, where `new` writes it, info after."""
    lines = text.splitlines()
    head = next((n for n, h in enumerate(lines, 1) if h.startswith("## ")), 1)
    if lines[head - 1 : head] == [BUG_WINDOW]:
        return []
    message = f"the live SPEC's first `## ` heading is not `{BUG_WINDOW}` (AC5.6)"
    if state.get("phase") != "DEFINITION":
        return [_findings.info(CODE, rel, head, message)]
    return [_findings.finding(CODE, rel, head, message,
            act("agent", f"open {spec} with `{BUG_WINDOW}` as its first `## ` heading, "
            "reviewing the prior candidate's table and each resolved record's fix, found by its "
            "`fix(bugs)` or `refactor(bugs)` line, as `dd-bug-resolution/LINEAGE.md` defines"))]  # fmt: skip


def _origin_row(
    specs: Path, spec: Path, line: int, live: Live, swept: bool, row: tuple[str, str, str, bool]
) -> dict[str, Any]:
    """One carried id's finding: info with no fix when it stands, else the pointer verb or act."""
    kind, i, standing, writable = row
    rel, message = spec.relative_to(specs).as_posix(), f"Origin {kind}:{i} {standing}"
    if standing == "traced" or (standing == "untraced" and not swept):
        return _findings.info(CODE, rel, line, message)
    values = {"i": i, "a": i.rpartition("-F")[0], "r": live.release_id}
    if standing == "untraced" and writable:
        skill, verb = _POINTER[kind]
        fix: str = script(_SKILLS / skill)(*(w.format(**values) for w in verb), specs=specs)
    elif standing == "untraced":
        fix = act(
            "agent", f"{_ACT[kind].format(**values)}, or rule it out of the Origin line of {spec}."
        )
    else:
        fix = act(
            "agent",
            f"name a live {kind} id for {kind}:{i}, or rule it out of the Origin line of {spec}.",
        )
    return _findings.finding(CODE, rel, line, message, fix)


def _origin_findings(specs: Path) -> list[dict[str, Any]]:
    """The live candidate's SPEC head: the bug-window heading, then its Origin line:
    grammar and existence always, and each carried id listed with its standing."""
    try:
        live = live_release(specs)
    except Refusal:
        return []  # the tree walk reports a missing or doubled live release
    spec = live.candidate / "SPEC.md" if live.candidate else None
    if spec is None or not spec.is_file():
        return []
    text, rel = read_text(spec), spec.relative_to(specs).as_posix()
    out, line = _window_findings(spec, text, live.state, rel), origin_line(text)
    try:
        closure = closure_summary(live.state)
        rows = _trace(specs, live.release_id, origin(text), "; ".join(closure.values()))
    except ValueError as error:
        return out + [_findings.finding(CODE, rel, line, str(error), act("agent", f"rewrite the Origin "
                              f"line {line} of {spec} to the Origin grammar ({error})"))]  # fmt: skip
    swept = bool(live.state.get("shipped") or closure)
    return out + [_origin_row(specs, spec, line, live, swept, row) for row in rows]


def _definition_findings(state: dict[str, Any], rel: str, specs: Path) -> list[dict[str, Any]]:
    """DEFINITION implements nothing: a closure entry logged after the live candidate's
    birth note means the phase verb was never run."""
    log = state["log"]
    born = max((n for n, e in enumerate(log) if e["agent"] == "release.py new"), default=-1)
    found = [f"closure entry kind {e['kind']!r} logged after the candidate's birth"
             for e in log[born + 1:] if e["kind"] not in ("note", "milestone", "merge")]  # fmt: skip
    if not found:
        return []
    fix = SCRIPT(*NEXT["DEFINITION"].split(), specs=specs)
    return [_findings.finding(CODE, rel, 1, "; ".join(found), fix)]


def _directory_findings(release_dir: Path, specs: Path) -> list[dict[str, Any]]:
    """One live directory: its state document, its live candidate's `W:` sets, then the
    SPEC, PLAN and job files in IMPLEMENTATION/CLOSURE, or its closure-entry check in DEFINITION."""
    dir_rel, path = release_dir.relative_to(specs).as_posix(), release_dir / STATE
    if not path.is_file():
        return [_findings.finding(CODE, dir_rel, 1, f"release directory carries no {STATE}", act("agent", f"restore {path} from git history, or move {release_dir} out of specs/"))]  # fmt: skip
    text = read_text(path)
    if findings := state_findings(text, f"{dir_rel}/{STATE}", specs.resolve()):
        return findings
    state = json.loads(text)
    phase, candidate = state["phase"], current_candidate(release_dir, state)
    jobs = [_findings.finding(CODE, f"{dir_rel}/{path.relative_to(release_dir).as_posix()}", 1, message, fix)
            for path, message, fix in (candidate_errors(candidate) if candidate else [])
            if not (phase == CLOSURE and MEMORY_WRITE in message)]  # fmt: skip
    if phase not in TRIO_PHASES:
        return (_definition_findings(state, f"{dir_rel}/{STATE}", specs)
                if candidate else []) + jobs  # fmt: skip
    missing = [n for n in CANDIDATE_DOCS if not (candidate and (candidate / n).is_file())]
    if candidate is None or missing:
        where = candidate.name if candidate else "rc-<N>"
        return [_findings.finding(CODE, dir_rel, 1, f"phase {phase} is missing {where}/{', '.join(missing)}",
                        act("agent", f"define {', '.join(missing)} in {candidate or release_dir}"
                        " (dd-release-definition)"))]  # fmt: skip
    return jobs


def memory_errors(specs: Path, phase: str, entry: dict[str, Any]) -> list[Refusal]:
    """Why *entry* reconciles nothing over its own [since, until], each with the act that
    clears it: what the `memory` verb refuses on. A name is valid when its atom matched the
    window's worklist or its own file moved in the window."""
    since, until = str(entry.get("since")), str(entry.get("until"))
    worklist = drift.report(specs, since, until)
    if phase != "CLOSURE":
        return [Refusal(f"release is in phase {phase!r} — the memory reconciliation is CLOSURE work",
                        SCRIPT(*NEXT.get(phase, "check").split(), specs=specs))]  # fmt: skip
    reviewed, changed = (
        [str(s) for s in entry.get(name) or []] for name in ("reviewed", "changed")
    )
    paths = {str(f["slug"]): str(f["path"]) for f in drift.entries(specs)}
    moved = set(drift.git(specs.parent, "diff", "--name-only", since, until))
    listed = [str(atom["slug"]) for atom in worklist["atoms"]]
    valid = set(listed) | {slug for slug, path in paths.items() if path in moved}
    run = f"run `{SCRIPT.inline('memory', specs=specs)}`"
    errors = [Refusal(f"worklist entry {e!r} is in neither --reviewed nor --changed",
                      act("agent", f"{run} with {e!r} in --reviewed, or in --changed once its atom is rewritten"))
              for e in listed if e not in {*reviewed, *changed}]  # fmt: skip
    errors += [Refusal(f"unit {u!r} is covered by no atom",
                       act("agent", f"write an atom whose `sources` glob covers the unit, commit it, then {run} "
                           "with that atom in --changed"))
               for u in worklist["uncovered"]]  # fmt: skip
    errors += [Refusal(f"{e!r} is not in the window's worklist",
                       act("agent", f"{run} naming only atoms `drift` lists or atoms created or rewritten in the window"))
               for e in sorted({*reviewed, *changed} - valid)]  # fmt: skip
    return errors or [Refusal(f"--changed names {slug!r}, whose atom did not move since {since}",
                              act("agent", f"{run} with {slug!r} in --reviewed"))
                      for slug in changed if slug in paths and paths[slug] not in moved]  # fmt: skip


def _memory_findings(specs: Path) -> list[dict[str, Any]]:
    """CLOSURE: a `kind: memory` log entry stamped at or after `implemented.ts` exists —
    memory references the code, never repeats it, so no git re-judges the entry."""
    try:
        live = live_release(specs)
    except Refusal:
        return []  # the tree walk reports a missing or doubled live release
    if live.state.get("phase") != "CLOSURE":
        return []
    stamp = str((live.state.get("implemented") or {}).get("ts") or "")
    if any(e.get("kind") == "memory" and str(e.get("ts")) >= stamp
           for e in live.state.get("log") or []):  # fmt: skip
        return []
    message = (f"release is in CLOSURE with no `kind: memory` log entry stamped at or after "
               f"implemented.ts {stamp!r} — the closure reconciled no memory")  # fmt: skip
    fix = act("agent", f"run `{SCRIPT.inline('drift', specs=specs)}`, judge its worklist, then run "
           f"`{SCRIPT.inline('memory', specs=specs)}` with the atom slugs the memory pass reviewed as "
           "--reviewed and changed as --changed")  # fmt: skip
    return [_findings.finding(CODE, f"releases/{live.release_id}/{STATE}", 1, message, fix)]


def tree_findings(specs: Path) -> list[dict[str, Any]]:
    """Every live directory under ``releases/``, each archived state document, the
    one-live-release rule and the ship ledger — what `new` refuses on."""
    releases, findings = specs / "releases", []
    for d in sorted(releases.iterdir()) if releases.is_dir() else []:
        if SEMVER_RE.match(d.name):
            findings += _directory_findings(d, specs)
        elif d.name != "_archive" and (d / STATE).is_file():
            move = f"{d.resolve()} into its canon shape (a bare M.m.p id), or out of specs/"
            findings.append(_findings.finding(CODE, f"releases/{d.name}", 1, f"{d.name!r} is not a bare M.m.p "
                                    "release id, so it is not a live release",
                                    act("agent", f"move {move}")))  # fmt: skip
    try:
        sole_live(specs)
    except Refusal as several:
        findings.append(_findings.finding(CODE, "releases", 1, str(several), several.fix))
    if (specs / HISTO).is_file():
        findings += ship_histo_findings(read_text(specs / HISTO), specs.resolve())
    for path in sorted(releases.glob(f"_archive/*/{STATE}")):
        # An archived state names its ship.
        rel, rewrite = path.relative_to(specs).as_posix(), f"rewrite {path.resolve()} as one JSON "
        try:
            state = json.loads(read_text(path))
        except json.JSONDecodeError as error:
            findings.append(_findings.finding(CODE, rel, 1, f"archived state is not valid JSON: {error}",
                                    act("agent", f"{rewrite}object, from git history")))  # fmt: skip
            continue
        shipped = state.get("shipped") if isinstance(state, dict) else None
        if not (isinstance(shipped, dict) and "pr" in shipped and isinstance(shipped["pr"], int | None)):  # fmt: skip
            findings.append(_findings.finding(CODE, rel, 1, "archived release carries no shipped {pr}",
                                    act("agent", f"{rewrite}object whose shipped names the "
                                    "merged promote PR")))  # fmt: skip
    return findings


@_findings.decodable(CODE)
def check(specs: Path) -> list[dict[str, Any]]:
    """The ONE release validator (the doctor delegates here): the tree, the live
    candidate's Origin, then the live CLOSURE's memory record."""
    return tree_findings(specs) + _origin_findings(specs) + _memory_findings(specs)


def ship_findings(specs: Path) -> list[dict[str, Any]]:
    """What `ship` refuses on: `check`'s errors, a phase short of CLOSURE (fix: that
    phase's NEXT verb), an archive already holding the id — one readiness authority."""
    live = live_release(specs)
    found = [f for f in check(specs) if f["verdict"] == "error"]
    rel, phase = f"releases/{live.release_id}/{STATE}", str(live.state.get("phase"))
    if phase != "CLOSURE":
        found.append(_findings.finding(CODE, rel, 1, f"release {live.release_id} is in phase {phase!r} — "
                     "only a CLOSURE release ships",
                     SCRIPT(*NEXT.get(phase, "check").split())))  # fmt: skip
    if (archive := specs / "releases" / "_archive" / live.release_id).exists():
        found.append(_findings.finding(CODE, rel, 1, f"release {live.release_id} is live and already "
                     f"archived at {archive}", act("agent", f"decide which of "
                     f"{live.release_dir.resolve()} and {archive.resolve()} is release "
                                    f"{live.release_id}; a release ships once")))  # fmt: skip
    return found
