"""Regression tests for T-011-07 / bug B4 — workspace-rooted relative artifact paths.

Bug: ``handoff-artifact-path-cannot-reference-specs-audits``.

A handoff whose ``artifact.path`` points at the canonical committed auditor channel
``repos/<slug>/specs/audits/<UTC>/audit.md`` could never validate, because
``_resolve_artifact_path`` only workspace-rooted paths prefixed ``.dadaia/``; every other
relative path resolved from the handoff file's own directory, so ``repos/...`` became
``.dadaia/handoff/<ctx>/repos/...`` → ``missing_artifact``.

The fix: ANY relative ``artifact.path`` that exists under ``workspace_root`` resolves
workspace-rooted; the handoff-dir-relative fallback is kept for legacy artifacts that only
exist there; when a path is resolvable BOTH ways, workspace-root wins; the
``_within_workspace`` guard (resolve + relative_to, symlink-safe) is preserved — security
coverage against path-escape (CWE-22).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from dadaia_workspace.features.reports.validation import (
    ReportsValidationService,
)
from tests.fakes import FakeHandoffValidator


def _make_service(tmp_path: Path) -> tuple[ReportsValidationService, Path]:
    """Build a service whose reports_root is a real ``<ws>/.dadaia/handoff`` tree."""
    handoff_root = tmp_path / ".dadaia" / "handoff"
    handoff_root.mkdir(parents=True)
    service = ReportsValidationService(
        validator=FakeHandoffValidator(canned_errors=[]),
        reports_root=handoff_root,
    )
    return service, handoff_root


def _write_handoff(handoff_path: Path, artifact_rel: str, content_hash: str) -> None:
    handoff_path.parent.mkdir(parents=True, exist_ok=True)
    doc: dict[str, object] = {
        "schema_version": "handoff-v1.1",
        "agent": "project-auditor",
        "context": "dadaia-workspace",
        "produced_at": "2026-06-10T00:00:00Z",
        "scope": "audit",
        "metrics": {"checks": 1},
        "artifact": {
            "type": "report",
            "path": artifact_rel,
            "content_hash": content_hash,
        },
    }
    handoff_path.write_text(json.dumps(doc), encoding="utf-8")


def test_resolve_repos_specs_audits_artifact_validates(tmp_path: Path) -> None:
    """Bug B4 repro: a ``repos/<slug>/specs/audits/<UTC>/audit.md`` path validates.

    The audit MD lives at the canonical committed auditor channel under the workspace
    root; the handoff lives under ``.dadaia/handoff/<ctx>/``. The artifact must resolve
    workspace-rooted and hash-match (exit-0 equivalent at the service layer).
    """
    service, handoff_root = _make_service(tmp_path)

    audit = (
        tmp_path
        / "repos"
        / "dadaia-workspace"
        / "specs"
        / "audits"
        / "2026-06-10T000000Z"
        / "audit.md"
    )
    audit.parent.mkdir(parents=True)
    audit.write_bytes(b"# Audit\n\nfindings\n")
    content_hash = hashlib.sha256(audit.read_bytes()).hexdigest()

    handoff_path = handoff_root / "dadaia-workspace" / "2026-06-10T000000Z-audit.handoff.json"
    _write_handoff(
        handoff_path,
        "repos/dadaia-workspace/specs/audits/2026-06-10T000000Z/audit.md",
        content_hash,
    )

    assert service.check_hash(handoff_path) == "match"


def test_workspace_root_wins_when_path_resolvable_both_ways(tmp_path: Path) -> None:
    """When the SAME relative path exists workspace-rooted AND handoff-relative,
    the workspace-rooted file must win (also proves the legacy handoff-dir-relative
    fallback resolves at all, via the losing side).

    Two distinct files share the relative path ``shared/artifact.md`` — one under the
    workspace root, one under the handoff dir. The handoff's ``content_hash`` matches
    only the WORKSPACE-ROOTED file, proving workspace-root resolution wins.
    """
    service, handoff_root = _make_service(tmp_path)

    # Workspace-rooted copy (the winner).
    ws_artifact = tmp_path / "shared" / "artifact.md"
    ws_artifact.parent.mkdir(parents=True)
    ws_artifact.write_bytes(b"WORKSPACE-ROOTED content\n")
    ws_hash = hashlib.sha256(ws_artifact.read_bytes()).hexdigest()

    # Handoff-dir-relative copy with deliberately different bytes.
    ctx_dir = handoff_root / "dadaia-workspace"
    ctx_dir.mkdir()
    handoff_relative_copy = ctx_dir / "shared" / "artifact.md"
    handoff_relative_copy.parent.mkdir(parents=True)
    handoff_relative_copy.write_bytes(b"HANDOFF-RELATIVE content\n")

    handoff_path = ctx_dir / "2026-06-10T000000Z-shared.handoff.json"
    # content_hash matches the workspace-rooted file only.
    _write_handoff(handoff_path, "shared/artifact.md", ws_hash)

    assert service.check_hash(handoff_path) == "match"

    # And the legacy fallback alone (no workspace-rooted competitor) still resolves.
    ctx_dir2 = handoff_root / "legacy-ctx"
    ctx_dir2.mkdir()
    sibling = ctx_dir2 / "report.html"
    sibling.write_bytes(b"<html>legacy sibling</html>")
    sibling_hash = hashlib.sha256(sibling.read_bytes()).hexdigest()
    legacy_handoff = ctx_dir2 / "2026-06-10T000000Z-report.handoff.json"
    _write_handoff(legacy_handoff, "report.html", sibling_hash)
    assert service.check_hash(legacy_handoff) == "match"


@pytest.mark.parametrize(
    "bad_ref_builder",
    ["absolute-outside", "dotdot-escape"],
)
def test_escape_paths_rejected(tmp_path: Path, bad_ref_builder: str) -> None:
    """Absolute-outside and ``..``-traversal artifact paths are both rejected by the
    ``_within_workspace`` guard (resolve + relative_to, symlink-safe — CWE-22)."""
    service, handoff_root = _make_service(tmp_path)

    outside = tmp_path.parent / f"t011_07_{bad_ref_builder}.md"
    outside.write_bytes(b"outside the workspace")
    try:
        ctx_dir = handoff_root / "dadaia-workspace"
        ctx_dir.mkdir(exist_ok=True)
        handoff_path = ctx_dir / f"2026-06-10T000000Z-{bad_ref_builder}.handoff.json"
        ref = (
            str(outside)
            if bad_ref_builder == "absolute-outside"
            else "../../../../" + outside.name
        )
        _write_handoff(
            handoff_path,
            ref,
            hashlib.sha256(outside.read_bytes()).hexdigest(),
        )

        assert service.check_hash(handoff_path) == "missing_artifact"
    finally:
        outside.unlink(missing_ok=True)
