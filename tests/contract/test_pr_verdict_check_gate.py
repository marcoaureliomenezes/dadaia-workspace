"""V20 — the CI verdict-evidence gate's seven arms (SPEC v0.5.0 A1.8/V20, T-050-06A(b)).

Intent: CONTRACT — SPEC v0.5.0 A1.8, A1.10, AS-15, §9.2 SEC-R1/SEC-R2, V20.

Exercises ``.github/scripts/pr-verdict-check.sh`` against real synthetic git-repo
fixtures — real ``git`` commits, real ``bash``, real ``python3`` derivation from
``dadaia_workspace.core.specs_version`` (via a controllable ``python3`` PATH shim so
arm 7's derivation-failure case is deterministic without depending on ambient
venv/site-packages state). Never a mock of ``git`` or ``jq``.

Each arm asserts the SPEC-stated outcome (A1.8):
  1. live ``verdicts/`` root -> PASS
  2. per-area archive ``verdicts/`` root -> PASS (the arm that was broken before this task)
  3. ``_ideas/`` root -> fails closed (never an evidence root)
  4. narrowing matrix: bare id accepted, v-prefixed archived id still resolves,
     traversal/non-canon tokens refused before interpolation
  5. no qualifying handoff anywhere -> exit non-zero
  6. a non-verdict path in the intervening diff still disqualifies coverage
  7. derivation failure -> exit non-zero, no fallback glob
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO_ROOT / ".github" / "scripts" / "pr-verdict-check.sh"
_REAL_PYTHON3 = shutil.which("python3")


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True)


def _head(repo: Path) -> str:
    return _git(repo, "rev-parse", "HEAD").stdout.strip()


def _init_repo(repo: Path) -> str:
    """Create a real git repo with one root commit; return its sha."""
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "Test")
    (repo / "README.md").write_text("root\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-q", "-m", "root")
    return _head(repo)


def _commit_all(repo: Path, message: str) -> str:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)
    return _head(repo)


def _write_verdict(
    repo: Path,
    relpath: str,
    *,
    reviewed_sha: str,
    agent: str = "security-reviewer",
    verdict: str = "APPROVED",
) -> None:
    path = repo / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"agent": agent, "verdict": verdict, "metrics": {"commit_sha": reviewed_sha}}),
        encoding="utf-8",
    )


def _make_shim_bin(tmp_path: Path, *, broken: bool) -> Path:
    """A controllable ``python3`` PATH shim.

    ``broken=False`` execs the real interpreter (the derivation genuinely runs,
    exactly as CI's bare ``python3`` does — proven separately in
    :func:`test_derivation_feasible_on_bare_checkout_cwd_relative_import` to work via
    cwd-relative ``sys.path``, no install needed). ``broken=True`` always fails,
    deterministically proving arm 7's fail-closed path without depending on ambient
    venv/site-packages state.
    """
    bin_dir = tmp_path / "shim-bin"
    bin_dir.mkdir(exist_ok=True)
    shim = bin_dir / "python3"
    if broken:
        shim.write_text("#!/usr/bin/env bash\necho 'simulated interpreter failure' >&2\nexit 1\n")
    else:
        assert _REAL_PYTHON3 is not None, "no python3 on PATH — cannot build the shim"
        shim.write_text(f'#!/usr/bin/env bash\nexec "{_REAL_PYTHON3}" "$@"\n')
    mode = shim.stat().st_mode
    shim.chmod(mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return bin_dir


def _run_gate(
    repo: Path,
    tmp_path: Path,
    *,
    pr_head_sha: str,
    release_id: str | None = None,
    broken_python: bool = False,
) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    shim_bin = _make_shim_bin(tmp_path, broken=broken_python)
    env["PATH"] = f"{shim_bin}{os.pathsep}{env.get('PATH', '')}"
    env["PR_HEAD_SHA"] = pr_head_sha
    if release_id is not None:
        env["RELEASE_ID"] = release_id
    else:
        env.pop("RELEASE_ID", None)
    return subprocess.run(["bash", str(_SCRIPT)], cwd=repo, env=env, capture_output=True, text=True)


def _output(result: subprocess.CompletedProcess[str]) -> str:
    return result.stdout + result.stderr


# ---------------------------------------------------------------------------
# Feasibility precondition the script's own header comment claims (SEC-R2 context):
# the derivation must work on a bare checkout with no `pip install`, purely via the
# cwd-relative sys.path Python adds for `-c` invocations.
# ---------------------------------------------------------------------------


def test_derivation_feasible_on_bare_checkout_cwd_relative_import() -> None:
    """`python3 -S` (no site-packages — i.e. no editable install in play) still
    imports the canon from the repo root, purely via cwd-relative sys.path. Proves
    the gate's own claim: no `setup-python`, no install step, needed on CI."""
    result = subprocess.run(
        [
            "python3",
            "-S",
            "-c",
            "import dadaia_workspace.core.specs_version as s; print(s.CANONICAL_SPECS_VERSION)",
        ],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().isdigit()


# ---------------------------------------------------------------------------
# Arm 1 — live verdicts/ root -> PASS
# ---------------------------------------------------------------------------


def test_arm1_live_verdicts_root_passes(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    reviewed = _init_repo(repo)
    _write_verdict(
        repo, f"specs/releases/0.5.0/verdicts/{reviewed}.handoff.json", reviewed_sha=reviewed
    )
    head = _commit_all(repo, "add verdict")

    result = _run_gate(repo, tmp_path, pr_head_sha=head)

    assert result.returncode == 0, _output(result)
    assert "PASS" in result.stdout


# ---------------------------------------------------------------------------
# Arm 2 — the per-area archive root -> PASS (the arm broken before T-050-06A)
# ---------------------------------------------------------------------------


def test_arm2_per_area_archive_root_passes(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    reviewed = _init_repo(repo)
    _write_verdict(
        repo,
        f"specs/releases/_archive/0.4.4/verdicts/{reviewed}.handoff.json",
        reviewed_sha=reviewed,
    )
    head = _commit_all(repo, "add archived verdict")

    result = _run_gate(repo, tmp_path, pr_head_sha=head)

    assert result.returncode == 0, _output(result)
    assert "PASS" in result.stdout


# ---------------------------------------------------------------------------
# Arm 3 — _ideas/ is never an evidence root -> fails closed
# ---------------------------------------------------------------------------


def test_arm3_ideas_root_refused_fails_closed(tmp_path: Path) -> None:
    """AS-15/A6.3: `_ideas/<id>/verdicts/` (the real on-disk shape — id NESTED under
    _ideas, matching FR1's `releases/_ideas/{version}/`) never matches either of the
    two canon-derived root templates (each has exactly one `{glob}` segment) — the
    refusal is structural, by construction, not a special-cased string check."""
    repo = tmp_path / "repo"
    reviewed = _init_repo(repo)
    _write_verdict(
        repo,
        f"specs/releases/_ideas/0.5.0/verdicts/{reviewed}.handoff.json",
        reviewed_sha=reviewed,
    )
    head = _commit_all(repo, "add ideas verdict — must never qualify")

    result = _run_gate(repo, tmp_path, pr_head_sha=head)

    assert result.returncode != 0
    assert "no candidate verdict files found" in _output(result)


# ---------------------------------------------------------------------------
# Arm 4 — narrowing + refusal matrix
# ---------------------------------------------------------------------------


def test_arm4_bare_id_narrows_to_live_root(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    reviewed = _init_repo(repo)
    _write_verdict(
        repo, f"specs/releases/0.5.0/verdicts/{reviewed}.handoff.json", reviewed_sha=reviewed
    )
    head = _commit_all(repo, "add live verdict")

    result = _run_gate(repo, tmp_path, pr_head_sha=head, release_id="0.5.0")

    assert result.returncode == 0, _output(result)


def test_arm4_v_prefixed_id_still_resolves_the_archive_root(tmp_path: Path) -> None:
    """AS-13: a `v`-prefixed id is the retired axis — it must still resolve an
    EXISTING archived directory even though it can never be minted."""
    repo = tmp_path / "repo"
    reviewed = _init_repo(repo)
    _write_verdict(
        repo,
        f"specs/releases/_archive/v0.4.4/verdicts/{reviewed}.handoff.json",
        reviewed_sha=reviewed,
    )
    head = _commit_all(repo, "add archived verdict")

    result = _run_gate(repo, tmp_path, pr_head_sha=head, release_id="v0.4.4")

    assert result.returncode == 0, _output(result)


@pytest.mark.parametrize(
    "bad_release_id",
    ["../etc", "_ideas", "_archive", "0.1", "not-a-version", "v0.1.2.3"],
)
def test_arm4_traversal_and_non_canon_tokens_refused_before_interpolation(
    tmp_path: Path, bad_release_id: str
) -> None:
    repo = tmp_path / "repo"
    reviewed = _init_repo(repo)
    _write_verdict(
        repo, f"specs/releases/0.5.0/verdicts/{reviewed}.handoff.json", reviewed_sha=reviewed
    )
    head = _commit_all(repo, "add live verdict")

    result = _run_gate(repo, tmp_path, pr_head_sha=head, release_id=bad_release_id)

    assert result.returncode != 0
    assert "does not match the canon-derived release-id pattern" in _output(result)
    # Refused BEFORE interpolation: no traversal attempt ever reaches git/the filesystem.
    assert "fatal:" not in _output(result)


# ---------------------------------------------------------------------------
# Arm 5 — no qualifying handoff anywhere -> exit non-zero
# ---------------------------------------------------------------------------


def test_arm5_no_qualifying_handoff_exits_nonzero(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    head = _init_repo(repo)

    result = _run_gate(repo, tmp_path, pr_head_sha=head)

    assert result.returncode != 0
    assert "no candidate verdict files found" in _output(result)


# ---------------------------------------------------------------------------
# Arm 6 — a non-verdict path in the intervening diff still disqualifies coverage
# ---------------------------------------------------------------------------


def test_arm6_nonverdict_path_in_diff_disqualifies_coverage(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    reviewed = _init_repo(repo)
    _write_verdict(
        repo, f"specs/releases/0.5.0/verdicts/{reviewed}.handoff.json", reviewed_sha=reviewed
    )
    _commit_all(repo, "add verdict")
    (repo / "prod.py").write_text("x = 1\n", encoding="utf-8")
    head = _commit_all(repo, "unrelated production change after review")

    result = _run_gate(repo, tmp_path, pr_head_sha=head)

    assert result.returncode != 0
    assert "does not cover PR head" in _output(result)
    assert "prod.py" in _output(result)


def test_arm6_gate_own_offender_allowlist_line_still_disqualifies(tmp_path: Path) -> None:
    """A1.8 arm 6's explicit named case: a change to the gate script's OWN
    offender-allowlist line, landed after the review, must still disqualify — a
    derivation touching the allowlist can never silently un-gate the check."""
    repo = tmp_path / "repo"
    reviewed = _init_repo(repo)
    _write_verdict(
        repo, f"specs/releases/0.5.0/verdicts/{reviewed}.handoff.json", reviewed_sha=reviewed
    )
    _commit_all(repo, "add verdict")
    scripts_dir = repo / ".github" / "scripts"
    scripts_dir.mkdir(parents=True)
    (scripts_dir / "pr-verdict-check.sh").write_text("# a hypothetical gate edit\n")
    head = _commit_all(repo, "touch the gate's own offender-allowlist line")

    result = _run_gate(repo, tmp_path, pr_head_sha=head)

    assert result.returncode != 0
    assert "does not cover PR head" in _output(result)


# ---------------------------------------------------------------------------
# Arm 7 — derivation failure -> exit non-zero, no fallback glob
# ---------------------------------------------------------------------------


def test_arm7_derivation_failure_exits_nonzero_no_fallback(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    reviewed = _init_repo(repo)
    _write_verdict(
        repo, f"specs/releases/0.5.0/verdicts/{reviewed}.handoff.json", reviewed_sha=reviewed
    )
    head = _commit_all(repo, "add verdict — the derivation must still fail before reading it")

    result = _run_gate(repo, tmp_path, pr_head_sha=head, broken_python=True)

    assert result.returncode != 0
    assert "could not derive the release-id pattern" in _output(result)
    # No fallback: the verdict that WOULD have qualified is never even mentioned.
    assert "PASS" not in result.stdout
