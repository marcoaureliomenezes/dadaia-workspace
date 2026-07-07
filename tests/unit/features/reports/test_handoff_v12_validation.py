"""handoff-v1.2 validation tests (v0.1.62 W1 — T-62-10 / T-62-11).

T-62-10 (AC-1) — back-compat corpus lock, written and committed BEFORE any
schema/service edit (golden-first): every in-tree v1/v1.1 handoff fixture plus
the two `dadaia-handoff-emitter` SKILL.md examples (transcribed verbatim below,
with `content_hash` recomputed against a materialized artifact — the literal
hash in the skill's report-mode example is illustrative) must pass
``ReportsValidationService.validate_file`` against the REAL public schema, and
must KEEP passing after the FR1/FR2 v1.2 bump (transition posture proven, not
asserted).

Corpus provenance (the tree carries no committed ``*.handoff.json`` files —
the in-tree corpus is the fixture documents embedded in tests + the skill):

* ``v1-minimal-report``      — ``tests/contract/cli/test_cli_reports.py#_make_valid_handoff``
* ``v1-no-artifact-path``    — ``tests/unit/test_reports_validation_service.py`` no-path variant
* ``v1.1-contract-full``     — ``tests/contract/test_handoff_schema_contract.py#_valid_handoff``
* ``v1.1-skill-handoff-only``— SKILL.md "Example — handoff-only (the default)"
* ``v1.1-skill-with-report`` — SKILL.md "Example — with HTML report"

Hash posture mirrors the existing reports tests: report-mode fixtures
materialize the artifact file and carry its real sha256; handoff-only fixtures
omit ``artifact.path`` so the hash check is skipped (``hash_status is None``).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from pathlib import Path

import pytest

from dadaia_workspace.features.reports.validation import ReportsValidationService
from dadaia_workspace.infrastructure.stdlib_handoff_validator import StdlibHandoffValidator

_REPO_ROOT = Path(__file__).resolve().parents[4]
_SCHEMA_PATH = _REPO_ROOT / "dadaia_workspace" / "public" / "schemas" / "handoff-v1.schema.json"


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


def _service(workspace: Path) -> ReportsValidationService:
    """Real StdlibHandoffValidator + real public schema, workspace-rooted at *workspace*."""
    handoff_root = workspace / ".dadaia" / "handoff"
    handoff_root.mkdir(parents=True, exist_ok=True)
    return ReportsValidationService(
        validator=StdlibHandoffValidator(_SCHEMA_PATH), reports_root=handoff_root
    )


def _materialize_artifact(workspace: Path, rel: str, content: bytes) -> str:
    """Create the artifact file under *workspace* and return its sha256 hex digest."""
    artifact = workspace / rel
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_bytes(content)
    return hashlib.sha256(content).hexdigest()


def _write_handoff(workspace: Path, doc: dict[str, object], stem: str) -> Path:
    path = workspace / ".dadaia" / "handoff" / "dadaia-workspace" / f"{stem}.handoff.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Corpus fixture builders (each returns the doc; artifacts are materialized)
# ---------------------------------------------------------------------------


def _corpus_v1_minimal_report(workspace: Path) -> dict[str, object]:
    """v1 fixture from tests/contract/cli/test_cli_reports.py#_make_valid_handoff."""
    rel = ".dadaia/reports/dadaia-workspace/software-engineer/report.html"
    content_hash = _materialize_artifact(workspace, rel, b"<html>report</html>")
    return {
        "schema_version": "handoff-v1",
        "agent": "software-engineer",
        "context": "dadaia-workspace",
        "produced_at": "2026-05-17T00:00:00Z",
        "scope": "dadaia-workspace/test",
        "metrics": {},
        "findings": [],
        "artifact": {"type": "report", "path": rel, "content_hash": content_hash},
    }


def _corpus_v1_no_artifact_path(workspace: Path) -> dict[str, object]:
    """v1 handoff-only variant (no artifact.path — hash check skipped, as today)."""
    return {
        "schema_version": "handoff-v1",
        "agent": "software-engineer",
        "context": "dadaia-workspace",
        "produced_at": "2026-05-16T23:29:05Z",
        "scope": "dadaia-workspace/test",
        "metrics": {"files_changed": 3},
        "artifact": {"type": "other"},
    }


