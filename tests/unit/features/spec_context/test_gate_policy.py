"""Current path taxonomy and advisory-presence behavior of the SDD gate."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

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


# ═════════════════════════════════════════════════════════════════════════════════
# v0.4.3 T-043-17/FR13 — the MEMORY path class covers dotfiles, by decision.
#
# Size: SMALL — pure classify_path/evaluate calls, tmp_path-scoped. Intent: SENTINEL —
# v0.4.3 A13.2 (memory-dotfile phase-gate parity). The software-architect ruling
# (handoff 2026-08-17T161500Z-software-architect-v0.4.3-fr13-fr14, HIGH finding #1) is
# ZERO-behavioral-change by design: gate_policy.py's bare-prefix match at
# ``_MEMORY_PREFIX``/``classify_path`` ALREADY classifies every path under
# ``specs/memory/`` — dotfiles included — as MEMORY; no carve-out exists and none is
# added (see the module docstring and the ``_MEMORY_PREFIX`` comment for the stated
# rule this ruling ratifies). These fixtures PIN that decision against future
# regression — they are not fixing a defect, they are formalizing doctrine that
# already held in code.
# ═════════════════════════════════════════════════════════════════════════════════

_MEMORY_DOTFILE_PATHS: tuple[str, ...] = (
    "specs/memory/.heading-allowlist",
    f"repos/{_DEFAULT_SLUG}/specs/memory/.heading-allowlist",
)
#: A non-dot sibling atom, in BOTH root and in-repo form, pinned for parity (the
#: ruling's fixture requirement) — same MEMORY class, same phase gate, no distinction.
_MEMORY_SIBLING_ATOM_PATHS: tuple[str, ...] = (
    "specs/memory/architecture.md",
    f"repos/{_DEFAULT_SLUG}/specs/memory/architecture.md",
)
_MEMORY_PHASES_ALLOWED: tuple[str, ...] = ("DEFINITION", "CLOSURE")
_MEMORY_PHASES_BLOCKED: tuple[str, ...] = (
    "IMPLEMENTATION",
    "DISCOVERY",
    "SPEC",
    "PLAN",
    "TASKS",
    "ARCHIVED",
)


@pytest.mark.parametrize("rel_path", _MEMORY_DOTFILE_PATHS)
def test_memory_dotfile_classifies_as_memory(rel_path: str) -> None:
    """A13.2: both the root and in-repo dotfile form classify MEMORY — no dotfile
    carve-out, bare-prefix match by decision."""
    assert classify_path(rel_path) == PathClass.MEMORY


@pytest.mark.parametrize("rel_path", _MEMORY_DOTFILE_PATHS)
@pytest.mark.parametrize("phase", _MEMORY_PHASES_ALLOWED)
def test_memory_dotfile_evaluate_allows_in_definition_and_closure(
    tmp_path: Path, rel_path: str, phase: str
) -> None:
    decision, _ = evaluate(
        tmp_path,
        rel_path,
        ctx="dadaia-workspace",
        phase=phase,
        session_id="sess-fr13",
        release="v0.4.3",
        mode="IMPLEMENTATION",
    )
    assert decision == Decision.ALLOW


@pytest.mark.parametrize("rel_path", _MEMORY_DOTFILE_PATHS)
@pytest.mark.parametrize("phase", _MEMORY_PHASES_BLOCKED)
def test_memory_dotfile_evaluate_blocks_rule_a_outside_definition_and_closure(
    tmp_path: Path, rel_path: str, phase: str
) -> None:
    """A13.2: IMPLEMENTATION and every other non-DEFINITION/CLOSURE phase — including
    the doctrine question the ruling's finding 1(b) answers ('no SPEC override of the
    phase rule', RULE A keeps blocking unconditionally by phase) — BLOCK [RULE A]."""
    decision, message = evaluate(
        tmp_path,
        rel_path,
        ctx="dadaia-workspace",
        phase=phase,
        session_id="sess-fr13",
        release="v0.4.3",
        mode="IMPLEMENTATION",
    )
    assert decision == Decision.BLOCK
    assert "[RULE A]" in message


def test_memory_dotfile_evaluate_matches_a_non_dot_sibling_atom_across_every_phase(
    tmp_path: Path,
) -> None:
    """A13.2 parity fixture: the dotfile and a normal (non-dot) sibling atom, root and
    in-repo, get an IDENTICAL decision at every phase in this matrix — no special-
    casing distinguishes a dotfile from an ordinary memory atom."""
    for dotfile, sibling in zip(_MEMORY_DOTFILE_PATHS, _MEMORY_SIBLING_ATOM_PATHS, strict=True):
        assert classify_path(dotfile) == classify_path(sibling)
        for phase in (*_MEMORY_PHASES_ALLOWED, *_MEMORY_PHASES_BLOCKED):
            dot_decision, _ = evaluate(
                tmp_path,
                dotfile,
                ctx="dadaia-workspace",
                phase=phase,
                session_id="sess-fr13-dot",
                release="v0.4.3",
                mode="IMPLEMENTATION",
            )
            sibling_decision, _ = evaluate(
                tmp_path,
                sibling,
                ctx="dadaia-workspace",
                phase=phase,
                session_id="sess-fr13-sibling",
                release="v0.4.3",
                mode="IMPLEMENTATION",
            )
            assert dot_decision == sibling_decision, (
                f"phase={phase}: dotfile and sibling atom must get the SAME decision"
            )


