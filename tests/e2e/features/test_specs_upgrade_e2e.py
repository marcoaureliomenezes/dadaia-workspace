"""Consumer specs-upgrade path E2E — the v0.5.1 contract (K10, T-051-16).

``dadaia specs upgrade`` re-stamps an upgradable tree (v6 or later) to the canonical
version, folding a consumer's ``memory/TECHSTACK.md`` body into ``ARCHITECTURE.md``'s
``## Tech Stack`` section and deleting the file. A tree ``state`` calls absent, malformed or foreign is
REFUSED (exit non-zero, its one fix printed) and nothing is written; a tree already at the canonical version
is a no-op (exit 0, byte-identical tree). The two scenarios are driven end-to-end through
the real CLI subprocess against a real on-disk tree.

Owner: dd-software-engineer
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

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


def _snapshot(root: Path) -> dict[str, bytes]:
    return {
        str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()
    }


@pytest.mark.parametrize(
    ("constitution", "fix"),
    [
        (None, "specs init --specs-dir {specs}"),
        ("---\nspecs_pattern_version: 7\ngitflow: {principal: main\n---\n", "repair the YAML"),
        (
            "---\nspecs_pattern_version: 5\n---\n# C\n",
            "specs init --specs-dir {specs} --replace-foreign",
        ),
    ],
)
def test_upgrade_refuses_a_tree_state_does_not_walk_and_writes_nothing(
    tmp_path: Path, constitution: str | None, fix: str
) -> None:
    """sa-specs-tree-state-read-five-ways#B28-5: absent/malformed/foreign exit non-zero,
    write nothing and print state()'s fix, never '0.4.x'."""
    specs = tmp_path / "specs"
    if constitution is not None:
        specs.mkdir()
        (specs / "constitution.md").write_text(constitution, encoding="utf-8")
    before = _snapshot(tmp_path)
    upgrade = _cli(tmp_path, "specs", "upgrade", "--specs-dir", str(specs))
    assert upgrade.returncode != 0, upgrade.stdout
    assert fix.format(specs=specs) in upgrade.stderr and "0.4.x" not in upgrade.stderr
    assert _snapshot(tmp_path) == before


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
    # sa-specs-upgrade-stamps-any-target-and-memory-vocabulary-diverges#47.1: no --target.
    assert _cli(root, "specs", "upgrade", "--target", "99").returncode == 2
    assert _snapshot(specs) == before


# ----------------------------------------------------------------- the upgrade hop (FR1)

_V6_ARCHITECTURE = (
    "---\nslug: ARCHITECTURE\ntitle: Architecture\ntldr: Architecture.\nsummary: Architecture.\n"
    "tags:\n  - architecture\n---\n\n# Architecture\n\n## Principles\n\nThe ring holds.\n"
)
_V6_TECHSTACK = (
    "---\nslug: TECHSTACK\ntitle: Tech Stack\n---\n\n"
    "# Tech Stack\n\n## Languages\n\nCONSUMER_STACK_SENTINEL\n"
)


def _seed_v6_tree(root: Path, architecture: str) -> Path:
    """A consumer tree stamped 6, carrying the retired ``memory/TECHSTACK.md``."""
    specs = root / "consumer" / "specs"
    (specs / "memory").mkdir(parents=True)
    (specs / "constitution.md").write_text(
        f"---\n{_MARKER}: 6\n---\n\n# Constitution — consumer\n", encoding="utf-8"
    )
    (specs / "memory" / "ARCHITECTURE.md").write_text(architecture, encoding="utf-8")
    (specs / "memory" / "TECHSTACK.md").write_text(_V6_TECHSTACK, encoding="utf-8")
    return specs


def test_upgrade_folds_techstack_into_architecture_and_deletes_it(tmp_path: Path) -> None:
    """sa-specs-upgrade-stamps-any-target-and-memory-vocabulary-diverges#47.2: the stamp written is exactly CANONICAL_SPECS_VERSION."""
    specs = _seed_v6_tree(tmp_path, _V6_ARCHITECTURE)

    upgrade = _cli(tmp_path, "specs", "upgrade", "--specs-dir", str(specs))

    assert upgrade.returncode == 0, upgrade.stderr or upgrade.stdout
    assert not (specs / "memory" / "TECHSTACK.md").exists(), (
        "the upgrade hop deletes the file it folded"
    )
    architecture = (specs / "memory" / "ARCHITECTURE.md").read_text(encoding="utf-8")
    assert architecture.startswith(_V6_ARCHITECTURE.rstrip("\n")), (
        "the consumer's own architecture text is kept verbatim, ahead of the fold"
    )
    assert "## Tech Stack" in architecture
    # The body moved whole, minus the folded file's own frontmatter and H1 title.
    assert "## Languages\n\nCONSUMER_STACK_SENTINEL" in architecture
    assert "slug: TECHSTACK" not in architecture
    assert architecture.index("## Principles") < architecture.index("## Tech Stack")
    assert f"{_MARKER}: {CANONICAL_SPECS_VERSION}" in (specs / "constitution.md").read_text(
        encoding="utf-8"
    )


def test_upgrade_refuses_a_two_tier_tree_without_stamping_or_writing(tmp_path: Path) -> None:
    """sa-specs-upgrade-stamps-any-target-and-memory-vocabulary-diverges#47.3 (ADR 0082):
    a v6 tree organised as Part 1 / Part 2 has nowhere safe to fold into — the upgrade
    refuses, non-zero, stamp still 6, the tree byte-identical."""
    two_tier = "# Architecture\n\n## Part 1 — Principles\n\nx\n\n## Part 2 — Implementation\n\ny\n"
    specs = _seed_v6_tree(tmp_path, two_tier)
    before = _snapshot(specs)

    upgrade = _cli(tmp_path, "specs", "upgrade", "--specs-dir", str(specs))

    assert upgrade.returncode != 0, upgrade.stdout
    assert "two-tier" in (upgrade.stderr + upgrade.stdout)
    assert _snapshot(specs) == before
    assert f"{_MARKER}: 6" in (specs / "constitution.md").read_text(encoding="utf-8")
