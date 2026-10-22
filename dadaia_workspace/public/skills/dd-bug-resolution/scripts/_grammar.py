#!/usr/bin/env python3
"""The shared name grammars of releases and candidates, and the folder decisions that apply them."""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path

from _platform import act
from _refusal import Refusal

STATE = "_RELEASE.json"
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
#: A candidate folder; the live one is the highest N.
CANDIDATE_RE = re.compile(r"^rc-([1-9][0-9]*)$")
#: A context name or repo slug used as a path component: no ``.``, ``/`` or ``\`` (CWE-22).
CONTEXT_NAME_RE = re.compile(r"[A-Za-z0-9_-]+")
TAG_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")
TASK_ID_RE = re.compile(r"^J[1-9][0-9]*(?:\.S[1-9][0-9]*)?\.T[1-9][0-9]*$")
#: The head of a closed release's task line (a checklist item or a table cell), read by lineage only.
HISTORICAL_TASK_RE = re.compile(
    r"^(?:- \[.\]\s*|\|\s*)\**(T-[0-9]+-[0-9]+[A-Z]?|J[A-Z]\.S[1-9][0-9]*\.T[1-9][0-9]*)\b"
)
STATUS_RE = re.compile(r"^\*\*Status:\*\*\s*(.+?)\s*$", re.MULTILINE)
#: A git object id as a human pastes it from a merge: short (7) to full (40), or SHA-256 (64).
SHA_RE = re.compile(r"^(?:[0-9a-f]{7,40}|[0-9a-f]{64})$")
#: A full git object id, SHA-1 (40) or SHA-256 (64) hex; the all-zero id matches it.
OBJECT_ID_RE = re.compile(r"^[0-9a-fA-F]{40}$|^[0-9a-fA-F]{64}$")


def is_zero_object_id(sha: str | bytes) -> bool:
    """Whether *sha* is git's absent-object id: exactly 40 or 64 zeros, nothing else."""
    text = sha.decode("ascii", "replace") if isinstance(sha, bytes) else sha
    return bool(OBJECT_ID_RE.fullmatch(text)) and not text.strip("0")


def candidate_number(names: Iterable[str]) -> int:
    """The highest ``rc-<N>`` among *names*, 0 when none — the live candidate's number."""
    return max((int(m.group(1)) for n in names if (m := CANDIDATE_RE.match(n))), default=0)


def candidate_dir(release_dir: Path) -> Path | None:
    """The highest-numbered ``rc-<N>/`` under *release_dir*; ``None`` when there is none."""
    n = candidate_number(d.name for d in release_dir.iterdir() if d.is_dir())
    return release_dir / f"rc-{n}" if n else None


def sole_live(specs: Path) -> str | None:
    """The one live release id, ``None`` when none is live; :class:`Refusal` when several are."""
    ids = live_ids(specs)
    if len(ids) > 1:
        raise Refusal(f"multiple live release directories carry {STATE}: {', '.join(ids)} — exactly one is allowed",
                      act("agent", f"keep one of {', '.join(ids)} live under {specs / 'releases'}; ship or move out the others"))  # fmt: skip
    return ids[0] if ids else None


def live_ids(specs: Path) -> list[str]:
    """Every SemVer-named release directory directly under ``releases/`` carrying a state
    document — `_archive` is not live."""
    releases = specs / "releases"
    if not releases.is_dir():
        return []
    return sorted(
        d.name
        for d in releases.iterdir()
        if d.is_dir() and SEMVER_RE.match(d.name) and (d / STATE).is_file()
    )
