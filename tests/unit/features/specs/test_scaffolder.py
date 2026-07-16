"""Unit tests for the SDD scaffolder — scaffold() function and ScaffoldResult."""

from __future__ import annotations

from pathlib import Path

import jinja2
import pytest

from dadaia_workspace.features.specs.scaffolder import (
    _render_template,
    scaffold,
    scaffold_hotfix_release,
)

_REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent
_TEMPLATES_DIR = _REPO_ROOT / "dadaia_workspace" / "public" / "templates"

# Expected canonical outputs (relative to specs_dir).
# Since memory-markdown-source-v1 (T-MMS-10/11), scaffold emits ONLY .md born-markdown
# files for memory atoms. Legacy .yaml stubs, .html files, and placeholder.html were
# retired. The paths below are the complete scaffolded set, including scoped rules,
# an empty generated catalog, and the v0.1.46
# AC-4 per-artifact _archive dirs (FROZEN gate-class landing zone).
_EXPECTED_FILES = [
    "constitution.md",
    "AGENTS.md",
    "memory/AGENTS.md",
    "memory/architecture.md",
    "memory/tech-stack.md",
    "memory/quality-assurance.md",
    "memory/product/index.md",
    "memory/product/catalog.json",
    "releases/ACTIVE.md",
    "backlog/candidates.md",
    "backlog/ideas.md",
    "_archive/releases/.gitkeep",
    "_archive/legacy-features/.gitkeep",
    "assets/.gitkeep",
    "backlog/_archive/.gitkeep",
    "audits/_archive/.gitkeep",
    "bugs/_archive/.gitkeep",
]


def test_scaffold_happy_path_creates_all_artifacts(tmp_path: Path) -> None:
    """A fresh directory scaffold creates all expected files with no errors, including
    the per-artifact _archive dirs (v0.1.46 AC-4)."""
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

    for artifact in ("backlog", "audits", "bugs"):
        gitkeep = specs_dir / artifact / "_archive" / ".gitkeep"
        assert gitkeep in result.created, f"{artifact}/_archive/.gitkeep must be reported created"

    active_content = (specs_dir / "releases" / "ACTIVE.md").read_text(encoding="utf-8")
    assert "release: none" in active_content
    assert "phase: none" in active_content

    # Born-markdown .md stubs exist and start with YAML frontmatter (memory-markdown-source-v1).
    for rel in ("memory/architecture.md", "memory/tech-stack.md", "memory/product/index.md"):
        content = (specs_dir / rel).read_text(encoding="utf-8")
        assert content.startswith("---"), f"{rel} must start with YAML frontmatter"

    assert "specs_pattern_version: 4" in (specs_dir / "constitution.md").read_text(encoding="utf-8")
    assert (specs_dir / "AGENTS.md").read_text(encoding="utf-8") == (
        _TEMPLATES_DIR / "specs-AGENTS.md"
    ).read_text(encoding="utf-8")


def test_scaffold_idempotent_force_and_template_render(tmp_path: Path) -> None:
    """Idempotence (second run all-skipped), --force overwrite (mutated content
    replaced), and the remaining (hotfix) templates render without UndefinedError."""
    specs_dir = tmp_path / "specs"

    first = scaffold(
        specs_dir=specs_dir,
        project_name="idempotent-project",
        force=False,
        templates_dir=_TEMPLATES_DIR,
    )
    assert first.errors == []
    assert len(first.created) == len(_EXPECTED_FILES)

    second = scaffold(
        specs_dir=specs_dir,
        project_name="idempotent-project",
        force=False,
        templates_dir=_TEMPLATES_DIR,
    )
    assert second.errors == []
    assert second.created == []
    assert len(second.skipped) == len(_EXPECTED_FILES)

    # --force overwrites existing (mutated) files with canonical scaffold content.
    arch_path = specs_dir / "memory" / "architecture.md"
    arch_path.write_text("# MUTATED\n", encoding="utf-8")
    third = scaffold(
        specs_dir=specs_dir,
        project_name="new-name",
        force=True,
        templates_dir=_TEMPLATES_DIR,
    )
    assert third.errors == []
    assert third.skipped == []
    assert len(third.created) == len(_EXPECTED_FILES)
    new_content = arch_path.read_text(encoding="utf-8")
    assert "MUTATED" not in new_content
    assert new_content.startswith("---")

    # Remaining (hotfix) template renders without UndefinedError given empty-ish context.
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(_TEMPLATES_DIR)),
        undefined=jinja2.StrictUndefined,
        autoescape=False,
    )
    template = env.get_template("release_hotfix.md.j2")
    try:
        rendered = template.render(
            {
                "version_id": "v0.0.1",
                "patches_release_id": "v0.0.0",
                "severity": "LOW",
                "today": "2026-01-01",
            }
        )
        assert len(rendered) > 10
    except jinja2.UndefinedError as exc:
        pytest.fail(f"release_hotfix.md.j2 raised UndefinedError: {exc}")


