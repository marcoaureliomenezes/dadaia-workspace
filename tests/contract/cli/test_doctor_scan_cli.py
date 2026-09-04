"""Intent: CONTRACT — 0.4.6 AC2, AC4 (the `dadaia doctor` surface: finding lines, score line,
exit code, `--json`, `--fix --expired-only --quiet`); size: SMALL.

The CLI renders what ``DoctorService.scan()``/``fix()`` return — nothing here re-tests the
walk (``tests/unit/test_spec_context_doctor_root.py``); it pins the shapes SPEC §3 names:
one ``WS-<zone>-<verdict>  <path>  (<detail>)`` line per non-canonical entry, the score line
last, exit 1 on any slop/expired/missing, the three ``--json`` keys, and a quiet lane that
speaks only when it deleted something.
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace import container
from dadaia_workspace.cli.main import app
from dadaia_workspace.core.harness_registry import L1_ENTRY_HARNESSES
from dadaia_workspace.core.platform import PLATFORM
from dadaia_workspace.core.workspace_layout import Creator, zones_created_by, zones_with_ttl
from dadaia_workspace.features.spec_context.doctor import DoctorService
from tests.fakes import FakeContextStore, FakeGitClient

pytestmark = pytest.mark.contract

_TTL_ZONE = zones_with_ttl()[0]
_EXPIRED_CODE = f"WS-{_TTL_ZONE.name.lstrip('.')}-expired"
_FINDING_LINE = re.compile(r"^WS-[a-z.-]+-(slop|expired|missing)  \S+  \(.+\)$")
_SCORE_LINE = re.compile(r"^compliance: [0-9]+/[0-9]+ entries canonical \([0-9]+%\)$")


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    dadaia = tmp_path / ".dadaia"
    for zone in (*zones_created_by(Creator.INIT), *zones_created_by(Creator.INSTALL)):
        (dadaia / zone.name).mkdir(parents=True, exist_ok=True)
    (dadaia / "states" / "spec_contexts.json").write_text(
        '{"schema_version": "2", "contexts": []}', encoding="utf-8"
    )
    # FR8: a healthy states/ carries the profile; absent it is WS-states-missing.
    (dadaia / "states" / "harness_profile.json").write_text(
        json.dumps({"schema_version": "1", "harnesses": list(L1_ENTRY_HARNESSES)}),
        encoding="utf-8",
    )
    # ... and the install ledger: absent, the harness dirs are never classified.
    (dadaia / "states" / "install_ledger.json").write_text(
        json.dumps({"schema_version": "1", "entries": []}), encoding="utf-8"
    )
    (tmp_path / "repos").mkdir()
    (tmp_path / "AGENTS.md").write_text("# agents", encoding="utf-8")
    venv_bin = dadaia / ".venv" / PLATFORM.venv_scripts_dir
    venv_bin.mkdir(parents=True)
    entry = venv_bin / f"dadaia{PLATFORM.venv_exe_suffix}"
    entry.write_text("#!/bin/sh\n", encoding="utf-8")
    entry.chmod(0o755)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        container,
        "build_doctor_service",
        lambda root: DoctorService(FakeContextStore(), FakeGitClient(), root),
    )
    return tmp_path


def _plant_expired(workspace: Path) -> Path:
    zone_dir = workspace / ".dadaia" / _TTL_ZONE.name
    zone_dir.mkdir(exist_ok=True)
    stale = zone_dir / "stale"
    stale.write_text("", encoding="utf-8")
    two_days_ago = time.time() - 2 * 86_400
    os.utime(stale, (two_days_ago, two_days_ago))
    return stale


def test_lists_findings_then_the_score_line_and_exits_1(workspace: Path) -> None:
    (workspace / "junk.txt").write_text("", encoding="utf-8")
    _plant_expired(workspace)

    result = CliRunner().invoke(app, ["doctor"])
    lines = result.output.splitlines()

    assert result.exit_code == 1, result.output
    finding_lines = [ln for ln in lines if ln.startswith("WS-")]
    assert len(finding_lines) == 2
    assert all(_FINDING_LINE.match(ln) for ln in finding_lines), finding_lines
    assert _SCORE_LINE.match(lines[-1]), lines[-1]


def test_healthy_workspace_exits_0_with_a_full_score(workspace: Path) -> None:
    result = CliRunner().invoke(app, ["doctor"])
    lines = result.output.splitlines()

    assert result.exit_code == 0, result.output
    assert lines[-1].endswith("(100%)")
    assert not any(ln.startswith("WS-") for ln in lines)


def test_json_carries_findings_compliance_and_fixed(workspace: Path) -> None:
    (workspace / "junk.txt").write_text("", encoding="utf-8")

    result = CliRunner().invoke(app, ["doctor", "--json"])
    payload = json.loads(result.output)

    assert result.exit_code == 1
    assert {"findings", "compliance", "fixed"} <= set(payload)
    assert payload["findings"] == [
        {
            "code": "WS-root-slop",
            "path": "junk.txt",
            "verdict": "slop",
            "fixable": True,
            "detail": "(not in the root law or the exceptions)",
        }
    ]
    assert set(payload["compliance"]) == {"canonical", "total", "percent"}
    assert payload["fixed"] == []


def test_fix_expired_only_quiet_prints_only_what_it_deleted(workspace: Path) -> None:
    (workspace / "junk.txt").write_text("", encoding="utf-8")
    stale = _plant_expired(workspace)

    result = CliRunner().invoke(app, ["doctor", "--fix", "--expired-only", "--quiet"])

    assert result.exit_code == 0, result.output
    assert result.output.splitlines() == [f"{_EXPIRED_CODE}: deleted '{_TTL_ZONE.name}/stale'"]
    assert not stale.exists()
    assert (workspace / "junk.txt").exists()

    again = CliRunner().invoke(app, ["doctor", "--fix", "--expired-only", "--quiet"])
    assert again.exit_code == 0
    assert again.output == ""


def test_fix_deletes_slop_and_reports_the_post_fix_score(workspace: Path) -> None:
    (workspace / "junk.txt").write_text("", encoding="utf-8")

    result = CliRunner().invoke(app, ["doctor", "--fix"])
    lines = result.output.splitlines()

    assert result.exit_code == 0, result.output
    assert "WS-root-slop: deleted 'junk.txt'" in result.output
    assert lines[-1].endswith("(100%)")
    assert not (workspace / "junk.txt").exists()
