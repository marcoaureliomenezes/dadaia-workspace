"""New-artifact creation helpers for dadaia CLI.

Implements:
- release_new:  creates specs/releases/<id>/SPEC.md stub
- backlog_new:  appends one ACTIVE subsection to specs/backlog/BACKLOG.md
  (SPEC v0.12.0 FR3, ADR #14 — the single-source document, not a per-entry file)

Both validate the slug/id; release_new refuses to clobber an existing release
directory, backlog_new refuses a slug already present in ACTIVE or LEDGER (A3.3). The
legacy ``bug_new`` Markdown scaffolder was retired in v0.1.53 — bugs are event-sourced
JSONL via ``dadaia bugs append`` (the v0.1.46 canon).
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

# ── backlog: single-source BACKLOG.md subsection writer (SPEC v0.12.0 FR3) ──────

# ``backlog_new`` authors an ``## ACTIVE`` subsection into ``specs/backlog/BACKLOG.md``
# instead of a per-entry file (ADR #14, ``dd-backlog-definition`` §2). Deliberately
# NOT importing ``features.backlog.document`` here: ``features/spec_artifacts`` and
# ``features/backlog`` are independent sibling features (``lint-imports``
# ``features-no-cross-feature`` — no accepted edge exists for this pair), so the
# writer re-derives the tiny slug-membership check it needs (below) rather than
# taking on a new cross-feature coupling. The shape it emits is exactly the grammar
# ``document.load_document`` parses (A3.5 — both go through the same schema even
# though not the same code), so the round trip closes without a shared import.

#: Every ACTIVE ``### <slug>`` heading in a ``BACKLOG.md`` text (module-level so a
#: freshly-created skeleton and an existing document share one membership check).
_ACTIVE_HEADING_RE = re.compile(r"^###[ \t]+(?P<slug>\S.*?)[ \t]*$", re.MULTILINE)

#: Every LEDGER bullet line's leading slug (``<slug> · disposition · ...``).
_LEDGER_LINE_RE = re.compile(r"^-[ \t]+(?P<slug>[^\s·]+)[ \t]*·", re.MULTILINE)

#: The ``## LEDGER`` top-level heading — the append anchor point (insert immediately
#: before it, preserving every other byte — A3.2).
_LEDGER_HEADING_RE = re.compile(r"^##[ \t]+LEDGER[ \t]*$", re.MULTILINE)

#: The skeleton a from-scratch document starts from — both section headings, nothing
#: else (A3.1). The SAME insertion routine used for an existing document runs over
#: this skeleton too, so there is exactly one append code path, not two.
_BACKLOG_DOCUMENT_SKELETON = "## ACTIVE\n\n## LEDGER\n"

# The subsection is born at ``status: idea`` — an unbound brainstorm. ``backlog doctor``
# exempts ``idea`` from the typed-intents requirement (v0.1.55 FR5, preserved verbatim
# over the new shape — SPEC v0.12.0 A2.3), so a fresh subsection is doctor-clean; the
# commented template TEACHES the ``**Intents:**`` fenced-YAML shape a maturing entry
# must adopt at `candidate` and beyond (a teaching template, NOT a live dummy subject
# that would gate-game). No ``.format`` field braces appear inside it beyond ``{slug}``/
# ``{today}``, so no escaping is needed.
_ACTIVE_SUBSECTION_TEMPLATE = """\
### {slug}
- **Title:** {slug}
- **Opened:** {today}
- **Status:** idea
- **Description:** (one-line description of the need)
- **Provenance:** operator request

