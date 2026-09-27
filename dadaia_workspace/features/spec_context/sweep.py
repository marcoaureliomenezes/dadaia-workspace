"""The ONE traversal primitive of the workspace reaper (0.4.7 FR6a).

``walk`` reads a directory, ``mtime`` reads one entry's age, ``move`` relocates an
entry, ``remove`` deletes it — all four behind ONE guard:

* a symlink is never followed (``walk`` refuses a symlinked root; ``move``/``remove``
  act on the link itself);
* an entry that vanished mid-walk is ABSENT, never an error;
* a location outside the workspace is SKIPPED, source and destination alike;
* a linked git worktree (or submodule) — a directory whose ``.git`` entry is a regular
  file — is SKIPPED, and so is any path inside one or above one: it holds uncommitted
  work and git's registration, which no hold in ``reaped/`` can give back;
* every ``OSError`` becomes exactly one ``skipped`` action — a pass never aborts;
* a cross-device move falls back to copy + remove HERE, so a failed move is never a
  partial delete;
* a read-only entry is made owner-writable and retried — the reaper owns what it
  reaps (a Go module cache is ``dr-xr-xr-x`` all the way down; loose VCS objects are 0444).

Bug class this replaces: ``doctor.py`` carried five per-call-site guards
(``_entries``/``_mtime``/``_remove``/``_guarded``/``_remove_dead_repo``), each
re-deriving "may I touch this?" from its own premises. The CRITICAL
``doctor-ptr-gc-deletes-valid-lock-free-bind`` is that shape's worst case: a call site
deleted live state directly because its own local rule said the state looked dead.
One guard, one home, and deletion reserved to TTL expiry (FR6b).
"""

from __future__ import annotations

import contextlib
import os
import shutil
import stat
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

__all__ = ["guarded", "move", "mtime", "remove", "rmtree", "walk"]

_OUTSIDE = "skipped '{label}' (outside the workspace)"
_WORKTREE = "skipped '{label}' (holds a linked git worktree)"


def walk(directory: Path) -> list[Path]:
    """The sorted entries of *directory*; empty for a missing, unreadable or SYMLINKED
    root. A symlinked root is refused because ``iterdir`` would follow it and every
    entry of the destination would then present a parent inside the workspace."""
    if directory.is_symlink():
        return []
    try:
        return sorted(directory.iterdir())
    except OSError:
        return []


def mtime(path: Path) -> float | None:
    """``lstat`` mtime (the LINK's own, never its destination's), or ``None`` for an
    entry that vanished between ``walk`` and here — absent, never an exception."""
    try:
        return path.lstat().st_mtime
    except OSError:
        return None


def newest(path: Path) -> float | None:
    """The newest ``lstat`` mtime of *path*'s content: itself when not a real directory,
    else its newest non-directory entry (its own mtime when it holds none) — a directory
    mtime a deletion refreshed is never content. ``None`` when it vanished."""
    if path.is_symlink() or not path.is_dir():
        return mtime(path)
    stamps = [mtime(Path(d) / f) for d, _, files in os.walk(path) for f in files]
    return max((t for t in stamps if t is not None), default=mtime(path))


def guarded(code: str, label: str, step: Callable[[], str | None]) -> list[str]:
    """Run one step, yielding at most one action line: what the step reports, or
    ``skipped`` with the errno when the process cannot perform it. The pass never
    aborts on an undeletable entry."""
    try:
        done = step()
    except OSError as exc:
        return [f"{code}: skipped '{label}' (errno {exc.errno}: {exc.strerror})"]
    return [] if done is None else [f"{code}: {done}"]


def _inside(workspace_root: Path, target: Path) -> bool:
    """True when *target*'s OWN location — its resolved parent plus its own name, so a
    symlink is judged where it sits, not where it points — is inside the workspace."""
    try:
        location = target.parent.resolve() / target.name
        location.relative_to(workspace_root.resolve())
    except (OSError, ValueError):
        return False
    return True


def _is_gitfile(entry: Path) -> bool:
    return entry.name == ".git" and entry.is_file() and not entry.is_symlink()


def linked_worktree(workspace_root: Path, target: Path) -> Path | None:
    """The linked worktree *target* sits inside or whose subtree holds one — an rmtree
    of ``tmp/<agent>/<day>/`` kills every worktree below it. Local and cheap: no git
    call, symlinks never followed."""
    root, here = workspace_root.resolve(), target.parent.resolve()
    for ancestor in (here, *here.parents):
        if ancestor == root:
            break
        if _is_gitfile(ancestor / ".git"):
            return ancestor
    if target.is_symlink() or not target.is_dir():
        return None
    trees = (Path(d) for d, _, files in os.walk(target) if ".git" in files)
    return next((d for d in trees if _is_gitfile(d / ".git")), None)


