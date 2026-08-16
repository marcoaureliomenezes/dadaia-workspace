"""GitSubprocessObjectReader — the GitObjectReader adapter (SPEC v0.9.0 FR1/FR6).

Intent: CONTRACT — v0.9.0 A1.1, A1.2, A1.3, A1.4, A6.1, A6.2; v0.11.0 A7.4, A8.1, A8.2,
A9.2, A9.3, A2.1, A2.2, A2.3, A2.4, A2.5

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


def test_new_objects_scans_the_first_cap_bytes_of_an_oversized_text_blob(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SPEC v0.11.0 FR4/A4.1-A4.2 (supersedes the v0.9.0 total-blind-spot skip): a blob
    over the adapter's size cap is read through a SEPARATE, bounded per-object stream —
    never the batch content-read conversation (the oversized sha is proven absent from
    every ``git cat-file --batch`` stdin payload, only ever appearing in the cheaper
    ``--batch-check`` size-check call) — and at most the cap's worth of its content is
    ever read. When that prefix decodes as valid UTF-8 it is reported
    ``decodable=True``/``oversized=True`` with ``text`` carrying the DECODED PREFIX
    (partial coverage, not zero coverage)."""
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
    assert big.decodable is True
    assert big.oversized is True
    assert big.size_bytes == 6 * 1024 * 1024
    assert big.scanned_bytes == git_objects_module._MAX_BLOB_BYTES
    assert len(big.text.encode("utf-8")) == big.scanned_bytes  # A4.2: never over the cap.
    assert big.sha == big_sha

    small = next(obj for obj in objects if obj.path == "small.txt")
    assert small.decodable is True
    assert small.oversized is False
    assert small.text == "tiny and clean\n"

    assert batch_stdins, "the content-read batch call must still run for the small blob"
    assert all(big_sha.encode() not in payload for payload in batch_stdins)


def test_new_objects_oversized_blob_with_undecodable_prefix_falls_back_to_binary(
    tmp_path: Path,
) -> None:
    """A4.6: an oversized blob whose scanned (first-cap-bytes) prefix is NOT valid
    UTF-8 falls back to ``decodable=False`` — the same class an ordinary undecodable
    blob reports — never raises, never fabricates text."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    # 6 MB of a byte that is never a valid UTF-8 lead or continuation byte.
    (repo / "big.bin").write_bytes(b"\xff" * (6 * 1024 * 1024))
    tip_sha = _commit(repo, "c1")
    big_sha = _blob_sha(repo, "big.bin")

    reader = GitSubprocessObjectReader()
    objects = list(reader.new_objects(repo, tip_sha, ZERO_SHA))

    big = next(obj for obj in objects if obj.path == "big.bin")
    assert big.decodable is False
    assert big.text == ""
    assert big.oversized is True
    assert big.sha == big_sha


# ═════════════════════════════════════════════════════════════════════════════════
# FR8 (v0.4.2, GRILL P11-P13, anchor correction P12) — a scan-path degradation is never
# silent. Sub-item (1): _read_oversized_blob_prefix inspects the process exit status
# and raises when the process FAILED and fewer than cap bytes arrived; the intentional
# early-close (EPIPE after the cap) stays the only swallowed shape.
# ═════════════════════════════════════════════════════════════════════════════════

# Intent: CONTRACT — v0.4.2 A8.1


def test_read_oversized_blob_prefix_raises_on_nonexistent_oid(tmp_path: Path) -> None:
    """A8.1: a nonexistent oid must raise the typed error, never silently return a
    0-byte 'partially scanned' prefix — `git cat-file blob <oid>` exits 128 delivering
    zero stdout bytes for an oid that resolves to nothing."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "a.txt").write_text("content\n")
    _commit(repo, "c1")

    from dadaia_workspace.infrastructure import git_objects as git_objects_module

    nonexistent_oid = "f" * 40
    with pytest.raises(GitObjectReadError):
        git_objects_module._read_oversized_blob_prefix(repo, nonexistent_oid)


def test_read_oversized_blob_prefix_raises_on_tree_sha(tmp_path: Path) -> None:
    """A8.1: a tree sha (not a blob) passed to `git cat-file blob` must raise the typed
    error rather than silently returning a 0-byte prefix — `git cat-file blob <tree>`
    exits 128 ("bad file") delivering zero stdout bytes."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "a.txt").write_text("content\n")
    tip_sha = _commit(repo, "c1")
    tree_sha = _git(["rev-parse", f"{tip_sha}^{{tree}}"], repo).stdout.strip()

    from dadaia_workspace.infrastructure import git_objects as git_objects_module

    with pytest.raises(GitObjectReadError):
        git_objects_module._read_oversized_blob_prefix(repo, tree_sha)


# Intent: CONTRACT — v0.4.2 A8.2 (regression — the existing EPIPE/full-cap path is not
# broken by the new returncode inspection)


def test_read_oversized_blob_prefix_full_cap_read_still_succeeds(tmp_path: Path) -> None:
    """A8.2: an oversized blob read that delivers the full cap still succeeds — the
    intentional early-close EPIPE outcome stays the only swallowed shape, unaffected by
    the new 'failed with fewer than cap bytes' check (len(prefix) == cap here, so the
    new guard never fires)."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "big.txt").write_text("a" * (6 * 1024 * 1024))
    _commit(repo, "c1")
    big_sha = _blob_sha(repo, "big.txt")

    from dadaia_workspace.infrastructure import git_objects as git_objects_module

    prefix = git_objects_module._read_oversized_blob_prefix(repo, big_sha)
    assert len(prefix) == git_objects_module._MAX_BLOB_BYTES


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


