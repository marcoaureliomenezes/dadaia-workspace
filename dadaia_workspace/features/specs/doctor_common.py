"""Shared leaf helpers for the SpecsDoctor decomposition (v0.1.55 FR1).

Cross-validator free functions used by THREE validator families (release, closure_audit,
governance) plus ``doctor_structural`` (a fourth, TREE-6). Holds no sibling-VALIDATOR
import (no ``ReleaseValidator``/``StructuralValidator`` class ever imported here or from
here) — the release-dir discovery helpers were instance methods on ``SpecsDoctor``; they
are re-homed here as free functions taking ``specs_dir`` explicitly so no family owns
them (they were cross-validator all along — SPEC-DOC-006/026/027/031).

``resolve_live_release_id`` + ``resolve_active_release`` (v0.5.0 FR4/T-050-21A, A4.1)
replace the former ``read_active_md``/``ACTIVE.md`` pair — that file is retired, no
replacement scaffolded in its place. Both ``doctor_release`` and ``doctor_structural``
need the resolved (release, segment, phase) triple, so it lives here rather than in
either — the same shared-leaf shape ``read_active_md`` had. The one tri-state disk read
+ parse of a release's ``RELEASE.jsonl`` (S1 FR23 amendment A6, "ONE reader") lives in
``_read_and_parse_release_jsonl``, below; ``features.specs.doctor_release
.read_release_phase`` is a thin wrapper over it for a caller that already knows the
release_id, never a second read implementation.
"""

from __future__ import annotations

import re
from pathlib import Path

from dadaia_workspace.core.release_events import (
    ReleaseEvent,
    fold_release_events,
    parse_release_events,
)

# A dir counts as a "release dir" iff it carries at least one SDD release artifact.
# Public name (v0.1.81 FR2): reused by doctor_release's partial-archive invariant
# (SPEC-DOC-039) so both checks share one canonical artifact-filename set.
RELEASE_ARTIFACTS: tuple[str, ...] = ("SPEC.md", "PLAN.md", "TASKS.md", "CLOSURE.md")
_RELEASE_ARTIFACTS = RELEASE_ARTIFACTS
# Segment dirs (ADR-1/ADR-5) live *inside* a release dir and are not themselves releases:
# alpha-N, rc-N, plus the historical `integration` segment container.
_SEGMENT_NAME_RE = re.compile(r"^(?:alpha|rc)-\d+$|^integration$")


def resolve_live_release_id(specs_dir: Path) -> tuple[str | None, str | None]:
    """Resolve which release under ``releases/`` is live (v0.5.0 FR4/T-050-21A, A4.1).

    The live release is the ONE directory directly under ``specs_dir/releases/`` —
    excluding ``_archive`` and ``_ideas`` (A4.6: a Draft under ``_ideas/`` carries no
    ``RELEASE.jsonl`` by canon, D10) — that carries a ``RELEASE.jsonl`` file
    (T-050-11 back-fills it the moment a release reaches DEFINITION). This directory
    scan is the sole replacement for ``ACTIVE.md``'s ``release:`` field; no file
    stands in its place.

    Returns ``(release_id, error)``. Zero matches is ``(None, None)`` — not an
    error, the honest "no active release" state and the successor of the old
    scaffold default ``release: none`` (there is no longer a placeholder file to
    write that value into). More than one match is a genuine structural anomaly
    (two live releases at once) and is reported as ``error`` rather than guessed at
    — the caller decides severity, this leaf only detects the shape.
    """
    releases_root = specs_dir / "releases"
    if not releases_root.is_dir():
        return None, None
    candidates = sorted(
        d.name
        for d in releases_root.iterdir()
        if d.is_dir() and d.name not in ("_archive", "_ideas") and (d / "RELEASE.jsonl").is_file()
    )
    if not candidates:
        return None, None
    if len(candidates) > 1:
        return None, (
            "multiple live release directories carry RELEASE.jsonl: " + ", ".join(candidates)
        )
    return candidates[0], None


def _read_and_parse_release_jsonl(
    specs_dir: Path, release_id: str
) -> tuple[tuple[ReleaseEvent, ...] | None, bool]:
    """The ONE tri-state disk read + parse of a release's ``RELEASE.jsonl`` (v0.5.0
    FR4/T-050-11, S1 FR23 firing amendment A6,
    ``specs/releases/0.5.0/reviews/S1-FR23-firing.md`` §3). ``core.release_events``
    itself never does file I/O (core file-I/O purity ratchet, architect A9); every
    reader of these bytes goes through this one function — :func:`resolve_active_release`
    (below) and ``features.specs.doctor_release.read_release_phase`` are its only two
    (thin) callers, so the tri-state disk read is never duplicated.

    The first Draft copy-pasted this same ~10-line body into ``hooks/sdd_gate.py`` and
    ``container.py`` too, defended by precedent from the pre-existing
    ``_active_field``/``read_active_md`` two-reader split — the S1 firing ruling names
    that precedent itself as the "N readers of one file" defect this release exists to
    retire (AR-1 §4), not a reason to add a third.

    Returns ``(events, found)``: ``found=False`` means
    ``specs_dir/releases/<release_id>/RELEASE.jsonl`` does not exist (``events=()``);
    ``events=None`` means it exists but could not be read (genuine I/O failure) —
    callers must treat that as UNKNOWN, never as "no records".
    """
    path = specs_dir / "releases" / release_id / "RELEASE.jsonl"
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return (), False
    except OSError:
        return None, False
    events, _errors = parse_release_events(text)
    return events, True


