"""v0.2.8 T2 — Kimi Code runtime-config generators (managed hook block + shims).

Pins the managed ``[[hooks]]`` TOML block shape (events, matchers, markers, absolute
commands), the replace-or-append upsert semantics, and the four workspace-agnostic shim
bodies — including a live ``sh`` replay of the pre-gate block/allow/fail-open contract
against a fake workspace venv.
"""

from __future__ import annotations

import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest

from dadaia_workspace.infrastructure.runtime_config import (
    KIMI_BLOCK_BEGIN,
    KIMI_BLOCK_END,
    kimi_code_home,
    kimi_hook_shims,
    kimi_hooks_block,
    upsert_kimi_hooks_block,
)

pytestmark = pytest.mark.unit

_HOME = Path("/tmp/kimi-home-test")


# ---------------------------------------------------------------------------
# kimi_code_home
# ---------------------------------------------------------------------------


def test_kimi_code_home_defaults_to_user_dot_dir() -> None:
    assert kimi_code_home({}) == Path.home() / ".kimi-code"


def test_kimi_code_home_honours_env_override() -> None:
    assert kimi_code_home({"KIMI_CODE_HOME": "/srv/kimi"}) == Path("/srv/kimi")


# ---------------------------------------------------------------------------
# kimi_hooks_block — exact managed TOML shape
# ---------------------------------------------------------------------------


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
    ]
    by_event = {h["event"]: h for h in hooks}
    assert by_event["PreToolUse"]["matcher"] == "^(Edit|Write|Bash)$"
    assert by_event["PostCompact"]["matcher"] == "manual|auto"
    assert "matcher" not in by_event["PostToolUse"]
    assert "matcher" not in by_event["UserPromptSubmit"]
    assert by_event["PreToolUse"]["command"] == "/tmp/kimi-home-test/hooks/dadaia-kimi-pre-gate.sh"
    assert by_event["PostCompact"]["command"] == (
        "/tmp/kimi-home-test/hooks/dadaia-kimi-post-compact.sh"
    )
    assert all(h["timeout"] == 10 for h in hooks)


# ---------------------------------------------------------------------------
# upsert_kimi_hooks_block — replace-or-append, foreign content preserved
# ---------------------------------------------------------------------------


def test_upsert_appends_to_empty_file() -> None:
    block = kimi_hooks_block(_HOME)
    assert upsert_kimi_hooks_block("", block) == block


def test_upsert_appends_after_foreign_config_untouched() -> None:
    foreign = 'default_model = "kimi-code/k3"\n\n[thinking]\nenabled = true\n'
    block = kimi_hooks_block(_HOME)
    out = upsert_kimi_hooks_block(foreign, block)
    assert out.startswith(foreign)
    assert out.endswith(block)


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


def test_upsert_is_idempotent() -> None:
    block = kimi_hooks_block(_HOME)
    once = upsert_kimi_hooks_block('default_model = "k3"\n', block)
    assert upsert_kimi_hooks_block(once, block) == once


def test_upsert_full_result_stays_valid_toml() -> None:
    foreign = 'default_model = "kimi-code/k3"\n'
    out = upsert_kimi_hooks_block(foreign, kimi_hooks_block(_HOME))
    parsed = tomllib.loads(out)
    assert parsed["default_model"] == "kimi-code/k3"
    assert len(parsed["hooks"]) == 4


# ---------------------------------------------------------------------------
# kimi_hook_shims — bodies and live sh contract
# ---------------------------------------------------------------------------


def test_kimi_hook_shims_keys_and_prologue() -> None:
    shims = kimi_hook_shims()
    assert set(shims) == {
        "dadaia-kimi-pre-gate.sh",
        "dadaia-kimi-post-gate.sh",
        "dadaia-kimi-ctx-inject.sh",
        "dadaia-kimi-post-compact.sh",
    }
    for body in shims.values():
        assert body.startswith("#!/usr/bin/env sh\n")
        assert ".dadaia/.venv/bin/python" in body
        assert "exit 0" in body


def test_kimi_hook_shims_module_wiring() -> None:
    shims = kimi_hook_shims()
    assert "dadaia_workspace.hooks.pre_gate" in shims["dadaia-kimi-pre-gate.sh"]
    assert "exit 2" in shims["dadaia-kimi-pre-gate.sh"]
    assert "dadaia_workspace.hooks.sdd_post_gate" in shims["dadaia-kimi-post-gate.sh"]
    assert "dadaia_workspace.hooks.ctx_inject" in shims["dadaia-kimi-ctx-inject.sh"]
    compact = shims["dadaia-kimi-post-compact.sh"]
    assert 'DADAIA_HOOK_EVENT="PostCompact"' in compact
    assert "dadaia_workspace.hooks.ctx_inject" in compact


@pytest.mark.skipif(shutil.which("sh") is None, reason="POSIX sh unavailable")
@pytest.mark.parametrize("body", kimi_hook_shims().values())
def test_kimi_hook_shims_are_valid_sh_syntax(body: str, tmp_path: Path) -> None:
    shim = tmp_path / "shim.sh"
    shim.write_text(body, encoding="utf-8")
    subprocess.run(["sh", "-n", str(shim)], check=True)


def _fake_workspace(tmp_path: Path, python_body: str) -> Path:
    """Create a fake dadaia workspace whose venv python is a stub script."""
    workspace = tmp_path / "ws"
    bin_dir = workspace / ".dadaia" / ".venv" / "bin"
    bin_dir.mkdir(parents=True)
    fake_python = bin_dir / "python"
    fake_python.write_text(python_body, encoding="utf-8")
    fake_python.chmod(0o755)
    return workspace