# ---------------------------------------------------------------------------
# code-reviewer LOW finding (v0.11.0 pre-PR review) — the module's stated second-layer
# argv defence (git_objects.py:37-42) must also cover `local_sha`: it is shape-checked
# BEFORE `_rev_list_candidates` ever interpolates it into the `git rev-list` argv,
# exactly as `_is_resolvable_commit` already does for `remote_sha`.
# ---------------------------------------------------------------------------


def test_new_objects_rejects_an_option_shaped_local_sha_before_interpolation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """LOW4: an option-shaped ``local_sha`` (e.g. ``--upload-pack=...``) must never
    reach the ``git rev-list --objects <local_sha> ...`` argv — it is rejected by the
    same sha-shape prefix check the module already applies to ``remote_sha``, raising
    ``GitObjectReadError`` before any ``git rev-list`` subprocess is even spawned."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "a.txt").write_text("content\n")
    _commit(repo, "c1")

    from dadaia_workspace.infrastructure import git_objects as git_objects_module

    real_run = git_objects_module._run
    rev_list_calls: list[list[str]] = []

    def _spy_run(
        args: list[str], cwd: Path, *, input_bytes: bytes | None = None
    ) -> subprocess.CompletedProcess[bytes]:
        if args[:3] == ["git", "rev-list", "--objects"]:
            rev_list_calls.append(args)
        return real_run(args, cwd, input_bytes=input_bytes)

    monkeypatch.setattr(git_objects_module, "_run", _spy_run)

    malicious_local_sha = "--upload-pack=/bin/false"
    reader = GitSubprocessObjectReader()
    with pytest.raises(GitObjectReadError, match="local_sha"):
        list(reader.new_objects(repo, malicious_local_sha, ZERO_SHA))

    assert rev_list_calls == [], "an option-shaped local_sha must never reach the rev-list argv"


# ---------------------------------------------------------------------------
# FR8/A8.1-A8.2 — the batch header-parse boundary surfaces a truncated stream and a
# non-numeric size field as GitObjectReadError instead of a raw ValueError, and a
# desynchronised header shape aborts typed rather than yielding a fabricated object.
# ---------------------------------------------------------------------------


def _patch_batch_stdout(monkeypatch: pytest.MonkeyPatch, corrupted_stdout: bytes) -> None:
    """Force the ``git cat-file --batch`` (content-read) call to return
    *corrupted_stdout* while every other call in the module runs for real."""
    from dadaia_workspace.infrastructure import git_objects as git_objects_module

    real_run = git_objects_module._run

    def _spy_run(
        args: list[str], cwd: Path, *, input_bytes: bytes | None = None
    ) -> subprocess.CompletedProcess[bytes]:
        if args == ["git", "cat-file", "--batch"]:
            return subprocess.CompletedProcess(args, 0, stdout=corrupted_stdout, stderr=b"")
        return real_run(args, cwd, input_bytes=input_bytes)

    monkeypatch.setattr(git_objects_module, "_run", _spy_run)


def test_truncated_batch_stream_raises_typed_error_not_raw_value_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A8.1: a batch stream with no trailing newline after the header (truncated mid
    read) raises GitObjectReadError — never a raw ValueError from ``bytes.index``."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "a.txt").write_text("hello\n")
    tip_sha = _commit(repo, "c1")
    blob_sha = _blob_sha(repo, "a.txt")

    # A well-formed header line with NO trailing newline anywhere in the buffer —
    # `out.index(b"\n", pos)` finds nothing and raises ValueError.
    _patch_batch_stdout(monkeypatch, f"{blob_sha} blob 6".encode())

    reader = GitSubprocessObjectReader()
    with pytest.raises(GitObjectReadError, match="desynchronised"):
        list(reader.new_objects(repo, tip_sha, ZERO_SHA))


def test_non_numeric_size_field_raises_typed_error_not_raw_value_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A8.1: a non-numeric size field raises GitObjectReadError — never a raw
    ValueError from ``int(size_str)``."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "a.txt").write_text("hello\n")
    tip_sha = _commit(repo, "c1")
    blob_sha = _blob_sha(repo, "a.txt")

    _patch_batch_stdout(monkeypatch, f"{blob_sha} blob abc\nhello\n".encode())

    reader = GitSubprocessObjectReader()
    with pytest.raises(GitObjectReadError, match="desynchronised"):
        list(reader.new_objects(repo, tip_sha, ZERO_SHA))


def test_desynchronised_header_shape_aborts_typed_never_yields_fabricated_object(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A8.2: a header that does not split into exactly 3 fields aborts with the typed
    error — it must NEVER yield a fabricated ``decodable=False`` object and continue
    (continuing would leave ``pos`` inside content bytes, corrupting every later parse
    into a stream of fabricated "binary" skips)."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "a.txt").write_text("hello\n")
    tip_sha = _commit(repo, "c1")
    blob_sha = _blob_sha(repo, "a.txt")

    # 4 fields instead of 3 — a desynchronised header shape.
    _patch_batch_stdout(monkeypatch, f"{blob_sha} blob 6 extra\nhello\n".encode())

    reader = GitSubprocessObjectReader()
    collected: list[object] = []
    with pytest.raises(GitObjectReadError, match="desynchronised"):
        for obj in reader.new_objects(repo, tip_sha, ZERO_SHA):
            collected.append(obj)
    assert collected == [], "no object — fabricated or otherwise — may be yielded on desync"


# ═════════════════════════════════════════════════════════════════════════════════
# FR8(3) (v0.4.2, GRILL P12 anchor correction) — an unparseable `--batch-check` row is
# typed-or-counted, never invisible, at its REAL sites: `_blob_info`
# (size-check for the candidate blob set) and `_resolve_prior_texts` (size-check
# resolving prior content). A legitimately non-blob row (a tree) and a documented
# `<spec> missing` row stay ordinary filtered outcomes, never errors.
# ═════════════════════════════════════════════════════════════════════════════════


def _patch_blob_info_batch_check(monkeypatch: pytest.MonkeyPatch, corrupted_stdout: bytes) -> None:
    """Force `_blob_info`'s `git cat-file --batch-check` call to return
    *corrupted_stdout* while every other call in the module runs for real."""
    from dadaia_workspace.infrastructure import git_objects as git_objects_module

    real_run = git_objects_module._run

    def _spy_run(
        args: list[str], cwd: Path, *, input_bytes: bytes | None = None
    ) -> subprocess.CompletedProcess[bytes]:
        if (
            len(args) >= 3
            and args[:2] == ["git", "cat-file"]
            and args[2].startswith("--batch-check")
        ):
            return subprocess.CompletedProcess(args, 0, stdout=corrupted_stdout, stderr=b"")
        return real_run(args, cwd, input_bytes=input_bytes)

    monkeypatch.setattr(git_objects_module, "_run", _spy_run)


# Intent: CONTRACT — v0.4.2 A8.4


def test_blob_info_raises_on_a_batch_check_row_with_wrong_field_count(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A8.4: a --batch-check row that is not the documented 3-field shape raises the
    typed error naming the row — silently skipping it would silently drop that blob
    from the scanned set (a coverage hole invisible to every caller)."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "a.txt").write_text("content\n")
    tip_sha = _commit(repo, "c1")

    _patch_blob_info_batch_check(monkeypatch, b"garbled-row-not-three-fields\n")

    reader = GitSubprocessObjectReader()
    with pytest.raises(GitObjectReadError, match="batch-check"):
        list(reader.new_objects(repo, tip_sha, ZERO_SHA))


def test_blob_info_raises_on_a_batch_check_row_with_non_numeric_size(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A8.4: a --batch-check row whose size field is not numeric raises the typed error
    rather than silently dropping the row (which would silently under-report the
    scanned set, exactly like the wrong-field-count case above)."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "a.txt").write_text("content\n")
    tip_sha = _commit(repo, "c1")
    fake_sha = "e" * 40

    _patch_blob_info_batch_check(monkeypatch, f"{fake_sha} blob not-a-number\n".encode())

    reader = GitSubprocessObjectReader()
    with pytest.raises(GitObjectReadError, match="batch-check"):
        list(reader.new_objects(repo, tip_sha, ZERO_SHA))


def test_blob_info_tree_row_is_an_ordinary_filtered_outcome_not_an_error(
    tmp_path: Path,
) -> None:
    """A8.4 (negative case): a legitimate 'tree' objecttype row — the ordinary,
    documented filter-out `_blob_info` performs for every non-blob candidate — is never
    treated as an error; this is the REAL git repo path (no monkeypatch needed), so it
    also proves the fix does not turn every normal push (which always includes at
    least one tree) into a false-positive failure."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "dir").mkdir()
    (repo / "dir" / "a.txt").write_text("content\n")
    tip_sha = _commit(repo, "c1")

    reader = GitSubprocessObjectReader()
    objects = list(reader.new_objects(repo, tip_sha, ZERO_SHA))
    assert any(obj.path == "dir/a.txt" for obj in objects)


