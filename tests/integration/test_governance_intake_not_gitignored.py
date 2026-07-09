"""T-70-03/04 (FR2): governance-intake paths must not be git-ignored.

``.gitignore`` opts governance-intake Markdown back into version control for
``specs/bugs/`` and ``specs/backlog/`` (see the ``backlog/_archive`` idiom),
but ``/specs/backlog/*`` (line 134) excludes the ``remote-bugs/`` subtree with
no negation, so new ``remote-bugs/*.md`` intake reports are silently
git-ignored. This is an executed-path repo-hygiene test: it writes real probe
files under the repo's working tree and asks the real ``git`` binary via
``git check-ignore`` whether they are ignored, then cleans them up.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from uuid import uuid4

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _is_ignored(repo_root: Path, relative_path: str) -> bool:
    result = subprocess.run(
        ["git", "check-ignore", "-q", relative_path],
        cwd=repo_root,
        check=False,
    )
    return result.returncode == 0


@pytest.fixture
def probe_paths() -> list[Path]:
    """Real probe *.md files under the governance-intake subtrees + controls.

    Written directly under the real repo working tree (not tmp_path) because
    ``git check-ignore`` evaluates against the real ``.gitignore`` at
    ``_REPO_ROOT``; the files are removed in the fixture teardown regardless
    of test outcome.
    """
    token = uuid4().hex[:8]
    paths = [
        _REPO_ROOT / "specs" / "bugs" / f"probe-{token}.md",
        _REPO_ROOT / "specs" / "backlog" / f"probe-{token}.md",
        _REPO_ROOT / "specs" / "backlog" / "remote-bugs" / f"probe-{token}.md",
        _REPO_ROOT / "specs" / "backlog" / "remote-bugs" / "_archive" / f"probe-{token}.md",
    ]
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# probe\n\nGovernance-intake gitignore probe.\n", encoding="utf-8")
    yield paths
    for path in paths:
        path.unlink(missing_ok=True)


def test_bugs_intake_probe_not_ignored(probe_paths: list[Path]) -> None:
    """Control: specs/bugs/*.md is already opted back in — must not be ignored."""
    relative = probe_paths[0].relative_to(_REPO_ROOT).as_posix()
    assert not _is_ignored(_REPO_ROOT, relative), (
        f"{relative} is unexpectedly git-ignored (control regression)"
    )


def test_backlog_top_level_probe_not_ignored(probe_paths: list[Path]) -> None:
    """Control: specs/backlog/*.md is already opted back in — must not be ignored."""
    relative = probe_paths[1].relative_to(_REPO_ROOT).as_posix()
    assert not _is_ignored(_REPO_ROOT, relative), (
        f"{relative} is unexpectedly git-ignored (control regression)"
    )


def test_remote_bugs_intake_probe_not_ignored(probe_paths: list[Path]) -> None:
    """FR2 subject: specs/backlog/remote-bugs/*.md must not be git-ignored.

    RED today: /specs/backlog/* (line 134) excludes the remote-bugs/ subtree
    with no negation, so this probe IS ignored on current code.
    """
    relative = probe_paths[2].relative_to(_REPO_ROOT).as_posix()
    assert not _is_ignored(_REPO_ROOT, relative), (
        f"{relative} is git-ignored — the remote-bugs/ intake subtree has no negation in .gitignore"
    )


def test_remote_bugs_archive_probe_not_ignored(probe_paths: list[Path]) -> None:
    """FR2 subject: specs/backlog/remote-bugs/_archive/*.md must not be git-ignored.

    RED today: same root cause as the remote-bugs/ probe above.
    """
    relative = probe_paths[3].relative_to(_REPO_ROOT).as_posix()
    assert not _is_ignored(_REPO_ROOT, relative), (
        f"{relative} is git-ignored — the remote-bugs/_archive/ intake subtree "
        "has no negation in .gitignore"
    )
