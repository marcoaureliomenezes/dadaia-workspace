"""v0.2.9 T2 — placeholder-atom repair (bug scaffold-repair-cannot-remediate-invalid-
placeholder-atom).

Old scaffolds shipped a raw ``memory/product/feature.md`` template
(``SLUG_PLACEHOLDER`` & friends) that NO verb could remediate. Now: the doctor flags it as fixable
(MEM-PLACEHOLDER-1), ``--fix`` removes it, and ``specs upgrade`` repairs even a
current-version tree (dry-run reports without deleting). Exact-token detection means
filled atoms are never touched.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.migrate import upgrade as upgrade_feat
from dadaia_workspace.features.spec_context import sweep
from dadaia_workspace.features.specs.canon import scaffold
from dadaia_workspace.features.specs.doctor import SpecsDoctor
from dadaia_workspace.features.specs.doctor_memory import is_placeholder_atom

_TEMPLATES_DIR = Path(__file__).resolve().parents[3] / "dadaia_workspace" / "public" / "templates"

_PLACEHOLDER_ATOM = """---
slug: SLUG_PLACEHOLDER
title: TITLE_PLACEHOLDER
tldr: Uma frase descrevendo o que esta feature faz.
summary: Uma a duas frases expandindo o tldr.
tags:
  - feature
token_estimate: 0
---

## Propósito

Placeholder — documentar o propósito desta feature aqui.
"""


def _fresh_specs(root: Path) -> Path:
    specs = root / "specs"
    scaffold(specs, project_name="testproj", force=False, public_dir=_TEMPLATES_DIR.parent)
    return specs


def _doctor(specs: Path) -> SpecsDoctor:
    return SpecsDoctor(specs, public_dir=None, templates_dir=_TEMPLATES_DIR)


def _placeholder_atom(tmp_path: Path) -> tuple[Path, Path]:
    specs = _fresh_specs(tmp_path)
    atom = specs / "memory" / "product" / "feature.md"
    atom.write_text(_PLACEHOLDER_ATOM, encoding="utf-8")
    return specs, atom


def test_fix_removes_placeholder_and_tree_is_clean(tmp_path: Path) -> None:
    specs, atom = _placeholder_atom(tmp_path)
    [flagged] = [i for i in _doctor(specs).check() if i.code == "MEM-PLACEHOLDER-1"]
    assert (flagged.fixable, flagged.verdict) == (True, "error")

    assert any(i.code == "MEM-PLACEHOLDER-1" for i in _doctor(specs).fix())
    assert not atom.exists()
    errors = [f"{i.code}: {i.message}" for i in _doctor(specs).check() if i.verdict == "error"]
    assert errors == []


def test_filled_atom_is_never_flagged_or_removed(tmp_path: Path) -> None:
    specs = _fresh_specs(tmp_path)
    atom = specs / "memory" / "product" / "feature.md"
    atom.write_text(
        "---\nslug: feature\ntitle: Real Feature\ntldr: A real feature.\n"
        "summary: This placeholder text in prose is NOT a template marker.\n"
        "tags: [feature]\ntoken_estimate: 50\n---\n\n## Propósito\n\nReal content.\n",
        encoding="utf-8",
    )
    assert is_placeholder_atom(atom) is False
    assert [i for i in _doctor(specs).check() if i.code == "MEM-PLACEHOLDER-1"] == []
    assert atom.exists()


def test_upgrade_dry_run_reports_without_deleting(tmp_path: Path) -> None:
    specs, atom = _placeholder_atom(tmp_path)
    upgrade_feat.upgrade(specs, remove=lambda p: sweep.remove(specs, p, p.name), dry_run=True)
    assert atom.exists()


def test_reconcile_ownership_preflight_names_owner_and_repair(tmp_path: Path) -> None:
    """Bug reconcile-root-owned-agentic: a mixed-ownership workspace gets an actionable
    ownership error (path + owner + chown command), never a bare Permission denied."""
    import os

    if not hasattr(os, "geteuid"):
        pytest.skip("POSIX-only ownership semantics")

    from dadaia_workspace.features.reconcile.service import _ownership_preflight

    (tmp_path / ".dadaia" / "agentic").mkdir(parents=True)
    assert _ownership_preflight(tmp_path) is None

    agentic = tmp_path / ".dadaia" / "agentic"
    agentic.chmod(0o500)
    error = _ownership_preflight(tmp_path)
    assert error is not None
    if "owned by" in error:
        assert "chown" in error
    else:
        assert "not writable" in error
    agentic.chmod(0o755)
