#!/usr/bin/env python3
"""The release TREE walk `release.py check` runs: every state document under
``releases/``, the ship ledger, and the live CLOSURE's memory entry re-judged over git.

Split from `_release_check`, which judges DOCUMENT bytes every write validates against;
this one judges a tree on disk and the history beside it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
# The worklist has ONE decider, the spec navigator's drift function, projected beside
# this skill: importing a pure function is not a script calling a script (SPEC D6).
sys.path.insert(1, str(Path(__file__).resolve().parents[2] / "dd-spec-navigator" / "scripts"))

import _memory_drift as drift  # noqa: E402
from _ledger import records  # noqa: E402
from _release_check import finding, histo_findings, state_findings  # noqa: E402
from _release_plan import plan_errors  # noqa: E402
from _release_schema import (  # noqa: E402
    HISTO,
    SEMVER_RE,
    STATE,
    TRIO,
    TRIO_PHASES,
    candidate_dir,
    origin,
    origin_line,
    unfinished_tasks,
)
from _release_store import SCRIPT, Refusal, live_ids, live_release, window_start  # noqa: E402
from _specs import quote, script, with_specs  # noqa: E402

__all__ = ["check", "drift", "memory_errors", "tree_findings"]

_SKILLS = Path(__file__).resolve().parents[2]
#: The verb writing a LIVE record's pointer back to the release (`{i}` the id, `{r}` it).
_POINTER = {
    "backlog": ("dd-backlog-definition/scripts/backlog.py",
                "exit {i} --disposition delivered --release {r}"),
    "findings": ("dd-audit-project/scripts/audit.py",
                 "disposition {a} {i} --disposition resolved --release {r}"),
}  # fmt: skip
#: The one operator act for a record no verb can point back alone (ADR 0158: no placeholder).
_ACT = {
    "backlog": "backlog entry {i} already exited naming another release",
    "bugs": "resolve bug {i} in release {r} (`bugs.py resolve {i} --resolved-release {r}` "
            "with its cause, lineage and evidence triple)",
    "findings": "finding {i}'s audit closed without naming release {r}",
}  # fmt: skip


def _trace(
    specs: Path, release: str, carried: dict[str, list[str]]
) -> list[tuple[str, str, str, bool]]:
    """Each carried id as ``(kind, id, standing, live)`` (ADR 0127), asked of its OWNING ledger,
    live or archived: ``traced`` when its record points back to *release* (a delivered or
    superseded exit naming it, a to-bug exit whose bug stands, a bug resolved in it,
    rejected, or superseded by a bug that traces, a finding dispositioned to it, live or in
    its closed audit's record), ``untraced`` while it does not yet, else why it is wrong;
    ``live`` when a verb can still write its pointer (an active entry, an open audit's finding)."""
    document = specs / "backlog" / "BACKLOG.json"
    active = json.loads(document.read_text(encoding="utf-8")) if document.is_file() else {}
    exits = records(specs / "backlog/_archive/backlog_histo.jsonl")
    bugs = {r.get("id"): r for p in ("BUGS.jsonl", "_archive/bugs_histo.jsonl")
            for r in records(specs / "bugs" / p)}  # fmt: skip
    closed = {r.get("id"): {"release": r.get("release"), "status": r.get("disposition")}
              for r in records(specs / "audits/_archive/audits_histo.jsonl")}  # fmt: skip
    found = {r.get("id"): r for p in sorted(specs.glob("audits/*/FINDINGS.jsonl"))
             for r in records(p)}  # fmt: skip
    ledgers = {
        "backlog": {**{e.get("id"): {} for e in active.get("active") or []},
                    **{r.get("id"): r for r in exits}},
        "bugs": bugs,
        "findings": found,
    }  # fmt: skip

    def standing(kind: str, i: str, seen: frozenset[str] = frozenset()) -> str:
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
        back = record.get("resolved_release" if kind == "bugs" else "release")
        return "traced" if back == release or record.get("status") == "rejected" else "untraced"

    live = {
        "backlog": {e.get("id") for e in active.get("active") or []},
        "bugs": set(),
        "findings": set(found),
    }
    return [
        (kind, i, standing(kind, i), i in live[kind]) for kind, ids in carried.items() for i in ids
    ]


def _origin_findings(specs: Path) -> list[dict[str, Any]]:
    """The live candidate's Origin line: grammar and existence always, and each carried id
    listed with its standing — a missing pointer is an error only once the live candidate
    (past DEFINITION, so a stacked candidate's inherited log is not its own) logged its
    `dispositions` entry, or shipped."""
    try:
        live = live_release(specs)
    except Refusal:
        return []  # the tree walk reports a missing or doubled live release
    spec = live.candidate / "SPEC.md" if live.candidate else None
    if spec is None or not spec.is_file():
        return []
    rel, text, state = (
        spec.relative_to(specs).as_posix(),
        spec.read_text(encoding="utf-8"),
        live.state,
    )
    line = origin_line(text)
    try:
        rows = _trace(specs, live.release_id, origin(text))
    except ValueError as error:
        return [finding(rel, line, str(error))]
    since = str((state.get("defined") or {}).get("ts") or "")
    swept = (
        state.get("shipped")
        or state.get("phase") != "DEFINITION"
        and any(
            e.get("kind") == "dispositions" and str(e.get("ts")) >= since
            for e in state.get("log") or []
        )
    )
    out = []
    for kind, i, standing, writable in rows:
        row = finding(rel, line, f"Origin {kind}:{i} {standing}")
        values = {"i": quote(i), "a": quote(i.rpartition("-F")[0]), "r": live.release_id}
        if standing == "untraced" and swept and writable:
            skill, verb = _POINTER[kind]
            row["fix"] = with_specs(f"{script(_SKILLS / skill)} {verb.format(**values)}", specs)
        elif standing == "untraced" and swept:
            act = _ACT[kind].format(**values)
            row["fix"] = f"Operator action: {act}, or rule it out of the Origin line of {spec}."
        elif standing in ("traced", "untraced"):
            row["verdict"] = "info"
        out.append(row)
    return out


def _directory_findings(release_dir: Path, specs: Path) -> list[dict[str, Any]]:
    """One live directory: its state document, then its live candidate's trio in
    IMPLEMENTATION/CLOSURE."""
    dir_rel, path = release_dir.relative_to(specs).as_posix(), release_dir / STATE
    if not path.is_file():
        return [finding(dir_rel, 1, f"release directory carries no {STATE}")]
    text = path.read_text(encoding="utf-8")
    if findings := state_findings(text, f"{dir_rel}/{STATE}"):
        return findings
    state = json.loads(text)
    phase, candidate = state["phase"], candidate_dir(release_dir)
    if phase not in TRIO_PHASES:
        return []
    missing = [n for n in TRIO if not (candidate and (candidate / n).is_file())]
    if candidate is None or missing:
        where = candidate.name if candidate else "rc-<N>"
        return [finding(dir_rel, 1, f"phase {phase} is missing {where}/{', '.join(missing)}")]
    plan = (candidate / "PLAN.md").read_text(encoding="utf-8")
    errors = plan_errors(plan, unfinished_tasks(candidate))
    return [finding(f"{dir_rel}/{candidate.name}/PLAN.md", 1, e) for e in errors]


def memory_errors(specs: Path, phase: str, entry: dict[str, Any]) -> list[str]:
    """Why *entry* reconciles nothing over its own [since, until]: the ONE judgement the
    `memory` verb refuses on and `check` re-applies to the entry the log records."""
    since, until = str(entry.get("since")), str(entry.get("until"))
    worklist = drift.report(specs, since, until)
    lists = [[str(s) for s in entry.get(name) or []] for name in ("reviewed", "changed")]
    paths = {str(atom["slug"]): str(atom["path"]) for atom in worklist["atoms"]}
    # git decides "moved": it normalises line endings a byte compare would not.
    unmoved = [f"--changed names {slug!r}, whose atom did not move since {since}"
               for slug in lists[1] if slug in paths and not drift.git(
                   specs.parent, "diff", "--name-only", since, until, "--", paths[slug])]  # fmt: skip
    if phase != "CLOSURE":
        return [f"release is in phase {phase!r} — the memory reconciliation is CLOSURE work"]
    listed = [str(atom["slug"]) for atom in worklist["atoms"]] + worklist["uncovered"]
    named = set(lists[0]) | set(lists[1])
    errors = [f"worklist entry {e!r} is in neither --reviewed nor --changed"
              for e in listed if e not in named]  # fmt: skip
    errors += [f"{e!r} is not in the window's worklist" for e in sorted(named - set(listed))]
    return errors or unmoved


def _memory_record_error(state: dict[str, Any]) -> str:
    """Why this CLOSURE state names no conformant reconciliation record, or "": the latest
    `kind: memory` entry stamped at or after `implemented.ts` carries its four fields and
    opens at the ledger-derived start."""
    stamp = str((state.get("implemented") or {}).get("ts") or "")
    log = [e for e in state.get("log") or [] if isinstance(e, dict)]
    entries = [e for e in log if e.get("kind") == "memory" and str(e.get("ts")) >= stamp]
    if not entries:
        return (f"release is in CLOSURE with no `kind: memory` log entry stamped at or after "
                f"implemented.ts {stamp!r} — the closure reconciled no memory")  # fmt: skip
    missing = [f for f in ("since", "until", "reviewed", "changed") if f not in entries[-1]]
    if missing:
        return (f"the latest `kind: memory` log entry lacks {', '.join(missing)} — a prose "
                "note names no window and dispositions no atom")  # fmt: skip
    try:
        start = window_start({**state, "log": log[: log.index(entries[-1])]})
    except Refusal:
        start = ""
    if str(entries[-1]["since"]) != start:
        return (f"the latest `kind: memory` log entry opens at {entries[-1]['since']!r}, not "
                f"at the ledger-derived start {start!r} — the window was chosen, not derived")  # fmt: skip
    return ""


def _window_findings(specs: Path) -> list[dict[str, Any]]:
    """CLOSURE: the latest memory entry names its window, is re-judged over its
    [since, until], and no atom's sources moved over [until, HEAD] — code after the
    entry is unreconciled."""
    try:
        live = live_release(specs)
    except Refusal:
        return []  # the tree walk reports a missing or doubled live release
    if live.state.get("phase") != "CLOSURE":
        return []
    rel = f"releases/{live.release_id}/{STATE}"
    if message := _memory_record_error(live.state):
        fix = with_specs(f"{SCRIPT} memory --reviewed <slugs> --changed <slugs>", specs)
        return [{**finding(rel, 1, message), "fix": fix}]
    entry = [e for e in live.state["log"] if isinstance(e, dict) and e.get("kind") == "memory"][-1]
    until = str(entry["until"])
    try:
        errors = memory_errors(specs, "CLOSURE", entry)
        errors += [f"atom {a['slug']!r} moved after the memory entry's until {until[:12]}: "
                   f"{', '.join(a['matched'])}" for a in drift.report(specs, until)["atoms"]]  # fmt: skip
    except (drift.Refusal, OSError) as refusal:  # a Refusal carries the fix that clears it
        return [{**finding(rel, 1, str(refusal)), "fix": getattr(refusal, "fix", "")}]
    return [finding(rel, 1, message) for message in errors]


def tree_findings(specs: Path) -> list[dict[str, Any]]:
    """Every live directory under ``releases/`` (``_archive/`` is history, exempt by
    location), the one-live-release rule and the ship ledger — what `new` refuses on."""
    releases, findings = specs / "releases", []
    for d in sorted(releases.iterdir()) if releases.is_dir() else []:
        if SEMVER_RE.match(d.name):
            findings += _directory_findings(d, specs)
        elif d.name != "_archive" and (d / STATE).is_file():
            move = f"{d.resolve()} into its canon shape (a bare M.m.p id), or out of specs/"
            findings.append({**finding(f"releases/{d.name}", 1, f"{d.name!r} is not a bare M.m.p "
                             "release id, so it is not a live release"),
                             "fix": f"Operator action: move {move}"})  # fmt: skip
    if len(ids := live_ids(specs)) > 1:
        findings.append(finding("releases", 1, f"multiple live release directories carry "
                                f"{STATE}: {', '.join(ids)} — exactly one is allowed"))  # fmt: skip
    if (specs / HISTO).is_file():
        findings += histo_findings((specs / HISTO).read_text(encoding="utf-8"))
    return findings


def check(specs: Path) -> list[dict[str, Any]]:
    """The ONE release validator (the doctor delegates here): the tree, the live
    candidate's Origin, then the live CLOSURE's memory record."""
    return tree_findings(specs) + _origin_findings(specs) + _window_findings(specs)
