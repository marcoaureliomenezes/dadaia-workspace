"""AcademyService — manage learning courses backed by knowledge_basis modules."""

import importlib.resources
import shutil
from datetime import UTC, datetime
from pathlib import Path

from dadaia_workspace.core.exceptions import ContextAlreadyExistsError, ContextNotFoundError
from dadaia_workspace.core.models.course import Course
from dadaia_workspace.core.protocols.course_store import CourseStore

_KNOWLEDGE_PKG = "dadaia_workspace.features.academy.knowledge_basis"


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _slugify(name: str) -> str:
    return name.lower().replace(" ", "-")


class AcademyService:
    def __init__(
        self,
        course_store: CourseStore,
        workspace_root: Path,
    ) -> None:
        self._store = course_store
        self._workspace_root = workspace_root

    def _academy_dir(self) -> Path:
        return self._workspace_root / ".dadaia" / "academy"

    def list_modules(self) -> list[tuple[int, str]]:
        """Return (number, name) pairs for each knowledge_basis module."""
        pkg_ref = importlib.resources.files(_KNOWLEDGE_PKG)
        modules: list[tuple[int, str]] = []
        for item in pkg_ref.iterdir():
            name = item.name
            if name.startswith("_"):
                continue
            parts = name.split("_", 1)
            if len(parts) == 2 and parts[0].isdigit():
                modules.append((int(parts[0]), name))
        return sorted(modules)

    def list_all(self) -> list[Course]:
        return self._store.list_all()

    def create(self, name: str, module_number: int) -> Course:
        slug = _slugify(name)
        if self._store.get(slug) is not None:
            raise ContextAlreadyExistsError(
                f"Course '{slug}' already exists. Use a different name."
            )
        modules = self.list_modules()
        matched = [(n, m) for n, m in modules if n == module_number]
        if not matched:
            raise ContextNotFoundError(
                f"Module {module_number} not found. Run 'dadaia academy modules' to see available modules."
            )
        module_name = matched[0][1]

        course_dir = self._academy_dir() / slug
        src_pkg = importlib.resources.files(_KNOWLEDGE_PKG) / module_name
        shutil.copytree(str(src_pkg), str(course_dir), dirs_exist_ok=True)

        course = Course(
            slug=slug,
            name=name,
            module_number=module_number,
            module_name=module_name,
            created_at=_now(),
            course_dir=str(course_dir),
        )
        self._store.save(course)
        return course

    def delete(self, slug: str) -> None:
        course = self._store.get(slug)
        if course is None:
            raise ContextNotFoundError(f"Course '{slug}' not found.")
        course_path = Path(course.course_dir)
        if course_path.exists():
            shutil.rmtree(course_path)
        self._store.delete(slug)

    def update(self, slug: str, module_number: int) -> Course:
        course = self._store.get(slug)
        if course is None:
            raise ContextNotFoundError(f"Course '{slug}' not found.")
        modules = self.list_modules()
        matched = [(n, m) for n, m in modules if n == module_number]
        if not matched:
            raise ContextNotFoundError(
                f"Module {module_number} not found. Run 'dadaia academy modules' to see available modules."
            )
        module_name = matched[0][1]

        course_path = Path(course.course_dir)
        if course_path.exists():
            shutil.rmtree(course_path)
        src_pkg = importlib.resources.files(_KNOWLEDGE_PKG) / module_name
        shutil.copytree(str(src_pkg), str(course_path), dirs_exist_ok=True)

        updated = Course(
            slug=course.slug,
            name=course.name,
            module_number=module_number,
            module_name=module_name,
            created_at=course.created_at,
            course_dir=course.course_dir,
        )
        self._store.update(updated)
        return updated
