"""v0.9.0 A4.2, A6.1; v0.11.0 A1.6, A2.3, A10.2: the push-range denylist
scan over a REAL throwaway repo, through the real ``GitSubprocessObjectReader`` wired into
``push_gate_decision`` (no CLI layer). Amnesty is bound to the PATH that already published
a value at the range base (v0.11.0 FR1) — for a tag pushed over a published sha and for
the first push of a new branch whose past is on origin (bug
new-branch-push-loses-prior-published-denylist-amnesty); a git failure refuses naming
``--no-verify`` (FR6 row 2). Synthetic terms only.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from dadaia_workspace.core.gitflow import DEFAULT
from dadaia_workspace.features.chokepoints import push_gate_decision
from dadaia_workspace.features.chokepoints.branch_policy import Decision, PushRef
from dadaia_workspace.features.specs.canon import canon_violations
from dadaia_workspace.features.specs.doctor_adr import cites_an_accepted_adr
from dadaia_workspace.infrastructure.git_objects import GitSubprocessObjectReader
from tests.fakes import gate_fixes

_T = "zz-frozen-invariant-term"
_ZERO = "0" * 40
_ARCHIVED = "specs/releases/_archive/0.4.0/notes.md"


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)


def _init_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    _git(["init"], path)
    _git(["config", "user.email", "t@example.com"], path)
    _git(["config", "user.name", "T"], path)


def _commit(path: Path, message: str) -> str:
    _git(["add", "-A"], path)
    _git(["commit", "-m", message], path)
    return _git(["rev-parse", "HEAD"], path).stdout.strip()


def _tag_push_ref(local_sha: str, *, remote_sha: str = _ZERO) -> PushRef:
    return PushRef("refs/tags/v1", local_sha, "refs/tags/v1", remote_sha)


def _decide(refs: list[PushRef], repo: Path, terms: tuple[tuple[str, str], ...] = ()) -> Decision:
    return push_gate_decision(
        refs, gitflow=DEFAULT, fixes=gate_fixes(), object_source=GitSubprocessObjectReader(),
        repo=repo, canon_violations_fn=canon_violations, cites_accepted_adr=cites_an_accepted_adr(None), denylist_terms=terms,
    )  # fmt: skip


@pytest.mark.parametrize(
    ("ref", "published", "pushed", "allowed"),
    [
        pytest.param("tag", {"notes.md": f"a {_T}\n"}, {_ARCHIVED: f"a {_T}\n"}, True, id="A4.2-git-mv-into-archive-reuses-the-blob"),
        pytest.param("tag", {"notes.md": f"a {_T}\n"}, {"notes.md": f"a {_T}\nmore\n"}, True, id="A1.1-edit-the-path-that-published-it"),
        pytest.param("tag", {"tests/f.py": f"S = {_T!r}\n"}, {"tests/f.py": f"S = {_T!r}\nE = 1\n"}, True, id="A1.6-edit-a-published-tests-fixture"),
        pytest.param("tag", {"tests/f.py": f"S = {_T!r}\n"}, {"tests/f.py": f"S = {_T!r}\n", "tests/new.py": f"C = {_T!r}\n"}, False, id="A1.2-same-value-into-a-new-path"),
        pytest.param("branch", {"notes.md": f"a {_T}\n"}, {"notes.md": f"a {_T}\nnew line\n"}, True, id="new-branch-already-published-term"),
        pytest.param("branch", {"notes.md": "u\n"}, {"notes.md": f"u\nintroducing {_T}\n"}, False, id="new-branch-novel-term"),
    ],
)  # fmt: skip
def test_the_amnesty_is_bound_to_the_path_that_already_published_the_value(
    tmp_path: Path, ref: str, published: dict[str, str], pushed: dict[str, str], allowed: bool
) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    for rel, text in published.items():
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_text(text)
    base = _commit(repo, "already-published")
    if ref == "branch":
        origin = tmp_path / "origin.git"
        _git(["init", "--bare", str(origin)], tmp_path)
        _git(["remote", "add", "origin", str(origin)], repo)
        _git(["push", "origin", "HEAD:refs/heads/develop"], repo)
        _git(["fetch", "origin"], repo)
        _git(["checkout", "-b", "feature/1.0.0"], repo)
    for rel in set(published) - set(pushed):
        (repo / rel).unlink()
    for rel, text in pushed.items():
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_text(text)
    tip = _commit(repo, "the pushed range")
    push = (
        PushRef("refs/heads/feature/1.0.0", tip, "refs/heads/feature/1.0.0", _ZERO)
        if ref == "branch"
        else _tag_push_ref(tip, remote_sha=base)
    )

    decision = _decide([push], repo, ((_T, "synthetic"),))

    assert decision.allowed is allowed, decision.message
    assert _T not in decision.message


def test_prior_side_lookup_failure_refuses_naming_the_failure_and_no_verify(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SPEC v0.11.0 A2.3 (integration tier — unit tier already pinned in
    ``tests/infrastructure/test_git_objects.py``): a forced git failure on
    the prior-side lookup refuses, naming the failure AND ``--no-verify``, over the
    REAL adapter wired into ``push_gate_decision``."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "notes.md").write_text("published content\n")
    already_published_sha = _commit(repo, "already-published")
    (repo / "notes.md").write_text("edited content\n")
    tip_sha = _commit(repo, "edit")

    from dadaia_workspace.infrastructure import git_objects as git_objects_module

    real_run = git_objects_module._run
    marker = f"{already_published_sha}:".encode()

    def _flaky_run(
        args: list[str], cwd: Path, *, input_bytes: bytes | None = None
    ) -> subprocess.CompletedProcess[bytes]:
        if input_bytes is not None and marker in input_bytes:
            return subprocess.CompletedProcess(
                args, 1, stdout=b"", stderr=b"simulated prior-lookup failure"
            )
        return real_run(args, cwd, input_bytes=input_bytes)

    monkeypatch.setattr(git_objects_module, "_run", _flaky_run)

    decision = _decide([_tag_push_ref(tip_sha, remote_sha=already_published_sha)], repo)

    assert not decision.allowed
    assert "prior content" in decision.message
    assert "--no-verify" in decision.message


def test_real_git_failure_refuses_naming_the_failure(tmp_path: Path) -> None:
    """FR6 row 2, integration-tier: a genuinely non-git directory wired through the
    REAL adapter refuses, never silently allows an unscannable push."""
    not_a_repo = tmp_path / "not-a-repo"
    not_a_repo.mkdir()
    decision = _decide([_tag_push_ref("a" * 40)], not_a_repo)

    assert not decision.allowed
    assert "--no-verify" in decision.message
