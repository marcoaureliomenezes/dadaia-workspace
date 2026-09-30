"""GitSubprocessObjectReader — the GitObjectReader adapter, driven over real git repos.

Intent: CONTRACT — v0.9.0 A1.1-A1.4, A6.1, A6.2; v0.11.0 A2.1-A2.4, A4.1, A4.2, A4.6, A7.4,
A8.1, A8.2; v0.4.2 A7.1, A8.4, CR-1, CR-3; v0.4.3 A11.1-A11.4, A11.6, A11.7;
bug new-branch-push-loses-prior-published-denylist-amnesty; 0.5.0 AC5.1/AC5.2.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

from dadaia_workspace.core.models.git_scan import ZERO_SHA, GitObjectReadError, ScannedObject
from dadaia_workspace.infrastructure import git_objects
from dadaia_workspace.infrastructure.git_objects import GitSubprocessObjectReader, unpublished

pytestmark = [pytest.mark.integration, pytest.mark.slow]

BIG = 6 * 1024 * 1024  # over the adapter's 5 MB cap
Tree = dict[str, "str | bytes | None"]  # path -> content; None deletes the path


def _git(args: list[str], cwd: Path) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    ).stdout.strip()


def _repo(tmp_path: Path, *commits: Tree) -> tuple[Path, list[str]]:
    """A repo with one commit per tree, returning the commit shas oldest first."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(["init", "-q"], repo)
    _git(["config", "user.email", "t@example.com"], repo)
    _git(["config", "user.name", "T"], repo)
    shas = []
    for i, tree in enumerate(commits):
        for rel, content in tree.items():
            target = repo / rel
            if content is None:
                _git(["rm", "-rq", rel], repo)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(content, bytes):
                target.write_bytes(content)
            else:
                target.write_text(content)
        _git(["add", "-A"], repo)
        _git(["commit", "-q", "--allow-empty", "-m", f"c{i}"], repo)
        shas.append(_git(["rev-parse", "HEAD"], repo))
    return repo, shas


def _scan(repo: Path, local: str, remote: str) -> list[ScannedObject]:
    return list(GitSubprocessObjectReader().new_objects(repo, local, remote))


def _blobs(objects: list[ScannedObject]) -> set[str]:
    return {obj.path for obj in objects if obj.kind == "blob"}


def _bodies(objects: list[ScannedObject], kind: str = "commit") -> list[ScannedObject]:
    return [obj for obj in objects if obj.kind == kind]


def _publish(repo: Path, tmp_path: Path, branch: str) -> None:
    remote = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
    _git(["remote", "add", "origin", str(remote)], repo)
    _git(["push", "-q", "origin", f"HEAD:refs/heads/{branch}"], repo)
    _git(["fetch", "-q", "origin"], repo)


@pytest.mark.parametrize(
    ("remote", "expected"),
    [
        pytest.param("base", {"b.txt"}, id="resolvable-remote-scopes-to-the-delta"),
        pytest.param(ZERO_SHA, {"a.txt", "b.txt"}, id="new-ref-falls-back-to-not-remotes"),
        pytest.param("f" * 40, {"a.txt", "b.txt"}, id="unresolvable-remote-falls-back"),
        pytest.param("--upload-pack=/bin/false", {"a.txt", "b.txt"}, id="option-shaped-remote"),
    ],
)
def test_the_range_form_decides_which_blobs_are_new(
    tmp_path: Path, remote: str, expected: set[str]
) -> None:
    """A1.1-A1.3, A7.4: a resolvable remote scopes the range; anything else falls back to
    ``--not --remotes`` (no remote here: everything). A2.2: no object ever carries prior
    text for a path that did not exist at a resolvable base."""
    repo, (base, tip) = _repo(tmp_path, {"a.txt": "one\n"}, {"b.txt": "two\n"})
    objects = _scan(repo, tip, base if remote == "base" else remote)
    assert _blobs(objects) == expected
    assert all(obj.prior_text is None for obj in objects)


