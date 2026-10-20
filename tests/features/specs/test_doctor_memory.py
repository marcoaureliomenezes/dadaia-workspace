"""Unit tests for the memory validator's LINT-1 mapping.

LINT-1 imports ``features.specs.memory_lint`` directly. These tests exercise
``check_lint1_memory_atoms`` against REAL memory-atom fixtures written under ``tmp_path``,
proving the severity mapping end to end through the real ``memory_lint`` implementation —
never a faked subprocess result.

MEM-DRIFT-1 compares the features package-map diagram in ARCHITECTURE.md with the live
``dadaia_workspace/features`` packages.

The live-package introspection is monkeypatched in the table; one smoke test runs it for
real.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.specs.doctor_memory import MemoryValidator
from dadaia_workspace.features.specs.doctor_types import finding_path
from tests.helpers.oslib import write_text

_VALID_FRONTMATTER = """---
slug: {slug}
title: "Fixture atom"
tldr: "a valid atom for LINT-1 fixture purposes"
summary: "a valid atom for LINT-1 fixture purposes, used across doctor_memory tests"
tags: ["fixture"]
sources: ["specs/**"]
---
"""


def _make_specs_with_memory(tmp_path: Path) -> Path:
    specs = tmp_path / "specs"
    (specs / "memory" / "product" / "a").mkdir(parents=True)
    return specs


def test_lint1_clean_atom_produces_no_issues(tmp_path: Path) -> None:
    specs = _make_specs_with_memory(tmp_path)
    write_text(
        specs / "memory" / "product" / "a" / "architecture.md",
        _VALID_FRONTMATTER.format(slug="architecture") + "\n## Purpose\n\nclean atom\n",
    )

    issues = MemoryValidator(specs).check_lint1_memory_atoms()

    assert issues == []


def test_lint1_forbidden_heading_maps_to_error(tmp_path: Path) -> None:
    specs = _make_specs_with_memory(tmp_path)
    write_text(
        specs / "memory" / "product" / "a" / "architecture.md",
        _VALID_FRONTMATTER.format(slug="architecture") + "\n## Changelog\n\nnot allowed\n",
    )

    issues = MemoryValidator(specs).check_lint1_memory_atoms()

    assert len(issues) == 1
    assert issues[0].code == "LINT-1"
    assert issues[0].error
    assert "Forbidden heading" in issues[0].message
    assert "Changelog" in issues[0].message


def test_lint1_unknown_heading_produces_no_issue(tmp_path: Path) -> None:
    """A heading nobody has ever seen before is neither an error nor a warning at the doctor
    mapping layer."""
    specs = _make_specs_with_memory(tmp_path)
    write_text(
        specs / "memory" / "product" / "a" / "architecture.md",
        _VALID_FRONTMATTER.format(slug="architecture")
        + "\n## Some Brand New Never Before Seen Heading\n\ncontent\n",
    )

    issues = MemoryValidator(specs).check_lint1_memory_atoms()

    assert issues == []


def test_lint1_error_atom_and_clean_atom_coexist_only_the_error_surfaces(tmp_path: Path) -> None:
    """Multiple atoms aggregate correctly: a genuine forbidden-heading ERROR in one
    atom surfaces, while a sibling atom with an ordinary (never-curated) heading
    contributes nothing — exactly one issue, not silently swallowed or duplicated."""
    specs = _make_specs_with_memory(tmp_path)
    write_text(
        specs / "memory" / "product" / "a" / "architecture.md",
        _VALID_FRONTMATTER.format(slug="architecture") + "\n## History\n\nforbidden\n",
    )
    write_text(
        specs / "memory" / "product" / "a" / "tech-stack.md",
        _VALID_FRONTMATTER.format(slug="tech-stack") + "\n## Some Other Heading\n\nx\n",
    )

    issues = MemoryValidator(specs).check_lint1_memory_atoms()

    assert len(issues) == 1
    assert issues[0].error


def test_lint1_no_memory_dir_is_a_noop(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    specs.mkdir()

    issues = MemoryValidator(specs).check_lint1_memory_atoms()

    assert issues == []


def test_lint1_empty_memory_dir_is_a_noop(tmp_path: Path) -> None:
    specs = _make_specs_with_memory(tmp_path)

    issues = MemoryValidator(specs).check_lint1_memory_atoms()

    assert issues == []


def test_lint1_emits_one_single_line_issue_per_atom_error(tmp_path: Path) -> None:
    """The doctor prints one `<CODE> <verdict> <message>` line per finding, so every lint
    error is its own issue naming its own atom — never a multi-line block of
    `  [path] ERROR:` lines."""
    specs = _make_specs_with_memory(tmp_path)
    architecture = specs / "memory" / "product" / "a" / "architecture.md"
    write_text(
        architecture,
        _VALID_FRONTMATTER.format(slug="architecture") + "\n## History\n\nx\n## Changelog\n",
    )
    quality = specs / "memory" / "product" / "a" / "quality.md"
    write_text(quality, _VALID_FRONTMATTER.format(slug="quality") + "\n## History\n\nx\n")

    issues = MemoryValidator(specs).check_lint1_memory_atoms()

    assert [(issue.code, finding_path(issue)) for issue in issues] == [
        ("LINT-1", str(architecture)),
        ("LINT-1", str(architecture)),
        ("LINT-1", str(quality)),
    ]
    assert all("\n" not in issue.message for issue in issues)


_HEADING = "### `dadaia_workspace/features` — package map ({n} packages)"


def _architecture_md(pkgs: tuple[str, ...]) -> str:
    return (
        "# Architecture\n\n## Part 2 — Implementation\n\n"
        f"{_HEADING.format(n=len(pkgs))}\n\n```mermaid\nflowchart TB\n"
        '    subgraph features["dadaia_workspace/features"]\n'
        f'      pkgs["{" · ".join(pkgs)}"]\n'
        "    end\n```\n\n### next section\n\nunrelated\n"
    )


@pytest.mark.parametrize(
    ("architecture", "live", "needle"),
    [
        pytest.param(
            _architecture_md(("panel", "spec_artifacts")),
            {"panel"},
            "spec_artifacts",
            id="stale-node",
        ),
        pytest.param(
            _architecture_md(("panel",)), {"panel", "repos"}, "repos", id="missing-live-package"
        ),
        pytest.param(_architecture_md(("panel", "repos")), {"panel", "repos"}, None, id="matching"),
        pytest.param(
            "# Architecture\n\nnothing relevant.\n",
            {"panel"},
            None,
            id="consumer-no-heading-silent",
        ),
        pytest.param(None, {"panel"}, None, id="no-architecture-md"),
    ],
)
def test_mem_drift1_table(
    tmp_path: Path,
    architecture: str | None,
    live: set[str],
    needle: str | None,
) -> None:
    specs = tmp_path / "specs"
    (specs / "memory").mkdir(parents=True)
    if architecture is not None:
        write_text(specs / "memory" / "ARCHITECTURE.md", architecture)
    for pkg in live:
        (tmp_path / "dadaia_workspace" / "features" / pkg).mkdir(parents=True)
        write_text(tmp_path / "dadaia_workspace" / "features" / pkg / "__init__.py", "")

    issues = MemoryValidator(specs).check_mem_drift1_features_package_map()

    if needle is None:
        assert issues == []
    else:
        [issue] = issues
        assert (issue.code, issue.verdict, issue.fixable) == ("MEM-DRIFT-1", "warning", False)
        assert needle in issue.message


def test_mem_drift1_lists_only_the_packages_of_the_trees_own_features_folder(
    tmp_path: Path,
) -> None:
    specs = tmp_path / "specs"
    (specs / "memory").mkdir(parents=True)
    write_text(specs / "memory" / "ARCHITECTURE.md", _architecture_md(("panel",)))
    features = tmp_path / "dadaia_workspace" / "features"
    (features / "panel").mkdir(parents=True)
    write_text(features / "panel" / "__init__.py", "")
    (features / "plain_dir").mkdir()
    write_text(features / "module.py", "")

    assert MemoryValidator(specs).check_mem_drift1_features_package_map() == []


def _tree(tmp_path: Path, mapped: tuple[str, ...], own: tuple[str, ...] | None) -> Path:
    """The specs dir of a repo whose ARCHITECTURE.md maps *mapped* and whose own
    `dadaia_workspace/features/` holds the packages *own* (no such folder when `None`)."""
    specs = tmp_path / "repo" / "specs"
    (specs / "memory").mkdir(parents=True)
    write_text(specs / "memory" / "ARCHITECTURE.md", _architecture_md(mapped))
    features = tmp_path / "repo" / "dadaia_workspace" / "features"
    for pkg in own or ():
        (features / pkg).mkdir(parents=True)
        write_text(features / pkg / "__init__.py", "")
    if own is not None:
        features.mkdir(parents=True, exist_ok=True)
    return specs


@pytest.mark.parametrize(
    ("mapped", "own", "expected"),
    [
        pytest.param(("alpha", "beta"), ("alpha", "beta"), [], id="own-folder-matches-its-map"),
        pytest.param(("alpha", "beta"), None, [], id="no-own-folder-no-list-no-finding"),
        pytest.param(
            ("alpha", "gone"),
            ("alpha", "extra"),
            ["'gone'", "dadaia_workspace/features/extra"],
            id="own-folder-disagrees",
        ),
    ],
)
def test_mem_drift1_reads_the_trees_own_features_folder(
    tmp_path: Path, mapped: tuple[str, ...], own: tuple[str, ...] | None, expected: list[str]
) -> None:
    issues = MemoryValidator(_tree(tmp_path, mapped, own)).check_mem_drift1_features_package_map()

    assert [issue.code for issue in issues] == ["MEM-DRIFT-1"] * len(expected)
    assert all(needle in issue.message for issue, needle in zip(issues, expected, strict=True))


def test_unfilled_placeholder_atom_is_reported_with_the_fill_or_delete_line(tmp_path: Path) -> None:
    specs = _make_specs_with_memory(tmp_path)
    atom = specs / "memory" / "product" / "a" / "x.md"
    write_text(
        atom,
        "---\nslug: SLUG_PLACEHOLDER\ntitle: TITLE_PLACEHOLDER\ntldr: t\nsummary: s\n---\n\n# X\n",
    )
    [issue] = MemoryValidator(specs).check_placeholder_atoms()
    assert (issue.code, issue.fixable) == ("MEM-PLACEHOLDER-1", False)
    assert issue.fix == f"Agent action: fill or delete the atom {atom}"
