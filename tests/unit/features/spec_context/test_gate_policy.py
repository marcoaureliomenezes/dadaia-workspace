"""Current path taxonomy and scope behavior of the SDD gate."""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.core.cli_line import fix_line
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


#: The workspace every gate fix line is built from (T-050-08: absolute, runnable anywhere).
_ROOT = Path("/ws")

# (row_id, ctx_rel_or_root_suffix, expected_class)
_SPEC_RELATIVE_CASES: tuple[tuple[str, str, PathClass], ...] = (
    ("additive_bugs", "specs/bugs/concurrency-warning.md", PathClass.ADDITIVE),
    ("additive_backlog", "specs/backlog/epic.md", PathClass.ADDITIVE),
    ("additive_audits", "specs/audits/2026-01-01T000000Z-abc12345/index.md", PathClass.ADDITIVE),
    ("additive_releases_histo", "specs/releases/_archive/releases_histo.jsonl", PathClass.ADDITIVE),
    ("memory_atom", "specs/memory/architecture.md", PathClass.MUTATING),
    ("memory_product", "specs/memory/product/catalog.md", PathClass.MUTATING),
    ("archived_release", "specs/releases/_archive/v0.1.9/SPEC.md", PathClass.MUTATING),
    ("mutating_release", "specs/releases/v0.1.10/SPEC.md", PathClass.MUTATING),
    ("mutating_constitution", "specs/constitution.md", PathClass.MUTATING),
)

