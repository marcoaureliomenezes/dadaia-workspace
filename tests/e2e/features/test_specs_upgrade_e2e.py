"""Consumer specs-upgrade path E2E — the v0.5.1 contract (K10, T-051-16).

``dadaia specs upgrade`` no longer carries the pre-v6 migration chain: a tree below the
canonical pattern version is REFUSED (exit non-zero, message names the 0.4.x release that
still carries the chain) and nothing is written; a tree already at the canonical version
is a no-op (exit 0, byte-identical tree). The two scenarios are driven end-to-end through
the real CLI subprocess against a real on-disk tree.

Intent: CONTRACT — v0.1.51 FR2 / AC-2 (specs upgrade path), rewritten at v0.5.1 K10. Size: LARGE (subprocess).
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


def _snapshot(root: Path) -> dict[str, bytes]:
    return {
        str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()
    }


def test_upgrade_refuses_a_tree_below_the_canonical_version_and_writes_nothing(
    tmp_path: Path,
) -> None:
    specs = _seed_below_canonical_tree(tmp_path)
    before = _snapshot(specs)

    upgrade = _cli(tmp_path, "specs", "upgrade", "--specs-dir", str(specs))

    assert upgrade.returncode != 0, upgrade.stdout
    assert "0.4.x" in (upgrade.stderr + upgrade.stdout)
    assert _snapshot(specs) == before, "a refused upgrade must not touch the tree"
    assert not list(tmp_path.rglob("*backup*")), "no backup dir is created on refusal"


def test_upgrade_at_the_canonical_version_is_a_byte_identical_no_op(tmp_path: Path) -> None:
    root = tmp_path / "consumer"
    root.mkdir()
    init = _cli(root, "specs", "init", "--specs-dir", str(root / "specs"))
    assert init.returncode == 0, init.stderr or init.stdout
    specs = root / "specs"
    assert str(CANONICAL_SPECS_VERSION) in (specs / "constitution.md").read_text(encoding="utf-8")
    before = _snapshot(specs)

    upgrade = _cli(root, "specs", "upgrade", "--specs-dir", str(specs))

    assert upgrade.returncode == 0, upgrade.stderr or upgrade.stdout
    assert _snapshot(specs) == before
