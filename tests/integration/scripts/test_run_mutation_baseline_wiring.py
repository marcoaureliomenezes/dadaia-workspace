"""Wiring test for tests/scripts/run_mutation_baseline.sh (FR20, v0.4.3 T-043-28).

This script is the runnable command that backs quality-assurance.md's mutation-cadence
claim ("once per release, off the push path") once mutmut is selected and pinned
(qa-engineer verdict, .dadaia/tmp/qa-engineer/20260817/
v0.4.3-T-043-28-mutation-tool-verdict.md). Because a real invocation spins a throwaway
venv and installs a package over the network, this suite never runs the script for
real (dadaia-test-stewardship / DADAIA.md "Slop-test discipline": "No real venvs built
in tests — they exhaust disk"). Instead it proves the three things a gating test CAN
prove cheaply and deterministically:

  1. The script is syntactically valid bash (`bash -n`) and carries the exact pin the
     verdict selected.
  2. The staging step alone (`DADAIA_MUTATION_STAGE_ONLY=1`) — which the real run also
     executes first — copies the scoped `dadaia_workspace/core/models/` +
     `tests/unit/core/models/` subset into an isolated destination (redirected via
     `DADAIA_WORKSPACE_ROOT` to a fake tmp_path tree, never the real workspace) and
     writes the exact `[tool.mutmut]` config the runner uses — WITHOUT touching the
     real repo's git-tracked tree (A20.1's "runs to completion" precondition: the
     staging half must be side-effect-free on the repo before the tool half is ever
     invoked). This is the verdict's own already-validated smoke-trial sub-slice
     (§3.1), not the wider `core/` the verdict recommended for the first baseline — see
     the runner script's header comment for the full narrowing rationale (mutmut's own
     `mutants/` sandbox mirrors ONLY `source_paths` on disk, and the wider
     `tests/unit/core/` flat tier contains real cross-layer architecture tests that
     cannot run inside any sandbox narrower than the whole package).
  3. The script is never referenced from any push-path selector (A20.3): a permanent
     regression guard against someone later wiring it into ci.yml, release.yml, or the
     local pre-push preflight.

Intent: CONTRACT — v0.4.3 A20.1, A20.3 (T-043-28, FR20)
Owner: software-engineer
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration]

_SCRIPT = Path(__file__).resolve().parent.parent.parent / "scripts" / "run_mutation_baseline.sh"
_REPO_ROOT = _SCRIPT.parent.parent.parent
_CI_YML = _REPO_ROOT / ".github" / "workflows" / "ci.yml"
_RELEASE_YML = _REPO_ROOT / ".github" / "workflows" / "release.yml"
_CI_PREFLIGHT_SERVICE = _REPO_ROOT / "dadaia_workspace" / "features" / "ci_preflight" / "service.py"


def test_script_exists_and_is_executable() -> None:
    assert _SCRIPT.is_file(), f"expected runner script at {_SCRIPT}"
    assert _SCRIPT.stat().st_mode & 0o111, "script must be executable (chmod +x)"


def test_script_has_valid_bash_syntax() -> None:
    result = subprocess.run(
        ["bash", "-n", str(_SCRIPT)], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, f"bash -n failed: {result.stderr}"


def test_script_pins_the_exact_verdict_version() -> None:
    """qa-engineer's verdict pin: `mutmut==3.7.0` (exact, per FR1)."""
    text = _SCRIPT.read_text("utf-8")
    assert "mutmut==3.7.0" in text


def test_staging_step_copies_scoped_subset_without_touching_repo_git_tree(
    tmp_path: Path,
) -> None:
    fake_workspace = tmp_path / "fake-workspace"
    fake_workspace.mkdir()

    before = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(_REPO_ROOT),
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    result = subprocess.run(
        [str(_SCRIPT), "wiring-test-output.json"],
        capture_output=True,
        text=True,
        env={
            "PATH": "/usr/bin:/bin",
            "DADAIA_MUTATION_STAGE_ONLY": "1",
            "DADAIA_WORKSPACE_ROOT": str(fake_workspace),
        },
    )
    assert result.returncode == 0, (
        f"stage-only run failed.\nstdout: {result.stdout!r}\nstderr: {result.stderr!r}"
    )

    after = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(_REPO_ROOT),
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert before == after, "staging must never modify the repo's own git-tracked tree"

    stage_dirs = list(
        (fake_workspace / ".dadaia" / "tmp" / "software-engineer").glob("*/mutation-run")
    )
    assert len(stage_dirs) == 1, f"expected exactly one dated mutation-run dir, found {stage_dirs}"
    stage = stage_dirs[0]

    real_core_models_files = {
        p.relative_to(_REPO_ROOT / "dadaia_workspace" / "core" / "models")
        for p in (_REPO_ROOT / "dadaia_workspace" / "core" / "models").rglob("*.py")
    }
    staged_core_models_files = {
        p.relative_to(stage / "dadaia_workspace" / "core" / "models")
        for p in (stage / "dadaia_workspace" / "core" / "models").rglob("*.py")
    }
    assert staged_core_models_files == real_core_models_files, (
        "staged core/models/ must mirror the real core/models/ exactly"
    )

    real_test_files = {
        p.relative_to(_REPO_ROOT / "tests" / "unit" / "core" / "models")
        for p in (_REPO_ROOT / "tests" / "unit" / "core" / "models").rglob("*.py")
    }
    staged_test_files = {
        p.relative_to(stage / "tests" / "unit" / "core" / "models")
        for p in (stage / "tests" / "unit" / "core" / "models").rglob("*.py")
    }
    assert staged_test_files == real_test_files, (
        "staged tests/unit/core/models must mirror the real tree exactly"
    )

    config_text = (stage / "pyproject.toml").read_text("utf-8")
    assert 'source_paths = ["dadaia_workspace/core/models"]' in config_text
    assert 'pytest_add_cli_args_test_selection = ["tests/unit/core/models"]' in config_text
    assert "mutate_only_covered_lines = true" in config_text
    assert "use_git_change_detection = false" in config_text


def test_script_never_referenced_from_a_push_path_selector() -> None:
    """A20.3: the tool is absent from every push-path selector; CI push timing unchanged."""
    for path in (_CI_YML, _RELEASE_YML, _CI_PREFLIGHT_SERVICE):
        assert path.is_file(), f"expected push-path file at {path}"
        text = path.read_text("utf-8")
        assert "run_mutation_baseline" not in text, f"{path} must not reference the runner"
        assert "mutmut" not in text, f"{path} must not reference mutmut"
