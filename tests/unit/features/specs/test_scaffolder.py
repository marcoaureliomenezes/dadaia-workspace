"""Unit tests for the SDD scaffolder — scaffold() function and ScaffoldResult."""

from __future__ import annotations

from pathlib import Path

import jinja2
import pytest

from dadaia_workspace.features.specs.doctor import SpecsDoctor, Severity
from dadaia_workspace.features.specs.scaffolder import ScaffoldResult, scaffold

# Templates directory — canonical location inside the package
# File is at tests/unit/features/specs/test_scaffolder.py
# Repo root is 5 levels up: specs -> features -> unit -> tests -> repo-root
_REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent
_TEMPLATES_DIR = _REPO_ROOT / "dadaia_workspace" / "public" / "templates"

# Expected canonical outputs (relative to specs_dir)
_EXPECTED_FILES = [
    "constitution.md",
    "memory/architecture.html",
    "memory/tech-stack.html",
    "memory/product/index.html",
    "releases/ACTIVE.md",
    "backlog/candidates.md",
    "backlog/ideas.md",
    "_archive/releases/.gitkeep",
    "_archive/legacy-features/.gitkeep",
    "assets/.gitkeep",
]


def _scaffold_fresh(tmp_path: Path, **kwargs: object) -> ScaffoldResult:
    """Helper: scaffold a fresh specs dir under tmp_path."""
    specs_dir = tmp_path / "specs"
    return scaffold(
        specs_dir=specs_dir,
        project_name=kwargs.get("project_name", "test-project"),  # type: ignore[arg-type]
        force=bool(kwargs.get("force", False)),
        templates_dir=_TEMPLATES_DIR,
    )


# ---- test 1: happy path creates all canonical artifacts


def test_scaffold_happy_path_creates_all_artifacts(tmp_path: Path) -> None:
    """A fresh directory scaffold creates all expected files with no errors."""
    specs_dir = tmp_path / "specs"
    result = scaffold(
        specs_dir=specs_dir,
        project_name="my-project",
        force=False,
        templates_dir=_TEMPLATES_DIR,
    )

    assert result.errors == [], f"Unexpected errors: {result.errors}"
    assert result.skipped == [], f"Unexpected skips on fresh dir: {result.skipped}"
    assert len(result.created) == len(_EXPECTED_FILES), (
        f"Expected {len(_EXPECTED_FILES)} created, got {len(result.created)}:\n"
        f"  created: {[str(p) for p in result.created]}"
    )

    for rel in _EXPECTED_FILES:
        full = specs_dir / rel
        assert full.exists(), f"Expected file/dir missing: {rel}"

    # Verify ACTIVE.md content
    active_content = (specs_dir / "releases" / "ACTIVE.md").read_text(encoding="utf-8")
    assert "release: none" in active_content
    assert "phase: none" in active_content

    # Verify project_name appears in rendered HTMLs
    arch_html = (specs_dir / "memory" / "architecture.html").read_text(encoding="utf-8")
    assert "my-project" in arch_html

    tech_html = (specs_dir / "memory" / "tech-stack.html").read_text(encoding="utf-8")
    assert "my-project" in tech_html

    product_html = (specs_dir / "memory" / "product" / "index.html").read_text(encoding="utf-8")
    assert "my-project" in product_html


# ---- test 2: idempotency — second run produces all skipped


def test_scaffold_is_idempotent_without_force(tmp_path: Path) -> None:
    """Running scaffold twice without --force skips all files on the second run."""
    specs_dir = tmp_path / "specs"

    first = scaffold(
        specs_dir=specs_dir,
        project_name="idempotent-project",
        force=False,
        templates_dir=_TEMPLATES_DIR,
    )
    assert first.errors == [], f"First run errors: {first.errors}"
    assert len(first.created) == len(_EXPECTED_FILES)

    second = scaffold(
        specs_dir=specs_dir,
        project_name="idempotent-project",
        force=False,
        templates_dir=_TEMPLATES_DIR,
    )
    assert second.errors == [], f"Second run errors: {second.errors}"
    assert second.created == [], f"Second run should not create files: {second.created}"
    assert len(second.skipped) == len(_EXPECTED_FILES), (
        f"Expected all {len(_EXPECTED_FILES)} files skipped, got {len(second.skipped)}"
    )


# ---- test 3: --force overwrites existing files


def test_scaffold_force_overwrites_files(tmp_path: Path) -> None:
    """With --force, existing files are overwritten with template content."""
    specs_dir = tmp_path / "specs"

    # First scaffold
    first = scaffold(
        specs_dir=specs_dir,
        project_name="original-name",
        force=False,
        templates_dir=_TEMPLATES_DIR,
    )
    assert first.errors == []

    # Mutate a file to detect overwrite
    arch_path = specs_dir / "memory" / "architecture.html"
    arch_path.write_text("<h1>MUTATED</h1>", encoding="utf-8")

    # Second scaffold with --force
    second = scaffold(
        specs_dir=specs_dir,
        project_name="new-name",
        force=True,
        templates_dir=_TEMPLATES_DIR,
    )
    assert second.errors == [], f"Force run errors: {second.errors}"
    assert second.skipped == [], f"Force run should not skip: {second.skipped}"
    assert len(second.created) == len(_EXPECTED_FILES)

    # Verify the mutated file was overwritten
    new_content = arch_path.read_text(encoding="utf-8")
    assert "MUTATED" not in new_content
    assert "new-name" in new_content


# ---- test 4: scaffolded specs passes doctor with 0 errors


def test_scaffolded_specs_passes_doctor(tmp_path: Path) -> None:
    """A freshly scaffolded specs/ directory passes SpecsDoctor with no errors."""
    specs_dir = tmp_path / "specs"
    result = scaffold(
        specs_dir=specs_dir,
        project_name="doctor-test",
        force=False,
        templates_dir=_TEMPLATES_DIR,
    )
    assert result.errors == [], f"Scaffold errors: {result.errors}"

    issues = SpecsDoctor(specs_dir).check()
    errors = [i for i in issues if i.severity == Severity.ERROR]
    assert errors == [], (
        "Scaffolded specs/ should pass doctor with 0 errors. Got:\n"
        + "\n".join(f"  {e.code}: {e.description}" for e in errors)
    )


# ---- test 5: templates render with default dict (no UndefinedError)


def test_templates_render_with_empty_context(tmp_path: Path) -> None:
    """All scaffold templates render without UndefinedError when given empty context."""
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(_TEMPLATES_DIR)),
        undefined=jinja2.StrictUndefined,
        autoescape=False,
    )
    template_names = [
        "memory-architecture.html.j2",
        "memory-tech-stack.html.j2",
        "memory-product-index.html.j2",
    ]
    for name in template_names:
        template = env.get_template(name)
        try:
            rendered = template.render({})
            assert len(rendered) > 100, f"Template {name} rendered suspiciously short output"
        except jinja2.UndefinedError as exc:
            pytest.fail(f"Template {name} raised UndefinedError with empty context: {exc}")
