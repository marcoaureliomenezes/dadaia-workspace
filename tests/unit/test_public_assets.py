"""Pure unit tests for public asset privacy checks.

The privacy denylist is operator-private and loaded at runtime from outside the
published package (env var ``DADAIA_PRIVACY_DENYLIST`` or
``<workspace_root>/.dadaia/states/privacy_denylist.json``). The shipped library
carries no private identifiers, so these tests seed their own terms.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.infrastructure.public_assets import (
    _PRIVACY_DENYLIST_ENV,
    FileSystemPublicAssetManager,
    _load_privacy_denylist,
)

_TEST_TERM = "10.99.99.99"


def _seed_denylist_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Seed the denylist via the env-var path (location-independent)."""
    source = tmp_path / "privacy_denylist.json"
    source.write_text(json.dumps([[_TEST_TERM, "test private IP"]]), encoding="utf-8")
    monkeypatch.setenv(_PRIVACY_DENYLIST_ENV, str(source))


def _make_workspace_root(tmp_path: Path) -> Path:
    """Create a minimal initialized workspace at *tmp_path* (sentinel present)."""
    sentinel = tmp_path / ".dadaia" / "states" / "spec_contexts.json"
    sentinel.parent.mkdir(parents=True, exist_ok=True)
    sentinel.write_text("{}", encoding="utf-8")
    return tmp_path


def test_public_privacy_gate_flags_text_denylist(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_denylist_env(monkeypatch, tmp_path)
    public_dir = tmp_path / "public"
    data_dir = public_dir / "data"
    data_dir.mkdir(parents=True)
    (data_dir / "AGENTS.md").write_text(f"Private endpoint: {_TEST_TERM}\n", encoding="utf-8")

    manager = FileSystemPublicAssetManager()
    manager._public_dir = public_dir  # noqa: SLF001

    report = manager._check_public_privacy()  # noqa: SLF001

    assert any(line.startswith("[error] public-privacy:") for line in report)
    assert any(_TEST_TERM in line.lower() for line in report)


def test_public_privacy_gate_ignores_bytecode_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_denylist_env(monkeypatch, tmp_path)
    public_dir = tmp_path / "public"
    cache_dir = public_dir / "skills" / "sample" / "__pycache__"
    cache_dir.mkdir(parents=True)
    (cache_dir / "leak.pyc").write_bytes(_TEST_TERM.encode())
    (public_dir / "data").mkdir()
    (public_dir / "data" / "AGENTS.md").write_text("# clean\n", encoding="utf-8")

    manager = FileSystemPublicAssetManager()
    manager._public_dir = public_dir  # noqa: SLF001

    assert manager._check_public_privacy() == ["[ok] public-privacy"]  # noqa: SLF001


def test_public_privacy_gate_noop_without_denylist_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With no denylist source the shipped library reports clean (no private terms)."""
    monkeypatch.delenv(_PRIVACY_DENYLIST_ENV, raising=False)
    # chdir to a directory with NO sentinel so resolve_workspace_root raises — no file fallback.
    no_ws = tmp_path / "no_workspace"
    no_ws.mkdir()
    monkeypatch.chdir(no_ws)

    public_dir = tmp_path / "public"
    data_dir = public_dir / "data"
    data_dir.mkdir(parents=True)
    (data_dir / "AGENTS.md").write_text("Endpoint: 10.99.99.99\n", encoding="utf-8")

    manager = FileSystemPublicAssetManager()
    manager._public_dir = public_dir  # noqa: SLF001

    assert manager._check_public_privacy() == ["[ok] public-privacy"]  # noqa: SLF001


def test_public_privacy_gate_scans_root_agents_md(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Root-level AGENTS.md (sibling of the package dir) is included in the scan."""
    _seed_denylist_env(monkeypatch, tmp_path)
    repo_root = tmp_path / "repo"
    public_dir = repo_root / "dadaia_workspace" / "public"
    public_dir.mkdir(parents=True)
    (repo_root / "AGENTS.md").write_text(f"host: {_TEST_TERM}\n", encoding="utf-8")

    manager = FileSystemPublicAssetManager()
    manager._public_dir = public_dir  # noqa: SLF001

    report = manager._check_public_privacy()  # noqa: SLF001
    assert any("AGENTS.md" in line and _TEST_TERM in line.lower() for line in report)


# --- _load_privacy_denylist loader contract -------------------------------


def test_load_denylist_dict_format(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "d.json"
    source.write_text(json.dumps({"foo": "reason-a", "bar": "reason-b"}), encoding="utf-8")
    monkeypatch.setenv(_PRIVACY_DENYLIST_ENV, str(source))
    assert _load_privacy_denylist() == (("foo", "reason-a"), ("bar", "reason-b"))


def test_load_denylist_list_of_strings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "d.json"
    source.write_text(json.dumps(["alpha", "beta"]), encoding="utf-8")
    monkeypatch.setenv(_PRIVACY_DENYLIST_ENV, str(source))
    assert _load_privacy_denylist() == (
        ("alpha", "private identifier"),
        ("beta", "private identifier"),
    )


def test_load_denylist_malformed_json_returns_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "d.json"
    source.write_text("{not valid json", encoding="utf-8")
    monkeypatch.setenv(_PRIVACY_DENYLIST_ENV, str(source))
    # chdir outside any workspace so the file fallback is also unavailable.
    no_ws = tmp_path / "no_workspace"
    no_ws.mkdir()
    monkeypatch.chdir(no_ws)
    assert _load_privacy_denylist() == ()


def test_load_denylist_missing_sources_returns_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(_PRIVACY_DENYLIST_ENV, str(tmp_path / "nope.json"))
    # chdir outside any workspace so the file fallback is also unavailable.
    no_ws = tmp_path / "no_workspace"
    no_ws.mkdir()
    monkeypatch.chdir(no_ws)
    assert _load_privacy_denylist() == ()


def test_load_denylist_env_takes_precedence_over_workspace_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Env var takes precedence; workspace file is ignored when env var is set."""
    workspace = _make_workspace_root(tmp_path / "ws")
    states = workspace / ".dadaia" / "states"
    (states / "privacy_denylist.json").write_text(
        json.dumps([["from-file", "file"]]), encoding="utf-8"
    )
    env_src = tmp_path / "env.json"
    env_src.write_text(json.dumps([["from-env", "env"]]), encoding="utf-8")
    monkeypatch.setenv(_PRIVACY_DENYLIST_ENV, str(env_src))
    monkeypatch.chdir(workspace)
    assert _load_privacy_denylist() == (("from-env", "env"),)


def test_load_denylist_falls_back_to_workspace_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When env var is absent, file at <workspace_root>/.dadaia/states/ is used."""
    monkeypatch.delenv(_PRIVACY_DENYLIST_ENV, raising=False)
    workspace = _make_workspace_root(tmp_path / "ws")
    states = workspace / ".dadaia" / "states"
    (states / "privacy_denylist.json").write_text(
        json.dumps([["from-file", "file"]]), encoding="utf-8"
    )
    monkeypatch.chdir(workspace)
    assert _load_privacy_denylist() == (("from-file", "file"),)


def test_load_denylist_no_workspace_no_env_returns_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When neither env var nor workspace is available, returns empty tuple."""
    monkeypatch.delenv(_PRIVACY_DENYLIST_ENV, raising=False)
    # chdir to a directory with no .dadaia sentinel so resolution fails.
    no_ws = tmp_path / "no_workspace"
    no_ws.mkdir()
    monkeypatch.chdir(no_ws)
    assert _load_privacy_denylist() == ()
