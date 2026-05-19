"""Memory view — serves memory HTML and assets verbatim (byte-identical).

SPEC-DOC-008 (memory atomicity) and NFR-2 (byte-identity) compliance:
  - Files are read with Path.read_bytes() and returned without ANY modification.
  - No decoding, no template interpolation, no head injection.
  - The served bytes are ALWAYS byte-identical to the file on disk.

Path traversal guard (OWASP A03):
  - After resolving the absolute path with Path.resolve(), we assert that the
    resolved path is relative to the memory root (repos/<slug>/specs/memory/).
  - Any path that escapes the root returns 404 (no information disclosure).
  - The slug parameter is a URL capture group — malicious values containing
    ".." are rejected by the guard after path resolution.

Architect R3 layer-bypass note:
  This module reads disk files directly (no domain service abstraction) as an
  intentional HTTP-layer concern. The architect's D4.A design explicitly permits
  this for the /memory/ route because the operation is read-only and the path
  guard is the adequate security boundary here.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

# Content-type map keyed by file suffix (lower-case, dot included).
_CONTENT_TYPES: dict[str, str] = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".gif": "image/gif",
    ".ico": "image/x-icon",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
}

_NOT_FOUND: tuple[int, str, bytes] = (
    404,
    "text/plain; charset=utf-8",
    b"Not found.",
)


def render_memory(
    workspace_root: Path,
) -> Callable[..., tuple[int, str, bytes]]:
    """Return a closure that serves memory files byte-identically.

    Parameters
    ----------
    workspace_root:
        Absolute path to the dadaia workspace root directory.
        Memory files are resolved under ``<workspace_root>/repos/<slug>/specs/memory/``.
    """

    def _view(slug: str = "", path: str = "", **_kwargs: object) -> tuple[int, str, bytes]:
        """Serve memory file byte-identically.

        SPEC-DOC-008 + NFR-2 canary: this function MUST NOT alter the bytes it reads.
        test_memory_byte_identity() in test_views_memory.py will fail if it does.
        """
        memory_root = (workspace_root / "repos" / slug / "specs" / "memory").resolve()
        target = (memory_root / path).resolve()

        # Path traversal guard (OWASP A03)
        if not target.is_relative_to(memory_root):
            return _NOT_FOUND

        if not target.exists() or not target.is_file():
            return _NOT_FOUND

        data = target.read_bytes()
        suffix = target.suffix.lower()
        content_type = _CONTENT_TYPES.get(suffix, "application/octet-stream")
        return (200, content_type, data)

    return _view
