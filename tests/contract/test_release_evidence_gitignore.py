"""Release governance evidence must be trackable by default."""

from __future__ import annotations

import subprocess
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _check_ignore(path: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "check-ignore", "-q", path],
        cwd=_REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_grill_and_oq_decisions_are_not_ignored() -> None:
    paths = [
        "specs/releases/v9.9.9/GRILL.md",
        "specs/releases/v9.9.9/OQ-DECISIONS.md",
        "specs/releases/v9.9.9/alpha-1/GRILL.md",
        "specs/releases/v9.9.9/alpha-1/OQ-DECISIONS.md",
        "specs/releases/v9.9.9/rc-1/GRILL.md",
        "specs/releases/v9.9.9/rc-1/OQ-DECISIONS.md",
    ]

    ignored = [path for path in paths if _check_ignore(path).returncode == 0]

    assert ignored == []
