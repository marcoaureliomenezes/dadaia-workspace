"""Intent: CONTRACT — AC3.2, AC3.3 (T-050-10): a memory stub is recognised as shipped by
its stripped digest (fixed sections removed), so a ``doctor --fix`` FIXED-2 rewrite of an
untouched stub still reads as ours and an edited body does not."""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.core.fixed_sections import (
    FIXED_SECTIONS,
    render_fixed_section,
    strip_fixed_sections,
)
from dadaia_workspace.core.template_history import was_shipped

_PUBLIC = Path(__file__).resolve().parents[3] / "dadaia_workspace" / "public"
_TEMPLATES = _PUBLIC / "templates"
_STUBS = {rel: section for rel, section in FIXED_SECTIONS if rel.startswith("memory/")}


@pytest.mark.parametrize("rel", sorted(_STUBS))
def test_fixed2_rewritten_stub_reads_shipped(rel: str) -> None:
    stub = (_PUBLIC / "scaffold" / rel).read_text(encoding="utf-8")
    fragment = (_PUBLIC / "data" / "fixed" / f"{_STUBS[rel]}.md").read_text(encoding="utf-8")
    rewritten = render_fixed_section(stub, _STUBS[rel], fragment)
    assert rewritten != stub
    assert was_shipped(strip_fixed_sections(rewritten), f"scaffold/{rel}", _TEMPLATES)

    edited = rewritten.replace("## ", "## Real project — ", 1)
    assert not was_shipped(strip_fixed_sections(edited), f"scaffold/{rel}", _TEMPLATES)


def test_a_stub_from_before_fixed_sections_strips_to_the_same_text() -> None:
    marked = "# T\n\nbody\n\n<!-- dadaia:fixed x -->\nlaw\n<!-- /dadaia:fixed x -->\n"
    assert strip_fixed_sections(marked) == strip_fixed_sections("# T\n\nbody\n") == "# T\n\nbody\n"
