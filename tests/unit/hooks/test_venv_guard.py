"""Unit tests for the venv-guard PreToolUse policy (FR-W3-01, ADR-G4, T-014-12, FR28).

Two independent, orthogonal rules live in this policy:

1. **Venv-rooting** (ADR-G4): a fixed leading-token check on the FIRST command token
   only — NO general shell parsing. It blocks `dadaia`, `pip`/`pip3`, and
   `python -m dadaia_workspace` invocations NOT rooted in `.dadaia/.venv/bin/` (or the
   workspace-absolute equivalent / ``$DADAIA_BIN``), emitting a block message that
   contains the corrected command. pytest, ruff, and mypy are explicitly NOT matched BY
   THIS RULE. The false-block law (ADR-G1) requires that quoted strings, in-repo paths
   like ``repos/x/pip.py``, and another venv's explicit bin path are never blocked —
   covered by the negative matrix below.
2. **Cache guard** (FR28, T-043-43 — "the cache must not be born"): blocks a
   `mypy`/`pytest`/`ruff` invocation (bare or rooted in OUR OWN `.dadaia/.venv/bin/`)
   that is missing the flag that stops it from creating an in-repo cache directory —
   `pytest` without `-p no:cacheprovider`, `ruff check`/`ruff format` without
   `--no-cache`, `mypy` without `--cache-dir`. Evaluated independently of rule 1 (it
   fires even for a venv-rooted, "already correct" pytest/ruff/mypy token). A foreign
   venv path, a quoted string, an unrelated command, or a ruff subcommand that never
   writes a cache (`--version`, `rule`, `config`) is never matched — A28.2/A28.3.

CRIT: the corrected-command message content is preserved as a parametrized column (was 3
separate fns) — never dropped. False-block law rows are untouched — never weakened.
"""

from __future__ import annotations

import pytest

from dadaia_workspace.hooks import venv_guard


def _bash(command: str) -> dict[str, object]:
    return {"tool_name": "Bash", "tool_input": {"command": command}}


# ----------------------------------------------------------------------------
# BLOCK matrix — bare workspace tools not rooted in the venv bin, with the
# expected corrected-command fragment carried as a param column.
# ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("command", "expected_correction"),
    [
        ("dadaia doctor", ".dadaia/.venv/bin/dadaia doctor"),
        ("dadaia context show --json", ".dadaia/.venv/bin/dadaia context show --json"),
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
        "/home/op/ws/.dadaia/.venv/bin/dadaia doctor",
        "/home/op/ws/.dadaia/.venv/bin/pip install foo",
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
# FR28 (T-043-43) — CACHE-GUARD block matrix. A cache-enabling mypy/pytest/ruff
# invocation is blocked with the corrected command in the message (A28.1). Fires for
# BOTH the bare form and our own venv-rooted form — rule 2 is independent of rule 1's
# "already venv-rooted -> ALLOW" shortcut.
# ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("command", "expected_correction"),
    [
        # pytest — missing `-p no:cacheprovider`.
        ("pytest", "pytest -p no:cacheprovider"),
        ("pytest -q", "pytest -p no:cacheprovider -q"),
        (
            "pytest -m 'not quarantine' -n auto",
            "pytest -p no:cacheprovider -m 'not quarantine' -n auto",
        ),
        (
            ".dadaia/.venv/bin/pytest -q",
            ".dadaia/.venv/bin/pytest -p no:cacheprovider -q",
        ),
        (
            "/home/op/ws/.dadaia/.venv/bin/pytest -q",
            "/home/op/ws/.dadaia/.venv/bin/pytest -p no:cacheprovider -q",
        ),
        # ruff check / ruff format — missing `--no-cache`.
        ("ruff check .", "ruff check --no-cache ."),
        (
            "ruff check dadaia_workspace/ tests/",
            "ruff check --no-cache dadaia_workspace/ tests/",
        ),
        ("ruff format --check .", "ruff format --no-cache --check ."),
        (
            ".dadaia/.venv/bin/ruff check .",
            ".dadaia/.venv/bin/ruff check --no-cache .",
        ),
        # mypy — missing `--cache-dir`.
        ("mypy --strict dadaia_workspace/", "mypy --strict dadaia_workspace/ --cache-dir"),
        (
            ".dadaia/.venv/bin/mypy --strict dadaia_workspace/",
            ".dadaia/.venv/bin/mypy --strict dadaia_workspace/ --cache-dir",
        ),
    ],
)
def test_blocks_cache_enabling_invocation(command: str, expected_correction: str) -> None:
    reason = venv_guard.evaluate_payload(_bash(command))
    assert reason is not None, f"expected cache-guard block for {command!r}"
    assert "[CACHE GUARD]" in reason
    assert expected_correction in reason


