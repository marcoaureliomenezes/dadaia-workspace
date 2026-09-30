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
from _release_check import finding, histo_findings, state_findings  # noqa: E402
from _release_schema import HISTO, SEMVER_RE, STATE, TRIO, TRIO_PHASES  # noqa: E402
from _release_store import SCRIPT, Refusal, live_ids, live_release, window_start  # noqa: E402
from _specs import with_specs  # noqa: E402

__all__ = ["check", "drift", "memory_errors", "tree_findings"]


def _directory_findings(release_dir: Path, specs: Path) -> list[dict[str, Any]]:
    """One live directory: its state document, then its trio in IMPLEMENTATION/CLOSURE."""
    dir_rel, path = release_dir.relative_to(specs).as_posix(), release_dir / STATE
    if not path.is_file():
        return [finding(dir_rel, 1, f"release directory carries no {STATE}")]
    text = path.read_text(encoding="utf-8")
    if findings := state_findings(text, f"{dir_rel}/{STATE}"):
        return findings
    phase = json.loads(text)["phase"]
    missing = [n for n in TRIO if not (release_dir / n).is_file()] if phase in TRIO_PHASES else []
    return (
        [finding(dir_rel, 1, f"phase {phase} is missing {', '.join(missing)}")] if missing else []
    )


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
    """The ONE release validator (the doctor delegates here): the tree, then the live
    CLOSURE's memory record."""
    return tree_findings(specs) + _window_findings(specs)
