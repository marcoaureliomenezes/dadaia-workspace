"""CI workflow hygiene contract (v0.1.61 FR6 CI-1/CI-2; amended T-65-14 CI-fix).

Pins three invariants over the GitHub Actions workflow YAMLs:

  (a) CI-1 — the legacy ``primary_context.json`` bootstrap write is gone: zero
      occurrences of that filename anywhere under ``.github/workflows/``. The only
      production references to the file are the v1→v2 migration *deleter*
      (``features/migrate/state_v2.py``); nothing requires it to exist.
  (b) CI-2 — neither ``ci.yml`` nor ``release.yml`` overrides
      ``PANEL_WEB_SERVER_COMMAND``. The hermetic bootstrap (T-65-14 CI-fix amendment:
      the v0.1.61 shared script was retired because it wrote ``spec_contexts.json``
      directly at the checkout root, making ``workspace_root`` == the source repo
      root — refused by the ``_is_source_repo_root`` production guard on any
      re-rendering PUT) now lives ONLY behind ``playwright.config.ts``'s default
      ``webServer.command`` (``tests/e2e/panel/run-panel-e2e-server.sh``). Since
      there is exactly one playwright config, an env override in either workflow
      would be the sole way the two legs could diverge again — so its absence in
      both is the anti-duplication invariant now.
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
_BOOTSTRAP_SCRIPT = _REPO_ROOT / "tests" / "e2e" / "panel" / "run-panel-e2e-server.sh"
_SCRIPT_REF = "tests/e2e/panel/run-panel-e2e-server.sh"

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
def test_workflows_do_not_override_web_server_command(workflow: str) -> None:
    """CI-2 (amended): neither e2e-panel leg overrides PANEL_WEB_SERVER_COMMAND.

    playwright.config.ts's own default (the hermetic run-panel-e2e-server.sh) is the
    sole source of truth for how the panel webServer is bootstrapped and launched; an
    override in either workflow YAML would be the only way the two legs could
    reintroduce a hand-synced-copy divergence (the CI-2 audit finding this contract
    guards).
    """
    text = (_WORKFLOWS_DIR / workflow).read_text(encoding="utf-8")
    assert "PANEL_WEB_SERVER_COMMAND" not in text, (
        f"{workflow} overrides PANEL_WEB_SERVER_COMMAND — this bypasses the shared "
        f"hermetic bootstrap ({_SCRIPT_REF}) and reopens the CI-2 divergence risk"
    )


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
