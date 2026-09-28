"""Wiring the push-range denylist scan into ``push_gate_decision`` (SPEC v0.9.0 FR1/FR2/FR5/FR6).

Intent: CONTRACT — v0.9.0 A1.1, A1.2, A1.3, A1.4, A2.1, A2.2, A2.3, A2.4, A5.1, A5.2,
A5.3, A5.4, A6.1; v0.11.0 A7.1, A7.2, A7.3, A4.5, A6.1, A6.2, A6.3, A6.6, A5.1

Every range is a real git range (``tests.fixtures.real_git.PushRepo``) read by the real
``GitSubprocessObjectReader`` (AC9.4). Only synthetic terms ever appear here (TASKS
standing rule): ``zz-``-prefixed values, never a real operator term.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.core.gitflow import DEFAULT
from dadaia_workspace.core.models.git_scan import GitObjectReadError, GitRunError, ScannedObject
from dadaia_workspace.features.chokepoints import push_gate_decision
from dadaia_workspace.features.chokepoints.branch_policy import parse_push_stdin
from dadaia_workspace.features.specs.canon import canon_violations
from dadaia_workspace.infrastructure.git_objects import GitSubprocessObjectReader
from tests.fakes import gate_fixes
from tests.fixtures.real_git import ZERO, PushRepo, git

_SHA_A = "a" * 40
_ZERO = ZERO
_SYNTHETIC_TERM = "zz-secret-term"
_TERMS = ((_SYNTHETIC_TERM, "synthetic"),)
_BIG = "clean content here\n" * 320_000  # > the reader's 5 MB per-blob cap


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
        **kw,
    )


def _branch(sha: str, remote: str = _ZERO) -> str:
    return f"refs/heads/feature/0.0.1 {sha} refs/heads/feature/0.0.1 {remote}"


def _tag(sha: str, name: str = "v1") -> str:
    return f"refs/tags/{name} {sha} refs/tags/{name} {_ZERO}"


# A1.1 — a branch ref whose range carries a denylist term is refused.
def test_branch_push_with_denylisted_blob_in_range_is_refused(repo: PushRepo) -> None:
    sha = repo.commit({"leak.md": f"contains {_SYNTHETIC_TERM} here\n"})
    decision = _decide(repo, _branch(sha), denylist_terms=_TERMS)
    assert not decision.allowed
    assert _SYNTHETIC_TERM not in decision.message  # A5.2: never unmasked.


# A1.2 — a term reachable only from remote_sha (excluded from the range) never refuses.
def test_term_outside_the_range_does_not_refuse(repo: PushRepo) -> None:
    published = repo.commit({"leak.md": f"{_SYNTHETIC_TERM}\n"})
    repo.publish()
    sha = repo.commit({"clean.md": "nothing here\n"})
    assert _decide(repo, _branch(sha, published), denylist_terms=_TERMS).allowed


# A1.3 / A2.3 — a deletion ref is never scanned (and never verdict-checked).
def test_deletion_ref_is_never_scanned(repo: PushRepo) -> None:
    decision = _decide(
        repo, f"refs/heads/old {_ZERO} refs/heads/old {_SHA_A}", denylist_terms=_TERMS
    )
    assert decision.allowed


# A1.4 — a blob reachable from two refs in the same push is deduped (one Hit, not two).
def test_shared_blob_across_two_refs_is_deduped(repo: PushRepo) -> None:
    first = repo.commit({"shared.md": f"{_SYNTHETIC_TERM} shows up\n"})
    second = repo.commit({"other.md": "clean\n"})
    blob = git(repo.path, "rev-parse", f"{first}:shared.md")
    decision = _decide(repo, _tag(first, "v1"), _tag(second, "v2"), denylist_terms=_TERMS)
    assert not decision.allowed
    assert decision.message.count(blob[:12]) == 1


# A2.1 — a tainted tag push is refused.
def test_tainted_tag_push_is_refused(repo: PushRepo) -> None:
    sha = repo.commit({"tag-blob.md": f"{_SYNTHETIC_TERM}\n"})
    assert not _decide(repo, _tag(sha), denylist_terms=_TERMS).allowed


# A2.2 — a clean tag push is allowed with NO security-verdict lookup (DP-5 intact).
def test_clean_tag_push_is_allowed_with_no_verdict_required(repo: PushRepo) -> None:
    sha = repo.commit({"clean.md": "nothing here\n"})
    assert _decide(repo, _tag(sha), denylist_terms=_TERMS).allowed


# A2.4 — branch policy still runs BEFORE the scan.
def test_branch_policy_refusal_precedes_the_scan(repo: PushRepo) -> None:
    sha = repo.commit({"leak.md": f"{_SYNTHETIC_TERM}\n"})
    decision = _decide(
        repo, f"refs/heads/main {sha} refs/heads/main {'b' * 40}", denylist_terms=_TERMS
    )
    assert not decision.allowed
    assert "main" in decision.message
    assert "denylisted term" not in decision.message


# A5.1 / A5.3 / A5.4 — the refusal message shape and the 10-item cap.
def test_refusal_message_shape_and_ten_item_cap(repo: PushRepo) -> None:
    sha = repo.commit({f"file{i}.md": f"{_SYNTHETIC_TERM} number {i}\n" for i in range(12)})
    decision = _decide(
        repo, _branch(sha), fixes=replace(gate_fixes(), head="main"), denylist_terms=_TERMS
    )
    assert not decision.allowed
    message = decision.message
    assert "refs/heads/feature/0.0.1" in message
    assert "file0.md:1" in message
    assert "z…m" in message  # masked form of the synthetic term.
    assert "operator denylist" in message
    assert "dd-release-implementation §2a" in message
    assert message.endswith("fix: git -C /repo switch feature/0.0.1")
    assert "already-published history never needs a rewrite" in message
    assert "2 more" in message or "and 2" in message  # 12 hits, 10 shown, 2 remainder.
    assert _SYNTHETIC_TERM not in message


def test_refusal_names_runtime_composition_as_the_fixture_remedy(repo: PushRepo) -> None:
    """denylist-refusal-omits-the-runtime-composition-remedy: the refusal names the edit."""
    sha = repo.commit({"t.py": f"{_SYNTHETIC_TERM}\n"})
    assert (
        "A test fixture that needs a secret shape composes it at runtime "
        "(string concatenation), never as a tracked literal."
    ) in _decide(repo, _branch(sha), denylist_terms=_TERMS).message


# v0.11.0 review MEDIUM — a one-shot generator of terms is consumed once, still refuses.
def test_generator_denylist_terms_still_refuses_not_silently_emptied(repo: PushRepo) -> None:
    sha = repo.commit({"leak.md": f"contains {_SYNTHETIC_TERM} here\n"})

    def _term_generator() -> Iterable[tuple[str, str]]:
        yield (_SYNTHETIC_TERM, "synthetic")

    decision = _decide(repo, _tag(sha), denylist_terms=_term_generator())
    assert not decision.allowed
    assert "denylisted term" in decision.message
    assert _SYNTHETIC_TERM not in decision.message


# ---------------------------------------------------------------------------
# FR7/A7.1 — an option-shaped `local_sha` refuses as a malformed line instead of
# silently producing a successful empty rev-list.
# ---------------------------------------------------------------------------


def test_option_shaped_local_sha_glob_form_is_malformed() -> None:
    refs, malformed = parse_push_stdin(
        f"refs/heads/develop --glob=refs/nonexistent refs/heads/develop {_ZERO}\n"
    )
    assert refs == []
    assert malformed == 1


def test_option_shaped_local_sha_branches_form_is_malformed() -> None:
    refs, malformed = parse_push_stdin(
        f"refs/heads/develop --branches=zzz refs/heads/develop {_ZERO}\n"
    )
    assert refs == []
    assert malformed == 1


def test_option_shaped_remote_sha_is_also_malformed() -> None:
    """The same option-shaped hardening applies symmetrically to ``remote_sha``."""
    refs, malformed = parse_push_stdin(
        f"refs/heads/develop {_SHA_A} refs/heads/develop --glob=refs/nonexistent\n"
    )
    assert refs == []
    assert malformed == 1


# ---------------------------------------------------------------------------
# FR7/A7.2 — the all-zero deletion sentinel still parses and still passes with no
# verdict (it is 40 hex characters, so it is a VALID sha shape, not a malformed one).
# ---------------------------------------------------------------------------


def test_all_zero_deletion_sentinel_still_parses() -> None:
    refs, malformed = parse_push_stdin(f"refs/heads/old {_ZERO} refs/heads/old {_SHA_A}\n")
    assert malformed == 0
    assert len(refs) == 1
    assert refs[0].is_deletion


# ---------------------------------------------------------------------------
# FR7/A7.3 — a 64-char (SHA-256) sha parses; a 39- or 41-char hex string does not.
# ---------------------------------------------------------------------------


def test_sha256_length_local_sha_parses() -> None:
    sha256 = "f" * 64
    refs, malformed = parse_push_stdin(f"refs/heads/develop {sha256} refs/heads/develop {_ZERO}\n")
    assert malformed == 0
    assert len(refs) == 1
    assert refs[0].local_sha == sha256


def test_39_and_41_char_hex_shas_are_malformed() -> None:
    too_short = "a" * 39
    too_long = "a" * 41

    _, malformed_short = parse_push_stdin(
        f"refs/heads/develop {too_short} refs/heads/develop {_ZERO}\n"
    )
    _, malformed_long = parse_push_stdin(
        f"refs/heads/develop {too_long} refs/heads/develop {_ZERO}\n"
    )
    assert malformed_short == 1
    assert malformed_long == 1


# FR4/A4.5 (v0.11.0) — `decision.warn` carries the oversized-blob note on allow and refuse.
def test_oversized_note_appears_in_decision_warn_on_allow(repo: PushRepo) -> None:
    sha = repo.commit({"big.md": _BIG})
    decision = _decide(repo, _tag(sha))
    assert decision.allowed
    assert decision.warn is not None
    assert "big.md" in decision.warn
    assert str(len(_BIG)) in decision.warn
    assert "NOT scanned" in decision.warn


def test_oversized_note_appears_in_decision_warn_on_refuse(repo: PushRepo) -> None:
    sha = repo.commit({"leak.md": f"{_SYNTHETIC_TERM} shows up here\n", "big.md": _BIG})
    decision = _decide(repo, _branch(sha), denylist_terms=_TERMS)
    assert not decision.allowed
    assert decision.warn is not None
    assert "big.md" in decision.warn
    assert "NOT scanned" in decision.warn


# FR6(b)/A6.1-A6.3/A6.6 (v0.11.0) — the blob path is masked at its offending segments in
# the refusal and the oversized note; a path matching nothing renders byte-identical.
_PRIVATE_SEGMENT = "zz-fake-private-owner"
_BOTH = (*_TERMS, (_PRIVATE_SEGMENT, "synthetic"))


def test_refusal_path_segment_matching_an_operator_term_is_masked(repo: PushRepo) -> None:
    sha = repo.commit({f"repos/{_PRIVATE_SEGMENT}/notes.md": f"{_SYNTHETIC_TERM} appears\n"})
    blob = git(repo.path, "rev-parse", f"{sha}:repos/{_PRIVATE_SEGMENT}/notes.md")
    decision = _decide(repo, _branch(sha), denylist_terms=_BOTH)
    assert not decision.allowed
    assert _PRIVATE_SEGMENT not in decision.message  # A6.6: never unmasked, anywhere.
    assert "repos/[REDACTED-PATH-1]/notes.md:1" in decision.message
    assert blob[:12] in decision.message  # short sha untouched — still locatable.


def test_refusal_path_with_no_matching_segment_is_byte_identical(repo: PushRepo) -> None:
    """A6.2 regression fixture: a path matching no term renders as-is."""
    sha = repo.commit({"notes/plain-file.md": f"{_SYNTHETIC_TERM} here\n"})
    decision = _decide(repo, _branch(sha), denylist_terms=_TERMS)
    assert not decision.allowed
    assert "notes/plain-file.md:1" in decision.message
    assert "[REDACTED-PATH-" not in decision.message


def test_oversized_note_path_segment_is_masked_too(repo: PushRepo) -> None:
    """A6.3: the FR4 oversized note's path is masked by the SAME rule."""
    sha = repo.commit({f"repos/{_PRIVATE_SEGMENT}/big.md": _BIG})
    decision = _decide(repo, _tag(sha), denylist_terms=((_PRIVATE_SEGMENT, "synthetic"),))
    assert decision.allowed
    assert decision.warn is not None
    assert _PRIVATE_SEGMENT not in decision.warn  # A6.6.
    assert "repos/[REDACTED-PATH-1]/big.md" in decision.warn


