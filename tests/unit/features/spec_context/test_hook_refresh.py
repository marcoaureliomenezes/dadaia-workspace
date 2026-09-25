"""Intent: CONTRACT — T-050 CI defect (HOOKS-DRIFT-1 after re-init upgrade): an installed
hook byte-identical to a previously shipped pre-push-ci-gate.sh is ours and is refreshed;
an operator's own hook stays untouched."""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.core import workspace_layout
from dadaia_workspace.core.template_history import load_shipped_hashes
from dadaia_workspace.features.spec_context.service import install_git_hooks

_SHIPPED = workspace_layout.public_scripts_dir() / "pre-push-ci-gate.sh"


def _hooks(tmp_path: Path, text: str) -> Path:
    hook = tmp_path / ".git" / "hooks" / "pre-push"
    hook.parent.mkdir(parents=True)
    hook.write_text(text, encoding="utf-8")
    return hook


def _history() -> set[str]:
    return load_shipped_hashes(workspace_layout.public_scripts_dir().parent / "templates")[
        "scripts/pre-push-ci-gate.sh"
    ]


def test_the_current_hook_is_recorded_as_shipped() -> None:
    import hashlib

    assert hashlib.sha256(_SHIPPED.read_bytes()).hexdigest() in _history()


def test_a_previously_shipped_hook_is_refreshed(tmp_path: Path, monkeypatch) -> None:
    old = "#!/bin/sh\n# an older shipped gate\n"
    import hashlib

    monkeypatch.setattr(
        "dadaia_workspace.features.spec_context.service.load_shipped_hashes",
        lambda _d: {"scripts/pre-push-ci-gate.sh": {hashlib.sha256(old.encode()).hexdigest()}},
    )
    hook = _hooks(tmp_path, old)
    assert install_git_hooks(tmp_path) == [hook]
    assert hook.read_bytes() == _SHIPPED.read_bytes()


def test_an_operator_hook_is_kept(tmp_path: Path) -> None:
    hook = _hooks(tmp_path, "#!/bin/sh\necho mine\n")
    assert install_git_hooks(tmp_path) == []
    assert hook.read_text(encoding="utf-8") == "#!/bin/sh\necho mine\n"
