"""The one enumeration of the test suite every ratchet pins (bug
``v26-ratchet-scans-tests-tmp-scratch-dir-xdist-race``).

A ratchet measures the TRACKED suite — what git holds — never whatever transient file a
concurrent xdist worker is writing and deleting under ``tests/tmp/`` at that instant.
``git ls-files`` is that definition in one call: scratch probes, ``__pycache__`` and every
ignored path are outside it by construction, so no walker needs its own exclusion rule.
"""

from __future__ import annotations

import fnmatch
import subprocess
from pathlib import Path


def tracked_test_files(repo_root: Path, pattern: str = "*.py") -> list[Path]:
    """Every git-tracked file under ``tests/`` whose basename matches *pattern*, sorted."""
    result = subprocess.run(
        ["git", "ls-files", "-z", "--", "tests"],
        cwd=repo_root,
        capture_output=True,
        check=True,
    )
    return sorted(
        repo_root / entry
        for entry in result.stdout.decode("utf-8").split("\0")
        if entry and fnmatch.fnmatch(Path(entry).name, pattern)
    )
