"""AISURF — ordered ritual belongs in the on-demand skill, not the always-loaded law.

The root ``AGENTS.md`` is loaded into every session of every harness, so it states the
law and names the skill. A skill is loaded on demand and **is** the procedure. These
tests pin which side of that line each surface sits on.
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.features.ai_surface.doctor import check_ai_surface_ritual

_RITUAL = (
    "1. Read ACTIVE.md.\n"
    "2. Read SPEC.md then PLAN.md then TASKS.md.\n"
    "3. Reserve your task: flip `[ ]` -> `[-]`.\n"
    "[SDD HARD STOP] do not proceed without an approved SPEC.\n"
)
_CLEAN = (
    "Run ordered work by dispatching the owning persona and having it follow the\n"
    "matching skill: `dadaia-release-definition`, `dadaia-task-manager`.\n"
    "The markers are `[ ]` OPEN, `[-]` IN PROGRESS, `[x]` DONE.\n"
)


def _public(tmp_path: Path, rel: str, body: str) -> Path:
    target = tmp_path / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")
    return tmp_path


def _drift(lines: list[str]) -> list[str]:
    return [line for line in lines if line.startswith("[drift]")]


def test_ritual_in_the_always_loaded_root_law_is_drift(tmp_path: Path) -> None:
    lines = check_ai_surface_ritual(_public(tmp_path, "data/AGENTS.md", _RITUAL))

    rules = {line.split("(")[-1].split(")")[0] for line in _drift(lines)}
    assert rules == {"AISURF-1", "AISURF-2", "AISURF-3"}
    assert all("data/AGENTS.md:" in line for line in _drift(lines))


def test_scaffold_law_is_policed_the_same_way(tmp_path: Path) -> None:
    lines = check_ai_surface_ritual(_public(tmp_path, "scaffold/AGENTS.md", _RITUAL))

    assert _drift(lines), "the scaffolded root law is always-loaded too"


def test_ritual_in_a_skill_is_correct_by_construction(tmp_path: Path) -> None:
    """The engine is gone: the skill IS the procedure, so ritual there is not drift."""
    root = _public(tmp_path, "skills/dadaia-task-manager/SKILL.md", _RITUAL)

    assert check_ai_surface_ritual(root) == ["[ok] ai-surface (no reintroduced lifecycle ritual)"]


def test_a_persona_carries_its_own_role_discipline(tmp_path: Path) -> None:
    root = _public(tmp_path, "agents/software-engineer.md", _RITUAL)

    assert _drift(check_ai_surface_ritual(root)) == []


def test_naming_the_skill_and_legending_the_markers_is_clean(tmp_path: Path) -> None:
    """The escape hatch has to stay open, or the law cannot describe itself."""
    root = _public(tmp_path, "data/AGENTS.md", _CLEAN)

    assert check_ai_surface_ritual(root) == ["[ok] ai-surface (no reintroduced lifecycle ritual)"]


def test_a_missing_public_dir_reports_nothing(tmp_path: Path) -> None:
    assert check_ai_surface_ritual(tmp_path / "absent") == []