# Intent: CONTRACT — v0.4.2 A8.4 (`_resolve_prior_texts` side)


def test_resolve_prior_texts_raises_on_a_malformed_batch_check_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A8.4: a --batch-check row resolving PRIOR content that is neither the documented
    3-field blob/tree shape NOR the documented 2-field '<spec> missing' absence shape
    raises the typed error — never silently treated as absence."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "notes.md").write_text("original content\n")
    base_sha = _commit(repo, "c1")
    (repo / "notes.md").write_text("edited content\n")
    tip_sha = _commit(repo, "c2")

    from dadaia_workspace.infrastructure import git_objects as git_objects_module

    real_run = git_objects_module._run
    marker = f"{base_sha}:notes.md".encode()

    def _spy_run(
        args: list[str], cwd: Path, *, input_bytes: bytes | None = None
    ) -> subprocess.CompletedProcess[bytes]:
        if (
            input_bytes is not None
            and marker in input_bytes
            and len(args) >= 3
            and args[2].startswith("--batch-check")
        ):
            return subprocess.CompletedProcess(
                args, 0, stdout=b"totally-garbled-not-missing-not-three-fields\n", stderr=b""
            )
        return real_run(args, cwd, input_bytes=input_bytes)

    monkeypatch.setattr(git_objects_module, "_run", _spy_run)

    reader = GitSubprocessObjectReader()
    with pytest.raises(GitObjectReadError, match="batch-check"):
        list(reader.new_objects(repo, tip_sha, base_sha))


