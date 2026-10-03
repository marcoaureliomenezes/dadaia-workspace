"""Intent: CONTRACT — bug scoped-memory-agents-md-prose-rewrite-undetected-by-doctor: the ONE TREE-5
comparator checks every scaffolded `specs/<area>/AGENTS.md` against its source and shipped history;
matching neither is a `copy-drift` WARNING, absence a finding, scaffold bytes silent."""

from __future__ import annotations

import hashlib
import json
import shlex
import subprocess
from pathlib import Path

import pytest

from dadaia_workspace.core.template_history import SHIPPED_HASHES_FILENAME
from dadaia_workspace.features.specs.doctor import SpecsDoctor

pytestmark = pytest.mark.contract

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PUBLIC = _REPO_ROOT / "dadaia_workspace" / "public"
_MEMORY_SCAFFOLD = (_PUBLIC / "scaffold" / "memory" / "AGENTS.md").read_text(encoding="utf-8")
_PROSE_REWRITE = "# specs/memory/AGENTS.md — Memory Rules\n\nA prose rewrite nobody shipped.\n"


def _public_tree(root: Path) -> Path:
    """A public/ tree carrying the real memory scaffold and a history recording it."""
    public = root / "public"
    templates = public / "templates"
    templates.mkdir(parents=True)
    (templates / "specs-AGENTS.md").write_text("# AGENTS\n", encoding="utf-8")
    scaffold = public / "scaffold" / "memory"
    scaffold.mkdir(parents=True)
    (scaffold / "AGENTS.md").write_text(_MEMORY_SCAFFOLD, encoding="utf-8")
    digest = hashlib.sha256(_MEMORY_SCAFFOLD.encode("utf-8")).hexdigest()
    (templates / SHIPPED_HASHES_FILENAME).write_text(
        json.dumps({"scaffold/memory/AGENTS.md": [digest]}), encoding="utf-8"
    )
    return public


def _specs_tree(root: Path, memory_agents_md: str | None) -> Path:
    specs = root / "specs"
    (specs / "memory" / "product").mkdir(parents=True)
    (specs / "AGENTS.md").write_text("# AGENTS\n", encoding="utf-8")
    if memory_agents_md is not None:
        (specs / "memory" / "AGENTS.md").write_text(memory_agents_md, encoding="utf-8")
    return specs


def _memory_issues(tmp_path: Path, content: str | None) -> list[str]:
    public = _public_tree(tmp_path)
    specs = _specs_tree(tmp_path / "tree", content)
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)  # the self-hosted case
    doctor = SpecsDoctor(specs, public_dir=public)
    return [
        f"{i.code} {i.verdict} {i.message}"
        for i in doctor.check()
        if i.message.replace("\\", "/").endswith("memory/AGENTS.md)")
    ]


def test_a_prose_rewrite_of_the_memory_scaffold_is_a_copy_drift_finding(tmp_path: Path) -> None:
    """Its fix, run as printed, shows the rewrite (tree5-copy-drift-fix-not-built-by-cli-line)."""
    issues = _memory_issues(tmp_path, _PROSE_REWRITE)
    assert len(issues) == 1, issues
    assert issues[0].startswith("TREE-5 warning copy-drift:"), issues[0]
    doctor = SpecsDoctor(tmp_path / "tree" / "specs", public_dir=tmp_path / "public")
    (fix,) = [i.fix for i in doctor.check() if "copy-drift" in i.message]
    shown = subprocess.run(
        shlex.split(fix), cwd=tmp_path, capture_output=True, text=True, check=False
    )
    assert shown.returncode == 1 and "+A prose rewrite nobody shipped." in shown.stdout, fix


def test_the_scaffold_bytes_are_silent(tmp_path: Path) -> None:
    assert _memory_issues(tmp_path, _MEMORY_SCAFFOLD) == []


def test_absence_is_still_a_finding(tmp_path: Path) -> None:
    """The presence check TREE-5M owned survives the fold into the one comparator."""
    issues = _memory_issues(tmp_path, None)
    assert len(issues) == 1, issues
    assert issues[0].startswith("TREE-5 warning"), issues[0]
    assert "specs/memory/AGENTS.md is missing" in issues[0]
