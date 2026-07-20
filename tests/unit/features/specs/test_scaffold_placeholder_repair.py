"""v0.2.9 T2 — placeholder-atom repair (bug scaffold-repair-cannot-remediate-invalid-
placeholder-atom).

Old scaffolds shipped a raw ``memory/product/feature.md`` template
(``SLUG_PLACEHOLDER`` & friends) that NO verb could remediate — hermes' real contexts
failed ``specs doctor`` forever. Now: the doctor flags it as fixable
(MEM-PLACEHOLDER-1), ``--fix`` removes it, and ``specs upgrade`` repairs even a
current-version tree (dry-run reports without deleting). Exact-token detection means
filled atoms are never touched.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.features.migrate import upgrade as upgrade_feat
from dadaia_workspace.features.specs.doctor import SpecsDoctor
from dadaia_workspace.features.specs.doctor_memory import (
    is_placeholder_atom,
    remove_placeholder_atoms,
)
from dadaia_workspace.features.specs.scaffolder import scaffold

pytestmark = pytest.mark.unit

_TEMPLATES_DIR = Path(__file__).resolve().parents[4] / "dadaia_workspace" / "public" / "templates"

_PLACEHOLDER_ATOM = """---
slug: SLUG_PLACEHOLDER
title: TITLE_PLACEHOLDER
category: product
tldr: Uma frase descrevendo o que esta feature faz.
summary: Uma a duas frases expandindo o tldr.
tags:
  - feature
token_estimate: 0
last_updated: "2026-01-01"
release_origin: RELEASE_PLACEHOLDER
---

## Propósito

Placeholder — documentar o propósito desta feature aqui.
"""


def _fresh_specs(tmp_path: Path) -> Path:
    specs = tmp_path / "specs"
    result = scaffold(
        specs_dir=specs,
        project_name="testproj",
        force=False,
        templates_dir=_TEMPLATES_DIR,
    )
    assert not result.errors, result.errors
    return specs


def _doctor(specs: Path) -> SpecsDoctor:
    return SpecsDoctor(specs, public_dir=None, templates_dir=_TEMPLATES_DIR)


def test_fresh_scaffold_is_doctor_clean_without_feature_placeholder(tmp_path: Path) -> None:
    """Hermes P3: a fresh tree reaches 0/0 with no manual edit (no feature.md at all)."""
    specs = _fresh_specs(tmp_path)
    assert not (specs / "memory" / "product" / "feature.md").exists()
    issues = _doctor(specs).check()
    errors = [i for i in issues if i.severity.value == "error"]
    assert errors == [], [f"{i.code}: {i.description}" for i in errors]


def test_doctor_flags_placeholder_atom_as_fixable(tmp_path: Path) -> None:
    specs = _fresh_specs(tmp_path)
    atom = specs / "memory" / "product" / "feature.md"
    atom.write_text(_PLACEHOLDER_ATOM, encoding="utf-8")

    issues = _doctor(specs).check()
    flagged = [i for i in issues if i.code == "MEM-PLACEHOLDER-1"]
    assert len(flagged) == 1
    assert flagged[0].fixable is True
    assert flagged[0].severity.value == "error"


def test_fix_removes_placeholder_and_tree_is_clean(tmp_path: Path) -> None:
    specs = _fresh_specs(tmp_path)
    atom = specs / "memory" / "product" / "feature.md"
    atom.write_text(_PLACEHOLDER_ATOM, encoding="utf-8")

    doctor = _doctor(specs)
    fixed = doctor.fix()
    assert any(i.code == "MEM-PLACEHOLDER-1" for i in fixed)
    assert not atom.exists()

    residual = _doctor(specs).check()
    assert [i for i in residual if i.code == "MEM-PLACEHOLDER-1"] == []
    errors = [i for i in residual if i.severity.value == "error"]
    assert errors == [], [f"{i.code}: {i.description}" for i in errors]


def test_filled_atom_is_never_flagged_or_removed(tmp_path: Path) -> None:
    specs = _fresh_specs(tmp_path)
    atom = specs / "memory" / "product" / "feature.md"
    atom.write_text(
        "---\n"
        "slug: feature\n"
        "title: Real Feature\n"
        "category: product\n"
        "tldr: A real feature with real content.\n"
        "summary: This placeholder text in prose is NOT a template marker.\n"
        "tags: [feature]\n"
        "token_estimate: 50\n"
        "last_updated: '2026-07-19'\n"
        "release_origin: v0.2.9\n"
        "---\n\n## Propósito\n\nReal content mentioning placeholder concepts.\n",
        encoding="utf-8",
    )
    assert is_placeholder_atom(atom) is False
    issues = _doctor(specs).check()
    assert [i for i in issues if i.code == "MEM-PLACEHOLDER-1"] == []
    assert remove_placeholder_atoms(specs) == []
    assert atom.exists()


def test_upgrade_repairs_current_version_tree(tmp_path: Path) -> None:
    """Hermes' exact case: tree already at canonical version + placeholder → repaired."""
    specs = _fresh_specs(tmp_path)
    atom = specs / "memory" / "product" / "feature.md"
    atom.write_text(_PLACEHOLDER_ATOM, encoding="utf-8")

    result = upgrade_feat.upgrade(specs)
    assert result.no_op is False
    assert result.placeholder_removed == [atom]
    assert not atom.exists()
    errors = [i for i in _doctor(specs).check() if i.severity.value == "error"]
    assert errors == [], [f"{i.code}: {i.description}" for i in errors]


def test_upgrade_dry_run_reports_without_deleting(tmp_path: Path) -> None:
    specs = _fresh_specs(tmp_path)
    atom = specs / "memory" / "product" / "feature.md"
    atom.write_text(_PLACEHOLDER_ATOM, encoding="utf-8")

    result = upgrade_feat.upgrade(specs, dry_run=True)
    assert result.placeholder_removed == [atom]
    assert atom.exists(), "dry-run must not delete"


def test_catalog_stays_valid_json_after_repair(tmp_path: Path) -> None:
    specs = _fresh_specs(tmp_path)
    atom = specs / "memory" / "product" / "feature.md"
    atom.write_text(_PLACEHOLDER_ATOM, encoding="utf-8")
    remove_placeholder_atoms(specs)
    catalog = json.loads((specs / "memory" / "product" / "catalog.json").read_text())
    assert catalog["features"] == []


def test_reconcile_ownership_preflight_names_owner_and_repair(tmp_path: Path) -> None:
    """Bug reconcile-root-owned-agentic: a mixed-ownership workspace gets an actionable
    ownership error (path + owner + chown command), never a bare Permission denied."""
    import os

    if not hasattr(os, "geteuid"):
        pytest.skip("POSIX-only ownership semantics")

    from dadaia_workspace.features.reconcile.service import _ownership_preflight

    # Writable tree: no error.
    (tmp_path / ".dadaia" / "agentic").mkdir(parents=True)
    assert _ownership_preflight(tmp_path) is None

    # Unwritable mode: the same preflight reports it (the foreign-owner branch is
    # covered by the same function; chmod works without privilege).
    agentic = tmp_path / ".dadaia" / "agentic"
    agentic.chmod(0o500)
    error = _ownership_preflight(tmp_path)
    assert error is not None
    if "owned by" in error:
        assert "chown" in error
    else:
        assert "not writable" in error
    agentic.chmod(0o755)