def test_resolve_prior_texts_missing_row_still_treated_as_absence(tmp_path: Path) -> None:
    """A8.4 (negative case, real repo): the documented '<spec> missing' row (a path
    genuinely absent at the base) stays an ordinary absence — no monkeypatch needed,
    git itself produces this row for a brand-new path. Regression guard for the SAME
    scenario `test_new_objects_resolvable_base_new_path_carries_no_prior_text` already
    covers — re-asserted here, next to the new raising behaviour, so the two outcomes
    (raise vs absence) are pinned side by side."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "existing.md").write_text("unrelated\n")
    base_sha = _commit(repo, "c1")
    (repo / "brand-new.md").write_text("never published before\n")
    tip_sha = _commit(repo, "c2")

    reader = GitSubprocessObjectReader()
    objects = list(reader.new_objects(repo, tip_sha, base_sha))

    new_obj = next(obj for obj in objects if obj.path == "brand-new.md")
    assert new_obj.prior_text is None


# Intent: CONTRACT — v0.4.2 CR-1 (code-reviewer HIGH, regression vs 741f2294)


def test_resolve_prior_texts_new_path_with_two_spaces_is_absence_not_a_raise(
    tmp_path: Path,
) -> None:
    """CR-1: a brand-new path containing TWO OR MORE embedded spaces must resolve as
    an ordinary absence, exactly like any other new path — never raise.

    ``git cat-file --batch-check`` answers a missing lookup by echoing the WHOLE
    ``<base>:<path>`` input followed by `` missing`` — a naive field-count classifier
    (``len(parts) == 2``) misclassifies any path with one or more embedded spaces,
    and RAISES for two or more (the exact regression this test pins). Real repo path
    (no monkeypatch needed) — git itself produces the multi-space missing row."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "existing.md").write_text("unrelated\n")
    base_sha = _commit(repo, "c1")

    (repo / "docs").mkdir()
    (repo / "docs" / "my other file.md").write_text("brand new content with spaces\n")
    tip_sha = _commit(repo, "c2")

    reader = GitSubprocessObjectReader()
    objects = list(reader.new_objects(repo, tip_sha, base_sha))

    new_obj = next(obj for obj in objects if obj.path == "docs/my other file.md")
    assert new_obj.prior_text is None


# ---------------------------------------------------------------------------
# FR9/A9.2 — the content-read `git cat-file --batch` conversation is CHUNKED: the
# number of invocations grows with the number of chunks, not the number of blobs, and
# an under-cap range spawns no per-object read.
# ---------------------------------------------------------------------------


