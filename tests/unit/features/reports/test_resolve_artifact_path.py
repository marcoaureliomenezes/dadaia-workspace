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
``_within_workspace`` guard (resolve + relative_to, symlink-safe) is preserved.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

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


def test_resolve_legacy_handoff_dir_relative_still_validates(tmp_path: Path) -> None:
    """A sibling artifact that exists ONLY next to the handoff still validates."""
    service, handoff_root = _make_service(tmp_path)

    ctx_dir = handoff_root / "dadaia-workspace"
    ctx_dir.mkdir()
    sibling = ctx_dir / "report.html"
    sibling.write_bytes(b"<html>legacy sibling</html>")
    content_hash = hashlib.sha256(sibling.read_bytes()).hexdigest()

    handoff_path = ctx_dir / "2026-06-10T000000Z-report.handoff.json"
    _write_handoff(handoff_path, "report.html", content_hash)

    assert service.check_hash(handoff_path) == "match"


def test_workspace_root_wins_when_path_resolvable_both_ways(tmp_path: Path) -> None:
    """When the SAME relative path exists workspace-rooted AND handoff-relative,
    the workspace-rooted file must win.

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


def test_absolute_path_outside_workspace_rejected(tmp_path: Path) -> None:
    """An absolute path outside the workspace is rejected by the guard."""
    service, handoff_root = _make_service(tmp_path)

    outside = tmp_path.parent / "t011_07_outside.md"
    outside.write_bytes(b"outside the workspace")
    try:
        ctx_dir = handoff_root / "dadaia-workspace"
        ctx_dir.mkdir()
        handoff_path = ctx_dir / "2026-06-10T000000Z-outside.handoff.json"
        _write_handoff(
            handoff_path,
            str(outside),
            hashlib.sha256(outside.read_bytes()).hexdigest(),
        )

        assert service.check_hash(handoff_path) == "missing_artifact"
    finally:
        outside.unlink(missing_ok=True)


def test_dotdot_escape_path_rejected(tmp_path: Path) -> None:
    """A ``..`` traversal escaping the workspace is rejected by the guard.

    The schema rejects ``..`` for real callers; this asserts the resolver's own
    ``_within_workspace`` guard is a defence-in-depth backstop independent of the schema.
    """
    service, handoff_root = _make_service(tmp_path)

    outside = tmp_path.parent / "t011_07_dotdot.md"
    outside.write_bytes(b"escaped via dotdot")
    try:
        ctx_dir = handoff_root / "dadaia-workspace"
        ctx_dir.mkdir()
        handoff_path = ctx_dir / "2026-06-10T000000Z-dotdot.handoff.json"
        # From <ws>/.dadaia/handoff/dadaia-workspace/ climb out of the workspace.
        escape_ref = "../../../../t011_07_dotdot.md"
        _write_handoff(
            handoff_path,
            escape_ref,
            hashlib.sha256(outside.read_bytes()).hexdigest(),
        )

        assert service.check_hash(handoff_path) == "missing_artifact"
    finally:
        outside.unlink(missing_ok=True)
