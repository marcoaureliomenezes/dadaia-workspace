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
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from dadaia_workspace.core.atomic_write import atomic_write
from dadaia_workspace.core.exceptions import PublicAssetError
from dadaia_workspace.core.models.doctor_report import DoctorLine, DoctorStatus

#: Which fixed-point discipline a rule's ``render`` observes (documentation only —
#: install/doctor run one algorithm regardless; see the module docstring).
CompareSemantic = Literal["bytes", "owned-slice", "managed-block"]


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


@dataclass(frozen=True)
class TranscriptLine:
    """One rule's install outcome — replaces the historical embedded-in-a-string
    ``"[ok]   "``/``"[skip] "`` protocol every prior consumer had to re-parse."""

    status: Literal["ok", "skip"]
    path: Path

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
