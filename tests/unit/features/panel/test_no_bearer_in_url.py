"""Residue grep contract — the long-lived panel Bearer never appears in a URL.

T-011-13 / AC-W4-02 (FR-W4-02, ADR-10): the launch URL carries only a
single-use launch token (`?launch=<tok>`).  The long-lived Bearer is exchanged
server-side for a session cookie on first GET; it must never be placed in any
URL — neither the CLI-printed launch URL, nor the `webbrowser.open` target, nor
the panel view assets.

This test is the permanent grep guard.  Corpus per the task spec: panel views +
launch/registry code + tests.  It greps for the live token-in-URL pattern
(`?token=` query param produced from the Bearer) and fails if it reappears.
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).parents[4]  # repos/dadaia-workspace/
_PANEL = _REPO_ROOT / "dadaia_workspace" / "features" / "panel"
_LAUNCH_CLI = _REPO_ROOT / "dadaia_workspace" / "cli" / "commands" / "panel.py"

# The forbidden pattern: a URL carrying the long-lived Bearer as a `?token=`
# query parameter interpolated from a token variable.  The new mechanism uses
# `?launch=<launch-token>` instead, so `?token=` in a URL string is the residue.
_TOKEN_IN_URL_RE = re.compile(r"\?token=")


def _python_sources() -> list[Path]:
    files: list[Path] = [p for p in _PANEL.rglob("*.py") if "__pycache__" not in p.parts]
    files.append(_LAUNCH_CLI)
    return files


def test_no_token_query_param_in_launch_cli() -> None:
    """The CLI launch path must not print or open a `?token=<bearer>` URL."""
    text = _LAUNCH_CLI.read_text(encoding="utf-8")
    hits = [ln for ln in text.splitlines() if _TOKEN_IN_URL_RE.search(ln)]
    assert not hits, (
        "CLI launch path still places the Bearer in a URL via `?token=`:\n"
        + "\n".join(hits)
        + "\nUse `?launch=<launch-token>` and exchange server-side (ADR-10)."
    )


def test_no_token_query_param_in_panel_python_sources() -> None:
    """No panel Python source (views/launch/registry) interpolates `?token=`."""
    offenders: list[str] = []
    for path in _python_sources():
        text = path.read_text(encoding="utf-8")
        for i, line in enumerate(text.splitlines(), start=1):
            if _TOKEN_IN_URL_RE.search(line):
                offenders.append(f"{path.relative_to(_REPO_ROOT)}:{i}: {line.strip()}")
    assert not offenders, "Bearer-in-URL `?token=` residue found:\n" + "\n".join(offenders)


def test_launch_query_param_is_the_mechanism() -> None:
    """Positive pin: the CLI launch URL uses the `?launch=` single-use param."""
    text = _LAUNCH_CLI.read_text(encoding="utf-8")
    assert "?launch=" in text, (
        "The CLI launch path must carry the single-use launch token via `?launch=`."
    )
