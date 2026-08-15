"""GitSubprocessObjectReader — the GitObjectReader adapter (SPEC v0.9.0 FR1/FR6).

Intent: CONTRACT — v0.9.0 A1.1, A1.2, A1.3, A1.4, A6.1, A6.2; v0.11.0 A7.4

Drives a real throwaway git repo under pytest ``tmp_path`` (never inside the source
tree). Covers both FR1 range forms (resolvable ``remote_sha`` vs ``--not --remotes``),
a binary blob marked undecodable, a deletion sha (empty range), a duplicate blob shared
by two commits (deduped), and a git failure (typed error, not a silent empty result).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from dadaia_workspace.core.protocols.git_object_reader import ZERO_SHA, GitObjectReadError
from dadaia_workspace.infrastructure.git_objects import GitSubprocessObjectReader

pytestmark = [pytest.mark.integration, pytest.mark.slow]


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


def _blob_sha(path: Path, relative: str) -> str:
    return _git(["rev-parse", f"HEAD:{relative}"], path).stdout.strip()


def test_new_objects_resolvable_remote_sha_scopes_to_the_delta(tmp_path: Path) -> None:
    """Row 1 of FR1: a resolvable ``remote_sha`` scopes the scan to objects new since it."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "a.txt").write_text("first commit content\n")
    base_sha = _commit(repo, "c1")

    (repo / "b.txt").write_text("second commit content\n")
    tip_sha = _commit(repo, "c2")

    reader = GitSubprocessObjectReader()
    objects = list(reader.new_objects(repo, tip_sha, base_sha))

    paths = {obj.path for obj in objects}
    assert paths == {"b.txt"}
    assert all(obj.decodable for obj in objects)
    assert all(obj.text for obj in objects)


def test_new_objects_zero_remote_sha_falls_back_to_not_remotes(tmp_path: Path) -> None:
    """Row 2 of FR1: a zero (new-ref) ``remote_sha`` scans every object reachable from
    ``local_sha`` (no remotes configured -> nothing is excluded)."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "only.txt").write_text("brand new branch content\n")
    tip_sha = _commit(repo, "c1")

    reader = GitSubprocessObjectReader()
    objects = list(reader.new_objects(repo, tip_sha, ZERO_SHA))

    assert {obj.path for obj in objects} == {"only.txt"}


def test_new_objects_unresolvable_remote_sha_falls_back_to_not_remotes(tmp_path: Path) -> None:
    """Row 2 of FR1: a ``remote_sha`` that does not resolve locally is treated the same
    as a new ref — it never crashes the read."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "a.txt").write_text("content\n")
    tip_sha = _commit(repo, "c1")

    reader = GitSubprocessObjectReader()
    objects = list(reader.new_objects(repo, tip_sha, "f" * 40))

    assert {obj.path for obj in objects} == {"a.txt"}


def test_new_objects_deletion_sha_is_an_empty_range(tmp_path: Path) -> None:
    """FR1 row 3: a zero ``local_sha`` (branch deletion) never scans — empty range."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "a.txt").write_text("content\n")
    tip_sha = _commit(repo, "c1")

    reader = GitSubprocessObjectReader()
    objects = list(reader.new_objects(repo, ZERO_SHA, tip_sha))

    assert objects == []


def test_new_objects_marks_binary_blob_undecodable(tmp_path: Path) -> None:
    """FR6 row 3: a non-UTF-8 blob is returned with ``decodable=False`` and empty text,
    never raised — the matcher skips and counts it."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "bin.dat").write_bytes(b"\x00\x01\xff\xfe binary payload")
    tip_sha = _commit(repo, "c1")

    reader = GitSubprocessObjectReader()
    objects = list(reader.new_objects(repo, tip_sha, ZERO_SHA))

    binaries = [obj for obj in objects if obj.path == "bin.dat"]
    assert len(binaries) == 1
    assert binaries[0].decodable is False
    assert binaries[0].text == ""


