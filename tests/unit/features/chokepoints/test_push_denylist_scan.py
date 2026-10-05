"""Wiring the push-range denylist scan into ``push_gate_decision`` (SPEC v0.9.0 FR1/FR2/FR5/FR6).

v0.9.0 A1.1-A1.4, A2.1-A2.4, A5.1-A5.4, A6.1; v0.11.0 A7.1-A7.3, A4.5,
A6.1-A6.3, A6.6, A5.1; v0.4.3 A11.1; 0.5.0 AC3.10

Every range is a real git range (``PushRepo``) read by the real ``GitSubprocessObjectReader``
(AC9.4). Only synthetic ``zz-`` terms ever appear here.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.container import load_denylist_terms
from dadaia_workspace.core.gitflow import DEFAULT
from dadaia_workspace.core.models.git_scan import GitObjectReadError, GitRunError, ScannedObject
from dadaia_workspace.features.chokepoints import push_gate_decision
from dadaia_workspace.features.chokepoints.branch_policy import parse_push_stdin
from dadaia_workspace.features.specs.canon import canon_violations
from dadaia_workspace.features.specs.doctor_adr import cites_an_accepted_adr
from dadaia_workspace.infrastructure.git_objects import GitSubprocessObjectReader
from dadaia_workspace.infrastructure.ledger_scripts import load_owner
from tests.fakes import gate_fixes
from tests.fixtures.real_git import ZERO, PushRepo, git

_SHA_A = "a" * 40
_TERM = "zz-secret-term"
_TERMS = ((_TERM, "synthetic"),)
_BIG = "clean content here\n" * 320_000  # > the reader's 5 MB per-blob cap
_PRIVATE = "zz-fake-private-owner"
_BOTH = (*_TERMS, (_PRIVATE, "synthetic"))
_SEG = f"repos/{_PRIVATE}"
_MASKED = "repos/[REDACTED-PATH-1]"


@pytest.fixture()
def repo(tmp_path: Path) -> PushRepo:
    return PushRepo(tmp_path)


def _decide(repo: PushRepo, *lines: str, source: Any = None, **kw: Any) -> Any:
    kw.setdefault("fixes", gate_fixes())
    return push_gate_decision(
        parse_push_stdin("\n".join(lines))[0],
        gitflow=DEFAULT,
        object_source=source or GitSubprocessObjectReader(),
        repo=repo.path,
        canon_violations_fn=canon_violations,
        cites_accepted_adr=cites_an_accepted_adr(None),
        **kw,
    )


def _branch(sha: str, remote: str = ZERO) -> str:
    return f"refs/heads/feature/0.0.1 {sha} refs/heads/feature/0.0.1 {remote}"


def _tag(sha: str, name: str = "v1") -> str:
    return f"refs/tags/{name} {sha} refs/tags/{name} {ZERO}"


def _gen() -> Iterable[tuple[str, str]]:
    yield (_TERM, "synthetic")


# fmt: off
@pytest.mark.parametrize(("files", "message", "ref", "terms", "in_message"), [
    pytest.param({"leak.md": f"{_TERM}\n"}, None, _branch, _TERMS, [], id="A1.1-blob-in-branch-range"),
    pytest.param({"tag-blob.md": f"{_TERM}\n"}, None, _tag, _TERMS, [], id="A2.1-tainted-tag"),
    pytest.param({"c.md": "clean\n"}, f"mentions {_TERM}", _branch, _TERMS,
                 ["Uncommit the unpublished range", "--no-verify"], id="A11.1-term-only-in-commit-message"),
    pytest.param({"leak.md": f"{_TERM}\n"}, None, _tag, "gen", ["denylisted term"], id="one-shot-generator-terms"),
    pytest.param({"t.py": f"{_TERM}\n"}, None, _branch, _TERMS, [
        "A test fixture that needs a secret shape composes it at runtime (string concatenation), never as a tracked literal."
    ], id="denylist-refusal-omits-the-runtime-composition-remedy"),
])
# fmt: on
def test_branch_push_with_denylisted_blob_in_range_is_refused(
    repo: PushRepo, files: dict[str, str], message: str | None, ref: Any, terms: Any, in_message: list[str]
) -> None:
    """A denylisted term anywhere in the pushed range (blob, tag, commit message) refuses; A5.2 never unmasked."""
    sha = repo.commit(files, message=message) if message else repo.commit(files)
    decision = _decide(repo, ref(sha), denylist_terms=_gen() if terms == "gen" else terms)
    assert not decision.allowed
    assert all(x in decision.message for x in in_message)
    assert _TERM not in decision.message


def test_term_outside_the_range_does_not_refuse(repo: PushRepo) -> None:
    """A1.2: a term reachable only from remote_sha is excluded from the range."""
    published = repo.commit({"leak.md": f"{_TERM}\n"})
    repo.publish()
    sha = repo.commit({"clean.md": "nothing here\n"})
    assert _decide(repo, _branch(sha, published), denylist_terms=_TERMS).allowed


def test_shared_blob_across_two_refs_is_deduped(repo: PushRepo) -> None:
    """A1.4: a blob reachable from two refs in one push is one Hit."""
    first = repo.commit({"shared.md": f"{_TERM} shows up\n"})
    second = repo.commit({"other.md": "clean\n"})
    blob = git(repo.path, "rev-parse", f"{first}:shared.md")
    decision = _decide(repo, _tag(first, "v1"), _tag(second, "v2"), denylist_terms=_TERMS)
    assert not decision.allowed
    assert decision.message.count(blob[:12]) == 1


def test_branch_policy_refusal_precedes_the_scan(repo: PushRepo) -> None:
    """A2.4."""
    sha = repo.commit({"leak.md": f"{_TERM}\n"})
    decision = _decide(repo, f"refs/heads/main {sha} refs/heads/main {'b' * 40}", denylist_terms=_TERMS)
    assert not decision.allowed
    assert "main" in decision.message
    assert "denylisted term" not in decision.message


def test_refusal_message_shape_and_ten_item_cap(repo: PushRepo) -> None:
    """A5.1/A5.3/A5.4: 12 hits, 10 shown, 2 remainder; masked; one switch fix line."""
    sha = repo.commit({f"file{i}.md": f"{_TERM} number {i}\n" for i in range(12)})
    message = _decide(repo, _branch(sha), fixes=replace(gate_fixes(), head="main"), denylist_terms=_TERMS).message
    for part in ("refs/heads/feature/0.0.1", "file0.md:1", "z…m", "operator denylist", "dd-release-implementation §2a",
                 "already-published history never needs a rewrite"):  # fmt: skip
        assert part in message
    assert "2 more" in message or "and 2" in message
    assert message.endswith("fix: git -C /repo switch feature/0.0.1")
    assert _TERM not in message


# fmt: off
@pytest.mark.parametrize(("local", "remote", "malformed"), [
    pytest.param("--glob=refs/x", ZERO, 1, id="A7.1-option-shaped-local-glob"),
    pytest.param("--branches=zzz", ZERO, 1, id="A7.1-option-shaped-local-branches"),
    pytest.param(_SHA_A, "--glob=refs/x", 1, id="A7.1-option-shaped-remote"),
    pytest.param("a" * 39, ZERO, 1, id="A7.3-39-hex"),
    pytest.param("a" * 41, ZERO, 1, id="A7.3-41-hex"),
    pytest.param("f" * 64, ZERO, 0, id="A7.3-sha256-parses"),
    pytest.param(ZERO, _SHA_A, 0, id="A7.2-zero-deletion-sentinel-parses"),
])
# fmt: on
def test_parse_push_stdin_admits_only_hex_sha_shapes(local: str, remote: str, malformed: int) -> None:
    refs, bad = parse_push_stdin(f"refs/heads/develop {local} refs/heads/develop {remote}\n")
    assert (len(refs), bad) == (1 - malformed, malformed)
    assert all(r.local_sha == local and r.is_deletion == (local == ZERO) for r in refs)


# fmt: off
@pytest.mark.parametrize("line", [
    pytest.param(f"refs/heads/old {ZERO} refs/heads/old {_SHA_A}", id="A1.3-deletion-never-scanned"),
    pytest.param("tag", id="A2.2-clean-tag-needs-no-verdict"),
])
# fmt: on
def test_a_deletion_or_clean_tag_is_allowed(repo: PushRepo, line: str) -> None:
    if line == "tag":
        line = _tag(repo.commit({"clean.md": "nothing here\n"}))
    assert _decide(repo, line, denylist_terms=_TERMS).allowed


# fmt: off
@pytest.mark.parametrize(("files", "terms", "allowed", "in_message", "in_warn"), [
    pytest.param({"big.md": _BIG}, (), True, [], ["big.md", str(len(_BIG)), "NOT scanned"], id="A4.5-note-on-allow"),
    pytest.param({"leak.md": f"{_TERM}\n", "big.md": _BIG}, _TERMS, False, [], ["big.md", "NOT scanned"], id="A4.5-note-on-refuse"),
    pytest.param({f"{_SEG}/notes.md": f"{_TERM}\n"}, _BOTH, False, [f"{_MASKED}/notes.md:1"], [], id="A6.1-hit-path-masked"),
    pytest.param({f"{_SEG}/big.md": _BIG}, ((_PRIVATE, "s"),), True, [], [f"{_MASKED}/big.md"], id="A6.3-note-path-masked"),
    pytest.param({f"{_SEG}/leak.md": f"{_TERM}\n", f"{_SEG}/big.md": _BIG}, _BOTH, False,
                 [f"{_MASKED}/leak.md"], [f"{_MASKED}/big.md"], id="one-masker-same-ordinal-across-hit-and-note"),
])
# fmt: on
def test_oversized_note_and_path_masking(
    repo: PushRepo, files: dict[str, str], terms: Any, allowed: bool, in_message: list[str], in_warn: list[str]
) -> None:
    """FR4/A4.5 the warn carries the oversized note; FR6(b) A6.1/A6.3/A6.6 offending path segments are masked everywhere."""
    decision = _decide(repo, _branch(repo.commit(files)), denylist_terms=terms)
    warn = decision.warn or ""
    assert decision.allowed is allowed
    assert all(x in decision.message for x in in_message)
    assert all(x in warn for x in in_warn)
    assert _PRIVATE not in decision.message + warn


def test_refusal_path_with_no_matching_segment_is_byte_identical(repo: PushRepo) -> None:
    """A6.2: a path matching no term renders as-is; the blob short sha stays locatable."""
    sha = repo.commit({"notes/plain-file.md": f"{_TERM} here\n"})
    decision = _decide(repo, _branch(sha), denylist_terms=_TERMS)
    assert "notes/plain-file.md:1" in decision.message
    assert "[REDACTED-PATH-" not in decision.message
    assert git(repo.path, "rev-parse", f"{sha}:notes/plain-file.md")[:12] in decision.message


@pytest.mark.parametrize("sep", ["\x9b", " "])
def test_refusal_path_segment_uppercase_hyphenated_variant_of_term_is_masked(repo: PushRepo, sep: str) -> None:
    """sa-path-segment-judged-by-two-matchers, sa-git-output-split-by-unicode-line-breaks — a segment split by U+009B or U+2028 is read whole (git output split on \\n only) and masked (A4.1)."""
    sha = repo.commit({f"repos/Zz-A{sep}cme-Corp/notes.md": "contains zz-acme here\n"})
    decision = _decide(repo, _branch(sha), denylist_terms=(("zz-acme", "synthetic"),))
    assert not decision.allowed
    assert f"Zz-A{sep}cme-Corp" not in decision.message
    assert f"{_MASKED}/notes.md:1" in decision.message


class _Raising:
    def __init__(self, exc: GitObjectReadError) -> None:
        self._exc = exc

    def remote_branch(self, repo: Path, branch: str) -> bool:
        return True

    def new_objects(self, repo: Path, local_sha: str, remote_sha: str) -> Iterable[ScannedObject]:
        raise self._exc


# fmt: off
@pytest.mark.parametrize(("exc", "in_message", "last_line"), [
    pytest.param(GitObjectReadError("stream desynchronised", path=f"{_SEG}/leak.md"),
                 [f"{_MASKED}/leak.md", "--no-verify"], "fix: git -C {repo} fsck", id="A4.2-read-failure-path-masked"),
    pytest.param(GitObjectReadError("stream desynchronised"), [], "fix: git -C {repo} fsck", id="S5-corruption-names-fsck"),
    pytest.param(GitRunError("git timed out"), [], "fix: Operator action: make git runnable here, then push again",
                 id="S5-git-cannot-run-no-fsck"),
])
# fmt: on
def test_a_git_read_failure_refuses_with_its_own_fix(
    repo: PushRepo, exc: GitObjectReadError, in_message: list[str], last_line: str
) -> None:
    """sa-fix-lines-not-built-by-cli-line#S5 — corruption's fix is `git -C <repo> fsck`; a git that cannot run is no corruption.

    The stub injects the one failure real git cannot produce on demand (a desynced cat-file stream).
    """
    sha = repo.commit({"x.md": "x\n"})
    decision = _decide(repo, _branch(sha), source=_Raising(exc), denylist_terms=((_PRIVATE, "s"),))
    assert not decision.allowed
    assert all(x in decision.message for x in in_message)
    assert _PRIVATE not in decision.message and "GitObjectReadError(" not in decision.message
    assert decision.message.splitlines()[-1] == last_line.format(repo=repo.path.as_posix())


# fmt: off
@pytest.mark.parametrize(("ref", "head", "end"), [
    pytest.param(_branch, "feature/0.0.1", "fix: git -C /repo reset --soft {oldest}", id="N3-reset-oldest-unpublished-then-amend"),
    pytest.param(_branch, "main", "fix: git -C /repo switch feature/0.0.1", id="H1-not-checked-out-switch-first"),
    pytest.param(lambda sha: _tag(sha, "v0.0.1"), "feature/0.0.1", None, id="N3-tag-operator-action-no-command"),
])
# fmt: on
def test_the_rewrite_fix_resets_to_the_oldest_unpublished_commit_and_amends(
    repo: PushRepo, ref: Any, head: str, end: str | None
) -> None:
    """c3 review 5 (C1, H1-H3): one fix line from the refused ref's own unpublished range, never HEAD or a ref deletion."""
    oldest = repo.commit({"a.md": "clean\n"})
    tip = repo.commit({"n.md": f"{_TERM}\n"})
    decision = _decide(repo, ref(tip), fixes=replace(gate_fixes(), head=head), denylist_terms=_TERMS)
    message = decision.message
    assert not decision.allowed and "update-ref" not in message
    if end is None:
        assert "\nfix: Operator action: " in message and message.count("\nfix: ") == 1
    else:
        assert message.endswith(end.format(oldest=oldest)) and message.count("\nfix: ") == 1
        assert "reset" not in end or "commit --amend" in message


def test_a_ledger_verb_outside_the_workspace_loads_the_pre_push_terms(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC3.10 / privacy-denylist-has-two-loaders (ADR 0157): run from a cwd outside the
    workspace, the ledger write seam finds the terms from its `--specs` tree, as pre-push does."""
    states = tmp_path / "ws" / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text('{"contexts": []}')
    (states / "privacy_denylist.json").write_text(json.dumps(dict(_TERMS)))
    specs = tmp_path / "ws" / "repos" / "r" / "specs"
    specs.mkdir(parents=True)
    monkeypatch.delenv("DADAIA_PRIVACY_DENYLIST", raising=False)
    monkeypatch.chdir(specs)
    assert load_denylist_terms() == _TERMS
    monkeypatch.chdir(tmp_path)
    ledger = load_owner("dd-bug-resolution", "_ledger")
    assert ledger.private_refusal([{"title": f"a {_TERM} leak"}], specs) is not None
