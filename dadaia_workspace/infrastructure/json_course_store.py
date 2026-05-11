"""JsonCourseStore — atomic CRUD over academy.json."""

import json
import os
from pathlib import Path

from dadaia_workspace.core.models.course import Course

_VERSION = "1"


def _load(path: Path) -> dict:  # type: ignore[type-arg]
    if not path.exists():
        return {"version": _VERSION, "courses": []}
    with path.open() as f:
        return json.load(f)  # type: ignore[no-any-return]


def _dump(path: Path, data: dict) -> None:  # type: ignore[type-arg]
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    os.replace(tmp, path)


def _to_dict(course: Course) -> dict:  # type: ignore[type-arg]
    return {
        "slug": course.slug,
        "name": course.name,
        "module_number": course.module_number,
        "module_name": course.module_name,
        "created_at": course.created_at,
        "course_dir": course.course_dir,
    }


def _from_dict(d: dict) -> Course:  # type: ignore[type-arg]
    return Course(
        slug=d["slug"],
        name=d["name"],
        module_number=d["module_number"],
        module_name=d["module_name"],
        created_at=d["created_at"],
        course_dir=d["course_dir"],
    )


class JsonCourseStore:
    def __init__(self, academy_dir: Path) -> None:
        self._path = academy_dir / "academy.json"

    def save(self, course: Course) -> None:
        data = _load(self._path)
        data["courses"].append(_to_dict(course))
        _dump(self._path, data)

    def update(self, course: Course) -> None:
        data = _load(self._path)
        data["courses"] = [
            _to_dict(course) if c["slug"] == course.slug else c for c in data["courses"]
        ]
        _dump(self._path, data)

    def get(self, slug: str) -> Course | None:
        data = _load(self._path)
        for c in data["courses"]:
            if c["slug"] == slug:
                return _from_dict(c)
        return None

    def list_all(self) -> list[Course]:
        data = _load(self._path)
        return [_from_dict(c) for c in data["courses"]]

    def delete(self, slug: str) -> None:
        data = _load(self._path)
        data["courses"] = [c for c in data["courses"] if c["slug"] != slug]
        _dump(self._path, data)
