#!/usr/bin/env python3
"""The local metric table of one candidate: ledgers, verdict handoffs and git, no remote."""

from __future__ import annotations

import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import _bugs_store
from _git import git, scrubbed_env
from _handoffs import reviewer_records
from _platform import run
from _specs import run_cli

_FREE = ("docs(memory)", "chore(release)", "chore(backlog)", "chore(bugs)", "docs(adr)", "chore(adrs)")  # fmt: skip
NA = "n/a"


def _parse(stamp: str) -> datetime:
    return datetime.fromisoformat(stamp.replace("Z", "+00:00"))


def _ratio(hit: int, total: int) -> str:
    return f"{hit}/{total} ({round(100 * hit / total)}%)" if total else NA


def _script(skill: str, script: str, *args: str) -> str | None:
    """The stdout of one sibling script, or None when it fails."""
    done = run([sys.executable, str(Path(__file__).resolve().parents[2] / skill / "scripts" / script), *args], env=scrubbed_env())  # fmt: skip
    return None if done.returncode else str(done.stdout)


def _window(state: dict[str, Any], rc: str) -> tuple[str, str, str | None]:
    """(birth, end, closure sha): the candidate's birth, its CLOSURE stamp or now, its `implemented` sha."""
    n = f"rc-{rc.rpartition('-rc')[2]}"
    log = [e for e in state.get("log") or [] if isinstance(e, dict)]
    mine = [e for e in log if e.get("candidate") == n]
    first = min((e["ts"] for e in mine), default="9")
    born = [e["ts"] for e in log if e.get("kind") == "note" and str(e.get("text")).startswith("Candidate born")]  # fmt: skip
    birth = max((t for t in born if t <= first), default=max(born, default=""))
    done = next((e for e in mine if e.get("milestone") == "implemented"), None)
    now = datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    return birth, done["ts"] if done else now, done["sha"] if done else None


def _integration(root: Path, repo: str) -> str | None:
    done = run_cli(root, "context", "list", "--json", env=scrubbed_env())
    try:
        rows = json.loads(done.stdout)
        return str(next(r["gitflow"]["integration"] for r in rows if r.get("gitflow") and repo in (r["main_repo"], *(a["slug"] for a in r["associated_repos"]))))  # fmt: skip
    except (ValueError, StopIteration, TypeError, KeyError):
        return None


def _closure_hours(repo: Path, branch: str | None, sha: str | None, ts: str) -> str:
    if not (branch and sha):
        return NA
    out = git(repo, "log", "--merges", "--reverse", "--format=%cI", "--ancestry-path", f"{sha}..{branch}", check=False).split()  # fmt: skip
    return f"{(_parse(out[0]) - _parse(ts)).total_seconds() / 3600:.1f} h" if out else NA


def _after_closure(repo: Path, sha: str | None) -> str:
    if not sha:
        return NA
    raw = git(repo, "log", "--no-merges", "--format=%x00%s%n%b", f"{sha}..HEAD", check=False)
    commits = [c for c in raw.split("\0") if c.strip()]
    keep = [c for c in commits if not c.startswith(_FREE) and not re.search(r"^block:", c, re.M)]
    return str(len(keep))


def table(root: Path, specs: Path, rc: str) -> str:
    """The tab-separated metric table of candidate *rc* (`<M.m.p>-rc<N>`); absent data reads `n/a`."""
    repo = specs.parent
    state = json.loads((specs / "releases" / rc.partition("-rc")[0] / "_RELEASE.json").read_text(encoding="utf-8"))  # fmt: skip
    birth, end, sha = _window(state, rc)
    ledger = specs / "bugs"
    closed = [r for p in (ledger / "BUGS.jsonl", ledger / "_archive/bugs_histo.jsonl") if p.is_file() for r in _bugs_store.read_records(p) if birth <= str(r.get("closed_at") or "") <= end]  # fmt: skip
    trees: dict[str, list[tuple[str, str]]] = {}
    seen = []
    for _path, data in reviewer_records(root):
        at = str(data.get("produced_at"))
        seen.append(at)
        if birth <= at <= end:
            trees.setdefault(str(data.get("scope", "")).partition("@")[0], []).append((at, str(data.get("verdict"))))  # fmt: skip
    first = [min(t)[1] for t in trees.values()]
    drift = _script("dd-release-implementation", "release.py", "drift", "--json", "--specs", str(specs))  # fmt: skip
    stats = _script("dd-bug-resolution", "bugs.py", "stats", "--specs", str(specs))
    try:
        atoms = str(len(json.loads(drift or "")["atoms"]))
    except (ValueError, KeyError, TypeError):
        atoms = NA
    rows = (
        (
            "1 fix-induced bugs",
            _ratio(sum(r.get("caused_by") not in (None, "none") for r in closed), len(closed)),
            "<= 20%",
        ),  # fmt: skip
        ("2 first-pass approval", _ratio(first.count("APPROVED"), len(first)), ">= 70%"),
        (
            "4 closure duration",
            _closure_hours(repo, _integration(root, repo.name), sha, end),
            "<= 4 h",
        ),  # fmt: skip
        ("6 non-block commits after closure", _after_closure(repo, sha), "0"),
        ("7 memory drift", atoms, "0"),
        (
            "9 rebuild-due patches",
            NA if stats is None else str(stats.count("rebuild-due:")),
            "0",
        ),  # fmt: skip
    )
    lines = ["metric\tvalue\ttarget", *("\t".join(r) for r in rows), f"oldest record\t{min(seen, default=NA)}"]  # fmt: skip
    return "\n".join(lines) + "\n"