@pytest.mark.parametrize("remote", ["base", ZERO_SHA])
def test_rev_list_argv_carries_trailing_end_of_options_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, remote: str
) -> None:
    """A7.4: both range forms end the rev-list argv with ``--``."""
    repo, (base, tip) = _repo(tmp_path, {"a.txt": "one\n"}, {"b.txt": "two\n"})
    real_run = git_objects._run
    argvs: list[list[str]] = []

    def spy(
        args: list[str], cwd: Path, *, input_bytes: bytes | None = None
    ) -> subprocess.CompletedProcess[bytes]:
        if args[:3] == ["git", "rev-list", "--objects"]:
            argvs.append(args)
        return real_run(args, cwd, input_bytes=input_bytes)

    monkeypatch.setattr(git_objects, "_run", spy)
    _scan(repo, tip, base if remote == "base" else remote)
    assert argvs and argvs[0][-1] == "--"


def test_an_option_shaped_local_sha_is_refused_before_git_runs(tmp_path: Path) -> None:
    repo, _ = _repo(tmp_path, {"a.txt": "one\n"})
    with pytest.raises(GitObjectReadError, match="local_sha"):
        _scan(repo, "--upload-pack=/bin/false", ZERO_SHA)


def test_a_deletion_sha_scans_nothing(tmp_path: Path) -> None:
    repo, (tip,) = _repo(tmp_path, {"a.txt": "one\n"})
    assert _scan(repo, ZERO_SHA, tip) == []


def test_a_blob_shared_by_two_paths_is_yielded_once(tmp_path: Path) -> None:
    """A1.4: one object per distinct blob sha."""
    repo, (tip,) = _repo(tmp_path, {"a.txt": "same\n", "b.txt": "same\n"})
    assert [o.path for o in _scan(repo, tip, ZERO_SHA) if o.kind == "blob"] in (
        ["a.txt"],
        ["b.txt"],
    )


@pytest.mark.parametrize(
    ("content", "decodable", "oversized", "text_len"),
    [
        pytest.param(b"\x00\x01\xff\xfe binary", False, False, 0, id="binary-is-undecodable"),
        pytest.param("a" * BIG, True, True, 5 * 1024 * 1024, id="oversized-text-scans-the-cap"),
        pytest.param(b"\xff" * BIG, False, True, 0, id="oversized-undecodable-prefix"),
    ],
)
def test_blob_decoding_and_the_size_cap(
    tmp_path: Path, content: str | bytes, decodable: bool, oversized: bool, text_len: int
) -> None:
    """A6.2, A4.1, A4.2, A4.6: undecodable -> empty text; oversized -> at most the cap is read."""
    repo, (tip,) = _repo(tmp_path, {"x": content, "small.txt": "tiny\n"})
    objects = {obj.path: obj for obj in _scan(repo, tip, ZERO_SHA)}
    blob = objects["x"]
    assert (blob.decodable, blob.oversized, len(blob.text)) == (decodable, oversized, text_len)
    if oversized:
        assert (blob.size_bytes, blob.scanned_bytes) == (BIG, 5 * 1024 * 1024)
    assert objects["small.txt"].text == "tiny\n"


