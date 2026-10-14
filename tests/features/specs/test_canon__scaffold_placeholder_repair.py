"""Placeholder-atom repair.

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


_BLOCK = (
    "<!-- dadaia:fixed adr-list -->\n- ADR-0042 — Templates stop shipping `TITLE_PLACEHOLDER`\n"
    "<!-- /dadaia:fixed adr-list -->\n"
)


@pytest.mark.medium
@pytest.mark.parametrize(
    "text",
    [
        "Operator prose documents the `SLUG_PLACEHOLDER` token.\n",
        f"Operator prose.\n\n{_BLOCK}",
    ],
    ids=["prose", "fixed-section"],
)
def test_a_token_mentioned_in_a_canon_file_is_not_flagged_and_survives_fix(
    tmp_path: Path, text: str
) -> None:
    specs = _fresh_specs(tmp_path)
    arch = specs / "memory" / "ARCHITECTURE.md"
    arch.write_text(text, encoding="utf-8")
    assert is_placeholder_atom(arch) is False
    assert [i for i in _doctor(specs).check() if i.code == "MEM-PLACEHOLDER-1"] == []
    _doctor(specs).fix()
    assert arch.read_text(encoding="utf-8").startswith(text.split("\n")[0])


def test_a_canon_file_with_a_token_frontmatter_is_never_a_placeholder_atom(tmp_path: Path) -> None:
    specs = _fresh_specs(tmp_path)
    arch = specs / "memory" / "ARCHITECTURE.md"
    arch.write_text(_PLACEHOLDER_ATOM, encoding="utf-8")
    assert is_placeholder_atom(arch) is False


def test_an_atom_mentioning_a_token_in_prose_is_kept(tmp_path: Path) -> None:
    specs = _fresh_specs(tmp_path)
    atom = specs / "memory" / "product" / "feature.md"
    atom.write_text(
        "---\nslug: feature\ntitle: Real\ntldr: x.\nsummary: y.\ntags: [feature]\n"
        "token_estimate: 5\n---\n\n## Propósito\n\nThe `SLUG_PLACEHOLDER` token is legacy.\n",
        encoding="utf-8",
    )
    assert is_placeholder_atom(atom) is False


_LEGACY_TEMPLATE = """---
slug: SLUG_PLACEHOLDER
title: TITLE_PLACEHOLDER
tldr: Document the user-visible purpose of TITLE_PLACEHOLDER.
summary: Describe the current behavior, boundaries, and operational contract.
tags:
  - SLUG_PLACEHOLDER
---

# TITLE_PLACEHOLDER

## Current behavior

Document the shipped product truth here.

## Boundaries

Document exclusions and failure behavior here.
"""


@pytest.mark.medium
def test_the_legacy_memory_template_verbatim_is_still_fixable_and_removed(tmp_path: Path) -> None:
    specs = _fresh_specs(tmp_path)
    atom = specs / "memory" / "product" / "feature.md"
    atom.write_text(_LEGACY_TEMPLATE, encoding="utf-8")
    assert is_placeholder_atom(atom) is True
    assert any(i.code == "MEM-PLACEHOLDER-1" for i in _doctor(specs).fix())
    assert not atom.exists()


@pytest.mark.medium
def test_an_atom_the_operator_filled_but_for_one_token_is_reported_and_kept(
    tmp_path: Path,
) -> None:
    specs = _fresh_specs(tmp_path)
    atom = specs / "memory" / "product" / "sessions.md"
    body = "".join(f"Operator line {n}.\n" for n in range(40))
    atom.write_text(
        "---\nslug: SLUG_PLACEHOLDER\ntitle: Sessions\ntldr: How sessions bind.\n"
        f"summary: Sessions.\ntags: [sessions]\n---\n\n## Purpose\n\n{body}",
        encoding="utf-8",
    )
    assert is_placeholder_atom(atom) is False
    [flagged] = [i for i in _doctor(specs).check() if i.code == "MEM-PLACEHOLDER-1"]
    assert flagged.fixable is False
    assert flagged.fix == f"Operator action: replace the token in slug of {atom}"

    _doctor(specs).fix()
    assert atom.exists()
    atom.write_text(atom.read_text(encoding="utf-8").replace("SLUG_PLACEHOLDER", "sessions"))
    assert [i for i in _doctor(specs).check() if i.code == "MEM-PLACEHOLDER-1"] == []


def test_upgrade_dry_run_reports_without_deleting(tmp_path: Path) -> None:
    specs, atom = _placeholder_atom(tmp_path)
    upgrade_feat.upgrade(specs, remove=lambda p: sweep.remove(specs, p, p.name), dry_run=True)
    assert atom.exists()


def test_reconcile_ownership_preflight_names_owner_and_repair(tmp_path: Path) -> None:
    """A mixed-ownership workspace gets an actionable
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
