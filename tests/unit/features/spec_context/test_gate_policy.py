"""Current path taxonomy and advisory-presence behavior of the SDD gate."""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.spec_context.gate_policy import (
    Decision,
    PathClass,
    classify_path,
    evaluate,
)

# The default (self-hosting) context slug and a non-default consumer slug. The class of a
# path must depend only on its context-relative remainder, never on which slug it is.
_DEFAULT_SLUG = "dadaia-workspace"
_NONDEFAULT_SLUG = "sample-engine"


def _in_repo(slug: str, ctx_rel: str) -> str:
    return f"repos/{slug}/{ctx_rel}"


# (row_id, ctx_rel_or_root_suffix, expected_class)
_SPEC_RELATIVE_CASES: tuple[tuple[str, str, PathClass], ...] = (
    ("additive_bugs", "specs/bugs/concurrency-warning.md", PathClass.ADDITIVE),
    ("additive_backlog", "specs/backlog/epic.md", PathClass.ADDITIVE),
    ("additive_audits", "specs/audits/2026-01-01T000000Z-abc12345/index.md", PathClass.ADDITIVE),
    ("memory_atom", "specs/memory/architecture.md", PathClass.MEMORY),
    ("memory_product", "specs/memory/product/catalog.md", PathClass.MEMORY),
    ("frozen_archive", "specs/_archive/releases/v0.1.9/SPEC.md", PathClass.FROZEN),
    ("mutating_release", "specs/releases/v0.1.10/SPEC.md", PathClass.MUTATING),
    ("mutating_constitution", "specs/constitution.md", PathClass.MUTATING),
)

# Workspace-root verdict for each spec-relative suffix (UNGATED where no root rule matches).
_ROOT_VERDICT_OVERRIDES: dict[str, PathClass] = {
    "mutating_constitution": PathClass.UNGATED,
}

# In-repo production source — the canonical no-class-match ⇒ MUTATING case (FR-R1-04).
_IN_REPO_PRODUCTION_CASES: tuple[tuple[str, str], ...] = (
    ("library_source", "dadaia_workspace/features/spec_context/gate_policy.py"),
    ("consumer_src", "src/engine/run.py"),
    ("repo_pyproject", "pyproject.toml"),
    ("repo_readme", "README.md"),
    ("repo_tests", "tests/unit/test_x.py"),
)


