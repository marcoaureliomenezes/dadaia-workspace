"""Unit tests for dadaia_workspace.hooks.root_whitelist."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from dadaia_workspace.hooks import root_whitelist


def _ws(tmp_path: Path) -> Path:
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    return tmp_path


def _run(
    monkeypatch: pytest.MonkeyPatch,
    payload: dict[str, object],
    *,
    capsys: pytest.CaptureFixture[str],
) -> str:
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    assert root_whitelist.main() == 0
    return capsys.readouterr().out


def test_non_write_tool_allows(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("WORKSPACE_ROOT", str(_ws(tmp_path)))
    out = _run(monkeypatch, {"tool_name": "Read", "tool_input": {"path": "x"}}, capsys=capsys)
    assert out == ""


def test_whitelisted_root_entry_allows(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ws = _ws(tmp_path)
    monkeypatch.setenv("WORKSPACE_ROOT", str(ws))
    out = _run(
        monkeypatch,
        {"tool_name": "Write", "tool_input": {"file_path": str(ws / "AGENTS.md")}},
        capsys=capsys,
    )
    assert out == ""


def test_subdir_write_allows(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ws = _ws(tmp_path)
    monkeypatch.setenv("WORKSPACE_ROOT", str(ws))
    target = ws / "repos" / "x" / "file.py"
    out = _run(
        monkeypatch,
        {"tool_name": "Write", "tool_input": {"file_path": str(target)}},
        capsys=capsys,
    )
    assert out == ""


def test_forbidden_root_entry_blocks(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ws = _ws(tmp_path)
    monkeypatch.setenv("WORKSPACE_ROOT", str(ws))
    out = _run(
        monkeypatch,
        {"tool_name": "Write", "tool_input": {"file_path": str(ws / "junk.txt")}},
        capsys=capsys,
    )
    decision = json.loads(out)
    assert decision["decision"] == "block"
    assert "ROOT WHITELIST GATE" in decision["reason"]


def test_operator_exception_allows(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ws = _ws(tmp_path)
    (ws / ".dadaia" / "states" / "root_exceptions.txt").write_text(
        "# operator exceptions\n*.png\n", encoding="utf-8"
    )
    monkeypatch.setenv("WORKSPACE_ROOT", str(ws))
    out = _run(
        monkeypatch,
        {"tool_name": "Write", "tool_input": {"file_path": str(ws / "screenshot.png")}},
        capsys=capsys,
    )
    assert out == ""


def test_unparseable_path_fails_open(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("WORKSPACE_ROOT", str(_ws(tmp_path)))
    out = _run(monkeypatch, {"tool_name": "Write", "tool_input": {}}, capsys=capsys)
    assert out == ""
