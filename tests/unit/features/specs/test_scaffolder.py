"""Unit tests for the SDD scaffolder — scaffold() function and ScaffoldResult."""

from __future__ import annotations

from pathlib import Path

import jinja2
import pytest

from dadaia_workspace.features.specs.scaffolder import (
    ScaffoldResult,
    _render_template,
    scaffold,
    scaffold_hotfix_release,
)

# Templates directory — canonical location inside the package
# File is at tests/unit/features/specs/test_scaffolder.py
# Repo root is 5 levels up: specs -> features -> unit -> tests -> repo-root
_REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent
_TEMPLATES_DIR = _REPO_ROOT / "dadaia_workspace" / "public" / "templates"

# Expected canonical outputs (relative to specs_dir).
# Since memory-markdown-source-v1 (T-MMS-10/11), scaffold emits ONLY .md born-markdown
# files for memory atoms.  Legacy .yaml stubs, .html files, and placeholder.html
# were retired.  The 10 paths below are the complete scaffolded set.
_EXPECTED_FILES = [
    "constitution.md",
    "memory/architecture.md",
    "memory/tech-stack.md",
    "memory/quality-assurance.md",
    "memory/product/index.md",
    "releases/ACTIVE.md",
    "backlog/candidates.md",
    "backlog/ideas.md",
    "_archive/releases/.gitkeep",
    "_archive/legacy-features/.gitkeep",
    "assets/.gitkeep",
    # v0.1.46 AC-4 — per-artifact _archive dirs (FROZEN gate-class landing zone).
    "backlog/_archive/.gitkeep",
    "audits/_archive/.gitkeep",
    "bugs/_archive/.gitkeep",
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

    # Verify born-markdown .md stubs exist and have valid YAML frontmatter.
    # memory-markdown-source-v1: .md is the sole source of truth; legacy .yaml/.html
    # scaffolds were retired (T-MMS-10/11).
    arch_md = (specs_dir / "memory" / "architecture.md").read_text(encoding="utf-8")
    assert arch_md.startswith("---"), "architecture.md must start with YAML frontmatter"

    tech_md = (specs_dir / "memory" / "tech-stack.md").read_text(encoding="utf-8")
    assert tech_md.startswith("---"), "tech-stack.md must start with YAML frontmatter"

    product_index_md = (specs_dir / "memory" / "product" / "index.md").read_text(encoding="utf-8")
    assert product_index_md.startswith("---"), "product/index.md must start with YAML frontmatter"


# ---- v0.1.46 AC-4: scaffolder produces the three per-artifact _archive dirs


def test_scaffold_creates_per_artifact_archive_dirs(tmp_path: Path) -> None:
    """The scaffolder creates specs/{backlog,audits,bugs}/_archive/ (v0.1.46 AC-4).

    These three FROZEN-classed subdirs are the landing zone for terminal/dispositioned
    entries; the bugs->JSONL migration git-mv's source .md into specs/bugs/_archive/ in
    process, so a new/upgraded workspace MUST already have them.
    """
    specs_dir = tmp_path / "specs"
    result = scaffold(
        specs_dir=specs_dir,
        project_name="archive-project",
        force=False,
        templates_dir=_TEMPLATES_DIR,
    )
    assert result.errors == [], f"Unexpected errors: {result.errors}"

    for artifact in ("backlog", "audits", "bugs"):
        gitkeep = specs_dir / artifact / "_archive" / ".gitkeep"
        assert gitkeep.exists(), f"scaffolder must create {artifact}/_archive/.gitkeep"
        assert gitkeep in result.created, f"{artifact}/_archive/.gitkeep must be reported created"


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
    arch_path = specs_dir / "memory" / "architecture.md"
    arch_path.write_text("# MUTATED\n", encoding="utf-8")

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

    # Verify the mutated file was overwritten with the canonical scaffold content.
    # memory-markdown-source-v1: scaffold emits .md only; MUTATED content must be gone
    # and the file must start with frontmatter again.
    new_content = arch_path.read_text(encoding="utf-8")
    assert "MUTATED" not in new_content
    assert new_content.startswith("---"), "architecture.md must start with YAML frontmatter"


# ---- test 4: templates render with default dict (no UndefinedError)


def test_templates_render_with_empty_context(tmp_path: Path) -> None:
    """Existing scaffold templates render without UndefinedError when given empty context.

    memory-markdown-source-v1: the YAML→HTML memory templates were retired (T-MMS-10/11).
    The remaining templates are the hotfix scaffold templates; this test verifies the
    templates directory is accessible and the hotfix templates render cleanly.
    """
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(_TEMPLATES_DIR)),
        undefined=jinja2.StrictUndefined,
        autoescape=False,
    )
    template_names = [
        "release_hotfix.md.j2",
    ]
    for name in template_names:
        template = env.get_template(name)
        try:
            rendered = template.render(
                {
                    "version_id": "v0.0.1",
                    "patches_release_id": "v0.0.0",
                    "severity": "LOW",
                    "today": "2026-01-01",
                }
            )
            assert len(rendered) > 10, f"Template {name} rendered suspiciously short output"
        except jinja2.UndefinedError as exc:
            pytest.fail(f"Template {name} raised UndefinedError: {exc}")


