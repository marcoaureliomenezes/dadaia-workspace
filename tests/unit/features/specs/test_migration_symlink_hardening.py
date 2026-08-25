"""Security review of the 0.4.3 mint — the write sites must never follow a link, and one
bad atom must never strand a half-migrated tree.

Intent: REGRESSION (security-reviewer findings on the 0.4.3 develop delta: CWE-59/CWE-61
link following, CWE-73 externally supplied path, CWE-703 unchecked exceptional condition,
CWE-674 uncontrolled recursion; bug
``atomic-writer-drift-guard-is-brittle-and-covers-only-two-of-eight-writers`` — T-044-35).
Size: SMALL.

This repo has already paid for the link-following class once (the dangling
``tests/AGENTS.md`` symlink). These tests pin the doctrine at every write site introduced
or touched by the retired-frontmatter-keys work, so the third recurrence cannot happen
quietly.

v0.4.5 FR2/T-045-14 history: this file used to ALSO carry a hand-kept, 10-case
``AtomicWriterCase`` battery pinning behaviour (hardlink rebind, CRLF-freedom, mode
preservation, temp-cleanup-on-injected-``os.replace``-failure) across every named/inline
atomic writer in the package — including the bug's own characterization test, which
pinned the *leaking* behaviour of 2 of those writers as CURRENT (bug
``two-atomic-writers-leak-temp-file-on-injected-os-replace-failure``). T-045-14 deleted
every one of those writers: every call site in the package now delegates directly to
``core.atomic_write.atomic_write``, so leaking is structurally impossible and the
characterization test that pinned it is dead by construction — deleting a test that
outlived its subject, per A2.4, rather than leaving a self-destructing tombstone. The
hand-kept 10-case table itself is exactly the pattern A2.2 forbids (a hand-kept census);
it is superseded by the derived, scan-based census in
``tests/unit/core/test_atomic_write_census.py``, and the primitive's own full
preserve-mode x content-kind x failure-point matrix already lives in
``tests/unit/core/test_atomic_write.py`` — nothing here duplicated either without a
hand-kept list of writer names to maintain, so nothing of that battery survives in this
file.
"""

from __future__ import annotations

import json
from pathlib import Path

from dadaia_workspace.features.migrate.agent_tier_frontmatter import (
    migrate_agent_tier_frontmatter,
)
from dadaia_workspace.features.migrate.retired_frontmatter_keys import (
    migrate_retired_frontmatter_keys,
)
from dadaia_workspace.features.specs.doctor import SpecsDoctor
from dadaia_workspace.features.specs.template_history import (
    SHIPPED_HASHES_FILENAME,
    load_shipped_hashes,
)

_REPO_ROOT = Path(__file__).parents[4]
_TEMPLATES_DIR = _REPO_ROOT / "dadaia_workspace" / "public" / "templates"
_CANONICAL_TEXT = (_TEMPLATES_DIR / "specs-AGENTS.md").read_text(encoding="utf-8")

_ATOM_WITH_RETIRED_KEYS = "---\nslug: x\nagent_tier: self-pull\ntoken_estimate: 999\n---\n\nBody.\n"


def _specs_with_memory(root: Path) -> Path:
    specs = root / "specs"
    (specs / "memory").mkdir(parents=True)
    return specs


def test_migrations_never_write_through_a_symlinked_atom(tmp_path: Path) -> None:
    """A symlinked atom points at a file outside the tree being migrated; both migration
    steps must leave it — and its target — untouched."""
    for name, migrate in (
        ("retired", migrate_retired_frontmatter_keys),
        ("agent-tier", migrate_agent_tier_frontmatter),
    ):
        outside = tmp_path / f"{name}-outside.md"
        outside.write_text(_ATOM_WITH_RETIRED_KEYS, encoding="utf-8")
        specs = _specs_with_memory(tmp_path / name)
        (specs / "memory" / "linked.md").symlink_to(outside)

        result = migrate(specs, dry_run=False)

        assert outside.read_text(encoding="utf-8") == _ATOM_WITH_RETIRED_KEYS, (
            f"{name} migration wrote through a symlink"
        )
        assert result.moved == []
        assert any("symlink" in note for note in result.skipped)


def test_one_unreadable_atom_does_not_strand_the_tree(tmp_path: Path) -> None:
    """A dangling link must not abort the run: every healthy atom still migrates and the
    skip is reported instead of raised."""
    specs = _specs_with_memory(tmp_path / "mixed")
    (specs / "memory" / "dangling.md").symlink_to(tmp_path / "nope.md")
    healthy = specs / "memory" / "healthy.md"
    healthy.write_text(_ATOM_WITH_RETIRED_KEYS, encoding="utf-8")

    result = migrate_retired_frontmatter_keys(specs, dry_run=False)

    assert "token_estimate" not in healthy.read_text(encoding="utf-8")
    assert result.moved and result.skipped


def test_fix_tree5_refuses_a_symlinked_projection(tmp_path: Path) -> None:
    """The repair must not write the canonical template through a link, and must ignore a
    caller-supplied path — the target is always derived from the specs dir."""
    stale = "# stale\n"
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / "specs-AGENTS.md").write_text(_CANONICAL_TEXT, encoding="utf-8")
    import hashlib

    (templates / SHIPPED_HASHES_FILENAME).write_text(
        json.dumps(
            {
                "specs-AGENTS.md": [
                    hashlib.sha256(t.encode("utf-8")).hexdigest() for t in (_CANONICAL_TEXT, stale)
                ]
            }
        ),
        encoding="utf-8",
    )

    outside = tmp_path / "outside_agents.md"
    outside.write_text(stale, encoding="utf-8")
    specs = _specs_with_memory(tmp_path / "linked")
    (specs / "AGENTS.md").symlink_to(outside)

    doctor = SpecsDoctor(specs, templates_dir=templates)
    doctor.fix(doctor.check())

    assert outside.read_text(encoding="utf-8") == stale, "fix_tree5 wrote through a symlink"