def resolve_active_release(specs_dir: Path) -> tuple[str, str | None, str | None, str | None]:
    """Resolve ``(release_id, segment, phase, error)`` straight from the live
    ``RELEASE.jsonl`` — the full replacement for ``read_active_md``/``ACTIVE.md``
    (v0.5.0 FR4/T-050-21A, A4.1). Same 4-tuple shape the retired reader returned, so
    every downstream consumer (``doctor_release``, ``doctor_structural``) keeps its
    existing branching (``if err: ...``, ``if release and release != "none": ...``).

    :func:`resolve_live_release_id` (above) answers "which directory" (pure stdlib);
    this function answers the content question — phase and the optional dir-based
    segment (ADR-1/ADR-5) a ``phase`` record's ``data.segment`` may carry (D-E: this
    release itself carries none — segments are ``TASKS.md`` blocks — but the mechanism
    stays live for any release that still scaffolds one via
    ``features.specs.scaffolder.scaffold_release_segment``). Both come out of the ONE
    disk read :func:`_read_and_parse_release_jsonl` performs, never a second read of
    the same bytes for the same fact.

    No live release directory: ``("none", None, "none", None)`` — success, not an
    error; the honest successor of ``ACTIVE.md``'s scaffold default ``release: none``.
    Ambiguous (two+ live release dirs) or an unreadable/phase-less ``RELEASE.jsonl``:
    ``error`` carries the reason and ``phase`` is ``None`` — the same "treat as
    UNKNOWN" contract the narrow phase reader already has.
    """
    release_id, disc_err = resolve_live_release_id(specs_dir)
    if disc_err:
        return "none", None, None, disc_err
    if release_id is None:
        return "none", None, "none", None
    events, found = _read_and_parse_release_jsonl(specs_dir, release_id)
    if not found or events is None:
        return release_id, None, None, f"RELEASE.jsonl for {release_id!r} could not be read"
    fold = fold_release_events(events)
    if not fold.phase:
        return (
            release_id,
            None,
            None,
            f"RELEASE.jsonl for {release_id!r} carries no 'phase' record",
        )
    segment: str | None = None
    for evt in events:
        if evt.event == "phase":
            value = evt.data.get("segment")
            segment = value if isinstance(value, str) and value and value != "none" else None
    return release_id, segment, fold.phase, None


def is_release_dir(d: Path) -> bool:
    if not d.is_dir() or not any((d / a).exists() for a in _RELEASE_ARTIFACTS):
        return False
    # Segment dirs (alpha-N/rc-N/integration) are an orthogonal lifecycle concept,
    # not releases — they carry artifacts but their *release id* is the parent dir.
    # Exclude them from release-id-uniqueness and naming-canon invariants.
    return _SEGMENT_NAME_RE.match(d.name) is None


def iter_archive_release_dirs(arch: Path) -> list[Path]:
    """All release dirs under ``_archive/releases/`` (recursive).

    Recurses so nested legacy milestone layouts (``v0.2.0/v0.1.9``) are
    discovered. A dir qualifies only when it carries an SDD release artifact;
    plain segment containers without artifacts are skipped (their artifact-bearing
    children are still found by the recursion).
    """
    out: list[Path] = []
    for d in sorted(p for p in arch.rglob("*") if p.is_dir()):
        if is_release_dir(d):
            out.append(d)
    return out


def is_legacy_nested_release(d: Path, releases_root: Path) -> bool:
    """True when ``d`` is a release dir nested *below* the top level of a
    releases root — i.e. its parent is itself a release dir, not the root.

    These are the documented-legacy milestone dirs (audit §4 collision:
    ``_archive/releases/v0.2.0/v0.1.{6..9}``). Per T-010-14 they earn a WARNING,
    never an ERROR, until T-010-15 renames them.
    """
    try:
        d.relative_to(releases_root)
    except ValueError:
        return False
    parent = d.parent
    return parent != releases_root and is_release_dir(parent)


def iter_all_release_dirs(specs_dir: Path) -> list[tuple[Path, Path, bool]]:
    """Enumerate every release dir across ``releases/`` and ``_archive/releases/``.

    Returns a list of ``(dir, releases_root, is_legacy_nested)`` triples. The
    active ``releases/`` root is enumerated at its top level only (a release in
    progress has no nested release dirs); the archive root is enumerated
    recursively to surface the nested-collision legacy layout.
    """
    out: list[tuple[Path, Path, bool]] = []
    live_root = specs_dir / "releases"
    if live_root.is_dir():
        for d in sorted(p for p in live_root.iterdir() if p.is_dir()):
            if is_release_dir(d):
                out.append((d, live_root, False))
    arch_root = specs_dir / "_archive" / "releases"
    if arch_root.is_dir():
        for d in iter_archive_release_dirs(arch_root):
            out.append((d, arch_root, is_legacy_nested_release(d, arch_root)))
    return out
