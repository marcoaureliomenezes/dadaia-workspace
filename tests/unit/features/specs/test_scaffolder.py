"""Unit tests for the SDD scaffolder — scaffold() function and ScaffoldResult."""

from __future__ import annotations

from pathlib import Path

import jinja2
import pytest

from dadaia_workspace.core.specs_version import CANONICAL_SPECS_VERSION
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
#
# v6 canon (T-050-05, FR1, specs_pattern_version 5 -> 6): root specs/_archive/ and
# specs/assets/ retire — neither is a v6 canon root member (TREE-8) — replaced by
# releases/_ideas/ + releases/_archive/ (RELEASE.jsonl-ready) and a new ADRs/ root
# member. Every scaffold README.md retires into its area's AGENTS.md (backlog/,
# bugs/, releases/, audits/ now each carry one, matching root and memory/).
_EXPECTED_FILES = [
    "constitution.md",
    "AGENTS.md",
    "memory/AGENTS.md",
    "memory/ARCHITECTURE.md",
    "memory/TECHSTACK.md",
    "memory/QUALITY.md",
    "memory/product/index.md",
    "memory/product/catalog.json",
    "releases/ACTIVE.md",
    "releases/AGENTS.md",
    "backlog/AGENTS.md",
    "backlog/BACKLOG.md",
    "bugs/AGENTS.md",
    "audits/AGENTS.md",
    "releases/_ideas/.gitkeep",
    "releases/_archive/.gitkeep",
    "ADRs/.gitkeep",
    "backlog/_archive/.gitkeep",
    "audits/_archive/.gitkeep",
    "bugs/_archive/.gitkeep",
]

# T-050-05 (A1.1): the v6 canon root is exactly these 8 members — nothing else is
# emitted directly under specs_dir by a fresh scaffold (retired: root _archive/,
# assets/; new: ADRs/).
_V6_CANON_ROOT = frozenset(
    {"backlog", "bugs", "memory", "releases", "audits", "ADRs", "constitution.md", "AGENTS.md"}
)


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
    for rel in ("memory/ARCHITECTURE.md", "memory/TECHSTACK.md", "memory/product/index.md"):
        content = (specs_dir / rel).read_text(encoding="utf-8")
        assert content.startswith("---"), f"{rel} must start with YAML frontmatter"

    assert f"specs_pattern_version: {CANONICAL_SPECS_VERSION}" in (
        specs_dir / "constitution.md"
    ).read_text(encoding="utf-8")
    assert (specs_dir / "AGENTS.md").read_text(encoding="utf-8") == (
        _TEMPLATES_DIR / "specs-AGENTS.md"
    ).read_text(encoding="utf-8")


def test_scaffold_emits_exact_v6_canon_root_zero_readme_zero_assets(tmp_path: Path) -> None:
    """Intent: CONTRACT — A1.1 (T-050-05).

    A freshly scaffolded workspace emits the v6 canon root exactly (backlog/, bugs/,
    memory/, releases/, audits/, ADRs/, constitution.md, AGENTS.md) — nothing else
    directly under specs_dir — and carries zero README.md and zero assets/ anywhere
    in the scaffolded tree.
    """
    specs_dir = tmp_path / "specs"
    result = scaffold(
        specs_dir=specs_dir,
        project_name="v6-project",
        force=False,
        templates_dir=_TEMPLATES_DIR,
    )
    assert result.errors == [], f"Unexpected errors: {result.errors}"

    root_entries = {p.name for p in specs_dir.iterdir()}
    assert root_entries == _V6_CANON_ROOT, (
        f"specs/ root must be exactly the v6 canon: {sorted(_V6_CANON_ROOT)}, "
        f"got: {sorted(root_entries)}"
    )

    readmes = list(specs_dir.rglob("README.md"))
    assert readmes == [], f"v6 canon emits zero README.md, found: {readmes}"

    assert not (specs_dir / "assets").exists(), "v6 canon emits zero assets/"

    for area in ("backlog", "bugs", "releases", "audits"):
        assert (specs_dir / area / "AGENTS.md").exists(), f"{area}/AGENTS.md must exist"


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
        ``load_document`` with zero errors (an empty ``## ACTIVE``-only skeleton — the
        single top-level section since v0.5.0 A5.2 — is a legitimate empty model, A1.2).

    ``backlog_new``'s own round-trip — a WRITTEN subsection, not just the empty
    skeleton, through ``load_document`` — is already covered by
    ``test_document.test_backlog_new_on_absent_document_creates_section_and_one_subsection``;
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
    arch_path = specs_dir / "memory" / "ARCHITECTURE.md"
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
