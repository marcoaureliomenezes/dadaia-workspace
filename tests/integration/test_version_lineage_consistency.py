"""Version / CHANGELOG lineage-consistency sentinel.

Intent: SENTINEL — the two shipping surfaces of the package version must agree
mechanically (bug ``minted-version-skips-published-lineage``: the release minted
``0.4.3`` in ``pyproject.toml`` while the publishable next number on the real
lineage was ``0.4.2``; nothing paired the CHANGELOG's top release section with the
minted version, so a renumber could drift the two surfaces apart silently — this
test is the RED reproduction of exactly that drift, and stays as the pairing).

Size: SMALL — two tracked-file reads, no subprocess, no network.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

_REPO_ROOT = Path(__file__).resolve().parents[2]

#: The one shape a PUBLISHED version section heading has (Keep a Changelog):
#: ``## [x.y.z] — YYYY-MM-DD``. ``[Unreleased]`` and ``— in progress`` headings never
#: match, by design: a section without a publication date names no published version,
#: and since T-047-90 ``pyproject.toml`` sits at the published floor release-please
#: bumps from, not at the id of the release being written.
_VERSION_HEADING = re.compile(r"^## \[(\d+\.\d+\.\d+)\] [-—] \d{4}-\d{2}-\d{2}\s*$", re.MULTILINE)


def test_pyproject_version_equals_changelog_top_section() -> None:
    """The minted version and the CHANGELOG's newest PUBLISHED section are one fact."""
    pyproject = tomllib.loads((_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    minted = pyproject["tool"]["poetry"]["version"]

    changelog = (_REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    match = _VERSION_HEADING.search(changelog)
    assert match is not None, "CHANGELOG.md has no dated `## [x.y.z] — <date>` section"

    assert match.group(1) == minted, (
        f"pyproject.toml mints {minted!r} but CHANGELOG.md's top release section is "
        f"[{match.group(1)}] — the two shipping surfaces must state the same version"
    )
