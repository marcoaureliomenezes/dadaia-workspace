"""Every public install is whole: no scope flag exists, and the staged set is the
public walk's set.

sa-scoped-public-install-prunes-the-gate-wiring#L1 and #L4.
"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.infrastructure.install_plan import InstallPlan


def test_public_install_has_no_only_option() -> None:
    """sa-scoped-public-install-prunes-the-gate-wiring#L1: Click rejects --only (exit 2)."""
    result = CliRunner().invoke(app, ["public", "install", "--only", "skills"])
    assert result.exit_code == 2


def test_one_install_plan_decides_full_for_table_and_reconciler() -> None:
    """sa-scoped-public-install-prunes-the-gate-wiring#L4: InstallPlan carries no `only`
    and the reconciler's `full` reads the plan, not a second predicate."""
    assert "only" not in InstallPlan.__dataclass_fields__
    root = Path(__file__).resolve().parents[3] / "dadaia_workspace" / "infrastructure"
    assert "full=plan.harness is None" in (root / "public_assets.py").read_text(encoding="utf-8")
    for name in ("public_assets.py", "projection_rules.py", "agent_transcodes.py"):
        assert "plan.only" not in (root / name).read_text(encoding="utf-8")