# FR4 (v0.4.2) — the masker consumes the detector's own compiled matchers.
_UPPERCASE_HYPHENATED_TERM = "zz-acme"


def test_refusal_path_segment_uppercase_hyphenated_variant_of_term_is_masked(
    repo: PushRepo,
) -> None:
    """Intent: sa-path-segment-judged-by-two-matchers — the masker IS _first_match:
    an upper-cased, hyphenated, ESC-split segment variant of a term is masked (A4.1)."""
    sha = repo.commit(
        {"repos/Zz-A\x1bcme-Corp/notes.md": f"contains {_UPPERCASE_HYPHENATED_TERM} here\n"}
    )
    decision = _decide(
        repo, _branch(sha), denylist_terms=((_UPPERCASE_HYPHENATED_TERM, "synthetic"),)
    )
    assert not decision.allowed
    assert "Zz-A\x1bcme-Corp" not in decision.message
    assert "repos/[REDACTED-PATH-1]/notes.md:1" in decision.message


# A4.2 — a read failure naming a denylisted path is refused with that path masked. The
# stub injects the one failure real git cannot be made to produce on demand (a desynced
# cat-file stream); it answers no git question.
class _FailingObjectSourceWithPath:
    """Simulates a git-read failure that names the offending blob's PATH structurally
    (GitObjectReadError.path, FR4) rather than embedding it in the message string."""

    def remote_branch(self, repo: Path, branch: str) -> bool:
        return True

    def new_objects(self, repo: Path, local_sha: str, remote_sha: str) -> Iterable[ScannedObject]:
        raise GitObjectReadError(
            "git cat-file --batch stream desynchronised resolving prior content",
            path=f"repos/{_PRIVATE_SEGMENT}/leak.md",
        )