# ═════════════════════════════════════════════════════════════════════════════════
# v0.4.5 FR1 (T-045-04) — LAW is a static, fail-closed floor decided by ORIGIN
# (workspace root + LAW_HARNESS_DIRS), never by the basename alone. A repo's own
# domain-scoped AGENTS.md/CLAUDE.md — fresh or existing, referenced by the manifest
# or not — is never LAW: its parent (repos/<slug>/) never matches a harness dir, and
# it is never a bare root basename, so the static floor excludes it by construction.
# Bugs: sdd-gate-blocks-fresh-repo-root-agents-md +
# repo-agents-md-law-gate-contradicts-template — one shared root cause: the
# classifier decided by *name*, not by *origin*.
# ═════════════════════════════════════════════════════════════════════════════════


def test_fresh_repo_agents_md_classifies_mutating_not_law() -> None:
    """Intent: CONTRACT — v0.4.5 A1.1.

    A brand-new repo with no prior projection, no manifest entry, nothing on disk
    yet: repos/<fresh-slug>/AGENTS.md must classify MUTATING, never LAW. Before the
    fix this asserted PathClass.LAW and failed (the false positive
    `sdd-gate-blocks-fresh-repo-root-agents-md` reports).
    """
    fresh_slug = "brand-new-repo-never-scaffolded-yet"
    assert classify_path(_in_repo(fresh_slug, "AGENTS.md")) == PathClass.MUTATING
    assert classify_path(_in_repo(fresh_slug, "CLAUDE.md")) == PathClass.MUTATING


def test_fresh_repo_agents_md_write_is_allowed_on_the_executed_path(tmp_path: Path) -> None:
    """Intent: CONTRACT — v0.4.5 A1.1 (evaluate()/Write envelope, not just classify_path)."""
    fresh_slug = "brand-new-repo-never-scaffolded-yet"
    decision, message = evaluate(
        tmp_path,
        _in_repo(fresh_slug, "AGENTS.md"),
        ctx=fresh_slug,
        phase="IMPLEMENTATION",
        session_id="anon-session",
        release="none",
        mode="IMPLEMENTATION",
    )
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

    decision, message = evaluate(
        tmp_path,
        _in_repo(slug, "AGENTS.md"),
        ctx=slug,
        phase="IMPLEMENTATION",
        session_id="anon-session",
        release="none",
        mode="IMPLEMENTATION",
    )
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
    "data/DADAIA.md": ("DADAIA.md", ".codex/DADAIA.md", ".kimi-code/DADAIA.md"),
    "kimi-code/AGENTS.md": (".kimi-code/AGENTS.md",),
}

#: A fixture manifest — mirrors .dadaia/agentic/manifest.json's real shape
#: (assets: [{path, sha256, type}]) but is NEVER loaded from the operator's live
#: workspace file (A1.3 explicitly forbids that dependency).
_FIXTURE_MANIFEST: dict[str, object] = {
    "package_version": "0.0.0-test",
    "schema_version": 1,
    "assets": [
        {"path": "agents/software-engineer.md", "sha256": "a" * 64, "type": "agents"},
        {"path": "data/AGENTS.md", "sha256": "b" * 64, "type": "data"},
        {"path": "data/DADAIA.md", "sha256": "c" * 64, "type": "data"},
        {"path": "kimi-code/AGENTS.md", "sha256": "d" * 64, "type": "kimi-code"},
        {"path": "templates/repo-AGENTS.md", "sha256": "e" * 64, "type": "templates"},
    ],
}


def test_manifest_tracked_law_projections_stay_law() -> None:
    """Intent: CONTRACT — v0.4.5 A1.3.

    Enumerates the fixture manifest (never the operator's live file) and pins that
    every LAW-basename asset's installed TARGET still classifies LAW after the fix.
    The static floor (workspace root + LAW_HARNESS_DIRS) already covers every
    lib-originated law projection this release's manifest ships — the additive
    manifest arm has nothing left to extend today, and nothing regresses.
    """
    law_assets = [
        asset
        for asset in _FIXTURE_MANIFEST["assets"]  # type: ignore[union-attr]
        if Path(asset["path"]).name in LAW_BASENAMES
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
            assert classify_path(target) == PathClass.LAW, target
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
        "CLAUDE.md",
        "DADAIA.md",
        ".codex/AGENTS.md",
        ".codex/DADAIA.md",
        ".kimi-code/AGENTS.md",
        ".kimi-code/DADAIA.md",
        ".agents/AGENTS.md",
        ".claude/rules/AGENTS.md",
    )
    for floor_path in floor_paths:
        assert classify_path(floor_path) == PathClass.LAW, floor_path

    manifest_path.unlink()
    assert not manifest_path.exists()
    for floor_path in floor_paths:
        assert classify_path(floor_path) == PathClass.LAW, floor_path
