"""AcademyService — manage learning courses backed by knowledge_basis modules."""

import importlib.resources
import shutil
from datetime import UTC, datetime
from pathlib import Path

from dadaia_workspace.core.exceptions import ContextAlreadyExistsError, ContextNotFoundError
from dadaia_workspace.core.models.course import Course
from dadaia_workspace.core.protocols.course_store import CourseStore

_KNOWLEDGE_PKG = "dadaia_workspace.features.academy.knowledge_basis"

# Real filesystem root of the shipped course content. ``importlib.resources.files``
# returns a MultiplexedPath that is not a concrete ``Path`` (so it cannot be used as a
# path-traversal anchor); the package directory lives in the source tree next to this
# module, so we resolve it directly for the read-only lesson-serving guard.
_KNOWLEDGE_ROOT = (Path(__file__).parent / "knowledge_basis").resolve()


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _slugify(name: str) -> str:
    return name.lower().replace(" ", "-")


def _humanize(slug_part: str) -> str:
    """Turn a ``NN_some_name`` segment into a human title ``Some Name``.

    Strips the leading ``NN_`` numeric prefix and a trailing ``.md`` suffix, then
    title-cases the underscore-separated words. Used to derive display titles for
    modules and lessons when no Markdown H1 is available.
    """
    stem = slug_part[:-3] if slug_part.endswith(".md") else slug_part
    parts = stem.split("_", 1)
    body = parts[1] if len(parts) == 2 and parts[0].isdigit() else stem
    return body.replace("_", " ").strip().title()


def _first_heading(text: str) -> str | None:
    """Return the first Markdown ``# H1`` heading text, or None if absent."""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return None


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

    def list_module_catalog(self) -> list[dict[str, object]]:
        """Return the shipped knowledge_basis catalog: modules with their lessons.

        This is the browse source for the panel Academy tab. Unlike
        :meth:`list_all` (user-created course copies in ``.dadaia/academy``), this
        enumerates the canonical course content shipped with the package.

        Each module dict:
          ``module`` (str, directory name, e.g. ``"07_codex"``),
          ``module_number`` (int),
          ``title`` (str, README H1 or humanized name),
          ``lesson_count`` (int),
          ``lessons`` (list of {``lesson``, ``title``}).

        Lessons are the numbered ``NN_*.md`` files plus README/EXERCISES/EXAMPLE/
        REFERENCES, sorted so numbered lessons come first in numeric order.
        """
        catalog: list[dict[str, object]] = []
        for number, module_name in self.list_modules():
            module_dir = _KNOWLEDGE_ROOT / module_name
            title = self._module_title(module_dir, module_name)
            lessons = self._module_lessons(module_dir)
            catalog.append(
                {
                    "module": module_name,
                    "module_number": number,
                    "title": title,
                    "lesson_count": len(lessons),
                    "lessons": lessons,
                }
            )
        return catalog

    def _module_title(self, module_dir: Path, module_name: str) -> str:
        readme = module_dir / "README.md"
        if readme.is_file():
            heading = _first_heading(readme.read_text(encoding="utf-8"))
            if heading:
                return heading
        return _humanize(module_name)

    @staticmethod
    def _lesson_sort_key(name: str) -> tuple[int, int, str]:
        """Sort numbered lessons first (by number), then named files alphabetically."""
        prefix = name.split("_", 1)[0]
        if prefix.isdigit():
            return (0, int(prefix), name)
        return (1, 0, name)

    def _module_lessons(self, module_dir: Path) -> list[dict[str, str]]:
        files = [
            f.name
            for f in module_dir.iterdir()
            if f.is_file() and f.name.endswith(".md") and not f.name.startswith("_")
        ]
        files.sort(key=self._lesson_sort_key)
        lessons: list[dict[str, str]] = []
        for fname in files:
            heading = _first_heading((module_dir / fname).read_text(encoding="utf-8"))
            lessons.append({"lesson": fname, "title": heading or _humanize(fname)})
        return lessons

    def read_lesson(self, module: str, lesson: str) -> str | None:
        """Return the raw Markdown of a lesson, or None if not found / out of bounds.

        Read-only and path-traversal-guarded (OWASP A03): the resolved target must be
        a regular ``.md`` file located directly inside ``knowledge_basis/<module>/``
        under :data:`_KNOWLEDGE_ROOT`. Any path that escapes the root, names a
        non-``.md`` file, or points at a directory returns None (caller maps to 404,
        no information disclosure).
        """
        if not lesson.endswith(".md"):
            return None
        target = (_KNOWLEDGE_ROOT / module / lesson).resolve()
        if not target.is_relative_to(_KNOWLEDGE_ROOT):
            return None
        # The lesson must sit exactly one level below the root (root/<module>/<file>),
        # never deeper, so a crafted ``module`` cannot reach into sub-packages.
        if target.parent.parent != _KNOWLEDGE_ROOT:
            return None
        if not target.is_file():
            return None
        return target.read_text(encoding="utf-8")

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
