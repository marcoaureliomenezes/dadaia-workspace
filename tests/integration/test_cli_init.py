"""dadaia init CLI — happy path + skip-assets + workspace resolution."""

from pathlib import Path

from typer.testing import CliRunner

from dadaia_workspace.cli.main import app

_runner = CliRunner()


def test_init_creates_dadaia_directory(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(app, ["init", "--workspace", str(tmp_path), "--skip-assets"])
    assert result.exit_code == 0, result.output
    assert (tmp_path / ".dadaia").exists()
    assert (tmp_path / ".dadaia" / "states" / "spec_contexts.json").exists()


def test_init_skip_assets_prints_skip_message(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(app, ["init", "--workspace", str(tmp_path), "--skip-assets"])
    assert result.exit_code == 0, result.output
    assert "skip" in result.output.lower() or "Skipped" in result.output


def test_init_is_idempotent(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _runner.invoke(app, ["init", "--workspace", str(tmp_path), "--skip-assets"])
    result = _runner.invoke(app, ["init", "--workspace", str(tmp_path), "--skip-assets"])
    assert result.exit_code == 0, result.output


def test_init_without_workspace_flag_uses_cwd(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(app, ["init", "--skip-assets"])
    assert result.exit_code == 0, result.output
    assert (tmp_path / ".dadaia").exists()


def test_init_with_assets_outputs_installed_or_up_to_date(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(app, ["init", "--workspace", str(tmp_path)])
    assert result.exit_code == 0, result.output
    # Either installs assets or reports all up to date
    assert (
        "asset" in result.output.lower()
        or "up to date" in result.output.lower()
        or "✓" in result.output
    )
