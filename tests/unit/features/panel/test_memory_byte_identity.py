"""Byte-identity canary test for views/memory.py — T-3.5.

SPEC-DOC-008 (memory atomicity invariant): memory HTML files on disk must never
be mutated by the panel. This test is the unit-level enforcement.

NFR-2 (byte-identity): the bytes returned by render_memory() MUST be
byte-for-byte identical to the bytes that Path.read_bytes() returns for the
same file. Any decoding, template interpolation, or byte manipulation inside
views/memory.py will cause this test to fail — which is the intended behaviour.

If this test fails: views/memory.py is mutating bytes it must not touch.
"""

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


# ---------------------------------------------------------------------------
# T-3.5 (a) — byte-identity for a simple HTML file
# ---------------------------------------------------------------------------


def test_serve_memory_byte_identity_html(tmp_path: Path) -> None:
    """SPEC-DOC-008 / NFR-2 canary.

    serve_memory must return bytes byte-identical to Path.read_bytes() of the fixture.
    """
    data = b"<!DOCTYPE html><html><body>Hello</body></html>"
    workspace_root = _build_memory_root(tmp_path, "my-project", "architecture.html", data)

    view = render_memory(workspace_root)
    status, content_type, body = view(slug="my-project", path="architecture.html")

    assert status == 200
    assert content_type == "text/html; charset=utf-8"
    # CANARY: this assertion fails if views/memory.py mutates bytes in any way.
    assert body == data, "serve_memory must return bytes byte-identical to disk"


# ---------------------------------------------------------------------------
# T-3.5 (b) — byte-identity for mixed binary content (non-UTF-8 bytes)
# ---------------------------------------------------------------------------


def test_serve_memory_byte_identity_binary(tmp_path: Path) -> None:
    """Binary content (bytes 0..255) must survive round-trip unchanged.

    SPEC-DOC-008 / NFR-2: no decoding or encoding step is permitted.
    """
    # bytes 0..255 followed by some non-UTF-8 sequences
    data = bytes(range(256)) + b"\xff\xfe\xfd"
    workspace_root = _build_memory_root(tmp_path, "x", "diagram.png", data)

    view = render_memory(workspace_root)
    status, content_type, body = view(slug="x", path="diagram.png")

    assert status == 200
    assert content_type == "image/png"
    assert body == data, "Binary bytes must be returned unchanged (SPEC-DOC-008 / NFR-2)"


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


# ---------------------------------------------------------------------------
# T-3.5 (f) — fixture file from tests/fixtures/memory/architecture.html
# ---------------------------------------------------------------------------


def test_serve_memory_byte_identity_fixture_file(tmp_path: Path) -> None:
    """Use the committed fixture file as additional canary input."""
    fixture_path = (
        Path(__file__).parent.parent.parent.parent / "fixtures" / "memory" / "architecture.html"
    )
    assert fixture_path.exists(), f"Fixture file missing: {fixture_path}"
    data = fixture_path.read_bytes()

    # Copy fixture into tmp workspace layout
    specs_dir = tmp_path / "repos" / "dadaia-workspace" / "specs" / "memory"
    specs_dir.mkdir(parents=True)
    (specs_dir / "architecture.html").write_bytes(data)

    view = render_memory(tmp_path)
    status, content_type, body = view(slug="dadaia-workspace", path="architecture.html")

    assert status == 200
    assert content_type == "text/html; charset=utf-8"
    # CANARY — SPEC-DOC-008 + NFR-2
    assert body == data


# ---------------------------------------------------------------------------
# Regression canary — T-5.3 path-mapping fix
# ---------------------------------------------------------------------------


def test_serve_memory_resolves_under_specs_memory_subdir(tmp_path: Path) -> None:
    """Regression canary: render_memory must resolve files under specs/memory/, not specs/.

    Before the T-5.3 fix, the memory_root was set to repos/<slug>/specs/ instead of
    repos/<slug>/specs/memory/. This meant a request for architecture.html would read
    the decoy file at specs/architecture.html instead of the correct file at
    specs/memory/architecture.html.

    This test proves the fix is in place: the correct file (under specs/memory/) is
    served, and the decoy file (under specs/) is ignored. If anyone reverts memory_root
    back to specs/, the final assertion will fail because the wrong bytes are returned.
    """
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
    # Must match the file under specs/memory/, not the decoy under specs/
    assert body == correct_bytes, (
        "render_memory served the wrong file: memory_root must point to specs/memory/, not specs/"
    )
    assert body != decoy_bytes, (
        "render_memory served the decoy file under specs/ — bug reintroduced"
    )
