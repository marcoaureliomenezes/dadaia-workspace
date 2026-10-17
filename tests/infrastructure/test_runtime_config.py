"""Kimi Code's managed ``[[hooks]]`` block (shape, replace-or-append upsert) and its five
user-level shims (sh syntax, fail-open outside a workspace). The block/allow replay runs in
tests/infrastructure/runtime_transforms/test_hook_wrappers.py.
"""

from __future__ import annotations

import shutil
import tomllib
from pathlib import Path

import pytest

from dadaia_workspace.core import platform
from dadaia_workspace.core.harness_registry import HARNESS_RECORDS
from dadaia_workspace.core.platform import Capabilities
from dadaia_workspace.infrastructure.runtime_config import (
    KIMI_BLOCK_BEGIN,
    KIMI_BLOCK_END,
    kimi_code_home,
    kimi_hooks_block,
    upsert_kimi_hooks_block,
)
from dadaia_workspace.infrastructure.runtime_transforms.hook_wrappers import (
    hook_wrapper_contents,
)
from tests.helpers.oslib import run, write_text

_HOME = Path("/tmp/kimi-home-test")
_SHIMS = hook_wrapper_contents(HARNESS_RECORDS["kimi-code"])


@pytest.mark.parametrize(
    ("env", "home"),
    [({}, Path.home() / ".kimi-code"), ({"KIMI_CODE_HOME": "/srv/kimi"}, Path("/srv/kimi"))],
)
def test_kimi_code_home(env: dict[str, str], home: Path) -> None:
    assert kimi_code_home(env) == home


def test_kimi_hooks_block_parses_as_toml_and_pins_rules() -> None:
    block = kimi_hooks_block(_HOME)
    assert block.startswith(KIMI_BLOCK_BEGIN + "\n")
    assert block.endswith(KIMI_BLOCK_END + "\n")

    parsed = tomllib.loads(block)
    hooks = parsed["hooks"]
    assert [h["event"] for h in hooks] == [
        "PreToolUse",
        "PostToolUse",
        "UserPromptSubmit",
        "PostCompact",
        "SessionStart",
    ]
    by_event = {h["event"]: h for h in hooks}
    assert "matcher" not in by_event["SessionStart"]
    assert by_event["PreToolUse"]["matcher"] == "^(Edit|Write)$"
    assert by_event["PostCompact"]["matcher"] == "manual|auto"
    assert "matcher" not in by_event["PostToolUse"]
    assert "matcher" not in by_event["UserPromptSubmit"]
    assert by_event["PreToolUse"]["command"] == "/tmp/kimi-home-test/hooks/dadaia-kimi-pre-gate.sh"
    assert by_event["PostCompact"]["command"] == (
        "/tmp/kimi-home-test/hooks/dadaia-kimi-post-compact.sh"
    )


@pytest.mark.parametrize("host", ["linux", "win32"])
@pytest.mark.parametrize("home", ["/tmp/kimi home", "/tmp/o'brien", "/tmp/kimi-home-test"])
def test_kimi_hook_command_is_the_kernels_spelling_of_the_wrapper_path(
    host: str, home: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("dadaia_workspace.core.platform.PLATFORM", Capabilities.detect(host))
    wrapper = f"{home}/hooks/dadaia-kimi-pre-gate.sh"
    spelled = platform.command(wrapper)
    # a head with no spelling on the host stays the raw path; an Agent action is never a command
    expected = wrapper if spelled.startswith("Agent action:") else spelled
    hooks = tomllib.loads(kimi_hooks_block(Path(home)))["hooks"]
    assert {h["event"]: h["command"] for h in hooks}["PreToolUse"] == expected


@pytest.mark.parametrize(
    "foreign", ["", 'default_model = "kimi-code/k3"\n\n[thinking]\nenabled = true\n']
)
def test_upsert_appends_once_after_foreign_config_as_valid_toml(foreign: str) -> None:
    block = kimi_hooks_block(_HOME)
    out = upsert_kimi_hooks_block(foreign, block)
    assert out.startswith(foreign) and out.endswith(block)
    assert upsert_kimi_hooks_block(out, block) == out
    assert len(tomllib.loads(out)["hooks"]) == 5


def test_upsert_replaces_between_markers_and_preserves_surroundings() -> None:
    stale = (
        'default_model = "k3"\n'
        + KIMI_BLOCK_BEGIN
        + '\n[[hooks]]\nevent = "Stale"\n'
        + KIMI_BLOCK_END
        + "\n\n[thinking]\nenabled = true\n"
    )
    block = kimi_hooks_block(_HOME)
    out = upsert_kimi_hooks_block(stale, block)
    assert 'event = "Stale"' not in out
    assert out.count(KIMI_BLOCK_BEGIN) == 1
    assert out.endswith("\n\n[thinking]\nenabled = true\n")
    assert out.startswith('default_model = "k3"\n')


def test_kimi_hook_shims_keys_and_prologue() -> None:
    assert set(_SHIMS) == {
        "dadaia-kimi-pre-gate.sh",
        "dadaia-kimi-post-gate.sh",
        "dadaia-kimi-ctx-inject.sh",
        "dadaia-kimi-post-compact.sh",
        "dadaia-kimi-doctor-expired.sh",
    }
    assert all(body.startswith("#!/usr/bin/env sh\n") for body in _SHIMS.values())


@pytest.mark.skipif(shutil.which("sh") is None, reason="POSIX sh unavailable")
@pytest.mark.parametrize("body", _SHIMS.values())
def test_kimi_hook_shims_are_valid_sh_syntax(body: str, tmp_path: Path) -> None:
    shim = tmp_path / "shim.sh"
    write_text(shim, body)
    run(["sh", "-n", str(shim)], check=True)


@pytest.mark.skipif(shutil.which("sh") is None, reason="POSIX sh unavailable")
def test_pre_gate_shim_fails_open_outside_dadaia_workspaces(tmp_path: Path) -> None:
    shim = tmp_path / "pre-gate.sh"
    write_text(shim, _SHIMS["dadaia-kimi-pre-gate.sh"])
    proc = run(["sh", str(shim)], input='{"tool_name": "Write"}', cwd=tmp_path)
    assert proc.returncode == 0
    assert proc.stderr == ""