def test_corrupt_history_degrades_instead_of_killing_the_doctor(tmp_path: Path) -> None:
    """A deeply nested history blows the JSON parser's stack; it must degrade to "nothing
    is provably ours" like every other malformation."""
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / SHIPPED_HASHES_FILENAME).write_text("[" * 200_000, encoding="utf-8")

    assert load_shipped_hashes(templates) == {}


def test_migrations_never_write_through_a_hardlink(tmp_path: Path) -> None:
    """A hard link is not a symlink, so the link guard alone misses it: writing must
    rebind the name (temp file + os.replace) instead of writing through the inode."""
    import os

    outside = tmp_path / "hardlink-outside.md"
    outside.write_text(_ATOM_WITH_RETIRED_KEYS, encoding="utf-8")
    specs = _specs_with_memory(tmp_path / "hardlink")
    os.link(outside, specs / "memory" / "linked.md")

    migrate_retired_frontmatter_keys(specs, dry_run=False)

    assert outside.read_text(encoding="utf-8") == _ATOM_WITH_RETIRED_KEYS, (
        "migration wrote through a hard link into a file outside the tree"
    )
    assert "token_estimate" not in (specs / "memory" / "linked.md").read_text(encoding="utf-8")


def test_symlinked_projection_is_not_advertised_as_fixable(tmp_path: Path) -> None:
    """The repair refuses a symlinked projection, so the check must not promise it —
    a reported fix that never happens is its own defect."""
    import hashlib

    stale = "# stale\n"
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / "specs-AGENTS.md").write_text(_CANONICAL_TEXT, encoding="utf-8")
    (templates / SHIPPED_HASHES_FILENAME).write_text(
        json.dumps(
            {
                "specs-AGENTS.md": [
                    hashlib.sha256(t.encode("utf-8")).hexdigest() for t in (_CANONICAL_TEXT, stale)
                ]
            }
        ),
        encoding="utf-8",
    )
    outside = tmp_path / "outside.md"
    outside.write_text(stale, encoding="utf-8")
    specs = _specs_with_memory(tmp_path / "advertise")
    (specs / "AGENTS.md").symlink_to(outside)

    doctor = SpecsDoctor(specs, templates_dir=templates)
    tree5 = [i for i in doctor.check() if i.code == "TREE-5"]
    assert tree5 and not tree5[0].fixable
    assert doctor.fix(doctor.check()) == [] or all(i.code != "TREE-5" for i in doctor.fix())


def test_repair_preserves_file_mode_and_newlines(tmp_path: Path) -> None:
    """Atomic replacement must not leak mkstemp's 0600 onto the target, nor let Windows
    text mode rewrite LF as CRLF — the write is byte-exact by contract."""
    import os
    import stat

    specs = _specs_with_memory(tmp_path / "mode")
    atom = specs / "memory" / "a.md"
    atom.write_text(_ATOM_WITH_RETIRED_KEYS, encoding="utf-8", newline="")  # T-044-36
    os.chmod(atom, 0o644)
    # Assert PRESERVATION against the mode actually on disk, never a hard-coded 0o644:
    # Windows has no POSIX mode bits (chmod only toggles the read-only attribute, so every
    # file reads back 0o666) and the contract under test is "the repair does not change the
    # mode", which is exactly what this comparison states on every platform.
    before = stat.S_IMODE(atom.stat().st_mode)

    migrate_retired_frontmatter_keys(specs, dry_run=False)

    assert stat.S_IMODE(atom.stat().st_mode) == before, "repair changed the atom's mode"
    assert b"\r\n" not in atom.read_bytes(), "repair introduced CRLF"


def test_symlinked_memory_directory_is_refused(tmp_path: Path) -> None:
    """The walk ROOT can itself be a link out of the tree: the per-file guard cannot see
    it, because every atom inside is a regular file."""
    outside = tmp_path / "outside-memory"
    outside.mkdir()
    victim = outside / "c.md"
    victim.write_text(_ATOM_WITH_RETIRED_KEYS, encoding="utf-8")

    specs = tmp_path / "rootlink" / "specs"
    specs.mkdir(parents=True)
    (specs / "memory").symlink_to(outside, target_is_directory=True)

    result = migrate_retired_frontmatter_keys(specs, dry_run=False)

    assert victim.read_text(encoding="utf-8") == _ATOM_WITH_RETIRED_KEYS
    assert result.moved == []
    assert any("symlink" in note for note in result.skipped)


def test_read_only_atom_is_left_alone(tmp_path: Path) -> None:
    """Replacement needs only directory permission, so a read-only atom would be rewritten
    silently; the operator's flag is honoured instead."""
    import os

    specs = _specs_with_memory(tmp_path / "readonly")
    atom = specs / "memory" / "ro.md"
    atom.write_text(_ATOM_WITH_RETIRED_KEYS, encoding="utf-8")
    os.chmod(atom, 0o444)
    try:
        result = migrate_retired_frontmatter_keys(specs, dry_run=False)
        assert atom.read_text(encoding="utf-8") == _ATOM_WITH_RETIRED_KEYS
        assert any("read-only" in note for note in result.skipped)
    finally:
        os.chmod(atom, 0o644)
