"""The candidate-archive verb (release 0.4.6 FR4, ADR 0008) — the deterministic
mechanics behind ``dadaia release rc-archive``.

The release-candidates model (ADRs 0005–0009): a release has OPEN scope and grows by
stacked candidates; each candidate is one closed-scope SDD cycle whose SPEC/PLAN/TASKS
trio lives at the release root. When the operator rules "continue" at the
promote-or-continue gate, this verb archives the completed trio into the next
``rc-N/`` folder so a fresh trio can be born at root — the version never increments,
no new branch is cut. The question itself is agent protocol (DADAIA §3.5 — a hook
never blocks a human); this module is only the mechanics.

One deep verb, zero options: everything a caller must know is "archive the live
candidate"; validation (trio present, every task ``[x]``, phase CLOSURE), numbering,
the move, the counter bump, the DISCOVERY reset and the canonical
:data:`~dadaia_workspace.core.release_state.RELEASE_STATE_FILENAME` write all live
behind it.
"""

from __future__ import annotations

import datetime as _dt
import json
import re
from dataclasses import dataclass
from pathlib import Path

from dadaia_workspace.core.release_state import RELEASE_STATE_FILENAME, release_state_file
from dadaia_workspace.features.specs.doctor_common import resolve_live_release_id

__all__ = ["CandidateArchive", "CandidateArchiveError", "archive_candidate"]

#: The closed-scope candidate trio that moves from the release root into ``rc-N/``.
_TRIO = ("SPEC.md", "PLAN.md", "TASKS.md")

#: An archived-candidate folder name (canon ``_RC``): ``rc-1``, ``rc-2``, …
_RC_DIR_RE = re.compile(r"^rc-(\d+)$")

#: Task markers that mean the candidate is NOT closed: open ``[ ]`` or reserved ``[-]``.
_UNFINISHED_MARKER_RE = re.compile(r"^\s*-\s\[( |-)\]\s", re.MULTILINE)


class CandidateArchiveError(Exception):
    """The candidate cannot be archived — the message names the exact refusal."""


@dataclass(frozen=True)
class CandidateArchive:
    """The completed archival: which release, which ``rc-N`` the trio landed in."""

    release: str
    rc: int
    rc_dir: Path


def _utc_now() -> str:
    return _dt.datetime.now(_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def archive_candidate(specs_dir: Path) -> CandidateArchive:
    """Archive the live release's completed candidate trio into the next ``rc-N/``.

    Refuses (``CandidateArchiveError``) unless: exactly one live release exists, its
    trio is present at the release root, its TASKS carry no open ``[ ]`` or reserved
    ``[-]`` marker, and its phase is ``CLOSURE``. On success the trio moves to
    ``rc-N/`` (N = highest existing + 1), the state document records ``rc = N`` with a
    log entry, phase resets to ``DISCOVERY`` (between candidates), and the document is
    always written under the canonical filename — a legacy ``RELEASE.json`` is renamed
    in the same act.
    """
    release_id, err = resolve_live_release_id(specs_dir)
    if err:
        raise CandidateArchiveError(err)
    if release_id is None:
        raise CandidateArchiveError("no live release under specs/releases/ — nothing to archive.")
    release_dir = specs_dir / "releases" / release_id

    missing = [name for name in _TRIO if not (release_dir / name).is_file()]
    if missing:
        raise CandidateArchiveError(
            f"release {release_id} has no complete candidate trio at root — "
            f"missing: {', '.join(missing)}."
        )

    tasks_text = (release_dir / "TASKS.md").read_text(encoding="utf-8")
    unfinished = _UNFINISHED_MARKER_RE.findall(tasks_text)
    if unfinished:
        raise CandidateArchiveError(
            f"TASKS.md still carries {len(unfinished)} open '[ ]'/reserved '[-]' "
            "marker(s) — a candidate archives only fully implemented ([x])."
        )

    state_path = release_state_file(release_dir)
    if state_path is None:
        raise CandidateArchiveError(f"release {release_id} carries no state document.")
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CandidateArchiveError(f"unreadable state document {state_path.name}: {exc}") from exc
    phase = state.get("phase")
    if phase != "CLOSURE":
        raise CandidateArchiveError(
            f"release {release_id} is in phase {phase!r} — a candidate archives only "
            "from CLOSURE (finish the cycle first)."
        )

    existing = [
        int(m.group(1))
        for d in release_dir.iterdir()
        if d.is_dir() and (m := _RC_DIR_RE.match(d.name))
    ]
    rc = max(existing, default=0) + 1
    rc_dir = release_dir / f"rc-{rc}"
    rc_dir.mkdir()
    for name in _TRIO:
        (release_dir / name).rename(rc_dir / name)

    state["rc"] = rc
    state["phase"] = "DISCOVERY"
    state.setdefault("log", []).append(
        {
            "ts": _utc_now(),
            "agent": "release-candidates",
            "kind": "note",
            "text": (
                f"Candidate {rc} archived to rc-{rc}/ (operator ruled continue at the "
                "promote-or-continue gate); root is ready for the next candidate's trio."
            ),
        }
    )
    canonical = release_dir / RELEASE_STATE_FILENAME
    canonical.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if state_path.name != RELEASE_STATE_FILENAME:
        state_path.unlink()
    return CandidateArchive(release=release_id, rc=rc, rc_dir=rc_dir)
