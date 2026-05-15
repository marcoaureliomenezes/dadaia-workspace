"""Unit tests for JsonCourseStore."""

from pathlib import Path

from dadaia_workspace.core.models.course import Course
from dadaia_workspace.infrastructure.json_course_store import JsonCourseStore


def _make_course(slug: str = "py101") -> Course:
    return Course(
        slug=slug,
        name=f"Course {slug}",
        module_number=1,
        module_name="Intro",
        created_at="2026-01-01T00:00:00",
        course_dir=f"/academy/{slug}",
    )


def test_list_all_empty_when_no_file(tmp_path: Path) -> None:
    store = JsonCourseStore(tmp_path)
    assert store.list_all() == []


def test_get_returns_none_when_not_found(tmp_path: Path) -> None:
    store = JsonCourseStore(tmp_path)
    assert store.get("ghost") is None


def test_save_and_get_roundtrip(tmp_path: Path) -> None:
    store = JsonCourseStore(tmp_path)
    course = _make_course("py101")
    store.save(course)
    assert store.get("py101") == course


def test_save_multiple_and_list_all(tmp_path: Path) -> None:
    store = JsonCourseStore(tmp_path)
    store.save(_make_course("a"))
    store.save(_make_course("b"))
    courses = store.list_all()
    assert len(courses) == 2
    assert {c.slug for c in courses} == {"a", "b"}


def test_update_replaces_existing(tmp_path: Path) -> None:
    store = JsonCourseStore(tmp_path)
    original = Course(
        slug="py101",
        name="Old Name",
        module_number=1,
        module_name="Old",
        created_at="2026-01-01T00:00:00",
        course_dir="/old",
    )
    store.save(original)
    updated = Course(
        slug="py101",
        name="New Name",
        module_number=2,
        module_name="New",
        created_at="2026-01-01T00:00:00",
        course_dir="/new",
    )
    store.update(updated)
    fetched = store.get("py101")
    assert fetched is not None
    assert fetched.name == "New Name"
    assert fetched.module_number == 2


def test_delete_removes_course(tmp_path: Path) -> None:
    store = JsonCourseStore(tmp_path)
    store.save(_make_course("todel"))
    store.delete("todel")
    assert store.get("todel") is None


def test_delete_nonexistent_is_noop(tmp_path: Path) -> None:
    store = JsonCourseStore(tmp_path)
    store.delete("ghost")  # must not raise


def test_save_persists_to_disk(tmp_path: Path) -> None:
    store = JsonCourseStore(tmp_path)
    store.save(_make_course("persist"))
    store2 = JsonCourseStore(tmp_path)
    assert store2.get("persist") is not None
