"""T-050 CI defect (HOOKS-DRIFT-1 after re-init upgrade): an installed
hook byte-identical to a previously shipped pre-push-ci-gate.sh is ours and is refreshed;
an operator's own hook (review M3: undecodable included) stays untouched."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest

from dadaia_workspace.core import workspace_layout
from dadaia_workspace.core.template_history import load_shipped_hashes
from dadaia_workspace.features.spec_context.service import install_git_hooks

_SHIPPED = workspace_layout.public_scripts_dir() / "pre-push-ci-gate.sh"
_OLD = b"#!/bin/sh\n# an older shipped gate\n"


def test_the_current_hook_is_recorded_as_shipped() -> None:
    history = load_shipped_hashes(workspace_layout.public_scripts_dir().parent / "templates")
    assert (
        hashlib.sha256(_SHIPPED.read_bytes()).hexdigest() in history["scripts/pre-push-ci-gate.sh"]
    )


# fmt: off
@pytest.mark.parametrize(("installed", "refreshed"), [
    pytest.param(_OLD.replace(b"\n", b"\r\n"), True, id="previously-shipped-crlf-checkout-refreshed"),
    pytest.param(b"#!/bin/sh\necho mine\n", False, id="operator-hook-kept"),
    pytest.param(b"#!/bin/sh\necho caf\xe9\n", False, id="M3-undecodable-operator-hook-kept"),
])
# fmt: on
def test_install_refreshes_only_a_hook_we_shipped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, installed: bytes, refreshed: bool
) -> None:
    monkeypatch.setattr(
        "dadaia_workspace.core.template_history.load_shipped_hashes",
        lambda _d: {"scripts/pre-push-ci-gate.sh": {hashlib.sha256(_OLD).hexdigest()}},
    )
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    hook = tmp_path / ".git" / "hooks" / "pre-push"
    hook.write_bytes(installed)
    assert install_git_hooks(tmp_path) == ([hook] if refreshed else [])
    assert hook.read_bytes() == (_SHIPPED.read_bytes() if refreshed else installed)
