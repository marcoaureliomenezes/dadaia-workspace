"""The ONE traversal primitive of the workspace reaper (0.4.7 FR6a).

``walk`` reads a directory, ``lstat`` reads one entry, ``move`` relocates an
entry, ``remove`` deletes it — all four behind ONE guard:

* a symlink is never followed (``walk`` refuses a symlinked root; ``move``/``remove``
  act on the link itself);
* an entry that vanished mid-walk is ABSENT, never an error;
* a location outside the workspace is SKIPPED, source and destination alike;
* a linked git worktree — a directory whose ``.git`` file names a gitdir under
  ``<common>/worktrees/`` — is SKIPPED, and so is any path inside one or above one: it
  holds uncommitted work and git's registration, which no hold in ``reaped/`` can give
  back; a submodule's ``.git`` file names a relative gitdir that moves with its repo;
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
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePath

from dadaia_workspace.core.workspace_layout import occupied

__all__ = [
    "Skipped",
    "guarded",
    "lstat",
    "move",
    "remove",
    "rmtree",
    "walk",
]


@dataclass(frozen=True)
class Skipped:
    """A refusal: falsy and no ``str``, like a no-op (``None``); only a done line is truthy."""

    line: str

    def __bool__(self) -> bool:
        return False

    def __str__(self) -> str:
        return self.line


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


def lstat(path: Path) -> os.stat_result | None:
    """The entry's OWN ``lstat`` (the link's, never its destination's), or ``None`` for an
    entry that vanished between ``walk`` and here — absent, never an exception."""
    try:
        return path.lstat()
    except OSError:
        return None


def guarded(code: str, label: str, step: Callable[[], str | Skipped | None]) -> list[str]:
    """Run one step, yielding at most one action line: what the step reports, or
    ``skipped`` with the errno when the process cannot perform it. The pass never
    aborts on an undeletable entry."""
    try:
        done = step()
    except OSError as exc:
        return [f"{code}: skipped '{label}' (errno {exc.errno}: {exc.strerror})"]
    return [] if done is None else [f"{code}: {done}"]


def _owner(path: Path) -> str:
    try:
        return path.owner()
    except (NotImplementedError, KeyError, OSError):  # Windows; a uid with no account
        return "another account"


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
    """A linked worktree's ``.git`` file: its gitdir sits in ``<common>/worktrees/``."""
    if entry.name != ".git" or not entry.is_file() or entry.is_symlink():
        return False
    try:
        gitdir = entry.read_text(encoding="utf-8").removeprefix("gitdir:").strip()
    except (OSError, UnicodeDecodeError):
        return False
    return PurePath(gitdir).parent.name == "worktrees"


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


def rmtree(target: Path) -> OSError | None:
    """Delete *target* — a file, a symlink or a tree, read-only entries included: a failing
    entry gets owner write on itself (never through a symlink) and on its parent, where
    unlink permission lives, then one retry. Answers the first failure that retry could
    not lift, recorded for this call only, else ``None``; it never raises."""
    failed: list[OSError] = []

    def retry(func: Callable[[str], object], path: str, _exc: BaseException) -> None:
        entry = Path(path)
        for each in (entry.parent, *(() if entry.is_symlink() else (entry,))):
            with contextlib.suppress(OSError):
                os.chmod(each, each.stat().st_mode | stat.S_IWUSR | stat.S_IRUSR | stat.S_IXUSR)
        try:
            func(path)
        except OSError as exc:
            failed.append(exc)

    if target.is_symlink() or not target.is_dir():
        try:
            target.unlink()
        except OSError as exc:
            retry(os.unlink, str(target), exc)
    else:
        shutil.rmtree(target, onexc=retry)
    return next(iter(failed), None)


