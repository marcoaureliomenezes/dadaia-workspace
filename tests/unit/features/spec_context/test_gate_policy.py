"""T-010-03 / WS-R1: classifier re-root — full class×location taxonomy.

The 2026-06-10 audit (CONF-1 CRITICAL, arch F1, sec F-1) proved the gate's class
taxonomy was computed on the **workspace-root-relative** path, so every in-repo write
(``repos/<slug>/...``) matched MUTATING first: in-repo bugs/backlog/audits acquired or
stole the per-context lease (the lease-theft incident), in-repo ``specs/memory`` bypassed
the PE phase lock, and in-repo ``specs/_archive`` was writable. All real Spec Context
artifacts live under ``repos/<slug>/specs/``, so the ADDITIVE/MEMORY/FROZEN classes were
dead for every compliant workspace.

This matrix asserts ``classify_path`` applies the ordered ``specs/`` taxonomy
**context-relatively**: every class × {workspace-root, in-repo} × {default slug,
non-default slug}, plus the two no-class-match MUTATING rows the audit named explicitly —
in-repo production source and in-repo ``specs/constitution.md``. An in-repo remainder that
matches no class is MUTATING (FR-R1-04), **never** UNGATED.
"""

from __future__ import annotations

import pytest

from dadaia_workspace.features.spec_context.gate_policy import PathClass, classify_path

# The default (self-hosting) context slug and a non-default consumer slug. The class of a
# path must depend only on its context-relative remainder, never on which slug it is.
_DEFAULT_SLUG = "dadaia-workspace"
_NONDEFAULT_SLUG = "rand-engine"


def _in_repo(slug: str, ctx_rel: str) -> str:
    return f"repos/{slug}/{ctx_rel}"


# (row_id, ctx_rel_or_root_suffix, expected_class)
# Each spec-relative path is asserted at the workspace root AND in-repo (both slugs).
# ``specs/releases`` is MUTATING at root via the explicit release rule, and in-repo via the
# no-class-match ⇒ MUTATING re-root rule — the same verdict from two code paths.
_SPEC_RELATIVE_CASES: tuple[tuple[str, str, PathClass], ...] = (
    ("additive_bugs", "specs/bugs/lease-stolen.md", PathClass.ADDITIVE),
    ("additive_backlog", "specs/backlog/epic.md", PathClass.ADDITIVE),
    ("additive_audits", "specs/audits/2026-01-01T000000Z-abc12345/index.md", PathClass.ADDITIVE),
    ("memory_atom", "specs/memory/architecture.md", PathClass.MEMORY),
    ("memory_product", "specs/memory/product/catalog.md", PathClass.MEMORY),
    ("frozen_archive", "specs/_archive/releases/v0.1.9/SPEC.md", PathClass.FROZEN),
    ("mutating_release", "specs/releases/v0.1.10/SPEC.md", PathClass.MUTATING),
    # No-class-match in-repo rows the audit named explicitly (FR-R1-04). At the workspace
    # root these classify UNGATED (no repo, no spec class) — asserted separately below.
    ("mutating_constitution", "specs/constitution.md", PathClass.MUTATING),
)

# Workspace-root verdict for each spec-relative suffix (UNGATED where no root rule matches).
_ROOT_VERDICT_OVERRIDES: dict[str, PathClass] = {
    # 'specs/constitution.md' at the workspace root is not under any class prefix → UNGATED.
    "mutating_constitution": PathClass.UNGATED,
}


@pytest.mark.parametrize("row", _SPEC_RELATIVE_CASES, ids=[r[0] for r in _SPEC_RELATIVE_CASES])
def test_workspace_root_classification(row: tuple[str, str, PathClass]) -> None:
    row_id, suffix, in_repo_expected = row
    expected = _ROOT_VERDICT_OVERRIDES.get(row_id, in_repo_expected)
    assert classify_path(suffix) == expected, f"root row {row_id}"


@pytest.mark.parametrize("slug", [_DEFAULT_SLUG, _NONDEFAULT_SLUG], ids=["default", "nondefault"])
@pytest.mark.parametrize("row", _SPEC_RELATIVE_CASES, ids=[r[0] for r in _SPEC_RELATIVE_CASES])
def test_in_repo_classification(row: tuple[str, str, PathClass], slug: str) -> None:
    """In-repo paths classify by their context-relative remainder (FR-R1-01..04)."""
    row_id, ctx_rel, expected = row
    assert classify_path(_in_repo(slug, ctx_rel)) == expected, f"in-repo {row_id} slug={slug}"


