"""Specs-pattern versioning (FR-S01 / FR-S02).

A Spec Context Project's ``specs/`` tree conforms to a *pattern version* — the
canonical structural layout the workspace expects. The library carries the single
source of truth (:data:`CANONICAL_SPECS_VERSION`); each project records its own
version in the ``specs_pattern_version`` field of ``specs/constitution.md``'s YAML
frontmatter.

Absent-stamp semantics: a constitution with no frontmatter (or no
``specs_pattern_version`` key) is treated as **version 0** — pre-framework, the flat
layout that predates the tree-v2 migration. Doctor warns and recommends
``dadaia specs upgrade``.
"""

from __future__ import annotations

import re
from pathlib import Path

#: Single source of truth for the current canonical specs-pattern version.
#: Bump this when a new migration step is added to the registry (see ``registry.py``).
#: v3 = agent-tier-frontmatter (v0.1.72 FR1 — the missing v0.1.61 schema-drop migration).
CANONICAL_SPECS_VERSION = 3

#: Version assigned to a tree with no stamp (pre-framework flat layout).
UNSTAMPED_VERSION = 0

#: Single source of truth for the release-directory SemVer form ``vX.Y.Z`` (v0.1.53 FR3).
#: This is the ONE compiled home for the ``^v\d+\.\d+\.\d+$`` pattern — previously
#: triplicated in ``features/specs/scaffolder.py``, ``features/specs/doctor.py``, and
#: ``features/spec_artifacts/new_artifacts.py``. Every consumer imports THIS object; the
#: agreement contract ``tests/contract/test_release_semver_canon.py`` locks the identity
#: (same compiled object everywhere) and forbids any re-introduced ``re.compile`` copy.
RELEASE_SEMVER_RE = re.compile(r"^v\d+\.\d+\.\d+$")

_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
_STAMP_RE = re.compile(r"^specs_pattern_version:\s*(\d+)\s*$", re.MULTILINE)


def is_release_semver(value: str) -> bool:
    """Return ``True`` when ``value`` is the canonical release-dir SemVer form ``vX.Y.Z``.

    The single predicate for "is this string a strict ``v<major>.<minor>.<patch>``
    release id?" — used by the scaffolder, the doctor's release-folder naming checks, and
    the ``dadaia release new`` validator. Callers that also accept the legacy slug form
    compose this with their own slug check.
    """
    return RELEASE_SEMVER_RE.match(value) is not None


def _constitution_path(specs_dir: Path) -> Path:
    return specs_dir / "constitution.md"


def read_pattern_version(specs_dir: Path) -> int:
    """Return the ``specs_pattern_version`` stamped in the constitution.

    Returns :data:`UNSTAMPED_VERSION` (0) when the constitution is absent, has no
    YAML frontmatter, or the frontmatter omits the stamp.
    """
    constitution = _constitution_path(specs_dir)
    if not constitution.exists():
        return UNSTAMPED_VERSION
    text = constitution.read_text(encoding="utf-8")
    fm = _FRONTMATTER_RE.match(text)
    if fm is None:
        return UNSTAMPED_VERSION
    stamp = _STAMP_RE.search(fm.group(1))
    if stamp is None:
        return UNSTAMPED_VERSION
    return int(stamp.group(1))


def write_pattern_version(specs_dir: Path, version: int) -> None:
    """Stamp ``specs_pattern_version: <version>`` into the constitution frontmatter.

    Creates the YAML frontmatter block if absent; updates the stamp in place if the
    block already exists. Idempotent: re-stamping the same version is a no-op write.
    """
    constitution = _constitution_path(specs_dir)
    text = constitution.read_text(encoding="utf-8") if constitution.exists() else ""
    fm = _FRONTMATTER_RE.match(text)

    if fm is None:
        # No frontmatter: prepend a fresh block.
        new_text = f"---\nspecs_pattern_version: {version}\n---\n{text}"
        constitution.write_text(new_text, encoding="utf-8")
        return

    block = fm.group(1)
    if _STAMP_RE.search(block):
        new_block = _STAMP_RE.sub(f"specs_pattern_version: {version}", block)
    else:
        new_block = f"{block}\nspecs_pattern_version: {version}"
    new_text = f"---\n{new_block}\n---\n" + text[fm.end() :]
    constitution.write_text(new_text, encoding="utf-8")