def remove(workspace_root: Path, target: Path, label: str) -> str | Skipped | None:
    """Delete *target* iff its own location resolves inside the workspace. A symlink is
    unlinked, never followed; an entry already gone is nothing to report. Judged by the
    outcome: a surviving target is refused naming the recorded failure, and only a
    permission failure prescribes the operator's act."""
    if not occupied(target):
        return None
    if not _inside(workspace_root, target):
        return Skipped(_OUTSIDE.format(label=label))
    if linked_worktree(workspace_root, target):
        return Skipped(_WORKTREE.format(label=label))
    failure = rmtree(target)
    if not occupied(target):
        return f"deleted '{label}'"
    line = (
        f"skipped '{label}' (errno {failure.errno}: {failure.strerror})"
        if failure
        else f"skipped '{label}'"
    )
    if isinstance(failure, PermissionError):
        held = Path(failure.filename or target)
        line += f" — {held} sits in a directory owned by {_owner(held.parent)}; Operator action: remove {target}"
    return Skipped(line)


#: The zone the reaper HOLDS what it takes off the working tree. Deletion is reserved to
#: TTL expiry of this zone, so no scan verdict ever deletes anything directly — the shape
#: behind the CRITICAL doctor-ptr-gc-deletes-valid-lock-free-bind.
REAPED_ZONE = "reaped"


def hold(workspace_root: Path, target: Path, label: str, *, note: str = "") -> str | Skipped | None:
    """:func:`move` *target* to ``.dadaia/reaped/<YYYYMMDD>/<workspace-relative path>``,
    the one hold: the origin path is the record of where the entry came from. The hold's
    clock is its top entry ``reaped/<YYYYMMDD>/<first segment>``, stamped once here."""
    day = workspace_root / ".dadaia" / REAPED_ZONE / datetime.now(tz=UTC).strftime("%Y%m%d")
    rel = target.relative_to(workspace_root)
    done = move(workspace_root, target, day / rel, label, note=note)
    if len(rel.parts) > 1 and done:
        os.utime(day / rel.parts[0])
    return done


def move(
    workspace_root: Path, target: Path, destination: Path, label: str, *, note: str = ""
) -> str | Skipped | None:
    """Relocate *target* to *destination*, creating its parents. Both ends must sit
    inside the workspace. *destination* itself is stamped: a hold counts from the move.

    N moves make N holds (ADR 0074): an occupied destination yields the first free
    ``<name>-N`` beside it, so no hold dies before its own TTL.

    A cross-device ``os.replace`` (EXDEV) falls back to copy + remove here — the one
    place — and the copy lands before the origin is unlinked, so a failure leaves the
    origin intact rather than a partial delete. Any other failure is a refusal, never raised.

    ONE message shape for every mover: ``moved '<label>'<note> -> '<destination>'``.
    *note* is the one extra field a caller may add when the label alone does not say
    whose entry it was (INV-5 names the context that owned the repo)."""
    if not occupied(target):
        return None
    if not _inside(workspace_root, target) or not _inside(workspace_root, destination):
        return Skipped(_OUTSIDE.format(label=label))
    if linked_worktree(workspace_root, target):
        return Skipped(_WORKTREE.format(label=label))
    stem, n = destination.name, 0
    while occupied(destination):
        n += 1
        destination = destination.with_name(f"{stem}-{n}")
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.replace(target, destination)
        except OSError as exc:
            if exc.errno != 18:  # EXDEV — every other errno is this act's refusal
                raise
            if target.is_symlink():
                destination.symlink_to(os.readlink(target))
            elif target.is_dir():
                shutil.copytree(target, destination, symlinks=True)
            else:
                shutil.copy2(target, destination)
            if isinstance(kept := remove(workspace_root, target, label), Skipped):
                return kept
        if os.utime in os.supports_follow_symlinks:  # a link's own clock, never its target's
            os.utime(destination, follow_symlinks=False)
        elif not destination.is_symlink():  # never followed to its target
            os.utime(destination)
    except OSError as exc:
        return Skipped(f"skipped '{label}' (errno {exc.errno}: {exc.strerror})")
    try:
        shown = destination.relative_to(workspace_root).as_posix()
    except ValueError:  # pragma: no cover — _inside already proved it is under the root
        shown = destination.as_posix()
    return f"moved '{label}'{note} -> '{shown}'"
