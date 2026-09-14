"""The two archive verbs — ``dadaia release rc-archive`` (0.4.6 FR4, ADR 0008) and
``dadaia release archive`` (0.4.7 FR3) — the deterministic mechanics of the
promote-or-continue gate's two answers.

The release-candidates model (ADRs 0005–0009): a release has OPEN scope and grows by
stacked candidates; each candidate is one closed-scope SDD cycle whose SPEC/PLAN/TASKS
trio lives at the release root. When the operator rules "continue" at the
promote-or-continue gate, this verb archives the completed trio into the next
``rc-N/`` folder so a fresh trio can be born at root — the version never increments,
no new branch is cut. The question itself is agent protocol (DADAIA §3.5 — a hook
never blocks a human); this module is only the mechanics.

"Promote" is :func:`archive_release`: it replaces RC-FLOW steps 9–12's hand-driven
``git mv`` into ``_archive/<id>/``, hand-appended histo record and hand-cut next
release with ONE transactional verb. The two share this module because they share the
same preamble — :func:`_load_live_release` (validate the tree, resolve the one live
release, read its state) and the same ``[x]`` marker rule — and the same law: nothing
is written unless everything can be.

One deep verb each, zero options: everything a caller must know is "archive the live
candidate" / "ship the live release"; validation, numbering, the move, the counter
bump, the phase reset and the canonical
:data:`~dadaia_workspace.core.release_state.RELEASE_STATE_FILENAME` write all live
behind them. Neither verb runs git, and neither knows what a bug ledger is — the CLI
composes ``bugs archive`` on top (P-07: features compose through the CLI/container).
"""

from __future__ import annotations

import datetime as _dt
import json
import re
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dadaia_workspace.core.kernel_tunables import DADAIA_BIN
from dadaia_workspace.core.models.histo import RELEASES_HISTO_DISPOSITIONS, HistoRecord
from dadaia_workspace.core.release_state import RELEASE_STATE_FILENAME, release_state_file
from dadaia_workspace.core.spec_status import extract_status
from dadaia_workspace.core.specs_version import is_release_semver
from dadaia_workspace.features.specs.canon import release_new
from dadaia_workspace.features.specs.doctor_common import resolve_live_release_id
from dadaia_workspace.features.specs.release_tree import validate_release_tree

__all__ = [
    "ReleaseFold",
    "fold_release",
    "ArchiveError",
    "CandidateArchive",
    "ReleaseArchive",
    "archive_candidate",
    "archive_release",
]

#: A shipped commit sha as a human pastes it from a merge: short (7) to full (40).
_SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")

#: The closed-scope candidate trio that moves from the release root into ``rc-N/``.
_TRIO = ("SPEC.md", "PLAN.md", "TASKS.md")

#: An archived-candidate folder name (canon ``_RC``): ``rc-1``, ``rc-2``, …
_RC_DIR_RE = re.compile(r"^rc-(\d+)$")

#: Task markers that mean the candidate is NOT closed: open ``[ ]`` or reserved ``[-]``.
_UNFINISHED_MARKER_RE = re.compile(r"^\s*-\s\[( |-)\]\s.*$", re.MULTILINE)


class ArchiveError(Exception):
    """The candidate cannot be archived — the message names the exact refusal."""


@dataclass(frozen=True)
class CandidateArchive:
    """The completed archival: which release, which ``rc-N`` the trio landed in."""

    release: str
    rc: int
    rc_dir: Path


@dataclass(frozen=True)
class ReleaseArchive:
    """The completed promotion: where the release landed, which record it left behind,
    and where its successor was born."""

    release: str
    rc: int | None
    archived_dir: Path
    histo_id: str
    next_release: str
    next_spec: Path


@dataclass(frozen=True)
class _LiveRelease:
    """The one live release, already proven valid — the preamble both verbs share."""

    release_id: str
    release_dir: Path
    state_path: Path
    state: dict[str, Any]


