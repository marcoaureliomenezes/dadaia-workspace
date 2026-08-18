"""v0.4.3 T-043-21/FR17: the repo-AGENTS.md destination refuses a symlink.

Intent: CONTRACT — v0.4.3 A17.1, A17.2.

``alive()``'s ``repo-AGENTS.md`` write (``features/spec_context/service.py``) carried
ZERO symlink refusals while its own SIBLING seam right below it — the conditional
``tests/AGENTS.md`` copy — already refuses BOTH a symlinked containing directory and a
symlinked (including dangling) destination file
(``tests/unit/features/spec_context/test_tests_agents_scaffold.py``, T-070-09 finding 7
and the v0.7.0 ship-review LOW). This file mirrors that hardened sibling seam's exact
two-tier defense (parent-containment symlink + destination-file symlink, both dangling
and non-dangling) onto the repo-AGENTS.md write, one fixture per refusal site — and
proves the clean/positive-control path is unaffected.
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("fcntl")

from pathlib import Path  # noqa: E402

from dadaia_workspace.features.spec_context import service as service_module  # noqa: E402
from dadaia_workspace.features.spec_context.service import (  # noqa: E402
    _PUBLIC_DIR,
    SpecContextService,
)
from tests.fakes import FakeContextStore, FakeGitClient  # noqa: E402

_TEMPLATE = _PUBLIC_DIR / "templates" / "repo-AGENTS.md"


@pytest.fixture()
def workspace_root(tmp_path: Path) -> Path:
    root = tmp_path / "ws"
    root.mkdir()
    (root / "repos").mkdir()
    return root


@pytest.fixture()
def service(workspace_root: Path) -> SpecContextService:
    return SpecContextService(
        context_store=FakeContextStore(),
        git_client=FakeGitClient(),
        workspace_root=workspace_root,
    )


# ---------------------------------------------------------------------------
# Positive control — the ordinary, unaffected path (A17.2: the memory atom's claim
# — repo templates copied at alive() — stays true for the common case).
# ---------------------------------------------------------------------------


def test_ordinary_repo_still_receives_the_template_byte_identical(
    service: SpecContextService, workspace_root: Path
) -> None:
    service.create("proj", "my-repo", "https://github.com/org/my-repo")
    service.alive("proj")
    installed = workspace_root / "repos" / "my-repo" / "AGENTS.md"
    assert installed.exists()
    assert installed.read_bytes() == _TEMPLATE.read_bytes()


def test_existing_repo_agents_is_never_overwritten(
    service: SpecContextService, workspace_root: Path
) -> None:
    service.create("proj", "my-repo", "https://github.com/org/my-repo")
    repo = workspace_root / "repos" / "my-repo"
    own_law = "# my own repo-owned AGENTS.md\n"
    repo.mkdir(parents=True, exist_ok=True)
    (repo / "AGENTS.md").write_text(own_law, encoding="utf-8")
    service.alive("proj")
    assert (repo / "AGENTS.md").read_text(encoding="utf-8") == own_law


# ---------------------------------------------------------------------------
# Refusal site 1 — a symlinked repo DIRECTORY (the write's containing dir) escapes
# the repos/ tree; never write through it.
# ---------------------------------------------------------------------------


def test_symlinked_repo_directory_is_never_written_through(
    service: SpecContextService, workspace_root: Path, tmp_path: Path
) -> None:
    # create() is a pure in-memory record write (no filesystem I/O) — safe to call
    # before the symlink exists, isolating the alive()-time refusal specifically.
    service.create("proj", "my-repo", "https://github.com/org/my-repo")
    outside = tmp_path / "outside-repo"
    outside.mkdir()
    (workspace_root / "repos" / "my-repo").symlink_to(outside, target_is_directory=True)

    service.alive("proj")

    assert not (outside / "AGENTS.md").exists()


# ---------------------------------------------------------------------------
# Refusal site 2 — a symlinked (non-dangling) destination FILE must never be written
# through, even though the symlink itself is the thing occupying the "AGENTS.md" name.
# ---------------------------------------------------------------------------


def test_non_dangling_destination_symlink_is_never_written_through(
    service: SpecContextService, workspace_root: Path, tmp_path: Path
) -> None:
    service.create("proj", "my-repo", "https://github.com/org/my-repo")
    repo = workspace_root / "repos" / "my-repo"
    repo.mkdir(parents=True, exist_ok=True)
    target = tmp_path / "elsewhere-agents.md"
    target.write_text("pre-existing real content\n", encoding="utf-8")
    (repo / "AGENTS.md").symlink_to(target)

    service.alive("proj")

    assert target.read_text(encoding="utf-8") == "pre-existing real content\n"


# ---------------------------------------------------------------------------
# Refusal site 3 — a DANGLING destination symlink reports not-exists (Path.exists()
# follows the link and finds nothing), but shutil.copy2 would still write straight
# through it to wherever the link points.
# ---------------------------------------------------------------------------


def test_dangling_destination_symlink_is_never_written_through(
    service: SpecContextService, workspace_root: Path, tmp_path: Path
) -> None:
    service.create("proj", "my-repo", "https://github.com/org/my-repo")
    repo = workspace_root / "repos" / "my-repo"
    repo.mkdir(parents=True, exist_ok=True)
    target = tmp_path / "dangling-target-agents.md"
    (repo / "AGENTS.md").symlink_to(target)
    assert not target.exists()

    service.alive("proj")

    assert not target.exists(), "the dangling symlink was written through"


# ---------------------------------------------------------------------------
# Refusal site 4 — the SAME destination-file check must hold regardless of which
# process/session created the symlink; re-running alive() idempotently must not
# resolve/replace it either (no silent self-healing that would still write through
# on a later call).
# ---------------------------------------------------------------------------


def test_repeated_alive_calls_never_resolve_a_symlinked_destination(
    service: SpecContextService, workspace_root: Path, tmp_path: Path
) -> None:
    service.create("proj", "my-repo", "https://github.com/org/my-repo")
    repo = workspace_root / "repos" / "my-repo"
    repo.mkdir(parents=True, exist_ok=True)
    target = tmp_path / "repeat-target-agents.md"
    (repo / "AGENTS.md").symlink_to(target)

    service.alive("proj")
    service.alive("proj")

    assert not target.exists()
    assert (repo / "AGENTS.md").is_symlink(), "the symlink itself must be left untouched"


# ---------------------------------------------------------------------------
# T-043-23 security-review rework (FR17 LOW, CWE-367 TOCTOU) — the destination
# write must go through a SINGLE atomic os.open() call carrying
# O_CREAT|O_EXCL|O_NOFOLLOW, never a separate is_symlink()/exists() probe followed
# by a distinct shutil.copy2 call (the pre-fix shape, which left a window for a
# same-user process to swap the destination for a symlink in between).
# ---------------------------------------------------------------------------


def test_repo_agents_write_uses_a_single_atomic_open_call(
    service: SpecContextService, workspace_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service.create("proj", "my-repo", "https://github.com/org/my-repo")
    dst = workspace_root / "repos" / "my-repo" / "AGENTS.md"

    # Patching ``os.open`` patches the ONE global ``os`` module every caller in the
    # process shares (``service_module.os`` is that same module object) — including
    # pytest's own ``tmp_path`` teardown (``shutil.rmtree`` calls ``os.open`` with
    # ``dir_fd=``). The spy must pass through EVERY kwarg unexamined, only recording
    # calls that target *dst* by position.
    seen: list[tuple[str, int]] = []
    real_open = service_module.os.open

    def spy_open(path: object, flags: int, *args: object, **kwargs: object) -> int:
        if str(path) == str(dst):
            seen.append((str(path), flags))
        return real_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(service_module.os, "open", spy_open)

    service.alive("proj")

    assert seen, "the repo-AGENTS.md write must go through os.open (atomic create)"
    _, flags = seen[0]
    assert flags & os.O_CREAT
    assert flags & os.O_EXCL
    assert hasattr(os, "O_NOFOLLOW") and flags & os.O_NOFOLLOW
