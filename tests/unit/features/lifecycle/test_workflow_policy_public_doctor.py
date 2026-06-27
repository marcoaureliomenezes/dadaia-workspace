"""Unit tests for the public-doctor Layer-2 residue check (T-28-D-02).

``dadaia public doctor`` must assert that removed/deferred Layer-2 worker harnesses
(``claude`` / ``opencode``) do not leak into the public workflow-policy docs as a
selectable Layer-2 *worker* choice (LAW 1). A doc that merely says "claude is a Layer-1
entry harness, not a Layer-2 worker" must NOT trip the check (it is the contract, stated).
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.features.lifecycle.policy_public_doctor import (
    check_workflow_policy_layer2_residue,
)


def _public(tmp_path: Path) -> Path:
    schemas = tmp_path / "schemas"
    schemas.mkdir(parents=True)
    return tmp_path


def test_clean_public_surface_passes(tmp_path: Path) -> None:
    public = _public(tmp_path)
    (public / "data").mkdir()
    (public / "data" / "AGENTS.md").write_text(
        "Layer-2 workflow workers are codex and pi only.\n", encoding="utf-8"
    )
    out = check_workflow_policy_layer2_residue(public)
    assert any(line.startswith("[ok]") for line in out)
    assert not any(line.startswith("[drift]") for line in out)


def test_layer2_worker_claude_residue_is_flagged(tmp_path: Path) -> None:
    public = _public(tmp_path)
    (public / "data").mkdir()
    (public / "data" / "AGENTS.md").write_text(
        "Select a Layer-2 worker harness: codex, pi, or claude.\n", encoding="utf-8"
    )
    out = check_workflow_policy_layer2_residue(public)
    assert any(line.startswith("[drift]") for line in out)
    assert any("claude" in line for line in out if line.startswith("[drift]"))


def test_layer2_worker_opencode_residue_is_flagged(tmp_path: Path) -> None:
    public = _public(tmp_path)
    (public / "skills").mkdir()
    (public / "skills" / "SKILL.md").write_text(
        "The Layer-2 worker harnesses are codex, pi, and opencode.\n", encoding="utf-8"
    )
    out = check_workflow_policy_layer2_residue(public)
    assert any(line.startswith("[drift]") for line in out)


def test_layer1_only_mention_does_not_trip(tmp_path: Path) -> None:
    """A doc stating claude/opencode are NOT Layer-2 workers is the contract, not a leak."""
    public = _public(tmp_path)
    (public / "data").mkdir()
    (public / "data" / "AGENTS.md").write_text(
        "claude is a Layer-1 entry harness; it is never a Layer-2 worker. opencode was "
        "removed as a Layer-2 worker in v0.1.24.\n",
        encoding="utf-8",
    )
    out = check_workflow_policy_layer2_residue(public)
    assert not any(line.startswith("[drift]") for line in out)


def test_missing_public_dir_is_noop(tmp_path: Path) -> None:
    out = check_workflow_policy_layer2_residue(tmp_path / "nope")
    assert out == []


def test_real_public_surface_is_clean() -> None:
    """The shipped public surface must carry no Layer-2 claude/opencode worker residue."""
    import dadaia_workspace

    public_dir = Path(dadaia_workspace.__file__).parent / "public"
    out = check_workflow_policy_layer2_residue(public_dir)
    drift = [line for line in out if line.startswith("[drift]")]
    assert drift == [], drift