# Workspace-root verdict overrides — none: the three-class taxonomy (0.4.7 FR1) gives a
# root path the SAME verdict as its context-relative twin, with no UNGATED tail.
_ROOT_VERDICT_OVERRIDES: dict[str, PathClass] = {}

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
            # sa-gate-allows-root-entries-the-reaper-moves#E5: root specs/ is not an entry,
            # so no ADDITIVE verdict applies at the root (DELETE-LOSER root-additive_*).
            if row[2] is not PathClass.ADDITIVE
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
            ".dadaia/mcps/server/s.json",
            PathClass.ADDITIVE,
            id="root-dadaia-mcps",
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
        pytest.param("root-path", "README.md", PathClass.MUTATING, id="root-readme-mutating"),
        pytest.param(
            "root-path", "some/loose/path.txt", PathClass.MUTATING, id="root-loose-mutating"
        ),
        # Leading slash stripped; bare repo prefix.
        pytest.param(
            "leading-slash", ("/specs/bugs/x.md", "specs/bugs/x.md"), None, id="leading-slash-equiv"
        ),
        pytest.param(
            "root-path",
            "/repos/foo/specs/bugs/a.md",
            PathClass.ADDITIVE,
            id="leading-slash-in-repo-additive",
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


def test_in_repo_unmatched_is_mutating() -> None:
    """The core invariant: a ctx_rel matching no ADDITIVE prefix is MUTATING."""
    for path in (
        _in_repo(_DEFAULT_SLUG, "specs/constitution.md"),
        _in_repo(_DEFAULT_SLUG, "dadaia_workspace/__init__.py"),
        _in_repo(_NONDEFAULT_SLUG, "specs/some-loose-file.md"),
        _in_repo(_NONDEFAULT_SLUG, "Makefile"),
    ):
        assert classify_path(path) == PathClass.MUTATING, path


def test_first_match_wins_ordering_in_repo() -> None:
    """Ordered classification (FR-P1-05) holds context-relatively: ADDITIVE before MUTATING."""
    assert classify_path(_in_repo(_DEFAULT_SLUG, "specs/bugs/x.md")) == PathClass.ADDITIVE


@pytest.mark.parametrize(
    ("rel_path", "expected_decision", "message_contains"),
    [
        pytest.param(
            "specs/audits/_archive/audits_histo.jsonl",
            Decision.ALLOW,
            None,
            id="allows-append-into-area-histo",
        ),
        pytest.param(
            "specs/releases/_archive/releases_histo.jsonl",
            Decision.ALLOW,
            None,
            id="allows-append-into-releases-histo",
        ),
        pytest.param(
            "specs/bugs/20260701T00Z-00.jsonl",
            Decision.ALLOW,
            None,
            id="allows-write-into-live-bugs",
        ),
    ],
)
def test_evaluate_area_histo_and_live_bugs_allow(
    tmp_path: Path, rel_path: str, expected_decision: Decision, message_contains: str | None
) -> None:
    decision, message = evaluate(rel_path, root=_ROOT)
    assert decision == expected_decision
    if message_contains is not None:
        assert message_contains in message.lower()


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------


# ═════════════════════════════════════════════════════════════════════════════════
# v0.4.5 FR1 (T-045-04), collapsed by 0.4.7 FR3 (T-047-55) — LAW is a static,
# fail-closed floor decided by ORIGIN (the projected AGENTS.md set: the root map and
# the `.dadaia/**` family), never by the basename alone. A repo's own domain-scoped
# AGENTS.md — fresh or existing, referenced by the manifest or not — is never LAW: its
# parent (repos/<slug>/) matches neither shape, so the floor excludes it by construction.
# Bugs: sdd-gate-blocks-fresh-repo-root-agents-md +
# repo-agents-md-law-gate-contradicts-template — one shared root cause: the
# classifier decided by *name*, not by *origin*.
# ═════════════════════════════════════════════════════════════════════════════════


def test_existing_nonmanifest_repo_agents_md_edit_is_allowed(tmp_path: Path) -> None:
    """Intent: CONTRACT — v0.4.5 A1.2.

    An EXISTING repos/<slug>/AGENTS.md that was scaffolded from
    templates/repo-AGENTS.md (never carries the canonical `data/AGENTS.md`
    provenance banner, so `dadaia public install` never re-touches it either) is
    repo-owned, editable content — classifies MUTATING and ALLOWs, same as any other
    repo-domain file. classify_path() is tool-agnostic (Write vs Edit both resolve
    through the same `file_path`), so the classification proof covers both tools.
    """
    slug = "existing-repo-with-scaffolded-agents-md"
    repo_agents_md = tmp_path / "repos" / slug / "AGENTS.md"
    repo_agents_md.parent.mkdir(parents=True)
    repo_agents_md.write_text(
        "# existing-repo-with-scaffolded-agents-md — Repo Rules\n", encoding="utf-8"
    )

    assert classify_path(_in_repo(slug, "AGENTS.md")) == PathClass.MUTATING

    decision, message = evaluate(_in_repo(slug, "AGENTS.md"), root=_ROOT)
    assert decision == Decision.ALLOW
    assert "[GATE]" not in message


# ═════════════════════════════════════════════════════════════════════════════════
# 0.4.7 FR1 — the Bind's SCOPE is the third and last gate block.
# ═════════════════════════════════════════════════════════════════════════════════

_BOUND_A: dict[str, object] = {
    "bound_context": "ctx-a",
    "bound_repos": frozenset({"ctx-a", "ctx-a-infra"}),
}


def _evaluate_scope(tmp_path: Path, rel_path: str, **kwargs: object) -> tuple[Decision, str]:
    return evaluate(rel_path, root=_ROOT, **kwargs)  # type: ignore[arg-type]


def test_write_into_a_repo_outside_the_bind_scope_is_blocked_with_a_runnable_fix(
    tmp_path: Path,
) -> None:
    """AC: bound to A, a write into repos/B/src/x.py is refused and names the bind that
    clears it."""
    decision, message = _evaluate_scope(
        tmp_path, "repos/ctx-b/src/x.py", **_BOUND_A, target_slug="ctx-b", target_owner="ctx-b"
    )
    assert decision == Decision.BLOCK
    assert f"fix: {fix_line(_ROOT, 'context', 'bind', 'ctx-b')}" in message


def test_an_associated_repo_of_the_bound_context_is_in_scope(tmp_path: Path) -> None:
    decision, _ = _evaluate_scope(
        tmp_path,
        "repos/ctx-a-infra/main.tf",
        **_BOUND_A,
        target_slug="ctx-a-infra",
        target_owner="ctx-a",
    )
    assert decision == Decision.ALLOW


def test_an_unbound_session_is_never_scope_blocked(tmp_path: Path) -> None:
    decision, _ = _evaluate_scope(
        tmp_path, "repos/ctx-b/src/x.py", target_slug="ctx-b", target_owner="ctx-b"
    )
    assert decision == Decision.ALLOW


def test_a_slug_no_context_registers_is_never_scope_blocked(tmp_path: Path) -> None:
    """Fail-open: the gate cannot attribute a repo nothing claims."""
    decision, _ = _evaluate_scope(
        tmp_path, "repos/stranger/src/x.py", **_BOUND_A, target_slug="stranger"
    )
    assert decision == Decision.ALLOW


@pytest.mark.parametrize(
    "ctx_rel", ["specs/bugs/BUGS.jsonl", "specs/releases/_archive/releases_histo.jsonl"]
)
def test_an_additive_path_in_a_foreign_repo_stays_writable(tmp_path: Path, ctx_rel: str) -> None:
    """sa-gate-path-classes-diverge-from-the-law#B39-4: any area's `_archive/*_histo.jsonl`
    (and the ledger areas) ALLOW, a foreign repo's included — the bind never scopes them."""
    decision, _ = _evaluate_scope(
        tmp_path,
        f"repos/ctx-b/{ctx_rel}",
        **_BOUND_A,
        target_slug="ctx-b",
        target_owner="ctx-b",
    )
    assert decision == Decision.ALLOW


@pytest.mark.parametrize(
    "rel_path",
    ["specs/memory/ARCHITECTURE.md", "repos/ctx-a/specs/memory/product/catalog.json"],
)
def test_a_memory_write_is_allowed_in_every_phase(tmp_path: Path, rel_path: str) -> None:
    """The MEMORY class is deleted: memory authorship is constitution discipline,
    audited by the drift pillar, never gated (0.4.7 FR1)."""
    decision, _ = _evaluate_scope(
        tmp_path, rel_path, **_BOUND_A, target_slug="ctx-a", target_owner="ctx-a"
    )
    assert decision == Decision.ALLOW


# ═════════════════════════════════════════════════════════════════════════════════
# 0.4.7 FR3 (T-047-55) — one authored law basename. The Claude bridge stub and the
# per-harness DADAIA.md mirrors are deleted, so the PROTECTED law rows collapse to the
# projected AGENTS.md set. A root CLAUDE.md is operator authorship, not law.
# ═════════════════════════════════════════════════════════════════════════════════


def test_root_claude_md_is_no_longer_a_protected_law_path() -> None:
    """Intent: CONTRACT — 0.4.7 AC3.1 (T-047-55).

    Nothing projects a root ``CLAUDE.md`` any more; the gate must not hold a path the
    library never writes. It classifies MUTATING, like any other root file.
    """
    assert classify_path("CLAUDE.md") == PathClass.MUTATING


def test_retired_harness_law_mirrors_are_no_longer_protected() -> None:
    """Intent: CONTRACT — 0.4.7 AC3.1 (T-047-55). A path the install ledger does not
    record (a retired mirror no install writes any more) is MUTATING, whatever its name."""
    for retired in (
        ".codex/AGENTS.md",
        ".kimi-code/AGENTS.md",
        ".agents/AGENTS.md",
        ".claude/rules/AGENTS.md",
    ):
        assert classify_path(retired) == PathClass.MUTATING, retired