@pytest.mark.parametrize(
    ("case", "path_or_row", "expected"),
    [
        # Root classification for every spec-relative case.
        *[
            pytest.param(
                "root-path",
                row[1],
                _ROOT_VERDICT_OVERRIDES.get(row[0], row[2]),
                id=f"root-{row[0]}",
            )
            for row in _SPEC_RELATIVE_CASES
        ],
        # In-repo classification for every spec-relative case, both slugs.
        *[
            pytest.param("in-repo", (row, slug), row[2], id=f"in-repo-{row[0]}-{slug}")
            for row in _SPEC_RELATIVE_CASES
            for slug in (_DEFAULT_SLUG, _NONDEFAULT_SLUG)
        ],
        # In-repo production source ⇒ MUTATING, both slugs.
        *[
            pytest.param(
                "in-repo-production",
                (row, slug),
                PathClass.MUTATING,
                id=f"in-repo-prod-{row[0]}-{slug}",
            )
            for row in _IN_REPO_PRODUCTION_CASES
            for slug in (_DEFAULT_SLUG, _NONDEFAULT_SLUG)
        ],
        # Workspace-root .dadaia/ ADDITIVE prefixes preserved (FR-R1-05).
        pytest.param(
            "root-path",
            ".dadaia/reports/ctx/agent/r.html",
            PathClass.ADDITIVE,
            id="root-dadaia-reports",
        ),
        pytest.param(
            "root-path", ".dadaia/handoff/ctx/h.json", PathClass.ADDITIVE, id="root-dadaia-handoff"
        ),
        pytest.param(
            "root-path", ".dadaia/tmp/agent/x.txt", PathClass.ADDITIVE, id="root-dadaia-tmp"
        ),
        # PROTECTED (fail-closed) + UNGATED fall-through preserved at root.
        pytest.param(
            "root-path",
            ".dadaia/sessions/runtime/ctx.ptr",
            PathClass.PROTECTED,
            id="root-protected",
        ),
        pytest.param("root-path", "README.md", PathClass.UNGATED, id="root-readme-ungated"),
        pytest.param(
            "root-path", "some/loose/path.txt", PathClass.UNGATED, id="root-loose-ungated"
        ),
        # Leading slash stripped; bare repo prefix.
        pytest.param(
            "leading-slash", ("/specs/bugs/x.md", "specs/bugs/x.md"), None, id="leading-slash-equiv"
        ),
        pytest.param(
            "root-path",
            "/repos/foo/specs/memory/a.md",
            PathClass.MEMORY,
            id="leading-slash-in-repo-memory",
        ),
        pytest.param("root-path", "repos/foo", PathClass.MUTATING, id="bare-repo-no-remainder"),
        pytest.param("root-path", "repos/foo/", PathClass.MUTATING, id="bare-repo-trailing-slash"),
    ],
)
def test_classification_matrix(case: str, path_or_row, expected) -> None:  # type: ignore[no-untyped-def]
    if case == "root-path":
        assert classify_path(path_or_row) == expected
    elif case == "in-repo":
        row, slug = path_or_row
        _row_id, ctx_rel, _cls = row
        assert classify_path(_in_repo(slug, ctx_rel)) == expected
    elif case == "in-repo-production":
        row, slug = path_or_row
        _row_id, ctx_rel = row
        assert classify_path(_in_repo(slug, ctx_rel)) == expected
    elif case == "leading-slash":
        with_slash, without_slash = path_or_row
        assert classify_path(with_slash) == classify_path(without_slash)


def test_in_repo_unmatched_never_ungated() -> None:
    """The core invariant: a ctx_rel matching no class NEVER falls through to UNGATED."""
    for path in (
        _in_repo(_DEFAULT_SLUG, "specs/constitution.md"),
        _in_repo(_DEFAULT_SLUG, "dadaia_workspace/__init__.py"),
        _in_repo(_NONDEFAULT_SLUG, "specs/some-loose-file.md"),
        _in_repo(_NONDEFAULT_SLUG, "Makefile"),
    ):
        assert classify_path(path) != PathClass.UNGATED, path
        assert classify_path(path) == PathClass.MUTATING, path


def test_first_match_wins_ordering_in_repo() -> None:
    """Ordered classification (FR-P1-05) holds context-relatively: ADDITIVE before MUTATING."""
    assert classify_path(_in_repo(_DEFAULT_SLUG, "specs/bugs/x.md")) == PathClass.ADDITIVE


# ---------------------------------------------------------------------------
# v0.1.46 AC-4 / R-2 — per-artifact _archive/ subdirs classify FROZEN, matched BEFORE
# the ADDITIVE prefixes (the ordering bug the release fixes) — CRITICAL boundary.
# ---------------------------------------------------------------------------


def test_archive_prefix_boundary_and_ordering() -> None:
    """Only ``_archive/`` (trailing slash) is FROZEN — a ``_archive``-prefixed sibling
    like ``_archivefoo.jsonl`` stays ADDITIVE, and _archive/ is matched BEFORE the
    ADDITIVE prefix (a live sibling in the same family stays ADDITIVE)."""
    for rel_path in (
        "specs/backlog/_archive/epic.md",
        "specs/audits/_archive/2026-01-01T000000Z-abc12345/audit.md",
        "specs/bugs/_archive/concurrency-warning.md",
    ):
        assert classify_path(rel_path) == PathClass.FROZEN

    # Live siblings in the same family stay ADDITIVE — the fix must not overreach.
    assert classify_path("specs/bugs/20260701T00Z-00.jsonl") == PathClass.ADDITIVE
    assert classify_path("specs/backlog/candidates.md") == PathClass.ADDITIVE
    assert classify_path("specs/audits/live-report/audit.md") == PathClass.ADDITIVE
    assert classify_path("specs/bugs/_archive/20260101T00Z-00.jsonl") == PathClass.FROZEN

    # Boundary: only the trailing-slash form is FROZEN.
    assert classify_path("specs/bugs/_archivefoo.jsonl") == PathClass.ADDITIVE
    assert classify_path("specs/backlog/_archived.md") == PathClass.ADDITIVE
    assert classify_path("specs/bugs/_archive") == PathClass.ADDITIVE

    # Holds context-relatively, both slugs.
    for slug in (_DEFAULT_SLUG, _NONDEFAULT_SLUG):
        assert (
            classify_path(_in_repo(slug, "specs/audits/_archive/2026-01-01T00Z-abc/audit.md"))
            == PathClass.FROZEN
        )
        assert (
            classify_path(_in_repo(slug, "specs/audits/2026-01-01T00Z-abc/audit.md"))
            == PathClass.ADDITIVE
        )