@pytest.mark.skipif(shutil.which("sh") is None, reason="POSIX sh unavailable")
def test_pre_gate_shim_blocks_with_reason_on_stderr(tmp_path: Path) -> None:
    workspace = _fake_workspace(
        tmp_path,
        '#!/usr/bin/env sh\ncat >/dev/null\nprintf \'{"decision": "block", "reason": "root law violated"}\\n\'\n',
    )
    shim = tmp_path / "pre-gate.sh"
    shim.write_text(kimi_hook_shims()["dadaia-kimi-pre-gate.sh"], encoding="utf-8")
    nested = workspace / "repos" / "x"
    nested.mkdir(parents=True)
    proc = subprocess.run(
        ["sh", str(shim)],
        input='{"tool_name": "Write", "session_id": "s1", "cwd": "' + str(nested) + '"}',
        cwd=nested,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2
    assert "root law violated" in proc.stderr


@pytest.mark.skipif(shutil.which("sh") is None, reason="POSIX sh unavailable")
def test_pre_gate_shim_allows_on_allow_envelope(tmp_path: Path) -> None:
    workspace = _fake_workspace(
        tmp_path,
        '#!/usr/bin/env sh\ncat >/dev/null\nprintf \'{"decision": "allow"}\\n\'\n',
    )
    shim = tmp_path / "pre-gate.sh"
    shim.write_text(kimi_hook_shims()["dadaia-kimi-pre-gate.sh"], encoding="utf-8")
    proc = subprocess.run(
        ["sh", str(shim)],
        input='{"tool_name": "Write", "session_id": "s1"}',
        cwd=workspace,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0


@pytest.mark.skipif(shutil.which("sh") is None, reason="POSIX sh unavailable")
def test_pre_gate_shim_fails_open_outside_dadaia_workspaces(tmp_path: Path) -> None:
    shim = tmp_path / "pre-gate.sh"
    shim.write_text(kimi_hook_shims()["dadaia-kimi-pre-gate.sh"], encoding="utf-8")
    proc = subprocess.run(
        ["sh", str(shim)],
        input='{"tool_name": "Write"}',
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert proc.stderr == ""


# ---------------------------------------------------------------------------
# upsert legacy adoption — bug kimi-install-duplicates-hooks-on-legacy-config
# ---------------------------------------------------------------------------

_LEGACY_UNMARKED_RULES = (
    '[[hooks]]\nevent = "PreToolUse"\nmatcher = "^(Edit|Write|Bash)$"\n'
    'command = "/home/u/.kimi-code/hooks/dadaia-kimi-pre-gate.sh"\ntimeout = 10\n\n'
    '[[hooks]]\nevent = "PostToolUse"\n'
    'command = "/home/u/.kimi-code/hooks/dadaia-kimi-post-gate.sh"\ntimeout = 10\n\n'
    '[[hooks]]\nevent = "UserPromptSubmit"\n'
    'command = "/home/u/.kimi-code/hooks/dadaia-kimi-ctx-inject.sh"\ntimeout = 10\n\n'
    '[[hooks]]\nevent = "PostCompact"\nmatcher = "manual|auto"\n'
    'command = "/home/u/.kimi-code/hooks/dadaia-kimi-post-compact.sh"\ntimeout = 10\n'
)


def test_upsert_adopts_legacy_unmarked_rules_instead_of_duplicating() -> None:
    """A pre-v0.2.8 config carries the 4 dadaia [[hooks]] rules WITHOUT the markers.
    The upsert must ADOPT them (strip, then append the managed block) — appending a
    second copy (4 -> 8 rules, every event double-registered) is the bug."""
    existing = 'default_model = "k3"\n\n' + _LEGACY_UNMARKED_RULES
    out = upsert_kimi_hooks_block(existing, kimi_hooks_block(_HOME))
    parsed = tomllib.loads(out)
    assert len(parsed["hooks"]) == 4, "legacy rules must be replaced, not duplicated"
    assert out.count(KIMI_BLOCK_BEGIN) == 1
    assert parsed["default_model"] == "k3"
    events = [h["event"] for h in parsed["hooks"]]
    assert events.count("PreToolUse") == 1
    assert out.count("dadaia-kimi-pre-gate.sh") == 1


def test_upsert_preserves_operator_rules_while_stripping_legacy() -> None:
    """An operator's own non-dadaia hook rule is content we never touch — it survives
    the legacy adoption byte-for-byte."""
    operator_rule = '[[hooks]]\nevent = "Notification"\ncommand = "terminal-notifier"\n'
    existing = 'default_model = "k3"\n\n' + _LEGACY_UNMARKED_RULES + "\n" + operator_rule
    out = upsert_kimi_hooks_block(existing, kimi_hooks_block(_HOME))
    parsed = tomllib.loads(out)
    assert len(parsed["hooks"]) == 5  # managed 4 + the operator's Notification rule
    assert 'command = "terminal-notifier"' in out


def test_upsert_repairs_stray_duplicates_outside_existing_markers() -> None:
    """A previously botched state (managed block AND a stray un-marked dadaia rule) is
    repaired to exactly one copy — strays outside the markers never survive."""
    stray = (
        '[[hooks]]\nevent = "PreToolUse"\n'
        'command = "/x/hooks/dadaia-kimi-pre-gate.sh"\ntimeout = 3\n'
    )
    botched = 'default_model = "k3"\n\n' + kimi_hooks_block(_HOME) + "\n" + stray
    out = upsert_kimi_hooks_block(botched, kimi_hooks_block(_HOME))
    assert out.count("dadaia-kimi-pre-gate.sh") == 1
    assert out.count(KIMI_BLOCK_BEGIN) == 1
    parsed = tomllib.loads(out)
    assert len(parsed["hooks"]) == 4