<!--
An `idea` needs no `**Intents:**` block. Before promoting this entry to
`**Status:** candidate`, add one more bullet, ABOVE this comment: the bold key
`Intents` (followed by a colon and a fenced ```yaml block, the same way `Title`/
`Status` above are written) whose fenced content binds each change to a canonical
subject anchor, shaped like the fenced example below (copy it above this comment,
under its own `Intents` bullet, to make it live):

```yaml
- subject:
    kind: code
    ref: path/to/module.py#Symbol
  change: what changes about this subject
- subject:
    kind: cli
    ref: dadaia some-command
  change: what changes about this command
```

Discover bindable anchors with `dadaia backlog subjects`. Subject kinds: code | cli |
catalog | doc | invariant (code anchors are derived from Python sources only — in a
non-Python repo bind catalog/doc/invariant anchors instead).
-->

"""


def _backlog_slug_exists(text: str, slug: str) -> bool:
    """True iff *slug* already names an ACTIVE subsection or a LEDGER row (A3.3) —
    the slug-uniqueness invariant across ``ACTIVE ∪ LEDGER`` that replaces the retired
    per-file no-clobber check (grill P11: there is no longer a path to collide with)."""
    active_slugs = {m.group("slug") for m in _ACTIVE_HEADING_RE.finditer(text)}
    ledger_slugs = {m.group("slug") for m in _LEDGER_LINE_RE.finditer(text)}
    return slug in active_slugs or slug in ledger_slugs


def _append_active_subsection(text: str, block: str) -> str:
    """Splice *block* in immediately before the ``## LEDGER`` heading.

    A pure string-slice insertion: every byte before and after the insertion point is
    untouched (A3.2's byte-diff guarantee). Falls back to appending at end-of-file only
    if ``## LEDGER`` is somehow absent (a malformed document outside this writer's own
    skeleton/append contract) — a defensive path, not the birth of a THIRD document
    shape: the appended text still conforms to the schema ``document.load_document``
    expects.
    """
    match = _LEDGER_HEADING_RE.search(text)
    if match is None:
        return text.rstrip("\n") + "\n\n" + block
    insertion_point = match.start()
    return text[:insertion_point] + block + text[insertion_point:]


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
    """Append one ``### <slug>`` ACTIVE subsection to ``specs/backlog/BACKLOG.md``
    (SPEC v0.12.0 FR3, ADR #14) — creating the document with both ``## ACTIVE`` and
    ``## LEDGER`` section headings first when it does not yet exist.

    Args:
        specs_dir: Absolute path to the ``specs/`` directory.
        slug:      Backlog entry slug.  Must match ``^[a-z][a-z0-9-]+$``.

    Returns:
        :class:`NewArtifactResult` with the path to ``BACKLOG.md``.

    Raises:
        ValueError:      If ``slug`` does not match the slug pattern (A3.4, unchanged
            message).
        FileExistsError: If ``slug`` already names an ACTIVE subsection or a LEDGER
            row (A3.3 — the slug-uniqueness invariant across ``ACTIVE ∪ LEDGER`` that
            replaces the retired per-file no-clobber check; same exception class and
            CLI exit-code class as the retired path, grill P11).
    """
    if not _SLUG_RE.match(slug):
        raise ValueError(
            f"Invalid slug {slug!r}. "
            "Must match ^[a-z][a-z0-9-]+$ "
            "(lowercase letters, digits, and hyphens; must start with a letter)."
        )

    backlog_dir = specs_dir / "backlog"
    backlog_dir.mkdir(parents=True, exist_ok=True)
    target = backlog_dir / "BACKLOG.md"
    existing_text = (
        target.read_text(encoding="utf-8") if target.is_file() else (_BACKLOG_DOCUMENT_SKELETON)
    )

    if _backlog_slug_exists(existing_text, slug):
        raise FileExistsError(
            f"Backlog slug already exists: {slug!r} is already present in ACTIVE or "
            f"LEDGER of {target}. Use a different slug."
        )

    block = _ACTIVE_SUBSECTION_TEMPLATE.format(slug=slug, today=_today())
    target.write_text(_append_active_subsection(existing_text, block), encoding="utf-8")
    return NewArtifactResult(path=target, created=True)
