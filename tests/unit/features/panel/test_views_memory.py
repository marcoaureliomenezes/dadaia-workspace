"""Tests for views/memory.py — Markdown-source render (T-MMS-06).

Five survivors, one per real decision:
  1. XSS strip: script/style stripped + meta-header escapes + fixture no-XSS (param).
  2. Path traversal: ../secrets + /etc/passwd + specs-escape list (param).
  3. Constitution allowlist: served + missing 404 + everything-else-404 (param).
  4. Frontmatter meta render: styled header, title, no raw YAML, malformed-no-crash,
     none -> no header.
  5. Render pipeline: mermaid pre + wikilink anchors + GFM table + png/legacy-html
     verbatim + missing 404 + content-type sniffing + specs/memory-subdir rooting,
     driven by the 3 real fixtures (param; folds test_memory_byte_identity.py).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.panel.views.memory import render_memory

pytestmark = pytest.mark.unit

_FIXTURES_DIR = Path(__file__).parent.parent.parent.parent / "fixtures" / "memory"


def _write_md(tmp_path: Path, slug: str, filename: str, content: str) -> Path:
    target_dir = tmp_path / "repos" / slug / "specs" / "memory"
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / filename).write_text(content, encoding="utf-8")
    return tmp_path


def _write_bytes(tmp_path: Path, slug: str, filename: str, data: bytes) -> Path:
    target_dir = tmp_path / "repos" / slug / "specs" / "memory"
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / filename).write_bytes(data)
    return tmp_path


def _mk_constitution_ws(tmp_path: Path) -> str:
    slug = "ctx"
    specs = tmp_path / "repos" / slug / "specs"
    (specs / "memory").mkdir(parents=True)
    (specs / "releases").mkdir()
    (specs / "constitution.md").write_text("# Constitution\n\nThe law of the project.\n")
    (specs / "releases" / "ACTIVE.md").write_text("release: x\n")
    (specs / "memory" / "architecture.md").write_text("# Arch\n")
    return slug


# ---------------------------------------------------------------------------
# 1. XSS strip — script/style stripped + meta-header escapes + fixture no-XSS
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("md", "forbidden_snippets"),
    [
        pytest.param(
            "Text before\n\n<script>alert('xss')</script>\n\nText after\n",
            ["<script>", "alert('xss')"],
            id="raw-script-tag-stripped",
        ),
        pytest.param(
            "Normal text\n\n<style>body { display: none; }</style>\n\nMore text\n",
            ["<style>", "display: none"],
            id="raw-style-tag-stripped",
        ),
        pytest.param(
            '---\ntitle: "<img src=x onerror=alert(1)>"\n---\n\nbody\n',
            ["<img src=x onerror=alert(1)>"],
            id="meta-header-html-escaped",
        ),
    ],
)
def test_xss_sanitiser_strips_unsafe_markup(
    tmp_path: Path, md: str, forbidden_snippets: list[str]
) -> None:
    workspace_root = _write_md(tmp_path, "proj", "evil.md", md)
    view = render_memory(workspace_root)
    status, _, body = view(slug="proj", path="evil.md")

    assert status == 200
    html = body.decode("utf-8")
    # The document chrome carries a trusted theme-prepaint <script>; only the
    # atom-injected content (inside <main>) must never leak unsafe markup.
    main_body = html.split('<main class="memory-doc">', 1)[1]
    for snippet in forbidden_snippets:
        assert snippet not in main_body

    # The 3 real memory fixtures never leak <script>/<style> from the atom body either.
    for fixture_file in ("architecture.md", "tech-stack.md", "panel.md"):
        content = (_FIXTURES_DIR / fixture_file).read_text(encoding="utf-8")
        fixture_ws = _write_md(tmp_path, f"dadaia-workspace-{fixture_file}", fixture_file, content)
        fixture_view = render_memory(fixture_ws)
        fixture_status, _, fixture_body = fixture_view(
            slug=f"dadaia-workspace-{fixture_file}", path=fixture_file
        )
        assert fixture_status == 200
        fixture_html = fixture_body.decode("utf-8")
        fixture_main = fixture_html.split('<main class="memory-doc">', 1)[1]
        assert "<script>" not in fixture_main
        assert "<style>" not in fixture_main


# ---------------------------------------------------------------------------
# 2. Path traversal — ../secrets + /etc/passwd + specs-escape list
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("slug", "escape_path"),
    [
        pytest.param("slug", "../../secrets.txt", id="parent-dir-secrets"),
        pytest.param("slug", "../../../etc/passwd", id="classic-etc-passwd"),
        pytest.param("ctx", "../constitution.md", id="specs-escape-one-up-constitution"),
        pytest.param("ctx", "../releases/ACTIVE.md", id="specs-escape-releases-active"),
        pytest.param("ctx", "releases/ACTIVE.md", id="specs-escape-releases-relative"),
        pytest.param("ctx", "../../specs/constitution.md", id="specs-escape-two-up-specs"),
    ],
)
def test_path_traversal_rejected(tmp_path: Path, slug: str, escape_path: str) -> None:
    _mk_constitution_ws(tmp_path)
    _write_md(tmp_path, "slug", "ok.md", "# OK\n")
    sensitive = tmp_path / "secrets.txt"
    sensitive.write_text("TOP SECRET", encoding="utf-8")

    view = render_memory(tmp_path)
    status, _, body = view(slug=slug, path=escape_path)

    assert status == 404
    assert b"TOP SECRET" not in body


# ---------------------------------------------------------------------------
# 3. Constitution allowlist
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("scenario", ["served", "missing"])
def test_constitution_md_allowlist(tmp_path: Path, scenario: str) -> None:
    if scenario == "served":
        slug = _mk_constitution_ws(tmp_path)
        view = render_memory(tmp_path)
        status, ct, body = view(slug=slug, path="constitution.md")
        assert status == 200
        assert "text/html" in ct
        html = body.decode("utf-8")
        assert "<h1" in html and "Constitution" in html
        assert "# Constitution" not in html
    else:
        slug = "bare"
        (tmp_path / "repos" / slug / "specs" / "memory").mkdir(parents=True)
        view = render_memory(tmp_path)
        status, _, _ = view(slug=slug, path="constitution.md")
        assert status == 404


# ---------------------------------------------------------------------------
# 4. Frontmatter meta render
# ---------------------------------------------------------------------------


def test_frontmatter_meta_render(tmp_path: Path) -> None:
    # Styled header + no raw YAML soup + tags-as-chips.
    md = (
        "---\n"
        "slug: arch\n"
        "title: Architecture Memory\n"
        "tldr: The layered architecture of the system.\n"
        "tags:\n"
        "  - architecture\n"
        "  - layers\n"
        "last_updated: '2026-06-11'\n"
        "---\n\n"
        "## Body heading\n\nContent.\n"
    )
    workspace_root = _write_md(tmp_path, "proj", "arch.md", md)
    view = render_memory(workspace_root)
    status, _, body = view(slug="proj", path="arch.md")
    assert status == 200
    html = body.decode("utf-8")
    assert '<header class="memory-meta">' in html
    assert '<h1 class="memory-meta__title">Architecture Memory</h1>' in html
    assert "The layered architecture of the system." in html
    assert '<li class="memory-meta__chip">architecture</li>' in html
    assert '<li class="memory-meta__chip">layers</li>' in html
    assert "2026-06-11" in html
    main_body = html.split('<main class="memory-doc">', 1)[1]
    assert "slug: arch" not in main_body
    assert "tldr:" not in main_body
    assert "last_updated:" not in main_body
    assert "Body heading" in html

    # Title used as document <title>.
    md_title = "---\ntitle: My Atom\n---\n\nbody\n"
    ws_title = _write_md(tmp_path, "proj2", "a.md", md_title)
    view_title = render_memory(ws_title)
    _, _, body_title = view_title(slug="proj2", path="a.md")
    assert "<title>My Atom</title>" in body_title.decode("utf-8")

    # Malformed YAML does not crash; doc still renders.
    md_bad = "---\ntitle: [unclosed\n---\n\n# Heading\n"
    ws_bad = _write_md(tmp_path, "proj3", "bad.md", md_bad)
    view_bad = render_memory(ws_bad)
    status_bad, _, body_bad = view_bad(slug="proj3", path="bad.md")
    assert status_bad == 200
    assert b"Heading" in body_bad

    # No frontmatter -> no meta header.
    md_none = "# Just a heading\n\nplain body\n"
    ws_none = _write_md(tmp_path, "proj4", "plain.md", md_none)
    view_none = render_memory(ws_none)
    status_none, _, body_none = view_none(slug="proj4", path="plain.md")
    assert status_none == 200
    html_none = body_none.decode("utf-8")
    assert '<main class="memory-doc">' in html_none
    assert "memory-meta" not in html_none
    assert "Just a heading" in html_none


# ---------------------------------------------------------------------------
# 5. Render pipeline — mermaid, wikilinks, GFM table, verbatim assets, 404,
#    content-type sniffing, specs/memory-subdir rooting
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("fixture_file", "expected_slugs", "expect_mermaid", "expect_wikilinks"),
    [
        ("architecture.md", ["tech-stack", "panel"], True, True),
        ("tech-stack.md", [], False, False),
        ("panel.md", ["architecture", "tech-stack"], True, True),
    ],
)
def test_render_pipeline_fixtures(
    tmp_path: Path,
    fixture_file: str,
    expected_slugs: list[str],
    expect_mermaid: bool,
    expect_wikilinks: bool,
) -> None:
    content = (_FIXTURES_DIR / fixture_file).read_text(encoding="utf-8")
    slug_name = fixture_file.replace(".md", "")
    workspace_root = _write_md(tmp_path, "dadaia-workspace", fixture_file, content)

    view = render_memory(workspace_root)
    status, content_type, body = view(slug="dadaia-workspace", path=fixture_file)

    assert status == 200
    assert "text/html" in content_type
    html = body.decode("utf-8")

    if expect_mermaid:
        assert '<pre class="mermaid">' in html, (
            f'{slug_name}: expected <pre class="mermaid"> but not found in rendered HTML'
        )
        assert "language-mermaid" not in html

    if expect_wikilinks:
        assert "<a" in html, f"{slug_name}: expected wikilink <a> anchors"
        assert "/memory-view/" in html
        for slug in expected_slugs:
            assert slug in html, f"{slug_name}: expected [[{slug}]] to appear in rendered HTML"

    # Only run the shared verbatim/mime/subdir/GFM checks once (on the first param row) —
    # they are independent of which fixture drove the parametrization above.
    if fixture_file != "architecture.md":
        return

    # Non-Markdown assets served verbatim; missing .md -> 404; MIME sniffed by extension.
    verbatim_cases: list[tuple[str, bytes | None, int, str | None, bool]] = [
        ("diagram.png", bytes(range(256)) + b"\x89PNG", 200, "image/png", True),
        (
            "old.html",
            b"<!DOCTYPE html><html><body>legacy</body></html>",
            200,
            "text/html; charset=utf-8",
            True,
        ),
        ("style.css", b"\x00", 200, "text/css; charset=utf-8", False),
        ("app.js", b"\x00", 200, "application/javascript; charset=utf-8", False),
        ("photo.jpg", b"\x00", 200, "image/jpeg", False),
        ("icon.svg", b"\x00", 200, "image/svg+xml", False),
        ("data.bin", b"\x00", 200, "application/octet-stream", False),
    ]
    for filename, file_content, expected_status, expected_ct, verbatim in verbatim_cases:
        asset_root = _write_bytes(tmp_path, f"proj-{filename}", filename, file_content)  # type: ignore[arg-type]
        asset_view = render_memory(asset_root)
        asset_status, asset_ct, asset_body = asset_view(slug=f"proj-{filename}", path=filename)
        assert asset_status == expected_status, filename
        assert asset_ct == expected_ct, filename
        if verbatim:
            assert asset_body == file_content, filename

    (tmp_path / "repos" / "missing-md" / "specs" / "memory").mkdir(parents=True)
    missing_view = render_memory(tmp_path)
    missing_status, _, _ = missing_view(slug="missing-md", path="nonexistent.md")
    assert missing_status == 404

    # specs/memory-subdir rooting: a decoy at specs/ must never shadow specs/memory/.
    correct_bytes = b"<!DOCTYPE html><!-- correct: lives under specs/memory/ -->"
    decoy_bytes = b"<!DOCTYPE html><!-- WRONG: decoy lives under specs/ -->"
    memory_dir = tmp_path / "repos" / "dw" / "specs" / "memory"
    memory_dir.mkdir(parents=True)
    (memory_dir / "architecture.html").write_bytes(correct_bytes)
    specs_dir = tmp_path / "repos" / "dw" / "specs"
    (specs_dir / "architecture.html").write_bytes(decoy_bytes)
    subdir_view = render_memory(tmp_path)
    subdir_status, subdir_ct, subdir_body = subdir_view(slug="dw", path="architecture.html")
    assert subdir_status == 200
    assert subdir_ct == "text/html; charset=utf-8"
    assert subdir_body == correct_bytes
    assert subdir_body != decoy_bytes

    # GFM table syntax produces a <table> element.
    table_md = "| A | B |\n|---|---|\n| 1 | 2 |\n"
    table_root = _write_md(tmp_path, "table-proj", "table.md", table_md)
    table_view = render_memory(table_root)
    table_status, _, table_body = table_view(slug="table-proj", path="table.md")
    assert table_status == 200
    table_html = table_body.decode("utf-8")
    assert "<table>" in table_html
    assert "<th>" in table_html or "<thead>" in table_html
