"""Table-driven tests for ``core.handoff_index``.

Intent: CONTRACT — release 0.5.1 K6 (one module owns version routing, the self_pull
rule and artifact resolution); sa-json-schema-validated-by-two-engines (jsonschema is the
one engine).

sa-handoff-self-pull-requirement-diverges (0.5.0 WP-46): the schema admits only
handoff-v1.2 (sa-handoff-self-pull-requirement-diverges#46.1) and self_pull is always required
(sa-handoff-self-pull-requirement-diverges#46.2).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from dadaia_workspace.core.exceptions import HandoffSchemaError
from dadaia_workspace.core.handoff_index import Handoff, HandoffIndex

_REPO_ROOT = Path(__file__).resolve().parents[4]
_SCHEMA_PATH = _REPO_ROOT / "dadaia_workspace" / "public" / "schemas" / "handoff-v1.schema.json"
_FIXTURES = Path(__file__).resolve().parents[3] / "fixtures" / "handoffs"
_SCHEMA = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


def _write(path: Path, doc: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    return path


#: The atom every default fixture self-pulls; :func:`_atom` makes it exist under a root.
_REF = "specs/memory/ARCHITECTURE.md"


def _atom(root: Path) -> Path:
    (root / _REF).parent.mkdir(parents=True, exist_ok=True)
    (root / _REF).write_text("# Architecture\n", encoding="utf-8")
    return root


def _base_doc(**overrides: object) -> dict[str, object]:
    doc: dict[str, object] = {
        "schema_version": "handoff-v1.2",
        "self_pull": {"refs": [_REF]},
        "agent": "dd-software-engineer",
        "context": "dadaia-workspace",
        "produced_at": "2026-08-28T12:00:00Z",
        "scope": "table-driven fixture",
        "metrics": {},
        "artifact": {"type": "other"},
    }
    doc.update(overrides)
    return doc


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
    result = handoff.validate(workspace_root=tmp_path, schema=_SCHEMA)
    assert result.valid is False
    assert result.errors[0].field_path == "$root"


# ---------------------------------------------------------------------------
# 3. Version routing — the schema's own ``schema_version`` enum is the router;
#    a future/unknown token is refused explicitly, never silently downgraded
#    (bug reports-sidecar-version-detection-misroutes-future-tokens, fixed at the root:
#    there is no second ad-hoc detector left to misroute it).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("schema_version", "expect_valid"),
    [
        pytest.param("handoff-v1", False, id="v1-refused"),
        pytest.param("handoff-v1.1", False, id="v1.1-refused"),
        pytest.param("handoff-v1.2", True, id="v1.2-valid"),
        pytest.param("handoff-v1.2-with-self-pull", False, id="v1.2-malformed-token-invalid"),
        pytest.param("handoff-v1.3", False, id="future-token-explicitly-refused"),
        pytest.param("handoff-v0.9", False, id="pre-v1-token-refused"),
        pytest.param("", False, id="empty-token-refused"),
    ],
)
def test_schema_version_routing_matrix(
    tmp_path: Path, schema_version: str, expect_valid: bool
) -> None:
    """sa-handoff-self-pull-requirement-diverges#46.1: only handoff-v1.2 is valid."""
    doc = _base_doc(schema_version=schema_version)
    path = _write(tmp_path / "h.handoff.json", doc)
    handoff = Handoff.load(path)

    result = handoff.validate(workspace_root=_atom(tmp_path), schema=_SCHEMA)

    assert result.valid is expect_valid, result.errors
    if not expect_valid:
        assert any("schema_version" in e.field_path for e in result.errors)


def test_v12_requires_self_pull(tmp_path: Path) -> None:
    """sa-handoff-self-pull-requirement-diverges#46.2: a v1.2 without self_pull is
    INVALID, naming the field; sa-json-schema-validated-by-two-engines: the error is
    jsonschema's own."""
    doc = _base_doc()
    del doc["self_pull"]
    result = Handoff.load(_write(tmp_path / "v12.handoff.json", doc)).validate(
        workspace_root=tmp_path, schema=_SCHEMA
    )
    assert result.valid is False
    assert [(e.field_path, e.message) for e in result.errors] == [
        ("$", "'self_pull' is a required property")
    ]


def test_real_fixture_v12_deepening_audit_self_pull_refs_and_hash_pass_schema_shape() -> None:
    """Real fixture: schema-shape + artifact.content_hash pattern are clean (proving the
    validator accepts genuine production output as-is); self_pull existence fails only
    because the fixtures directory is not a real workspace tree — the SAME resolution
    rule exercised end-to-end against real field values, not synthesized ones."""
    path = _FIXTURES / "v1.2-deepening-audit-self-pull.handoff.json"
    handoff = Handoff.load(path)

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

    result = handoff.validate(workspace_root=_atom(tmp_path), schema=_SCHEMA)
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
    """sa-context-repo-mapping-falls-back-to-the-name#B3: refs resolve in the context's
    registered repo — the context NAME (dadaia-workspace) differs from its repo slug."""
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text(
        json.dumps({"contexts": [{"name": "dadaia-workspace", "repo_slug": "alphamain"}]})
    )
    (tmp_path / "repos" / "alphamain" / "specs" / "memory").mkdir(parents=True)
    (tmp_path / "repos" / "alphamain" / "specs" / "memory" / "TECHSTACK.md").write_text("x")

    handoff = Handoff.load(
        _write(
            tmp_path / "h.handoff.json",
            _v12_doc_with_refs(["specs/memory/TECHSTACK.md", "specs/memory/MISSING.md"]),
        )
    )

    result = handoff.validate(workspace_root=tmp_path, schema=_SCHEMA)

    assert result.valid is False
    assert [e.field_path for e in result.errors] == ["self_pull.refs[1]"]
    assert "MISSING.md" in result.errors[0].message


def test_self_pull_resolves_against_reviewed_root_before_workspace(tmp_path: Path) -> None:
    """The open-bug fix (reports-validate-resolves-self-pull-refs-against-the-checked-out-
    branch-not-the-reviewed-tree): a ref present in a linked worktree (``reviewed_root``)
    but absent/different from whatever ``repos/<context>`` currently has checked out on
    disk must resolve — reviewed_root wins."""
    workspace = tmp_path / "workspace"
    (workspace / ".dadaia" / "states").mkdir(parents=True)
    (workspace / ".dadaia" / "states" / "spec_contexts.json").write_text(
        json.dumps({"contexts": [{"name": "dadaia-workspace", "repo_slug": "dadaia-workspace"}]})
    )
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
    (workspace / ".dadaia" / "states").mkdir(parents=True)
    (workspace / ".dadaia" / "states" / "spec_contexts.json").write_text(
        json.dumps({"contexts": [{"name": "dadaia-workspace", "repo_slug": "dadaia-workspace"}]})
    )
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
# 7. HandoffIndex — the workspace-rooted, schema-caching entry the CLI uses
# ---------------------------------------------------------------------------


def test_handoff_index_validate_file_raises_handoff_schema_error_when_unstaged(
    tmp_path: Path,
) -> None:
    index = HandoffIndex(tmp_path)
    handoff_path = _write(tmp_path / ".dadaia" / "handoff" / "ctx" / "h.handoff.json", _base_doc())

    with pytest.raises(HandoffSchemaError):
        index.validate_file(handoff_path)
