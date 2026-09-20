"""``ProjectionRule``: the one seam every install/doctor comparison flows through.

K3 (release 0.5.1, candidate "one ProjectionRule table; harness as a real seam with
three adapters"). Before this module, "does this projected file match what the
library ships" was decided five separate ways across ``public_assets.py``,
``install_helpers.py`` and ``codex_doctor.py``: a raw sha compare, a rendered-content
string compare, a policy-aware render compare reserved for Claude agents only, a
merge-then-compare special case for ``settings.json``/the kimi hooks block, and nine
narrow Codex-specific field/regex checks (D-CX-1/2/4/5/10) that re-derived a TOML's
correctness from its shape instead of its bytes.

This module collapses all of it into one algorithm. A :class:`ProjectionRule`'s
``render`` is a pure, deterministic transform of "the bytes currently on disk (or
``None`` when absent)" to "the bytes that belong there":

* A rule whose render ignores its input is a plain byte-compare (``compare="bytes"``)
  — the staged source fully determines the projection (Claude/Codex agent bodies, the
  law file, the guardrail pair, the skills/scripts trees, the kimi projected tree).
* A rule whose render MERGES its input — preserving whatever it does not own — is an
  ``"owned-slice"`` (the dadaia hook wiring folded into an operator's
  ``.claude/settings.json``) or ``"managed-block"`` compare (the marker-delimited kimi
  hooks block folded into an operator's ``config.toml``).

``install`` and ``doctor`` run the SAME algorithm for every rule regardless of which
of the three a render performs: a merge render is a fixed point on already-canonical
content (so equality still means OK — the operator's foreign keys never read as
drift), and reproduces the canonical form otherwise (so a diverged owned slice is
still correctly detected as a byte difference). The renderer is the only verifier.
"""

from __future__ import annotations

import contextlib
import hashlib
import os
import shutil
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from dadaia_workspace.core.atomic_write import atomic_write
from dadaia_workspace.core.exceptions import PublicAssetError
from dadaia_workspace.core.models.doctor_report import DoctorLine, DoctorStatus

#: Which fixed-point discipline a rule's ``render`` observes (documentation only —
#: install/doctor run one algorithm regardless; see the module docstring).
CompareSemantic = Literal["bytes", "owned-slice", "managed-block"]

#: What a projected entry physically IS on disk. ``read_bytes()`` follows a link, so the
#: digest alone can never tell a symlink from a copy of the same content — the kind
#: travels with the entry, through the transcript, into the install ledger.
EntryKind = Literal["file", "symlink", "copy"]


def link_render(_current: bytes | None) -> bytes:
    """A link rule projects an inode, not bytes — its canonical content is its target's.

    Never called: install and doctor both branch on ``link_to`` before rendering.
    """
    return b""


@dataclass(frozen=True)
class ProjectionRule:
    """One projected file: where it lives, how to render it, how it is owned.

    ``render`` receives the current bytes on disk (``None`` when the destination is
    absent) and returns the bytes that belong there. It may raise
    :class:`~dadaia_workspace.core.exceptions.PublicAssetError` (e.g. an unparseable
    operator-owned file) — :func:`install_rules` lets that propagate (install fails
    loud, before any further rule runs); :func:`doctor_rules` converts it to a single
    ``DRIFT`` line (doctor never crashes on a bad operator file).
    """

    label: str
    harness: str
    dst: Path
    render: Callable[[bytes | None], bytes]
    compare: CompareSemantic = "bytes"
    #: chmod applied after every write AND every already-correct skip — mode drift
    #: (e.g. a cleared executable bit on a hook shim) is repaired even when the
    #: content already matches. ``None`` leaves the destination's mode untouched.
    mode: int | None = None
    #: When set, the rule projects a RELATIVE symlink at ``dst`` pointing at this
    #: canonical path (one authored set, N harness views) — falling back to a
    #: hash-verified copy when the platform refuses to create one (Windows without
    #: Developer Mode raises ``OSError``/``NotImplementedError``). ``render`` is unused.
    link_to: Path | None = None


