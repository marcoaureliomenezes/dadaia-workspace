"""T-69-04/T-69-05 (FR2, bug ``lifecycle-diagnostic-commands-missing-context-options``, HIGH).

``lifecycle preflight`` and ``specs doctor`` are the two diagnostic verbs where
``--context``/``--release-id`` are load-bearing — they feed
``LifecyclePreflightInput`` (FR3) / resolve ``repos/<context>/specs`` — yet before
T-69-05 they exposed only ``--json``/``--specs-dir``.

The pre-fix RED (CliRunner confirming both rejected ``--context`` with Typer's "No
such option" usage error, exit code 2) is superseded here by the T-69-05 GREEN
assertion — both options are now accepted (exit code != 2, i.e. no usage error) and
``specs doctor`` rejects passing ``--context`` and ``--specs-dir`` together (AC2.2).

v0.1.71 FR2 CORRECTION (bug ``lifecycle-status-handoffs-doctor-missing-context``): the
v0.1.69 "architect F2 scoping decision" — that ``status``/``handoffs doctor`` must NEVER
accept ``--context`` because their builders were workspace-global — was WRONG for the
operator's real release workflow, which runs every lifecycle verb with an explicit
``--context dd-chain-capture --release-id v0.2.0``. ``LifecycleRun`` carries ``context``
and ``release_id``, so the option is a REAL run filter, not accepted-but-ignored. The two
former "must-reject" regression guards are inverted here to "accepts (parse contract)";
the DEEP filtering behaviour is proven hermetically in
``tests/unit/features/lifecycle/test_workflow_handoff_doctor.py`` (doctor) and
``tests/unit/cli/test_lifecycle_status_runs_summary.py`` (status).
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


def test_status_accepts_context_option_v0171() -> None:
    """v0.1.71 FR2 (AC): ``lifecycle status`` ACCEPTS ``--context``/``--release-id`` — no
    Typer "No such option" usage error (exit 2). Parse-contract only, hermetic: the deep
    run-scoped summary is proven against a tmp_path workspace in the unit test (this must
    NOT depend on an ambient initialized workspace — there is none on CI)."""
    result = _runner.invoke(
        app,
        ["lifecycle", "status", "--context", "dd-chain-capture", "--release-id", "v0.2.0"],
    )
    assert result.exit_code != 2, result.output
    assert "No such option" not in result.output


def test_handoffs_doctor_accepts_context_option_v0171() -> None:
    """v0.1.71 FR2 (AC): ``lifecycle handoffs doctor`` ACCEPTS ``--context``/
    ``--release-id`` — no Typer "No such option" usage error. Parse-contract only,
    hermetic; the deep run filter is proven in the unit test."""
    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "handoffs",
            "doctor",
            "--context",
            "dd-chain-capture",
            "--release-id",
            "v0.2.0",
        ],
    )
    assert result.exit_code != 2, result.output
    assert "No such option" not in result.output
