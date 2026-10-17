"""The ONE TREE-5 comparator checks every scaffolded `specs/<area>/AGENTS.md` against its source and
shipped history; matching neither is a `copy-drift` WARNING, absence a finding, scaffold bytes
silent."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from dadaia_workspace.core.platform import Capabilities
from dadaia_workspace.core.template_history import SHIPPED_HASHES_FILENAME
from dadaia_workspace.core.workspace_layout import render_registry_tables
from dadaia_workspace.features.specs.doctor import SpecsDoctor
from dadaia_workspace.features.specs.doctor_types import finding_path
from tests.helpers.oslib import read_text, run_bytes, run_line, write_text
from tests.helpers.oslib import run as os_run

_REPO_ROOT = Path(__file__).resolve().parents[3]
_PUBLIC = _REPO_ROOT / "dadaia_workspace" / "public"
_MEMORY_SCAFFOLD = read_text(_PUBLIC / "scaffold" / "memory" / "AGENTS.md")
_PROSE_REWRITE = "# specs/memory/AGENTS.md — Memory Rules\n\nA prose rewrite nobody shipped.\n"


def _public_tree(root: Path) -> Path:
    """A public/ tree carrying the real memory scaffold and a history recording it."""
    public = root / "public"
    templates = public / "templates"
    templates.mkdir(parents=True)
    write_text(templates / "specs-AGENTS.md", "# AGENTS\n")
    scaffold = public / "scaffold" / "memory"
    scaffold.mkdir(parents=True)
    write_text(scaffold / "AGENTS.md", _MEMORY_SCAFFOLD)
    digest = hashlib.sha256(_MEMORY_SCAFFOLD.encode("utf-8")).hexdigest()
    write_text(
        templates / SHIPPED_HASHES_FILENAME, json.dumps({"scaffold/memory/AGENTS.md": [digest]})
    )
    return public


def _specs_tree(root: Path, memory_agents_md: str | None) -> Path:
    specs = root / "specs"
    (specs / "memory" / "product").mkdir(parents=True)
    write_text(specs / "AGENTS.md", "# AGENTS\n")
    if memory_agents_md is not None:
        write_text(specs / "memory" / "AGENTS.md", memory_agents_md)
    return specs


def _memory_issues(tmp_path: Path, content: str | None) -> list[str]:
    public = _public_tree(tmp_path)
    specs = _specs_tree(tmp_path / "tree", content)
    os_run(["git", "init", "-q", str(tmp_path)], check=True)  # the self-hosted case
    doctor = SpecsDoctor(specs, public_dir=public)
    return [
        f"{i.code} {i.verdict} {i.message}"
        for i in doctor.check()
        if Path(finding_path(i) or "").as_posix().endswith("memory/AGENTS.md")
    ]


def test_a_prose_rewrite_of_the_memory_scaffold_is_a_copy_drift_finding(tmp_path: Path) -> None:
    """Its fix, run as printed, shows the rewrite."""
    issues = _memory_issues(tmp_path, _PROSE_REWRITE)
    assert len(issues) == 1, issues
    assert issues[0].startswith("TREE-5 warning copy-drift:"), issues[0]
    doctor = SpecsDoctor(tmp_path / "tree" / "specs", public_dir=tmp_path / "public")
    (fix,) = [i.fix for i in doctor.check() if "copy-drift" in i.message]
    shown = run_line(fix, cwd=tmp_path, check=False)
    assert shown.returncode == 1 and "+A prose rewrite nobody shipped." in shown.stdout, fix


def test_the_scaffold_bytes_are_silent(tmp_path: Path) -> None:
    assert _memory_issues(tmp_path, _MEMORY_SCAFFOLD) == []


def test_absence_is_still_a_finding(tmp_path: Path) -> None:
    """A missing scaffolded memory AGENTS.md is a finding of the one comparator."""
    issues = _memory_issues(tmp_path, None)
    assert len(issues) == 1, issues
    assert issues[0].startswith("TREE-5 warning"), issues[0]
    assert "specs/memory/AGENTS.md is missing" in issues[0]


def test_a_tree_checked_out_from_git_carries_the_canonical_specs_law(tmp_path: Path) -> None:
    """The specs tree git tracks (the index, what
    every clone and worktree gets) holds every scaffolded `specs/<area>/AGENTS.md` the doctor judges canonical."""
    listing = run_bytes(["git", "-C", str(_REPO_ROOT), "ls-files", "-z", "--", "specs"])
    assert listing.returncode == 0, listing.stderr
    tracked = listing.stdout
    checkout = run_bytes(
        ["git", "-C", str(_REPO_ROOT), "checkout-index", "-z", "--stdin", f"--prefix={tmp_path}/"],
        input=tracked,
    )
    assert checkout.returncode == 0, checkout.stderr
    os_run(["git", "init", "-q", str(tmp_path)], check=True)
    issues = SpecsDoctor(tmp_path / "specs", public_dir=_PUBLIC).check()
    assert [
        i.message
        for i in issues
        if i.code in ("TREE-5", "MEM-DRIFT-2") and "AGENTS.md" in i.message
    ] == []


def test_a_law_in_either_cli_form_is_silent_under_win32(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The tracked source form and the rendered
    `Scripts\\dadaia.exe` form of a canonical law are the same law, never drift."""
    monkeypatch.setattr("dadaia_workspace.core.platform.PLATFORM", Capabilities.detect("win32"))
    rendered = render_registry_tables(_MEMORY_SCAFFOLD)
    assert ".venv/Scripts/dadaia.exe" in rendered
    assert _memory_issues(tmp_path / "a", _MEMORY_SCAFFOLD) == []
    assert _memory_issues(tmp_path / "b", rendered) == []