def _corpus_v11_contract_full(workspace: Path) -> dict[str, object]:
    """v1.1 fixture from tests/contract/test_handoff_schema_contract.py#_valid_handoff."""
    rel = ".dadaia/reports/dadaia-workspace/code-reviewer/report.html"
    content_hash = _materialize_artifact(workspace, rel, b"<html>review</html>")
    return {
        "schema_version": "handoff-v1.1",
        "agent": "code-reviewer",
        "context": "dadaia-workspace",
        "produced_at": "2026-06-03T12:00:00Z",
        "scope": "dadaia-workspace/tests",
        "metrics": {"files_changed": 2, "tests_added": 1},
        "artifact": {"type": "report", "path": rel, "content_hash": content_hash},
        "findings": [
            {
                "severity": "HIGH",
                "message": "Suite has stale implementation tests.",
                "detail_md": "Tests assert deleted implementation details instead of current contracts.",
                "fix_recommendation": "Delete stale tests and promote behavior contracts.",
            }
        ],
        "verdict": "APPROVED",
        "verdict_reason": "Contract is valid.",
    }


def _corpus_v11_skill_handoff_only(workspace: Path) -> dict[str, object]:
    """SKILL.md 'Example — handoff-only (the default)' — transcribed verbatim."""
    return {
        "schema_version": "handoff-v1.1",
        "agent": "software-engineer",
        "context": "dadaia-workspace",
        "produced_at": "2026-06-10T12:00:00Z",
        "scope": "T-128 implementation — run.resume idempotency",
        "metrics": {"files_changed": 2, "tests_added": 4},
        "artifact": {"type": "other"},
        "release_id": "v0.1.10",
        "next_handoff": {
            "agent": "qa-engineer",
            "context": "dadaia-workspace",
            "expected_artifact_type": "report",
        },
    }


def _corpus_v11_skill_with_report(workspace: Path) -> dict[str, object]:
    """SKILL.md 'Example — with HTML report' — verbatim structure, real hash."""
    rel = ".dadaia/reports/dadaia-workspace/qa-engineer/2026-06-10T120000Z-T-128-validation.html"
    content_hash = _materialize_artifact(workspace, rel, b"<html>T-128 validation</html>")
    return {
        "schema_version": "handoff-v1.1",
        "agent": "qa-engineer",
        "context": "dadaia-workspace",
        "produced_at": "2026-06-10T12:00:00Z",
        "scope": "T-128 acceptance validation",
        "metrics": {"checks_run": 12, "checks_passed": 12},
        "release_id": "v0.1.10",
        "artifact": {"type": "report", "path": rel, "content_hash": content_hash},
        "findings": [
            {
                "severity": "INFO",
                "message": "All acceptance checks passed.",
                "detail_md": "Ran full pytest suite; 0 failures.",
                "fix_recommendation": "No action required.",
            }
        ],
        "verdict": "APPROVED",
        "verdict_reason": "Acceptance criteria satisfied.",
        "next_handoff": {
            "agent": "human",
            "context": "dadaia-workspace",
            "expected_artifact_type": "other",
        },
    }


_CORPUS: dict[str, Callable[[Path], dict[str, object]]] = {
    "v1-minimal-report": _corpus_v1_minimal_report,
    "v1-no-artifact-path": _corpus_v1_no_artifact_path,
    "v1.1-contract-full": _corpus_v11_contract_full,
    "v1.1-skill-handoff-only": _corpus_v11_skill_handoff_only,
    "v1.1-skill-with-report": _corpus_v11_skill_with_report,
}


# ---------------------------------------------------------------------------
# AC-1 — back-compat corpus lock (T-62-10; must stay green post-FR1/FR2)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fixture_name", sorted(_CORPUS))
def test_backcompat_corpus_lock(fixture_name: str, tmp_path: Path) -> None:
    """Every historical v1/v1.1 handoff shape validates — before AND after the v1.2 bump."""
    service = _service(tmp_path)
    doc = _CORPUS[fixture_name](tmp_path)
    handoff_path = _write_handoff(tmp_path, doc, fixture_name.replace(".", "-"))

    result = service.validate_file(handoff_path)

    assert result.valid is True, [(e.field_path, e.message) for e in result.errors]
    if "path" in doc["artifact"]:  # type: ignore[operator]
        assert result.hash_status == "match"
    else:
        assert result.hash_status is None


def test_backcompat_corpus_lock_via_validate_all(tmp_path: Path) -> None:
    """The whole corpus under one handoff root passes ``validate_all`` — zero invalid."""
    service = _service(tmp_path)
    for name, builder in _CORPUS.items():
        _write_handoff(tmp_path, builder(tmp_path), name.replace(".", "-"))

    results = service.validate_all(context="dadaia-workspace")

    assert len(results) == len(_CORPUS)
    assert all(r.valid for r in results), [
        (str(r.path), [(e.field_path, e.message) for e in r.errors]) for r in results if not r.valid
    ]


