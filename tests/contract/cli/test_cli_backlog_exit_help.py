"""Intent: CONTRACT — bug backlog-exit-help-says-superseded-needs-reason.

``dadaia backlog exit --help`` is the documented contract of the verb. Its
``--disposition`` help was a hand-written copy of the evidence table in
``core/models/histo.py`` and drifted: it said ``superseded (needs --reason)`` while the
verb, reading the table, refuses ``superseded`` without ``--release``. The help must be
DERIVED from that one table, so this test reads the option's help text off the command
object (never the wrapped terminal rendering) and checks every disposition against
``REQUIRED_EVIDENCE``.
"""

from __future__ import annotations

from typing import Any

import typer.main

from dadaia_workspace.cli.commands.newartifacts import backlog_app
from dadaia_workspace.core.models.histo import BACKLOG_HISTO_DISPOSITIONS, REQUIRED_EVIDENCE


def _option_help(command_name: str, option: str) -> str:
    group: Any = typer.main.get_command(backlog_app)
    ctx = group.make_context("backlog", [], resilient_parsing=True)
    command = group.get_command(ctx, command_name)
    assert command is not None, command_name
    for param in command.params:
        if option in param.opts:
            return str(getattr(param, "help", "") or "")
    raise AssertionError(f"{command_name} has no option {option}")


def test_disposition_help_states_the_evidence_the_verb_enforces() -> None:
    help_text = _option_help("exit", "--disposition")
    for disposition in BACKLOG_HISTO_DISPOSITIONS:
        expected = f"{disposition} (needs --{REQUIRED_EVIDENCE[disposition]})"
        assert expected in help_text, f"{expected!r} missing from {help_text!r}"


def test_disposition_help_never_promises_an_evidence_the_verb_refuses() -> None:
    help_text = _option_help("exit", "--disposition")
    for disposition in BACKLOG_HISTO_DISPOSITIONS:
        required = REQUIRED_EVIDENCE[disposition]
        wrong = "reason" if required == "release" else "release"
        assert f"{disposition} (needs --{wrong})" not in help_text, help_text