def test_new_objects_marks_oversized_blob_undecodable_and_never_fetches_its_content(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SPEC v0.9.0 R3 blob-size guard (code-reviewer MEDIUM finding): a blob over the
    adapter's size cap is reported ``decodable=False`` without ever being decoded — and,
    stronger than that, its content is never even fetched: the oversized blob's sha is
    proven absent from every ``git cat-file --batch`` (content-read) stdin payload, only
    ever appearing in the cheaper ``--batch-check`` (size-check) call."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    big_content = "a" * (6 * 1024 * 1024)  # 6 MB, over the 5 MB cap; otherwise valid UTF-8
    (repo / "big.txt").write_text(big_content)
    (repo / "small.txt").write_text("tiny and clean\n")
    tip_sha = _commit(repo, "c1")
    big_sha = _blob_sha(repo, "big.txt")

    from dadaia_workspace.infrastructure import git_objects as git_objects_module

    real_run = git_objects_module._run
    batch_stdins: list[bytes] = []

    def _spy_run(
        args: list[str], cwd: Path, *, input_bytes: bytes | None = None
    ) -> subprocess.CompletedProcess[bytes]:
        if args[:3] == ["git", "cat-file", "--batch"] and input_bytes is not None:
            batch_stdins.append(input_bytes)
        return real_run(args, cwd, input_bytes=input_bytes)

    monkeypatch.setattr(git_objects_module, "_run", _spy_run)

    reader = GitSubprocessObjectReader()
    objects = list(reader.new_objects(repo, tip_sha, ZERO_SHA))

    big = next(obj for obj in objects if obj.path == "big.txt")
    assert big.decodable is False
    assert big.text == ""
    assert big.sha == big_sha

    small = next(obj for obj in objects if obj.path == "small.txt")
    assert small.decodable is True
    assert small.text == "tiny and clean\n"

    assert batch_stdins, "the content-read batch call must still run for the small blob"
    assert all(big_sha.encode() not in payload for payload in batch_stdins)


def test_new_objects_dedupes_a_blob_reachable_from_two_commits(tmp_path: Path) -> None:
    """A1.4: the identical blob content committed on two separate files in the range is
    returned once per distinct blob sha, never once per path occurrence."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    shared_content = "identical content shared by two files\n"
    (repo / "a.txt").write_text(shared_content)
    (repo / "b.txt").write_text(shared_content)
    tip_sha = _commit(repo, "c1")

    shared_sha = _blob_sha(repo, "a.txt")
    assert shared_sha == _blob_sha(repo, "b.txt")

    reader = GitSubprocessObjectReader()
    objects = list(reader.new_objects(repo, tip_sha, ZERO_SHA))

    matching = [obj for obj in objects if obj.sha == shared_sha]
    assert len(matching) == 1


def test_new_objects_git_failure_raises_typed_error(tmp_path: Path) -> None:
    """FR6 row 2: a git failure (not a repository) raises the typed error — never an
    empty, silently-clean result."""
    not_a_repo = tmp_path / "not-a-repo"
    not_a_repo.mkdir()

    reader = GitSubprocessObjectReader()
    with pytest.raises(GitObjectReadError):
        list(reader.new_objects(not_a_repo, "a" * 40, ZERO_SHA))


def test_new_objects_batch_check_timeout_raises_typed_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """code-reviewer MEDIUM finding: the ``--batch-check`` call must route through the
    same typed-error wrapper as every other git invocation in this module — a subprocess
    timeout or a missing ``git`` executable must never escape as a raw exception
    (``core/protocols/git_object_reader.py`` — 'Any git failure raises
    GitObjectReadError rather than returning a partial/empty result'). Forces the
    failure specifically on the batch-check call (the rev-list call that precedes it
    still runs for real) so this exercises the previously-untested gap distinctly from
    ``test_new_objects_git_failure_raises_typed_error`` above, which fails before
    batch-check ever runs."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "a.txt").write_text("content\n")
    tip_sha = _commit(repo, "c1")

    real_run = subprocess.run

    def _flaky_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        if any("--batch-check" in str(arg) for arg in args):
            raise subprocess.TimeoutExpired(cmd=args, timeout=30)
        return real_run(args, **kwargs)  # type: ignore[return-value]

    monkeypatch.setattr("dadaia_workspace.infrastructure.git_objects.subprocess.run", _flaky_run)

    reader = GitSubprocessObjectReader()
    with pytest.raises(GitObjectReadError):
        list(reader.new_objects(repo, tip_sha, ZERO_SHA))


# ---------------------------------------------------------------------------
# FR7/A7.4 — `_rev_list_candidates` closes the argv interpolation site with a
# trailing `--` end-of-options marker; `_is_resolvable_commit` rejects non-sha
# input before it is ever interpolated into a git argv.
# ---------------------------------------------------------------------------


def _spy_on_rev_list(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    from dadaia_workspace.infrastructure import git_objects as git_objects_module

    real_run = git_objects_module._run
    captured: list[list[str]] = []

    def _spy_run(
        args: list[str], cwd: Path, *, input_bytes: bytes | None = None
    ) -> subprocess.CompletedProcess[bytes]:
        if args[:3] == ["git", "rev-list", "--objects"]:
            captured.append(args)
        return real_run(args, cwd, input_bytes=input_bytes)

    monkeypatch.setattr(git_objects_module, "_run", _spy_run)
    return captured


def test_rev_list_argv_carries_trailing_end_of_options_marker_resolvable_base(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Resolvable-``remote_sha`` shape (row 1): the ``--`` marker trails the revision
    arguments so a crafted sha can never be parsed as a git option."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "a.txt").write_text("first\n")
    base_sha = _commit(repo, "c1")
    (repo / "b.txt").write_text("second\n")
    tip_sha = _commit(repo, "c2")

    captured = _spy_on_rev_list(monkeypatch)
    reader = GitSubprocessObjectReader()
    list(reader.new_objects(repo, tip_sha, base_sha))

    assert captured, "rev-list --objects must have been invoked"
    assert captured[0][-1] == "--"


def test_rev_list_argv_carries_trailing_end_of_options_marker_fallback_shape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fallback (``--not --remotes``) shape (row 2): same trailing marker."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "a.txt").write_text("content\n")
    tip_sha = _commit(repo, "c1")

    captured = _spy_on_rev_list(monkeypatch)
    reader = GitSubprocessObjectReader()
    list(reader.new_objects(repo, tip_sha, ZERO_SHA))

    assert captured, "rev-list --objects must have been invoked"
    assert captured[0][-1] == "--"


def test_is_resolvable_commit_rejects_option_shaped_sha_before_interpolation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An option-shaped ``remote_sha`` (e.g. ``--upload-pack=...``) must never reach
    ``git cat-file -e <sha>^{commit}`` — it is rejected by a prefix/shape check before
    interpolation, so the adapter treats it as unresolvable (falls back to
    ``--not --remotes``) rather than ever spawning git with that string embedded."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "a.txt").write_text("content\n")
    tip_sha = _commit(repo, "c1")

    from dadaia_workspace.infrastructure import git_objects as git_objects_module

    real_run = git_objects_module._run
    cat_file_e_calls: list[list[str]] = []

    def _spy_run(
        args: list[str], cwd: Path, *, input_bytes: bytes | None = None
    ) -> subprocess.CompletedProcess[bytes]:
        if args[:3] == ["git", "cat-file", "-e"]:
            cat_file_e_calls.append(args)
        return real_run(args, cwd, input_bytes=input_bytes)

    monkeypatch.setattr(git_objects_module, "_run", _spy_run)

    malicious_remote_sha = "--upload-pack=/bin/false"
    reader = GitSubprocessObjectReader()
    objects = list(reader.new_objects(repo, tip_sha, malicious_remote_sha))

    assert cat_file_e_calls == [], "an option-shaped sha must never be interpolated into argv"
    # Falls back to the --not --remotes shape (no remotes configured -> full range).
    assert {obj.path for obj in objects} == {"a.txt"}
