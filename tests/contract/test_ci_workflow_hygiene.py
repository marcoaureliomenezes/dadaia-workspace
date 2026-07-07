"""CI workflow hygiene contract (v0.1.61 FR6 CI-1/CI-2).

Pins three invariants over the GitHub Actions workflow YAMLs:

  (a) CI-1 — the legacy ``primary_context.json`` bootstrap write is gone: zero
      occurrences of that filename anywhere under ``.github/workflows/``. The only
      production references to the file are the v1→v2 migration *deleter*
      (``features/migrate/state_v2.py``); nothing requires it to exist.
  (b) CI-2 — both ``ci.yml`` and ``release.yml`` invoke the shared bootstrap script
      ``.github/scripts/bootstrap-panel-ws.sh`` instead of carrying the block inline.
  (c) CI-2 — no inline duplicate of the bootstrap body remains: the distinctive
      bootstrap-body line (``Memory atoms verified OK``) appears 0 times in the
      workflow YAMLs and exactly once in the shared script (which must exist and be
      executable).

AC-9(c) mutation-sanity: restoring the ``primary_context.json`` heredoc in ``ci.yml``
makes assertion (a) FAIL.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

_REPO_ROOT = Path(__file__).resolve().parents[2]
_WORKFLOWS_DIR = _REPO_ROOT / ".github" / "workflows"
_BOOTSTRAP_SCRIPT = _REPO_ROOT / ".github" / "scripts" / "bootstrap-panel-ws.sh"
_SCRIPT_REF = ".github/scripts/bootstrap-panel-ws.sh"

# A line unique to the bootstrap block body — present exactly once in the shared
# script, and never inline in any workflow YAML. (``spec_contexts.json`` is NOT
# usable here: release.yml's smoke job legitimately asserts on that filename.)
_DISCRIMINATOR = "Memory atoms verified OK"


def _workflow_files() -> list[Path]:
    files = sorted(_WORKFLOWS_DIR.glob("*.yml")) + sorted(_WORKFLOWS_DIR.glob("*.yaml"))
    assert files, f"no workflow files found under {_WORKFLOWS_DIR}"
    return files


def test_no_primary_context_json_in_workflows() -> None:
    """CI-1: the legacy primary_context.json bootstrap write must be gone."""
    offenders = [
        f.name for f in _workflow_files() if "primary_context.json" in f.read_text(encoding="utf-8")
    ]
    assert offenders == [], (
        f"legacy primary_context.json reference(s) found in workflows: {offenders} — "
        "the file is legacy v1 state; only the v1→v2 migration deleter may mention it"
    )


@pytest.mark.parametrize("workflow", ["ci.yml", "release.yml"])
def test_workflows_call_shared_bootstrap_script(workflow: str) -> None:
    """CI-2: both e2e-panel legs must call the shared bootstrap script."""
    text = (_WORKFLOWS_DIR / workflow).read_text(encoding="utf-8")
    assert _SCRIPT_REF in text, f"{workflow} does not reference {_SCRIPT_REF}"


def test_no_inline_bootstrap_body_duplicate() -> None:
    """CI-2: the bootstrap body lives only in the shared script (exactly once)."""
    for f in _workflow_files():
        occurrences = f.read_text(encoding="utf-8").count(_DISCRIMINATOR)
        assert occurrences == 0, (
            f"{f.name} carries {occurrences} inline occurrence(s) of the bootstrap "
            f"body discriminator {_DISCRIMINATOR!r} — the body belongs in {_SCRIPT_REF}"
        )
    assert _BOOTSTRAP_SCRIPT.is_file(), f"{_SCRIPT_REF} is missing"
    assert _BOOTSTRAP_SCRIPT.read_text(encoding="utf-8").count(_DISCRIMINATOR) == 1


def test_bootstrap_script_is_executable() -> None:
    """The shared script must carry the executable bit (skipped on Windows)."""
    if os.name == "nt":
        pytest.skip("executable bit not meaningful on Windows")
    assert _BOOTSTRAP_SCRIPT.is_file(), f"{_SCRIPT_REF} is missing"
    mode = _BOOTSTRAP_SCRIPT.stat().st_mode
    assert mode & stat.S_IXUSR, f"{_SCRIPT_REF} is not executable"
