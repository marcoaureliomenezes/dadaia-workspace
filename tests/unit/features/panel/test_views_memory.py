"""Tests for views/memory.py — Markdown-source render (T-MMS-06).

Covers:
  - .md atoms are rendered to HTML in-memory (D-4).
  - Mermaid fences → <pre class="mermaid"> (D-1).
  - [[wikilink]] → <a> anchor (D-1).
  - No raw <script> or <style> survives in output (OWASP A03).
  - Path traversal outside memory_root returns 404 (OWASP A03).
  - Non-Markdown assets are still served verbatim.
  - Missing file returns 404.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.panel.views.memory import render_memory

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FIXTURES_DIR = Path(__file__).parent.parent.parent.parent / "fixtures" / "memory"


def _build_memory_root(tmp_path: Path, slug: str) -> Path:
    """Create <tmp_path>/repos/<slug>/specs/memory/ and return tmp_path."""
    (tmp_path / "repos" / slug / "specs" / "memory").mkdir(parents=True)
    return tmp_path


def _write_md(tmp_path: Path, slug: str, filename: str, content: str) -> Path:
    """Write a .md file into <tmp_path>/repos/<slug>/specs/memory/<filename>."""
    target_dir = tmp_path / "repos" / slug / "specs" / "memory"
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / filename).write_text(content, encoding="utf-8")
    return tmp_path


def _write_bytes(tmp_path: Path, slug: str, filename: str, data: bytes) -> Path:
    """Write a binary file into <tmp_path>/repos/<slug>/specs/memory/<filename>."""
    target_dir = tmp_path / "repos" / slug / "specs" / "memory"
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / filename).write_bytes(data)
    return tmp_path


# ---------------------------------------------------------------------------
# Mermaid rendering
# ---------------------------------------------------------------------------


def test_mermaid_fence_renders_to_pre_mermaid(tmp_path: Path) -> None:
    """A ```mermaid fenced block must render to <pre class="mermaid">...</pre>.

    The Mermaid JS client on the panel page processes this block client-side.
    Content must NOT be HTML-escaped (e.g. --> must remain --> not &rarr;).
    """
    md = "# Diagram\n\n```mermaid\ngraph LR\n  A-->B\n```\n"
    workspace_root = _write_md(tmp_path, "proj", "architecture.md", md)

    view = render_memory(workspace_root)
    status, content_type, body = view(slug="proj", path="architecture.md")

    assert status == 200
    assert content_type == "text/html; charset=utf-8"
    html = body.decode("utf-8")
    # Must produce <pre class="mermaid">
    assert '<pre class="mermaid">' in html
    # Must NOT produce language-mermaid (that is the escaped version)
    assert "language-mermaid" not in html
    # Diagram content must be verbatim (not escaped)
    assert "A-->B" in html


def test_mermaid_fence_with_sequence_arrows(tmp_path: Path) -> None:
    """Sequence diagram arrow operators (->> and -->) must survive verbatim."""
    md = "```mermaid\nsequenceDiagram\n  A->>B: hello\n  B-->A: ok\n```\n"
    workspace_root = _write_md(tmp_path, "proj", "seq.md", md)

    view = render_memory(workspace_root)
    status, _, body = view(slug="proj", path="seq.md")

    assert status == 200
    html = body.decode("utf-8")
    assert "A->>B" in html
    assert "B-->A" in html
    # Must not appear as HTML entities
    assert "&gt;&gt;" not in html


# ---------------------------------------------------------------------------
# Wikilink rendering
# ---------------------------------------------------------------------------


def test_wikilink_renders_to_anchor(tmp_path: Path) -> None:
    """[[slug]] wikilinks must convert to <a> anchors for the panel memory route."""
    md = "See [[architecture]] for details.\n"
    workspace_root = _write_md(tmp_path, "proj", "index.md", md)

    view = render_memory(workspace_root)
    status, _, body = view(slug="proj", path="index.md")

    assert status == 200
    html = body.decode("utf-8")
    assert "<a" in html
    assert "architecture" in html
    # Must link to the panel memory-view route
    assert "/memory-view/" in html


def test_wikilink_multiple_slugs_in_one_atom(tmp_path: Path) -> None:
    """Multiple [[wikilinks]] in one document all render as anchors."""
    md = "See [[architecture]] and [[tech-stack]] and [[panel]].\n"
    workspace_root = _write_md(tmp_path, "proj", "multi.md", md)

    view = render_memory(workspace_root)
    _, _, body = view(slug="proj", path="multi.md")

    html = body.decode("utf-8")
    assert html.count("<a") >= 3
    assert "architecture" in html
    assert "tech-stack" in html
    assert "panel" in html


# ---------------------------------------------------------------------------
# Sanitiser (OWASP A03)
# ---------------------------------------------------------------------------


def test_script_tag_is_stripped_from_output(tmp_path: Path) -> None:
    """Raw <script> in atom content must NOT survive in rendered HTML."""
    md = "Text before\n\n<script>alert('xss')</script>\n\nText after\n"
    workspace_root = _write_md(tmp_path, "proj", "evil.md", md)

    view = render_memory(workspace_root)
    status, _, body = view(slug="proj", path="evil.md")

    assert status == 200
    html = body.decode("utf-8")
    assert "<script>" not in html
    assert "alert('xss')" not in html


def test_style_tag_is_stripped_from_output(tmp_path: Path) -> None:
    """Raw <style> in atom content must NOT survive in rendered HTML."""
    md = "Normal text\n\n<style>body { display: none; }</style>\n\nMore text\n"
    workspace_root = _write_md(tmp_path, "proj", "evil2.md", md)

    view = render_memory(workspace_root)
    status, _, body = view(slug="proj", path="evil2.md")

    assert status == 200
    html = body.decode("utf-8")
    assert "<style>" not in html
    assert "display: none" not in html


# ---------------------------------------------------------------------------
# Path traversal guard (OWASP A03)
# ---------------------------------------------------------------------------


def test_path_traversal_rejected_for_md(tmp_path: Path) -> None:
    """Path traversal (../../secrets) must return 404, not leak content."""
    workspace_root = _write_md(tmp_path, "slug", "ok.md", "# OK\n")

    # Place a sensitive file outside the memory root
    sensitive = tmp_path / "secrets.txt"
    sensitive.write_text("TOP SECRET", encoding="utf-8")

    view = render_memory(workspace_root)
    status, _, body = view(slug="slug", path="../../secrets.txt")

    assert status == 404
    assert b"TOP SECRET" not in body


def test_path_traversal_etc_passwd_rejected(tmp_path: Path) -> None:
    """Classic ../../../etc/passwd traversal must return 404."""
    workspace_root = _write_md(tmp_path, "slug", "ok.md", "# OK\n")

    view = render_memory(workspace_root)
    status, _, _ = view(slug="slug", path="../../../etc/passwd")

    assert status == 404


# ---------------------------------------------------------------------------
# Non-Markdown assets served verbatim
# ---------------------------------------------------------------------------


def test_png_asset_served_verbatim(tmp_path: Path) -> None:
    """PNG (non-Markdown) asset must be served byte-for-byte unchanged."""
    data = bytes(range(256)) + b"\x89PNG"
    workspace_root = _write_bytes(tmp_path, "proj", "diagram.png", data)

    view = render_memory(workspace_root)
    status, content_type, body = view(slug="proj", path="diagram.png")

    assert status == 200
    assert content_type == "image/png"
    assert body == data


def test_legacy_html_served_verbatim(tmp_path: Path) -> None:
    """Legacy .html files are still served byte-identical (for transition period)."""
    data = b"<!DOCTYPE html><html><body>legacy</body></html>"
    workspace_root = _write_bytes(tmp_path, "proj", "old.html", data)

    view = render_memory(workspace_root)
    status, content_type, body = view(slug="proj", path="old.html")

    assert status == 200
    assert content_type == "text/html; charset=utf-8"
    assert body == data


# ---------------------------------------------------------------------------
# Missing file → 404
# ---------------------------------------------------------------------------


def test_missing_md_file_returns_404(tmp_path: Path) -> None:
    """A request for a .md file that does not exist must return 404."""
    workspace_root = _build_memory_root(tmp_path, "proj")

    view = render_memory(workspace_root)
    status, _, _ = view(slug="proj", path="nonexistent.md")

    assert status == 404


# ---------------------------------------------------------------------------
# GFM tables render correctly
# ---------------------------------------------------------------------------


def test_table_renders_to_html_table(tmp_path: Path) -> None:
    """GFM table syntax must produce a <table> element."""
    md = "| A | B |\n|---|---|\n| 1 | 2 |\n"
    workspace_root = _write_md(tmp_path, "proj", "table.md", md)

    view = render_memory(workspace_root)
    status, _, body = view(slug="proj", path="table.md")

    assert status == 200
    html = body.decode("utf-8")
    assert "<table>" in html
    assert "<th>" in html or "<thead>" in html


# ---------------------------------------------------------------------------
# Fixture-based integration: 3 real .md fixtures render correctly
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("fixture_file", "expected_slugs", "expect_mermaid", "expect_wikilinks"),
    [
        ("architecture.md", ["tech-stack", "panel"], True, True),
        ("tech-stack.md", [], False, False),
        ("panel.md", ["architecture", "tech-stack"], True, True),
    ],
)
def test_fixture_md_renders_correctly(
    tmp_path: Path,
    fixture_file: str,
    expected_slugs: list[str],
    expect_mermaid: bool,
    expect_wikilinks: bool,
) -> None:
    """Fixture .md atoms (core + product) render with correct Mermaid/wikilink output.

    These fixtures live in tests/fixtures/memory/ and contain the key structures
    we need to verify:
    - Mermaid blocks → <pre class="mermaid">
    - [[wikilinks]] → <a> anchors
    - No raw <script> or <style> survives
    """
    fixture_path = _FIXTURES_DIR / fixture_file
    assert fixture_path.exists(), f"Fixture missing: {fixture_path}"

    content = fixture_path.read_text(encoding="utf-8")
    slug_name = fixture_file.replace(".md", "")

    # Copy into tmp workspace layout
    workspace_root = _write_md(tmp_path, "dadaia-workspace", fixture_file, content)

    view = render_memory(workspace_root)
    status, content_type, body = view(slug="dadaia-workspace", path=fixture_file)

    assert status == 200
    assert "text/html" in content_type
    html = body.decode("utf-8")

    # No XSS
    assert "<script>" not in html
    assert "<style>" not in html

    # Mermaid
    if expect_mermaid:
        assert '<pre class="mermaid">' in html, (
            f'{slug_name}: expected <pre class="mermaid"> but not found in rendered HTML'
        )
        assert "language-mermaid" not in html

    # Wikilinks
    if expect_wikilinks:
        assert "<a" in html, f"{slug_name}: expected wikilink <a> anchors"
        assert "/memory-view/" in html
        for slug in expected_slugs:
            assert slug in html, f"{slug_name}: expected [[{slug}]] to appear in rendered HTML"


# ---------------------------------------------------------------------------
# Constitution allowlist (operator demand 2026-06-11): the single literal path
# `constitution.md` re-roots to repos/<slug>/specs/constitution.md. Nothing
# else under specs/ is reachable through the memory routes.
# ---------------------------------------------------------------------------


def _mk_ws(tmp_path):
    slug = "ctx"
    specs = tmp_path / "repos" / slug / "specs"
    (specs / "memory").mkdir(parents=True)
    (specs / "releases").mkdir()
    (specs / "constitution.md").write_text("# Constitution\n\nThe law of the project.\n")
    (specs / "releases" / "ACTIVE.md").write_text("release: x\n")
    (specs / "memory" / "architecture.md").write_text("# Arch\n")
    return slug


def test_constitution_md_served_via_allowlist(tmp_path) -> None:
    from dadaia_workspace.features.panel.views.memory import render_memory

    slug = _mk_ws(tmp_path)
    view = render_memory(tmp_path)
    status, ct, body = view(slug=slug, path="constitution.md")
    assert status == 200
    assert "text/html" in ct
    html = body.decode("utf-8")
    assert "<h1" in html and "Constitution" in html
    assert "# Constitution" not in html  # rendered, not raw


def test_specs_paths_other_than_constitution_stay_404(tmp_path) -> None:
    from dadaia_workspace.features.panel.views.memory import render_memory

    slug = _mk_ws(tmp_path)
    view = render_memory(tmp_path)
    for escape in (
        "../constitution.md",
        "../releases/ACTIVE.md",
        "releases/ACTIVE.md",
        "../../specs/constitution.md",
    ):
        status, _, _ = view(slug=slug, path=escape)
        assert status == 404, f"{escape!r} must stay unreachable"


def test_constitution_missing_file_is_404(tmp_path) -> None:
    from dadaia_workspace.features.panel.views.memory import render_memory

    slug = "bare"
    (tmp_path / "repos" / slug / "specs" / "memory").mkdir(parents=True)
    view = render_memory(tmp_path)
    status, _, _ = view(slug=slug, path="constitution.md")
    assert status == 404