# ---- scaffold_hotfix_release ----


def _make_specs_with_patches_release(tmp_path: Path, patches_id: str = "v0.5.0") -> Path:
    specs_dir = tmp_path / "specs"
    patches_dir = specs_dir / "releases" / patches_id
    patches_dir.mkdir(parents=True)
    (patches_dir / "SPEC.md").write_text("# Spec\n\n> **Status:** Aprovado\n", encoding="utf-8")
    (specs_dir / "_archive" / "releases").mkdir(parents=True)
    return specs_dir


def test_hotfix_scaffold_happy_path_and_idempotent(tmp_path: Path) -> None:
    """scaffold_hotfix_release creates SPEC.md + TASKS.md (never PLAN.md — D24 hotfix
    PLAN is optional), renders template variables, and is idempotent without --force."""
    specs_dir = _make_specs_with_patches_release(tmp_path)
    first = scaffold_hotfix_release(
        specs_dir=specs_dir,
        version_id="v0.5.1",
        patches_release_id="v0.5.0",
        severity="HIGH",
        templates_dir=_TEMPLATES_DIR,
    )
    assert first.errors == []
    assert first.skipped == []
    release_dir = specs_dir / "releases" / "v0.5.1"
    assert (release_dir / "SPEC.md").exists()
    assert (release_dir / "TASKS.md").exists()
    assert not (release_dir / "PLAN.md").exists()
    assert len(first.created) == 2  # SPEC.md + TASKS.md
    spec_text = (release_dir / "SPEC.md").read_text(encoding="utf-8")
    assert "v0.5.1" in spec_text
    assert "v0.5.0" in spec_text
    assert "HIGH" in spec_text

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


@pytest.mark.parametrize(
    ("version_id", "patches_release_id", "match"),
    [
        pytest.param("v0.6.0", "v0.5.0", "PATCH=0", id="rejects-patch-zero"),
        pytest.param("my-hotfix-v1", "v0.5.0", "SemVer", id="rejects-invalid-semver"),
        pytest.param(
            "v0.5.1",
            "nonexistent-release-id",
            "does not resolve",
            id="rejects-invalid-patches-release",
        ),
    ],
)
def test_hotfix_scaffold_rejections(
    tmp_path: Path, version_id: str, patches_release_id: str, match: str
) -> None:
    specs_dir = _make_specs_with_patches_release(tmp_path)
    with pytest.raises(ValueError, match=match):
        scaffold_hotfix_release(
            specs_dir=specs_dir,
            version_id=version_id,
            patches_release_id=patches_release_id,
            severity="LOW",
            templates_dir=_TEMPLATES_DIR,
        )


def test_render_template_sandbox_blocks_python_internals(tmp_path: Path) -> None:
    """F-03: the scaffolder uses a SandboxedEnvironment — template access to
    Python internals (dunder attributes) raises rather than evaluating."""
    (tmp_path / "evil.md.j2").write_text("{{ ().__class__.__bases__ }}\n", encoding="utf-8")

    with pytest.raises(jinja2.exceptions.SecurityError):
        _render_template(tmp_path, "evil.md.j2", {})
