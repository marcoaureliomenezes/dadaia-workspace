"""AC3.2, AC3.3 (T-050-10): a memory stub is recognised as shipped by
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
from dadaia_workspace.core.platform import Capabilities
from dadaia_workspace.core.template_history import was_shipped
from dadaia_workspace.core.workspace_layout import render_registry_tables

_PUBLIC = Path(__file__).resolve().parents[2] / "dadaia_workspace" / "public"
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


def test_a_law_rendered_for_win32_reads_shipped(monkeypatch: pytest.MonkeyPatch) -> None:
    """shipped-law-hardcodes-the-posix-venv-path: history holds recorded Windows digests;
    forward-rendering an authored law to `Scripts/dadaia.exe` still identifies it as ours."""
    monkeypatch.setattr("dadaia_workspace.core.platform.PLATFORM", Capabilities.detect("win32"))
    source = (_PUBLIC / "scaffold" / "memory" / "AGENTS.md").read_text(encoding="utf-8")
    rendered = render_registry_tables(source)
    assert rendered != source
    assert was_shipped(rendered, "scaffold/memory/AGENTS.md", _TEMPLATES)
    assert not was_shipped(rendered + "x", "scaffold/memory/AGENTS.md", _TEMPLATES)