def _spy_on_content_batch_calls(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    from dadaia_workspace.infrastructure import git_objects as git_objects_module

    real_run = git_objects_module._run
    calls: list[list[str]] = []

    def _spy_run(
        args: list[str], cwd: Path, *, input_bytes: bytes | None = None
    ) -> subprocess.CompletedProcess[bytes]:
        if args == ["git", "cat-file", "--batch"]:
            calls.append(args)
        return real_run(args, cwd, input_bytes=input_bytes)

    monkeypatch.setattr(git_objects_module, "_run", _spy_run)
    return calls


def test_under_cap_blob_count_spawns_a_single_batch_call_not_per_object(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FR9/A9.2: a blob count well under the chunk size spawns exactly ONE content-read
    batch call — never one subprocess per object (the single-conversation win FR9
    preserves)."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "a.txt").write_text("a\n")
    (repo / "b.txt").write_text("b\n")
    tip_sha = _commit(repo, "c1")

    batch_calls = _spy_on_content_batch_calls(monkeypatch)

    reader = GitSubprocessObjectReader()
    objects = list(reader.new_objects(repo, tip_sha, ZERO_SHA))

    assert {obj.path for obj in objects} == {"a.txt", "b.txt"}
    assert len(batch_calls) == 1


def test_batch_conversation_invocations_grow_with_chunks_not_blob_count(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FR9/A9.2: with the chunk size patched down to 3, a 7-blob range spawns exactly
    ceil(7/3) == 3 content-read batch calls — the invocation count tracks the number of
    CHUNKS, not the number of blobs."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    for i in range(7):
        (repo / f"f{i}.txt").write_text(f"content {i}\n")
    tip_sha = _commit(repo, "c1")

    from dadaia_workspace.infrastructure import git_objects as git_objects_module

    monkeypatch.setattr(git_objects_module, "_BATCH_CHUNK_SIZE", 3)
    batch_calls = _spy_on_content_batch_calls(monkeypatch)

    reader = GitSubprocessObjectReader()
    objects = list(reader.new_objects(repo, tip_sha, ZERO_SHA))

    assert len(objects) == 7
    assert len(batch_calls) == 3


# ---------------------------------------------------------------------------
# FR2/A2.1-A2.5 (v0.11.0) — the prior-side same-path lookup: resolvable-base objects
# carry the base's published text for their own path (or an explicit absence); the
# fallback shape carries absence everywhere; a forced failure refuses typed; the
# lookup costs a constant TWO extra batched calls per chunk, deduplicated by path.
# ---------------------------------------------------------------------------


def test_new_objects_resolvable_base_edited_path_carries_prior_text(tmp_path: Path) -> None:
    """A2.1: with a resolvable ``remote_sha``, an object whose path already existed at
    the base carries the base's FULL prior text for that SAME path."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "notes.md").write_text("original published content\n")
    base_sha = _commit(repo, "c1")

    (repo / "notes.md").write_text("edited content, different now\n")
    tip_sha = _commit(repo, "c2")

    reader = GitSubprocessObjectReader()
    objects = list(reader.new_objects(repo, tip_sha, base_sha))

    notes = next(obj for obj in objects if obj.path == "notes.md")
    assert notes.prior_text == "original published content\n"


def test_new_objects_resolvable_base_new_path_carries_no_prior_text(tmp_path: Path) -> None:
    """A2.1/A2.4 (path absent at base): a genuinely NEW path — absent at the base —
    carries an explicit absence, never an empty string."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "existing.md").write_text("unrelated\n")
    base_sha = _commit(repo, "c1")

    (repo / "brand-new.md").write_text("never published before\n")
    tip_sha = _commit(repo, "c2")

    reader = GitSubprocessObjectReader()
    objects = list(reader.new_objects(repo, tip_sha, base_sha))

    new_obj = next(obj for obj in objects if obj.path == "brand-new.md")
    assert new_obj.prior_text is None


def test_new_objects_fallback_shape_every_object_carries_no_prior_text(tmp_path: Path) -> None:
    """A2.2: in the ``--not --remotes`` fallback shape (no resolvable base), EVERY
    object carries an explicit absence — byte-identical to v0.9.0 for the same
    inputs."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "only.txt").write_text("brand new branch content\n")
    tip_sha = _commit(repo, "c1")

    reader = GitSubprocessObjectReader()
    objects = list(reader.new_objects(repo, tip_sha, ZERO_SHA))

    assert objects
    assert all(obj.prior_text is None for obj in objects)


def test_new_objects_over_cap_prior_blob_carries_no_prior_text(tmp_path: Path) -> None:
    """A2.4: a prior blob that exceeds the adapter's size cap yields no prior content
    — the cap applies to the PRIOR side exactly as it does to the current side."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "big.txt").write_text("a" * (6 * 1024 * 1024))  # 6 MB prior version
    base_sha = _commit(repo, "c1")

    (repo / "big.txt").write_text("small now\n")
    tip_sha = _commit(repo, "c2")

    reader = GitSubprocessObjectReader()
    objects = list(reader.new_objects(repo, tip_sha, base_sha))

    big = next(obj for obj in objects if obj.path == "big.txt")
    assert big.prior_text is None


def test_new_objects_undecodable_prior_blob_carries_no_prior_text(tmp_path: Path) -> None:
    """A2.4: a prior blob that is not valid UTF-8 yields no prior content."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "notes.md").write_bytes(b"\xff\xfe binary prior content")
    base_sha = _commit(repo, "c1")

    (repo / "notes.md").write_text("now it is clean text\n")
    tip_sha = _commit(repo, "c2")

    reader = GitSubprocessObjectReader()
    objects = list(reader.new_objects(repo, tip_sha, base_sha))

    notes = next(obj for obj in objects if obj.path == "notes.md")
    assert notes.prior_text is None


# ---------------------------------------------------------------------------
# code-reviewer LOW finding (v0.11.0 pre-PR review) — `_resolve_prior_texts` must
# discard `%(objecttype)` for real: only a `blob` may ever yield prior text. A path
# that was a DIRECTORY (tree) at the base must resolve to explicit absence even in the
# pathological case where the tree's raw bytes happen to decode as valid UTF-8 (a real
# tree's packed 20-byte shas virtually always fail to decode, which is why this defect
# was otherwise invisible) — proven here by forcing a decodable 'tree'-typed response
# onto the prior-side batch conversation.
# ---------------------------------------------------------------------------


def test_new_objects_path_that_was_a_directory_at_base_carries_no_prior_text(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """LOW5: a path that was a directory (tree) at the base and becomes a file at the
    tip must never have the tree's bytes read as its prior text."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "foo").mkdir()
    (repo / "foo" / "bar.txt").write_text("nested content\n")
    base_sha = _commit(repo, "c1")

    _git(["rm", "-r", "foo"], repo)
    (repo / "foo").write_text("now a file, not a directory\n")
    tip_sha = _commit(repo, "c2")

    from dadaia_workspace.infrastructure import git_objects as git_objects_module

    real_run = git_objects_module._run
    marker = f"{base_sha}:foo".encode()
    fake_tree_sha = "f" * 40
    fake_content = b"decodable tree-shaped content"

    def _spy_run(
        args: list[str], cwd: Path, *, input_bytes: bytes | None = None
    ) -> subprocess.CompletedProcess[bytes]:
        if input_bytes is not None and marker in input_bytes:
            if args[2].startswith("--batch-check"):
                return subprocess.CompletedProcess(
                    args,
                    0,
                    stdout=f"{fake_tree_sha} tree {len(fake_content)}\n".encode(),
                    stderr=b"",
                )
            if args == ["git", "cat-file", "--batch"]:
                header = f"{fake_tree_sha} tree {len(fake_content)}\n".encode()
                return subprocess.CompletedProcess(
                    args, 0, stdout=header + fake_content + b"\n", stderr=b""
                )
        return real_run(args, cwd, input_bytes=input_bytes)

    monkeypatch.setattr(git_objects_module, "_run", _spy_run)

    reader = GitSubprocessObjectReader()
    objects = list(reader.new_objects(repo, tip_sha, base_sha))

    foo_obj = next(obj for obj in objects if obj.path == "foo")
    assert foo_obj.prior_text is None


# ---------------------------------------------------------------------------
# code-reviewer MEDIUM finding M3 support (v0.11.0 pre-PR review, CLOSURE drift
# `oversized-never-amnestied-scope-boundary`) — pin the adapter-level guarantee that an
# oversized CURRENT object never carries prior_text, even when the base IS resolvable
# and the SAME path existed (under cap) at that base — the prior-side lookup rides only
# the FR9 chunked content-read loop; oversized objects are yielded through the separate
# `_read_oversized_blob` path, which never receives `prior_texts` at all.
# ---------------------------------------------------------------------------


def test_new_objects_oversized_current_object_never_carries_prior_text_even_with_resolvable_base(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "big.txt").write_text("small prior version\n")  # under cap at the base
    base_sha = _commit(repo, "c1")

    (repo / "big.txt").write_text("a" * (6 * 1024 * 1024))  # 6 MB now, over cap
    tip_sha = _commit(repo, "c2")

    reader = GitSubprocessObjectReader()
    objects = list(reader.new_objects(repo, tip_sha, base_sha))

    big = next(obj for obj in objects if obj.path == "big.txt")
    assert big.oversized is True
    assert big.prior_text is None


def test_new_objects_prior_side_batch_check_failure_raises_typed_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A2.3 (unit tier — ``tests/integration/test_push_gate_denylist.py`` re-proves
    this over a real remote): a forced git failure on the prior-side ``--batch-check``
    lookup raises ``GitObjectReadError`` — never a silent 'no prior content'."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "notes.md").write_text("published\n")
    base_sha = _commit(repo, "c1")
    (repo / "notes.md").write_text("edited\n")
    tip_sha = _commit(repo, "c2")

    from dadaia_workspace.infrastructure import git_objects as git_objects_module

    real_run = git_objects_module._run
    marker = f"{base_sha}:".encode()

    def _flaky_run(
        args: list[str], cwd: Path, *, input_bytes: bytes | None = None
    ) -> subprocess.CompletedProcess[bytes]:
        if input_bytes is not None and marker in input_bytes:
            return subprocess.CompletedProcess(
                args, 1, stdout=b"", stderr=b"simulated prior-lookup failure"
            )
        return real_run(args, cwd, input_bytes=input_bytes)

    monkeypatch.setattr(git_objects_module, "_run", _flaky_run)

    reader = GitSubprocessObjectReader()
    with pytest.raises(GitObjectReadError, match="prior content"):
        list(reader.new_objects(repo, tip_sha, base_sha))


def test_prior_side_lookup_invocations_are_two_per_chunk_not_per_blob(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A2.5: the prior-side lookup costs exactly TWO extra batched calls per chunk
    (``--batch-check`` + ``--batch``), independent of the number of blobs in that
    chunk — never per-object."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    for i in range(7):
        (repo / f"f{i}.txt").write_text(f"original {i}\n")
    base_sha = _commit(repo, "c1")
    for i in range(7):
        (repo / f"f{i}.txt").write_text(f"edited {i}\n")
    tip_sha = _commit(repo, "c2")

    from dadaia_workspace.infrastructure import git_objects as git_objects_module

    monkeypatch.setattr(git_objects_module, "_BATCH_CHUNK_SIZE", 3)

    real_run = git_objects_module._run
    marker = f"{base_sha}:".encode()
    prior_calls: list[list[str]] = []

    def _spy_run(
        args: list[str], cwd: Path, *, input_bytes: bytes | None = None
    ) -> subprocess.CompletedProcess[bytes]:
        if input_bytes is not None and marker in input_bytes:
            prior_calls.append(args)
        return real_run(args, cwd, input_bytes=input_bytes)

    monkeypatch.setattr(git_objects_module, "_run", _spy_run)

    reader = GitSubprocessObjectReader()
    objects = list(reader.new_objects(repo, tip_sha, base_sha))

    assert len(objects) == 7
    # 7 blobs / chunk size 3 -> 3 chunks -> 2 prior-side calls per chunk = 6 total.
    assert len(prior_calls) == 6


def test_prior_side_lookup_dedups_a_repeated_path_within_one_chunk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A2.5 dedup clause: two DISTINCT blob shas at the SAME path within one chunk
    cost exactly ONE prior-side lookup line, not two — 'a path appearing twice costs
    one lookup' (PLAN §4)."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "file.txt").write_text("v1\n")
    base_sha = _commit(repo, "c1")
    (repo / "file.txt").write_text("v2\n")
    _commit(repo, "c2")
    (repo / "file.txt").write_text("v3\n")
    tip_sha = _commit(repo, "c3")

    from dadaia_workspace.infrastructure import git_objects as git_objects_module

    real_run = git_objects_module._run
    marker = f"{base_sha}:".encode()
    check_stdins: list[bytes] = []

    def _spy_run(
        args: list[str], cwd: Path, *, input_bytes: bytes | None = None
    ) -> subprocess.CompletedProcess[bytes]:
        if input_bytes is not None and marker in input_bytes and "--batch-check" in args[2]:
            check_stdins.append(input_bytes)
        return real_run(args, cwd, input_bytes=input_bytes)

    monkeypatch.setattr(git_objects_module, "_run", _spy_run)

    reader = GitSubprocessObjectReader()
    objects = list(reader.new_objects(repo, tip_sha, base_sha))

    matching = [obj for obj in objects if obj.path == "file.txt"]
    assert len(matching) == 2  # both the v2 and v3 blobs are new in this range.
    assert all(obj.prior_text == "v1\n" for obj in matching)

    assert len(check_stdins) == 1  # one chunk (well under 500) -> ONE batch-check call
    assert check_stdins[0].decode().count(f"{base_sha}:file.txt") == 1


# ═════════════════════════════════════════════════════════════════════════════════
# FR7 (v0.4.2, GRILL P10, ADR R1, D4) — no amnesty for a multi-path blob (fail-closed).
# A blob reachable at MORE THAN ONE path in the pushed range receives NO prior text at
# all, regardless of whether one of its paths individually has amnesty-eligible prior
# content at the base. Pre-fix, `_blob_info`'s "first-seen path wins" (GRILL P10) meant
# the surviving path — and therefore whether prior_text was attached at all — depended
# on `git rev-list`'s enumeration order, which is not a security-relevant property.
# ═════════════════════════════════════════════════════════════════════════════════

# Intent: CONTRACT — v0.4.2 A7.1


def test_new_objects_multi_path_blob_gets_no_prior_text_fail_closed(tmp_path: Path) -> None:
    """A7.1: a blob newly reachable at TWO paths in the range receives NO prior text —
    even though one of its two paths ('existing.md') individually has prior content at
    the base, which a pre-fix, path-keyed lookup could have attached to this blob."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "existing.md").write_text("old existing content\n")
    base_sha = _commit(repo, "c1")

    shared_new_content = "brand new shared content, reachable at two paths now\n"
    (repo / "existing.md").write_text(shared_new_content)
    (repo / "second.md").write_text(shared_new_content)
    tip_sha = _commit(repo, "c2")

    reader = GitSubprocessObjectReader()
    objects = list(reader.new_objects(repo, tip_sha, base_sha))

    multi_path_objs = [obj for obj in objects if obj.path in {"existing.md", "second.md"}]
    assert len(multi_path_objs) == 1, (
        "the shared blob must still be deduped by sha across its two paths (unchanged "
        "cross-path dedupe behaviour)"
    )
    assert multi_path_objs[0].prior_text is None, (
        "a blob reachable at more than one path must receive NO prior text at all, "
        "fail-closed (R1/D4) — even though 'existing.md' individually has prior "
        "content ('old existing content') at the base"
    )


# Intent: CONTRACT — v0.4.2 A7.1 (tree-order-independence fixture)


@pytest.mark.parametrize(
    ("existing_name", "new_name"),
    [
        pytest.param("aaa-existing.md", "zzz-second.md", id="existing-path-sorts-first"),
        pytest.param("zzz-existing.md", "aaa-second.md", id="existing-path-sorts-last"),
    ],
)
def test_new_objects_multi_path_amnesty_refusal_is_tree_order_independent(
    tmp_path: Path, existing_name: str, new_name: str
) -> None:
    """A7.1: the outcome (no prior text -> the matcher would refuse a denylisted value
    unconditionally) is IDENTICAL whether the existing-content path sorts before or
    after the brand-new path — proving the fix does not merely relocate the
    order-dependence (GRILL P10) rather than removing it. Pre-fix, ``_blob_info``'s
    first-seen-path-wins meant the 'existing-path-sorts-first' case could attach the
    existing path's prior text (amnesty-eligible) while the 'sorts-last' case could
    not — two different outcomes for the SAME semantic scenario, differing only by
    path name. Post-fix both parametrizations yield prior_text=None uniformly."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / existing_name).write_text("old existing content\n")
    base_sha = _commit(repo, "c1")

    shared_new_content = "brand new shared content, reachable at two paths now\n"
    (repo / existing_name).write_text(shared_new_content)
    (repo / new_name).write_text(shared_new_content)
    tip_sha = _commit(repo, "c2")

    reader = GitSubprocessObjectReader()
    objects = list(reader.new_objects(repo, tip_sha, base_sha))

    multi_path_objs = [obj for obj in objects if obj.path in {existing_name, new_name}]
    assert len(multi_path_objs) == 1
    assert multi_path_objs[0].prior_text is None


# ═════════════════════════════════════════════════════════════════════════════════
# CR-3 (v0.4.2 code-review MEDIUM; operator ruling: SPEC wins, widen to the range) —
# ``_multi_path_shas`` pre-remediation scoped detection to the pushed TIP's tree only.
# SPEC FR7/A7.1 say "reachable at more than one path in the RANGE": a blob multi-pathed
# in an INTERMEDIATE commit — but single-pathed (or absent) at the tip — must still be
# denied amnesty, fail-closed. The matcher and its amnesty predicate stay untouched
# (D4) — this is the ONLY place the decision widens.
# ═════════════════════════════════════════════════════════════════════════════════

# Intent: CONTRACT — v0.4.2 CR-3


def test_new_objects_multi_path_in_an_intermediate_commit_denies_amnesty_even_when_tip_is_single_path(
    tmp_path: Path,
) -> None:
    """CR-3: a blob reachable at TWO paths in an INTERMEDIATE commit of the pushed
    range, but at only ONE path in the pushed TIP's tree, must still receive NO prior
    text — the pre-remediation tip-tree-only scope would miss this (the second path
    was deleted again before the tip), silently granting amnesty for a blob that WAS
    published at two paths somewhere in the range."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "existing.md").write_text("old existing content\n")
    base_sha = _commit(repo, "c1")

    shared_new_content = "brand new shared content, reachable at two paths mid-range\n"
    (repo / "existing.md").write_text(shared_new_content)
    (repo / "second.md").write_text(shared_new_content)
    _commit(repo, "c2 (intermediate — multi-path here)")

    # c3 (tip): second.md's path is gone again — the blob survives ONLY at
    # existing.md, so the tip's own tree is single-path for this blob.
    _git(["rm", "second.md"], repo)
    tip_sha = _commit(repo, "c3 (tip — single-path here)")

    reader = GitSubprocessObjectReader()
    objects = list(reader.new_objects(repo, tip_sha, base_sha))

    shared_sha = _blob_sha(repo, "existing.md")
    surviving = next(obj for obj in objects if obj.sha == shared_sha)
    assert surviving.path == "existing.md"
    assert surviving.prior_text is None, (
        "the blob was reachable at two paths in the pushed RANGE (intermediate commit "
        "c2) — the tip's single-path tree must not grant amnesty just because the "
        "second path was deleted again before the tip"
    )
