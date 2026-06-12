"""Unit tests for the venv-guard PreToolUse policy (FR-W3-01, ADR-G4, T-014-12).

ADR-G4 narrowness: a fixed leading-token check on the FIRST command token only — NO
general shell parsing. It blocks `dadaia`, `pip`/`pip3`, and `python -m dadaia_workspace`
invocations NOT rooted in `.dadaia/.venv/bin/` (or the workspace-absolute equivalent /
``$DADAIA_BIN``), emitting a block message that contains the corrected command. pytest,
ruff, and mypy are explicitly NOT matched. The false-block law (ADR-G1) requires that
quoted strings, in-repo paths like ``repos/x/pip.py``, and another venv's explicit bin
path are never blocked — covered by the negative matrix below.
"""

from __future__ import annotations

import pytest

from dadaia_workspace.hooks import venv_guard


def _bash(command: str) -> dict[str, object]:
    return {"tool_name": "Bash", "tool_input": {"command": command}}


# ----------------------------------------------------------------------------
# BLOCK matrix — bare workspace tools not rooted in the venv bin.
# ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "command",
    [
        "dadaia doctor",
        "dadaia context show --json",
        "pip install foo",
        "pip3 install foo",
        "python -m dadaia_workspace",
        "python3 -m dadaia_workspace",
        "python -m dadaia_workspace.cli.main doctor",
    ],
)
def test_blocks_bare_workspace_invocation(command: str) -> None:
    reason = venv_guard.evaluate_payload(_bash(command))
    assert reason is not None, f"expected block for {command!r}"
    # Block message must contain the corrected, venv-rooted invocation.
    assert ".dadaia/.venv/bin/" in reason


def test_block_message_contains_corrected_command() -> None:
    reason = venv_guard.evaluate_payload(_bash("pip install foo"))
    assert reason is not None
    assert ".dadaia/.venv/bin/pip install foo" in reason


def test_block_message_for_dadaia_corrects_to_venv_dadaia() -> None:
    reason = venv_guard.evaluate_payload(_bash("dadaia doctor"))
    assert reason is not None
    assert ".dadaia/.venv/bin/dadaia doctor" in reason


def test_block_message_for_python_module_corrects_to_venv_python() -> None:
    reason = venv_guard.evaluate_payload(_bash("python -m dadaia_workspace"))
    assert reason is not None
    assert ".dadaia/.venv/bin/python -m dadaia_workspace" in reason


# ----------------------------------------------------------------------------
# ALLOW matrix — venv-rooted / overridden / out-of-scope tools.
# ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "command",
    [
        # Venv-rooted (relative) — the canonical correct form.
        ".dadaia/.venv/bin/dadaia doctor",
        ".dadaia/.venv/bin/pip install foo",
        ".dadaia/.venv/bin/python -m dadaia_workspace",
        # Workspace-absolute venv equivalent.
        "/home/op/ws/.dadaia/.venv/bin/dadaia doctor",
        "/home/op/ws/.dadaia/.venv/bin/pip install foo",
        # $DADAIA_BIN override.
        "$DADAIA_BIN doctor",
        "${DADAIA_BIN} doctor",
    ],
)
def test_allows_venv_rooted_or_overridden(command: str) -> None:
    assert venv_guard.evaluate_payload(_bash(command)) is None


@pytest.mark.parametrize(
    "command",
    [
        # ADR-G4 explicit exclusions — never matched.
        "pytest -p no:cacheprovider",
        "ruff check .",
        "ruff format --check",
        "mypy --strict dadaia_workspace",
        "python -m pytest",
        "python -m ruff check",
        # Unrelated commands.
        "ls -la",
        "git status",
        "python script.py",
        "python -m http.server",
    ],
)
def test_allows_unmatched_commands(command: str) -> None:
    assert venv_guard.evaluate_payload(_bash(command)) is None


# ----------------------------------------------------------------------------
# FALSE-BLOCK law (ADR-G1) — quoted strings, in-repo paths, foreign venv bins.
# ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "command",
    [
        # Quoted strings that merely CONTAIN the words must not block.
        'echo "run dadaia doctor"',
        "echo 'pip install foo'",
        'grep -r "pip install" repos/',
        # In-repo paths ending in the tool name are not the leading token.
        "cat repos/x/pip.py",
        "python repos/x/pip.py",
        "vim repos/dadaia-workspace/dadaia_workspace/cli/main.py",
        # Another venv's explicit bin path (rooted, just not ours) — out of scope.
        "repos/other/.venv/bin/pip install foo",
        "/opt/otherproj/.venv/bin/pip install foo",
        # A path that merely has 'pip' or 'dadaia' as a substring.
        "./scripts/pip-helper.sh",
        "./dadaia-wrapper.sh doctor",
    ],
)
def test_no_false_block(command: str) -> None:
    assert venv_guard.evaluate_payload(_bash(command)) is None


# ----------------------------------------------------------------------------
# Non-Bash and malformed payloads fail open (ALLOW).
# ----------------------------------------------------------------------------


def test_non_bash_tool_is_ignored() -> None:
    payload = {"tool_name": "Edit", "tool_input": {"command": "pip install foo"}}
    assert venv_guard.evaluate_payload(payload) is None


def test_empty_command_allows() -> None:
    assert venv_guard.evaluate_payload(_bash("")) is None
    assert venv_guard.evaluate_payload(_bash("   ")) is None


def test_missing_command_field_allows() -> None:
    assert venv_guard.evaluate_payload({"tool_name": "Bash", "tool_input": {}}) is None


def test_codex_shell_command_is_inspected() -> None:
    # Codex shell event carries the same tool_input.command shape.
    payload = {"tool_name": "Bash", "tool_input": {"command": "pip install foo"}}
    reason = venv_guard.evaluate_payload(payload)
    assert reason is not None
