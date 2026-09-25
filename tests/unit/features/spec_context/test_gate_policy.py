"""Current path taxonomy and scope behavior of the SDD gate."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.core.cli_line import fix_line
from dadaia_workspace.core.workspace_layout import LAW_BASENAMES
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


def test_fresh_repo_agents_md_classifies_mutating_not_law() -> None:
    """Intent: CONTRACT — v0.4.5 A1.1.

    A brand-new repo with no prior projection, no manifest entry, nothing on disk
    yet: repos/<fresh-slug>/AGENTS.md must classify MUTATING, never LAW. Before the
    fix this asserted PathClass.PROTECTED and failed (the false positive
    `sdd-gate-blocks-fresh-repo-root-agents-md` reports).
    """
    fresh_slug = "brand-new-repo-never-scaffolded-yet"
    assert classify_path(_in_repo(fresh_slug, "AGENTS.md")) == PathClass.MUTATING


def test_fresh_repo_agents_md_write_is_allowed_on_the_executed_path(tmp_path: Path) -> None:
    """Intent: CONTRACT — v0.4.5 A1.1 (evaluate()/Write envelope, not just classify_path)."""
    fresh_slug = "brand-new-repo-never-scaffolded-yet"
    decision, message = evaluate(_in_repo(fresh_slug, "AGENTS.md"), root=_ROOT)
    assert decision == Decision.ALLOW
    assert "[GATE]" not in message


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


# Known source -> installed TARGET mapping for every LAW-basename asset the real
# .dadaia/agentic/manifest.json ships today (v0.4.5 A1.3 fixture — this table is
# derived from infrastructure/workspace_guardrail.py + install_helpers.py's actual
# projection targets, NEVER from reading the operator's live manifest file).
# `templates/repo-AGENTS.md` is deliberately absent from this table: its installed
# target (repos/<slug>/AGENTS.md) is a provenance-gated CONSUMER projection (FOREIGN
# once it carries repo-specific content — see workspace_guardrail._write_consumer_agents),
# never a floor path; A1.1/A1.2 above pin it MUTATING.
_LAW_ASSET_TARGETS: dict[str, tuple[str, ...]] = {
    "data/AGENTS.md": ("AGENTS.md",),
    "data/dadaia-AGENTS.md": (".dadaia/AGENTS.md",),
}

#: A fixture manifest — mirrors .dadaia/agentic/manifest.json's real shape
#: (assets: [{path, sha256, type}]) but is NEVER loaded from the operator's live
#: workspace file (A1.3 explicitly forbids that dependency).
_FIXTURE_MANIFEST: dict[str, object] = {
    "package_version": "0.0.0-test",
    "schema_version": 1,
    "assets": [
        {"path": "agents/dd-software-engineer.md", "sha256": "a" * 64, "type": "agents"},
        {"path": "data/AGENTS.md", "sha256": "b" * 64, "type": "data"},
        {"path": "data/dadaia-AGENTS.md", "sha256": "d" * 64, "type": "data"},
        {"path": "templates/repo-AGENTS.md", "sha256": "e" * 64, "type": "templates"},
    ],
}


def test_manifest_tracked_law_projections_stay_law() -> None:
    """Intent: CONTRACT — v0.4.5 A1.3.

    Enumerates the fixture manifest (never the operator's live file) and pins that
    every LAW-basename asset's installed TARGET still classifies LAW after the fix.
    The static floor (the projected AGENTS.md set) already covers every
    lib-originated law projection this release's manifest ships — the additive
    manifest arm has nothing left to extend today, and nothing regresses.
    """
    law_assets = [
        asset
        for asset in _FIXTURE_MANIFEST["assets"]  # type: ignore[union-attr]
        if Path(asset["path"]).name.endswith("AGENTS.md")
    ]
    assert law_assets, "fixture manifest must carry at least one LAW-basename asset"
    checked_any = False
    for asset in law_assets:
        targets = _LAW_ASSET_TARGETS.get(asset["path"])
        if targets is None:
            # repo-scoped template projections (e.g. templates/repo-AGENTS.md) are
            # asserted MUTATING by A1.1/A1.2 above, never LAW.
            continue
        for target in targets:
            assert classify_path(target) == PathClass.PROTECTED, target
            checked_any = True
    assert checked_any, "fixture manifest carried no known floor-mapped LAW asset"


def test_manifest_removal_never_demotes_a_statically_floored_law_path(tmp_path: Path) -> None:
    """Intent: CONTRACT — v0.4.5 A1.7 (security, CWE-284).

    classify_path() takes only a path string — no workspace/manifest argument — and
    performs zero I/O, so the static floor can never be demoted by editing or
    deleting .dadaia/agentic/manifest.json: the floor never reads it. Prove the
    attack directly — write a manifest with every LAW asset stripped, then delete it
    outright — and confirm every statically-floored path is LAW regardless.
    """
    manifest_dir = tmp_path / ".dadaia" / "agentic"
    manifest_dir.mkdir(parents=True)
    manifest_path = manifest_dir / "manifest.json"
    stripped_manifest = {"assets": [], "package_version": "0.0.0", "schema_version": 1}
    manifest_path.write_text(json.dumps(stripped_manifest), encoding="utf-8")

    floor_paths = (
        "AGENTS.md",
        ".dadaia/AGENTS.md",
        ".dadaia/handoff/AGENTS.md",
        ".dadaia/tmp/AGENTS.md",
        ".dadaia/states/AGENTS.md",
    )
    for floor_path in floor_paths:
        assert classify_path(floor_path) == PathClass.PROTECTED, floor_path

    manifest_path.unlink()
    assert not manifest_path.exists()
    for floor_path in floor_paths:
        assert classify_path(floor_path) == PathClass.PROTECTED, floor_path


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


def test_an_additive_path_in_a_foreign_repo_stays_writable(tmp_path: Path) -> None:
    decision, _ = _evaluate_scope(
        tmp_path,
        "repos/ctx-b/specs/bugs/BUGS.jsonl",
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
    assert frozenset({"AGENTS.md"}) == LAW_BASENAMES
    assert classify_path("CLAUDE.md") == PathClass.MUTATING


def test_retired_harness_law_mirrors_are_no_longer_protected() -> None:
    """Intent: CONTRACT — 0.4.7 AC3.1 (T-047-55).

    The harness-dir law row died with the files it guarded: no ``.codex/DADAIA.md``,
    no ``.kimi-code/`` tree, no ``.claude/rules/AGENTS.md`` projection.
    """
    for retired in (
        ".codex/AGENTS.md",
        ".kimi-code/AGENTS.md",
        ".agents/AGENTS.md",
        ".claude/rules/AGENTS.md",
    ):
        assert classify_path(retired) == PathClass.MUTATING, retired


def test_the_projected_agents_md_set_stays_protected() -> None:
    """Intent: CONTRACT — 0.4.7 FR3 (T-047-55). The root map and every ``.dadaia/**``
    scoped AGENTS.md the installer projects stay human-only."""
    for projected in (
        "AGENTS.md",
        ".dadaia/AGENTS.md",
        ".dadaia/handoff/AGENTS.md",
        ".dadaia/tmp/AGENTS.md",
        ".dadaia/states/AGENTS.md",
    ):
        assert classify_path(projected) == PathClass.PROTECTED, projected
