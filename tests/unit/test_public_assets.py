"""Pure unit tests for public asset privacy checks.

The privacy denylist is operator-private and loaded at runtime from outside the
published package (env var ``DADAIA_PRIVACY_DENYLIST`` or
``<repo_root>/.dadaia/states/privacy_denylist.json``). The shipped library
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


def _seed_denylist(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    source = tmp_path / "privacy_denylist.json"
    source.write_text(json.dumps([[_TEST_TERM, "test private IP"]]), encoding="utf-8")
    monkeypatch.setenv(_PRIVACY_DENYLIST_ENV, str(source))


def test_public_privacy_gate_flags_text_denylist(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_denylist(monkeypatch, tmp_path)
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
    _seed_denylist(monkeypatch, tmp_path)
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
    public_dir = tmp_path / "public"
    data_dir = public_dir / "data"
    data_dir.mkdir(parents=True)
    # repo_root resolves to tmp_path (public/.parent.parent); ensure no seed file there.
    (data_dir / "AGENTS.md").write_text("Endpoint: 10.99.99.99\n", encoding="utf-8")

    manager = FileSystemPublicAssetManager()
    manager._public_dir = public_dir  # noqa: SLF001

    assert manager._check_public_privacy() == ["[ok] public-privacy"]  # noqa: SLF001


def test_public_privacy_gate_scans_root_agents_md(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Root-level AGENTS.md (sibling of the package dir) is included in the scan."""
    _seed_denylist(monkeypatch, tmp_path)
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
    assert _load_privacy_denylist(tmp_path) == (("foo", "reason-a"), ("bar", "reason-b"))


def test_load_denylist_list_of_strings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "d.json"
    source.write_text(json.dumps(["alpha", "beta"]), encoding="utf-8")
    monkeypatch.setenv(_PRIVACY_DENYLIST_ENV, str(source))
    assert _load_privacy_denylist(tmp_path) == (
        ("alpha", "private identifier"),
        ("beta", "private identifier"),
    )


def test_load_denylist_malformed_json_returns_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "d.json"
    source.write_text("{not valid json", encoding="utf-8")
    monkeypatch.setenv(_PRIVACY_DENYLIST_ENV, str(source))
    assert _load_privacy_denylist(tmp_path) == ()


def test_load_denylist_missing_sources_returns_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(_PRIVACY_DENYLIST_ENV, str(tmp_path / "nope.json"))
    assert _load_privacy_denylist(tmp_path) == ()


def test_load_denylist_env_takes_precedence_over_repo_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = tmp_path / "repo"
    states = repo_root / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "privacy_denylist.json").write_text(
        json.dumps([["from-file", "file"]]), encoding="utf-8"
    )
    env_src = tmp_path / "env.json"
    env_src.write_text(json.dumps([["from-env", "env"]]), encoding="utf-8")
    monkeypatch.setenv(_PRIVACY_DENYLIST_ENV, str(env_src))
    assert _load_privacy_denylist(repo_root) == (("from-env", "env"),)


def test_load_denylist_falls_back_to_repo_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(_PRIVACY_DENYLIST_ENV, raising=False)
    repo_root = tmp_path / "repo"
    states = repo_root / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "privacy_denylist.json").write_text(
        json.dumps([["from-file", "file"]]), encoding="utf-8"
    )
    assert _load_privacy_denylist(repo_root) == (("from-file", "file"),)
