"""Tests for views/memory.py path guard and non-Markdown asset routing."""

from pathlib import Path

import pytest

from dadaia_workspace.features.panel.views.memory import render_memory

# ---------------------------------------------------------------------------
# Fixtures helpers
# ---------------------------------------------------------------------------


def _build_memory_root(tmp_path: Path, slug: str, filename: str, data: bytes) -> Path:
    """Create <tmp_path>/repos/<slug>/specs/memory/<filename> and return tmp_path."""
    target_dir = tmp_path / "repos" / slug / "specs" / "memory"
    target_dir.mkdir(parents=True)
    (target_dir / filename).write_bytes(data)
    return tmp_path


def test_serve_memory_html_asset_200(tmp_path: Path) -> None:
    """Legacy .html assets remain readable as non-Markdown fallback assets."""
    data = b"<!DOCTYPE html><html><body>Hello</body></html>"
    workspace_root = _build_memory_root(tmp_path, "my-project", "architecture.html", data)

    view = render_memory(workspace_root)
    status, content_type, _ = view(slug="my-project", path="architecture.html")

    assert status == 200
    assert content_type == "text/html; charset=utf-8"


# ---------------------------------------------------------------------------
# T-3.5 (c) — path traversal rejected with 404
# ---------------------------------------------------------------------------


def test_serve_memory_traversal_rejected(tmp_path: Path) -> None:
    """Path traversal (../../etc/passwd) must return 404, not leak content."""
    # Create a benign file in the specs dir so the workspace root exists.
    workspace_root = _build_memory_root(tmp_path, "slug", "ok.html", b"ok")

    # Create a sensitive file outside the memory root
    sensitive = tmp_path / "secrets.txt"
    sensitive.write_bytes(b"TOP SECRET")

    view = render_memory(workspace_root)

    # Attempt traversal to escape the memory root
    status, _, body = view(slug="slug", path="../../secrets.txt")
    assert status == 404
    assert b"TOP SECRET" not in body


def test_serve_memory_traversal_etc_passwd(tmp_path: Path) -> None:
    """Classic ../../../etc/passwd traversal must return 404."""
    workspace_root = _build_memory_root(tmp_path, "slug", "ok.html", b"ok")

    view = render_memory(workspace_root)
    status, _, body = view(slug="slug", path="../../../etc/passwd")
    assert status == 404


# ---------------------------------------------------------------------------
# T-3.5 (d) — non-existent file returns 404
# ---------------------------------------------------------------------------


def test_serve_memory_missing_file_returns_404(tmp_path: Path) -> None:
    """A request for a file that does not exist must return 404."""
    # Create the specs/memory dir but not the file
    specs_dir = tmp_path / "repos" / "proj" / "specs" / "memory"
    specs_dir.mkdir(parents=True)

    view = render_memory(tmp_path)
    status, _, _ = view(slug="proj", path="nonexistent.html")
    assert status == 404


# ---------------------------------------------------------------------------
# T-3.5 (e) — content-type sniffing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("filename", "expected_ct"),
    [
        ("file.html", "text/html; charset=utf-8"),
        ("style.css", "text/css; charset=utf-8"),
        ("app.js", "application/javascript; charset=utf-8"),
        ("image.png", "image/png"),
        ("photo.jpg", "image/jpeg"),
        ("icon.svg", "image/svg+xml"),
        ("data.bin", "application/octet-stream"),
    ],
)
def test_serve_memory_content_type_sniffing(
    tmp_path: Path, filename: str, expected_ct: str
) -> None:
    """Content-type is sniffed from file extension (no OS MIME database)."""
    workspace_root = _build_memory_root(tmp_path, "proj", filename, b"\x00")

    view = render_memory(workspace_root)
    _, content_type, _ = view(slug="proj", path=filename)
    assert content_type == expected_ct


def test_serve_memory_resolves_under_specs_memory_subdir(tmp_path: Path) -> None:
    """Memory asset lookup is rooted under specs/memory, not specs."""
    correct_bytes = b"<!DOCTYPE html><!-- correct: lives under specs/memory/ -->"
    decoy_bytes = b"<!DOCTYPE html><!-- WRONG: decoy lives under specs/ -->"

    # Correct file: repos/dw/specs/memory/architecture.html
    memory_dir = tmp_path / "repos" / "dw" / "specs" / "memory"
    memory_dir.mkdir(parents=True)
    (memory_dir / "architecture.html").write_bytes(correct_bytes)

    # Decoy file: repos/dw/specs/architecture.html (wrong path — would be served before fix)
    specs_dir = tmp_path / "repos" / "dw" / "specs"
    (specs_dir / "architecture.html").write_bytes(decoy_bytes)

    view = render_memory(tmp_path)
    status, content_type, body = view(slug="dw", path="architecture.html")

    assert status == 200
    assert content_type == "text/html; charset=utf-8"
    assert body == correct_bytes
    assert body != decoy_bytes
