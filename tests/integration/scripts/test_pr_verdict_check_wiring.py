"""Wiring test for .github/scripts/pr-verdict-check.sh (v0.4.4 FR4; v0.5.1 K7).

v0.5.1 K7 ("split chokepoints.service into its four modules; one verdict store")
collapses the script to a thin wrapper over `dadaia ci verdict-check`, built over
`features.chokepoints.verdict.covering_verdict` — the ONE rule now reading the
committed `specs/releases/**/verdicts/` evidence. Every behavioral case this file
used to exercise via real subprocess/git plumbing (exact-sha match, first-parent
match, archived-tree evidence, stale/unrelated shas, wrong-agent/rejected verdicts,
release-id narrowing) now lives at the cheaper `covering_verdict`/`verdict-check`
Python level — see `tests/unit/features/chokepoints/test_verdict.py` and
`tests/integration/cli/test_cli_ci_verdict_check.py`. This file keeps only the
wiring proof: the script is syntactically valid, executable, requires PR_HEAD_SHA,
and forwards to the right CLI verb with the right arguments.

Intent: CONTRACT — v0.4.4 A4.3 (wiring only, post-K7)
Owner: software-engineer
"""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration]

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT = _REPO_ROOT / ".github" / "scripts" / "pr-verdict-check.sh"
_SHA_A = "a" * 40


def _fake_dadaia_path(tmp_path: Path, *, exit_code: int = 0) -> Path:
    """A PATH dir carrying a fake `dadaia` that records its argv and exits *exit_code*."""
    bin_dir = tmp_path / "fakebin"
    bin_dir.mkdir()
    fake = bin_dir / "dadaia"
    fake.write_text(
        f'#!/usr/bin/env bash\necho "$@" > "{tmp_path}/argv.txt"\nexit {exit_code}\n',
        encoding="utf-8",
    )
    fake.chmod(0o755)
    return bin_dir


def _run_script(tmp_path: Path, env_overrides: dict[str, str], *, exit_code: int = 0) -> str:
    bin_dir = _fake_dadaia_path(tmp_path, exit_code=exit_code)
    env = {"PATH": f"{bin_dir}:/usr/bin:/bin", **env_overrides}
    subprocess.run(["bash", str(_SCRIPT)], capture_output=True, text=True, env=env, check=False)
    return (tmp_path / "argv.txt").read_text(encoding="utf-8").strip()


def test_script_exists_and_is_executable() -> None:
    assert _SCRIPT.is_file(), f"expected script at {_SCRIPT}"
    if os.name != "nt":
        mode = _SCRIPT.stat().st_mode
        assert mode & stat.S_IXUSR, "script must be executable (chmod +x)"


def test_script_has_valid_bash_syntax() -> None:
    result = subprocess.run(["bash", "-n", str(_SCRIPT)], capture_output=True, text=True)
    assert result.returncode == 0, f"bash -n failed: {result.stderr}"


def test_missing_pr_head_sha_fails_before_calling_dadaia(tmp_path: Path) -> None:
    bin_dir = _fake_dadaia_path(tmp_path)
    result = subprocess.run(
        ["bash", str(_SCRIPT)],
        capture_output=True,
        text=True,
        env={"PATH": f"{bin_dir}:/usr/bin:/bin"},
    )
    assert result.returncode != 0
    assert not (tmp_path / "argv.txt").exists()


def test_forwards_head_sha_to_verdict_check(tmp_path: Path) -> None:
    argv = _run_script(tmp_path, {"PR_HEAD_SHA": _SHA_A})
    assert argv == f"ci verdict-check --head {_SHA_A}"


def test_forwards_release_id_when_set_and_not_none(tmp_path: Path) -> None:
    argv = _run_script(tmp_path, {"PR_HEAD_SHA": _SHA_A, "RELEASE_ID": "0.5.1"})
    assert argv == f"ci verdict-check --head {_SHA_A} --release-id 0.5.1"


def test_release_id_none_literal_is_never_forwarded(tmp_path: Path) -> None:
    argv = _run_script(tmp_path, {"PR_HEAD_SHA": _SHA_A, "RELEASE_ID": "none"})
    assert argv == f"ci verdict-check --head {_SHA_A}"


def test_script_exit_code_propagates_from_the_cli(tmp_path: Path) -> None:
    bin_dir = _fake_dadaia_path(tmp_path, exit_code=1)
    result = subprocess.run(
        ["bash", str(_SCRIPT)],
        capture_output=True,
        text=True,
        env={"PATH": f"{bin_dir}:/usr/bin:/bin", "PR_HEAD_SHA": _SHA_A},
    )
    assert result.returncode == 1
