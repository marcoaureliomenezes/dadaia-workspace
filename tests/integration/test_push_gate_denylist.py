"""Push-range denylist scan over a REAL throwaway git repo (SPEC v0.9.0 FR4/FR6;
SPEC v0.11.0 FR1/FR2/FR5).

Intent: CONTRACT — v0.9.0 A4.2, A6.1; v0.11.0 A1.6, A2.3, A10.2, A5.1, A5.2, A5.4

Exercises the real ``GitSubprocessObjectReader`` adapter (real ``git`` subprocess) wired
into ``push_gate_decision`` — no CLI layer, so this stays a fast, direct integration
proof of the FROZEN<->scan invariant (FR4), the fail-closed git-failure boundary
(FR6 row 2), and — since v0.11.0 — the FR1 amnesty over a real range with a real
remote. The FR5 registry-derived foreign-name tests below DO cross into the CLI/
container layer (``container.load_registry_context_identities``,
``cli.commands.ci._foreign_repo_slugs``) — the only way to exercise the real registry
seam over a real fixture registry file, per this task's declared write set. Only
synthetic terms ever appear here (TASKS standing rule).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from dadaia_workspace import container
from dadaia_workspace.cli.commands import ci
from dadaia_workspace.core.protocols.git_object_reader import GitObjectReadError
from dadaia_workspace.features.chokepoints import push_gate_decision
from dadaia_workspace.features.chokepoints.service import PushRef
from dadaia_workspace.infrastructure.git_objects import GitSubprocessObjectReader

_SYNTHETIC_TERM = "zz-frozen-invariant-term"
_ZERO = "0" * 40


def _write_registry(workspace: Path, contexts: list[dict]) -> None:
    states = workspace / ".dadaia" / "states"
    states.mkdir(parents=True, exist_ok=True)
    (states / "spec_contexts.json").write_text(
        json.dumps({"schema_version": "2", "contexts": contexts})
    )


def _registry_ctx_row(name: str, *, repo_slug: str | None = None, state: str = "dead") -> dict:
    return {
        "name": name,
        "state": state,
        "repo_slug": repo_slug or name,
        "repo_url": f"https://example.com/{repo_slug or name}.git",
        "created_at": "2026-01-01T00:00:00Z",
        "alive_since": "2026-01-01T00:00:00Z" if state == "alive" else None,
        "dead_since": "2026-05-01T00:00:00Z" if state == "dead" else None,
        "current_branch": None,
    }


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
    return PushRef(
        local_ref="refs/tags/v1",
        local_sha=local_sha,
        remote_ref="refs/tags/v1",
        remote_sha=remote_sha,
    )


def test_git_mv_into_archive_produces_no_new_blob_and_a_clean_scan(tmp_path: Path) -> None:
    """FR4/A4.2: renaming a tainted file into ``specs/_archive/`` reuses the same blob
    object — the range carries no NEW blob, so the scan is clean by construction."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "notes.md").write_text(f"leftover {_SYNTHETIC_TERM} content\n")
    # Simulates a push already reachable at the remote — the FROZEN↔scan invariant only
    # holds relative to a real range boundary; `remote_sha` anchors it (FR1 row 1).
    already_published_sha = _commit(repo, "already-published")

    (repo / "specs" / "_archive").mkdir(parents=True)
    _git(["mv", "notes.md", "specs/_archive/notes.md"], repo)
    renamed_sha = _commit(repo, "archive: git mv the tainted file")

    reader = GitSubprocessObjectReader()
    decision = push_gate_decision(
        [_tag_push_ref(renamed_sha, remote_sha=already_published_sha)],
        object_source=reader,
        repo=repo,
        denylist_terms=((_SYNTHETIC_TERM, "synthetic"),),
    )
    assert decision.allowed, decision.message


