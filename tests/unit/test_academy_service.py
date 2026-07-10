"""Unit tests for AcademyService."""

from pathlib import Path

import pytest

from dadaia_workspace.core.exceptions import ContextAlreadyExistsError, ContextNotFoundError
from dadaia_workspace.features.academy.service import AcademyService
from tests.fakes import FakeCourseStore


@pytest.fixture()
def workspace_root(tmp_path: Path) -> Path:
    root = tmp_path / "ws"
    (root / ".dadaia" / "academy").mkdir(parents=True)
    return root


@pytest.fixture()
def store() -> FakeCourseStore:
    return FakeCourseStore()


@pytest.fixture()
def service(store: FakeCourseStore, workspace_root: Path) -> AcademyService:
    return AcademyService(course_store=store, workspace_root=workspace_root)


def test_list_modules_create_and_invalid_module_raises(
    service: AcademyService, store: FakeCourseStore
) -> None:
    mods = service.list_modules()
    assert len(mods) > 0
    for number, name in mods:
        assert isinstance(number, int)
        assert isinstance(name, str)
        assert name.startswith(f"{number:02d}_") or name.startswith(f"{number}_")

    number, _ = mods[0]
    course = service.create("My Course", number)
    assert store.get("my-course") is not None
    assert course.slug == "my-course"
    assert course.module_number == number
    assert Path(course.course_dir).exists()

    with pytest.raises(ContextNotFoundError):
        service.create("Bad Course", 999)


def test_duplicate_and_delete_lifecycle(service: AcademyService, store: FakeCourseStore) -> None:
    mods = service.list_modules()
    number, _ = mods[0]
    service.create("My Course", number)

    with pytest.raises(ContextAlreadyExistsError):
        service.create("My Course", number)

    service.delete("my-course")
    assert store.get("my-course") is None

    with pytest.raises(ContextNotFoundError):
        service.delete("ghost")


def test_update_changes_module(service: AcademyService, store: FakeCourseStore) -> None:
    mods = service.list_modules()
    assert len(mods) >= 2, "Need at least 2 modules to test update"
    n1, _ = mods[0]
    n2, name2 = mods[1]
    service.create("My Course", n1)
    updated = service.update("my-course", n2)
    assert updated.module_number == n2
    assert updated.module_name == name2
