"""Session-bound context residue contract.

The v2 context model is session-bound. Active product code must not operate on a
global primary context, except for explicit legacy migration/import cleanup that
removes retired state from old workspaces.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ResiduePattern:
    pattern: str
    reason: str


@dataclass(frozen=True)
class ResidueClassification:
    relpath: str
    patterns: tuple[ResiduePattern, ...]
    disposition: str


ACTIVE_RESIDUE_PATTERNS: tuple[str, ...] = (
    "primary_context",
    "PRIMARY_",
    "is_primary",
    "context promote",
    "context activate",
)

ALLOWED_LEGACY_RESIDUE: tuple[ResidueClassification, ...] = (
    ResidueClassification(
        relpath="dadaia_workspace/features/migrate/state_v2.py",
        patterns=(
            ResiduePattern("primary_context", "delete legacy primary_context.json during v1->v2"),
            ResiduePattern("is_primary", "remove legacy is_primary during v1->v2"),
        ),
        disposition="keep as explicit legacy migration cleanup",
    ),
    ResidueClassification(
        relpath="dadaia_workspace/features/import_/service.py",
        patterns=(
            ResiduePattern("primary_context", "delete imported legacy primary_context.json"),
            ResiduePattern("is_primary", "strip imported legacy is_primary fields"),
        ),
        disposition="keep as explicit import compatibility cleanup",
    ),
    ResidueClassification(
        relpath="dadaia_workspace/cli/commands/migrate.py",
        patterns=(
            ResiduePattern("primary_context", "delete legacy primary_context.json during v1->v2"),
            ResiduePattern("is_primary", "report legacy is_primary field removal during v1->v2"),
        ),
        disposition="keep as explicit legacy migration cleanup",
    ),
)

EXPECTED_RESIDUE_TO_REMOVE: tuple[ResidueClassification, ...] = (
    ResidueClassification(
        relpath="tests",
        patterns=(
            ResiduePattern("primary_context", "tests/helpers still use retired terminology"),
            ResiduePattern("PRIMARY_", "tests still assert primary variable names"),
            ResiduePattern("is_primary", "tests still assert retired panel/context fields"),
            ResiduePattern("context activate", "tests still describe removed verb"),
        ),
        disposition="rename/remove or move into explicit migration compatibility tests in T-BUG-06",
    ),
)


def _matches_prefix(relpath: str, prefix: str) -> bool:
    return relpath == prefix or relpath.startswith(prefix.rstrip("/") + "/")


def classify_residue_hit(relpath: str, text: str) -> ResidueClassification | None:
    """Return the allowed/expected classification for a residue hit.

    A ``None`` return is a failure condition: the hit is neither an explicit
    legacy cleanup exception nor part of the known residue inventory for this
    release.
    """
    candidates = (*ALLOWED_LEGACY_RESIDUE, *EXPECTED_RESIDUE_TO_REMOVE)
    for classification in candidates:
        if not _matches_prefix(relpath, classification.relpath):
            continue
        if any(pattern.pattern in text for pattern in classification.patterns):
            return classification
    return None


def test_legacy_primary_context_exceptions_are_migration_or_import_cleanup_only() -> None:
    """Allowed exceptions must stay narrow and explicitly cleanup-oriented."""
    cleanup_paths = {entry.relpath for entry in ALLOWED_LEGACY_RESIDUE}

    assert cleanup_paths == {
        "dadaia_workspace/cli/commands/migrate.py",
        "dadaia_workspace/features/migrate/state_v2.py",
        "dadaia_workspace/features/import_/service.py",
    }
    for entry in ALLOWED_LEGACY_RESIDUE:
        assert "cleanup" in entry.disposition or "migration" in entry.disposition


def test_current_residue_inventory_is_classified() -> None:
    """T-BUG-01 classifies active residue so later tasks can remove it deliberately."""
    relpaths = {entry.relpath for entry in EXPECTED_RESIDUE_TO_REMOVE}

    assert "tests" in relpaths


def test_unclassified_primary_context_residue_is_a_failure() -> None:
    """Any future hit outside the exception/inventory list must be rejected."""
    assert classify_residue_hit("dadaia_workspace/unknown.py", "primary_context") is None


def test_classification_paths_exist() -> None:
    """Every file-level classification must point at an existing source path."""
    repo_root = Path(__file__).resolve().parents[2]

    for entry in (*ALLOWED_LEGACY_RESIDUE, *EXPECTED_RESIDUE_TO_REMOVE):
        if entry.relpath in {"specs/memory", "tests", "dadaia_workspace/features/panel"}:
            assert (repo_root / entry.relpath).is_dir()
        else:
            assert (repo_root / entry.relpath).exists()
