"""Intent: CONTRACT — sa-editable-install-reports-a-frozen-version: one provider_version()
answers "which version is running", for every verb. Size: SMALL — the importlib.metadata
boundary is faked; every reader above it runs for real."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.features.reconcile.service import reconcile_workspace
from dadaia_workspace.infrastructure.provider_version import provider_version
from tests.fixtures.provider_dist import install_fake_dist

pytestmark = pytest.mark.unit

_PKG = Path(__file__).resolve().parents[3] / "dadaia_workspace"


def _source(tmp_path: Path, version: str) -> Path:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "pyproject.toml").write_text(f'[tool.poetry]\nversion = "{version}"\n')
    return tmp_path / "src"


def _three_verbs(tmp_path: Path) -> tuple[str, str, str | None]:
    runner = CliRunner()
    shown = runner.invoke(app, ["--version"]).output.strip()
    caps = json.loads(runner.invoke(app, ["capabilities", "--json"]).output)
    reconciled = reconcile_workspace(
        tmp_path, expected_version="0.4.7", public_service=None, doctor_service=None
    )
    return shown, caps["provider"]["distribution_version"], reconciled.error


def test_an_editable_install_reports_its_source_version_everywhere(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """sa-editable-install-reports-a-frozen-version#B1: dist-info frozen at 0.1.4, editable
    to a source declaring 0.4.7 — `--version`, `capabilities --json` and `reconcile
    --expect-version 0.4.7` all answer 0.4.7 and reconcile accepts the version."""
    install_fake_dist(monkeypatch, "0.1.4", editable_source=_source(tmp_path, "0.4.7"))

    shown, caps, reconcile_error = _three_verbs(tmp_path)

    assert provider_version() == "0.4.7"
    assert shown == "dadaia-workspace 0.4.7"
    assert caps == "0.4.7"
    assert "provider version mismatch" not in str(reconcile_error)


def test_a_wheel_install_reports_its_dist_info_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """sa-editable-install-reports-a-frozen-version#B2: a non-editable install answers its
    dist-info version in all three verbs."""
    install_fake_dist(monkeypatch, "0.4.7")

    shown, caps, reconcile_error = _three_verbs(tmp_path)

    assert (shown, caps) == ("dadaia-workspace 0.4.7", "0.4.7")
    assert "provider version mismatch" not in str(reconcile_error)


def test_the_running_version_is_read_in_one_place() -> None:
    """sa-editable-install-reports-a-frozen-version#B4: metadata.version('dadaia-workspace')
    is called nowhere but inside infrastructure/provider_version.py."""
    readers = []
    for path in sorted(_PKG.rglob("*.py")):
        if path == _PKG / "infrastructure" / "provider_version.py":
            continue
        for node in ast.walk(ast.parse(path.read_text("utf-8"))):
            if (
                isinstance(node, ast.Call)
                and ast.unparse(node.func).split(".")[-1] == "version"
                and any(
                    isinstance(a, ast.Constant) and a.value == "dadaia-workspace" for a in node.args
                )
            ):
                readers.append(f"{path.relative_to(_PKG)}:{node.lineno}")
    assert readers == []
