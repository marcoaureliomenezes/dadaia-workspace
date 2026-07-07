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
from pathlib import Path
from typing import Callable

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
        (str(r.path), [(e.field_path, e.message) for e in r.errors])
        for r in results
        if not r.valid
    ]
