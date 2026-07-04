"""Enumerate every ``build_fragment_suffix`` caller and pin the ``is_review`` threading (A4).

This is the back-compat guard for the keyword-only, no-default ``is_review`` param
(D-2 / C2): the test ENUMERATES the known call sites and asserts each passes ``is_review``.
A new caller that omits the flag (or a new module that calls ``build_fragment_suffix``
without it) FAILS this test. It also asserts no new ``expected_schema=`` is wired at the
call sites (A4 — the default ``agent-run-result-v1`` stands; no per-step schema wiring).

The threading is asserted on the assembled source-level call (the keyword argument actually
passed), complemented by a behaviour check that ``build_fragment_suffix`` produces the
review-vs-create text for ``is_review=True``/``False`` respectively.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from dadaia_workspace.features.lifecycle.prompt_builder import (
    FragmentBundle,
    build_fragment_suffix,
)

_LIFECYCLE = Path(__file__).resolve().parents[4] / "dadaia_workspace" / "features" / "lifecycle"

#: Every module that calls ``build_fragment_suffix`` (D-2 / A4). Since v0.1.57 FR1 the four
#: handoff-ledger bodies (``release_definition`` / ``audit`` / ``research`` / ``bug_report``)
#: share ONE call in the ``_fragment_gate`` base — which threads ``step.is_review`` — instead of
#: a per-body copy. ``pipeline`` threads ``step.is_review``; ``backlog_definition`` threads the
#: literal ``False`` for its create steps. (The whole-tree scan below still guards every file.)
_CALLER_MODULES = {
    "workflows/_fragment_gate.py": "step.is_review",
    "workflows/backlog_definition.py": "False",
    "pipeline.py": "step.is_review",
}


def _suffix_calls(source: str) -> list[ast.Call]:
    tree = ast.parse(source)
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "build_fragment_suffix"
    ]


def _is_review_kw(call: ast.Call) -> ast.expr | None:
    for kw in call.keywords:
        if kw.arg == "is_review":
            return kw.value
    return None


@pytest.mark.parametrize("rel_path", sorted(_CALLER_MODULES))
def test_each_caller_threads_is_review(rel_path: str) -> None:
    source = (_LIFECYCLE / rel_path).read_text(encoding="utf-8")
    calls = _suffix_calls(source)
    assert calls, f"{rel_path} is a declared build_fragment_suffix caller but has no call"
    expected = _CALLER_MODULES[rel_path]
    for call in calls:
        value = _is_review_kw(call)
        assert value is not None, f"{rel_path}: build_fragment_suffix call omits is_review="
        assert ast.unparse(value) == expected, (
            f"{rel_path}: expected is_review={expected!r}, got {ast.unparse(value)!r}"
        )
        # No per-step expected_schema wiring at the call site (A4).
        assert all(kw.arg != "expected_schema" for kw in call.keywords), (
            f"{rel_path}: build_fragment_suffix call must not wire expected_schema="
        )


def test_no_other_module_calls_build_fragment_suffix_without_flag() -> None:
    """Any lifecycle module that calls build_fragment_suffix must thread is_review."""
    offenders: list[str] = []
    for path in _LIFECYCLE.rglob("*.py"):
        calls = _suffix_calls(path.read_text(encoding="utf-8"))
        for call in calls:
            if _is_review_kw(call) is None:
                offenders.append(str(path.relative_to(_LIFECYCLE)))
    assert not offenders, f"build_fragment_suffix called without is_review= in: {offenders}"


def _bundle() -> FragmentBundle:
    return FragmentBundle(
        fragment_id="spec.create",
        role="product-engineer",
        body="body",
        output_schema="release-scope-handoff-v1",
    )


def test_threading_behaviour_review_vs_create() -> None:
    review = build_fragment_suffix(_bundle(), selected_context="", is_review=True)
    create = build_fragment_suffix(_bundle(), selected_context="", is_review=False)
    assert "verdict" in review.lower()
    assert "verdict" not in create.lower()