@dataclass(frozen=True)
class TranscriptLine:
    """One rule's install outcome — replaces the historical embedded-in-a-string
    ``"[ok]   "``/``"[skip] "`` protocol every prior consumer had to re-parse."""

    status: Literal["ok", "skip"]
    path: Path
    kind: EntryKind = "file"

    def render(self) -> str:
        prefix = "[ok]   " if self.status == "ok" else "[skip] "
        return f"{prefix}{self.path}"


@dataclass(frozen=True)
class Transcript:
    """The typed record of one :func:`install_rules` run.

    Ledger reconciliation and any other structured consumer reads :attr:`lines`
    directly (each carries its own ``.path``); :meth:`render` reproduces the legacy
    wire format for the port's ``list[str]`` return and any other string-facing
    consumer (CLI printer, golden tests).
    """

    lines: tuple[TranscriptLine, ...]

    def render(self) -> list[str]:
        return [line.render() for line in self.lines]

    def paths(self) -> tuple[Path, ...]:
        return tuple(line.path for line in self.lines)


def _read_bytes(path: Path) -> bytes | None:
    return path.read_bytes() if path.is_file() else None


def _posix_relpath(target: Path, start: Path) -> str:
    """A relative path with ``/`` separators on every OS: the one spelling a link target
    and its ledger digest carry, so Windows and POSIX agree byte for byte."""
    return os.path.relpath(target, start).replace(os.sep, "/")


def _link_target(rule: ProjectionRule) -> str:
    """The relative target a link rule's ``dst`` must carry (POSIX-shaped, portable)."""
    assert rule.link_to is not None, "a link rule always carries link_to"
    return _posix_relpath(rule.link_to, rule.dst.parent)


def _source_files(src: Path) -> Iterator[tuple[Path, Path]]:
    """(source file, path relative to *src*) for a file or every file under a directory."""
    if src.is_dir():
        for path in sorted(src.rglob("*")):
            if path.is_file():
                yield path, path.relative_to(src)
    elif src.is_file():
        yield src, Path(".")


def _copy_verified(src: Path, dst: Path) -> list[Path]:
    """Copy *src* (file or tree) onto *dst*, verifying each written file by digest.

    The fallback half of a link rule: a platform that refuses symlinks still gets the
    same content, and the ledger records it as ``copy`` so the doctor can tell them apart.
    """
    written: list[Path] = []
    for source, rel in _source_files(src):
        target = dst if rel == Path(".") else dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = source.read_bytes()
        atomic_write(target, payload)
        if hashlib.sha256(target.read_bytes()).digest() != hashlib.sha256(payload).digest():
            raise PublicAssetError(f"copy fallback for {dst} did not verify at {target}")
        written.append(target)
    return written


def _clear(dst: Path) -> None:
    if dst.is_symlink() or dst.is_file():
        dst.unlink()
    elif dst.is_dir():
        shutil.rmtree(dst)


def _install_link(rule: ProjectionRule, *, force: bool) -> list[TranscriptLine]:
    assert rule.link_to is not None
    target = _link_target(rule)
    if not force and rule.dst.is_symlink() and os.readlink(rule.dst).replace(os.sep, "/") == target:
        return [TranscriptLine("skip", rule.dst, "symlink")]
    rule.dst.parent.mkdir(parents=True, exist_ok=True)
    _clear(rule.dst)
    try:
        # The canonical target is POSIX-spelled (ledger, doctor); the OS gets its native
        # separators only here — Windows cannot resolve a reparse target written with "/".
        os.symlink(target.replace("/", os.sep), rule.dst, target_is_directory=rule.link_to.is_dir())
    except (OSError, NotImplementedError):
        return [
            TranscriptLine("ok", path, "copy") for path in _copy_verified(rule.link_to, rule.dst)
        ]
    return [TranscriptLine("ok", rule.dst, "symlink")]


