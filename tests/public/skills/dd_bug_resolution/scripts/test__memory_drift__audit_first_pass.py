"""`memory.py drift
--since <root commit>` is a runnable worklist on a consumer layout. Size: SMALL.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tests.helpers.oslib import run, write_text

_REPO = Path(__file__).resolve().parents[5]
_SKILLS = _REPO / "dadaia_workspace" / "public" / "skills"
_MEMORY = _SKILLS / "dd-spec-navigator" / "scripts" / "memory.py"


def _git(repo: Path, *argv: str) -> str:
    return run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *argv], cwd=repo, check=True).stdout.strip()  # fmt: skip


def _drift(repo: Path, catalog: dict[str, object]) -> subprocess.CompletedProcess[str]:
    product = repo / "specs" / "memory" / "product"
    product.mkdir(parents=True, exist_ok=True)
    write_text(product / "catalog.json", json.dumps(catalog))
    root = _git(repo, "rev-list", "--max-parents=0", "HEAD")
    return run([sys.executable, str(_MEMORY), "drift", "--since", root, "--specs", str(repo / "specs")], check=False)  # fmt: skip


def test_drift_from_root_lists_units_of_a_consumer_layout(tmp_path: Path) -> None:
    """A consumer repo shares nothing with the library's layout: its units come from its
    own tracked code — every directory holding a code file, outside specs/tests/docs."""
    for path in ("app/core.py", "src/svc/api/routes.ts", "tests/test_core.py", "docs/x.md"):
        (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
        write_text(tmp_path / path, "x\n")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "root")
    result = _drift(tmp_path, {"features": []})
    assert result.returncode == 1, result.stderr
    listed = [line.split()[1] for line in result.stdout.splitlines() if "uncovered" in line]
    assert listed == ["app", "src/svc/api"]


def test_drift_demands_no_atom_for_the_specs_backup_specs_init_writes(tmp_path: Path) -> None:
    """`specs-bkp/` and `specs-bkp/<UTC>/` hold the foreign specs `specs init` moved aside,
    like `specs/`: no unit, so no atom is demanded for them."""
    for path in ("app/core.py", "specs-bkp/old/notes.py", "specs-bkp/2026-10-25T170000Z/x/y.py"):
        (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
        write_text(tmp_path / path, "x\n")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "root")
    result = _drift(tmp_path, {"features": []})
    listed = [line.split()[1] for line in result.stdout.splitlines() if "uncovered" in line]
    assert listed == ["app"]
