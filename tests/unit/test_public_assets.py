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

from dadaia_workspace.infrastructure.privacy_check import (
    _BASELINE_OK_MARKER,
    _PRIVACY_DENYLIST_ENV,
    _load_privacy_baseline,
    _load_privacy_denylist,
)
from dadaia_workspace.infrastructure.public_assets import (
    FileSystemPublicAssetManager,
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


def _disable_operator_denylist(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Ensure no operator denylist resolves (env unset + chdir outside any workspace)."""
    monkeypatch.delenv(_PRIVACY_DENYLIST_ENV, raising=False)
    no_ws = tmp_path / "no_workspace"
    no_ws.mkdir(exist_ok=True)
    monkeypatch.chdir(no_ws)


def test_baseline_flags_planted_ip_when_no_operator_denylist(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fail-closed: absent operator denylist still runs the baseline structural scan."""
    _disable_operator_denylist(monkeypatch, tmp_path)
    public_dir = tmp_path / "public"
    data_dir = public_dir / "data"
    data_dir.mkdir(parents=True)
    (data_dir / "AGENTS.md").write_text("Endpoint: 10.99.99.99\n", encoding="utf-8")

    manager = FileSystemPublicAssetManager()
    manager._public_dir = public_dir  # noqa: SLF001

    report = manager._check_public_privacy()  # noqa: SLF001
    assert any(line.startswith("[error] public-privacy:") for line in report)
    assert any("10.99.99.99" in line for line in report)


def test_baseline_flags_internal_hostname(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _disable_operator_denylist(monkeypatch, tmp_path)
    public_dir = tmp_path / "public"
    data_dir = public_dir / "data"
    data_dir.mkdir(parents=True)
    (data_dir / "AGENTS.md").write_text("host: bastion.internal\n", encoding="utf-8")

    manager = FileSystemPublicAssetManager()
    manager._public_dir = public_dir  # noqa: SLF001

    report = manager._check_public_privacy()  # noqa: SLF001
    assert any("bastion.internal" in line for line in report)


def test_baseline_clean_fixture_reports_ok_with_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Clean public/ + no operator denylist ⇒ [ok] with the baseline-scan marker."""
    _disable_operator_denylist(monkeypatch, tmp_path)
    public_dir = tmp_path / "public"
    data_dir = public_dir / "data"
    data_dir.mkdir(parents=True)
    (data_dir / "AGENTS.md").write_text("# clean generic content\n", encoding="utf-8")

    manager = FileSystemPublicAssetManager()
    manager._public_dir = public_dir  # noqa: SLF001

    assert manager._check_public_privacy() == [_BASELINE_OK_MARKER]  # noqa: SLF001


def test_baseline_does_not_flag_loopback_or_doc_ranges(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Loopback (127.x / ::1 / 0.0.0.0) and RFC-5737 doc ranges must NOT be flagged."""
    _disable_operator_denylist(monkeypatch, tmp_path)
    public_dir = tmp_path / "public"
    data_dir = public_dir / "data"
    data_dir.mkdir(parents=True)
    (data_dir / "AGENTS.md").write_text(
        "bind 127.0.0.1 and 0.0.0.0; doc 192.0.2.10 / 203.0.113.5; v6 ::1\n",
        encoding="utf-8",
    )

    manager = FileSystemPublicAssetManager()
    manager._public_dir = public_dir  # noqa: SLF001

    assert manager._check_public_privacy() == [_BASELINE_OK_MARKER]  # noqa: SLF001


def test_baseline_does_not_flag_sha_hash_in_lockfile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Conservative: a 64-hex SHA in a lockfile must not trip the secret-token pattern."""
    _disable_operator_denylist(monkeypatch, tmp_path)
    public_dir = tmp_path / "public"
    data_dir = public_dir / "data"
    data_dir.mkdir(parents=True)
    sha = "a" * 64
    (data_dir / "lock.json").write_text(f'{{"hash": "sha256:{sha}"}}\n', encoding="utf-8")

    manager = FileSystemPublicAssetManager()
    manager._public_dir = public_dir  # noqa: SLF001

    assert manager._check_public_privacy() == [_BASELINE_OK_MARKER]  # noqa: SLF001


def test_operator_denylist_merges_additive_over_baseline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Operator terms are ADDITIVE: both an operator term and a baseline pattern fire."""
    _seed_denylist_env(monkeypatch, tmp_path)  # operator term = "10.99.99.99"
    public_dir = tmp_path / "public"
    data_dir = public_dir / "data"
    data_dir.mkdir(parents=True)
    # operator term + a baseline-only hit (internal hostname)
    (data_dir / "AGENTS.md").write_text(f"ip {_TEST_TERM}\nhost db.internal\n", encoding="utf-8")

    manager = FileSystemPublicAssetManager()
    manager._public_dir = public_dir  # noqa: SLF001

    report = manager._check_public_privacy()  # noqa: SLF001
    assert any(_TEST_TERM in line for line in report)
    assert any("db.internal" in line for line in report)


def test_baseline_data_loads_with_version_header() -> None:
    """Packaged baseline data ships with a versioned, documented header."""
    patterns = _load_privacy_baseline()
    assert patterns, "baseline must ship at least one structural pattern"
    ids = {p.id for p in patterns}
    assert {"ipv4-literal", "internal-hostname", "home-abs-path", "email-address"} <= ids


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