def link_entry_defect(entry: Path, canonical: Path) -> str | None:
    """What is wrong with one projected harness view of *canonical*, else ``None``.

    The ONE definition of "a correct view of the authored set": a symlink carrying the
    relative target of *canonical* and resolving to something that exists, or — on a
    platform that refused the link — a copy equal to it byte for byte. The rule-table
    compare (:func:`_doctor_link`) and the ledger-driven ``SYMLINK-TARGET-1`` sweep in
    ``infrastructure/public_assets.py`` both read this, so a link entry cannot be
    judged correct by one surface and broken by the other.
    """
    expected = _posix_relpath(canonical, entry.parent)
    if entry.is_symlink():
        actual = os.readlink(entry).replace(os.sep, "/")
        if actual != expected:
            return f"symlink target {actual!r} is not the canonical {expected!r}"
        if not canonical.exists():
            return f"symlink target {expected!r} does not exist"
        return None
    if not entry.exists():
        return "missing"
    if not canonical.exists():
        return f"canonical {expected!r} does not exist"
    for source, rel in _source_files(canonical):
        copied = entry if rel == Path(".") else entry / rel
        if not copied.is_file() or copied.read_bytes() != source.read_bytes():
            return f"copy diverged at {rel.as_posix()}"
    return None


def _doctor_link(rule: ProjectionRule) -> DoctorLine:
    assert rule.link_to is not None
    if not rule.dst.is_symlink() and not rule.dst.exists():
        return DoctorLine(DoctorStatus.MISSING, rule.label)
    defect = link_entry_defect(rule.dst, rule.link_to)
    if defect is None:
        return DoctorLine(DoctorStatus.OK, rule.label)
    return DoctorLine(DoctorStatus.DRIFT, f"{rule.label} ({defect})")


def _apply_mode(path: Path, mode: int | None) -> None:
    if mode is not None:
        with contextlib.suppress(OSError):
            path.chmod(mode)


def install_rules(rules: Sequence[ProjectionRule], *, force: bool) -> Transcript:
    """``install`` half of the seam: ``write(render)`` for every rule.

    A missing destination is always written. An existing destination is rewritten
    only when its bytes differ from ``render(current)`` — or unconditionally under
    ``force`` (a byte-identical forced rewrite still reports ``ok``, matching the
    historical ``copy_file``/``write_generated`` contract every rule replaces).
    """
    lines: list[TranscriptLine] = []
    for rule in rules:
        if rule.link_to is not None:
            lines.extend(_install_link(rule, force=force))
            continue
        current = _read_bytes(rule.dst)
        desired = rule.render(current)
        if current is None or current != desired or force:
            rule.dst.parent.mkdir(parents=True, exist_ok=True)
            if current is not None:
                # A read-only projection (law files are 0o444) must become writable
                # before os.replace — Windows refuses to replace a read-only target.
                _apply_mode(rule.dst, 0o644)
            atomic_write(rule.dst, desired)
            lines.append(TranscriptLine("ok", rule.dst))
        else:
            lines.append(TranscriptLine("skip", rule.dst))
        _apply_mode(rule.dst, rule.mode)
    return Transcript(tuple(lines))


def doctor_rules(rules: Sequence[ProjectionRule]) -> list[DoctorLine]:
    """``doctor`` half of the seam: ``compare(render)`` for every rule.

    The renderer is the only verifier: a rule's line is ``[missing]`` when its
    destination is absent, ``[drift]`` when the destination's bytes differ from
    ``render(current)`` (or when ``render`` itself refuses the current content),
    ``[ok]`` otherwise.
    """
    out: list[DoctorLine] = []
    for rule in rules:
        if rule.link_to is not None:
            out.append(_doctor_link(rule))
            continue
        current = _read_bytes(rule.dst)
        if current is None:
            out.append(DoctorLine(DoctorStatus.MISSING, rule.label))
            continue
        try:
            desired = rule.render(current)
        except PublicAssetError as exc:
            out.append(DoctorLine(DoctorStatus.DRIFT, f"{rule.label} ({exc})"))
            continue
        status = DoctorStatus.OK if current == desired else DoctorStatus.DRIFT
        out.append(DoctorLine(status, rule.label))
    return out