def test_git_object_read_failure_at_a_denylisted_path_masks_the_path(repo: PushRepo) -> None:
    sha = repo.commit({"x.md": "x\n"})
    decision = _decide(
        repo, _branch(sha), source=_FailingObjectSourceWithPath(),
        denylist_terms=((_PRIVATE_SEGMENT, "synthetic"),),
    )  # fmt: skip
    assert not decision.allowed
    assert _PRIVATE_SEGMENT not in decision.message
    assert "repos/[REDACTED-PATH-1]/leak.md" in decision.message
    assert "--no-verify" in decision.message
    assert "GitObjectReadError(" not in decision.message


class _Raising:
    def __init__(self, exc: GitObjectReadError) -> None:
        self._exc = exc

    def remote_branch(self, repo: Path, branch: str) -> bool:
        return True

    def new_objects(self, repo: Path, local_sha: str, remote_sha: str) -> Iterable[ScannedObject]:
        raise self._exc


def test_a_corrupt_object_read_names_git_fsck_on_the_repo(repo: PushRepo) -> None:
    """Intent: sa-fix-lines-not-built-by-cli-line#S5 — corruption's fix is `git -C <repo> fsck`."""
    sha = repo.commit({"x.md": "x\n"})
    decision = _decide(
        repo, _branch(sha), source=_Raising(GitObjectReadError("stream desynchronised"))
    )
    assert not decision.allowed
    assert decision.message.splitlines()[-1] == f"fix: git -C {repo.path.as_posix()} fsck"


