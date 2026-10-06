"""Unit tests for the venv-guard PreToolUse policy (FR-W3-01, ADR-G4, T-014-12).

ONE rule lives in this policy (0.4.7 FR3 deleted the second):

**Venv-rooting** (ADR-G4): a fixed leading-token check on the FIRST command token
only — NO general shell parsing. It blocks `dadaia` and `python -m dadaia_workspace`
invocations NOT rooted in `.dadaia/.venv/bin/` (or the workspace-absolute equivalent),
emitting a block message that contains the corrected command.
``pip``/``pip3`` are never judged (ADR 0134). pytest, ruff, and mypy are never matched — their
caches are redirected by `pyproject.toml` configuration, so no flag is enforced here.
The false-block law (ADR-G1) requires that quoted strings, in-repo paths like
``repos/x/dadaia``, and another venv's explicit bin path are never blocked — covered by
the negative matrix below.

CRIT: the corrected-command message content is preserved as a parametrized column (was 3
separate fns) — never dropped. False-block law rows are untouched — never weakened.
"""

from __future__ import annotations

import shlex
from pathlib import Path

import pytest

from dadaia_workspace.core.cli_line import fix_line, venv_line
from dadaia_workspace.hooks import _common, venv_guard


def _bash(command: str) -> dict[str, object]:
    return {"tool_name": "Bash", "tool_input": {"command": command}}


# ----------------------------------------------------------------------------
# BLOCK matrix — bare workspace tools not rooted in the venv bin, with the
# expected corrected-command fragment carried as a param column.
# ----------------------------------------------------------------------------


@pytest.mark.parametrize("args", ["doctor", "context show --json"])
def test_bare_dadaia_is_corrected_to_the_cli_fix_line(args: str) -> None:
    reason = venv_guard.evaluate_payload(_bash(f"dadaia {args}"))
    assert reason is not None
    assert f"fix: {fix_line(None)} {args}" in reason
    assert "DADAIA_BIN" not in reason  # dadaia-bin-still-honoured-after-adr-0045


@pytest.mark.parametrize(
    ("command", "tool", "args"),
    [
        ("python -m dadaia_workspace", "python", "-m dadaia_workspace"),
        ("python3 -m dadaia_workspace", "python", "-m dadaia_workspace"),
        (
            "python -m dadaia_workspace.cli.main doctor",
            "python",
            "-m dadaia_workspace.cli.main doctor",
        ),
    ],
)
def test_blocks_bare_workspace_invocation(command: str, tool: str, args: str) -> None:
    """sa-fix-lines-not-built-by-cli-line#S4 — the python fix is the absolute venv tool."""
    reason = venv_guard.evaluate_payload(_bash(command))
    assert reason is not None, f"expected block for {command!r}"
    fix = reason.splitlines()[-1]
    assert fix == f"fix: {venv_line(None, tool)} {args}"
    assert Path(shlex.split(fix[len("fix: ") :])[0]).is_absolute()


# ----------------------------------------------------------------------------
# ALLOW matrix — venv-rooted / out-of-scope tools.
# ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "command",
    [
        # Venv-rooted (relative) — the canonical correct form.
        ".dadaia/.venv/bin/dadaia doctor",
        ".dadaia/.venv/bin/python -m dadaia_workspace",
        # Workspace-absolute venv equivalent.
        "/home/user/ws/.dadaia/.venv/bin/dadaia doctor",
        # ADR-G4 explicit exclusions from the VENV-ROOTING rule — never matched by it.
        # (Compliant with the FR28 cache-guard too, see the dedicated matrices below.)
        "pytest -p no:cacheprovider",
        "ruff check --no-cache .",
        "ruff format --check --no-cache",
        "mypy --strict --cache-dir .dadaia/tmp/mypy-cache dadaia_workspace",
        # `python -m X` forms are out of scope for BOTH rules (T-043-43 scope decision —
        # only the bare name / our own venv-rooted path are recognized, see module
        # docstring); only `python -m dadaia_workspace` is special-cased (rule 1).
        "python -m pytest",
        "python -m ruff check",
        # ADR 0134: a project's own pip is never judged.
        "pip install requests",
        "pip3 install foo",
        # Unrelated commands.
        "ls -la",
        "git status",
        "python script.py",
        "python -m http.server",
    ],
)
def test_allows_venv_rooted_or_unmatched(command: str) -> None:
    assert venv_guard.evaluate_payload(_bash(command)) is None


# ----------------------------------------------------------------------------
# FALSE-BLOCK law (ADR-G1) — quoted strings, in-repo paths, foreign venv bins.
# ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "command",
    [
        # Quoted strings that merely CONTAIN the words must not block.
        'echo "run dadaia doctor"',
        # In-repo paths ending in the tool name are not the leading token.
        "cat repos/x/dadaia",
        "vim repos/dadaia-workspace/dadaia_workspace/cli/main.py",
        # Another venv's explicit bin path (rooted, just not ours) — out of scope.
        "repos/other/.venv/bin/dadaia doctor",
        # A path that merely has 'dadaia' as a substring.
        "./dadaia-wrapper.sh doctor",
        # sa-text-restates-rules-the-code-contradicts#49.1: only the FIRST token counts.
        "cd x && dadaia doctor",
    ],
)
def test_no_false_block(command: str) -> None:
    assert venv_guard.evaluate_payload(_bash(command)) is None


# ----------------------------------------------------------------------------
# Non-Bash and malformed payloads fail open (ALLOW); Codex shell shape blocks
# same as Claude's Bash shape.
# ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("payload", "expect_block"),
    [
        ({"tool_name": "Edit", "tool_input": {"command": "dadaia doctor"}}, False),
        ({"tool_name": "Bash", "tool_input": {"command": ""}}, False),
        ({"tool_name": "Bash", "tool_input": {"command": "   "}}, False),
        ({"tool_name": "Bash", "tool_input": {}}, False),
        # sa-gate-blind-on-cursor-copilot-devin#B6: every harness's shell alias, read through the one alias table.
        ({"tool_name": "Bash", "tool_input": {"command": "dadaia doctor"}}, True),
        ({"tool_name": "exec", "command": "dadaia doctor"}, True),
        ({"tool_name": "Shell", "tool_input": {"command": "dadaia doctor"}}, True),
        ({"toolName": "bash", "toolArgs": '{"command": "dadaia doctor"}'}, True),
        ({"command": "dadaia doctor"}, True),
    ],
)
def test_every_shell_alias_is_judged_like_bash(
    payload: dict[str, object], expect_block: bool
) -> None:
    reason = venv_guard.evaluate_payload(_common.claude_payload(payload))
    if expect_block:
        assert reason is not None
    else:
        assert reason is None


def test_the_block_fix_runs_verbatim_from_a_repo_subdirectory(tmp_path: Path) -> None:
    """sa-fix-lines-not-built-by-cli-line#S2 — the fix runs as printed from repos/alpha."""
    import subprocess

    cwd = tmp_path / "repos" / "alpha"
    cwd.mkdir(parents=True)
    reason = venv_guard.evaluate_payload(_bash("python -m dadaia_workspace --version"))
    assert reason is not None
    fix = reason.splitlines()[-1].removeprefix("fix: ")
    done = subprocess.run(shlex.split(fix), cwd=cwd, capture_output=True, text=True, check=False)
    assert done.returncode == 0, done.stderr