@pytest.mark.parametrize(
    ("commits", "prior"),
    [
        pytest.param([{"n.md": "old\n"}, {"n.md": "new\n"}], "old\n", id="edited-path"),
        pytest.param([{"e.md": "x\n"}, {"new.md": "y\n"}], None, id="new-path"),
        pytest.param(
            [{"e.md": "x\n"}, {"d/my other file.md": "y\n"}],
            None,
            id="CR-1-new-path-with-two-spaces",
        ),
        pytest.param([{"b.txt": "a" * BIG}, {"b.txt": "s\n"}], None, id="over-cap-prior"),
        pytest.param([{"b.txt": "s\n"}, {"b.txt": "a" * BIG}], None, id="over-cap-current"),
        pytest.param([{"n.md": b"\xff\xfe"}, {"n.md": "t\n"}], None, id="undecodable-prior"),
        pytest.param(
            [{"foo/bar.txt": "x\n"}, {"foo/bar.txt": None, "foo": "file\n"}],
            None,
            id="directory-at-base",
        ),
        pytest.param(
            [{"f.txt": "v1\n"}, {"f.txt": "v2\n"}, {"f.txt": "v3\n"}],
            "v1\n",
            id="two-new-blobs-at-one-path",
        ),
        pytest.param(
            [{"aaa.md": "old\n"}, {"aaa.md": "shared\n", "zzz.md": "shared\n"}],
            None,
            id="A7.1-multi-path-existing-sorts-first",
        ),
        pytest.param(
            [{"zzz.md": "old\n"}, {"zzz.md": "shared\n", "aaa.md": "shared\n"}],
            None,
            id="A7.1-multi-path-existing-sorts-last",
        ),
        pytest.param(
            [{"e.md": "old\n"}, {"e.md": "shared\n", "s.md": "shared\n"}, {"s.md": None}],
            None,
            id="CR-3-multi-path-only-mid-range",
        ),
    ],
)
def test_prior_text_is_the_base_text_of_the_same_single_path(
    tmp_path: Path, commits: list[Tree], prior: str | None
) -> None:
    """A2.1, A2.4, A7.1, CR-3: prior text only for a single-path, under-cap, decodable
    blob whose path held a blob at the base; every other case is an explicit ``None``.
    Each row's range holds only the blobs under test (a shared blob dedupes to one)."""
    repo, shas = _repo(tmp_path, *commits)
    blobs = [o for o in _scan(repo, shas[-1], shas[0]) if o.kind == "blob"]
    assert blobs
    assert all(obj.prior_text == prior for obj in blobs)


def _fail(rc: int) -> Callable[[list[str]], subprocess.CompletedProcess[bytes]]:
    return lambda args: subprocess.CompletedProcess(args, rc, stdout=b"", stderr=b"boom")


def _out(stdout: str) -> Callable[[list[str]], subprocess.CompletedProcess[bytes]]:
    return lambda args: subprocess.CompletedProcess(args, 0, stdout=stdout.encode(), stderr=b"")


def _timeout(args: list[str]) -> subprocess.CompletedProcess[bytes]:
    raise subprocess.TimeoutExpired(cmd=args, timeout=30)


# (call, stdin) predicates; "blob" = the tip's a.txt blob sha, "base"/"tip" = commit shas.
_CURRENT_CHECK = "current-batch-check"
_PRIOR_CHECK = "prior-batch-check"
_CONTENT = "content-batch"
_BODIES = "commit-body-batch"