def test_git_that_cannot_run_gets_no_fsck_fix(repo: PushRepo) -> None:
    """Intent: sa-fix-lines-not-built-by-cli-line#S5 — a timeout or missing git is no corruption."""
    sha = repo.commit({"x.md": "x\n"})
    decision = _decide(repo, _branch(sha), source=_Raising(GitRunError("git timed out")))
    assert not decision.allowed
    assert "fsck" not in decision.message
    assert decision.message.splitlines()[-1] == (
        "fix: Operator action: make git runnable here, then push again"
    )


def test_same_offending_segment_gets_the_same_ordinal_across_hit_and_note(repo: PushRepo) -> None:
    """One masker per decision: the same segment gets the same ordinal everywhere."""
    sha = repo.commit({
        f"repos/{_PRIVATE_SEGMENT}/leak.md": f"{_SYNTHETIC_TERM} here\n",
        f"repos/{_PRIVATE_SEGMENT}/big.md": _BIG,
    })  # fmt: skip
    decision = _decide(repo, _branch(sha), denylist_terms=_BOTH)
    assert not decision.allowed
    assert decision.warn is not None
    assert _PRIVATE_SEGMENT not in decision.message + decision.warn
    assert "repos/[REDACTED-PATH-1]/leak.md" in decision.message
    assert "repos/[REDACTED-PATH-1]/big.md" in decision.warn


