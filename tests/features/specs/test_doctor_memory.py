"""Unit tests for the memory validator's LINT-1 mapping (v0.4.3 T-043-20/FR16).

LINT-1 imports ``features.specs.memory_lint`` directly (A16.1). These tests exercise ``check_lint1_memory_atoms`` against REAL
memory-atom fixtures written under ``tmp_path``, proving the severity mapping end to end
through the real ``memory_lint`` implementation — never a faked subprocess result.

v0.5.1 T-051-22 rework: MEM-DRIFT-1, the features package-map
diagram in ARCHITECTURE.md vs the live ``dadaia_workspace/features`` packages (bug
push-gate-test-pins-memory-package-count-that-only-closure-may-change).

The live-package introspection is monkeypatched in the table; one smoke test runs it for
real.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.specs import doctor_memory
from dadaia_workspace.features.specs.doctor_memory import MemoryValidator
from dadaia_workspace.features.specs.doctor_types import finding_path

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
    (specs / "memory" / "product" / "a" / "architecture.md").write_text(
        _VALID_FRONTMATTER.format(slug="architecture") + "\n## Purpose\n\nclean atom\n",
        encoding="utf-8",
    )

    issues = MemoryValidator(specs).check_lint1_memory_atoms()

    assert issues == []


def test_lint1_forbidden_heading_maps_to_error(tmp_path: Path) -> None:
    specs = _make_specs_with_memory(tmp_path)
    (specs / "memory" / "product" / "a" / "architecture.md").write_text(
        _VALID_FRONTMATTER.format(slug="architecture") + "\n## Changelog\n\nnot allowed\n",
        encoding="utf-8",
    )

    issues = MemoryValidator(specs).check_lint1_memory_atoms()

    assert len(issues) == 1
    assert issues[0].code == "LINT-1"
    assert issues[0].error
    assert "Forbidden heading" in issues[0].message
    assert "Changelog" in issues[0].message


def test_lint1_unknown_heading_produces_no_issue(tmp_path: Path) -> None:
    """The heading-vocabulary check (a curated allowlist of "known" headings) is
    retired (v0.5.0): a heading vocabulary is prose policy, not a lint. A heading
    nobody has ever seen before is neither an error nor a warning at the doctor
    mapping layer either."""
    specs = _make_specs_with_memory(tmp_path)
    (specs / "memory" / "product" / "a" / "architecture.md").write_text(
        _VALID_FRONTMATTER.format(slug="architecture")
        + "\n## Some Brand New Never Before Seen Heading\n\ncontent\n",
        encoding="utf-8",
    )

    issues = MemoryValidator(specs).check_lint1_memory_atoms()

    assert issues == []


def test_lint1_error_atom_and_clean_atom_coexist_only_the_error_surfaces(tmp_path: Path) -> None:
    """Multiple atoms aggregate correctly: a genuine forbidden-heading ERROR in one
    atom surfaces, while a sibling atom with an ordinary (never-curated) heading
    contributes nothing — exactly one issue, not silently swallowed or duplicated."""
    specs = _make_specs_with_memory(tmp_path)
    (specs / "memory" / "product" / "a" / "architecture.md").write_text(
        _VALID_FRONTMATTER.format(slug="architecture") + "\n## History\n\nforbidden\n",
        encoding="utf-8",
    )
    (specs / "memory" / "product" / "a" / "tech-stack.md").write_text(
        _VALID_FRONTMATTER.format(slug="tech-stack") + "\n## Some Other Heading\n\nx\n",
        encoding="utf-8",
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
    """Bug lint1-prints-raw-multiline-findings: the doctor prints one
    `<CODE> <verdict> <message>` line per finding, so every lint error is its own issue
    naming its own atom — never a multi-line block of `  [path] ERROR:` lines."""
    specs = _make_specs_with_memory(tmp_path)
    architecture = specs / "memory" / "product" / "a" / "architecture.md"
    architecture.write_text(
        _VALID_FRONTMATTER.format(slug="architecture") + "\n## History\n\nx\n## Changelog\n",
        encoding="utf-8",
    )
    quality = specs / "memory" / "product" / "a" / "quality.md"
    quality.write_text(
        _VALID_FRONTMATTER.format(slug="quality") + "\n## History\n\nx\n", encoding="utf-8"
    )

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
    monkeypatch: pytest.MonkeyPatch,
    architecture: str | None,
    live: set[str],
    needle: str | None,
) -> None:
    specs = tmp_path / "specs"
    (specs / "memory").mkdir(parents=True)
    if architecture is not None:
        (specs / "memory" / "ARCHITECTURE.md").write_text(architecture, encoding="utf-8")
    monkeypatch.setattr(doctor_memory, "_live_feature_package_names", lambda: live)

    issues = MemoryValidator(specs).check_mem_drift1_features_package_map()

    if needle is None:
        assert issues == []
    else:
        [issue] = issues
        assert (issue.code, issue.verdict, issue.fixable) == ("MEM-DRIFT-1", "warning", False)
        assert needle in issue.message


def test_mem_drift1_real_live_introspection_returns_package_names() -> None:
    live = doctor_memory._live_feature_package_names()
    assert "specs" in live and all(isinstance(name, str) and name for name in live)