# ----------------------------------------------------------------------------
# FR28 — CACHE-GUARD compliant-invocation matrix (A28.2). Every one of these mirrors
# a REAL invocation used by `dadaia ci preflight` (features/ci_preflight/service.py)
# or documented in DADAIA.md's Quality section — the workspace's own gate commands
# must survive the guard unaltered.
# ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "command",
    [
        # Bare, documented forms (DADAIA.md §6).
        "pytest -p no:cacheprovider",
        "pytest -q -p no:cacheprovider -m 'not quarantine' -n auto",
        "ruff format --check --no-cache",
        "ruff format --check --no-cache .",
        "ruff check --no-cache",
        "ruff check --no-cache .",
        "mypy --strict --cache-dir .dadaia/tmp/mypy-cache dadaia_workspace/",
        # Venv-rooted forms mirroring `_resolve_tool`'s sibling resolution
        # (features/ci_preflight/service.py) — the tool sits next to the resolved
        # python/dadaia executable.
        ".dadaia/.venv/bin/pytest -q -p no:cacheprovider -m 'not quarantine' -n auto",
        ".dadaia/.venv/bin/ruff format --check --no-cache dadaia_workspace/ tests/",
        ".dadaia/.venv/bin/ruff check --no-cache dadaia_workspace/ tests/",
        (
            ".dadaia/.venv/bin/mypy --strict --cache-dir "
            ".dadaia/tmp/ci-preflight/mypy-cache dadaia_workspace/"
        ),
        # Workspace-absolute venv equivalent.
        "/home/op/ws/.dadaia/.venv/bin/pytest -p no:cacheprovider",
        "/home/op/ws/.dadaia/.venv/bin/ruff check --no-cache .",
        "/home/op/ws/.dadaia/.venv/bin/mypy --strict --cache-dir /tmp/x dadaia_workspace/",
        # `--cache-dir=PATH` (long-option `=` form) also counts as present for mypy.
        "mypy --strict --cache-dir=.dadaia/tmp/mypy-cache dadaia_workspace/",
        # ruff subcommands that never write `.ruff_cache/` are out of scope — no flag
        # required (A28.2 no-false-block).
        "ruff --version",
        "ruff rule E501",
        "ruff config",
        "ruff linter",
    ],
)
def test_allows_compliant_cache_invocation(command: str) -> None:
    assert venv_guard.evaluate_payload(_bash(command)) is None


# ----------------------------------------------------------------------------
# FR28 — CACHE-GUARD false-block law (A28.2/A28.3). Fixed-leading-token discipline:
# a command that merely CONTAINS one of these words, an in-repo path ending in the
# tool name, or a foreign venv's pytest/ruff/mypy must never block.
# ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "command",
    [
        # Quoted strings that merely CONTAIN the words must not block.
        'git commit -m "fix pytest issue"',
        "echo ruff",
        "echo 'run mypy later'",
        'grep -r "pytest" repos/',
        # In-repo / unrelated paths ending in the tool name are not the leading token.
        "cat repos/x/mypy_notes.txt",
        "vim tests/conftest.py",
        "ls dadaia_workspace/hooks/venv_guard.py",
        # A leading token that merely starts with / contains the tool name, but is not
        # an exact bare match, must not block (e.g. a wrapper script or a sibling tool).
        "./scripts/pytest-runner.sh",
        "pytest-watch",
        "mypyc build",
        # A foreign venv's pytest/ruff/mypy (rooted, just not ours) — out of scope,
        # same discipline as rule 1's foreign-venv exemption.
        "repos/other/.venv/bin/pytest",
        "/opt/otherproj/.venv/bin/ruff check .",
    ],
)
def test_no_false_block_cache_guard(command: str) -> None:
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
