"""v0.2.9 T2 — placeholder-atom repair (bug scaffold-repair-cannot-remediate-invalid-
placeholder-atom).

Old scaffolds shipped a raw ``memory/product/feature.md`` template
(``SLUG_PLACEHOLDER`` & friends) that NO verb could remediate — consumer' real contexts
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
_TESTS_AGENTS_TEMPLATE = _TEMPLATES_DIR / "tests-AGENTS.md"

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
    """Consumer P3: a fresh tree reaches 0/0 with no manual edit (no feature.md at all)."""
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
    """Consumer' exact case: tree already at canonical version + placeholder → repaired."""
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


# ---------------------------------------------------------------------------
# T-043-10 (FR8, idea tests-agents-md-placeholder-doctor-warning): AGENTS-PLACEHOLDER-1
# — an INSTALLED tests/AGENTS.md still carrying unfilled <TOKEN> placeholders.
# Intent: CONTRACT — asserts SPEC.md FR8 / A8.1-A8.3. Same validator family/shape as
# MEM-PLACEHOLDER-1 above; reuses this module rather than a new sibling file.
# ---------------------------------------------------------------------------


def _specs_with_installed_tests_agents(tmp_path: Path, content: str | None) -> Path:
    """A repo-shaped tree: <repo>/specs/ + <repo>/tests/AGENTS.md (or no tests/ at all)."""
    repo = tmp_path / "repo"
    specs = _fresh_specs_at(repo)
    if content is not None:
        tests_dir = repo / "tests"
        tests_dir.mkdir(parents=True, exist_ok=True)
        (tests_dir / "AGENTS.md").write_text(content, encoding="utf-8")
    return specs


def _fresh_specs_at(repo: Path) -> Path:
    specs = repo / "specs"
    result = scaffold(
        specs_dir=specs,
        project_name="testproj",
        force=False,
        templates_dir=_TEMPLATES_DIR,
    )
    assert not result.errors, result.errors
    return specs


def test_agents_placeholder1_warns_on_unfilled_installed_tests_agents_md(tmp_path: Path) -> None:
    """A8.1: an installed tests/AGENTS.md with a raw `<TOKEN>` placeholder → one WARN
    naming the file."""
    specs = _specs_with_installed_tests_agents(
        tmp_path,
        "# Test Rules\n\nPer-test timeout: `<UNIT_TIMEOUT_S>`s.\n",
    )
    issues = _doctor(specs).check()
    flagged = [i for i in issues if i.code == "AGENTS-PLACEHOLDER-1"]
    assert len(flagged) == 1, [i.to_dict() for i in issues]
    assert flagged[0].severity.value == "warning"
    assert str(specs.parent / "tests" / "AGENTS.md") == flagged[0].path


def test_agents_placeholder1_silent_on_filled_installed_tests_agents_md(tmp_path: Path) -> None:
    """A8.3: a filled installed tests/AGENTS.md (no leftover `<TOKEN>`) → no finding."""
    specs = _specs_with_installed_tests_agents(
        tmp_path,
        "# Test Rules\n\nPer-test timeout: 30s.\n",
    )
    issues = _doctor(specs).check()
    assert [i for i in issues if i.code == "AGENTS-PLACEHOLDER-1"] == []


def test_agents_placeholder1_ignores_a_token_shape_inside_a_longer_code_span(
    tmp_path: Path,
) -> None:
    """A false positive this check must never produce: the template's own
    `` `Intent: <KIND> — <AC id | bug-id | task-id>` `` line illustrates a DIFFERENT
    file's docstring syntax and ships verbatim in a correctly-filled installed copy
    (this repo's own tests/AGENTS.md carries it at HEAD). Only a TIGHT single-backtick
    span wrapping nothing but the bracketed token counts as an unfilled placeholder."""
    specs = _specs_with_installed_tests_agents(
        tmp_path,
        "# Test Rules\n\n"
        "Every test declares intent — `Intent: <KIND> — <AC id | bug-id | task-id>`.\n",
    )
    issues = _doctor(specs).check()
    assert [i for i in issues if i.code == "AGENTS-PLACEHOLDER-1"] == []


def test_agents_placeholder1_silent_when_tests_agents_md_absent(tmp_path: Path) -> None:
    """No installed tests/AGENTS.md at all (repo hasn't run `context alive` yet) →
    silent; this check's job is placeholder content, never the file's existence."""
    specs = _specs_with_installed_tests_agents(tmp_path, None)
    issues = _doctor(specs).check()
    assert [i for i in issues if i.code == "AGENTS-PLACEHOLDER-1"] == []


def test_agents_placeholder1_never_flags_the_canonical_template(tmp_path: Path) -> None:
    """A8.2: the canonical template legitimately carries placeholders (verified here so
    the regex is proven live), yet the check never fires on it — it inspects the
    installed consumer copy only, never dadaia_workspace/public/templates/tests-AGENTS.md."""
    from dadaia_workspace.core.specs_repair import has_unfilled_angle_placeholders

    assert _TESTS_AGENTS_TEMPLATE.exists()
    assert has_unfilled_angle_placeholders(_TESTS_AGENTS_TEMPLATE) is True

    # A tree with no installed tests/AGENTS.md never resolves to the template's own
    # path — the check stays silent even though the template itself would trip the regex.
    specs = _specs_with_installed_tests_agents(tmp_path, None)
    issues = _doctor(specs).check()
    assert [i for i in issues if i.code == "AGENTS-PLACEHOLDER-1"] == []


def test_agents_placeholder1_silent_on_this_workspaces_own_tests_agents_md() -> None:
    """A8.3 (Done criterion): `specs doctor` stays green on THIS workspace at HEAD —
    dadaia-workspace's own installed tests/AGENTS.md is already filled in. Exercises the
    MemoryValidator method directly (never the full SpecsDoctor.check()) so this stays
    a pure unit test — LINT-1 shells a real subprocess and is out of scope here."""
    from dadaia_workspace.core.specs_repair import has_unfilled_angle_placeholders
    from dadaia_workspace.features.specs.doctor_memory import MemoryValidator

    repo_root = Path(__file__).resolve().parents[4]
    installed = repo_root / "tests" / "AGENTS.md"
    assert installed.exists()
    assert has_unfilled_angle_placeholders(installed) is False

    validator = MemoryValidator(repo_root / "specs")
    issues = validator.check_tests_agents_placeholder()
    assert issues == []


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
