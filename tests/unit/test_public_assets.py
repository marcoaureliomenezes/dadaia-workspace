"""Pure unit tests for public asset privacy checks.

The privacy denylist is operator-private and loaded at runtime from outside the
published package (env var ``DADAIA_PRIVACY_DENYLIST`` or
``<workspace_root>/.dadaia/states/privacy_denylist.json``). The shipped library
carries no private identifiers, so these tests seed their own terms.

CRIT public-privacy gate (the repo went public and was reverted for an infra leak
once — never weaken). The fail-closed baseline (no operator denylist) and the
false-block law (loopback / RFC-5737 doc ranges never flagged) are kept standalone.
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


def _disable_operator_denylist(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Ensure no operator denylist resolves (env unset + chdir outside any workspace)."""
    monkeypatch.delenv(_PRIVACY_DENYLIST_ENV, raising=False)
    no_ws = tmp_path / "no_workspace"
    no_ws.mkdir(exist_ok=True)
    monkeypatch.chdir(no_ws)


def _manager(public_dir: Path) -> FileSystemPublicAssetManager:
    manager = FileSystemPublicAssetManager()
    manager._public_dir = public_dir  # noqa: SLF001
    return manager


# ---------------------------------------------------------------------------
# CRIT: fail-closed baseline with NO operator denylist.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "content", "expect_fragment"),
    [
        ("planted_ip", "Endpoint: 10.99.99.99\n", "10.99.99.99"),
        ("internal_hostname", "host: bastion.internal\n", "bastion.internal"),
    ],
)
def test_baseline_fires_with_no_operator_denylist(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str, content: str, expect_fragment: str
) -> None:
    """Fail-closed: absent operator denylist still runs the baseline structural scan."""
    _disable_operator_denylist(monkeypatch, tmp_path)
    public_dir = tmp_path / "public"
    data_dir = public_dir / "data"
    data_dir.mkdir(parents=True)
    (data_dir / "AGENTS.md").write_text(content, encoding="utf-8")

    report = _manager(public_dir)._check_public_privacy()  # noqa: SLF001
    assert any(line.startswith("[error] public-privacy:") for line in report)
    assert any(expect_fragment in line for line in report)


# ---------------------------------------------------------------------------
# CRIT: false-block law — loopback / RFC-5737 doc ranges / SHA-in-lockfile never
# flagged.
# ---------------------------------------------------------------------------


