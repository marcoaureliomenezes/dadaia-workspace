"""Intent: CONTRACT — T-048-08 (FR5 AC5.1, AC5.2): dd-audit-project carries the first-pass
section, and `memory.py drift --since <root commit>` is a runnable worklist. Size: SMALL.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

_REPO = Path(__file__).resolve().parents[2]
_SKILLS = _REPO / "dadaia_workspace" / "public" / "skills"
_SKILL = _SKILLS / "dd-audit-project" / "SKILL.md"
_MEMORY = _SKILLS / "dd-spec-navigator" / "scripts" / "memory.py"


def test_skill_carries_the_first_pass_statements() -> None:
    text = _SKILL.read_text(encoding="utf-8")
    section = text.split("## 3. First pass", 1)[1].split("\n## ", 1)[0]
    for statement in (
        "audits_histo.jsonl` holds no record",
        "memory.py drift --since $(git -C repos/<slug> rev-list --max-parents=0 HEAD) --specs repos/<slug>/specs",
        "`dd-product-engineer` fills `ARCHITECTURE.md`, `QUALITY.md` and the product atoms",
        "`specs-bkp/`",
        "`memory.py check` exit 0",
        "audit.py close <YYYYMMDD>-first-pass --sha <HEAD sha>",
    ):
        assert statement in section, statement


def _git(repo: Path, *argv: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *argv],
        cwd=repo, capture_output=True, text=True, check=True,
    ).stdout.strip()  # fmt: skip


def _drift(repo: Path, catalog: dict[str, object]) -> subprocess.CompletedProcess[str]:
    product = repo / "specs" / "memory" / "product"
    product.mkdir(parents=True, exist_ok=True)
    (product / "catalog.json").write_text(json.dumps(catalog), encoding="utf-8")
    root = _git(repo, "rev-list", "--max-parents=0", "HEAD")
    return subprocess.run(
        [sys.executable, str(_MEMORY), "drift", "--since", root, "--specs", str(repo / "specs")],
        capture_output=True, text=True, check=False,
    )  # fmt: skip


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    unit = tmp_path / "dadaia_workspace" / "features" / "greet"
    unit.mkdir(parents=True)
    (unit / "core.py").write_text("X = 1\n", encoding="utf-8")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "root")
    return tmp_path


def test_drift_from_root_lists_the_uncovered_unit(repo: Path) -> None:
    result = _drift(repo, {"features": []})
    assert result.returncode == 1, result.stderr
    assert "uncovered dadaia_workspace/features/greet" in result.stdout


def test_drift_from_root_exits_zero_once_the_worklist_is_covered(repo: Path) -> None:
    feature = {"slug": "greet", "path": "p", "sources": ["dadaia_workspace/features/greet/*"]}
    result = _drift(repo, {"features": [feature]})
    assert result.returncode == 0, result.stdout + result.stderr
    assert "nothing drifted" in result.stdout


def test_drift_from_root_lists_units_of_a_consumer_layout(tmp_path: Path) -> None:
    """A consumer repo shares nothing with the library's layout: its units come from its
    own tracked code — every directory holding a code file, outside specs/tests/docs."""
    for path in ("app/core.py", "src/svc/api/routes.ts", "tests/test_core.py", "docs/x.md"):
        (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / path).write_text("x\n", encoding="utf-8")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "root")
    result = _drift(tmp_path, {"features": []})
    assert result.returncode == 1, result.stderr
    listed = [line.split()[1] for line in result.stdout.splitlines() if "uncovered" in line]
    assert listed == ["app", "src/svc/api"]
