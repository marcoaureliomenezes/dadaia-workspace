"""v0.1.55 FR5 (bug ``backlog-new-stub-readme-lag-intents-schema``): fresh stub is clean.

Root fix (OQ-1 INVERSION): the ``idea``-status BL-SCHEMA gate. A freshly-scaffolded
``dadaia backlog new`` stub carries ``status: idea`` and no ``intents[]`` — an unbound
brainstorm. ``backlog doctor`` must NOT flag it (``idea`` is exempt from the no-intents and
unresolved-subject BL-SCHEMA errors); those become mandatory at ``candidate`` and beyond.

E2E, deterministic, no spawned processes: scaffold a fresh ``specs/`` **without a
catalog.json**, generate the stub with the real ``backlog_new``, and run the real
``run_backlog_doctor`` engine — asserting zero BL-SCHEMA. AC-7(e): flipping the fresh stub to
``candidate`` must make BL-SCHEMA FIRE (proving the gate is status-gated, not a blanket
exemption).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.backlog.doctor import (
    BacklogDoctorCode,
    run_backlog_doctor,
)
from dadaia_workspace.features.spec_artifacts.new_artifacts import backlog_new

pytestmark = pytest.mark.integration


def _run_doctor(specs: Path, src: Path) -> list:
    """Run the real doctor engine over a fresh scaffold WITHOUT a catalog.json."""
    return run_backlog_doctor(
        specs_dir=specs,
        source_root=src,
        catalog_path=specs / "memory" / "product" / "catalog.json",  # deliberately absent
        alias_map_path=specs / "no-aliases.txt",  # absent → tolerated
        archive_root=specs / "_archive",  # absent → BL-STALE no-op
        cli_anchors=frozenset(),
    )


def _schema_findings(findings: list) -> list:
    return [f for f in findings if f.code is BacklogDoctorCode.BL_SCHEMA]


def test_fresh_stub_clean_then_flipped_to_candidate_fires_bl_schema(tmp_path: Path) -> None:
    """A fresh ``dadaia backlog new`` stub (status: idea, no intents, no catalog.json) is
    ``backlog doctor``-clean: zero BL-SCHEMA errors. AC-7(e): the SAME stub flipped to
    ``status: candidate`` FIRES BL-SCHEMA (a candidate carrying no intents is not exempt)
    — proving the gate is status-gated, not a blanket exemption."""
    specs = tmp_path / "specs"
    specs.mkdir()
    src = tmp_path / "src"
    src.mkdir()

    result = backlog_new(specs, "my-fresh-idea")
    assert result.path.is_file()

    findings = _run_doctor(specs, src)
    schema = _schema_findings(findings)
    assert schema == [], [f.to_dict() for f in schema]

    text = result.path.read_text(encoding="utf-8")
    assert "status: idea" in text
    result.path.write_text(text.replace("status: idea", "status: candidate"), encoding="utf-8")

    schema2 = _schema_findings(_run_doctor(specs, src))
    assert schema2, "a candidate with no intents[] must fire BL-SCHEMA (status-gate is not blanket)"
