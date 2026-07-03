"""New-artifact creation helpers for dadaia CLI.

Implements:
- release_new:  creates specs/releases/<id>/SPEC.md stub
- backlog_new:  creates specs/backlog/<slug>.md stub

Both validate the slug/id and refuse to clobber existing artifacts. The legacy
``bug_new`` Markdown scaffolder was retired in v0.1.53 — bugs are event-sourced JSONL
via ``dadaia bugs append`` (the v0.1.46 canon).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from dadaia_workspace.core.specs_version import RELEASE_SEMVER_RE

# ── slug validation patterns ──────────────────────────────────────────────────
# Shared pattern for backlog/bug slugs (and the legacy release-id form):
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

# ── backlog entry stub ────────────────────────────────────────────────────────

# The stub is born at ``status: idea`` — an unbound brainstorm. ``backlog doctor`` exempts
# ``idea`` from the typed-``intents[]`` requirement (v0.1.55 FR5), so a fresh stub is clean; the
# commented template below TEACHES the shape a maturing entry must adopt at ``candidate`` and
# beyond (a teaching template, NOT a live dummy subject that would gate-game). No ``.format``
# field braces appear inside it, so no escaping is needed.
_BACKLOG_STUB = """\
---
title: {slug}
status: idea
opened: {today}
description: (one-line description of the need)
---

# {slug}

## Description

(Describe the backlog item here.)

## Motivation

(Why is this item worth pursuing?)

## Acceptance criteria

(List measurable acceptance criteria.)

## Intents (required at `candidate` and beyond)

<!--
An `idea` needs no `intents[]`. Before promoting this entry to `status: candidate`, add a
typed `intents[]` frontmatter block binding each change to a canonical subject anchor, then
move it ABOVE the closing `---` of the frontmatter. Discover bindable anchors with
`dadaia backlog subjects`. Subject kinds: code | cli | catalog | doc | invariant
(code anchors are derived from Python sources only — in a non-Python repo bind catalog/doc/
invariant anchors instead).

intents:
  - subject:
      kind: code
      ref: path/to/module.py#Symbol
    change: what changes about this subject
  - subject:
      kind: cli
      ref: dadaia some-command
    change: what changes about this command
-->
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


def backlog_new(specs_dir: Path, slug: str) -> NewArtifactResult:
    """Create ``specs/backlog/<slug>.md`` with a canonical frontmatter stub.

    Args:
        specs_dir: Absolute path to the ``specs/`` directory.
        slug:      Backlog entry slug.  Must match ``^[a-z][a-z0-9-]+$``.

    Returns:
        :class:`NewArtifactResult` with the path to the created file.

    Raises:
        ValueError:    If ``slug`` does not match the slug pattern.
        FileExistsError: If the file already exists (no-clobber).
    """
    if not _SLUG_RE.match(slug):
        raise ValueError(
            f"Invalid slug {slug!r}. "
            "Must match ^[a-z][a-z0-9-]+$ "
            "(lowercase letters, digits, and hyphens; must start with a letter)."
        )

    backlog_dir = specs_dir / "backlog"
    backlog_dir.mkdir(parents=True, exist_ok=True)
    target = backlog_dir / f"{slug}.md"
    if target.exists():
        raise FileExistsError(
            f"Backlog entry already exists: {target}. "
            "Remove the existing file or use a different slug."
        )

    target.write_text(
        _BACKLOG_STUB.format(slug=slug, today=_today()),
        encoding="utf-8",
    )
    return NewArtifactResult(path=target, created=True)
