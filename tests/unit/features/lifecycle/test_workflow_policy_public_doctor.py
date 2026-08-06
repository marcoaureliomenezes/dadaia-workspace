"""Unit tests for the public-doctor Layer-2 residue check (T-28-D-02).

``dadaia public doctor`` must assert that removed/deferred Layer-2 worker harnesses
(``claude`` / ``opencode``) do not leak into the public workflow-policy docs as a
selectable Layer-2 *worker* choice (LAW 1). A doc that merely says "claude is a Layer-1
entry harness, not a Layer-2 worker" must NOT trip the check (it is the contract, stated).

Layer-2 residue enforcement, docs layer (one of four independent layers: resolver, doctor,
schema, public docs).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.lifecycle.policy_public_doctor import (
    check_workflow_policy_layer2_residue,
)


def _rendered(result: object) -> list[str]:
    """Legacy string view of a typed doctor result (DoctorReport | list[DoctorLine])."""
    if hasattr(result, "rendered"):
        return result.rendered()  # type: ignore[attr-defined, no-any-return]
    return [
        line.render() if hasattr(line, "render") else str(line)
        for line in result  # type: ignore[union-attr]
    ]


def _public(tmp_path: Path) -> Path:
    schemas = tmp_path / "schemas"
    schemas.mkdir(parents=True)
    return tmp_path


_FIXTURE_CASES = (
    (
        "claude-flagged",
        ("data",),
        "data/AGENTS.md",
        "Select a Layer-2 worker harness: codex, pi, or claude.\n",
        True,
        "claude",
    ),
    (
        "opencode-flagged",
        ("skills",),
        "skills/SKILL.md",
        "The Layer-2 worker harnesses are codex, pi, and opencode.\n",
        True,
        None,
    ),
    (
        "layer1-only-mention-passes",
        ("data",),
        "data/AGENTS.md",
        (
            "claude is a Layer-1 entry harness; it is never a Layer-2 worker. opencode was "
            "removed as a Layer-2 worker in v0.1.24.\n"
        ),
        False,
        None,
    ),
    (
        "clean-passes",
        ("data",),
        "data/AGENTS.md",
        "Layer-2 workflow workers are codex and pi only.\n",
        False,
        None,
    ),
)


@pytest.mark.parametrize(
    "case_id,dirs,rel_path,content,expect_drift,expect_substring",
    _FIXTURE_CASES,
    ids=[c[0] for c in _FIXTURE_CASES],
)
def test_fixture_matrix(
    tmp_path: Path,
    case_id: str,
    dirs: tuple[str, ...],
    rel_path: str,
    content: str,
    expect_drift: bool,
    expect_substring: str | None,
) -> None:
    public = _public(tmp_path)
    for d in dirs:
        (public / d).mkdir(exist_ok=True)
    (public / rel_path).write_text(content, encoding="utf-8")

    out = _rendered(check_workflow_policy_layer2_residue(public))

    if expect_drift:
        drift_lines = [line for line in out if line.startswith("[drift]")]
        assert drift_lines
        if expect_substring is not None:
            assert any(expect_substring in line for line in drift_lines)
    else:
        assert not any(line.startswith("[drift]") for line in out)
        if case_id == "clean-passes":
            assert any(line.startswith("[ok]") for line in out)


def test_missing_public_dir_is_noop(tmp_path: Path) -> None:
    out = _rendered(check_workflow_policy_layer2_residue(tmp_path / "nope"))
    assert out == []


def test_real_public_surface_is_clean() -> None:
    """The shipped public surface must carry no Layer-2 claude/opencode worker residue."""
    import dadaia_workspace

    public_dir = Path(dadaia_workspace.__file__).parent / "public"
    out = _rendered(check_workflow_policy_layer2_residue(public_dir))
    drift = [line for line in out if line.startswith("[drift]")]
    assert drift == [], drift
