"""AC-9 (v0.1.57 FR6) — ``--model`` is hard-removed from every lifecycle run verb.

Deprecation-expiry: v0.1.56 kept ``--model`` as a non-fatal deprecation warning "until
callers migrate"; the only ``dadaia lifecycle --model`` callers were the deprecation-warning
tests, so migration is complete. After this release ``--model`` is an UNKNOWN option on all
12 run verbs — ``--step-model <profile-id>`` (D-3) is the sole model-selection surface.

R-QA-1 / Q4 trap: under Click 8.4.1 a ``UsageError`` (unknown option) lands in **stderr** with
an **empty stdout**, and ``mix_stderr`` was removed from ``CliRunner`` in Click 8.2 (passing it
``TypeError``s on 8.4.1) — so ``CliRunner()`` is constructed with NO ``mix_stderr`` kwarg and
``result.stderr`` / ``result.stdout`` are read as separate channels.

The pi/codex subprocess ``--model`` args are a DIFFERENT flag (OUT of scope, v0.1.56): the sole
surviving ``--model`` reference in production is ``infrastructure/pi_runtime.py``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from tests.helpers.golden_platform import norm_stderr

# _norm_stderr: consolidated into tests/helpers/golden_platform.norm_stderr (v0.1.64 FR1).


# NEVER pass mix_stderr (removed in Click 8.2; the installed 8.4.1 TypeErrors on it).
_runner = CliRunner()
_RELEASE = "v0.1.57"
_REPO_ROOT = Path(__file__).resolve().parents[3]

# All 12 lifecycle run verbs (Q7): the exact CLI verb argv that reaches each command.
_RUN_VERBS: list[tuple[str, list[str]]] = [
    ("release-define", ["release", "define"]),
    ("backlog-define", ["backlog", "define"]),
    ("implement", ["implement"]),
    ("review-qa", ["review", "qa"]),
    ("review-security", ["review", "security"]),
    ("review-code", ["review", "code"]),
    ("close", ["close"]),
    ("pipeline", ["pipeline"]),
    ("audit", ["audit"]),
    ("research", ["research"]),
    ("bug_report", ["bug_report"]),
    ("implement-review", ["implement-review"]),
]
_IDS = [row[0] for row in _RUN_VERBS]


@pytest.mark.parametrize("subcmd", [row[1] for row in _RUN_VERBS], ids=_IDS)
def test_model_flag_is_unknown_option_on_every_run_verb(subcmd: list[str]) -> None:
    """AC-9: ``--model X`` is an unknown option on all 12 verbs — exit 2, stderr, empty stdout.

    The unknown-option ``UsageError`` fires at parse time (before the command body / any
    workspace resolution), so no workspace fixture is needed.
    """
    result = _runner.invoke(
        app,
        ["lifecycle", *subcmd, "--release-id", _RELEASE, "--model", "anything:high"],
    )
    assert result.exit_code == 2
    assert "No such option: --model" in norm_stderr(result.stderr)
    # Q4: the UsageError is on stderr — stdout stays empty (no partial payload leaks).
    assert result.stdout == ""


def _iter_py(root: Path):  # type: ignore[no-untyped-def]
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        yield path


def test_warn_model_deprecated_helper_is_deleted() -> None:
    """AC-9 grep: ``_warn_model_deprecated`` has ZERO references in production + tests.

    This meta-test file is excluded from the scan — it necessarily NAMES the deleted symbol
    in its own test name / assertion message; any OTHER reference is a live caller.
    """
    this_file = Path(__file__).resolve()
    hits: list[str] = []
    for base in (_REPO_ROOT / "dadaia_workspace", _REPO_ROOT / "tests"):
        for path in _iter_py(base):
            if path.resolve() == this_file:
                continue
            if "_warn_model_deprecated" in path.read_text(encoding="utf-8"):
                hits.append(str(path.relative_to(_REPO_ROOT)))
    assert hits == [], f"_warn_model_deprecated still referenced in: {hits}"


def test_cli_model_option_is_gone_and_pi_runtime_is_sole_surviving_reference() -> None:
    """AC-9 grep: no CLI ``--model`` option decl survives; ``pi_runtime.py`` is the sole
    production ``--model`` literal (the pi subprocess arg, a different flag, OUT of scope)."""
    lifecycle_cli = (
        _REPO_ROOT / "dadaia_workspace" / "cli" / "commands" / "lifecycle.py"
    ).read_text(encoding="utf-8")
    assert '"--model"' not in lifecycle_cli

    survivors = sorted(
        str(path.relative_to(_REPO_ROOT))
        for path in _iter_py(_REPO_ROOT / "dadaia_workspace")
        if '"--model"' in path.read_text(encoding="utf-8")
    )
    assert survivors == ["dadaia_workspace/infrastructure/pi_runtime.py"], survivors
