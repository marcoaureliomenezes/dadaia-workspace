"""Exit codes must tell the truth (validation-029 F-04/F-12) + certify without a workspace (F-03).

A CLI that finds problems and exits 0 masks failures from every script/agent that
consumes it — the exact 'cmd | tail masks exit' class the house gotchas document.
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from dadaia_workspace import container
from dadaia_workspace.cli.main import app

_runner = CliRunner()


class _Issue:
    code = "ROOT-4"
    description = "Unknown top-level subdirectory/ies inside .dadaia/: 'nonsense'."
    fixable = False


class _StubDoctor:
    def check(self):
        return [_Issue()]


def test_doctor_exits_nonzero_when_issues_found(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    (tmp_path / ".dadaia" / "states" / "spec_contexts.json").write_text(
        '{"schema_version": "2", "contexts": []}'
    )
    (tmp_path / "repos").mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(container, "build_doctor_service", lambda root: _StubDoctor())
    result = _runner.invoke(app, ["doctor"])
    assert "ROOT-4" in result.output
    assert result.exit_code != 0, "doctor found issues but exited 0"


def test_reports_validate_invalid_file_exits_nonzero(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    (tmp_path / ".dadaia" / "states" / "spec_contexts.json").write_text(
        '{"schema_version": "2", "contexts": []}'
    )
    (tmp_path / "repos").mkdir()
    monkeypatch.chdir(tmp_path)
    # Stage the packaged schema where the validator expects it.
    import shutil

    import dadaia_workspace

    pkg = Path(dadaia_workspace.__file__).parent
    schema_src = pkg / "public" / "schemas" / "handoff-v1.schema.json"
    schema_dst = tmp_path / ".dadaia" / "agentic" / "schemas" / "handoff-v1.schema.json"
    schema_dst.parent.mkdir(parents=True)
    shutil.copy2(schema_src, schema_dst)
    bad = tmp_path / "bad.handoff.json"
    bad.write_text(json.dumps({"not": "a-handoff"}))
    result = _runner.invoke(app, ["reports", "validate", str(bad)])
    assert "INVALID" in result.output
    assert result.exit_code != 0, "INVALID result must not exit 0"


def test_certify_runs_without_initialized_workspace(tmp_path: Path, monkeypatch) -> None:
    """certify's contract is a DISPOSABLE workspace — a bare cwd must not traceback."""
    monkeypatch.chdir(tmp_path)

    class _Ok:
        ok = True
        checks: list = []

        def to_dict(self):
            return {"ok": True, "checks": []}

    seen: dict[str, Path] = {}

    def _spy(root: Path, *, keep: bool = False):
        seen["root"] = root
        return _Ok()

    monkeypatch.setattr(container, "run_certification", _spy)
    result = _runner.invoke(app, ["certify", "--json"])
    assert result.exit_code == 0, result.output
    assert "Traceback" not in result.output
    assert seen, "certification must still run, on a fallback disposable root"


def test_certify_json_stdout_is_pure_json(tmp_path: Path, monkeypatch) -> None:
    """Bug certify-json-stdout-polluted-info-line: diagnostics belong on stderr.

    With no initialized workspace the disposable-anchor info line must not precede
    the JSON document on stdout — consumers pipe stdout straight into json.loads.
    """
    monkeypatch.chdir(tmp_path)

    class _Ok:
        ok = True
        checks: list = []

        def to_dict(self):
            return {"ok": True, "checks": []}

    monkeypatch.setattr(container, "run_certification", lambda root, *, keep=False: _Ok())
    result = _runner.invoke(app, ["certify", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
