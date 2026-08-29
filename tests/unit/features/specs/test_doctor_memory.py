"""Unit tests for the memory validator's MEM-DRIFT-1 rule (v0.5.1 T-051-22 rework).

Relocates the diagram-vs-code correspondence guard the deleted push-gated contract test
``tests/contract/test_architecture_diagrams_current.py`` used to own (removed at 5e0719af,
bug ``push-gate-test-pins-memory-package-count-that-only-closure-may-change``) into a
`specs doctor` WARNING per qa-engineer's 2026-08-29 deletion-verdict handoff. Table-driven:
stale diagram node, missing live package, matching set, and no ``ARCHITECTURE.md`` at all.

The live-package introspection (``_live_feature_package_names``) is monkeypatched so this
test never depends on this REPO's own actual ``dadaia_workspace/features`` package set —
only the doctor interface (``check_mem_drift1_features_package_map``) is under test.

Intent: CONTRACT — v0.5.1 T-051-22 rework (qa-engineer deletion verdict
2026-08-29T212000Z-qa-engineer-0.5.1-diagram-test-deletion-verdict).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.specs import doctor_memory
from dadaia_workspace.features.specs.doctor_memory import MemoryValidator
from dadaia_workspace.features.specs.doctor_types import Severity

_HEADING = "### `dadaia_workspace/features` — package map ({n} packages)"


def _architecture_md(pkgs: tuple[str, ...]) -> str:
    """A minimal ARCHITECTURE.md carrying the real features package-map mermaid shape."""
    pkgs_line = " · ".join(pkgs)
    return (
        "# Architecture\n\n"
        "## Part 2 — Implementation\n\n"
        f"{_HEADING.format(n=len(pkgs))}\n\n"
        "```mermaid\n"
        "flowchart TB\n"
        '    subgraph features["dadaia_workspace/features"]\n'
        f'      pkgs["{pkgs_line}"]\n'
        '      subs["reports submodules — next · retention · validation"]\n'
        "    end\n"
        '    container["container.py"] --> features\n'
        '    features --> core["core"]\n'
        "```\n\n"
        "### next section\n\nsome unrelated content\n"
    )


def _write_architecture_md(specs: Path, pkgs: tuple[str, ...]) -> None:
    mem_dir = specs / "memory"
    mem_dir.mkdir(parents=True, exist_ok=True)
    (mem_dir / "ARCHITECTURE.md").write_text(_architecture_md(pkgs), encoding="utf-8")


@pytest.mark.parametrize(
    "case_id, diagrammed, live, expected_codes, expected_needle",
    [
        (
            "stale_node",
            ("academy", "spec_artifacts"),
            frozenset({"academy"}),
            ["MEM-DRIFT-1"],
            "spec_artifacts",
        ),
        (
            "missing_live_package",
            ("academy",),
            frozenset({"academy", "repos"}),
            ["MEM-DRIFT-1"],
            "repos",
        ),
        (
            "matching",
            ("academy", "repos"),
            frozenset({"academy", "repos"}),
            [],
            None,
        ),
    ],
)
def test_mem_drift1_table(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case_id: str,
    diagrammed: tuple[str, ...],
    live: frozenset[str],
    expected_codes: list[str],
    expected_needle: str | None,
) -> None:
    specs = tmp_path / "specs"
    _write_architecture_md(specs, diagrammed)
    monkeypatch.setattr(doctor_memory, "_live_feature_package_names", lambda: set(live))

    issues = MemoryValidator(specs).check_mem_drift1_features_package_map()

    assert [i.code for i in issues] == expected_codes, case_id
    if expected_codes:
        assert len(issues) == 1, case_id
        assert issues[0].severity == Severity.WARNING, case_id
        assert issues[0].fixable is False, case_id
        assert expected_needle is not None
        assert expected_needle in issues[0].description, case_id


def test_mem_drift1_no_architecture_md_produces_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    specs = tmp_path / "specs"
    (specs / "memory").mkdir(parents=True)
    monkeypatch.setattr(doctor_memory, "_live_feature_package_names", lambda: {"academy"})

    issues = MemoryValidator(specs).check_mem_drift1_features_package_map()

    assert issues == []


def test_mem_drift1_no_memory_dir_produces_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    specs = tmp_path / "specs"
    specs.mkdir(parents=True)
    monkeypatch.setattr(doctor_memory, "_live_feature_package_names", lambda: {"academy"})

    issues = MemoryValidator(specs).check_mem_drift1_features_package_map()

    assert issues == []


def test_mem_drift1_missing_heading_produces_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A consumer's ARCHITECTURE.md with no features-package-map heading at all (this
    rule's content is dadaia-workspace-library-specific) is a silent no-op, never a
    'heading missing' complaint — SPEC-DOC-002/TREE-3 already own atom-presence."""
    specs = tmp_path / "specs"
    mem_dir = specs / "memory"
    mem_dir.mkdir(parents=True)
    (mem_dir / "ARCHITECTURE.md").write_text("# Architecture\n\nnothing relevant here.\n")
    monkeypatch.setattr(doctor_memory, "_live_feature_package_names", lambda: {"academy"})

    issues = MemoryValidator(specs).check_mem_drift1_features_package_map()

    assert issues == []


def test_mem_drift1_real_live_introspection_returns_package_names() -> None:
    """Unmocked smoke test: ``_live_feature_package_names`` really introspects this repo's
    own installed ``dadaia_workspace.features`` package (no hardcoded expectation list)."""
    live = doctor_memory._live_feature_package_names()

    assert "specs" in live  # this very module's own package
    assert all(isinstance(name, str) and name for name in live)
