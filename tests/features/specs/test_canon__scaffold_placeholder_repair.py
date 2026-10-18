"""Placeholder-atom detection: reported, never repaired.

A legacy placeholder atom (a memory atom whose frontmatter keeps a template token such as
``SLUG_PLACEHOLDER``) is reported as MEM-PLACEHOLDER-1, not auto-fixable, its fix line naming
fill or delete. ``doctor --fix`` leaves it byte for byte.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.migrate import upgrade as upgrade_feat
from dadaia_workspace.features.spec_context import sweep
from dadaia_workspace.features.specs.canon import scaffold
from dadaia_workspace.features.specs.doctor import SpecsDoctor
from dadaia_workspace.features.specs.doctor_memory import is_placeholder_atom
from tests.helpers.oslib import effective_uid, make_readonly, make_writable, read_text, write_text

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
    write_text(atom, _PLACEHOLDER_ATOM)
    return specs, atom


_FILL_OR_DELETE = "Agent action: fill or delete the atom"


def test_fix_reports_placeholder_and_leaves_it_byte_for_byte(tmp_path: Path) -> None:
    specs, atom = _placeholder_atom(tmp_path)
    before = atom.read_bytes()
    [flagged] = [i for i in _doctor(specs).check() if i.code == "MEM-PLACEHOLDER-1"]
    assert (flagged.fixable, flagged.verdict, flagged.fix) == (
        False,
        "error",
        f"{_FILL_OR_DELETE} {atom}",
    )

    _doctor(specs).fix()
    assert atom.read_bytes() == before
    [still] = [i for i in _doctor(specs).check() if i.code == "MEM-PLACEHOLDER-1"]
    assert still.fix == f"{_FILL_OR_DELETE} {atom}"


def test_filled_atom_is_never_flagged_or_removed(tmp_path: Path) -> None:
    specs = _fresh_specs(tmp_path)
    atom = specs / "memory" / "product" / "feature.md"
    write_text(
        atom,
        "---\nslug: feature\ntitle: Real Feature\ntldr: A real feature.\n"
        "summary: This placeholder text in prose is NOT a template marker.\n"
        "tags: [feature]\ntoken_estimate: 50\n---\n\n## Propósito\n\nReal content.\n",
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
    write_text(arch, text)
    assert is_placeholder_atom(arch) is False
    assert [i for i in _doctor(specs).check() if i.code == "MEM-PLACEHOLDER-1"] == []
    _doctor(specs).fix()
    assert read_text(arch).startswith(text.split("\n")[0])


def test_a_canon_file_with_a_token_frontmatter_is_never_a_placeholder_atom(tmp_path: Path) -> None:
    specs = _fresh_specs(tmp_path)
    arch = specs / "memory" / "ARCHITECTURE.md"
    write_text(arch, _PLACEHOLDER_ATOM)
    assert is_placeholder_atom(arch) is False


def test_an_atom_mentioning_a_token_in_prose_is_kept(tmp_path: Path) -> None:
    specs = _fresh_specs(tmp_path)
    atom = specs / "memory" / "product" / "feature.md"
    write_text(
        atom,
        "---\nslug: feature\ntitle: Real\ntldr: x.\nsummary: y.\ntags: [feature]\n"
        "token_estimate: 5\n---\n\n## Propósito\n\nThe `SLUG_PLACEHOLDER` token is legacy.\n",
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
def test_the_legacy_memory_template_verbatim_is_reported_and_kept(tmp_path: Path) -> None:
    specs = _fresh_specs(tmp_path)
    atom = specs / "memory" / "product" / "feature.md"
    write_text(atom, _LEGACY_TEMPLATE)
    before = atom.read_bytes()
    [flagged] = [i for i in _doctor(specs).check() if i.code == "MEM-PLACEHOLDER-1"]
    assert (flagged.fixable, flagged.fix) == (False, f"{_FILL_OR_DELETE} {atom}")
    _doctor(specs).fix()
    assert atom.read_bytes() == before


@pytest.mark.medium
def test_an_atom_the_operator_filled_but_for_one_token_is_reported_and_kept(
    tmp_path: Path,
) -> None:
    specs = _fresh_specs(tmp_path)
    atom = specs / "memory" / "product" / "sessions.md"
    body = "".join(f"Operator line {n}.\n" for n in range(40))
    write_text(
        atom,
        "---\nslug: SLUG_PLACEHOLDER\ntitle: Sessions\ntldr: How sessions bind.\n"
        f"summary: Sessions.\ntags: [sessions]\n---\n\n## Purpose\n\n{body}",
    )
    assert is_placeholder_atom(atom) is False
    [flagged] = [i for i in _doctor(specs).check() if i.code == "MEM-PLACEHOLDER-1"]
    assert flagged.fixable is False
    assert flagged.fix == f"Agent action: replace the token in slug of {atom}"

    _doctor(specs).fix()
    assert atom.exists()
    write_text(atom, read_text(atom).replace("SLUG_PLACEHOLDER", "sessions"))
    assert [i for i in _doctor(specs).check() if i.code == "MEM-PLACEHOLDER-1"] == []


def test_upgrade_dry_run_reports_without_deleting(tmp_path: Path) -> None:
    specs, atom = _placeholder_atom(tmp_path)
    upgrade_feat.upgrade(specs, remove=lambda p: sweep.remove(specs, p, p.name), dry_run=True)
    assert atom.exists()


def test_reconcile_ownership_preflight_names_owner_and_repair(tmp_path: Path) -> None:
    """A mixed-ownership workspace gets an actionable
    ownership error (path + owner + chown command), never a bare Permission denied."""
    if effective_uid() is None:
        pytest.skip("this host has no ownership semantics")

    from dadaia_workspace.features.reconcile.service import _ownership_preflight

    (tmp_path / ".dadaia" / "agentic").mkdir(parents=True)
    assert _ownership_preflight(tmp_path) is None

    agentic = tmp_path / ".dadaia" / "agentic"
    make_readonly(agentic)
    error = _ownership_preflight(tmp_path)
    assert error is not None
    if "owned by" in error:
        assert "chown" in error
    else:
        assert "not writable" in error
    make_writable(agentic)
