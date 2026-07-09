"""T-69-04 (FR2, bug ``lifecycle-diagnostic-commands-missing-context-options``, HIGH).

``lifecycle preflight`` and ``specs doctor`` are the two diagnostic verbs where
``--context``/``--release-id`` are load-bearing — they feed
``LifecyclePreflightInput`` (FR3) / resolve ``repos/<context>/specs`` — yet today they
expose only ``--json``/``--specs-dir``. RED: CliRunner confirms both reject
``--context`` with Typer's "No such option" usage error (exit code 2) on current code.

Positive control (AC2.3, documenting the architect F2 scoping decision): ``lifecycle
status`` and ``lifecycle handoffs doctor`` are backed by workspace-global builders
(``build_lifecycle_hygiene_service`` / ``build_workflow_handoff_doctor`` take no
``specs_dir``) and must NEVER gain a ``--context`` option — accepted-but-ignored would
be worse than absent. This assertion is a REGRESSION GUARD, not a repro: it passes
today and must keep passing after T-69-05's GREEN (which touches only
``preflight``/``specs doctor``).
"""

from __future__ import annotations

from typer.testing import CliRunner

from dadaia_workspace.cli.main import app

_runner = CliRunner()


def test_preflight_rejects_context_option_today() -> None:
    result = _runner.invoke(
        app,
        ["lifecycle", "preflight", "--context", "dadaia-workspace", "--release-id", "v0.1.69"],
    )
    assert result.exit_code == 2, result.output
    assert "No such option" in result.output


def test_specs_doctor_rejects_context_option_today() -> None:
    result = _runner.invoke(app, ["specs", "doctor", "--context", "dadaia-workspace"])
    assert result.exit_code == 2, result.output
    assert "No such option" in result.output


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
