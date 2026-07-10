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


def test_save_roundtrip_multiple_and_update(tmp_path: Path) -> None:
    store = JsonCourseStore(tmp_path)
    assert store.list_all() == []
    assert store.get("ghost") is None

    course = _make_course("py101")
    store.save(course)
    assert store.get("py101") == course

    store.save(_make_course("a"))
    courses = store.list_all()
    assert {c.slug for c in courses} == {"py101", "a"}

    original = Course(
        slug="upd",
        name="Old Name",
        module_number=1,
        module_name="Old",
        created_at="2026-01-01T00:00:00",
        course_dir="/old",
    )
    store.save(original)
    updated = Course(
        slug="upd",
        name="New Name",
        module_number=2,
        module_name="New",
        created_at="2026-01-01T00:00:00",
        course_dir="/new",
    )
    store.update(updated)
    fetched = store.get("upd")
    assert fetched is not None
    assert fetched.name == "New Name"
    assert fetched.module_number == 2


def test_delete_removes_noop_on_missing_and_persists_to_disk(tmp_path: Path) -> None:
    store = JsonCourseStore(tmp_path)
    store.save(_make_course("todel"))
    store.delete("todel")
    assert store.get("todel") is None

    store.delete("ghost")  # must not raise

    store.save(_make_course("persist"))
    store2 = JsonCourseStore(tmp_path)
    assert store2.get("persist") is not None
