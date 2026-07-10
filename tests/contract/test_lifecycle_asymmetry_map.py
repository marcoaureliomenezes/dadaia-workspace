"""Lifecycle-asymmetry coverage-map completeness contract (T-011-11 / FR-W3-03, R2).

The "Lifecycle-asymmetry coverage map" in ``tests/contract/README.md`` discharges the
project's lifecycle-asymmetry policy: for every feature it records where the three
asymmetric paths (delete/orphan, dirty input, missing dependency) are covered, or marks
an honest ``GAP``. That map is a **hand-maintained pairing** with the actual set of
``dadaia_workspace/features/`` subpackages — and an unguarded hand-maintained pairing is
exactly where drift gets in (see README "Consistency-contract-at-introduction").

This contract closes that window mechanically. It enumerates the live ``features/``
subpackages via filesystem listing at test time and asserts that **every** subpackage is
accounted for in the map — either with a real-coverage row or an explicit ``GAP`` cell.
Adding a feature subpackage without giving it a map row (or an explicit GAP) fails here,
so the map can never silently fall behind the code again.

How a subpackage is "accounted for": its package name must appear as an inline code span
(backtick-wrapped, e.g. ``ci_preflight``) somewhere inside the coverage-map section of
the README. The map authors already name each feature's package and its real test paths
in backticks, so the contract reads the same tokens the human map declares — it does not
invent a parallel registry.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

#: Repository root: tests/contract/<this file> -> repo root is two parents up.
_REPO_ROOT = Path(__file__).resolve().parents[2]

#: The features package whose subpackages must each appear in the map.
_FEATURES_DIR = _REPO_ROOT / "dadaia_workspace" / "features"

#: The map lives in the contract-tests README.
_README = Path(__file__).resolve().parent / "README.md"

#: Heading that opens the coverage-map section. Everything from this heading to the next
#: top-level ``## `` heading (or EOF) is the parsed map region.
_MAP_HEADING = "## Lifecycle-asymmetry coverage map"

#: A subpackage is "named" in the map when it appears as an inline code span.
_CODE_SPAN_RE = re.compile(r"`([^`]+)`")


def _features_subpackages(features_dir: Path) -> set[str]:
    """Enumerate immediate subpackages of ``features_dir`` (dirs with ``__init__.py``).

    ``__pycache__`` and any non-package directory are excluded; the bare ``features``
    package ``__init__.py`` (a file, not a dir) is naturally skipped.
    """
    out: set[str] = set()
    for child in features_dir.iterdir():
        if not child.is_dir():
            continue
        if child.name == "__pycache__":
            continue
        if (child / "__init__.py").exists():
            out.add(child.name)
    return out


def _map_section(readme_text: str) -> str:
    """Slice the coverage-map section out of the README (heading -> next ``## ``/EOF)."""
    start = readme_text.find(_MAP_HEADING)
    assert start != -1, (
        f"coverage-map heading {_MAP_HEADING!r} not found in {_README} — the map is the "
        "deliverable that discharges the lifecycle-asymmetry policy"
    )
    rest = readme_text[start + len(_MAP_HEADING) :]
    next_heading = re.search(r"\n## ", rest)
    end = next_heading.start() if next_heading else len(rest)
    return rest[:end]


def _named_tokens(map_section: str) -> set[str]:
    """All inline-code-span tokens in the map section (e.g. ``ci_preflight``)."""
    tokens: set[str] = set()
    for span in _CODE_SPAN_RE.findall(map_section):
        # A span may name a path like ``unit/test_x.py::test_y`` — the bare package name
        # is what we match, so we keep the whole span and test membership below.
        tokens.add(span.strip())
    return tokens


def _is_accounted_for(pkg: str, map_section: str, named: set[str]) -> bool:
    """A subpackage is accounted for if its name appears as a standalone code span OR as
    a path segment inside any code span in the map section (real coverage), OR if the map
    explicitly names it with a ``GAP`` disposition on the same table row."""
    # Standalone code span ``pkg``.
    if pkg in named:
        return True
    # Path segment inside a code span, e.g. ``features/<pkg>/...`` or ``<pkg>/test_x.py``.
    seg_re = re.compile(rf"(?:^|[/.]){re.escape(pkg)}(?:[/.]|$)")
    return any(seg_re.search(span) for span in named)


def test_every_features_subpackage_is_in_the_asymmetry_map() -> None:
    subpackages = _features_subpackages(_FEATURES_DIR)
    assert subpackages, "no features subpackages enumerated — fixture/path is broken"

    section = _map_section(_README.read_text(encoding="utf-8"))
    named = _named_tokens(section)

    missing = sorted(pkg for pkg in subpackages if not _is_accounted_for(pkg, section, named))
    assert not missing, (
        "the lifecycle-asymmetry coverage map in tests/contract/README.md does not "
        f"account for these features/ subpackages: {missing}. Every subpackage must "
        "have a map row (real coverage) or an explicit GAP cell — add it in the same "
        "change that introduced the subpackage."
    )
