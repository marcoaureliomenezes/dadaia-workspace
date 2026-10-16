"""A constitution that is not UTF-8 gets the kernel's re-encode act wherever a state or a step
names its remedy, never the YAML-repair act."""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.core.specs_version import state
from dadaia_workspace.features.workspace.onboarding import next_step


def _specs(tmp_path: Path) -> tuple[Path, str]:
    specs = tmp_path / "specs"
    specs.mkdir()
    (specs / "constitution.md").write_bytes("# Constituição — ação\n".encode("cp1252"))
    act = (
        f"Agent action: re-encode line 1 of {(specs / 'constitution.md').resolve()} "
        "as UTF-8 in place; every other line stays"
    )
    return specs, act


def test_the_specs_state_names_the_reencode_act(tmp_path: Path) -> None:
    specs, act = _specs(tmp_path)

    assert state(specs) == ("malformed", act)


def test_the_constitution_step_names_the_reencode_act(tmp_path: Path) -> None:
    specs, act = _specs(tmp_path)

    step = next_step(tmp_path, {"proj": specs}, "proj")

    assert step is not None and (step.id, step.kind, step.command) == ("constitution", "agent", act)
