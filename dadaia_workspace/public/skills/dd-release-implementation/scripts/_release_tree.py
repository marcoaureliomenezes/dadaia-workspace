#!/usr/bin/env python3
"""The release TREE walk `release.py check` runs: every state document under
``releases/``, the ship ledger, and the live CLOSURE's memory entry.

Split from `_release_check`, which judges DOCUMENT bytes every write validates against;
this one judges a tree on disk and the history beside it.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
# The worklist has ONE decider, the spec navigator's drift function, projected beside
# this skill: importing a pure function is not a script calling a script (SPEC D6).
sys.path.insert(1, str(Path(__file__).resolve().parents[2] / "dd-spec-navigator" / "scripts"))

import _memory_drift as drift  # noqa: E402
from _ledger import records  # noqa: E402
from _release_check import dag_errors, finding, histo_findings, state_findings  # noqa: E402
from _release_phase import NEXT  # noqa: E402
from _release_schema import (  # noqa: E402
    CANDIDATE_DOCS,
    HISTO,
    MARK_RE,
    SEMVER_RE,
    SHA_RE,
    STATE,
    TRIO_PHASES,
    candidate_dir,
    job_errors,
    origin,
    origin_line,
    writes,
)
from _release_store import SCRIPT, Refusal, live_ids, live_release  # noqa: E402
from _specs import quote, script, with_specs  # noqa: E402

__all__ = ["check", "drift", "memory_errors", "refuse_open_bugs", "ship_findings", "tree_findings"]

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
    "bugs": "resolve bug {i} (`bugs.py resolve {i}` "
            "with --cause, --caused-by, --solution and --fix-sha)",
    "findings": "finding {i}'s audit closed without naming release {r}",
}  # fmt: skip


def _trace(
    specs: Path, release: str, carried: dict[str, list[str]], summary: str = ""
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
        if summary and re.search(rf"(?<![\w-]){re.escape(i)}(?![\w-])", summary):
            return "traced"
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


#: AC5.6: the first `## ` heading of every live candidate's SPEC.
BUG_WINDOW = "## Bug window review"


def _origin_findings(specs: Path) -> list[dict[str, Any]]:
    """The live candidate's SPEC head: its first `## ` heading is :data:`BUG_WINDOW` (AC5.6;
    an error only in DEFINITION, where `new` writes it — info after), then its Origin line:
    grammar and existence always, and each carried id listed with its standing — a missing
    pointer is an error only once the live candidate (past DEFINITION, so a stacked
    candidate's inherited log is not its own) logged its `dispositions` entry, or shipped."""
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
    lines = text.splitlines()
    head = next((n for n, h in enumerate(lines, 1) if h.startswith("## ")), 1)
    out = [] if lines[head - 1 : head] == [BUG_WINDOW] else [
        finding(rel, head, f"the live SPEC's first `## ` heading is not `{BUG_WINDOW}` (AC5.6)",
                f"Operator action: open {spec} with `{BUG_WINDOW}` as its first `## ` heading, "
                "reviewing `bugs.py window` and each cited test")
        | ({} if state.get("phase") == "DEFINITION" else {"verdict": "info"})
    ]  # fmt: skip
    line = origin_line(text)
    try:
        summary = next(
            (
                str(entry.get("text") or "")
                for entry in reversed(state.get("log") or [])
                if entry.get("kind") == "summary"
            ),
            "",
        )
        rows = _trace(specs, live.release_id, origin(text), summary)
    except ValueError as error:
        return out + [finding(rel, line, str(error), f"Operator action: rewrite the Origin "
                              f"line {line} of {spec} to the Origin grammar ({error})")]  # fmt: skip
    since = str((state.get("defined") or {}).get("ts") or "")
    swept = (
        state.get("shipped")
        or state.get("phase") != "DEFINITION"
        and any(
            e.get("kind") == "dispositions" and str(e.get("ts")) >= since
            for e in state.get("log") or []
        )
    )
    for kind, i, standing, writable in rows:
        row = finding(rel, line, f"Origin {kind}:{i} {standing}", f"Operator action: name a "
                      f"live {kind} id for {kind}:{i}, or rule it out of the Origin line of {spec}.")  # fmt: skip
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


def _definition_findings(
    state: dict[str, Any], marks: list[re.Match[str]], rel: str, candidate: Path, specs: Path
) -> list[dict[str, Any]]:
    """DEFINITION implements nothing: a `[-]`/`[x]` marker, or a closure entry logged
    after the live candidate's birth note, means the phase verb was never run."""
    log = state["log"]
    born = max((n for n, e in enumerate(log) if e["agent"] == "release.py new"), default=-1)
    found = [f"closure entry kind {e['kind']!r} logged after the candidate's birth"
             for e in log[born + 1:] if e["kind"] not in ("note", "milestone", "merge")]  # fmt: skip
    found += [f"task {m[0].strip()[:80]!r} is marked past '[ ]' in phase DEFINITION"
              for m in marks if m[2] != " "]  # fmt: skip
    if not found:
        return []
    try:  # `defined` is the commit that approved the trio, never HEAD: impl commits follow it
        docs = [str(candidate / n) for n in ("SPEC.md", "PLAN.md")]
        sha = drift.git(specs.parent, "log", "-1", "--format=%h", "--", *docs)[0]
        fix = with_specs(f"{SCRIPT} {NEXT['DEFINITION']} --sha {sha}", specs)
    except (drift.Refusal, OSError, IndexError):  # no history, no git binary
        fix = f"Operator action: run `{NEXT['DEFINITION']}` at the commit approving {candidate}"
    return [finding(rel, 1, "; ".join(found), fix)]


def _directory_findings(release_dir: Path, specs: Path) -> list[dict[str, Any]]:
    """One live directory: its state document, its live candidate's `W:` sets, then the
    trio in IMPLEMENTATION/CLOSURE or the untouched markers in DEFINITION."""
    dir_rel, path = release_dir.relative_to(specs).as_posix(), release_dir / STATE
    if not path.is_file():
        return [finding(dir_rel, 1, f"release directory carries no {STATE}", f"Operator action: "
                        f"restore {path} from git history, or move {release_dir} out of specs/")]  # fmt: skip
    text = path.read_text(encoding="utf-8")
    if findings := state_findings(text, f"{dir_rel}/{STATE}", specs.resolve()):
        return findings
    state = json.loads(text)
    phase, candidate = state["phase"], candidate_dir(release_dir)
    jobs = [finding(f"{dir_rel}/{job.parent.parent.name}/tasks/{job.name}", 1, error,
                    f"Operator action: correct {job} (dd-release-definition §5)")
            for job in (sorted(candidate.glob("tasks/*.md")) if candidate else [])
            for error in job_errors(job.read_text("utf-8"), f"tasks/{job.name}")]  # fmt: skip
    plan = candidate / "PLAN.md" if candidate else None
    if plan and plan.is_file():
        jobs += [finding(f"{dir_rel}/{plan.parent.name}/PLAN.md", 1, error,
                         f"Operator action: redesign the DAG table in {plan}")
                 for error in dag_errors(plan.read_text("utf-8"))]  # fmt: skip
    tasks = candidate / "TASKS.md" if candidate else None
    marks = list(MARK_RE.finditer(tasks.read_text("utf-8"))) if tasks and tasks.is_file() else []
    memory = _memory_tasks(marks, tasks, dir_rel) if tasks else []
    if phase not in TRIO_PHASES:
        return (_definition_findings(state, marks, f"{dir_rel}/{STATE}", candidate, specs)
                if candidate else []) + memory + jobs  # fmt: skip
    missing = [n for n in CANDIDATE_DOCS if not (candidate and (candidate / n).is_file())]
    if candidate is None or missing:
        where = candidate.name if candidate else "rc-<N>"
        return [finding(dir_rel, 1, f"phase {phase} is missing {where}/{', '.join(missing)}",
                        f"Operator action: define {', '.join(missing)} in {candidate or release_dir}"
                        " (dd-release-definition)")]  # fmt: skip
    return memory + jobs


def _memory_tasks(marks: list[re.Match[str]], tasks: Path, dir_rel: str) -> list[dict[str, Any]]:
    """A task whose `W:` writes `specs/memory`: memory is closure procedure, never a task."""
    fix = f"Operator action: drop the specs/memory path from that task's `W:` in {tasks}"
    return [finding(f"{dir_rel}/{tasks.parent.name}/TASKS.md", 1, f"task {line[:80]!r} writes "
                    "specs/memory — memory is closure procedure (RC-FLOW step 4)", fix)
            for line in (m[0].strip() for m in marks)
            if any(p.split("/")[:2] == ["specs", "memory"] for p in writes(line))]  # fmt: skip


def memory_errors(specs: Path, phase: str, entry: dict[str, Any]) -> list[str]:
    """Why *entry* reconciles nothing over its own [since, until]: what the `memory`
    verb refuses on."""
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
    if any(isinstance(e, dict) and e.get("kind") == "memory" and str(e.get("ts")) >= stamp
           for e in live.state.get("log") or []):  # fmt: skip
        return []
    message = (f"release is in CLOSURE with no `kind: memory` log entry stamped at or after "
               f"implemented.ts {stamp!r} — the closure reconciled no memory")  # fmt: skip
    fix = (f"Operator action: run `{SCRIPT} memory --specs {quote(str(specs))}` with the "
           "atom slugs the memory pass reviewed as --reviewed and changed as --changed")  # fmt: skip
    return [finding(f"releases/{live.release_id}/{STATE}", 1, message, fix)]


def refuse_open_bugs(specs: Path, release_id: str, release_dir: Path) -> None:
    """Candidate stacking has no bug gate; ship judges all persisted open records."""
    del specs, release_id, release_dir


def tree_findings(specs: Path) -> list[dict[str, Any]]:
    """Every live directory under ``releases/``, each archived state document, the
    one-live-release rule and the ship ledger — what `new` refuses on."""
    releases, findings = specs / "releases", []
    for d in sorted(releases.iterdir()) if releases.is_dir() else []:
        if SEMVER_RE.match(d.name):
            findings += _directory_findings(d, specs)
        elif d.name != "_archive" and (d / STATE).is_file():
            move = f"{d.resolve()} into its canon shape (a bare M.m.p id), or out of specs/"
            findings.append(finding(f"releases/{d.name}", 1, f"{d.name!r} is not a bare M.m.p "
                                    "release id, so it is not a live release",
                                    f"Operator action: move {move}"))  # fmt: skip
    if len(ids := live_ids(specs)) > 1:
        findings.append(finding("releases", 1, f"multiple live release directories carry "
                                f"{STATE}: {', '.join(ids)} — exactly one is allowed",
                                f"Operator action: keep one of {', '.join(ids)} live under "
                                f"{releases}; ship or move out the others"))  # fmt: skip
    if (specs / HISTO).is_file():
        findings += histo_findings((specs / HISTO).read_text(encoding="utf-8"), specs.resolve())
    for path in sorted(releases.glob(f"_archive/*/{STATE}")):
        # ADR 0152 (1): an archived state names its ship (F059). Not the live schema: the
        # 0.4.5-0.4.7 archives predate it (`ARCHIVED`, `rc`) and history is not rewritten.
        rel, act = path.relative_to(specs).as_posix(), f"rewrite {path.resolve()} as one JSON "
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            findings.append(finding(rel, 1, f"archived state is not valid JSON: {error}",
                                    f"Operator action: {act}object, from git history"))  # fmt: skip
            continue
        shipped = state.get("shipped") if isinstance(state, dict) else None
        if not (isinstance(shipped, dict) and SHA_RE.match(str(shipped.get("sha")))
                and "pr" in shipped and isinstance(shipped["pr"], int | None)):  # fmt: skip
            findings.append(finding(rel, 1, "archived release carries no shipped {sha, pr}",
                                    f"Operator action: {act}object whose shipped names the "
                                    "merged promote PR's sha"))  # fmt: skip
    return findings


def check(specs: Path) -> list[dict[str, Any]]:
    """The ONE release validator (the doctor delegates here): the tree, the live
    candidate's Origin, then the live CLOSURE's memory record."""
    return tree_findings(specs) + _origin_findings(specs) + _memory_findings(specs)


def ship_findings(specs: Path) -> list[dict[str, Any]]:
    """What `ship` refuses on: `check`'s errors, a phase short of CLOSURE (fix: that
    phase's NEXT verb), an archive already holding the id — one readiness authority (AC3.4)."""
    live = live_release(specs)
    found = [f for f in check(specs) if f["verdict"] == "error"]
    rel, phase = f"releases/{live.release_id}/{STATE}", str(live.state.get("phase"))
    if phase != "CLOSURE":
        found.append(finding(rel, 1, f"release {live.release_id} is in phase {phase!r} — "
                     "only a CLOSURE release ships",
                     f"{SCRIPT} {NEXT.get(phase, 'check')} --sha $(git rev-parse --short HEAD)"))  # fmt: skip
    if (archive := specs / "releases" / "_archive" / live.release_id).exists():
        found.append(finding(rel, 1, f"release {live.release_id} is live and already "
                     f"archived at {archive}", f"Operator action: decide which of "
                     f"{live.release_dir.resolve()} and {archive.resolve()} is release "
                                    f"{live.release_id}; a release ships once"))  # fmt: skip
    for record in records(specs / "bugs/BUGS.jsonl"):
        if record.get("status") == "open":
            bug_id = str(record.get("id"))
            found.append(
                finding(
                    "bugs/BUGS.jsonl",
                    1,
                    f"open bug {bug_id} blocks ship",
                    f"Operator action: resolve {bug_id} before ship",
                )
            )
    return found
