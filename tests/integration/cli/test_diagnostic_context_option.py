"""T-69-04/T-69-05 (FR2, bug ``lifecycle-diagnostic-commands-missing-context-options``, HIGH).

Kept per plan-integration.md: only the --context/--specs-dir mutual-exclusion rejection
(AC2.2). The four "accepts --context (exit != 2)" parse-contract greps are deleted —
deep behavior is proven elsewhere (``test_preflight_real_wiring.py``,
``test_specs_doctor_context_self_hosting.py``, and the unit filters in
``test_workflow_handoff_doctor.py`` / ``test_lifecycle_status_runs_summary.py``).
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
