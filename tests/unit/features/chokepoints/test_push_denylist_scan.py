"""Wiring the push-range denylist scan into ``push_gate_decision`` (SPEC v0.9.0 FR1/FR2/FR5/FR6).

Intent: CONTRACT — v0.9.0 A1.1, A1.2, A1.3, A1.4, A2.1, A2.2, A2.3, A2.4, A5.1, A5.2,
A5.3, A5.4, A6.1; v0.11.0 A7.1, A7.2, A7.3

Drives ``push_gate_decision`` with an injected fake :class:`GitObjectReader` — no real
git, no filesystem (FR7/A7.2). Only synthetic terms/slugs ever appear here (TASKS
standing rule): ``zz-``-prefixed values, never a real operator term or foreign slug.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from dadaia_workspace.core.protocols.git_object_reader import GitObjectReadError, ScannedObject
from dadaia_workspace.features.chokepoints import push_gate_decision
from dadaia_workspace.features.chokepoints.service import PushRef, parse_push_refs

_SHA_A = "a" * 40
_SHA_B = "b" * 40
_ZERO = "0" * 40
_SYNTHETIC_TERM = "zz-secret-term"


@dataclass
class _FakeObjectSource:
    """Maps an exact ``(local_sha, remote_sha)`` pair to a fixed object list."""

    by_range: dict[tuple[str, str], list[ScannedObject]] = field(default_factory=dict)
    calls: list[tuple[str, str]] = field(default_factory=list)

    def new_objects(self, repo: Path, local_sha: str, remote_sha: str) -> Iterable[ScannedObject]:
        self.calls.append((local_sha, remote_sha))
        return self.by_range.get((local_sha, remote_sha), [])


class _FailingObjectSource:
    def new_objects(self, repo: Path, local_sha: str, remote_sha: str) -> Iterable[ScannedObject]:
        raise GitObjectReadError("simulated git rev-list failure")


def _refs(*lines: str) -> list[PushRef]:
    return parse_push_refs("\n".join(lines))


def _obj(path: str, text: str, *, sha: str = "cafef00d") -> ScannedObject:
    return ScannedObject(path=path, sha=sha, text=text, decodable=True)


# ---------------------------------------------------------------------------
# A1.1 — a branch ref whose range carries a denylist term is refused.
# ---------------------------------------------------------------------------


def test_branch_push_with_denylisted_blob_in_range_is_refused(tmp_path: Path) -> None:
    source = _FakeObjectSource(
        by_range={
            (_SHA_A, _ZERO): [_obj("leak.md", f"contains {_SYNTHETIC_TERM} here\n")],
        }
    )
    decision = push_gate_decision(
        tmp_path,
        _refs(f"refs/heads/develop {_SHA_A} refs/heads/develop {_ZERO}"),
        object_source=source,
        repo=tmp_path,
        denylist_terms=((_SYNTHETIC_TERM, "synthetic"),),
    )
    assert not decision.allowed
    assert _SYNTHETIC_TERM not in decision.message  # A5.2: never unmasked.


# ---------------------------------------------------------------------------
# A1.2 — a term reachable only from remote_sha (excluded from the range) never refuses.
# ---------------------------------------------------------------------------


def test_term_outside_the_range_does_not_refuse(tmp_path: Path) -> None:
    """The fake never surfaces an object for this (local, remote) pair — mirroring an
    object that is reachable only from ``remote_sha`` and therefore out of range."""
    from dadaia_workspace.features.chokepoints.service import iter_security_approvals

    assert iter_security_approvals(tmp_path) == []  # sanity: no verdict on disk either.

    source = _FakeObjectSource(by_range={})
    decision = push_gate_decision(
        tmp_path,
        _refs(f"refs/tags/v9.9.9 {_SHA_A} refs/tags/v9.9.9 {_ZERO}"),
        object_source=source,
        repo=tmp_path,
        denylist_terms=((_SYNTHETIC_TERM, "synthetic"),),
    )
    assert decision.allowed


# ---------------------------------------------------------------------------
# A1.3 / A2.3 — a deletion ref is never scanned (and never verdict-checked).
# ---------------------------------------------------------------------------


def test_deletion_ref_is_never_scanned(tmp_path: Path) -> None:
    source = _FakeObjectSource()
    decision = push_gate_decision(
        tmp_path,
        _refs(f"refs/heads/old {_ZERO} refs/heads/old {_SHA_A}"),
        object_source=source,
        repo=tmp_path,
        denylist_terms=((_SYNTHETIC_TERM, "synthetic"),),
    )
    assert decision.allowed
    assert source.calls == []


# ---------------------------------------------------------------------------
# A1.4 — a blob reachable from two refs in the same push is deduped (one Hit, not two).
# ---------------------------------------------------------------------------


def test_shared_blob_across_two_refs_is_deduped(tmp_path: Path) -> None:
    shared = _obj("shared.md", f"{_SYNTHETIC_TERM} shows up\n", sha="shared-sha")
    source = _FakeObjectSource(
        by_range={
            (_SHA_A, _ZERO): [shared],
            (_SHA_B, _ZERO): [shared],
        }
    )
    decision = push_gate_decision(
        tmp_path,
        _refs(
            f"refs/tags/v1 {_SHA_A} refs/tags/v1 {_ZERO}",
            f"refs/tags/v2 {_SHA_B} refs/tags/v2 {_ZERO}",
        ),
        object_source=source,
        repo=tmp_path,
        denylist_terms=((_SYNTHETIC_TERM, "synthetic"),),
    )
    assert not decision.allowed
    assert decision.message.count("shared-sha"[:12]) == 1


# ---------------------------------------------------------------------------
# A2.1 — a tainted tag push is refused.
# ---------------------------------------------------------------------------


def test_tainted_tag_push_is_refused(tmp_path: Path) -> None:
    source = _FakeObjectSource(
        by_range={(_SHA_A, _ZERO): [_obj("tag-blob.md", f"{_SYNTHETIC_TERM}\n")]}
    )
    decision = push_gate_decision(
        tmp_path,
        _refs(f"refs/tags/v1 {_SHA_A} refs/tags/v1 {_ZERO}"),
        object_source=source,
        repo=tmp_path,
        denylist_terms=((_SYNTHETIC_TERM, "synthetic"),),
    )
    assert not decision.allowed


# ---------------------------------------------------------------------------
# A2.2 — a clean tag push is allowed with NO security-verdict lookup (DP-5 intact).
# ---------------------------------------------------------------------------


def test_clean_tag_push_is_allowed_with_no_verdict_required(tmp_path: Path) -> None:
    source = _FakeObjectSource(by_range={(_SHA_A, _ZERO): [_obj("clean.md", "nothing here\n")]})
    decision = push_gate_decision(
        tmp_path,
        _refs(f"refs/tags/v1 {_SHA_A} refs/tags/v1 {_ZERO}"),
        object_source=source,
        repo=tmp_path,
        denylist_terms=((_SYNTHETIC_TERM, "synthetic"),),
    )
    assert decision.allowed  # no handoff file exists anywhere under tmp_path.


# ---------------------------------------------------------------------------
# A2.4 — branch policy still runs BEFORE the scan (a bad branch name never
# triggers a scan call); for a tag ref the scan is the only policy that runs.
# ---------------------------------------------------------------------------


def test_branch_policy_refusal_precedes_the_scan(tmp_path: Path) -> None:
    source = _FailingObjectSource()  # would raise if ever called.
    decision = push_gate_decision(
        tmp_path,
        _refs(f"refs/heads/main {_SHA_A} refs/heads/main {_ZERO}"),
        object_source=source,
        repo=tmp_path,
    )
    assert not decision.allowed
    assert "main" in decision.message


# ---------------------------------------------------------------------------
# A5.1 / A5.3 / A5.4 — the refusal message shape: ref, path:line, short sha, masked
# term + source layer, the law, edit+rewrite-before-push remediation, 10-item cap.
# ---------------------------------------------------------------------------


def test_refusal_message_shape_and_ten_item_cap(tmp_path: Path) -> None:
    objects = [
        _obj(f"file{i}.md", f"{_SYNTHETIC_TERM} number {i}\n", sha=f"{i:040x}") for i in range(12)
    ]
    source = _FakeObjectSource(by_range={(_SHA_A, _ZERO): objects})
    decision = push_gate_decision(
        tmp_path,
        _refs(f"refs/heads/develop {_SHA_A} refs/heads/develop {_ZERO}"),
        object_source=source,
        repo=tmp_path,
        denylist_terms=((_SYNTHETIC_TERM, "synthetic"),),
    )
    assert not decision.allowed
    message = decision.message
    assert "refs/heads/develop" in message
    assert "file0.md:1" in message
    assert "z…m" in message  # masked form of the synthetic term.
    assert "operator denylist" in message
    assert "DADAIA.md §7" in message
    assert "--amend" in message or "rebase" in message
    assert "already-published history never needs a rewrite" in message
    assert "2 more" in message or "and 2" in message  # 12 hits, 10 shown, 2 remainder.
    assert _SYNTHETIC_TERM not in message


# ---------------------------------------------------------------------------
# A6.1 — a simulated git failure refuses, naming the failure + --no-verify.
# ---------------------------------------------------------------------------


def test_git_object_read_failure_refuses_naming_the_failure(tmp_path: Path) -> None:
    decision = push_gate_decision(
        tmp_path,
        _refs(f"refs/heads/develop {_SHA_A} refs/heads/develop {_ZERO}"),
        object_source=_FailingObjectSource(),
        repo=tmp_path,
    )
    assert not decision.allowed
    assert "simulated git rev-list failure" in decision.message
    assert "--no-verify" in decision.message


# ---------------------------------------------------------------------------
# FR7/A7.1 — an option-shaped `local_sha` refuses as a malformed line instead of
# silently producing a successful empty rev-list.
# ---------------------------------------------------------------------------


def test_option_shaped_local_sha_glob_form_is_malformed() -> None:
    from dadaia_workspace.features.chokepoints.service import parse_push_stdin

    refs, malformed = parse_push_stdin(
        f"refs/heads/develop --glob=refs/nonexistent refs/heads/develop {_ZERO}\n"
    )
    assert refs == []
    assert malformed == 1


def test_option_shaped_local_sha_branches_form_is_malformed() -> None:
    from dadaia_workspace.features.chokepoints.service import parse_push_stdin

    refs, malformed = parse_push_stdin(
        f"refs/heads/develop --branches=zzz refs/heads/develop {_ZERO}\n"
    )
    assert refs == []
    assert malformed == 1


def test_option_shaped_remote_sha_is_also_malformed() -> None:
    """The same option-shaped hardening applies symmetrically to ``remote_sha``."""
    from dadaia_workspace.features.chokepoints.service import parse_push_stdin

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
    from dadaia_workspace.features.chokepoints.service import parse_push_stdin

    refs, malformed = parse_push_stdin(f"refs/heads/old {_ZERO} refs/heads/old {_SHA_A}\n")
    assert malformed == 0
    assert len(refs) == 1
    assert refs[0].is_deletion


# ---------------------------------------------------------------------------
# FR7/A7.3 — a 64-char (SHA-256) sha parses; a 39- or 41-char hex string does not.
# ---------------------------------------------------------------------------


def test_sha256_length_local_sha_parses() -> None:
    from dadaia_workspace.features.chokepoints.service import parse_push_stdin

    sha256 = "f" * 64
    refs, malformed = parse_push_stdin(f"refs/heads/develop {sha256} refs/heads/develop {_ZERO}\n")
    assert malformed == 0
    assert len(refs) == 1
    assert refs[0].local_sha == sha256


def test_39_and_41_char_hex_shas_are_malformed() -> None:
    from dadaia_workspace.features.chokepoints.service import parse_push_stdin

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
