"""Public-doctor Layer-2 residue check for workflow-policy docs (T-28-D-02).

``dadaia public doctor`` must assert that the removed/deferred Layer-2 worker harnesses
(``claude`` / ``opencode``) never leak into the **public** workflow-policy docs as a
*selectable Layer-2 worker* choice (LAW 1 — Layer-2 workers are ``codex``/``pi`` only).

This is the public-surface twin of the in-repo ``policy_doctor`` WMP-LAYER2-RESIDUE check
(which polices the governed catalog + profile registry). It scans the dehydrated public
bodies for a leak and ``[drift]``-flags any reintroduction, so a future edit cannot paste
``claude``/``opencode`` back in as a worker harness choice.

Detection (deliberately narrow — the contract may *name* these harnesses to forbid them):
a body is in violation when a line presents a forbidden harness as part of a **Layer-2
worker harness** choice. We detect that with a structural regex: a line that mentions
``Layer-2`` + a worker/harness selection token AND names ``claude`` or ``opencode`` as an
offered option (``codex, pi, or claude`` / ``codex, pi, and opencode`` / an enum list).
A line that states the *negative* contract — "claude is a Layer-1 ... not a Layer-2
worker", "opencode was removed as a Layer-2 worker" — is exempt (it is the law, stated).

Mirrors the ``check_ai_surface_ritual`` contract: returns doctor report lines; ``[drift]``
lines make ``dadaia public doctor`` exit non-zero, and a single ``[ok]`` summary line is
emitted when the surface is clean.
"""

from __future__ import annotations

import re
from pathlib import Path

from dadaia_workspace.core.models.doctor_report import DoctorLine, DoctorStatus

#: Forbidden Layer-2 worker harness names (LAW 1).
_FORBIDDEN = ("claude", "opencode")

#: Public doc globs scanned for residue (markdown surfaces operators read).
_SCAN_GLOBS: tuple[str, ...] = (
    "data/*.md",
    "scaffold/*.md",
    "skills/**/*.md",
    "agents/*.md",
    "rules/*.md",
)

#: A line "selects" a Layer-2 worker when it mentions Layer-2 alongside a worker/harness
#: selection token. (Both must be present on the same line — keeps the match structural.)
_LAYER2_RE = re.compile(r"layer-?2", re.IGNORECASE)
_WORKER_SELECT_RE = re.compile(r"worker|harness", re.IGNORECASE)

#: The negative-contract exemption: a line forbidding the harness, not offering it.
_NEGATIVE_RE = re.compile(r"\b(not|never|forbidden|rejected|removed|layer-?1)\b", re.IGNORECASE)


def _is_residue_line(line: str) -> str | None:
    """Return the forbidden harness named as a Layer-2 worker option, else ``None``."""
    if not (_LAYER2_RE.search(line) and _WORKER_SELECT_RE.search(line)):
        return None
    if _NEGATIVE_RE.search(line):
        # The line forbids/disclaims the harness — that is the contract, not a leak.
        return None
    lower = line.lower()
    for harness in _FORBIDDEN:
        if harness in lower:
            return harness
    return None


def _scan_files(public_dir: Path) -> list[Path]:
    paths: list[Path] = []
    for glob in _SCAN_GLOBS:
        paths.extend(sorted(public_dir.glob(glob)))
    return paths


def check_workflow_policy_layer2_residue(public_dir: Path) -> list[DoctorLine]:
    """Scan public workflow-policy docs for a Layer-2 ``claude``/``opencode`` leak.

    Returns doctor report lines. ``[drift]`` (one per offending line) makes
    ``dadaia public doctor`` exit non-zero; a single ``[ok]`` summary is emitted when the
    public surface is clean. A missing ``public_dir`` is a no-op (empty list).
    """
    public_dir = Path(public_dir)
    if not public_dir.exists():
        return []
    out: list[DoctorLine] = []
    for path in _scan_files(public_dir):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        rel = path.relative_to(public_dir).as_posix()
        for line_no, line in enumerate(text.splitlines(), start=1):
            harness = _is_residue_line(line)
            if harness is not None:
                out.append(
                    DoctorLine(
                        DoctorStatus.DRIFT,
                        f"workflow-policy:{rel}:{line_no}: forbidden Layer-2 worker "
                        f"harness {harness!r} offered as a selectable choice — Layer-2 workers "
                        "are codex/pi only (LAW 1).",
                    )
                )
    if not out:
        out.append(
            DoctorLine(
                DoctorStatus.OK, "workflow-policy (no Layer-2 claude/opencode worker residue)"
            )
        )
    return out


__all__ = ["check_workflow_policy_layer2_residue"]
