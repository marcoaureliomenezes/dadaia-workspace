"""Root conftest.py — workspace-level pytest fixtures.

TR-3 (T-GOS-A4): repo-root write-backstop guard.

This fixture captures the set of entries present in specific protected directories
at the lib repo root BEFORE each test and asserts that no NEW entries have appeared
in those directories AFTER the test completes.

The guard is intentionally scope=``function`` and autouse=True so it fires around
every test in the suite.  It is implemented as a *root-write guard only* — it does
NOT force-chdir tests to a temporary directory (that would break tests that rely on
their own CWD assumptions).

Protected paths (relative to the repo root, checked recursively):
  .claude/
  .agents/
  .codex/
  .opencode/
  .dadaia/agentic/
  .dadaia/scripts/
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Resolve repo root once at import time.
# tests/ lives one level below the repo root, so __file__/../.. is the root.
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).parent.parent.resolve()

# Directories (relative to repo root) whose contents must not grow during a test.
_GUARDED_DIRS: tuple[str, ...] = (
    ".claude",
    ".agents",
    ".codex",
    ".opencode",
    os.path.join(".dadaia", "agentic"),
    os.path.join(".dadaia", "scripts"),
)


def _collect_entries(root: Path, rel_dirs: tuple[str, ...]) -> frozenset[str]:
    """Return the set of all file paths (as strings) within the guarded dirs."""
    entries: set[str] = set()
    for rel in rel_dirs:
        guarded = root / rel
        if not guarded.exists():
            continue
        for path in guarded.rglob("*"):
            if path.is_file():
                entries.add(str(path))
    return frozenset(entries)


@pytest.fixture(autouse=True)
def _repo_root_write_guard() -> object:
    """Assert no new files appear in protected lib-repo paths during a test.

    Yields control to the test, then compares the file-set snapshot taken
    before the test against the one taken after.  If new files appear, the
    test fails with a descriptive message listing the offending paths.
    """
    before = _collect_entries(_REPO_ROOT, _GUARDED_DIRS)
    yield
    after = _collect_entries(_REPO_ROOT, _GUARDED_DIRS)
    new_files = after - before
    if new_files:
        formatted = "\n  ".join(sorted(new_files))
        pytest.fail(
            f"Test wrote unexpected files into protected lib-repo paths:\n  {formatted}\n"
            "These directories must not be modified by tests: "
            + ", ".join(_GUARDED_DIRS)
        )
