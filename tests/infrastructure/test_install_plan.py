"""Every public install is whole: no scope flag exists, and the staged set is the
public walk's set.

"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.infrastructure.install_plan import InstallPlan
from tests.helpers.oslib import read_text


def test_public_install_has_no_only_option() -> None:
    """Click rejects --only (exit 2)."""
    result = CliRunner().invoke(app, ["public", "install", "--only", "skills"])
    assert result.exit_code == 2


def test_one_install_plan_decides_full_for_table_and_reconciler() -> None:
    """InstallPlan carries no `only`
    and the reconciler's `full` reads the plan, not a second predicate."""
    assert "only" not in InstallPlan.__dataclass_fields__
    root = Path(__file__).resolve().parents[2] / "dadaia_workspace" / "infrastructure"
    assert "full=plan.harness is None" in read_text(root / "public_assets.py")
    for name in ("public_assets.py", "projection_rules.py", "agent_transcodes.py"):
        assert "plan.only" not in read_text(root / name)
