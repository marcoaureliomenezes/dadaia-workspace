"""The deny translator the cursor, copilot and kimi wrappers pipe the gate's envelope through:
only a deny is answered, in the shape the table's `HookAnswer` names; anything else is silence.
Size: MEDIUM — runs the module as the wrapper does.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

from tests.fixtures.harness_env import suite_env
from tests.helpers.oslib import run

pytestmark = pytest.mark.medium

#: A reason with a character cp1252 cannot encode and a fix line, as the gate sends them.
_REASON = "refused — café →\nfix: do it"


def _envelope(decision: str = "deny") -> str:
    out = {"permissionDecision": decision, "permissionDecisionReason": _REASON}
    return json.dumps({"hookSpecificOutput": out})


def _translate(stdin: str, *words: str, tmp: Path) -> tuple[int, str, str]:
    env = suite_env(os.environ, tmp, overrides={"PYTHONIOENCODING": "cp1252"})
    argv = [sys.executable, "-B", "-m", "dadaia_workspace.hooks.translate", *words]
    done = run(argv, input=stdin, env=env, timeout=60)
    return done.returncode, done.stdout, done.stderr


def test_a_deny_with_an_exit_code_prints_the_reason_to_stderr_in_utf8_and_exits_with_it(
    tmp_path: Path,
) -> None:
    assert _translate(_envelope(), "2", tmp=tmp_path) == (2, "", f"{_REASON}\n")


def test_a_deny_with_keys_prints_one_json_object(tmp_path: Path) -> None:
    code, out, err = _translate(_envelope(), "permission", "agent_message", tmp=tmp_path)
    assert (code, err) == (0, "")
    assert json.loads(out) == {"permission": "deny", "agent_message": _REASON}


@pytest.mark.parametrize("words", [("2",), ("permission", "agent_message")])
@pytest.mark.parametrize(
    "stdin",
    [
        _envelope("allow"),
        '{"hookSpecificOutput": {}}',
        '{"hookSpecificOutput": "deny"}',
        "[1]",
        "",
        "{",
    ],
    ids=["allow", "empty-output", "string-output", "list", "empty", "truncated"],
)
def test_anything_but_a_deny_is_silence(stdin: str, words: tuple[str, ...], tmp_path: Path) -> None:
    assert _translate(stdin, *words, tmp=tmp_path) == (0, "", "")