def _load_live_release(specs_dir: Path, verb: str) -> _LiveRelease:
    """Validate the whole release tree, resolve the ONE live release, read its state.

    Nothing moves until :func:`~dadaia_workspace.features.specs.release_tree
    .validate_release_tree` passes on the whole tree: archiving from an invalid tree
    mints a second invalid document in the archive and makes the damage harder to see,
    which is exactly how the pre-Wave-0 0.4.6 document survived unnoticed. One
    validator, shared with ``dadaia doctor`` and with both verbs — never a second
    opinion here.
    """
    tree_issues = validate_release_tree(specs_dir)
    if tree_issues:
        listed = "\n".join(f"  {i.path}: {i.code} — {i.message}" for i in tree_issues)
        raise ArchiveError(
            f"the release tree carries {len(tree_issues)} issue(s); a release archives "
            f"only from a valid tree:\n{listed}\n"
            f"fix: {DADAIA_BIN} doctor --fix (then re-run "
            f"{DADAIA_BIN} release {verb})"
        )
    release_id, err = resolve_live_release_id(specs_dir)
    if err:
        raise ArchiveError(err)
    if release_id is None:
        raise ArchiveError(
            "no live release under specs/releases/ — nothing to archive.\n"
            f"fix: {DADAIA_BIN} release new <M.m.p>"
        )
    release_dir = specs_dir / "releases" / release_id
    state_path = release_state_file(release_dir)
    if state_path is None:
        raise ArchiveError(f"release {release_id} carries no state document.")
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ArchiveError(f"unreadable state document {state_path.name}: {exc}") from exc
    return _LiveRelease(release_id, release_dir, state_path, state)


def _unfinished_tasks(release_dir: Path) -> list[str]:
    """The ``[ ]``/``[-]`` task lines TASKS.md still carries (empty = the candidate is
    implemented). A missing TASKS.md carries none — its absence is the trio rule's
    business, not this one's. The LINES, not a count: a refusal names the task that
    blocks it, and a count is one `len()` away."""
    tasks = release_dir / "TASKS.md"
    if not tasks.is_file():
        return []
    return [
        match.group(0).strip()
        for match in _UNFINISHED_MARKER_RE.finditer(tasks.read_text(encoding="utf-8"))
    ]


