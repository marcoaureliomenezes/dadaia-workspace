#!/usr/bin/env python3
"""The exit's refusals and its terminal record — the ONE path out of ``active[]``.

Every refusal is raised BEFORE anything is written, so an item is never removed by a
call that then fails to record why it left. An exit is once-only and terminal: the
slug it names must be LIVE, and liveness is asked first, because a slug that already
exited must be told so rather than diagnosed for a status it no longer has.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import _bugs_store
import _clock
import _git
from _backlog_schema import DISPOSITIONS, HISTO
from _backlog_store import SCRIPT, Items
from _platform import act, command, run
from _refusal import Refusal, fix_of

#: `release.py`'s Origin parser, run as its own script: the one reader of the line.
_RELEASE = (
    Path(__file__).resolve().parents[2] / "dd-release-implementation" / "scripts" / "release.py"
)


def _origin_ids(spec: Path) -> list[str]:
    """The `backlog:` ids of *spec*'s first Origin line, as `release.py origin` prints them."""
    fix = command(sys.executable, str(_RELEASE), "origin", str(spec))
    try:
        done = run([sys.executable, str(_RELEASE), "origin", str(spec)], env=_git.scrubbed_env())
    except OSError as exc:
        raise Refusal(f"Origin unreadable: {exc}", fix) from exc
    if done.returncode:
        lines = done.stderr.splitlines()
        raise Refusal(
            f"Origin unreadable: {lines[0] if lines else done.returncode}", fix_of(done.stderr, fix)
        )
    return [ln[len("backlog ") :] for ln in done.stdout.splitlines() if ln.startswith("backlog ")]


def _release(specs: Path, slug: str, disposition: str, release: str | None) -> None:
    """*release* must name a folder directly under `releases/`, and that folder's candidate SPECs
    must name *slug* in an Origin's `backlog:` clause."""
    releases = specs / "releases"
    if release not in (
        {p.name for p in releases.iterdir() if p.is_dir()} if releases.is_dir() else set()
    ):
        raise Refusal(
            f"--release {release or '(none)'} names no folder directly under {releases}",
            act(
                "agent",
                f"pass --release with the release folder under {releases} whose SPEC "
                f"names {slug}, then rerun this exit with --disposition {disposition}.",
            ),
        )
    folder = releases / release
    if not any(slug in _origin_ids(s) for s in folder.glob("rc-*/SPEC.md")):
        raise Refusal(
            f"--release {release}: no {folder}/rc-<N>/SPEC.md first `**Origin:**` line "
            f"picks {slug!r} — only a release that picked an item can exit it as {disposition!r}",
            act(
                "agent",
                f"name {slug} in the backlog: clause of the first **Origin:** line "
                f"of a SPEC under {folder}, then rerun this exit with --disposition {disposition}.",
            ),
        )


def _reason(specs: Path, slug: str, disposition: str, reason: str | None) -> None:
    """The one-line why of a rejection."""
    if not (reason or "").strip():
        raise Refusal(
            f"{disposition!r} requires --reason: the histo record is the only trace of why {slug!r} left",
            act(
                "agent",
                f"rerun `{SCRIPT.inline('exit', slug, '--disposition', disposition, specs=specs)}` with a "
                f"one-line --reason saying why {slug} is refused.",
            ),
        )  # fmt: skip


def _bug(specs: Path, slug: str, disposition: str, reason: str | None) -> None:
    """The id of the BUGS.jsonl record the item is handed to, read by the bug store's reader."""
    bugs = specs / "bugs" / "BUGS.jsonl"
    ids = {record.get("id") for record in _bugs_store.read_records(bugs)}
    if reason not in ids:
        raise Refusal(
            f"--reason {reason!r} names no record of {bugs}: `to-bug` hands {slug!r} to a registered bug",
            act("operator", f"confirm {slug} as a bug (dd-bug-registration §2)"),
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
            command("grep", slug, str(specs / HISTO)),
        )
    if disposition not in EVIDENCE:
        raise Refusal(
            f"unknown disposition {disposition!r}: a backlog item exits as one of "
            f"{'|'.join(DISPOSITIONS)}",
            act("agent", "a postponed item stays in active[] and needs no exit."),
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
