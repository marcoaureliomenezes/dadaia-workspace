#!/usr/bin/env python3
"""The local metric table of one candidate: ledgers, verdict handoffs and git, no remote."""

from __future__ import annotations

import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from _git import fix_files, git, scrubbed_env
from _handoffs import reviewer_records
from _jsonl import parse_object
from _memory_drift import by_subject
from _platform import act, read_text, run
from _specs import check_release, context_row

_FREE = ("docs(memory)", "chore(release)", "chore(backlog)", "chore(bugs)", "docs(adr)", "chore(adrs)")  # fmt: skip
NA = "n/a"
_parse = datetime.fromisoformat
_ROWS = """1 fix-induced bugs\t{}\t<= 20%
2 first-pass approval\t{}\t>= 70%
4 closure duration\t{}\t<= 4 h
6 non-block commits after closure\t{}\t0
7 memory drift\t{}\t0
9 rebuild-due patches\t{}\t0
oldest record\t{}
"""


def _ratio(hit: int, total: int) -> str:
    return f"{hit}/{total} ({round(100 * hit / total)}%)" if total else NA


def _script(skill: str, script: str, *args: str, ok: tuple[int, ...] = (0,)) -> str | None:
    """The stdout of one sibling script, or None when its exit code is not in *ok*."""
    done = run([sys.executable, str(Path(__file__).resolve().parents[2] / skill / "scripts" / script), *args], env=scrubbed_env())  # fmt: skip
    return str(done.stdout) if done.returncode in ok else None


def _window(state: dict[str, Any], rc: str) -> tuple[str, str, str, bool, bool] | None:
    """(birth, previous CLOSURE or "", end, closed, newest) of a candidate the log names,
    where end is its CLOSURE stamp or now; None when the log never names it."""
    n = int(m) if (m := rc.rpartition("-rc")[2]).isdigit() else 0
    log = [(int(e["candidate"][3:]), e) for e in state.get("log") or [] if e.get("candidate")]
    mine = [e for k, e in log if k == n]
    if not mine:
        return None
    first = min(e["ts"] for e in mine)
    born = [e["ts"] for e in state["log"] if e.get("agent") == "release.py new" and e["ts"] <= first]  # fmt: skip
    now = datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    done = next((e for e in mine if e.get("milestone") == "implemented"), None)
    before = [e["ts"] for k, e in log if k < n and e.get("milestone") == "implemented"]
    newest = n >= max(k for k, _ in log)
    return (
        max(born, default=first),
        max(before, default=""),
        (done or {"ts": now})["ts"],
        done is not None,
        newest,
    )


def _merge(repo: Path, branch: str, sha: str) -> list[str]:
    """[sha, committer date] of the first merge on *branch*'s first-parent line that holds *sha*, or []."""
    holds = set(git(repo, "rev-list", "--ancestry-path", f"{sha}..{branch}", check=False).split())
    log = ("log", "--merges", "--first-parent", "--reverse", "--format=%H %cI", branch)
    merges = git(repo, *log, check=False).splitlines()
    return next((m.split() for m in merges if m.split()[0] in holds), [])


def _after_closure(repo: Path, sha: str | None, tip: str) -> str:
    if not sha:  # the candidate is not closed yet
        return NA
    raw = git(repo, "log", "--no-merges", "--format=%H%x00%B%x01", f"{sha}..{tip}", check=False)
    entries = [c.strip().partition("\0") for c in raw.split("\x01") if c.strip()]
    files = fix_files(repo, [h for h, _, _ in entries])
    return str(sum(not ((f := files.get(h)) and all(p.startswith("specs/audits/") for p in f) or text.startswith(_FREE) or re.search(r"^block:", text, re.M)) for h, _, text in entries))  # fmt: skip


def table(root: Path, specs: Path, rc: str) -> str:
    """The tab-separated metric table of candidate *rc* (`<M.m.p>-rc<N>`); absent data reads `n/a`; a release state `release.py check` refuses raises its Refusal."""
    repo = specs.parent
    check_release(specs)
    p = specs / "releases" / rc.partition("-rc")[0] / "_RELEASE.json"
    state = parse_object(read_text(p), act("agent", f"repair {p} until release.py check passes")) if p.is_file() else {}  # fmt: skip
    window = _window(state, rc)
    seen: list[str] = []
    vals = [NA] * 6
    if window:
        birth, prior, end, closed, newest = window
        version, _, n = rc.partition("-rc")
        closing = by_subject(repo, version, f"rc-{n}", "(?:phase|enters) CLOSURE")
        sha = closing[0] if closed and closing else None
        row = context_row(root, repo) or {}
        name, integration = row.get("name"), (row.get("gitflow") or {}).get("integration")
        trees: dict[str, list[tuple[str, str]]] = {}
        for _path, data in reviewer_records(root):
            if data.get("context") != name:
                continue
            at = str(data.get("produced_at"))
            seen.append(at)
            if birth <= at <= end:
                trees.setdefault(str(data.get("scope", "")).partition("@")[0], []).append((at, str(data.get("verdict"))))  # fmt: skip
        first = [min(t)[1] for t in trees.values()]
        merge = _merge(repo, integration, sha) if integration and sha else []
        bugs = _script("dd-bug-resolution", "bugs.py", "stats", "--specs", str(specs), "--closed-after", prior, "--closed-until", end)  # fmt: skip
        got = dict(ln.split("\t", 1) for ln in (bugs or "").splitlines() if "\t" in ln)
        drift = _script("dd-release-implementation", "release.py", "drift", "--json", "--specs", str(specs), ok=(0, 1)) if newest else None  # fmt: skip
        try:
            atoms = str(len(json.loads(drift or "")["atoms"]))
        except (ValueError, KeyError, TypeError):
            atoms = NA
        vals = [
            _ratio(int(got["fix-induced"]), int(got["closed"])) if "closed" in got else NA,
            _ratio(first.count("APPROVED"), len(first)),
            f"{(_parse(merge[1]) - _parse(end)).total_seconds() / 3600:.1f} h" if merge else NA,
            _after_closure(repo, sha, f"{merge[0]}^2" if merge else "HEAD")
            if sha or not closed
            else f"{NA} (no closure commit)",  # fmt: skip
            atoms,
            got.get("rebuild-due", NA),
        ]
    return "metric\tvalue\ttarget\n" + _ROWS.format(*vals, min(seen, default=NA))
