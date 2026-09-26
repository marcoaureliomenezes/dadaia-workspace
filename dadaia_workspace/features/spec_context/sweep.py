"""The ONE traversal primitive of the workspace reaper (0.4.7 FR6a).

``walk`` reads a directory, ``mtime`` reads one entry's age, ``move`` relocates an
entry, ``remove`` deletes it — all four behind ONE guard:

* a symlink is never followed (``walk`` refuses a symlinked root; ``move``/``remove``
  act on the link itself);
* an entry that vanished mid-walk is ABSENT, never an error;
* a location outside the workspace is SKIPPED, source and destination alike;
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
from pathlib import Path

__all__ = ["guarded", "move", "mtime", "remove", "rmtree", "walk"]

_OUTSIDE = "skipped '{label}' (outside the workspace)"


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


def move(
    workspace_root: Path, target: Path, destination: Path, label: str, *, note: str = ""
) -> str | None:
    """Relocate *target* to *destination*, creating its parents. Both ends must sit
    inside the workspace. The moved entry's mtime is stamped at the move, so a TTL zone
    clocks a held entry from when it was reaped, never from the origin's own age.

    ONE hold per destination: a tool re-creates what the reaper just took (a
    ``.mypy_cache`` regenerated by the next typecheck), so the same origin is reaped
    again within one TTL window. The earlier hold is REMOVED here and the new entry takes
    its place, restarting the clock — never a second ``<name>-N`` copy of one origin.
    ``os.replace`` cannot do it alone: onto an existing non-empty directory it raises
    ENOTEMPTY, which the guard would report as ``skipped`` forever.

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
    destination.parent.mkdir(parents=True, exist_ok=True)
    remove(workspace_root, destination, label)
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
