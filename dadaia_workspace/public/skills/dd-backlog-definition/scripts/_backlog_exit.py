#!/usr/bin/env python3
"""The exit's refusals and its terminal record — the ONE path out of ``active[]``.

Every refusal is raised BEFORE anything is written, so an item is never removed by a
call that then fails to record why it left. An exit is once-only and terminal: the
slug it names must be LIVE, and liveness is asked first, because a slug that already
exited must be told so rather than diagnosed for a status it no longer has.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import _clock
import _git
from _backlog_schema import DISPOSITIONS
from _backlog_store import SCRIPT, Items
from _bugs_store import read_records
from _refusal import Refusal
from _specs import quote

#: `release.py`'s Origin parser, run as its own script: the one reader of the line.
_RELEASE = (
    Path(__file__).resolve().parents[2] / "dd-release-implementation" / "scripts" / "release.py"
)


def _origin_ids(spec: Path) -> list[str]:
    """The `backlog:` ids of *spec*'s first Origin line, as `release.py origin` prints them."""
    done = subprocess.run([sys.executable, str(_RELEASE), "origin", str(spec)], env=_git.scrubbed_env(),
                          capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)  # fmt: skip
    if done.returncode:
        lines = done.stderr.splitlines()
        fix = next((ln[5:] for ln in lines if ln.startswith("fix: ")), f"{sys.executable} {_RELEASE} origin {spec}")  # fmt: skip
        raise Refusal(f"Origin unreadable: {lines[0] if lines else done.returncode}", fix)
    return [ln[len("backlog ") :] for ln in done.stdout.splitlines() if ln.startswith("backlog ")]


def _picks(specs: Path, slug: str) -> list[str]:
    """Each release whose candidate SPEC (``rc-<N>/``) carries *slug* in its Origin's `backlog:` clause."""
    picks = {s.parents[1].name for s in (specs / "releases").glob("*/rc-*/SPEC.md") if slug in _origin_ids(s)}  # fmt: skip
    return sorted(picks, key=lambda v: [int(p) if p.isdigit() else -1 for p in v.split(".")])


def _release(specs: Path, slug: str, disposition: str, release: str | None) -> None:
    """A release whose candidate SPEC picked *slug*; the fix keeps the disposition."""
    picks = _picks(specs, slug)
    if release not in picks:
        raise Refusal(
            f"--release {release or '(none)'}: no releases/<v>/rc-<N>/SPEC.md first `**Origin:**` line "
            f"picks {slug!r} — only a release that picked an item can exit it as {disposition!r}",
            f"{SCRIPT} exit {slug} --disposition {disposition} --release {picks[-1]}" if picks
            else f"Operator action: name {slug} in the `backlog:` clause of a candidate SPEC's "
                 f"first `**Origin:**` line under {specs / 'releases'}, then rerun this exit.",
        )  # fmt: skip


def _reason(specs: Path, slug: str, disposition: str, reason: str | None) -> None:
    """The one-line why of a rejection."""
    if not (reason or "").strip():
        raise Refusal(
            f"{disposition!r} requires --reason: the histo record is the only trace of why {slug!r} left",
            f"Operator action: rerun `{SCRIPT} exit {slug} --disposition {disposition} --specs "
            f"{quote(str(specs))}` with a "
            f"one-line --reason saying why {slug} is refused.",
        )  # fmt: skip


def _bug(specs: Path, slug: str, disposition: str, reason: str | None) -> None:
    """The id of the BUGS.jsonl record the item is handed to, read by the bug skill's reader."""
    bugs = specs / "bugs" / "BUGS.jsonl"
    ids = {record.get("id") for record in read_records(bugs)}
    if reason not in ids:
        raise Refusal(
            f"--reason {reason!r} names no record of {bugs}: `to-bug` hands {slug!r} to a registered bug",
            f"Operator action: register the bug {slug} becomes with bugs.py append "
            f"(dd-bug-registration), then rerun `{SCRIPT} exit {slug} --disposition {disposition} "
            f"--specs {quote(str(specs))}` "
            "with its id as --reason.",
        )  # fmt: skip


#: Each terminal word -> the evidence flag it carries and its verifier; the histo record
#: is the only surviving trace of why the item left.
EVIDENCE = {
    "delivered": ("release", _release),
    "superseded": ("release", _release),
    "rejected": ("reason", _reason),
    "to-bug": ("reason", _bug),
}


def check_exit(specs: Path, active: Items, slug: str, values: dict[str, Any]) -> dict[str, Any]:
    """Refuse, before any write, an exit whose subject is not live or whose evidence does
    not match its disposition. Returns the entry the exit will remove."""
    disposition = values["disposition"]
    entry = next((item for item in active if item.get("id") == slug), None)
    if entry is None:
        raise Refusal(
            f"{slug!r} does not name a live active[] entry — an item is retained forever, "
            "so a slug missing from active[] has already exited",
            f"grep {slug} specs/backlog/_archive/backlog_histo.jsonl",
        )
    if disposition not in EVIDENCE:
        raise Refusal(
            f"unknown disposition {disposition!r}: a backlog item exits as one of "
            f"{'|'.join(DISPOSITIONS)}",
            "Operator action: a postponed item stays in active[] and needs no exit.",
        )
    flag, verify = EVIDENCE[disposition]
    verify(specs, slug, disposition, values[flag])
    return entry


def histo_record(entry: dict[str, Any], values: dict[str, Any]) -> dict[str, Any]:
    """The one histo-record-v1 shape: ``entry`` IS the removed object."""
    return {
        "id": entry["id"],
        "ts": _clock.today(),
        "disposition": values["disposition"],
        "release": values["release"],
        "reason": values["reason"],
        "summary": values.get("summary"),
        "entry": entry,
    }
