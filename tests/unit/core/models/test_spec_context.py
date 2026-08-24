"""``SpecContextProject.associated_repos`` and the one repo-resolution accessor (FR15).

Intent: CONTRACT — A15.3

The main repo (``repo_slug``/``repo_url``) stays the sole specs/bind target (G13, I4,
FR19); ``associated_repos`` is an *additive*, ordered collection next to it. A15.3
requires exactly one accessor for "the context's repos" — this module proves
``SpecContextProject.all_repos()`` is that accessor: main first, then every associated
repo in registration order, and that a context with zero associated repos yields exactly
the main repo (the behavioural half of A15.2, at the model layer).
"""

from __future__ import annotations

from dadaia_workspace.core.models.spec_context import (
    AssociatedRepo,
    ContextState,
    SpecContextProject,
)


def _ctx(**overrides: object) -> SpecContextProject:
    base: dict[str, object] = dict(
        name="alpha",
        state=ContextState.ALIVE,
        repo_slug="alpha",
        repo_url="https://github.com/org/alpha",
        created_at="2026-01-01T00:00:00Z",
    )
    base.update(overrides)
    return SpecContextProject(**base)  # type: ignore[arg-type]


def test_associated_repos_defaults_empty_and_is_ordered() -> None:
    ctx = _ctx()
    assert ctx.associated_repos == ()

    ordered = _ctx(
        associated_repos=(
            AssociatedRepo(slug="second", url="https://github.com/org/second"),
            AssociatedRepo(slug="first", url="https://github.com/org/first"),
        )
    )
    # Registration order is preserved verbatim — no implicit re-sort.
    assert ordered.associated_repos[0].slug == "second"
    assert ordered.associated_repos[1].slug == "first"


def test_all_repos_zero_associated_yields_only_main() -> None:
    """A15.2 (model half): zero associated repos == behaviourally just the main repo."""
    ctx = _ctx()
    assert ctx.all_repos() == (AssociatedRepo(slug="alpha", url="https://github.com/org/alpha"),)


def test_all_repos_main_first_then_associated_in_order() -> None:
    ctx = _ctx(
        associated_repos=(
            AssociatedRepo(slug="repo-b", url="https://github.com/org/repo-b"),
            AssociatedRepo(slug="repo-a", url="https://github.com/org/repo-a"),
        )
    )
    assert ctx.all_repos() == (
        AssociatedRepo(slug="alpha", url="https://github.com/org/alpha"),
        AssociatedRepo(slug="repo-b", url="https://github.com/org/repo-b"),
        AssociatedRepo(slug="repo-a", url="https://github.com/org/repo-a"),
    )


def test_associated_repo_is_frozen_and_comparable() -> None:
    a = AssociatedRepo(slug="x", url="https://github.com/org/x")
    b = AssociatedRepo(slug="x", url="https://github.com/org/x")
    assert a == b
    with_raises = False
    try:
        a.slug = "y"  # type: ignore[misc]
    except Exception:
        with_raises = True
    assert with_raises, "AssociatedRepo must be immutable (frozen dataclass)"
