"""Runtime configuration generation regressions."""

from __future__ import annotations

from dadaia_workspace.infrastructure.runtime_config import codex_hook_wrapper_contents


def test_codex_hook_wrappers_disable_bytecode_writes() -> None:
    wrappers = codex_hook_wrapper_contents()

    assert wrappers
    for name, body in wrappers.items():
        assert 'exec "$PYTHON_BIN" -B -m ' in body, name