def test_editing_a_path_that_already_published_the_value_no_longer_refuses(
    tmp_path: Path,
) -> None:
    """SPEC v0.11.0 FR1/A1.1 (supersedes the v0.9.0-era assumption pinned by the OLD
    version of this test, ``test_editing_the_same_content_produces_a_new_blob_and_a_
    refusal``): editing the SAME path that already published the matched value at the
    resolvable base no longer refuses, over a REAL range with a REAL remote — the
    amnesty derives from published git state, not from narrowing the FR4 whole-blob
    matching ruler (which this release explicitly does not touch, SPEC §4.2)."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "notes.md").write_text(f"leftover {_SYNTHETIC_TERM} content\n")
    already_published_sha = _commit(repo, "already-published")

    (repo / "notes.md").write_text(f"leftover {_SYNTHETIC_TERM} content, plus more\n")
    edited_sha = _commit(repo, "edit the file in place, keeping the same term")

    reader = GitSubprocessObjectReader()
    decision = push_gate_decision(
        [_tag_push_ref(edited_sha, remote_sha=already_published_sha)],
        object_source=reader,
        repo=repo,
        denylist_terms=((_SYNTHETIC_TERM, "synthetic"),),
    )
    assert decision.allowed, decision.message


def test_editing_a_tests_fixture_that_already_published_the_literal_no_longer_refuses(
    tmp_path: Path,
) -> None:
    """SPEC v0.11.0 A1.6 (the literal ``tests/**`` scope this criterion names): editing
    a file UNDER ``tests/**`` that already carried a pre-existing fixture literal at the
    base no longer refuses the push — the exact real-world class this release exists to
    fix (SPEC §1 "The blocking problem")."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "tests").mkdir()
    (repo / "tests" / "fixture.py").write_text(f"SAMPLE = {_SYNTHETIC_TERM!r}\n")
    already_published_sha = _commit(repo, "already-published")

    (repo / "tests" / "fixture.py").write_text(
        f"SAMPLE = {_SYNTHETIC_TERM!r}\nEXTRA = 'a genuinely unrelated addition'\n"
    )
    edited_sha = _commit(repo, "edit the tests fixture, keeping the same literal")

    reader = GitSubprocessObjectReader()
    decision = push_gate_decision(
        [_tag_push_ref(edited_sha, remote_sha=already_published_sha)],
        object_source=reader,
        repo=repo,
        denylist_terms=((_SYNTHETIC_TERM, "synthetic"),),
    )
    assert decision.allowed, decision.message


def test_same_value_introduced_into_a_new_path_still_refuses(tmp_path: Path) -> None:
    """SPEC v0.11.0 A1.2 (integration tier): the amnesty is bound to the PATH, not the
    value — the same value copied into a path that never published it before is a new
    publication and still refuses, over a real range with a real remote."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "tests").mkdir()
    (repo / "tests" / "fixture.py").write_text(f"SAMPLE = {_SYNTHETIC_TERM!r}\n")
    already_published_sha = _commit(repo, "already-published")

    (repo / "tests" / "new_fixture.py").write_text(f"COPY = {_SYNTHETIC_TERM!r}\n")
    tip_sha = _commit(repo, "copy the term into a brand-new path")

    reader = GitSubprocessObjectReader()
    decision = push_gate_decision(
        [_tag_push_ref(tip_sha, remote_sha=already_published_sha)],
        object_source=reader,
        repo=repo,
        denylist_terms=((_SYNTHETIC_TERM, "synthetic"),),
    )
    assert not decision.allowed
    assert _SYNTHETIC_TERM not in decision.message


# ---------------------------------------------------------------------------
# bug new-branch-push-loses-prior-published-denylist-amnesty (v0.4.4) — the FIRST
# push of a `feature/{M.m.p}` branch (gitflow v2's only pushable ref, DADAIA.md §4)
# is a NEW remote ref: git's own pre-push line reports `remote_sha` as the all-zero
# sentinel. Every fixture above configures NO remote at all, so it never exercised
# "a real origin already published this branch's own past" — exactly the gap that
# let a new-branch push of already-published content be refused as if it were
# novel. These fixtures configure a REAL bare `origin` and fetch it, then push a
# genuine `refs/heads/feature/M.m.p` branch line (the bug's own repro shape), not a
# tag.
# ---------------------------------------------------------------------------


def _publish_to_bare_origin(repo: Path, tmp_path: Path, *, branch: str = "develop") -> None:
    remote = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--bare", str(remote)], capture_output=True, check=True)
    _git(["remote", "add", "origin", str(remote)], repo)
    _git(["push", "origin", f"HEAD:refs/heads/{branch}"], repo)
    _git(["fetch", "origin"], repo)


def _feature_push_ref(local_sha: str, *, branch: str = "feature/1.0.0") -> PushRef:
    return PushRef(
        local_ref=f"refs/heads/{branch}",
        local_sha=local_sha,
        remote_ref=f"refs/heads/{branch}",
        remote_sha=_ZERO,
    )


def test_new_branch_push_of_an_already_published_term_passes(tmp_path: Path) -> None:
    """(a) The first push of a brand-new `feature/M.m.p` branch (`remote_sha` is the
    all-zero sentinel) that only carries a term ALREADY published on `origin` must
    pass — DADAIA.md §7's range scope: already-published history never needs a
    rewrite, regardless of whether THIS ref existed on origin before."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "notes.md").write_text(f"already published: {_SYNTHETIC_TERM}\n")
    _commit(repo, "publish")
    _publish_to_bare_origin(repo, tmp_path)

    _git(["checkout", "-b", "feature/1.0.0"], repo)
    (repo / "notes.md").write_text(
        f"already published: {_SYNTHETIC_TERM}\nplus a genuinely new, unrelated line\n"
    )
    tip_sha = _commit(repo, "append an unrelated line")

    reader = GitSubprocessObjectReader()
    decision = push_gate_decision(
        [_feature_push_ref(tip_sha)],
        object_source=reader,
        repo=repo,
        denylist_terms=((_SYNTHETIC_TERM, "synthetic"),),
    )
    assert decision.allowed, decision.message


def test_new_branch_push_of_a_novel_term_still_refuses(tmp_path: Path) -> None:
    """(b) Negative twin: a brand-new `feature/M.m.p` branch introducing a term never
    published anywhere on `origin` is still refused — the amnesty stays scoped to
    what is genuinely already published."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "notes.md").write_text("unrelated\n")
    _commit(repo, "publish")
    _publish_to_bare_origin(repo, tmp_path)

    _git(["checkout", "-b", "feature/1.0.0"], repo)
    (repo / "notes.md").write_text(f"unrelated\nintroducing {_SYNTHETIC_TERM} for the first time\n")
    tip_sha = _commit(repo, "introduce a novel term")

    reader = GitSubprocessObjectReader()
    decision = push_gate_decision(
        [_feature_push_ref(tip_sha)],
        object_source=reader,
        repo=repo,
        denylist_terms=((_SYNTHETIC_TERM, "synthetic"),),
    )
    assert not decision.allowed
    assert _SYNTHETIC_TERM not in decision.message


def test_prior_side_lookup_failure_refuses_naming_the_failure_and_no_verify(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SPEC v0.11.0 A2.3 (integration tier — unit tier already pinned in
    ``tests/unit/infrastructure/test_git_object_reader.py``): a forced git failure on
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

    reader = GitSubprocessObjectReader()
    decision = push_gate_decision(
        [_tag_push_ref(tip_sha, remote_sha=already_published_sha)],
        object_source=reader,
        repo=repo,
    )

    assert not decision.allowed
    assert "prior content" in decision.message
    assert "--no-verify" in decision.message


# ---------------------------------------------------------------------------
# FR5/A5.1-A5.4 (v0.11.0, entry #22) — the registry-derived foreign-name layer, over a
# REAL registry fixture file and the REAL container/CLI seam functions.
# ---------------------------------------------------------------------------


def test_dead_registry_context_name_and_slug_both_refuse_a_push_introducing_them(
    tmp_path: Path,
) -> None:
    """SPEC v0.11.0 A5.1: a DEAD registry context's name AND its repo_slug both refuse
    a push that introduces them in new content — the registry-derived layer protects a
    context whose repo directory is absent, which the v0.9.0 directory-derived-only
    set silently forgot."""
    workspace = tmp_path / "workspace"
    repo = workspace / "repos" / "pushing-repo"
    _init_repo(repo)
    (repo / "notes.md").write_text("first\n")
    tip_sha = _commit(repo, "c1")

    dead_name = "zz-dead-context-name"
    dead_slug = "zz-dead-context-slug"
    _write_registry(
        workspace,
        [
            _registry_ctx_row("pushing-repo", state="alive"),
            _registry_ctx_row(dead_name, repo_slug=dead_slug, state="dead"),
        ],
    )

    registry_result = container.load_registry_context_identities(workspace)
    assert registry_result.degraded is False
    foreign_slugs = ci._foreign_repo_slugs(workspace, "pushing-repo", registry_result.identities)
    assert dead_name in foreign_slugs
    assert dead_slug in foreign_slugs
    assert "pushing-repo" not in foreign_slugs

    reader = GitSubprocessObjectReader()

    (repo / "notes.md").write_text(f"mentions {dead_name} now\n")
    name_sha = _commit(repo, "introduce the dead context's name")
    name_decision = push_gate_decision(
        [_tag_push_ref(name_sha, remote_sha=tip_sha)],
        object_source=reader,
        repo=repo,
        foreign_slugs=foreign_slugs,
    )
    assert not name_decision.allowed
    assert dead_name not in name_decision.message

    (repo / "notes.md").write_text(f"mentions {dead_slug} now\n")
    slug_sha = _commit(repo, "introduce the dead context's slug")
    slug_decision = push_gate_decision(
        [_tag_push_ref(slug_sha, remote_sha=name_sha)],
        object_source=reader,
        repo=repo,
        foreign_slugs=foreign_slugs,
    )
    assert not slug_decision.allowed
    assert dead_slug not in slug_decision.message


def test_own_context_with_differing_name_and_slug_never_contributes_either_identity(
    tmp_path: Path,
) -> None:
    """SPEC v0.11.0 A5.2: when the PUSHING repo's own registry entry has a ``name``
    that differs from its ``repo_slug``, NEITHER identity is contributed as a foreign
    term — subtracting only the slug would re-open the A3.2 regression (the pushed
    repo blocking every push of itself) through the new door the registry name opens."""
    workspace = tmp_path / "workspace"
    (workspace / "repos" / "own-repo-slug").mkdir(parents=True)
    _write_registry(
        workspace,
        [_registry_ctx_row("own-context-name", repo_slug="own-repo-slug", state="alive")],
    )

    registry_result = container.load_registry_context_identities(workspace)
    assert registry_result.degraded is False
    foreign_slugs = ci._foreign_repo_slugs(workspace, "own-repo-slug", registry_result.identities)

    assert "own-context-name" not in foreign_slugs
    assert "own-repo-slug" not in foreign_slugs


def test_missing_registry_yields_empty_and_never_crashes(tmp_path: Path) -> None:
    """SPEC v0.11.0 A5.4 (missing case): no registry file at all yields an empty
    result — the push hook never dies on registry state. SPEC v0.4.2 A8.3: a missing
    registry is a LEGITIMATE absence, not a degradation — `degraded` stays False (only
    a genuinely malformed/unreadable registry sets it)."""
    workspace = tmp_path / "workspace-with-no-dadaia-dir"
    result = container.load_registry_context_identities(workspace)
    assert result.identities == ()
    assert result.degraded is False


def test_empty_registry_yields_empty_and_never_crashes(tmp_path: Path) -> None:
    """SPEC v0.11.0 A5.4 (empty case). SPEC v0.4.2 A8.3: an empty registry is not a
    degradation either."""
    workspace = tmp_path / "workspace"
    _write_registry(workspace, [])
    result = container.load_registry_context_identities(workspace)
    assert result.identities == ()
    assert result.degraded is False


def test_malformed_registry_yields_empty_and_never_crashes(tmp_path: Path) -> None:
    """SPEC v0.11.0 A5.4 (malformed case): invalid JSON never raises — it degrades to
    the empty result, and the widened foreign-slug set falls back to the
    directory-derived-only set. SPEC v0.4.2 FR8(2)/A8.3: this IS a degradation —
    `degraded` is True, unlike the missing/empty cases above — so the caller
    (cli/commands/ci.py#push_gate_check) can surface exactly one stderr note naming it
    (pinned at the CLI tier by
    tests/contract/test_push_gate_wiring.py::test_malformed_registry_produces_exactly_one_stderr_note)."""
    workspace = tmp_path / "workspace"
    states = workspace / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text("{not-json")

    result = container.load_registry_context_identities(workspace)
    assert result.identities == ()
    assert result.degraded is True

    (workspace / "repos" / "own-slug").mkdir(parents=True)
    (workspace / "repos" / "sibling-dir").mkdir(parents=True)
    foreign_slugs = ci._foreign_repo_slugs(workspace, "own-slug", result.identities)
    assert foreign_slugs == ["sibling-dir"]


def test_real_git_failure_refuses_naming_the_failure(tmp_path: Path) -> None:
    """FR6 row 2, integration-tier: a genuinely non-git directory wired through the
    REAL adapter refuses, never silently allows an unscannable push."""
    not_a_repo = tmp_path / "not-a-repo"
    not_a_repo.mkdir()
    reader = GitSubprocessObjectReader()

    decision = push_gate_decision(
        [_tag_push_ref("a" * 40)],
        object_source=reader,
        repo=not_a_repo,
    )

    assert not decision.allowed
    assert "--no-verify" in decision.message


def test_git_object_read_error_is_importable_from_core_protocols() -> None:
    """Sentinel-level sanity: the typed failure the adapter raises stays importable
    from `core.protocols` without pulling in infrastructure (purity boundary)."""
    assert issubclass(GitObjectReadError, Exception)