# ---------------------------------------------------------------------------
# T-62-11 — FR1/FR2: v1.2 conditional, existence, coverage, detection fix
# ---------------------------------------------------------------------------
#
# Staged RED-first captures (AC-2, recorded 2026-07-07 before the edits):
#   Stage 1 (pre-FR1 schema): v1.2-without-self_pull failed ONLY on the enum —
#     [('schema_version', "'handoff-v1.2' is not one of ['handoff-v1', 'handoff-v1.1']")]
#   Stage 2 (post-FR1 schema, pre-FR2 service): the SAME doc passed schema-blind
#     (validator errors == []) — the conditional gap this section closes.
# AC-4 RED capture (the picked bug's repro VERBATIM, pre-detection-fix):
#   `dadaia reports validate <v1.2 sidecar>` → exit 1 with
#   "ERROR: Missing required field 'findings[]'. This sidecar appears to be v1.0
#    and is incompatible with v1.1." (misrouted into _check_v10_compat).


def _v12_doc(
    refs: list[str] | None,
    agent: str = "software-engineer",
    schema_version: str = "handoff-v1.2",
) -> dict[str, object]:
    doc: dict[str, object] = {
        "schema_version": schema_version,
        "agent": agent,
        "context": "dadaia-workspace",
        "produced_at": "2026-07-07T12:00:00Z",
        "scope": "T-62-11 v1.2 validation",
        "metrics": {},
        "artifact": {"type": "other"},
    }
    if refs is not None:
        doc["self_pull"] = {"refs": refs}
    return doc


def _plant_atom(workspace: Path, ref: str) -> None:
    atom = workspace / ref
    atom.parent.mkdir(parents=True, exist_ok=True)
    atom.write_text("atom", encoding="utf-8")


# --- AC-2: the 4-case version matrix — ONE named parametrized test (QA62-5) ---


@pytest.mark.parametrize(
    ("schema_version", "with_self_pull", "expect_valid"),
    [
        ("handoff-v1", False, True),
        ("handoff-v1.1", False, True),
        ("handoff-v1.2", True, True),
        ("handoff-v1.2", False, False),
    ],
    ids=["v1-ok", "v1.1-ok", "v1.2-with-self_pull-ok", "v1.2-without-self_pull-fails"],
)
def test_schema_version_matrix(
    schema_version: str, with_self_pull: bool, expect_valid: bool, tmp_path: Path
) -> None:
    """v1 ✓ / v1.1 ✓ / v1.2+self_pull ✓ / v1.2−self_pull ✗ (one auditability point)."""
    service = _service(tmp_path)
    ref = "specs/memory/architecture.md"
    _plant_atom(tmp_path, ref)
    doc = _v12_doc([ref] if with_self_pull else None, schema_version=schema_version)
    handoff_path = _write_handoff(tmp_path, doc, f"matrix-{schema_version}-{with_self_pull}")

    result = service.validate_file(handoff_path)

    assert result.valid is expect_valid, [(e.field_path, e.message) for e in result.errors]
    if not expect_valid:
        assert any(e.field_path == "self_pull" for e in result.errors)


# --- AC-3(a): refs existence ---


def test_v12_nonexistent_ref_fails_with_indexed_evidence(tmp_path: Path) -> None:
    service = _service(tmp_path)
    good = "specs/memory/architecture.md"
    _plant_atom(tmp_path, good)
    doc = _v12_doc([good, "specs/memory/ghost-atom.md"])
    handoff_path = _write_handoff(tmp_path, doc, "missing-ref")

    result = service.validate_file(handoff_path)

    assert result.valid is False
    assert any(
        e.field_path == "self_pull.refs[1]" and "does not exist" in e.message for e in result.errors
    ), [(e.field_path, e.message) for e in result.errors]


def test_v12_ref_resolves_under_repos_context(tmp_path: Path) -> None:
    """Resolution order (a): <workspace>/repos/<context>/<ref>."""
    service = _service(tmp_path)
    ref = "specs/memory/quality-assurance.md"
    _plant_atom(tmp_path, f"repos/dadaia-workspace/{ref}")
    doc = _v12_doc([ref], agent="qa-engineer")
    handoff_path = _write_handoff(tmp_path, doc, "repos-resolved")

    result = service.validate_file(handoff_path)

    assert result.valid is True, [(e.field_path, e.message) for e in result.errors]


