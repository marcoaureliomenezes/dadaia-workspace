"""FR6 copy-drift: a scaffolded AGENTS.md matching neither source nor shipped history.

Intent: CONTRACT — T-047-02 / 0.4.7 FR6 and bug
`scoped-memory-agents-md-prose-rewrite-undetected-by-doctor`: every scaffolded
`specs/<area>/AGENTS.md` — `memory/` included — is compared against its scaffold source
and the shipped-hashes history by the ONE TREE-5 comparator. Bytes matching neither are
a `copy-drift` finding (WARNING); absence is a finding too (the check TREE-5M used to
own); scaffold bytes are silent.
Size: SMALL — SpecsDoctor over tmp_path trees plus one read of the real scaffold.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from dadaia_workspace.features.specs.doctor import SpecsDoctor
from dadaia_workspace.features.specs.template_history import SHIPPED_HASHES_FILENAME, was_shipped

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
    doctor = SpecsDoctor(specs, public_dir=public)
    return [
        f"{i.code} {i.severity.value} {i.description}"
        for i in doctor.check()
        if Path(i.path).as_posix().endswith("memory/AGENTS.md")
    ]


def test_a_prose_rewrite_of_the_memory_scaffold_is_a_copy_drift_finding(tmp_path: Path) -> None:
    issues = _memory_issues(tmp_path, _PROSE_REWRITE)
    assert len(issues) == 1, issues
    assert issues[0].startswith("TREE-5 warning copy-drift:"), issues[0]


def test_the_scaffold_bytes_are_silent(tmp_path: Path) -> None:
    assert _memory_issues(tmp_path, _MEMORY_SCAFFOLD) == []


def test_absence_is_still_a_finding(tmp_path: Path) -> None:
    """The presence check TREE-5M owned survives the fold into the one comparator."""
    issues = _memory_issues(tmp_path, None)
    assert len(issues) == 1, issues
    assert issues[0].startswith("TREE-5 warning"), issues[0]
    assert "scaffold/memory/AGENTS.md" in issues[0]


def test_shipped_history_records_the_current_memory_scaffold() -> None:
    """Anti-rot: editing the scaffold without appending its digest makes the next stale
    projection unrecognisable as ours."""
    assert was_shipped(_MEMORY_SCAFFOLD, "scaffold/memory/AGENTS.md", _PUBLIC / "templates")
