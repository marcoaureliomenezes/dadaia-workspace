"""Source-repo hygiene contracts for files that must be visible to review/CI."""

from __future__ import annotations

import subprocess
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _is_ignored(path: str) -> bool:
    result = subprocess.run(
        ["git", "check-ignore", "-q", path],
        cwd=_REPO_ROOT,
        check=False,
    )
    return result.returncode == 0


def test_sdd_release_gate_artifacts_are_not_gitignored() -> None:
    """The SDD gate cannot depend on local-only files hidden from git."""
    visible_paths = [
        "specs/releases/ACTIVE.md",
        "specs/releases/v9.9.9/SPEC.md",
        "specs/releases/v9.9.9/PLAN.md",
        "specs/releases/v9.9.9/TASKS.md",
        "specs/releases/v9.9.9/CLOSURE.md",
        "specs/_archive/releases/v9.9.8/SPEC.md",
        "specs/_archive/releases/v9.9.8/PLAN.md",
        "specs/_archive/releases/v9.9.8/TASKS.md",
        "specs/_archive/releases/v9.9.8/CLOSURE.md",
        # Bug records are repository truth (bug-registration-guardrail); the
        # /specs/* privacy backstop must not hide them from review/CI.
        "specs/bugs/some-bug.md",
        "specs/audits/20991231T235959Z/index.md",
    ]

    ignored = [path for path in visible_paths if _is_ignored(path)]

    assert ignored == []


def test_noncanonical_specs_content_stays_gitignored() -> None:
    """Only canonical lifecycle artifacts are opted back into version control."""
    ignored_paths = [
        "specs/backlog/candidates.md",
        "specs/bugs/non-markdown-attachment.png",
        "specs/releases/v9.9.9/local-notes.md",
        "specs/releases/v9.9.9/tmp/debug.json",
        "specs/_archive/releases/v9.9.8/local-notes.md",
    ]

    not_ignored = [path for path in ignored_paths if not _is_ignored(path)]

    assert not_ignored == []