def _exists(target: Path) -> bool:
    return target.is_symlink() or target.exists()


def _writable_retry(func: Callable[[str], object], path: str, _exc: BaseException) -> None:
    """``shutil.rmtree`` ``onexc``: grant owner write on the failing entry's parent (where
    unlink permission lives) and on the entry itself — never through a symlink, whose
    chmod would reach its destination — then retry once."""
    target = Path(path)
    for entry in (target.parent, target):
        if entry is target and target.is_symlink():
            continue
        with contextlib.suppress(OSError):
            os.chmod(entry, entry.stat().st_mode | stat.S_IWUSR | stat.S_IRUSR | stat.S_IXUSR)
    func(path)


def rmtree(target: Path) -> None:
    """Delete a directory tree, read-only entries included."""
    shutil.rmtree(target, onexc=_writable_retry)


def remove(workspace_root: Path, target: Path, label: str) -> str | None:
    """Delete *target* iff its own location resolves inside the workspace. A symlink is
    unlinked, never followed; an entry already gone is nothing to report."""
    if not _exists(target):
        return None
    if not _inside(workspace_root, target):
        return _OUTSIDE.format(label=label)
    if linked_worktree(workspace_root, target):
        return _WORKTREE.format(label=label)
    if target.is_symlink() or target.is_file():
        try:
            target.unlink()
        except PermissionError as exc:
            _writable_retry(os.unlink, str(target), exc)
    elif target.is_dir():
        rmtree(target)
    else:
        return None
    return f"deleted '{label}'"


#: The zone the reaper HOLDS what it takes off the working tree. Deletion is reserved to
#: TTL expiry of this zone, so no scan verdict ever deletes anything directly — the shape
#: behind the CRITICAL doctor-ptr-gc-deletes-valid-lock-free-bind.
REAPED_ZONE = "reaped"


def hold(workspace_root: Path, target: Path, label: str, *, note: str = "") -> str | None:
    """:func:`move` *target* to ``.dadaia/reaped/<YYYYMMDD>/<workspace-relative path>``,
    the one hold: the origin path is the record of where the entry came from."""
    day = datetime.now(tz=UTC).strftime("%Y%m%d")
    rel = target.relative_to(workspace_root)
    held = workspace_root / ".dadaia" / REAPED_ZONE / day / rel
    return move(workspace_root, target, held, label, note=note)


def move(
    workspace_root: Path, target: Path, destination: Path, label: str, *, note: str = ""
) -> str | None:
    """Relocate *target* to *destination*, creating its parents. Both ends must sit
    inside the workspace. The moved entry's mtime is stamped at the move, so a TTL zone
    clocks a held entry from when it was reaped, never from the origin's own age.

    N moves make N holds (ADR 0074): an occupied destination yields the first free
    ``<name>-N`` beside it, so no hold dies before its own TTL.

    A cross-device ``os.replace`` (EXDEV) falls back to copy + remove here — the one
    place — and the copy lands before the origin is unlinked, so a failure leaves the
    origin intact rather than a partial delete.

    ONE message shape for every mover: ``moved '<label>'<note> -> '<destination>'``.
    *note* is the one extra field a caller may add when the label alone does not say
    whose entry it was (INV-5 names the context that owned the repo)."""
    if not _exists(target):
        return None
    if not _inside(workspace_root, target) or not _inside(workspace_root, destination):
        return _OUTSIDE.format(label=label)
    if linked_worktree(workspace_root, target):
        return _WORKTREE.format(label=label)
    destination.parent.mkdir(parents=True, exist_ok=True)
    stem, n = destination.name, 0
    while _exists(destination):
        n += 1
        destination = destination.with_name(f"{stem}-{n}")
    try:
        os.replace(target, destination)
    except OSError as exc:
        if exc.errno != 18:  # EXDEV — every other errno is the guard's one skipped line
            raise
        if target.is_symlink():
            destination.symlink_to(os.readlink(target))
        elif target.is_dir():
            shutil.copytree(target, destination, symlinks=True)
        else:
            shutil.copy2(target, destination)
        remove(workspace_root, target, label)
    if not destination.is_symlink():
        os.utime(destination)
    try:
        shown = destination.relative_to(workspace_root).as_posix()
    except ValueError:  # pragma: no cover — _inside already proved it is under the root
        shown = destination.as_posix()
    return f"moved '{label}'{note} -> '{shown}'"