# In-repo production source — the canonical no-class-match ⇒ MUTATING case (FR-R1-04).
# These have NO workspace-root analogue (production source only lives in repos).
_IN_REPO_PRODUCTION_CASES: tuple[tuple[str, str], ...] = (
    ("library_source", "dadaia_workspace/features/spec_context/gate_policy.py"),
    ("consumer_src", "src/engine/run.py"),
    ("repo_pyproject", "pyproject.toml"),
    ("repo_readme", "README.md"),
    ("repo_tests", "tests/unit/test_x.py"),
)


@pytest.mark.parametrize("slug", [_DEFAULT_SLUG, _NONDEFAULT_SLUG], ids=["default", "nondefault"])
@pytest.mark.parametrize(
    "row", _IN_REPO_PRODUCTION_CASES, ids=[r[0] for r in _IN_REPO_PRODUCTION_CASES]
)
def test_in_repo_production_source_is_mutating(row: tuple[str, str], slug: str) -> None:
    """In-repo production source ⇒ MUTATING, never UNGATED (FR-R1-04, the lease guard)."""
    row_id, ctx_rel = row
    assert classify_path(_in_repo(slug, ctx_rel)) == PathClass.MUTATING, f"{row_id} slug={slug}"


def test_in_repo_unmatched_never_ungated() -> None:
    """The core invariant: a ctx_rel matching no class NEVER falls through to UNGATED."""
    for path in (
        _in_repo(_DEFAULT_SLUG, "specs/constitution.md"),
        _in_repo(_DEFAULT_SLUG, "dadaia_workspace/__init__.py"),
        _in_repo(_NONDEFAULT_SLUG, "specs/some-loose-file.md"),
        _in_repo(_NONDEFAULT_SLUG, "Makefile"),
    ):
        assert classify_path(path) != PathClass.UNGATED, path
        assert classify_path(path) == PathClass.MUTATING, path


def test_workspace_root_dadaia_additive_preserved() -> None:
    """FR-R1-05: workspace-root .dadaia/ ADDITIVE prefixes are unchanged (no regression).

    The .dadaia/ ADDITIVE classes are workspace-root-only — .dadaia/ is forbidden inside
    any repo working tree, so there is no in-repo analogue to honor.
    """
    assert classify_path(".dadaia/reports/ctx/agent/r.html") == PathClass.ADDITIVE
    assert classify_path(".dadaia/handoff/ctx/h.json") == PathClass.ADDITIVE
    assert classify_path(".dadaia/tmp/agent/x.txt") == PathClass.ADDITIVE


def test_workspace_root_protected_and_ungated_preserved() -> None:
    """FR-R1-05: PROTECTED (sole fail-closed) and UNGATED fall-through unchanged at root."""
    assert classify_path(".dadaia/sessions/runtime/ctx.ptr") == PathClass.PROTECTED
    assert classify_path("README.md") == PathClass.UNGATED
    assert classify_path("some/loose/path.txt") == PathClass.UNGATED


def test_leading_slash_is_stripped() -> None:
    """An absolute-looking workspace path classifies identically to its relative form."""
    assert classify_path("/specs/bugs/x.md") == classify_path("specs/bugs/x.md")
    assert classify_path("/repos/foo/specs/memory/a.md") == PathClass.MEMORY


def test_bare_repo_prefix_is_mutating() -> None:
    """'repos/<slug>' with no remainder is still in-repo ⇒ MUTATING (not UNGATED)."""
    assert classify_path("repos/foo") == PathClass.MUTATING
    assert classify_path("repos/foo/") == PathClass.MUTATING


def test_first_match_wins_ordering_in_repo() -> None:
    """Ordered classification (FR-P1-05) holds context-relatively: ADDITIVE before MUTATING."""
    # A bugs path under a release-looking dir still matches ADDITIVE first by prefix order.
    assert classify_path(_in_repo(_DEFAULT_SLUG, "specs/bugs/x.md")) == PathClass.ADDITIVE
