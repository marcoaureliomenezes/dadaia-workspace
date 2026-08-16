"""Unit tests for the SDD scaffolder — scaffold() function and ScaffoldResult."""

from __future__ import annotations

from pathlib import Path

import jinja2
import pytest

from dadaia_workspace.features.backlog import document
from dadaia_workspace.features.backlog.document import load_document
from dadaia_workspace.features.specs import scaffolder
from dadaia_workspace.features.specs.scaffolder import (
    _render_template,
    scaffold,
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
    "backlog/BACKLOG.md",
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


def test_scaffolded_backlog_skeleton_pins_writer_and_round_trips_load_document(
    tmp_path: Path,
) -> None:
    """LOW (code-reviewer, v0.12.0 pre-PR): the BACKLOG.md grammar is written by THREE
    modules (``scaffolder._BACKLOG_STUB`` for a fresh ``specs init``,
    ``document._BACKLOG_DOCUMENT_SKELETON`` for ``backlog new`` on an absent document
    — moved here from ``new_artifacts`` at SPEC v0.4.2 FR1/GRILL D1 — and the live
    subsection-append template) and parsed by a FOURTH, ``document.load_document`` —
    with no test pinning their agreement. Pin two things:

    (a) the two from-scratch skeleton literals stay byte-identical (a grammar change in
        one writer can no longer silently desync the other), and
    (b) a fresh ``specs init`` scaffold's ``BACKLOG.md`` round-trips through
        ``load_document`` with zero errors (an empty ACTIVE/LEDGER skeleton is a
        legitimate empty model, A1.2).

    ``backlog_new``'s own round-trip — a WRITTEN subsection, not just the empty
    skeleton, through ``load_document`` — is already covered by
    ``test_document.test_backlog_new_on_absent_document_creates_both_sections_and_one_subsection``;
    this test extends the pin to the scaffolder producer rather than duplicating that
    coverage."""
    assert scaffolder._BACKLOG_STUB == document._BACKLOG_DOCUMENT_SKELETON, (
        "the scaffolder's fresh-tree BACKLOG.md skeleton must stay byte-identical to "
        "backlog_new's from-scratch skeleton — both are parsed by the SAME grammar "
        "document.load_document owns, and a drift here would desync them silently"
    )

    specs_dir = tmp_path / "specs"
    result = scaffold(
        specs_dir=specs_dir,
        project_name="pin-project",
        force=False,
        templates_dir=_TEMPLATES_DIR,
    )
    assert result.errors == []

    doc = load_document(specs_dir / "backlog")
    assert doc.errors == ()
    assert doc.active == ()
    assert doc.ledger == ()


def test_scaffold_idempotent_force_and_template_render(tmp_path: Path) -> None:
    """Idempotence (second run all-skipped) and --force overwrite (mutated content
    replaced)."""
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


def test_render_template_sandbox_blocks_python_internals(tmp_path: Path) -> None:
    """F-03: the scaffolder uses a SandboxedEnvironment — template access to
    Python internals (dunder attributes) raises rather than evaluating."""
    (tmp_path / "evil.md.j2").write_text("{{ ().__class__.__bases__ }}\n", encoding="utf-8")

    with pytest.raises(jinja2.exceptions.SecurityError):
        _render_template(tmp_path, "evil.md.j2", {})