# ---- scaffold_hotfix_release tests


def _make_specs_with_patches_release(tmp_path: Path, patches_id: str = "v0.5.0") -> Path:
    """Create a minimal specs/ tree with a patches release directory."""
    specs_dir = tmp_path / "specs"
    patches_dir = specs_dir / "releases" / patches_id
    patches_dir.mkdir(parents=True)
    (patches_dir / "SPEC.md").write_text("# Spec\n\n> **Status:** Aprovado\n", encoding="utf-8")
    (specs_dir / "_archive" / "releases").mkdir(parents=True)
    return specs_dir


def test_hotfix_scaffold_happy_path(tmp_path: Path) -> None:
    """scaffold_hotfix_release creates SPEC.md and TASKS.md for a valid hotfix version."""
    specs_dir = _make_specs_with_patches_release(tmp_path)
    result = scaffold_hotfix_release(
        specs_dir=specs_dir,
        version_id="v0.5.1",
        patches_release_id="v0.5.0",
        severity="HIGH",
        templates_dir=_TEMPLATES_DIR,
    )
    assert result.errors == [], f"Unexpected errors: {result.errors}"
    assert result.skipped == [], f"Unexpected skips: {result.skipped}"
    release_dir = specs_dir / "releases" / "v0.5.1"
    assert (release_dir / "SPEC.md").exists()
    assert (release_dir / "TASKS.md").exists()
    # PLAN.md must NOT be created (D24 — hotfix PLAN is optional)
    assert not (release_dir / "PLAN.md").exists()
    # Verify template variables rendered
    spec_text = (release_dir / "SPEC.md").read_text(encoding="utf-8")
    assert "v0.5.1" in spec_text
    assert "v0.5.0" in spec_text
    assert "HIGH" in spec_text


def test_hotfix_scaffold_idempotent(tmp_path: Path) -> None:
    """Running scaffold_hotfix_release twice without force skips on the second run."""
    specs_dir = _make_specs_with_patches_release(tmp_path)
    first = scaffold_hotfix_release(
        specs_dir=specs_dir,
        version_id="v0.5.1",
        patches_release_id="v0.5.0",
        severity="LOW",
        templates_dir=_TEMPLATES_DIR,
    )
    assert first.errors == []
    assert len(first.created) == 2  # SPEC.md + TASKS.md

    second = scaffold_hotfix_release(
        specs_dir=specs_dir,
        version_id="v0.5.1",
        patches_release_id="v0.5.0",
        severity="LOW",
        templates_dir=_TEMPLATES_DIR,
    )
    assert second.errors == []
    assert second.created == [], "Second run should not overwrite without --force"
    assert len(second.skipped) == 2


def test_hotfix_scaffold_rejects_patch_zero(tmp_path: Path) -> None:
    """scaffold_hotfix_release raises ValueError when version_id has PATCH=0 (feature release)."""
    specs_dir = _make_specs_with_patches_release(tmp_path)
    with pytest.raises(ValueError, match="PATCH=0"):
        scaffold_hotfix_release(
            specs_dir=specs_dir,
            version_id="v0.6.0",
            patches_release_id="v0.5.0",
            severity="LOW",
            templates_dir=_TEMPLATES_DIR,
        )


def test_hotfix_scaffold_rejects_invalid_semver(tmp_path: Path) -> None:
    """scaffold_hotfix_release raises ValueError when version_id is not valid SemVer."""
    specs_dir = _make_specs_with_patches_release(tmp_path)
    with pytest.raises(ValueError, match="SemVer"):
        scaffold_hotfix_release(
            specs_dir=specs_dir,
            version_id="my-hotfix-v1",
            patches_release_id="v0.5.0",
            severity="LOW",
            templates_dir=_TEMPLATES_DIR,
        )


def test_hotfix_scaffold_rejects_invalid_patches_release(tmp_path: Path) -> None:
    """scaffold_hotfix_release raises ValueError when patches_release_id does not resolve."""
    specs_dir = _make_specs_with_patches_release(tmp_path)
    with pytest.raises(ValueError, match="does not resolve"):
        scaffold_hotfix_release(
            specs_dir=specs_dir,
            version_id="v0.5.1",
            patches_release_id="nonexistent-release-id",
            severity="LOW",
            templates_dir=_TEMPLATES_DIR,
        )


def test_render_template_sandbox_blocks_python_internals(tmp_path: Path) -> None:
    """F-03: the scaffolder uses a SandboxedEnvironment — template access to
    Python internals (dunder attributes) raises rather than evaluating."""
    (tmp_path / "evil.md.j2").write_text("{{ ().__class__.__bases__ }}\n", encoding="utf-8")

    with pytest.raises(jinja2.exceptions.SecurityError):
        _render_template(tmp_path, "evil.md.j2", {})


def test_render_template_renders_normal_context(tmp_path: Path) -> None:
    """Normal rendering still works under the sandbox."""
    (tmp_path / "ok.md.j2").write_text("# {{ project_name }}\n", encoding="utf-8")

    # Jinja strips the single trailing template newline by default.
    assert _render_template(tmp_path, "ok.md.j2", {"project_name": "demo"}) == "# demo"
