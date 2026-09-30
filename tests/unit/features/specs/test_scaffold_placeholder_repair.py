"""Intent: CONTRACT — v0.2.9 T2 — placeholder-atom repair (bug scaffold-repair-cannot-remediate-invalid-
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
from dadaia_workspace.features.specs.doctor_types import finding_path

pytestmark = pytest.mark.unit

_TEMPLATES_DIR = Path(__file__).resolve().parents[4] / "dadaia_workspace" / "public" / "templates"

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


@pytest.mark.parametrize(
    ("content", "flagged"),
    [
        pytest.param(
            "# Test Rules\n\nTimeout: `<UNIT_TIMEOUT_S>`s.\n", True, id="A8.1-unfilled-warns"
        ),
        pytest.param("# Test Rules\n\nTimeout: 30s.\n", False, id="A8.3-filled-silent"),
        pytest.param(
            "# Rules\n\nIntent — `Intent: <KIND> — <AC id | bug-id | task-id>`.\n",
            False,
            id="token-inside-a-longer-code-span-silent",
        ),
        pytest.param(None, False, id="A8.2-absent-file-silent-never-reads-the-template"),
    ],
)
def test_agents_placeholder1_on_installed_tests_agents_md(
    tmp_path: Path, content: str | None, flagged: bool
) -> None:
    """T-043-10 FR8 A8.1-A8.3: only the INSTALLED ``<repo>/tests/AGENTS.md`` is inspected;
    only a tight single-backtick span around a bare ``<TOKEN>`` is unfilled."""
    repo = tmp_path / "repo"
    specs = _fresh_specs(repo)
    installed = repo / "tests" / "AGENTS.md"
    if content is not None:
        installed.parent.mkdir(parents=True)
        installed.write_text(content, encoding="utf-8")
    issues = [i for i in _doctor(specs).check() if i.code == "AGENTS-PLACEHOLDER-1"]
    expected = [("warning", str(installed))] if flagged else []
    assert [(i.verdict, finding_path(i)) for i in issues] == expected


def test_agents_placeholder1_template_trips_the_regex_and_this_repos_copy_is_filled() -> None:
    """A8.2/A8.3: the canonical template carries placeholders (the regex is live), this
    repo's installed tests/AGENTS.md does not, and the validator is silent on this repo."""
    from dadaia_workspace.features.specs.doctor_memory import (
        MemoryValidator,
        has_unfilled_angle_placeholders,
    )

    repo_root = Path(__file__).resolve().parents[4]
    assert has_unfilled_angle_placeholders(_TEMPLATES_DIR / "tests-AGENTS.md") is True
    assert has_unfilled_angle_placeholders(repo_root / "tests" / "AGENTS.md") is False
    assert MemoryValidator(repo_root / "specs").check_tests_agents_placeholder() == []


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
