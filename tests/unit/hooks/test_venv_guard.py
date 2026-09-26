"""Unit tests for the venv-guard PreToolUse policy (FR-W3-01, ADR-G4, T-014-12).

ONE rule lives in this policy (0.4.7 FR3 deleted the second):

**Venv-rooting** (ADR-G4): a fixed leading-token check on the FIRST command token
only — NO general shell parsing. It blocks `dadaia`, `pip`/`pip3`, and
`python -m dadaia_workspace` invocations NOT rooted in `.dadaia/.venv/bin/` (or the
workspace-absolute equivalent / ``$DADAIA_BIN``), emitting a block message that
contains the corrected command. pytest, ruff, and mypy are never matched — their
caches are redirected by `pyproject.toml` configuration, so no flag is enforced here
(tests/unit/features/ci_preflight/test_no_pollution.py proves the bare commands clean).
The false-block law (ADR-G1) requires that quoted strings, in-repo paths like
``repos/x/pip.py``, and another venv's explicit bin path are never blocked — covered by
the negative matrix below.

CRIT: the corrected-command message content is preserved as a parametrized column (was 3
separate fns) — never dropped. False-block law rows are untouched — never weakened.
"""

from __future__ import annotations

import pytest

from dadaia_workspace.core.cli_line import fix_line
from dadaia_workspace.hooks import venv_guard


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


@pytest.mark.parametrize(
    ("command", "expected_correction"),
    [
        ("pip install foo", ".dadaia/.venv/bin/pip install foo"),
        ("pip3 install foo", ".dadaia/.venv/bin/pip3 install foo"),
        ("python -m dadaia_workspace", ".dadaia/.venv/bin/python -m dadaia_workspace"),
        ("python3 -m dadaia_workspace", ".dadaia/.venv/bin/python -m dadaia_workspace"),
        (
            "python -m dadaia_workspace.cli.main doctor",
            ".dadaia/.venv/bin/python -m dadaia_workspace.cli.main doctor",
        ),
    ],
)
def test_blocks_bare_workspace_invocation(command: str, expected_correction: str) -> None:
    reason = venv_guard.evaluate_payload(_bash(command))
    assert reason is not None, f"expected block for {command!r}"
    # Block message must contain the corrected, venv-rooted invocation.
    assert ".dadaia/.venv/bin/" in reason
    assert expected_correction in reason


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
        "/home/user/ws/.dadaia/.venv/bin/dadaia doctor",
        "/home/user/ws/.dadaia/.venv/bin/pip install foo",
        # $DADAIA_BIN override.
        "$DADAIA_BIN doctor",
        "${DADAIA_BIN} doctor",
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
        # Unrelated commands.
        "ls -la",
        "git status",
        "python script.py",
        "python -m http.server",
    ],
)
def test_allows_venv_rooted_overridden_or_unmatched(command: str) -> None:
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
# Non-Bash and malformed payloads fail open (ALLOW); Codex shell shape blocks
# same as Claude's Bash shape.
# ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("payload", "expect_block"),
    [
        ({"tool_name": "Edit", "tool_input": {"command": "pip install foo"}}, False),
        ({"tool_name": "Bash", "tool_input": {"command": ""}}, False),
        ({"tool_name": "Bash", "tool_input": {"command": "   "}}, False),
        ({"tool_name": "Bash", "tool_input": {}}, False),
        # Codex shell event carries the same tool_input.command shape.
        ({"tool_name": "Bash", "tool_input": {"command": "pip install foo"}}, True),
    ],
)
def test_fail_open_and_codex_shape(payload: dict[str, object], expect_block: bool) -> None:
    reason = venv_guard.evaluate_payload(payload)
    if expect_block:
        assert reason is not None
    else:
        assert reason is None