# v0.4.3 A11.1 — a term only in a commit message body is refused like a blob.
def test_push_with_denylisted_term_only_in_a_commit_message_body_is_refused(
    repo: PushRepo,
) -> None:
    sha = repo.commit(
        {"clean.md": "clean\n"}, message=f"fixed a bug, mentions {_SYNTHETIC_TERM} here"
    )
    decision = _decide(repo, _branch(sha), denylist_terms=_TERMS)
    assert not decision.allowed
    assert _SYNTHETIC_TERM not in decision.message  # never unmasked
    assert "Uncommit the unpublished range" in decision.message
    assert "--no-verify" in decision.message


# c3 review 5 (C1, H1-H3): the rewrite fix comes from the REFUSED ref's own unpublished
# range — never HEAD, never origin/<integration>, never a ref deletion.
def _refuse(repo: PushRepo, line: str, head: str) -> str:
    decision = _decide(repo, line, fixes=replace(gate_fixes(), head=head), denylist_terms=_TERMS)
    assert not decision.allowed
    assert "update-ref" not in decision.message
    return decision.message


def _two_unpublished(repo: PushRepo) -> tuple[str, str]:
    oldest = repo.commit({"a.md": "clean\n"})
    return oldest, repo.commit({"n.md": f"{_SYNTHETIC_TERM}\n"})


def test_the_rewrite_fix_resets_to_the_oldest_unpublished_commit_and_amends(repo: PushRepo) -> None:
    """N3: reset --soft to the oldest unpublished commit, edit, amend; one fix line."""
    oldest, tip = _two_unpublished(repo)
    message = _refuse(repo, _branch(tip), "feature/0.0.1")
    assert message.endswith(f"fix: git -C /repo reset --soft {oldest}")
    assert "commit --amend" in message and message.count("\nfix: ") == 1


def test_a_refused_branch_that_is_not_checked_out_is_switched_to_first(repo: PushRepo) -> None:
    """H1: HEAD is `main` — resetting HEAD would uncommit the wrong branch."""
    _, tip = _two_unpublished(repo)
    assert _refuse(repo, _branch(tip), "main").endswith("fix: git -C /repo switch feature/0.0.1")


def test_a_tag_gets_operator_action_and_no_command(repo: PushRepo) -> None:
    """N3: a tag has no branch to reset — no command is printed."""
    _, tip = _two_unpublished(repo)
    message = _refuse(repo, _tag(tip, "v0.0.1"), "feature/0.0.1")
    assert "Operator action" in message and "\nfix: " not in message