@pytest.mark.parametrize(
    ("call", "reply", "match"),
    [
        pytest.param(_CONTENT, "{blob} blob 6", "desynchronised", id="A8.1-truncated-stream"),
        pytest.param(_CONTENT, "{blob} blob abc\nhello\n", "desynchronised", id="A8.1-size-nan"),
        pytest.param(_CONTENT, "{blob} blob 6 x\nhello\n", "desynchronised", id="A8.2-4-fields"),
        pytest.param(_CURRENT_CHECK, "garbled\n", "batch-check", id="A8.4-check-row-fields"),
        pytest.param(_CURRENT_CHECK, "{blob} blob nan\n", "batch-check", id="A8.4-check-size"),
        pytest.param(_CURRENT_CHECK, _timeout, None, id="check-timeout"),
        pytest.param(_PRIOR_CHECK, "garbled\n", "batch-check", id="A8.4-prior-row"),
        pytest.param(_PRIOR_CHECK, _fail(1), "prior content", id="A2.3-prior-lookup-fails"),
        pytest.param(_BODIES, _fail(1), None, id="A11.4-commit-body-read-fails"),
    ],
)
def test_a_corrupt_or_failing_git_answer_raises_the_typed_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    call: str,
    reply: str | Callable[[list[str]], subprocess.CompletedProcess[bytes]],
    match: str | None,
) -> None:
    """A6.1, A8.1, A8.2, A8.4, A2.3, A11.4: never a raw exception, never a
    fabricated undecodable object."""
    repo, (base, tip) = _repo(tmp_path, {"a.txt": "hello\n"}, {"a.txt": "edited\n"})
    blob = _git(["rev-parse", "HEAD:a.txt"], repo)
    real_run = subprocess.run

    def is_target(args: list[str], stdin: bytes) -> bool:
        check = args[:2] == ["git", "cat-file"] and args[2].startswith("--batch-check")
        prior = f"{base}:".encode() in stdin
        return {
            _CURRENT_CHECK: check and not prior,
            _PRIOR_CHECK: check and prior,
            _CONTENT: args == ["git", "cat-file", "--batch"] and blob.encode() in stdin,
            _BODIES: args == ["git", "cat-file", "--batch"] and stdin.strip() == tip.encode(),
        }[call]

    def fake(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        stdin = kwargs.get("input") or b""
        assert isinstance(stdin, bytes)
        if not is_target(args, stdin):
            return real_run(args, **kwargs)  # type: ignore[call-overload, no-any-return]
        if isinstance(reply, str):
            return _out(reply.format(blob=blob))(args)
        return reply(args)

    monkeypatch.setattr(git_objects.subprocess, "run", fake)
    yielded: list[ScannedObject] = []
    with pytest.raises(GitObjectReadError, match=match):
        yielded.extend(GitSubprocessObjectReader().new_objects(repo, tip, base))
    assert [o for o in yielded if not o.decodable] == []


def test_a_directory_that_is_not_a_repo_raises_the_typed_error(tmp_path: Path) -> None:
    with pytest.raises(GitObjectReadError):
        _scan(tmp_path, "a" * 40, ZERO_SHA)


def test_each_range_commit_body_is_scanned_without_its_header(tmp_path: Path) -> None:
    """A11.1, A11.2, A11.6, A11.7: empty commits still yield their bodies; the identity
    header never reaches the text; a repeated published message is never amnestied."""
    repo, (base,) = _repo(tmp_path, {"a.txt": "x\n"})
    _git(["config", "user.name", "HeaderOnlyName"], repo)
    _git(["commit", "-q", "--allow-empty", "-m", "one SECRET"], repo)
    _git(["commit", "-q", "--allow-empty", "-m", "c0"], repo)
    tip = _git(["rev-parse", "HEAD"], repo)

    objects = _scan(repo, tip, base)

    assert _blobs(objects) == set()
    assert sorted(obj.text for obj in _bodies(objects)) == ["c0\n", "one SECRET\n"]
    assert all(obj.prior_text is None and obj.path != "a.txt" for obj in _bodies(objects))
    assert tip in {obj.sha for obj in _bodies(objects)}


@pytest.mark.parametrize(("annotated", "tags"), [(True, 1), (False, 0)])
def test_only_an_annotated_tag_yields_its_own_body(
    tmp_path: Path, annotated: bool, tags: int
) -> None:
    """A11.3: a lightweight tag is no object of its own; the commit body is yielded either way."""
    repo, _ = _repo(tmp_path, {"a.txt": "x\n"})
    _git(["tag", *(["-a", "-m", "tag notes SECRET"] if annotated else []), "v9"], repo)
    tag_sha = _git(["rev-parse", "v9"], repo)
    objects = _scan(repo, tag_sha, ZERO_SHA)
    assert [o.text for o in _bodies(objects, "tag")] == ["tag notes SECRET\n"] * tags
    assert len(_bodies(objects)) == 1


def test_mergetag_embedded_tag_body_reaches_the_matcher(tmp_path: Path) -> None:
    """CWE-184: a signed-tag merge folds the tag's body into the commit HEADER region;
    its body is scanned, its own header lines are not (synthetic block, no GPG key)."""
    repo, (base,) = _repo(tmp_path, {"a.txt": "x\n"})
    raw = subprocess.run(
        ["git", "cat-file", "commit", base], cwd=repo, capture_output=True, check=True
    ).stdout
    header, _, rest = raw.partition(b"\n\n")
    block = (
        b"mergetag object " + base.encode() + b"\n type commit\n tag v9\n"
        b" tagger T <t@example.com> 1700000000 +0000\n \n SECRET-IN-MERGETAG-BODY probe\n"
    )
    sha = (
        subprocess.run(
            ["git", "hash-object", "-t", "commit", "-w", "--stdin"],
            cwd=repo,
            input=header + b"\n" + block + b"\n\n" + rest,
            capture_output=True,
            check=True,
        )
        .stdout.decode()
        .strip()
    )

    (body,) = _bodies(_scan(repo, sha, ZERO_SHA))
    assert "SECRET-IN-MERGETAG-BODY probe" in body.text
    assert "tagger T" not in body.text


def test_a_new_branch_keeps_amnesty_for_what_origin_already_published(tmp_path: Path) -> None:
    """bug new-branch-push-loses-prior-published-denylist-amnesty: a ZERO_SHA push of a
    branch cut from published history still resolves prior text for published paths, and
    only for them; the resolvable-remote form yields the identical result."""
    repo, (base,) = _repo(tmp_path, {"ledger.jsonl": "first\n"})
    _publish(repo, tmp_path, "develop")
    _git(["checkout", "-q", "-b", "feature/1.0.0"], repo)
    (repo / "ledger.jsonl").write_text("first\nsecond\n")
    (repo / "brand-new.md").write_text("new\n")
    _git(["add", "-A"], repo)
    _git(["commit", "-q", "-m", "c1"], repo)
    tip = _git(["rev-parse", "HEAD"], repo)

    def shape(objs: list[ScannedObject]) -> dict[str, str | None]:
        return {o.path: o.prior_text for o in objs if o.kind == "blob"}

    assert shape(_scan(repo, tip, ZERO_SHA)) == {"ledger.jsonl": "first\n", "brand-new.md": None}
    assert shape(_scan(repo, tip, base)) == shape(_scan(repo, tip, ZERO_SHA))


def _published_repo(tmp_path: Path) -> tuple[Path, str]:
    """A repo whose one commit is already on a bare ``origin``."""
    remote = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
    repo, (sha,) = _repo(tmp_path, {"a.txt": "first\n"})
    _git(["remote", "add", "origin", str(remote)], repo)
    _git(["push", "-q", "origin", "HEAD:refs/heads/main"], repo)
    return repo, sha


def test_a_commit_already_on_origin_publishes_nothing(tmp_path: Path) -> None:
    repo, sha = _published_repo(tmp_path)
    assert GitSubprocessObjectReader().unpublished(repo, sha) == []


def test_the_unpublished_range_is_newest_first_and_ignores_an_advanced_origin(
    tmp_path: Path,
) -> None:
    """H2/N3: the oldest entry is where the rewrite fix resets — never origin's tip."""
    repo, _ = _published_repo(tmp_path)
    _git(["checkout", "-q", "-b", "topic"], repo)
    _git(["commit", "-q", "--allow-empty", "-m", "mine"], repo)
    oldest = _git(["rev-parse", "HEAD"], repo)
    _git(["commit", "-q", "--allow-empty", "-m", "more"], repo)
    tip = _git(["rev-parse", "HEAD"], repo)
    _git(["checkout", "-q", "main"], repo)
    _git(["commit", "-q", "--allow-empty", "-m", "dep"], repo)
    _git(["push", "-q", "origin", "main"], repo)
    assert GitSubprocessObjectReader().unpublished(repo, tip) == [tip, oldest]


def test_a_range_reaching_a_root_commit_ends_at_the_root(tmp_path: Path) -> None:
    """N3: an empty origin is the same formula — the oldest commit is the root."""
    repo, (root, sha) = _repo(tmp_path, {}, {})
    assert GitSubprocessObjectReader().unpublished(repo, sha) == [sha, root]


def test_a_commit_only_another_remote_holds_is_still_unpublished(tmp_path: Path) -> None:
    """SA-H3-1: "published" means on origin — one rule for the gate and ``unpushed``."""
    repo, (sha,) = _repo(tmp_path, {})
    _git(["update-ref", "refs/remotes/fork/main", sha], repo)
    assert unpublished(repo, sha) == [sha]
    _git(["update-ref", "refs/remotes/origin/main", sha], repo)
    assert unpublished(repo, sha) == []


@pytest.mark.parametrize("sha", ["a" * 40, "--upload-pack=evil"])
def test_an_unresolvable_or_option_shaped_sha_fails_closed(tmp_path: Path, sha: str) -> None:
    """Unreadable counts as unpublished: never a birth, never an empty range."""
    repo, _ = _published_repo(tmp_path)
    assert GitSubprocessObjectReader().unpublished(repo, sha) == [sha]
