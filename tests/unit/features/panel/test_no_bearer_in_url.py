"""Residue grep contract — no credential ever appears in a panel URL.

Panel auth removed by operator decision 2026-06-11 — the panel is a loopback-only
local dev tool that serves every route WITHOUT a credential.  There is no Bearer,
no launch token, and no session cookie; the no-auth + Host-guard contract is
pinned in test_no_auth_contract.py.

This test is the permanent grep guard against any credential-in-URL residue
re-appearing.  Corpus: panel views + the CLI launch path.  It fails if either the
old ``?token=<bearer>`` pattern OR the (now also dead) ``?launch=<launch-token>``
pattern reappears in a panel URL.
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).parents[4]  # repos/dadaia-workspace/
_PANEL = _REPO_ROOT / "dadaia_workspace" / "features" / "panel"
_LAUNCH_CLI = _REPO_ROOT / "dadaia_workspace" / "cli" / "commands" / "panel.py"

# The forbidden patterns: a URL carrying a credential as a `?token=` query param
# (the old long-lived Bearer) OR a `?launch=` query param (the now-removed
# single-use launch token).  Either in a URL string is dead-credential residue.
_TOKEN_IN_URL_RE = re.compile(r"\?token=|\?launch=")


def _python_sources() -> list[Path]:
    files: list[Path] = [p for p in _PANEL.rglob("*.py") if "__pycache__" not in p.parts]
    files.append(_LAUNCH_CLI)
    return files


def test_no_credential_query_param_in_launch_cli() -> None:
    """The CLI panel path must not print or open a credential-bearing URL."""
    text = _LAUNCH_CLI.read_text(encoding="utf-8")
    hits = [ln for ln in text.splitlines() if _TOKEN_IN_URL_RE.search(ln)]
    assert not hits, (
        "CLI panel path still places a credential in a URL (`?token=` / `?launch=`):\n"
        + "\n".join(hits)
        + "\nThe panel is credential-free (no-auth decision 2026-06-11)."
    )


def test_no_credential_query_param_in_panel_python_sources() -> None:
    """No panel Python source (views/server) interpolates `?token=` / `?launch=`."""
    offenders: list[str] = []
    for path in _python_sources():
        text = path.read_text(encoding="utf-8")
        for i, line in enumerate(text.splitlines(), start=1):
            if _TOKEN_IN_URL_RE.search(line):
                offenders.append(f"{path.relative_to(_REPO_ROOT)}:{i}: {line.strip()}")
    assert not offenders, "Credential-in-URL residue found:\n" + "\n".join(offenders)
