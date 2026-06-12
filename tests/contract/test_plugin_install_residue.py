"""Plugin-install residue contract (FR-W4-01 / AC-W4-01, release v0.1.11).

ADR-4 resolved bug ``plugin-install-command-missing`` by honest-relabel, not by
inventing a ``dadaia plugin`` command: no plugin pack assets exist anywhere under
``dadaia_workspace/``, so an install command would have nothing to install. The
``plugin-scope`` rule and the three plugin agent stubs (``frontend-engineer``,
``design-specialist``, ``devops-engineer``) must therefore never instruct anyone to run
``dadaia plugin install`` — the wording routes plugin-domain work to the operator and
points at the backlog entry ``plugin-packs-and-install-command`` (the real feature,
registered at CLOSURE).

This contract pins the relabel permanently: zero ``plugin install`` references under
the canonical asset tree ``dadaia_workspace/public/``. The grep is scoped to public
assets only — CHANGELOG, ``specs/``, bug files, and test files may discuss the retired
wording freely.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PUBLIC_ROOT = _REPO_ROOT / "dadaia_workspace" / "public"

# Any "plugin install" phrasing is residue: the command does not exist (ADR-4).
_RESIDUE = re.compile(r"plugin\s+install", re.IGNORECASE)

# Text-bearing public asset types worth scanning (skip binaries like .png/.xlsx).
_TEXT_SUFFIXES = {".md", ".json", ".sh", ".ts", ".js", ".py", ".toml", ".yml", ".yaml", ".txt"}


def _public_text_assets() -> list[Path]:
    return [
        p
        for p in sorted(_PUBLIC_ROOT.rglob("*"))
        if p.is_file() and p.suffix in _TEXT_SUFFIXES and "__pycache__" not in p.parts
    ]


def test_no_plugin_install_references_under_public() -> None:
    """Zero `plugin install` references in canonical public assets (AC-W4-01)."""
    assert _PUBLIC_ROOT.is_dir(), f"public asset tree missing: {_PUBLIC_ROOT}"
    offenders: list[str] = []
    for asset in _public_text_assets():
        rel = asset.relative_to(_REPO_ROOT).as_posix()
        for lineno, line in enumerate(asset.read_text(encoding="utf-8").splitlines(), 1):
            if _RESIDUE.search(line):
                offenders.append(f"{rel}:{lineno}: {line.strip()}")
    assert not offenders, (
        "`plugin install` references the nonexistent command (ADR-4 honest-relabel; "
        "route to the operator + backlog `plugin-packs-and-install-command`):\n"
        + "\n".join(offenders)
    )
