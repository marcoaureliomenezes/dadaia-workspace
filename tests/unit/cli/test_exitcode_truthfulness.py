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
from dadaia_workspace.core.doctor_rules import SectionFinding

_runner = CliRunner()


_ISSUE = SectionFinding(
    "ROOT-4", "error", ".dadaia/nonsense", False, True, "rm -r .dadaia/nonsense"
)


class _StubDoctor:
    def check(self):
        return [_ISSUE]

    def check_installed_hooks(self, context=None):
        return []

    check_projection = check_worktrees = check_skill_md_length = check_installed_hooks

    def scan(self):
        return ()


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


def test_certify_runs_without_a_workspace_and_prints_pure_json(tmp_path: Path, monkeypatch) -> None:
    """F-03: certify's contract is a DISPOSABLE workspace — a bare cwd runs it on a fallback root;
    bug certify-json-stdout-polluted-info-line: diagnostics go to stderr, stdout is the JSON alone."""
    monkeypatch.chdir(tmp_path)
    seen: list[Path] = []

    class _Ok:
        ok = True
        checks: list = []

        def to_dict(self):
            return {"ok": True, "checks": []}

    def _spy(root: Path, *, keep: bool = False):
        seen.append(root)
        return _Ok()

    monkeypatch.setattr(container, "run_certification", _spy)
    result = _runner.invoke(app, ["certify", "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == {"ok": True, "checks": []}
    assert len(seen) == 1
