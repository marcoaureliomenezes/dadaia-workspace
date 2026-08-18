"""Bug ``ruff-0-16-2-markdown-python-fence-format-drift``.

Intent: SENTINEL -- the one integration test of this seam: the exact
``poetry.lock``-pinned ``ruff`` binary running ``ruff format --check`` over the real
tracked repo tree must be green. Every other ruff-format test in this suite
(``tests/unit/features/ci_preflight/test_no_pollution.py``) pins argv shape only --
``--no-cache`` is present -- without ever invoking the real formatter, so a version
drift between the shared workspace venv's cached ruff build and the pin this repo's
``pyproject.toml``/``poetry.lock`` actually declares was invisible to the whole suite.
That is exactly how this bug shipped silent: the dependency bump commit ``dad9eab9``
(ruff 0.15.20 -> 0.16.2) changed the lock, but the shared local venv used for every
prior gate run stayed on the stale 0.15.20 build, so ``ruff format --check`` kept
reporting green locally while the CI-installed pin (and any fresh venv rebuild) would
already fail on 5 pre-existing ``specs/_archive/**`` Markdown files whose fenced Python
code-block comment spacing 0.16.2 reformats by default.

This test runs the REAL venv-sibling ``ruff`` -- whatever version is actually
installed, exactly what the pre-push preflight and CI both execute -- against this
repo's real, checked-out tree. It is deliberately NOT parameterized by version: its
job is to catch drift, not to assert a specific ruff release's behavior.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

_REPO_ROOT = Path(__file__).resolve().parents[2]
_TIMEOUT_S = 60


def _ruff_bin() -> Path:
    """The workspace-venv ``ruff`` sibling of the interpreter running this test --
    the same resolution seam ``dadaia ci preflight`` and the pre-push gate use."""
    candidate = Path(sys.executable).parent / "ruff"
    if not candidate.is_file():
        pytest.skip(f"ruff not installed alongside {sys.executable}")
    return candidate


def test_ruff_format_check_is_green_over_the_real_tracked_tree() -> None:
    """The exact command the pre-push preflight and CI run (``ruff format --check
    --no-cache .``) must exit 0 against this repo's real, checked-out working tree --
    not against argv shape, not against a synthetic fixture. A future FROZEN-archive
    Markdown fence reformat drift (or any other formatter-reach regression) fails HERE
    before it ever reaches the pre-push chokepoint."""
    result = subprocess.run(
        [str(_ruff_bin()), "format", "--check", "--no-cache", "."],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=_TIMEOUT_S,
    )

    assert result.returncode == 0, (
        "ruff format --check --no-cache . is not green against the real installed "
        f"ruff ({result.args[0]}) over this repo's tracked tree -- bug "
        "ruff-0-16-2-markdown-python-fence-format-drift (or a regression of it) is "
        f"back:\n{result.stdout}\n{result.stderr}"
    )
