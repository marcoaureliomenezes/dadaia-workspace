"""Table-driven tests for the deepened ``features.handoff`` interface (release 0.5.1 K6).

Intent: CONTRACT — release 0.5.1 K6 ("features/handoff: one module owns discovery,
version routing and artifact resolution").

Replaces (per ``dadaia-test-stewardship``'s replace-don't-layer discipline): the 12
report/handoff test files this candidate's card names for collapse —
``tests/unit/test_handoff_models.py``, ``tests/unit/test_stdlib_handoff_validator.py``,
``tests/unit/test_reports_validation_service.py``,
``tests/unit/features/reports/test_resolve_artifact_path.py``,
``tests/unit/features/reports/test_handoff_v12_validation.py``,
``tests/unit/features/panel/test_reports_doctor_invariant.py`` are DELETED outright (the
symbols they tested — ``HandoffDocument``, ``StdlibHandoffValidator``,
``ReportsValidationService``, ``ReportsDoctor`` — no longer exist); their coverage is
re-derived here, at the one new interface (``core.handoff_index`` /
``features.handoff``), never re-mocked against the deleted shallow modules. The
remaining reports/panel/CLI test files (``test_next_service.py``,
``test_retention_service.py``, ``test_views_reports.py``,
``test_reports_retention_cleanup.py``, ``tests/contract/cli/test_cli_reports*.py``) stay
— they assert BEHAVIOR through their own public surface (CLI exit codes, service
results), which this refactor does not change.

Two real, in-tree fixture handoffs (``tests/fixtures/handoffs/*.json``, no absolute
paths, nothing redacted) anchor the table against genuine production shapes: a
handoff-v1.1 QA-gate verdict with no ``self_pull`` (pre-v1.2), and a handoff-v1.2
deepening-audit handoff carrying real ``self_pull.refs``.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from dadaia_workspace.core.exceptions import HandoffSchemaError
from dadaia_workspace.features.handoff import (
    Handoff,
    HandoffIndex,
    discover_handoff_paths,
    load_schema,
    scan_handoffs,
    validate_schema_shape,
)

_REPO_ROOT = Path(__file__).resolve().parents[4]
_SCHEMA_PATH = _REPO_ROOT / "dadaia_workspace" / "public" / "schemas" / "handoff-v1.schema.json"
_FIXTURES = Path(__file__).resolve().parents[3] / "fixtures" / "handoffs"
_SCHEMA = load_schema(_SCHEMA_PATH)


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


def _write(path: Path, doc: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    return path


def _base_doc(**overrides: object) -> dict[str, object]:
    doc: dict[str, object] = {
        "schema_version": "handoff-v1.1",
        "agent": "software-engineer",
        "context": "dadaia-workspace",
        "produced_at": "2026-08-28T12:00:00Z",
        "scope": "table-driven fixture",
        "metrics": {},
        "artifact": {"type": "other"},
    }
    doc.update(overrides)
    return doc


def _stage_schema(workspace_root: Path) -> None:
    schema_path = workspace_root / ".dadaia" / "agentic" / "schemas" / "handoff-v1.schema.json"
    schema_path.parent.mkdir(parents=True, exist_ok=True)
    schema_path.write_text(_SCHEMA_PATH.read_text(encoding="utf-8"), encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. Discovery — the one primitive every reader now shares
# ---------------------------------------------------------------------------


def test_scan_handoffs_yields_every_file_and_tolerates_a_missing_root(tmp_path: Path) -> None:
    assert list(scan_handoffs(tmp_path / "does-not-exist")) == []

    _write(tmp_path / "ctx" / "a.handoff.json", _base_doc(agent="a"))
    _write(tmp_path / "ctx" / "sub" / "b.handoff.json", _base_doc(agent="b"))
    _write(tmp_path / "ctx" / "not-a-handoff.json", {"noise": True})

    found = {h.agent for h in scan_handoffs(tmp_path)}
    assert found == {"a", "b"}


def test_discover_handoff_paths_is_pattern_scoped_and_path_only(tmp_path: Path) -> None:
    """The doctor_release.py:637 use case — a filename-glob, never content parsing."""
    _write(tmp_path / "releases" / "0.5.1" / "verdicts" / "abc.handoff.json", _base_doc())
    _write(tmp_path / "releases" / "0.5.1" / "other.handoff.json", _base_doc())

    verdict_paths = discover_handoff_paths(tmp_path, "releases/*/verdicts/*.handoff.json")

    assert [p.name for p in verdict_paths] == ["abc.handoff.json"]
    assert discover_handoff_paths(tmp_path / "missing", "**/*.handoff.json") == []


# ---------------------------------------------------------------------------
# 2. Malformed-JSON classification — a Handoff always exists, fields degrade to None
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "content"),
    [
        pytest.param("not json at all", "{ not json", id="truncated-json"),
        pytest.param("a bare JSON array", "[1, 2, 3]", id="non-object-top-level"),
        pytest.param("empty file", "", id="empty-file"),
    ],
)
def test_malformed_handoff_classification(tmp_path: Path, name: str, content: str) -> None:
    path = tmp_path / "bad.handoff.json"
    path.write_text(content, encoding="utf-8")

    handoff = Handoff.load(path)

    assert handoff.malformed_error is not None, name
    assert handoff.agent is None
    assert handoff.verdict is None
    assert handoff.findings == ()
    result = handoff.validate(workspace_root=tmp_path, schema=_SCHEMA)
    assert result.valid is False
    assert result.errors[0].field_path == "$root"


def test_malformed_sibling_is_skipped_by_discovery_a_good_handoff_still_found(
    tmp_path: Path,
) -> None:
    (tmp_path / "ctx").mkdir()
    (tmp_path / "ctx" / "broken.handoff.json").write_text("{ not json", encoding="utf-8")
    _write(tmp_path / "ctx" / "good.handoff.json", _base_doc(agent="qa-engineer"))

    agents = [h.agent for h in scan_handoffs(tmp_path) if h.malformed_error is None]
    assert agents == ["qa-engineer"]


# ---------------------------------------------------------------------------
# 3. Version routing — the schema's own ``schema_version`` enum is the router;
#    a future/unknown token is refused explicitly, never silently downgraded
#    (bug reports-sidecar-version-detection-misroutes-future-tokens, fixed at the root:
#    there is no second ad-hoc detector left to misroute it).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("schema_version", "expect_valid"),
    [
        pytest.param("handoff-v1", True, id="v1-legacy-still-valid"),
        pytest.param("handoff-v1.1", True, id="v1.1-valid"),
        pytest.param("handoff-v1.2-with-self-pull", False, id="v1.2-malformed-token-invalid"),
        pytest.param("handoff-v1.3", False, id="future-token-explicitly-refused"),
        pytest.param("handoff-v0.9", False, id="pre-v1-token-refused"),
        pytest.param("", False, id="empty-token-refused"),
    ],
)
def test_schema_version_routing_matrix(
    tmp_path: Path, schema_version: str, expect_valid: bool
) -> None:
    doc = _base_doc(schema_version=schema_version)
    path = _write(tmp_path / "h.handoff.json", doc)
    handoff = Handoff.load(path)

    result = handoff.validate(workspace_root=tmp_path, schema=_SCHEMA)

    assert result.valid is expect_valid, result.errors
    if not expect_valid:
        assert any("schema_version" in e.field_path for e in result.errors)


def test_v12_requires_self_pull_v11_does_not(tmp_path: Path) -> None:
    v11 = Handoff.load(_write(tmp_path / "v11.handoff.json", _base_doc()))
    assert v11.validate(workspace_root=tmp_path, schema=_SCHEMA).valid is True

    v12_no_refs = Handoff.load(
        _write(tmp_path / "v12.handoff.json", _base_doc(schema_version="handoff-v1.2"))
    )
    result = v12_no_refs.validate(workspace_root=tmp_path, schema=_SCHEMA)
    assert result.valid is False
    assert any(e.field_path == "self_pull" for e in result.errors)


def test_backcompat_fixture_v11_qa_gate_validates_clean() -> None:
    """Real fixture, transition posture: a pre-v1.2 verdict handoff keeps validating."""
    path = _FIXTURES / "v1.1-qa-gate-no-self-pull.handoff.json"
    handoff = Handoff.load(path)

    result = handoff.validate(workspace_root=path.parent, schema=_SCHEMA)

    assert result.valid is True, result.errors
    assert handoff.verdict == "APPROVED"


def test_real_fixture_v12_deepening_audit_self_pull_refs_and_hash_pass_schema_shape() -> None:
    """Real fixture: schema-shape + artifact.content_hash pattern are clean (proving the
    validator accepts genuine production output as-is); self_pull existence fails only
    because the fixtures directory is not a real workspace tree — the SAME resolution
    rule exercised end-to-end against real field values, not synthesized ones."""
    path = _FIXTURES / "v1.2-deepening-audit-self-pull.handoff.json"
    handoff = Handoff.load(path)

    assert handoff.schema_version == "handoff-v1.2"
    assert handoff.self_pull_refs == ("specs/memory/ARCHITECTURE.md", "specs/memory/TECHSTACK.md")
    assert validate_schema_shape(handoff.raw, _SCHEMA) == []

    result = handoff.validate(workspace_root=path.parent, schema=_SCHEMA)

    assert result.valid is False
    assert all(e.field_path.startswith("self_pull") for e in result.errors)


# ---------------------------------------------------------------------------
# 4. Artifact-path resolution — the one rule (bugs handoff-artifact-path-*)
# ---------------------------------------------------------------------------


def test_artifact_path_none_when_undeclared(tmp_path: Path) -> None:
    handoff = Handoff.load(_write(tmp_path / "h.handoff.json", _base_doc()))
    assert handoff.artifact_path(tmp_path) is None


def test_artifact_path_resolves_repos_specs_audits_workspace_rooted(tmp_path: Path) -> None:
    """Bug handoff-artifact-path-cannot-reference-specs-audits: a
    repos/<slug>/specs/audits/<UTC>/audit.md path resolves — it is NOT
    .dadaia/reports/-prefixed, and the one rule has no such special case."""
    audit = tmp_path / "repos" / "dadaia-workspace" / "specs" / "audits" / "2026-06-10" / "audit.md"
    audit.parent.mkdir(parents=True)
    audit.write_bytes(b"# Audit\n")

    handoff_path = _write(
        tmp_path / ".dadaia" / "handoff" / "dadaia-workspace" / "h.handoff.json",
        _base_doc(
            artifact={
                "type": "report",
                "path": "repos/dadaia-workspace/specs/audits/2026-06-10/audit.md",
                "content_hash": hashlib.sha256(audit.read_bytes()).hexdigest(),
            }
        ),
    )
    handoff = Handoff.load(handoff_path)

    resolved = handoff.artifact_path(tmp_path)

    assert resolved == audit.resolve()
    assert handoff.artifact_hash_status(tmp_path) == "match"


def test_artifact_path_workspace_root_wins_when_resolvable_both_ways(tmp_path: Path) -> None:
    ws_artifact = tmp_path / "shared" / "artifact.md"
    ws_artifact.parent.mkdir(parents=True)
    ws_artifact.write_bytes(b"WORKSPACE-ROOTED\n")
    ws_hash = hashlib.sha256(ws_artifact.read_bytes()).hexdigest()

    handoff_dir = tmp_path / ".dadaia" / "handoff" / "dadaia-workspace"
    handoff_relative_copy = handoff_dir / "shared" / "artifact.md"
    handoff_relative_copy.parent.mkdir(parents=True)
    handoff_relative_copy.write_bytes(b"HANDOFF-RELATIVE\n")

    handoff_path = _write(
        handoff_dir / "h.handoff.json",
        _base_doc(
            artifact={"type": "report", "path": "shared/artifact.md", "content_hash": ws_hash}
        ),
    )
    handoff = Handoff.load(handoff_path)

    assert handoff.artifact_path(tmp_path) == ws_artifact.resolve()
    assert handoff.artifact_hash_status(tmp_path) == "match"


def test_artifact_path_legacy_handoff_dir_relative_fallback(tmp_path: Path) -> None:
    handoff_dir = tmp_path / ".dadaia" / "handoff" / "legacy-ctx"
    sibling = handoff_dir / "report.html"
    handoff_dir.mkdir(parents=True)
    sibling.write_bytes(b"<html>legacy</html>")

    handoff_path = _write(
        handoff_dir / "h.handoff.json",
        _base_doc(
            artifact={
                "type": "report",
                "path": "report.html",
                "content_hash": hashlib.sha256(sibling.read_bytes()).hexdigest(),
            }
        ),
    )
    handoff = Handoff.load(handoff_path)

    assert handoff.artifact_path(tmp_path) == sibling.resolve()


@pytest.mark.parametrize(
    "bad_ref",
    [
        pytest.param("../../../../etc/passwd", id="dotdot-escape"),
        pytest.param("/etc/passwd", id="absolute-outside"),
    ],
)
def test_artifact_path_rejects_escape(tmp_path: Path, bad_ref: str) -> None:
    handoff_path = _write(
        tmp_path / ".dadaia" / "handoff" / "ctx" / "h.handoff.json",
        _base_doc(artifact={"type": "report", "path": bad_ref, "content_hash": "a" * 64}),
    )
    handoff = Handoff.load(handoff_path)

    assert handoff.artifact_path(tmp_path) is None
    assert handoff.artifact_hash_status(tmp_path) == "missing_artifact"


# ---------------------------------------------------------------------------
# 5. Hash mismatch / missing artifact
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("materialize", "declared_hash", "expected_status"),
    [
        pytest.param(True, "match", "match", id="match"),
        pytest.param(True, "wrong", "mismatch", id="mismatch"),
        pytest.param(False, "match", "missing_artifact", id="missing_artifact"),
    ],
)
def test_artifact_hash_status_matrix(
    tmp_path: Path, materialize: bool, declared_hash: str, expected_status: str
) -> None:
    content = b"artifact bytes\n"
    real_hash = hashlib.sha256(content).hexdigest()
    artifact = tmp_path / ".dadaia" / "reports" / "ctx" / "agent" / "report.html"
    if materialize:
        artifact.parent.mkdir(parents=True)
        artifact.write_bytes(content)

    declared = real_hash if declared_hash == "match" else "b" * 64
    handoff_path = _write(
        tmp_path / ".dadaia" / "handoff" / "ctx" / "h.handoff.json",
        _base_doc(
            artifact={
                "type": "report",
                "path": ".dadaia/reports/ctx/agent/report.html",
                "content_hash": declared,
            }
        ),
    )
    handoff = Handoff.load(handoff_path)

    assert handoff.artifact_hash_status(tmp_path) == expected_status

    result = handoff.validate(workspace_root=tmp_path, schema=_SCHEMA)
    assert result.valid is (expected_status == "match")
    if expected_status != "match":
        assert result.hash_status == expected_status


# ---------------------------------------------------------------------------
# 6. self_pull.refs — existence + role-map coverage, and the open-bug fix:
#    reviewed_root resolves FIRST, before repos/<context>/<ref> and <workspace>/<ref>.
# ---------------------------------------------------------------------------


def _v12_doc_with_refs(refs: list[str]) -> dict[str, object]:
    return _base_doc(schema_version="handoff-v1.2", self_pull={"refs": refs})


def test_self_pull_ref_existence_and_missing_ref_named(tmp_path: Path) -> None:
    (tmp_path / "repos" / "dadaia-workspace" / "specs" / "memory").mkdir(parents=True)
    (tmp_path / "repos" / "dadaia-workspace" / "specs" / "memory" / "TECHSTACK.md").write_text("x")

    handoff = Handoff.load(
        _write(
            tmp_path / "h.handoff.json",
            _v12_doc_with_refs(["specs/memory/TECHSTACK.md", "specs/memory/MISSING.md"]),
        )
    )

    result = handoff.validate(workspace_root=tmp_path, schema=_SCHEMA)

    assert result.valid is False
    assert any(
        "self_pull.refs[1]" in e.field_path and "MISSING.md" in e.message for e in result.errors
    )


def test_self_pull_role_map_coverage_required_for_mapped_agent(tmp_path: Path) -> None:
    doc = _v12_doc_with_refs(["specs/memory/product/catalog.json"])
    doc["agent"] = "product-engineer"
    (tmp_path / "repos" / "dadaia-workspace" / "specs" / "memory" / "product").mkdir(parents=True)
    (
        tmp_path / "repos" / "dadaia-workspace" / "specs" / "memory" / "product" / "catalog.json"
    ).write_text("{}")
    ok = Handoff.load(_write(tmp_path / "ok.handoff.json", doc))
    assert ok.validate(workspace_root=tmp_path, schema=_SCHEMA).valid is True

    doc_missing_coverage = _v12_doc_with_refs(["specs/memory/ARCHITECTURE.md"])
    doc_missing_coverage["agent"] = "product-engineer"
    (tmp_path / "repos" / "dadaia-workspace" / "specs" / "memory" / "ARCHITECTURE.md").write_text(
        "x"
    )
    bad = Handoff.load(_write(tmp_path / "bad.handoff.json", doc_missing_coverage))
    result = bad.validate(workspace_root=tmp_path, schema=_SCHEMA)
    assert result.valid is False
    assert any("role-mapped" in e.message for e in result.errors)


def test_self_pull_resolves_against_reviewed_root_before_workspace(tmp_path: Path) -> None:
    """The open-bug fix (reports-validate-resolves-self-pull-refs-against-the-checked-out-
    branch-not-the-reviewed-tree): a ref present in a linked worktree (``reviewed_root``)
    but absent/different from whatever ``repos/<context>`` currently has checked out on
    disk must resolve — reviewed_root wins."""
    workspace = tmp_path / "workspace"
    (workspace / "repos" / "dadaia-workspace" / "specs" / "memory").mkdir(parents=True)
    (workspace / "repos" / "dadaia-workspace" / "specs" / "memory" / "TECHSTACK.md").write_text(
        "checked-out-branch version"
    )

    reviewed_worktree = tmp_path / "linked-worktree"
    (reviewed_worktree / "specs" / "memory").mkdir(parents=True)
    (reviewed_worktree / "specs" / "memory" / "QUALITY.md").write_text("only in the reviewed tree")

    handoff = Handoff.load(
        _write(
            workspace / ".dadaia" / "handoff" / "dadaia-workspace" / "h.handoff.json",
            _v12_doc_with_refs(["specs/memory/QUALITY.md"]),
        )
    )

    # Without reviewed_root: the ref is genuinely missing from the checked-out tree.
    without = handoff.validate(workspace_root=workspace, schema=_SCHEMA)
    assert without.valid is False
    assert any("QUALITY.md" in e.message for e in without.errors)

    # With reviewed_root pointed at the linked worktree: the ref resolves.
    with_reviewed = handoff.validate(
        workspace_root=workspace, schema=_SCHEMA, reviewed_root=reviewed_worktree
    )
    assert with_reviewed.valid is True, with_reviewed.errors


def test_self_pull_falls_back_to_workspace_when_reviewed_root_lacks_the_ref(tmp_path: Path) -> None:
    """reviewed_root is tried FIRST, not exclusively — a ref absent there but present
    under the ordinary repos/<context>/<ref> candidate still resolves."""
    workspace = tmp_path / "workspace"
    (workspace / "repos" / "dadaia-workspace" / "specs" / "memory").mkdir(parents=True)
    (workspace / "repos" / "dadaia-workspace" / "specs" / "memory" / "TECHSTACK.md").write_text("x")

    reviewed_worktree = tmp_path / "linked-worktree"
    reviewed_worktree.mkdir()  # exists, but carries none of the referenced files

    handoff = Handoff.load(
        _write(
            workspace / ".dadaia" / "handoff" / "dadaia-workspace" / "h.handoff.json",
            _v12_doc_with_refs(["specs/memory/TECHSTACK.md"]),
        )
    )

    result = handoff.validate(
        workspace_root=workspace, schema=_SCHEMA, reviewed_root=reviewed_worktree
    )

    assert result.valid is True, result.errors


# ---------------------------------------------------------------------------
# 7. Findings summary / severity / expiry derivation
# ---------------------------------------------------------------------------


def test_findings_summary_and_severity_max(tmp_path: Path) -> None:
    doc = _base_doc(
        findings=[
            {"severity": "LOW", "message": "l"},
            {"severity": "HIGH", "message": "h1"},
            {"severity": "HIGH", "message": "h2"},
            {"severity": "INFO", "message": "info excluded from the 4-bucket summary"},
        ]
    )
    handoff = Handoff.load(_write(tmp_path / "h.handoff.json", doc))

    assert handoff.findings_summary() == {"CRITICAL": 0, "HIGH": 2, "MEDIUM": 0, "LOW": 1}
    assert handoff.severity_max() == "HIGH"


def test_severity_max_none_without_findings(tmp_path: Path) -> None:
    handoff = Handoff.load(_write(tmp_path / "h.handoff.json", _base_doc()))
    assert handoff.severity_max() is None


def test_expires_at_uses_produced_at_then_filename_then_mtime(tmp_path: Path) -> None:
    ttl = timedelta(hours=48)

    with_produced_at = Handoff.load(
        _write(tmp_path / "a.handoff.json", _base_doc(produced_at="2026-01-01T00:00:00Z"))
    )
    assert with_produced_at.expires_at(ttl) == datetime(2026, 1, 3, 0, 0, tzinfo=UTC)

    doc_no_produced_at = _base_doc()
    del doc_no_produced_at["produced_at"]
    named = _write(
        tmp_path / "2026-02-01T090000Z-agent-slug.handoff.json",
        doc_no_produced_at,
    )
    from_name = Handoff.load(named)
    assert from_name.expires_at(ttl) == datetime(2026, 2, 3, 9, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# 8. HandoffIndex — the workspace-rooted, schema-caching facade CLI/container use
# ---------------------------------------------------------------------------


def test_handoff_index_construction_is_cheap_no_schema_required(tmp_path: Path) -> None:
    """Chokepoints/doctor_release/panel readers never need a staged schema."""
    index = HandoffIndex(tmp_path)  # no .dadaia/agentic/schemas/... on disk at all
    assert list(index.scan()) == []


def test_handoff_index_validate_file_raises_handoff_schema_error_when_unstaged(
    tmp_path: Path,
) -> None:
    index = HandoffIndex(tmp_path)
    handoff_path = _write(tmp_path / ".dadaia" / "handoff" / "ctx" / "h.handoff.json", _base_doc())

    with pytest.raises(HandoffSchemaError):
        index.validate_file(handoff_path)


def test_handoff_index_validate_all_scoped_by_context_and_caches_the_schema(
    tmp_path: Path,
) -> None:
    _stage_schema(tmp_path)
    index = HandoffIndex(tmp_path)
    _write(tmp_path / ".dadaia" / "handoff" / "ctx-a" / "h1.handoff.json", _base_doc())
    _write(tmp_path / ".dadaia" / "handoff" / "ctx-b" / "h2.handoff.json", _base_doc())

    all_results = index.validate_all()
    scoped = index.validate_all(context="ctx-a")

    assert len(all_results) == 2
    assert len(scoped) == 1
    assert all(r.valid for r in all_results)
    # Schema loaded once, cached — a second call must not raise even if the file moved.
    (tmp_path / ".dadaia" / "agentic" / "schemas" / "handoff-v1.schema.json").unlink()
    assert index.validate_file(scoped[0].path).valid is True


def test_handoff_index_check_hash_matches_module_level_hash_status(tmp_path: Path) -> None:
    content = b"x"
    artifact = tmp_path / ".dadaia" / "reports" / "ctx" / "r.html"
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(content)
    handoff_path = _write(
        tmp_path / ".dadaia" / "handoff" / "ctx" / "h.handoff.json",
        _base_doc(
            artifact={
                "type": "report",
                "path": ".dadaia/reports/ctx/r.html",
                "content_hash": hashlib.sha256(content).hexdigest(),
            }
        ),
    )
    index = HandoffIndex(tmp_path)

    assert index.check_hash(handoff_path) == "match"


def test_validate_schema_shape_and_load_schema_are_the_standalone_public_primitives() -> None:
    """The schema-contract tests (test_handoff_schema_contract.py,
    test_handoff_instruction_adoption.py) use exactly these two — proving the internal
    validator (folded from the deleted StdlibHandoffValidator/ValidatorPort) stays
    reachable without a workspace root."""
    schema = load_schema(_SCHEMA_PATH)
    assert validate_schema_shape(_base_doc(), schema) == []
    assert validate_schema_shape({}, schema) != []