# ---------------------------------------------------------------------------
# evaluate() block/allow pair — the archive is really blocked, a live additive write flows
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("rel_path", "expected_decision", "message_contains"),
    [
        pytest.param(
            "specs/audits/_archive/2026-01-01T00Z-abc/audit.md",
            Decision.BLOCK,
            "frozen archive",
            id="blocks-write-into-archive",
        ),
        pytest.param(
            "specs/bugs/20260701T00Z-00.jsonl",
            Decision.ALLOW,
            None,
            id="allows-write-into-live-bugs",
        ),
    ],
)
def test_evaluate_archive_block_and_additive_allow(
    tmp_path: Path, rel_path: str, expected_decision: Decision, message_contains: str | None
) -> None:
    decision, message = evaluate(
        tmp_path,
        rel_path,
        ctx="dadaia-workspace",
        phase="IMPLEMENTATION",
        session_id="sess-1",
        release="v0.1.46",
        mode="IMPLEMENTATION",
    )
    assert decision == expected_decision
    if message_contains is not None:
        assert message_contains in message.lower()


# ---------------------------------------------------------------------------
# Advisory presence is caller-owned state and never blocks.
# ---------------------------------------------------------------------------


def test_evaluate_mutating_write_upserts_presence(tmp_path: Path) -> None:
    decision, _ = evaluate(
        tmp_path,
        "repos/dadaia-workspace/specs/releases/v0.1.46/TASKS.md",
        ctx="dadaia-workspace",
        phase="IMPLEMENTATION",
        session_id="sess-solo",
        release="v0.1.46",
        mode="IMPLEMENTATION",
        runtime="claude",
        pid=1234,
    )
    assert decision == Decision.ALLOW
    record = tmp_path / ".dadaia" / "states" / "presence" / "dadaia-workspace" / "sess-solo.json"
    assert record.is_file()


def test_evaluate_peer_presence_warns_but_allows(tmp_path: Path) -> None:
    from dadaia_workspace.features.spec_context import presence

    presence.upsert(tmp_path, "dadaia-workspace", "owner-A", runtime="claude", pid=1)

    decision, message = evaluate(
        tmp_path,
        "repos/dadaia-workspace/specs/releases/v0.1.46/PLAN.md",
        ctx="dadaia-workspace",
        phase="IMPLEMENTATION",
        session_id="intruder",
        release="v0.1.46",
        mode="IMPLEMENTATION",
        runtime="codex",
        pid=5678,
    )
    assert decision == Decision.ALLOW
    assert "owner-A" in message


def test_evaluate_anon_session_emits_no_presence_events(tmp_path: Path) -> None:
    decision, _ = evaluate(
        tmp_path,
        "repos/dadaia-workspace/specs/releases/v0.1.46/TASKS.md",
        ctx="dadaia-workspace",
        phase="IMPLEMENTATION",
        session_id="anon-session",
        release="v0.1.46",
        mode="IMPLEMENTATION",
    )
    assert decision == Decision.ALLOW
    presence_dir = tmp_path / ".dadaia" / "states" / "presence" / "dadaia-workspace"
    assert not presence_dir.exists()
