"""New-artifact creation helpers for dadaia CLI.

Implements:
- release_new:  creates specs/releases/<id>/SPEC.md stub

Validates the release id and refuses to clobber an existing release directory. The
legacy ``bug_new`` Markdown scaffolder was retired in v0.1.53 — bugs are event-sourced
JSONL via ``dadaia bugs append`` (the v0.1.46 canon).

``backlog_new`` MOVED to ``features.backlog.document`` at SPEC v0.4.2 FR1 (GRILL D1):
that module already owns the ``BACKLOG.md`` grammar for reading, and
``features/spec_artifacts``/``features/backlog`` are independent sibling features under
the ``features-no-cross-feature`` import-linter contract (no accepted edge exists for
this pair) — moving the writer into the feature that owns the grammar needs no new
edge at all, where importing it here would.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from dadaia_workspace.core.specs_version import RELEASE_SEMVER_RE

# ── slug validation patterns ──────────────────────────────────────────────────
# Shared pattern for the legacy release-id slug form:
# must start with a lowercase letter, followed by lowercase letters, digits, or hyphens.
_SLUG_RE = re.compile(r"^[a-z][a-z0-9-]+$")

# Canonical release-dir SemVer form REQUIRED by `specs doctor` SPEC-DOC-027 for a live
# release dir. The compiled pattern is the shared canon (RELEASE_SEMVER_RE, imported from
# core.specs_version — v0.1.53 FR3 centralised the previously-triplicated literal). A
# release id must satisfy EITHER this SemVer canon (preferred) OR the legacy slug — closing
# the bug `release-new-rejects-semver-but-doctor-requires-it`, where the old slug-only
# validator rejected the very `vX.Y.Z` form the doctor mandates.


def _is_valid_release_id(release_id: str) -> bool:
    """A release id is valid if it is the SemVer canon (``vX.Y.Z``) or the legacy slug."""
    return bool(RELEASE_SEMVER_RE.match(release_id) or _SLUG_RE.match(release_id))


def _today() -> str:
    return datetime.now(tz=UTC).strftime("%Y-%m-%d")


# ── result types ─────────────────────────────────────────────────────────────


@dataclass
class NewArtifactResult:
    """Outcome of a new-artifact creation.

    Attributes:
        path:    Absolute path to the created file.
        created: True when the file was freshly created; False if it already existed
                 (should not happen — callers guard with exists() check first).
    """

    path: Path
    created: bool = True


# ── SPEC.md stub template ─────────────────────────────────────────────────────

_RELEASE_SPEC_STUB = """\
# SPEC — Release: {release_id}

**Status:** Draft
**Release ID:** {release_id}
**Owner:** product-engineer
**Opened:** {today}

---

## 1. Problem and context

(Describe the problem this release solves.)

---

## 2. Objective

(State the release objective in one sentence.)

---

## 3. Scope

(List the scope clusters / acceptance criteria.)

---

## 4. Out of scope

(Explicitly list what this release does NOT cover.)

---

## 5. Dependencies and risks

(Upstream blockers, sequencing constraints, risk table.)
"""


# ── public API ────────────────────────────────────────────────────────────────


def release_new(specs_dir: Path, release_id: str) -> NewArtifactResult:
    """Create ``specs/releases/<release_id>/SPEC.md`` with a canonical stub.

    Args:
        specs_dir:  Absolute path to the ``specs/`` directory.
        release_id: New release identifier. Must be the SemVer canon ``vX.Y.Z``
            (preferred — what ``specs doctor`` SPEC-DOC-027 requires for a live dir) OR
            the legacy slug ``^[a-z][a-z0-9-]+$``.

    Returns:
        :class:`NewArtifactResult` with the path to the created ``SPEC.md``.

    Raises:
        ValueError:    If ``release_id`` is neither the SemVer canon nor the legacy slug.
        FileExistsError: If the release directory already exists (no-clobber).
    """
    if not _is_valid_release_id(release_id):
        raise ValueError(
            f"Invalid release ID {release_id!r}. "
            "Must be SemVer ^v\\d+\\.\\d+\\.\\d+$ (e.g. v0.1.23 — preferred, matches the "
            "specs-doctor naming canon) or the legacy slug ^[a-z][a-z0-9-]+$ "
            "(lowercase letters, digits, and hyphens; must start with a letter)."
        )

    release_dir = specs_dir / "releases" / release_id
    if release_dir.exists():
        raise FileExistsError(
            f"Release directory already exists: {release_dir}. "
            "Use a different release ID or remove the existing directory first."
        )

    release_dir.mkdir(parents=True, exist_ok=False)
    spec_path = release_dir / "SPEC.md"
    spec_path.write_text(
        _RELEASE_SPEC_STUB.format(release_id=release_id, today=_today()),
        encoding="utf-8",
    )
    return NewArtifactResult(path=spec_path, created=True)
