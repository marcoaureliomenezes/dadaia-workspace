"""Unit tests for the memory validator's LINT-1 mapping (v0.4.3 T-043-20/FR16).

LINT-1 imports ``features.specs.memory_lint`` directly now — no subprocess, no
``ProcessRunner``, no dependency on the projected ``public/scripts/lint-memory-atoms.py``
copy existing (A16.1). These tests exercise ``check_lint1_memory_atoms`` against REAL
memory-atom fixtures written under ``tmp_path``, proving the severity mapping end to end
through the real ``memory_lint`` implementation — never a faked subprocess result.

Intent: CONTRACT — v0.4.3 A16.1.
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.features.specs import Severity
from dadaia_workspace.features.specs.doctor_memory import MemoryValidator

_VALID_FRONTMATTER = """---
slug: {slug}
title: "Fixture atom"
category: core
tldr: "a valid atom for LINT-1 fixture purposes"
summary: "a valid atom for LINT-1 fixture purposes, used across doctor_memory tests"
tags: ["fixture"]
last_updated: "2026-08-17"
release_origin: "v0.4.3"
---
"""


def _make_specs_with_memory(tmp_path: Path) -> Path:
    specs = tmp_path / "specs"
    (specs / "memory").mkdir(parents=True)
    return specs


def test_lint1_clean_atom_produces_no_issues(tmp_path: Path) -> None:
    specs = _make_specs_with_memory(tmp_path)
    (specs / "memory" / "architecture.md").write_text(
        _VALID_FRONTMATTER.format(slug="architecture") + "\n## Purpose\n\nclean atom\n",
        encoding="utf-8",
    )

    issues = MemoryValidator(specs).check_lint1_memory_atoms()

    assert issues == []


def test_lint1_forbidden_heading_maps_to_error(tmp_path: Path) -> None:
    specs = _make_specs_with_memory(tmp_path)
    (specs / "memory" / "architecture.md").write_text(
        _VALID_FRONTMATTER.format(slug="architecture") + "\n## Changelog\n\nnot allowed\n",
        encoding="utf-8",
    )

    issues = MemoryValidator(specs).check_lint1_memory_atoms()

    assert len(issues) == 1
    assert issues[0].code == "LINT-1"
    assert issues[0].severity == Severity.ERROR
    assert "Forbidden heading" in issues[0].description
    assert "Changelog" in issues[0].description


def test_lint1_unknown_heading_maps_to_warning(tmp_path: Path) -> None:
    specs = _make_specs_with_memory(tmp_path)
    (specs / "memory" / "architecture.md").write_text(
        _VALID_FRONTMATTER.format(slug="architecture")
        + "\n## Some Brand New Unallowlisted Heading\n\ncontent\n",
        encoding="utf-8",
    )

    issues = MemoryValidator(specs).check_lint1_memory_atoms()

    assert len(issues) == 1
    assert issues[0].code == "LINT-1"
    assert issues[0].severity == Severity.WARNING
    assert "not in the curated allowlist" in issues[0].description


def test_lint1_error_takes_priority_over_warning_in_the_same_run(tmp_path: Path) -> None:
    """When BOTH an error-class and a warning-class atom exist, the aggregate issue is
    ERROR — errors are never silently downgraded by a co-occurring warning."""
    specs = _make_specs_with_memory(tmp_path)
    (specs / "memory" / "architecture.md").write_text(
        _VALID_FRONTMATTER.format(slug="architecture") + "\n## History\n\nforbidden\n",
        encoding="utf-8",
    )
    (specs / "memory" / "tech-stack.md").write_text(
        _VALID_FRONTMATTER.format(slug="tech-stack") + "\n## Totally Unknown Heading\n\nx\n",
        encoding="utf-8",
    )

    issues = MemoryValidator(specs).check_lint1_memory_atoms()

    assert len(issues) == 1
    assert issues[0].severity == Severity.ERROR


def test_lint1_no_memory_dir_is_a_noop(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    specs.mkdir()

    issues = MemoryValidator(specs).check_lint1_memory_atoms()

    assert issues == []


def test_lint1_empty_memory_dir_is_a_noop(tmp_path: Path) -> None:
    specs = _make_specs_with_memory(tmp_path)

    issues = MemoryValidator(specs).check_lint1_memory_atoms()

    assert issues == []


def test_lint1_process_runner_constructor_arg_is_accepted_but_unused(tmp_path: Path) -> None:
    """v0.4.3 T-043-20/FR16: the constructor still accepts ``process_runner`` (kept for
    SpecsDoctor.__init__'s call-site compatibility), but LINT-1 no longer touches it —
    passing a runner that would explode if ever called proves it is never invoked."""

    class _ExplodingRunner:
        def run(self, argv: object, **kwargs: object) -> object:
            raise AssertionError("LINT-1 must never invoke a ProcessRunner (A16.1)")

    specs = _make_specs_with_memory(tmp_path)
    (specs / "memory" / "architecture.md").write_text(
        _VALID_FRONTMATTER.format(slug="architecture") + "\n## Purpose\n\nclean\n",
        encoding="utf-8",
    )

    issues = MemoryValidator(specs, process_runner=_ExplodingRunner()).check_lint1_memory_atoms()  # type: ignore[arg-type]

    assert issues == []
