"""Bug ``mypy-strict-cache-dir-created-without-cache-dir-env-override``.

Intent: CONTRACT -- bug mypy-strict-cache-dir-created-without-cache-dir-env-override.

INTEGRATION / SLOW (dadaia-test-stewardship declaration: this is the one test in the
suite that actually EXECUTES mypy against the real, checked-in ``[tool.mypy]`` config,
rather than asserting on argv shape -- ``tests/unit/features/ci_preflight/
test_no_pollution.py`` already pins the ``dadaia ci preflight`` mypy check's argv
WITHOUT running mypy; this test proves the OTHER documented path -- the PR-template
checklist's local ``mypy --strict`` invocation -- is honest about repo hygiene, by
literally running mypy per what that file currently documents).

``pyproject.toml``'s ``[tool.mypy]`` comment used to claim ``incremental = false``
alone keeps ``.mypy_cache/`` out of the repo tree. False under mypy 2.x: mypy writes
the cache dir (``CACHEDIR.TAG`` + a version subdir) at its resolved ``cache_dir``
regardless of ``incremental``. The fix is documentation, not mypy config (a portable,
crash-proof static ``cache_dir`` does not exist -- ``$MYPY_CONFIG_FILE_DIR/../..``
assumes this checkout's nesting depth under a dadaia workspace root, and an
unwritable resolved target makes mypy crash with an INTERNAL ERROR, verified
manually against ``/root/...``): ``.github/PULL_REQUEST_TEMPLATE.md``'s mypy
checklist line must require the ``MYPY_CACHE_DIR`` redirect mypy itself honours (the
same one ``ci.yml`` already uses), so this test extracts THAT line's literal command
and proves it (a) never pollutes an isolated checkout copying the repo's real
``[tool.mypy]`` config, and (b) type-checks cleanly. Before the doc fix the extracted
line carried no ``MYPY_CACHE_DIR`` clause, so the exact same procedure ran the bare
invocation and failed on the ``.mypy_cache`` assertion below -- the real bug, not a
scaffold.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.slow]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PR_TEMPLATE = _REPO_ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md"

_MINI_MODULE = "def add(a: int, b: int) -> int:\n    return a + b\n"


def _documented_mypy_checklist_line() -> str:
    """The PR-template checklist line documenting the local ``mypy --strict`` command."""
    text = _PR_TEMPLATE.read_text(encoding="utf-8")
    for line in text.splitlines():
        if "mypy --strict" in line:
            return line
    raise AssertionError(
        f"{_PR_TEMPLATE}: no checklist line documents `mypy --strict` -- "
        "this test's whole premise (extract and literally run the documented "
        "local invocation) is stale; update the marker string above."
    )


def _mypy_bin() -> Path:
    """The workspace-venv ``mypy`` sibling of the interpreter running this test."""
    candidate = Path(sys.executable).parent / "mypy"
    if not candidate.is_file():
        pytest.skip(f"mypy not installed alongside {sys.executable}")
    return candidate


def test_documented_local_mypy_invocation_does_not_pollute_repo_tree(tmp_path: Path) -> None:
    """Literally run the PR-template-documented local invocation; assert no pollution.

    Isolated to a ``tmp_path`` copy of the real ``pyproject.toml`` + one minimal typed
    module -- the real repo checkout is never touched, so this can never leave a stray
    ``.mypy_cache/`` at the actual repo root even mid-run.
    """
    line = _documented_mypy_checklist_line()

    isolated = tmp_path / "isolated-checkout"
    isolated.mkdir()
    (isolated / "pyproject.toml").write_text(
        (_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (isolated / "mini.py").write_text(_MINI_MODULE, encoding="utf-8")

    env = dict(os.environ)
    env.pop("MYPY_CACHE_DIR", None)
    if "MYPY_CACHE_DIR" in line:
        # The documented command redirects the cache -- reproduce that redirect at a
        # location outside the isolated checkout, exactly as the doc's own
        # `$(mktemp -d)` would.
        env["MYPY_CACHE_DIR"] = str(tmp_path / "mypy-cache-out")

    result = subprocess.run(
        [str(_mypy_bin()), "--strict", "--config-file", "pyproject.toml", "mini.py"],
        cwd=isolated,
        env=env,
        capture_output=True,
        text=True,
        timeout=45,
    )

    assert result.returncode == 0, (
        f"documented command failed against the real [tool.mypy] config: "
        f"{result.stdout}\n{result.stderr}"
    )
    assert not (isolated / ".mypy_cache").exists(), (
        f"the PR-template-documented local mypy invocation ({line!r}) left "
        f".mypy_cache/ inside the checkout -- it must redirect via MYPY_CACHE_DIR "
        "(pyproject.toml's [tool.mypy] comment names the same requirement)."
    )


def test_pyproject_mypy_comment_no_longer_claims_incremental_false_suffices() -> None:
    """Static regression lock on the false claim itself (bug's root cause)."""
    text = (_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r"\[tool\.mypy\].*?(?=\n\[)", text, re.DOTALL)
    assert match, "pyproject.toml: [tool.mypy] section not found"
    section = match.group(0)
    assert "already disables the mypy cache" not in section, (
        "pyproject.toml [tool.mypy]: the false claim that `incremental = false` alone "
        "keeps .mypy_cache/ out of the repo tree is back -- mypy 2.x writes the cache "
        "dir regardless (bug mypy-strict-cache-dir-created-without-cache-dir-env-override)."
    )
    assert "MYPY_CACHE_DIR" in section, (
        "pyproject.toml [tool.mypy]: the comment must name MYPY_CACHE_DIR as the "
        "required redirect for a bare local `mypy --strict` invocation."
    )