def _utc_now() -> str:
    return _dt.datetime.now(_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def archive_candidate(specs_dir: Path) -> CandidateArchive:
    """Archive the live release's completed candidate trio into the next ``rc-N/``.

    Refuses (``ArchiveError``) unless: the release tree is valid, exactly one live
    release exists, its trio is present at the release root, its TASKS carry no open
    ``[ ]`` or reserved ``[-]`` marker, and its phase is ``CLOSURE``. On success the
    trio moves to ``rc-N/`` (N = highest existing + 1), the state document records
    ``rc = N`` with a log entry, phase resets to ``DEFINITION`` (the next candidate's
    trio is authored there — 0.4.7 FR4 deleted the ``DISCOVERY`` phase this used to
    park in), and the document is always written under the canonical filename — a
    legacy ``RELEASE.json`` is renamed in the same act.
    """
    live = _load_live_release(specs_dir, "rc-archive")
    release_id, release_dir, state_path, state = (
        live.release_id,
        live.release_dir,
        live.state_path,
        live.state,
    )

    missing = [name for name in _TRIO if not (release_dir / name).is_file()]
    if missing:
        raise ArchiveError(
            f"release {release_id} has no complete candidate trio at root — "
            f"missing: {', '.join(missing)}."
        )

    unfinished = _unfinished_tasks(release_dir)
    if unfinished:
        raise ArchiveError(
            f"TASKS.md still carries {len(unfinished)} open '[ ]'/reserved '[-]' "
            f"marker(s) — a candidate archives only fully implemented ([x]): "
            f"{unfinished[0]}"
        )

    phase = state.get("phase")
    if phase != "CLOSURE":
        raise ArchiveError(
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
    state["phase"] = "DEFINITION"
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


# ═════════════════════════════════════════════════════════════════════════════════
# ── release phase — the ONE writer of `phase`, `defined` and `implemented` ────────
# ═════════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class PhaseChange:
    """The completed transition: which release moved to which phase, and when."""

    release: str
    phase: str
    ts: str


#: The one ordered lane a candidate walks. ``DEFINITION`` is written by ``release
#: new``/``rc-archive`` and ``ARCHIVED`` by ``release archive`` — this verb owns the two
#: transitions in between, each from exactly one predecessor, so an out-of-order move
#: and a re-run are the same single check.
_PHASE_PREDECESSOR: dict[str, str] = {
    "IMPLEMENTATION": "DEFINITION",
    "CLOSURE": "IMPLEMENTATION",
}


def _refuse_unapproved_trio(release_dir: Path, release_id: str) -> None:
    """A candidate enters IMPLEMENTATION only with all three documents ``Aprovado`` —
    the same status token ``dd-spec-navigator`` reads, parsed by the one extractor."""
    for name in _TRIO:
        document = release_dir / name
        if not document.is_file():
            raise ArchiveError(
                f"release {release_id} has no {name} at root — a candidate is defined by "
                "its trio.\n"
                f"fix: {DADAIA_BIN} release new {release_id}"
            )
        status = extract_status(document.read_text(encoding="utf-8"))
        if status != "Aprovado":
            raise ArchiveError(
                f"specs/releases/{release_id}/{name} carries status {status!r} — a "
                "candidate enters IMPLEMENTATION only once SPEC, PLAN and TASKS are all "
                "'**Status:** Aprovado'.\n"
                f"fix: sed -i 's/^\\*\\*Status:\\*\\* .*/**Status:** Aprovado/' "
                f"specs/releases/{release_id}/{name}"
            )


def set_phase(specs_dir: Path, phase: str, *, sha: str) -> PhaseChange:
    """Move the live release to *phase* and stamp the milestone that phase records.

    The ONE writer of ``phase``, ``defined`` and ``implemented`` (0.4.7 FR5). These
    three fields were Read-then-Edit, which is how candidate 1 reached a state where
    ``release archive`` refused on a hand-set ``implemented`` that ``archive`` itself
    validated: a document with two writers, one of them indistinguishable from a typo.

    - ``IMPLEMENTATION`` requires the trio at root, all ``Aprovado``, and stamps
      ``defined {sha, ts}`` (re-stamped when a later candidate is defined).
    - ``CLOSURE`` requires every task ``[x]`` and stamps ``implemented {sha, rc, ts}``
      where ``rc`` names the candidate being closed (the archived count + 1).

    Refuses — writing nothing — an unknown target, an out-of-order or repeated
    transition, an unapproved document, an unfinished task, or a malformed sha. One
    ``note`` is appended per transition; the state document is always written under the
    canonical filename.
    """
    if not _SHA_RE.match(sha):
        raise ArchiveError(
            f"--sha {sha!r} is not a 7-40 character hex commit sha.\n"
            f"fix: {DADAIA_BIN} release phase {phase} --sha $(git rev-parse --short HEAD)"
        )
    if phase not in _PHASE_PREDECESSOR:
        raise ArchiveError(
            f"{phase!r} is not a phase this verb writes: DEFINITION is written by "
            "`release new`/`release rc-archive` and ARCHIVED by `release archive`.\n"
            f"fix: {DADAIA_BIN} release phase IMPLEMENTATION --sha {sha}"
        )

    live = _load_live_release(specs_dir, f"phase {phase}")
    current = live.state.get("phase")
    expected = _PHASE_PREDECESSOR[phase]
    if current != expected:
        raise ArchiveError(
            f"release {live.release_id} is in phase {current!r} — {phase} follows "
            f"{expected} exactly once.\n"
            f"fix: {DADAIA_BIN} release phase {expected} --sha {sha}"
            if current != phase
            else (
                f"release {live.release_id} is already in phase {phase!r} — a transition "
                "happens once per candidate.\n"
                f"fix: {DADAIA_BIN} release rc-archive"
            )
        )

    ts = _utc_now()
    state = live.state
    if phase == "IMPLEMENTATION":
        _refuse_unapproved_trio(live.release_dir, live.release_id)
        state["defined"] = {"sha": sha, "ts": ts}
        text = f"Candidate defined at {sha}; phase IMPLEMENTATION."
    else:
        unfinished = _unfinished_tasks(live.release_dir)
        if unfinished:
            raise ArchiveError(
                f"TASKS.md still carries {len(unfinished)} open '[ ]'/reserved '[-]' "
                f"marker(s) — a candidate closes fully implemented: {unfinished[0]}\n"
                f"fix: sed -i 's/^- \\[-\\]/- [x]/' "
                f"specs/releases/{live.release_id}/TASKS.md"
            )
        rc = int(state.get("rc") or 0) + 1
        state["implemented"] = {"sha": sha, "rc": rc, "ts": ts}
        text = f"Candidate {rc} implemented at {sha}; phase CLOSURE."

    state["phase"] = phase
    state.setdefault("log", []).append(
        {"ts": ts, "agent": "release-candidates", "kind": "note", "text": text}
    )
    canonical = live.release_dir / RELEASE_STATE_FILENAME
    canonical.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if live.state_path.name != RELEASE_STATE_FILENAME:
        live.state_path.unlink()
    return PhaseChange(release=live.release_id, phase=phase, ts=ts)


def _refuse_bad_arguments(shipped_sha: str, pr: int, next_release: str) -> None:
    """The three operator-supplied values, checked before anything is read from disk."""
    if not _SHA_RE.match(shipped_sha):
        raise ArchiveError(
            f"--shipped {shipped_sha!r} is not a commit sha (7–40 lowercase hex).\n"
            "--shipped takes the sha of the develop -> main merge commit:\n"
            "fix: git rev-parse origin/main"
        )
    if pr <= 0:
        raise ArchiveError(
            f"--pr {pr} is not a pull-request number.\n"
            "--pr takes the ship PR's number:\n"
            "fix: gh pr list --state merged --base main --limit 1"
        )
    if not is_release_semver(next_release):
        raise ArchiveError(
            f"--next {next_release!r} is not bare SemVer M.m.p.\n"
            "--next takes the next patch of the published version:\n"
            f"fix: {DADAIA_BIN} release archive <id> --next 1.2.4"
        )


def _histo_summary(release_id: str, shipped_sha: str, pr: int, state: dict[str, Any]) -> str:
    """``shipped <sha> PR #<n>; rc=<rc>; <the last `summary` log entry's text>`` — the
    release's whole exit, in the one free-text field the histo record has for it."""
    parts = [f"shipped {shipped_sha} PR #{pr}", f"rc={state.get('rc')}"]
    last = [
        entry.get("text")
        for entry in state.get("log", [])
        if isinstance(entry, dict) and entry.get("kind") == "summary" and entry.get("text")
    ]
    if last:
        parts.append(str(last[-1]))
    return "; ".join(parts) + f" ({release_id})"


def archive_release(
    specs_dir: Path,
    release_id: str,
    *,
    shipped_sha: str,
    pr: int,
    next_release: str,
    histo_append: Callable[[HistoRecord], None],
) -> ReleaseArchive:
    """Ship the live release: the promote lane as ONE transactional verb (0.4.7 FR3).

    Refuses — writing NOTHING — unless the release tree is valid, *release_id* IS the
    one live release, its TASKS carry no ``[ ]``/``[-]`` marker, its phase is
    ``CLOSURE``, its ``implemented`` milestone is set, ``_archive/<id>/`` is free, and
    *shipped_sha*/*pr*/*next_release* are well-formed. Every refusal names an
    executable ``fix:``.

    On success, in this order:

    1. write ``shipped {sha, pr, ts}``, ``phase: ARCHIVED`` and one ``note`` log entry
       into the state document (canonical filename; a legacy ``RELEASE.json`` is
       removed in the same act);
    2. move the whole ``releases/<id>/`` directory to ``releases/_archive/<id>/`` —
       the final trio stays at the release root inside it (ADR 0009);
    3. birth *next_release* through :func:`~dadaia_workspace.features.specs.canon
       .release_new` — the ONE birth act, which only works because step 2 already
       freed the single-live-release slot;
    4. append the ONE :class:`~dadaia_workspace.core.models.histo.HistoRecord` LAST.

    The histo append is last on purpose: it is the only step with an append-only
    external ledger behind it, and being last means the record exists if and only if
    every filesystem step already succeeded — there is no truncation path to get
    wrong. Everything before it rolls back here (the birthed directory is removed, the
    move is reversed, the original state bytes are restored), so a failure anywhere
    leaves the tree byte-identical and the operator re-runs one verb.

    *histo_append* is injected rather than built: ``features/specs`` owns no ledger
    file and imports no infrastructure — the CLI hands it a ``JsonlRecordStore``
    append, a test hands it a list.
    """
    _refuse_bad_arguments(shipped_sha, pr, next_release)
    live = _load_live_release(specs_dir, "archive")
    if live.release_id != release_id:
        raise ArchiveError(
            f"{release_id} is not the live release ({live.release_id} is).\n"
            f"fix: {DADAIA_BIN} release archive {live.release_id} "
            f"--shipped {shipped_sha} "
            f"--pr {pr} --next {next_release}"
        )
    release_dir, state_path, state = live.release_dir, live.state_path, live.state

    unfinished = _unfinished_tasks(release_dir)
    if unfinished:
        raise ArchiveError(
            f"TASKS.md still carries {len(unfinished)} open '[ ]'/reserved '[-]' marker(s) — "
            "a release ships only fully implemented work.\n"
            f"fix: flip the open task markers to [x] in specs/releases/{release_id}/TASKS.md"
        )
    if state.get("phase") != "CLOSURE":
        # ONE check, not two (0.4.7 FR5): `phase` and `implemented` are written by the
        # same act — `dadaia release phase CLOSURE` — so a release in CLOSURE always
        # carries the milestone. The separate `implemented` refusal this verb used to
        # raise existed only because a hand edit could set one without the other, and
        # candidate 1's reviewer found `archive` hanging on exactly that.
        raise ArchiveError(
            f"release {release_id} is in phase {state.get('phase')!r} — a release "
            "archives only from CLOSURE.\n"
            f"fix: {DADAIA_BIN} release phase CLOSURE --sha <implementation-tip-sha>"
        )

    archive_root = specs_dir / "releases" / "_archive"
    destination = archive_root / release_id
    if destination.exists():
        raise ArchiveError(
            f"{destination.relative_to(specs_dir).as_posix()} already exists — "
            "this release is already archived.\n"
            "fix: inspect it and remove the stale copy before re-running the verb."
        )
    next_dir = specs_dir / "releases" / next_release
    if next_dir.exists() or (archive_root / next_release).exists():
        raise ArchiveError(
            f"release {next_release} already exists — --next must name an unused "
            "version.\n"
            f"fix: {DADAIA_BIN} release archive <id> --next "
            f"{_bump_patch(next_release)}"
        )

    original_bytes = state_path.read_bytes()
    shipped_state = dict(state)
    shipped_state["shipped"] = {"sha": shipped_sha, "pr": pr, "ts": _utc_now()}
    shipped_state["phase"] = "ARCHIVED"
    shipped_state["log"] = [*state.get("log", [])] + [
        {
            "ts": _utc_now(),
            "agent": "release-candidates",
            "kind": "note",
            "text": (
                f"Shipped {shipped_sha} (PR #{pr}); release archived to "
                f"_archive/{release_id}/ and {next_release} born."
            ),
        }
    ]

    canonical = release_dir / RELEASE_STATE_FILENAME
    legacy = state_path if state_path.name != RELEASE_STATE_FILENAME else None
    moved = False
    born: Path | None = None
    try:
        canonical.write_text(
            json.dumps(shipped_state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        if legacy is not None:
            legacy.unlink()
        archive_root.mkdir(parents=True, exist_ok=True)
        release_dir.rename(destination)
        moved = True
        next_spec = release_new(specs_dir, next_release)
        born = next_spec.parent
        record = HistoRecord(
            id=release_id,
            ts=_utc_now(),
            disposition=RELEASES_HISTO_DISPOSITIONS[0],
            release=release_id,
            reason=None,
            summary=_histo_summary(release_id, shipped_sha, pr, state),
            entry=None,
        )
        histo_append(record)
    except BaseException:
        if born is not None:
            shutil.rmtree(born, ignore_errors=True)
        if moved:
            destination.rename(release_dir)
        if legacy is not None:
            canonical.unlink(missing_ok=True)
        state_path.write_bytes(original_bytes)
        raise
    return ReleaseArchive(
        release=release_id,
        rc=shipped_state.get("rc"),
        archived_dir=destination,
        histo_id=record.id,
        next_release=next_release,
        next_spec=next_spec,
    )


def _bump_patch(version: str) -> str:
    """``1.2.3`` -> ``1.2.4`` — the suggestion in the "--next already exists" fix line."""
    major, minor, patch = version.split(".")
    return f"{major}.{minor}.{int(patch) + 1}"


# ═════════════════════════════════════════════════════════════════════════════════
# ── release fold — the archive holds PUBLISHED versions only (ADR 0014) ───────────
# ═════════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class ReleaseFold:
    """The completed fold: which archived release became which candidate of which
    published version, where its trio now lives, and the histo records rewritten."""

    folded: str
    into: str
    rc: int | None
    placed_at: Path
    target_dir: Path
    histo_ids: tuple[str, ...]


def _semver_key(release_id: str) -> tuple[int, ...]:
    return tuple(int(part) for part in release_id.split("."))


def _read_state(path: Path) -> dict[str, Any]:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ArchiveError(f"unreadable state document {path}: {exc}") from exc
    if not isinstance(doc, dict):
        raise ArchiveError(f"state document {path} is not an object.")
    return doc


def _rc_numbers(release_dir: Path) -> list[int]:
    return sorted(
        int(m.group(1))
        for d in release_dir.iterdir()
        if d.is_dir() and (m := _RC_DIR_RE.match(d.name))
    )


def fold_release(
    specs_dir: Path,
    folded_id: str,
    *,
    into: str,
    shipped_sha: str | None,
    pr: int | None,
    shipped_ts: str | None = None,
    final: bool,
    histo_update: Callable[[str, Callable[[HistoRecord], HistoRecord]], HistoRecord | None],
) -> ReleaseFold:
    """Fold a wrongly archived release into ``rc-N/`` of the version that published it.

    The archive holds published versions only (operator ruling 2026-09-14, ADR 0014):
    a candidate closed between two PyPI publications belongs to the version that
    published it, never to its own archived release. This is the ONE governed path for
    that repair — `RELEASE-TREE-ARCHIVE-ID` / `RELEASE-TREE-ARCHIVE-UNSHIPPED` name it
    in their ``fix:`` line — so the move, the state merge and the histo rewrite happen
    together or not at all; never a hand move.

    Refuses, writing nothing, unless ``_archive/<folded_id>/`` exists with a state
    document, *into* is bare SemVer below every live release, and
    ``_archive/<into>/`` either exists ARCHIVED with a shipped sha/pr or is born here
    from *shipped_sha*/*pr* (both then required; *shipped_ts* is the publication's own
    timestamp, defaulting to now). With *final* the folded trio takes
    the target's ROOT (the final candidate, ADR 0009) — refused when a root trio is
    already there; otherwise it becomes the next ``rc-N/``. A folded release that
    itself carries ``rc-K/`` folders contributes them first, in order.

    On success: the trio(s) move; the target state merges both logs in ``ts`` order
    plus one ``note``, ``rc`` becomes the highest ``rc-N`` present, ``defined`` keeps
    the earliest milestone and ``implemented`` the folded one when the target has
    none; the folded directory is deleted; LAST, every histo record whose id is
    *folded_id* or ``v<folded_id>`` is rewritten in place through *histo_update* —
    ``release`` becomes *into* and the summary names the placement.
    """
    if not is_release_semver(into):
        raise ArchiveError(
            f"--into {into!r} is not bare SemVer M.m.p.\n"
            f"fix: {DADAIA_BIN} release fold {folded_id} --into <published M.m.p>"
        )
    if folded_id == into:
        raise ArchiveError(
            f"{folded_id} cannot be folded into itself.\n"
            f"fix: {DADAIA_BIN} release fold {folded_id} --into <the version that published it>"
        )
    archive_root = specs_dir / "releases" / "_archive"
    folded_dir = archive_root / folded_id
    folded_state_path = release_state_file(folded_dir) if folded_dir.is_dir() else None
    if folded_state_path is None:
        raise ArchiveError(
            f"_archive/{folded_id}/ is not an archived release (no directory or no state "
            f"document).\nfix: ls {archive_root}"
        )
    live_ids = [
        d.name
        for d in (specs_dir / "releases").iterdir()
        if d.is_dir() and is_release_semver(d.name)
    ]
    above = [live for live in live_ids if _semver_key(into) >= _semver_key(live)]
    if above:
        raise ArchiveError(
            f"--into {into} is not below the live release {above[0]} — the archive holds "
            "published versions only.\n"
            f"fix: {DADAIA_BIN} release fold {folded_id} --into <last published M.m.p>"
        )
    folded_state = _read_state(folded_state_path)

    target_dir = archive_root / into
    target_state_path = release_state_file(target_dir) if target_dir.is_dir() else None
    born_target = target_state_path is None
    if born_target:
        if not shipped_sha or not pr:
            raise ArchiveError(
                f"_archive/{into}/ carries no state document yet — its publication must "
                "be named to birth it.\n"
                f"fix: {DADAIA_BIN} release fold {folded_id} --into {into} "
                "--shipped <develop->main sha> --pr <ship PR>"
            )
        if not _SHA_RE.match(shipped_sha) or pr <= 0:
            raise ArchiveError(
                f"--shipped {shipped_sha!r} / --pr {pr} are not a commit sha and a PR number.\n"
                "fix: git log --oneline origin/main | head"
            )
        target_state: dict[str, Any] = {
            "schema": "release-state-v1",
            "release": into,
            "phase": "ARCHIVED",
            "rc": None,
            "defined": None,
            "implemented": None,
            "shipped": {"sha": shipped_sha, "pr": pr, "ts": shipped_ts or _utc_now()},
            "log": [],
        }
    else:
        assert target_state_path is not None
        target_state = _read_state(target_state_path)
        shipped = target_state.get("shipped")
        if target_state.get("phase") != "ARCHIVED" or not (
            isinstance(shipped, dict) and shipped.get("sha") and shipped.get("pr")
        ):
            raise ArchiveError(
                f"_archive/{into}/ is not a published, ARCHIVED release.\n"
                f"fix: {DADAIA_BIN} doctor --specs-dir {specs_dir}"
            )
    target_dir.mkdir(parents=True, exist_ok=True)
    if final and any((target_dir / name).is_file() for name in _TRIO):
        raise ArchiveError(
            f"_archive/{into}/ already carries a root trio — only one final candidate.\n"
            f"fix: {DADAIA_BIN} release fold {folded_id} --into {into}"
        )

    # ── the move plan: folded rc-K/ first, then the folded root trio ────────────
    next_rc = max(_rc_numbers(target_dir), default=0) + 1
    moves: list[tuple[Path, Path]] = []
    for k in _rc_numbers(folded_dir):
        moves.append((folded_dir / f"rc-{k}", target_dir / f"rc-{next_rc}"))
        next_rc += 1
    root_trio = [name for name in _TRIO if (folded_dir / name).is_file()]
    placed_at = target_dir if final else target_dir / f"rc-{next_rc}"
    for name in root_trio:
        moves.append((folded_dir / name, placed_at / name))
    rc_after = max([*_rc_numbers(target_dir), next_rc if (root_trio and not final) else 0] + [0])
    if not root_trio and not final:
        rc_after = next_rc - 1

    placement = "root (final candidate)" if final else placed_at.name
    note = {
        "ts": _utc_now(),
        "agent": "release-candidates",
        "kind": "note",
        "text": (
            f"Folded former archived release {folded_id} into {into}/{placement}: the "
            "archive holds published versions only (operator ruling 2026-09-14, ADR 0014)."
        ),
    }
    merged_log = sorted(
        [*target_state.get("log", []), *folded_state.get("log", [])],
        key=lambda e: str(e.get("ts", "")),
    ) + [note]
    new_state = dict(target_state)
    new_state["log"] = merged_log
    new_state["rc"] = rc_after or None
    defined = [
        d for d in (target_state.get("defined"), folded_state.get("defined")) if isinstance(d, dict)
    ]
    new_state["defined"] = min(defined, key=lambda d: str(d.get("ts", ""))) if defined else None
    if new_state.get("implemented") is None or final:
        new_state["implemented"] = folded_state.get("implemented") or new_state.get("implemented")

    original_target_bytes = target_state_path.read_bytes() if target_state_path else None
    done: list[tuple[Path, Path]] = []
    try:
        for src, dst in moves:
            dst.parent.mkdir(parents=True, exist_ok=True)
            src.rename(dst)
            done.append((src, dst))
        (target_dir / RELEASE_STATE_FILENAME).write_text(
            json.dumps(new_state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        shutil.rmtree(folded_dir)
    except BaseException:
        for src, dst in reversed(done):
            dst.rename(src)
        if original_target_bytes is not None:
            (target_dir / RELEASE_STATE_FILENAME).write_bytes(original_target_bytes)
        elif born_target:
            shutil.rmtree(target_dir, ignore_errors=True)
        raise

    rewritten: list[str] = []
    suffix = f" | folded into {into}/{placement} (operator ruling 2026-09-14, ADR 0014)"

    def _mutate(record: HistoRecord) -> HistoRecord:
        return HistoRecord(
            id=record.id,
            ts=record.ts,
            disposition=record.disposition,
            release=into,
            reason=record.reason,
            summary=(record.summary or "") + suffix,
            entry=record.entry,
        )

    for histo_id in (folded_id, f"v{folded_id}"):
        if histo_update(histo_id, _mutate) is not None:
            rewritten.append(histo_id)
    return ReleaseFold(
        folded=folded_id,
        into=into,
        rc=new_state["rc"],
        placed_at=placed_at,
        target_dir=target_dir,
        histo_ids=tuple(rewritten),
    )
