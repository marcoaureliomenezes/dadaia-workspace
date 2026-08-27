"""Consumer specs-upgrade path E2E (v0.1.51 FR2 / AC-2).

The upgrade path had ZERO end-to-end coverage: only a unit test asserting the doctor's
staleness WARN message. This E2E runs the REAL command chain a consumer runs —

    dadaia specs upgrade --specs-dir <tree>   (migrate + re-stamp, backup-first)
    dadaia specs init    --specs-dir <tree>   (fill canonical structure, skip existing)
    dadaia specs doctor  --specs-dir <tree>   (must report 0 errors)

on a **below-canonical, structurally-complete** tree: an unstamped constitution
(⇒ version 0) plus the required memory atoms and mandatory dirs, carrying legacy
``foundation/`` + root ``SPEC.md`` (the tree-v2 registry step's input) and one legacy
bug markdown (the bugs-jsonl step's input). Upgrade migrates and re-stamps — it never
scaffolds; ``specs init`` fills canonical gaps without touching existing files. That
composition is exactly what this journey proves doctor-green.

Sandboxed: the tree lives in ``tmp_path``; every command is a bounded real subprocess.
Test-only release: a failure here is a product bug to register, never an inline fix.

Intent: CONTRACT — v0.1.51 FR2 / AC-2 (specs upgrade path)
Owner: software-engineer
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from dadaia_workspace.core.specs_version import CANONICAL_SPECS_VERSION

_MARKER = "specs_pattern_version"


def _cli(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "dadaia_workspace.cli.main", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=120.0,
    )


def _seed_below_canonical_tree(root: Path) -> Path:
    """A structurally-complete specs tree at pattern version 0 with legacy artifacts."""
    specs = root / "consumer" / "specs"
    (specs / "memory" / "product").mkdir(parents=True)
    (specs / "backlog").mkdir()
    (specs / "bugs").mkdir()
    (specs / "releases").mkdir()
    (specs / "foundation").mkdir()

    # Unstamped constitution ⇒ version 0 (below canonical).
    (specs / "constitution.md").write_text(
        "# Constitution — consumer\n\nAbsolute laws of the consumer project.\n",
        encoding="utf-8",
    )
    # The atoms a real consumer authored from the canonical stubs (valid frontmatter —
    # LINT-1 requires it); copied from the package's own scaffold source.
    scaffold_memory = (
        Path(__import__("dadaia_workspace").__file__).parent / "public" / "scaffold" / "memory"
    )
    # This fixture is a deliberately BELOW-canonical (pre-v6, pattern version 0) tree —
    # `specs upgrade` is not grown to rename these case-only (FR1, T-050-05/T-050-06:
    # the rename is a by-hand recipe step, never automated) — so the legacy lowercase
    # destination names are kept on purpose. Only the scaffold SOURCE filenames moved
    # to the v6 canon (ARCHITECTURE.md/TECHSTACK.md/QUALITY.md).
    _legacy_to_canon_source = {
        "architecture.md": "ARCHITECTURE.md",
        "tech-stack.md": "TECHSTACK.md",
        "quality-assurance.md": "QUALITY.md",
    }
    for rel, source_name in _legacy_to_canon_source.items():
        (specs / "memory" / rel).write_text(
            (scaffold_memory / source_name).read_text(encoding="utf-8"), encoding="utf-8"
        )
    (specs / "memory" / "product" / "index.md").write_text(
        (scaffold_memory / "product" / "index.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    for d in ("backlog", "bugs", "releases"):
        (specs / d / "README.md").write_text(f"# {d}\n", encoding="utf-8")
        (specs / d / ".gitkeep").write_text("", encoding="utf-8")

    # Legacy artifacts both registry steps consume: pre-v2 foundation tree + root
    # SPEC.md (tree-v2 moves them under releases/legacy/) and a legacy bug markdown
    # (bugs-jsonl converts it).
    (specs / "foundation" / "vision.md").write_text("# Vision (legacy)\n", encoding="utf-8")
    (specs / "SPEC.md").write_text("# Legacy root SPEC\n", encoding="utf-8")
    (specs / "bugs" / "legacy-sample-bug.md").write_text(
        "---\nname: legacy-sample-bug\nseverity: LOW\nstatus: open\n---\n\n"
        "# BUG — legacy sample\n\nLegacy markdown bug for the 1→2 conversion step.\n",
        encoding="utf-8",
    )
    return specs


def test_upgrade_then_init_reaches_doctor_green_and_at_target_rerun_is_a_no_op(
    tmp_path: Path,
) -> None:
    """AC-2 scenario 1: version-0 tree → upgrade → init → doctor 0 errors.
    AC-2 scenario 2: rerunning upgrade at canonical version makes no new backup."""
    specs = _seed_below_canonical_tree(tmp_path)

    upgrade = _cli(tmp_path, "specs", "upgrade", "--specs-dir", str(specs), "--yes")
    assert upgrade.returncode == 0, upgrade.stderr or upgrade.stdout

    # Backup-first: specs_bkp/<from>→<to>-<UTC>/ beside the tree.
    backups = list((specs / "specs_bkp").glob("*")) + list((specs.parent / "specs_bkp").glob("*"))
    assert backups, "upgrade must create the backup dir before mutating"

    # Re-stamp: constitution frontmatter carries the canonical version.
    constitution = (specs / "constitution.md").read_text(encoding="utf-8")
    assert _MARKER in constitution
    assert str(CANONICAL_SPECS_VERSION) in constitution

    # tree-v2 migration: foundation/ + root SPEC.md relocated under releases/legacy/.
    assert not (specs / "foundation").exists()
    assert not (specs / "SPEC.md").exists()
    legacy_home = specs / "releases" / "legacy"
    assert legacy_home.is_dir(), "tree-v2 must relocate legacy artifacts, not drop them"

    init = _cli(tmp_path, "specs", "init", "--specs-dir", str(specs))
    assert init.returncode == 0, init.stderr or init.stdout

    doctor = _cli(tmp_path, "specs", "doctor", "--specs-dir", str(specs))
    assert doctor.returncode == 0, doctor.stderr or doctor.stdout
    assert "0 error(s)" in doctor.stdout, doctor.stdout

    def _backups() -> set[Path]:
        return set((specs / "specs_bkp").glob("*")) | set((specs.parent / "specs_bkp").glob("*"))

    before = _backups()
    assert before, "first upgrade must have produced a backup"

    second = _cli(tmp_path, "specs", "upgrade", "--specs-dir", str(specs), "--yes")
    assert second.returncode == 0, second.stderr or second.stdout
    assert _backups() == before, "an at-target rerun must be a no-op (no new backup)"
