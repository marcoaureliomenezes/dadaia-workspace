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

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from tests.helpers.golden_platform import norm_stderr

# _norm_stderr: consolidated into tests/helpers/golden_platform.norm_stderr (v0.1.64 FR1).


# NEVER pass mix_stderr (removed in Click 8.2; the installed 8.4.1 TypeErrors on it).
_runner = CliRunner()
_RELEASE = "v0.1.57"

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
