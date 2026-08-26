"""CLI-level regression for bug ``symlinked-specs-root-is-followed-by-migration-and-repair``
(T-044-40, LOW, security-reviewer, CWE-59).

Before the fix, ``core.specs_resolver.resolve_specs_dir`` called ``Path(specs_dir)
.resolve()`` unconditionally on an explicit ``--specs-dir``, silently following a
symlinked root the caller named. The inner walk roots this same package already
refuses to follow (``migrate_retired_frontmatter_keys``'s ``memory/`` walk root,
``SpecsDoctor``'s TREE-5 projection target — pinned in
``tests/unit/features/specs/test_migration_symlink_hardening.py``) never even saw the
link, because the OUTER root had already been dereferenced one level up, at the one
resolution seam every resolver-driven verb shares.

This file pins the decision — refuse, uniformly, once, at that seam — through BOTH
entry points the bug named, proving the fix is not duplicated per write site (the
puxadinho this bug forbids): ``specs upgrade`` and ``specs doctor --fix``.

Intent: CONTRACT (bug ``symlinked-specs-root-is-followed-by-migration-and-repair``,
T-044-40).
Size: MEDIUM (CliRunner over the real ``app``, real tmp filesystem).
Owner: software-engineer
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app

pytestmark = [pytest.mark.integration]

_runner = CliRunner()

_ATOM_WITH_RETIRED_KEYS = "---\nslug: x\nagent_tier: self-pull\ntoken_estimate: 999\n---\n\nBody.\n"


def _symlinked_specs_root(tmp_path: Path) -> tuple[Path, Path]:
    """A real specs/ tree (with content a migration would otherwise rewrite) behind a
    symlinked root the caller names — the exact shape the bug's own repro builds."""
    real = tmp_path / "real-specs"
    (real / "memory").mkdir(parents=True)
    (real / "memory" / "atom.md").write_text(_ATOM_WITH_RETIRED_KEYS, encoding="utf-8")
    linked = tmp_path / "proj" / "specs"
    linked.parent.mkdir(parents=True)
    linked.symlink_to(real, target_is_directory=True)
    return real, linked


def test_cli_specs_upgrade_refuses_a_symlinked_root(tmp_path: Path) -> None:
    real, linked = _symlinked_specs_root(tmp_path)
    before = (real / "memory" / "atom.md").read_text(encoding="utf-8")

    result = _runner.invoke(app, ["specs", "upgrade", "--specs-dir", str(linked), "--yes"])

    assert result.exit_code != 0, result.output
    assert "symlink" in result.output.lower(), result.output
    assert (real / "memory" / "atom.md").read_text(encoding="utf-8") == before, (
        "upgrade wrote through the symlinked root"
    )
    assert not any(tmp_path.rglob("specs_bkp")), "upgrade took a backup behind the refused link"


def test_cli_specs_doctor_fix_refuses_a_symlinked_root(tmp_path: Path) -> None:
    real, linked = _symlinked_specs_root(tmp_path)
    before = (real / "memory" / "atom.md").read_text(encoding="utf-8")

    result = _runner.invoke(app, ["specs", "doctor", "--specs-dir", str(linked), "--fix"])

    assert result.exit_code != 0, result.output
    assert "symlink" in result.output.lower(), result.output
    assert (real / "memory" / "atom.md").read_text(encoding="utf-8") == before, (
        "doctor --fix wrote through the symlinked root"
    )