def test_baseline_never_flags_loopback_doc_ranges_or_lockfile_sha(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Loopback (127.x / ::1 / 0.0.0.0), RFC-5737 doc ranges, and a 64-hex SHA in a
    lockfile must NOT be flagged — a clean fixture also reports [ok] with the marker."""
    _disable_operator_denylist(monkeypatch, tmp_path)

    ranges_dir = tmp_path / "public"
    (ranges_dir / "data").mkdir(parents=True)
    (ranges_dir / "data" / "AGENTS.md").write_text(
        "bind 127.0.0.1 and 0.0.0.0; doc 192.0.2.10 / 203.0.113.5; v6 ::1\n",
        encoding="utf-8",
    )
    assert _manager(ranges_dir)._check_public_privacy() == [_BASELINE_OK_MARKER]  # noqa: SLF001

    lockfile_dir = tmp_path / "public-lock"
    (lockfile_dir / "data").mkdir(parents=True)
    sha = "a" * 64
    (lockfile_dir / "data" / "lock.json").write_text(
        f'{{"hash": "sha256:{sha}"}}\n', encoding="utf-8"
    )
    assert _manager(lockfile_dir)._check_public_privacy() == [_BASELINE_OK_MARKER]  # noqa: SLF001

    clean_dir = tmp_path / "public-clean"
    (clean_dir / "data").mkdir(parents=True)
    (clean_dir / "data" / "AGENTS.md").write_text("# clean generic content\n", encoding="utf-8")
    assert _manager(clean_dir)._check_public_privacy() == [_BASELINE_OK_MARKER]  # noqa: SLF001


# ---------------------------------------------------------------------------
# CRIT: operator terms are ADDITIVE over the baseline.
# ---------------------------------------------------------------------------


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

    report = _manager(public_dir)._check_public_privacy()  # noqa: SLF001
    assert any(_TEST_TERM in line for line in report)
    assert any("db.internal" in line for line in report)


# ---------------------------------------------------------------------------
# Scan-scope + no-false-positive parametrized table.
# ---------------------------------------------------------------------------


def test_text_denylist_flags_and_scans_root_agents_md(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_denylist_env(monkeypatch, tmp_path)
    public_dir = tmp_path / "public"
    data_dir = public_dir / "data"
    data_dir.mkdir(parents=True)
    (data_dir / "AGENTS.md").write_text(f"Private endpoint: {_TEST_TERM}\n", encoding="utf-8")

    report = _manager(public_dir)._check_public_privacy()  # noqa: SLF001
    assert any(line.startswith("[error] public-privacy:") for line in report)
    assert any(_TEST_TERM in line.lower() for line in report)

    # Root-level AGENTS.md (sibling of the package dir) is included in the scan.
    repo_root = tmp_path / "repo"
    repo_public_dir = repo_root / "dadaia_workspace" / "public"
    repo_public_dir.mkdir(parents=True)
    (repo_root / "AGENTS.md").write_text(f"host: {_TEST_TERM}\n", encoding="utf-8")
    root_report = _manager(repo_public_dir)._check_public_privacy()  # noqa: SLF001
    assert any("AGENTS.md" in line and _TEST_TERM in line.lower() for line in root_report)


def test_bytecode_cache_ignored(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _seed_denylist_env(monkeypatch, tmp_path)
    public_dir = tmp_path / "public"
    cache_dir = public_dir / "skills" / "sample" / "__pycache__"
    cache_dir.mkdir(parents=True)
    (cache_dir / "leak.pyc").write_bytes(_TEST_TERM.encode())
    (public_dir / "data").mkdir()
    (public_dir / "data" / "AGENTS.md").write_text("# clean\n", encoding="utf-8")

    assert _manager(public_dir)._check_public_privacy() == ["[ok] public-privacy"]  # noqa: SLF001


def test_baseline_data_loads_with_version_header() -> None:
    """Packaged baseline data ships with a versioned, documented header."""
    patterns = _load_privacy_baseline()
    assert patterns, "baseline must ship at least one structural pattern"
    ids = {p.id for p in patterns}
    assert {"ipv4-literal", "internal-hostname", "home-abs-path", "email-address"} <= ids


# --- _load_privacy_denylist loader contract -------------------------------


@pytest.mark.parametrize(
    ("name", "payload", "expected"),
    [
        (
            "dict_format",
            {"foo": "reason-a", "bar": "reason-b"},
            (("foo", "reason-a"), ("bar", "reason-b")),
        ),
        (
            "list_of_strings",
            ["alpha", "beta"],
            (("alpha", "private identifier"), ("beta", "private identifier")),
        ),
    ],
)
def test_load_denylist_source_formats(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str, payload: object, expected: tuple
) -> None:
    source = tmp_path / "d.json"
    source.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setenv(_PRIVACY_DENYLIST_ENV, str(source))
    assert _load_privacy_denylist() == expected


def test_load_denylist_returns_empty_when_unresolvable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Malformed JSON, a missing source path, and neither env nor workspace present all
    resolve to an empty tuple (fail-open on the loader side, never a crash)."""
    no_ws = tmp_path / "no_workspace"
    no_ws.mkdir()

    malformed = tmp_path / "malformed.json"
    malformed.write_text("{not valid json", encoding="utf-8")
    monkeypatch.setenv(_PRIVACY_DENYLIST_ENV, str(malformed))
    monkeypatch.chdir(no_ws)
    assert _load_privacy_denylist() == ()

    monkeypatch.setenv(_PRIVACY_DENYLIST_ENV, str(tmp_path / "nope.json"))
    monkeypatch.chdir(no_ws)
    assert _load_privacy_denylist() == ()

    monkeypatch.delenv(_PRIVACY_DENYLIST_ENV, raising=False)
    monkeypatch.chdir(no_ws)
    assert _load_privacy_denylist() == ()


def test_load_denylist_env_precedence_and_workspace_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Env var takes precedence over the workspace file; when env is absent the
    workspace file at <workspace_root>/.dadaia/states/ is used."""
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

    monkeypatch.delenv(_PRIVACY_DENYLIST_ENV, raising=False)
    assert _load_privacy_denylist() == (("from-file", "file"),)