def test_v12_existence_fail_soft_when_workspace_root_is_none(tmp_path: Path) -> None:
    """Non-canonical handoff root → no workspace root → shape-only (fail-soft)."""
    # reports_root NOT ending in .dadaia/handoff → _infer_workspace_root returns None.
    service = ReportsValidationService(
        validator=StdlibHandoffValidator(_SCHEMA_PATH), reports_root=tmp_path
    )
    doc = _v12_doc(["specs/memory/never-created.md"])
    handoff_path = tmp_path / "failsoft.handoff.json"
    handoff_path.write_text(json.dumps(doc), encoding="utf-8")

    result = service.validate_file(handoff_path)

    assert result.valid is True, [(e.field_path, e.message) for e in result.errors]


# --- AC-3(b): role-map coverage ---


def test_v12_mapped_agent_missing_its_atom_fails_coverage(tmp_path: Path) -> None:
    """A qa-engineer v1.2 handoff omitting specs/memory/quality-assurance.md fails."""
    service = _service(tmp_path)
    other = "specs/memory/architecture.md"
    _plant_atom(tmp_path, other)
    doc = _v12_doc([other], agent="qa-engineer")
    handoff_path = _write_handoff(tmp_path, doc, "coverage-miss")

    result = service.validate_file(handoff_path)

    assert result.valid is False
    assert any(
        e.field_path == "self_pull.refs" and "quality-assurance" in e.message for e in result.errors
    ), [(e.field_path, e.message) for e in result.errors]


def test_v12_unmapped_agent_has_no_coverage_requirement(tmp_path: Path) -> None:
    """software-engineer is unmapped — any existing refs satisfy v1.2."""
    service = _service(tmp_path)
    ref = "specs/constitution.md"
    _plant_atom(tmp_path, ref)
    doc = _v12_doc([ref], agent="software-engineer")
    handoff_path = _write_handoff(tmp_path, doc, "unmapped-ok")

    result = service.validate_file(handoff_path)

    assert result.valid is True, [(e.field_path, e.message) for e in result.errors]


# --- AC-3(c): traversal refs rejected by the schema pattern ---


@pytest.mark.parametrize("bad_ref", ["specs/../etc/passwd", "../outside.md", "/etc/passwd"])
def test_v12_traversal_or_absolute_ref_rejected_by_schema_pattern(
    bad_ref: str, tmp_path: Path
) -> None:
    service = _service(tmp_path)
    doc = _v12_doc([bad_ref])
    handoff_path = _write_handoff(tmp_path, doc, "traversal")

    result = service.validate_file(handoff_path)

    assert result.valid is False
    assert any(e.field_path == "self_pull.refs[0]" for e in result.errors), [
        (e.field_path, e.message) for e in result.errors
    ]


# --- Re-export contract (ADR-4): role_atoms keeps exporting the SAME map object ---


def test_role_atom_map_reexported_from_core_same_object() -> None:
    from dadaia_workspace.core.role_atom_map import ROLE_ATOM_MAP as core_map
    from dadaia_workspace.features.lifecycle.role_atoms import ROLE_ATOM_MAP as lifecycle_map

    assert core_map is lifecycle_map
    assert core_map == {
        "software-architect": "memory/architecture.md",
        "qa-engineer": "memory/quality-assurance.md",
        "product-engineer": "memory/product/catalog.json",
    }


# --- AC-4: detection fix — the picked bug's repro VERBATIM (Ruling 62-E) ---


def test_v12_sidecar_never_routes_to_v10_compat_cli(tmp_path: Path, monkeypatch) -> None:
    """Bug reports-sidecar-version-detection-misroutes-future-tokens (HIGH).

    Repro verbatim: author a handoff with schema token handoff-v1.2 and run
    `dadaia reports validate <file>`. Pre-fix (RED, captured 2026-07-07): the
    detector fell through to v1.0-compat and hard-errored exit 1 with
    "Missing required field 'findings[]'". Post-fix: the same v1.2 sidecar with
    NO findings[] exits 0 and the compat message never appears.
    """
    from typer.testing import CliRunner

    from dadaia_workspace.cli.main import app
    from dadaia_workspace.features.workspace.service import WorkspaceService
    from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
    from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(tmp_path)
    FileSystemPublicAssetManager().stage(tmp_path)
    monkeypatch.chdir(tmp_path)

    ref = "specs/memory/architecture.md"
    _plant_atom(tmp_path, ref)
    doc = _v12_doc([ref])
    assert "findings" not in doc  # the repro's trigger condition
    handoff_path = tmp_path / "v12.handoff.json"
    handoff_path.write_text(json.dumps(doc), encoding="utf-8")

    result = CliRunner().invoke(app, ["reports", "validate", str(handoff_path)])

    assert result.exit_code == 0, result.output
    assert "Missing required field 'findings[]'" not in result.output
    assert "1 valid" in result.output
