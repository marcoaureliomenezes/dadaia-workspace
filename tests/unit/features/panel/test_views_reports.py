"""Tests for the Reports + Academy tabpanel scaffolds (merges test_views_academy.py).

Covers the static Reports and Academy tabpanel skeletons: each is a focusable
``<section>`` tab target carrying the correct id, ARIA wiring, heading, content
div (hidden by default for Reports), and a loading placeholder for
client-side population.

One merged param (section id, tabpanel ARIA, content div, hidden default,
placeholder).
"""

from __future__ import annotations

import pytest

from dadaia_workspace.features.panel.views.academy import render_academy_section
from dadaia_workspace.features.panel.views.reports import render_reports_section

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("render_fn", "section_id", "tab_id", "heading", "content_div_id", "hidden_by_default"),
    [
        pytest.param(
            render_reports_section,
            "section-reports",
            "tab-reports",
            "Reports",
            "reports-content",
            True,
            id="reports-scaffold",
        ),
        pytest.param(
            render_academy_section,
            "section-academy",
            "tab-academy",
            "Academy",
            "academy-content",
            False,
            id="academy-scaffold",
        ),
    ],
)
def test_section_scaffold(
    render_fn,  # type: ignore[no-untyped-def]
    section_id: str,
    tab_id: str,
    heading: str,
    content_div_id: str,
    hidden_by_default: bool,
) -> None:
    result = render_fn()
    stripped = result.strip()

    # Root element is a focusable <section> ... </section> tab target.
    assert stripped.startswith("<section")
    assert "</section>" in stripped
    assert f'id="{section_id}"' in result
    assert 'role="tabpanel"' in result
    assert f'aria-labelledby="{tab_id}"' in result
    assert "tabindex" in result

    # Heading + content div for JS population + loading placeholder.
    assert heading in result
    assert "<h2>" in result or "<h2 " in result
    assert f'id="{content_div_id}"' in result
    assert "empty-state" in result or "Loading" in result

    if hidden_by_default:
        assert "hidden" in result
        assert 'id="reports-list"' in result
