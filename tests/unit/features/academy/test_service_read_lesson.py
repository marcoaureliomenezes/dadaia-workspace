"""Unit tests for AcademyService.read_lesson — lesson read + traversal guard (T-013-07).

``read_lesson(module, lesson)`` is the read-only, path-traversal-guarded source for
``GET /academy/<module>/<lesson>``. The security contract (OWASP A03) is: the resolved
target must be a regular ``.md`` file located **exactly one level below** the shipped
``knowledge_basis`` root (``root/<module>/<file>``). Anything else — unknown module /
lesson, a non-``.md`` name, a directory, or any path component that escapes the module
(``..``, an embedded separator, an absolute-path injection, a sibling-module reach) —
returns ``None`` with no information disclosure.

These tests run against the **packaged** knowledge_basis root (no fake root injection is
exposed by the service), exercising the real resolve + ``is_relative_to`` guard.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.features.academy.service import AcademyService

# A module/lesson pair that genuinely ships in knowledge_basis (used for the happy path
# and as the *anchor* for sibling-escape negatives).
_REAL_MODULE = "07_codex"
_REAL_LESSON = "README.md"
_SIBLING_MODULE = "06_claude_code"


class _FakeCourseStore:
    """No-op CourseStore — read_lesson never touches the store."""

    def save(self, course: Any) -> None: ...
    def update(self, course: Any) -> None: ...
    def get(self, slug: str) -> Any | None:
        return None

    def list_all(self) -> list[Any]:
        return []

    def delete(self, slug: str) -> None: ...


def _make_service() -> AcademyService:
    return AcademyService(_FakeCourseStore(), Path("/workspace"))


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_read_lesson_happy_path_returns_markdown() -> None:
    """A real module/lesson returns the raw Markdown body."""
    svc = _make_service()
    source = svc.read_lesson(_REAL_MODULE, _REAL_LESSON)
    assert source is not None
    # README.md ships a top-level H1 — assert a real content fragment, not just truthiness.
    assert source.lstrip().startswith("#")


def test_read_lesson_numbered_lesson_returns_markdown() -> None:
    """A numbered ``NN_*.md`` lesson in a real module resolves and reads."""
    svc = _make_service()
    source = svc.read_lesson(_REAL_MODULE, "01_codex_mental_model.md")
    assert source is not None
    assert len(source) > 0


# ---------------------------------------------------------------------------
# Unknown / malformed but in-bounds
# ---------------------------------------------------------------------------


def test_read_lesson_unknown_module_returns_none() -> None:
    svc = _make_service()
    assert svc.read_lesson("99_does_not_exist", "README.md") is None


def test_read_lesson_unknown_lesson_returns_none() -> None:
    svc = _make_service()
    assert svc.read_lesson(_REAL_MODULE, "nonexistent_lesson.md") is None


def test_read_lesson_non_md_extension_returns_none() -> None:
    """A non-``.md`` name is rejected before any filesystem access."""
    svc = _make_service()
    assert svc.read_lesson(_REAL_MODULE, "README") is None
    assert svc.read_lesson(_REAL_MODULE, "service.py") is None


def test_read_lesson_directory_target_returns_none() -> None:
    """A name that resolves to a directory (not a regular file) returns None."""
    svc = _make_service()
    # ``07_codex`` is a directory; appending ``.md`` keeps it non-existent-as-file.
    assert svc.read_lesson(_REAL_MODULE, f"{_SIBLING_MODULE}.md") is None


# ---------------------------------------------------------------------------
# Traversal negatives (OWASP A03)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "module",
    [
        "..",
        "../..",
        f"../{_SIBLING_MODULE}",
        f"{_REAL_MODULE}/..",
        "07_codex/../..",
        "/etc",
        "",
        ".",
    ],
)
def test_read_lesson_traversal_in_module_returns_none(module: str) -> None:
    """Any ``module`` carrying a separator / ``..`` / absolute prefix is denied."""
    svc = _make_service()
    assert svc.read_lesson(module, "README.md") is None


@pytest.mark.parametrize(
    "lesson",
    [
        # Sibling-module reach: was a guard bypass (parent.parent == root yet escapes
        # the requested module). Closed by the single-segment component check.
        f"../{_SIBLING_MODULE}/README.md",
        "../../setup.py.md",
        "subdir/nested.md",
        "/etc/passwd.md",
        "..\\windows\\evil.md",
        "..README.md",  # this one IS a single segment and must still 404 (no such file)
    ],
)
def test_read_lesson_traversal_in_lesson_returns_none(lesson: str) -> None:
    """A crafted ``lesson`` cannot escape its module or name a non-existent file."""
    svc = _make_service()
    assert svc.read_lesson(_REAL_MODULE, lesson) is None


def test_read_lesson_sibling_escape_does_not_leak_sibling_content() -> None:
    """Regression: the sibling-module escape must NOT return the sibling's content.

    Before the fix, ``read_lesson('07_codex', '../06_claude_code/README.md')`` resolved
    to the sibling module's README (parent.parent == root, is_relative_to True) and
    leaked it. The fixed guard returns None.
    """
    svc = _make_service()
    leaked = svc.read_lesson(_REAL_MODULE, f"../{_SIBLING_MODULE}/README.md")
    assert leaked is None
    # Sanity: the sibling README does exist and IS readable via its proper coordinates,
    # proving the negative above is the guard denying escape, not a missing file.
    legit = svc.read_lesson(_SIBLING_MODULE, "README.md")
    assert legit is not None


def test_read_lesson_url_decoded_slash_segment_returns_none() -> None:
    """A ``..%2f``-style segment, once URL-decoded by the handler into ``../``, is denied.

    The handler passes the decoded segment to ``read_lesson``; the embedded separator
    makes it a multi-component path which the single-segment guard rejects.
    """
    svc = _make_service()
    assert svc.read_lesson(_REAL_MODULE, "../README.md") is None
    assert svc.read_lesson("../07_codex", "README.md") is None
