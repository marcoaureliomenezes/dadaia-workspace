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


# ---------------------------------------------------------------------------
# Denial matrix — unknown/malformed-but-in-bounds + traversal negatives (OWASP A03)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("module", "lesson"),
    [
        pytest.param("99_does_not_exist", "README.md", id="unknown-module"),
        pytest.param(_REAL_MODULE, "nonexistent_lesson.md", id="unknown-lesson"),
        pytest.param(_REAL_MODULE, "README", id="non-md-extension-no-suffix"),
        pytest.param(_REAL_MODULE, "service.py", id="non-md-extension-py"),
        pytest.param(_REAL_MODULE, f"{_SIBLING_MODULE}.md", id="directory-target-not-file"),
        pytest.param("..", "README.md", id="module-dotdot"),
        pytest.param("../..", "README.md", id="module-dotdot-dotdot"),
        pytest.param(f"../{_SIBLING_MODULE}", "README.md", id="module-escape-sibling"),
        pytest.param(f"{_REAL_MODULE}/..", "README.md", id="module-embedded-dotdot"),
        pytest.param("07_codex/../..", "README.md", id="module-embedded-double-dotdot"),
        pytest.param("/etc", "README.md", id="module-absolute-path"),
        pytest.param("", "README.md", id="module-empty"),
        pytest.param(".", "README.md", id="module-dot"),
        pytest.param(
            _REAL_MODULE,
            f"../{_SIBLING_MODULE}/README.md",
            id="lesson-escape-sibling",
        ),
        pytest.param(_REAL_MODULE, "../../setup.py.md", id="lesson-escape-double-dotdot"),
        pytest.param(_REAL_MODULE, "subdir/nested.md", id="lesson-embedded-subdir"),
        pytest.param(_REAL_MODULE, "/etc/passwd.md", id="lesson-absolute-path"),
        pytest.param(_REAL_MODULE, "..\\windows\\evil.md", id="lesson-backslash-escape"),
        pytest.param(_REAL_MODULE, "..README.md", id="lesson-dotdot-prefix-single-segment"),
        pytest.param(_REAL_MODULE, "../README.md", id="lesson-url-decoded-slash"),
        pytest.param("../07_codex", "README.md", id="module-url-decoded-slash"),
    ],
)
def test_read_lesson_denies_out_of_bounds(module: str, lesson: str) -> None:
    """Every unknown/malformed/traversal (module, lesson) pair returns None."""
    svc = _make_service()
    assert svc.read_lesson(module, lesson) is None


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
