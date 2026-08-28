"""Intent: CONTRACT — bug dadaia-reconcile-quarantines-sanctioned-references-clone.

``dadaia reconcile`` / ``dadaia migrate`` quarantine known-legacy ``.dadaia/`` top-level
subdirs via :func:`quarantine_legacy_dadaia_dirs`. Operator ruling O4 (v0.4.5, T-045-23,
FR10) sanctioned ``.dadaia/references/<clone>/`` as a permanent, documented subdir
(``DoctorService._DADAIA_ALLOWED_SUBDIRS``) — but ``LEGACY_DADAIA_SUBDIRS`` still listed
``"references"`` as a hand-copied, unsynchronized duplicate of the same fact, so
reconcile kept moving an operator-placed reference clone into quarantine on every run.

The fix ties the two together at one source (``core.workspace_layout.DADAIA_ALLOWED_SUBDIRS``)
instead of hand-duplicating membership — see
``tests/contract/test_workspace_layout_single_authority.py`` for the structural proof.
This module proves the behavioral consequence on the real seam ``dadaia reconcile`` calls.
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.features.migrate.legacy_dadaia_dirs import (
    LEGACY_DADAIA_SUBDIRS,
    quarantine_legacy_dadaia_dirs,
)


def _plant_reference_clone(root: Path, clone: str = "mattpocock-skills") -> Path:
    """Plant an operator-owned reference clone with real content, as ``git clone`` would."""
    clone_dir = root / ".dadaia" / "references" / clone
    (clone_dir / ".git").mkdir(parents=True)
    (clone_dir / "README.md").write_text("# reference material\n", encoding="utf-8")
    return clone_dir


def test_sanctioned_reference_clone_is_never_quarantined(tmp_path: Path) -> None:
    """RED before the fix: 'references' was still in LEGACY_DADAIA_SUBDIRS, so this
    moved the clone into .dadaia/tmp/legacy-quarantine/. GREEN after: the clone and its
    content are left byte-for-byte untouched at its original path."""
    clone_dir = _plant_reference_clone(tmp_path)
    before = (clone_dir / "README.md").read_text(encoding="utf-8")

    moved = quarantine_legacy_dadaia_dirs(tmp_path)

    assert moved == []
    assert clone_dir.exists()
    assert (clone_dir / ".git").exists()
    assert (clone_dir / "README.md").read_text(encoding="utf-8") == before
    assert not (tmp_path / ".dadaia" / "tmp" / "legacy-quarantine").exists()


def test_genuinely_legacy_dirs_are_still_quarantined_alongside_a_reference_clone(
    tmp_path: Path,
) -> None:
    """The fix must not over-correct: real pre-0.2.x legacy leftovers (e.g. 'bugs')
    are still quarantined even while a sanctioned reference clone sits untouched next
    to them in the same run."""
    clone_dir = _plant_reference_clone(tmp_path)
    (tmp_path / ".dadaia" / "bugs" / "legacy-report.md").parent.mkdir(parents=True)
    (tmp_path / ".dadaia" / "bugs" / "legacy-report.md").write_text("x", encoding="utf-8")

    moved = quarantine_legacy_dadaia_dirs(tmp_path)

    assert moved == ["bugs"]
    assert clone_dir.exists()
    assert not (tmp_path / ".dadaia" / "bugs").exists()


def test_legacy_candidate_set_excludes_references() -> None:
    """Direct pin on the exported constant: 'references' is no longer a member."""
    assert "references" not in LEGACY_DADAIA_SUBDIRS
