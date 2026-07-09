"""T-69-04/T-69-05 (FR2, bug ``lifecycle-diagnostic-commands-missing-context-options``, HIGH).

``lifecycle preflight`` and ``specs doctor`` are the two diagnostic verbs where
``--context``/``--release-id`` are load-bearing — they feed
``LifecyclePreflightInput`` (FR3) / resolve ``repos/<context>/specs`` — yet before
T-69-05 they exposed only ``--json``/``--specs-dir``.

The pre-fix RED (CliRunner confirming both rejected ``--context`` with Typer's "No
such option" usage error, exit code 2) is superseded here by the T-69-05 GREEN
assertion — both options are now accepted (exit code != 2, i.e. no usage error) and
``specs doctor`` rejects passing ``--context`` and ``--specs-dir`` together (AC2.2).

Positive control (AC2.3, documenting the architect F2 scoping decision): ``lifecycle
status`` and ``lifecycle handoffs doctor`` are backed by workspace-global builders
(``build_lifecycle_hygiene_service`` / ``build_workflow_handoff_doctor`` take no
``specs_dir``) and must NEVER gain a ``--context`` option — accepted-but-ignored would
be worse than absent. This assertion is a REGRESSION GUARD, not a repro: it passed
before T-69-05 and keeps passing after (which touches only
``preflight``/``specs doctor``).
"""

from __future__ import annotations

import re

from typer.testing import CliRunner

from dadaia_workspace.cli.main import app

_runner = CliRunner()

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _norm(text: str) -> str:
    """Strip ANSI colour + Rich box-drawing borders and collapse all whitespace.

    Rich renders Typer errors inside a bordered box whose wrap width depends on the
    terminal (GitHub Actions wraps at a different width than a local TTY), which can
    split a token like ``--context`` onto its own line inside the box. Normalising
    away the borders/newlines makes substring assertions platform-invariant
    (see the golden-platform normalization law; Rich box-wrap on GHA gotcha).
    """
    cleaned = _ANSI.sub("", text)
    cleaned = re.sub(r"[│╭╮╰╯─|]", " ", cleaned)
    return " ".join(cleaned.split())


def test_preflight_accepts_context_option_ac21() -> None:
    # AC2.1: exits != 2 (no "No such option" usage error) and resolves repos/<ctx>/specs.
    result = _runner.invoke(
        app,
        ["lifecycle", "preflight", "--context", "dadaia-workspace", "--release-id", "v0.1.69"],
    )
    assert result.exit_code != 2, result.output
    assert "No such option" not in result.output


def test_specs_doctor_accepts_context_option_ac22() -> None:
    # AC2.2: the ``--context`` option is ACCEPTED (parsed) by ``specs doctor`` — no Typer
    # "No such option" usage error (exit 2). Hermetic, environment-invariant: this asserts
    # the CLI-parse contract only. The deep behaviour (``--context`` resolves the context's
    # specs tree, with the self-hosting workspace-root fallback) is proven hermetically in
    # ``test_specs_doctor_context_self_hosting.py`` against a ``tmp_path`` workspace — this
    # test must NOT depend on an ambient initialized workspace (there is none on CI).
    result = _runner.invoke(app, ["specs", "doctor", "--context", "dadaia-workspace"])
    assert result.exit_code != 2, result.output
    assert "No such option" not in result.output


def test_specs_doctor_context_and_specs_dir_mutually_exclusive_ac22() -> None:
    # AC2.2: passing both --context and --specs-dir errors clearly. Normalise the Rich
    # box-wrapped error so the token assertions are platform-invariant (GHA wraps at a
    # different width than a local TTY and can split ``--context`` across lines).
    result = _runner.invoke(
        app,
        ["specs", "doctor", "--context", "dadaia-workspace", "--specs-dir", "/tmp/whatever"],
    )
    assert result.exit_code != 0, result.output
    clean = _norm(result.output)
    assert "--context" in clean, result.output
    assert "--specs-dir" in clean, result.output


def test_status_stays_workspace_global_no_context_option() -> None:
    """AC2.3 positive control: status's builder takes no specs_dir; --context must
    never be accepted there (accepted-but-ignored is worse than absent)."""
    result = _runner.invoke(app, ["lifecycle", "status", "--context", "dadaia-workspace"])
    assert result.exit_code == 2, result.output
    assert "No such option" in result.output


def test_handoffs_doctor_stays_workspace_global_no_context_option() -> None:
    """AC2.3 positive control: handoffs doctor's builder takes no specs_dir; --context
    must never be accepted there."""
    result = _runner.invoke(
        app, ["lifecycle", "handoffs", "doctor", "--context", "dadaia-workspace"]
    )
    assert result.exit_code == 2, result.output
    assert "No such option" in result.output
