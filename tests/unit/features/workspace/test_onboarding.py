"""The derived onboarding next step — one fixture per level.

Intent: CONTRACT — 0.4.8 FR6 AC6.1 / D11 (T-048-07). Size: SMALL (unit).
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.features.workspace.onboarding import next_step

_CLI = ".dadaia/.venv/bin/dadaia"


def _specs(tmp_path: Path, *, version: int = 7, stamped: bool = False) -> Path:
    specs = tmp_path / "repos" / "app" / "specs"
    specs.mkdir(parents=True)
    (specs / "constitution.md").write_text(
        f"---\nspecs_pattern_version: {version}\n---\n# c\n", encoding="utf-8"
    )
    if stamped:
        histo = specs / "audits" / "_archive" / "audits_histo.jsonl"
        histo.parent.mkdir(parents=True)
        histo.write_text('{"id": "first"}\n', encoding="utf-8")
    return specs


def _snapshot(root: Path) -> set[Path]:
    return set(root.rglob("*"))


def test_zero_contexts_names_context_create(tmp_path: Path) -> None:
    step = next_step(tmp_path, {})
    assert step is not None
    assert step.command == f"{tmp_path}/{_CLI} context create <name> --main-repo <clone-url>"


def test_a_context_without_specs_names_specs_init(tmp_path: Path) -> None:
    step = next_step(tmp_path, {"app": tmp_path / "repos" / "app" / "specs"})
    assert step is not None
    assert step.command == f"{tmp_path}/{_CLI} specs init --context app"


def test_an_older_or_foreign_tree_is_still_level_two(tmp_path: Path) -> None:
    step = next_step(tmp_path, {"app": _specs(tmp_path, version=6)})
    assert step is not None
    assert step.command.endswith("specs init --context app")


def test_an_unaudited_tree_names_the_first_pass_worklist(tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    step = next_step(tmp_path, {"app": specs})
    assert step is not None
    assert "dd-audit-project" in step.reason
    assert f"memory.py drift --since $(git -C {specs.parent} rev-list" in step.command
    assert step.command.endswith(f"--specs {specs}")


def test_the_lowest_unmet_level_wins_across_contexts(tmp_path: Path) -> None:
    trees = {"app": _specs(tmp_path), "new": tmp_path / "repos" / "new" / "specs"}
    step = next_step(tmp_path, trees)
    assert step is not None
    assert step.command.endswith("specs init --context new")


def test_a_complete_workspace_has_no_step_and_nothing_is_written(tmp_path: Path) -> None:
    trees = {"app": _specs(tmp_path, stamped=True)}
    before = _snapshot(tmp_path)
    assert next_step(tmp_path, trees) is None
    assert _snapshot(tmp_path) == before  # D11: derived, never a state file


def test_the_text_is_the_reason_plus_one_fix_line(tmp_path: Path) -> None:
    step = next_step(tmp_path, {})
    assert step is not None
    assert step.text().splitlines() == [f"Next: {step.reason}", f"fix: {step.command}"]
