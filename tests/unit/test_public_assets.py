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


#: SPEC v0.4.2 FR10/GRILL P15/D9, bug push-gate-refuses-its-own-privacy-baseline-
#: fixtures — the two cross-platform home-path positive fixtures were originally
#: dedicated, tracked fixture files under tests/fixtures/privacy_baseline/. A
#: positive fixture must carry a value its own pattern matches, which means a NEW
#: blob at a NEW path on first publication — the prior-published-term amnesty grants
#: it nothing, so the real push-range denylist scan refused them (registered bug
#: push-gate-refuses-its-own-privacy-baseline-fixtures, HIGH). Root-cause fix:
#: compose each literal at RUNTIME so it is never contiguous in this module's own
#: tracked source — the same technique test_repo_self_scan.py::_archive_fixture_literal
#: already uses for its own archive fixture. This also removes the earlier reason for
#: separate files (denylist_scan.scan_objects reports at most one hit per scanned
#: object, so a literal inlined here could be masked by the pre-existing
#: ipv4-literal hit from _TEST_TERM above) — a runtime-composed literal never
#: reaches the tracked blob at all, so there is nothing left to mask or to hit.
def _macos_home_literal() -> str:
    """The bare ``users-abs-path`` positive literal, composed at runtime (never
    contiguous in this module's own tracked source)."""
    return "/Users/" + "zz-fixture-user"


def _windows_home_literal() -> str:
    """The bare ``windows-users-path`` positive literal, composed at runtime (never
    contiguous in this module's own tracked source)."""
    return "C:\\Users\\" + "zz-fixture-user"


def _macos_home_path_fixture() -> str:
    """Synthetic positive fixture for the ``users-abs-path`` baseline pattern
    (macOS) — content identical to the retired ``macos_home_path.txt`` fixture."""
    home = _macos_home_literal()
    return (
        "SPEC v0.4.2 FR10/GRILL P15/D9 -- synthetic positive fixture for the users-abs-path\n"
        "baseline pattern (macOS). The name below is synthetic and non-identifying.\n"
        f"backup at {home}/Documents\n"
    )


def _windows_home_path_fixture() -> str:
    """Synthetic positive fixture for the ``windows-users-path`` baseline pattern
    (Windows) — content identical to the retired ``windows_home_path.txt`` fixture,
    including the CR-2 mid-sentence prose form (a hit not only at a trailing path
    separator/end-of-line, proven again in isolation by
    :func:`test_windows_users_path_pattern_fires_in_prose_form_parity_with_posix_patterns`)."""
    home = _windows_home_literal()
    return (
        "SPEC v0.4.2 FR10/GRILL P15/D9 -- synthetic positive fixture for the windows-users-path\n"
        "baseline pattern (Windows). The name below is synthetic and non-identifying.\n"
        f"backup at {home}\\Documents\n"
        "CR-2 remediation (v0.4.2 code review) -- the same path also fires in prose, not only\n"
        f"when followed by a path separator or end of line: seen at {home} in\n"
        "running text with more words after it.\n"
    )


@pytest.mark.parametrize(
    ("name", "content", "expect_fragment"),
    [
        ("planted_ip", "Endpoint: 10.99.99.99\n", "10.99.99.99"),
        ("internal_hostname", "host: bastion.internal\n", "bastion.internal"),
        (
            "macos_users_path",
            _macos_home_path_fixture(),
            _macos_home_literal(),
        ),
        (
            "windows_users_path",
            _windows_home_path_fixture(),
            _windows_home_literal(),
        ),
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

    report = [line.render() for line in _manager(public_dir)._check_public_privacy()]  # noqa: SLF001
    assert any(line.startswith("[error] public-privacy:") for line in report)
    assert any(expect_fragment in line for line in report)


# ---------------------------------------------------------------------------
# SPEC v0.4.2 FR10/GRILL P15/A10.1 — the cross-platform home-path patterns never flag
# their own documented placeholder forms, on any of the three declared-support
# platforms (Linux /home, macOS /Users, Windows C:\Users).
# ---------------------------------------------------------------------------


def test_baseline_never_flags_placeholder_home_paths_on_any_declared_platform(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Intent: CONTRACT — v0.4.2 A10.1.

    (negative case): /home/username (existing), /Users/username (macOS, new),
    and C:\\Users\\username (Windows, new) are all documented placeholder forms and
    must never fire — a clean fixture reports only the baseline OK marker. CR-2
    remediation (v0.4.2 code review MEDIUM) strengthens this fixture with the BARE
    prose form (no trailing path separator) for the Windows placeholder, so the
    negative case is proven in the same mid-sentence shape CR-2's positive case
    exercises — not only the trailing-`\\AppData` form the widened lookahead was
    never at risk of over-matching."""
    _disable_operator_denylist(monkeypatch, tmp_path)
    public_dir = tmp_path / "public"
    (public_dir / "data").mkdir(parents=True)
    (public_dir / "data" / "AGENTS.md").write_text(
        "see /home/username/.config, /Users/username/Library, and C:\\Users\\username\\AppData\n"
        "the same directory is also written in prose as C:\\Users\\username here.\n",
        encoding="utf-8",
    )
    assert _manager(public_dir)._check_public_privacy() == [_BASELINE_OK_MARKER]  # noqa: SLF001


# ---------------------------------------------------------------------------
# SPEC v0.4.2 CR-2 (code-reviewer MEDIUM) — the windows-users-path pattern must share
# the SAME trailing-lookahead parity home-abs-path/users-abs-path already have: a hit
# followed by a path separator, a word boundary (mid-sentence prose), OR end of line.
# Pre-fix, the pattern's `(?=\\|$)` lookahead fired ONLY on a trailing backslash or
# end-of-line — missing the most common leak shape, an operator-local Windows path
# written inline in a sentence.
# ---------------------------------------------------------------------------

# Intent: CONTRACT — v0.4.2 CR-2


def test_windows_users_path_pattern_fires_in_prose_form_parity_with_posix_patterns() -> None:
    """Root-cause proof at the regex level (not only through the doctor plumbing):
    the `windows-users-path` pattern must fire on the prose (mid-sentence) form the
    same way `home-abs-path`/`users-abs-path` already do, and the documented
    placeholder form must still be excluded in that SAME prose shape."""
    patterns = {p.id: p for p in _load_privacy_baseline()}
    windows_pattern = patterns["windows-users-path"]

    prose = "backup lives at C:\\Users\\zz-fixture-user and more prose follows"
    match = windows_pattern.regex.search(prose)
    assert match is not None, (
        "the pattern must fire on the prose (mid-sentence) form, not only when "
        "followed by a path separator or end of line"
    )
    assert match.group(0) == "C:\\Users\\zz-fixture-user"

    placeholder_prose = "backup lives at C:\\Users\\username and more prose follows"
    placeholder_match = windows_pattern.regex.search(placeholder_prose)
    assert placeholder_match is not None
    assert windows_pattern.exclude is not None
    assert windows_pattern.exclude.search(placeholder_match.group(0)), (
        "the documented placeholder form must still be excluded even in prose"
    )


def test_windows_users_path_prose_form_fires_through_the_doctor_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """End-to-end confirmation through ``_check_public_privacy`` (not only the bare
    regex): the prose form is reported as a genuine finding, same as the trailing-
    separator form already was."""
    _disable_operator_denylist(monkeypatch, tmp_path)
    public_dir = tmp_path / "public"
    (public_dir / "data").mkdir(parents=True)
    (public_dir / "data" / "AGENTS.md").write_text(
        "backup lives at C:\\Users\\zz-fixture-user and more prose follows in the line\n",
        encoding="utf-8",
    )
    report = [line.render() for line in _manager(public_dir)._check_public_privacy()]  # noqa: SLF001
    assert any(line.startswith("[error] public-privacy:") for line in report)
    assert any("C:\\Users\\zz-fixture-user" in line for line in report)


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

    report = [line.render() for line in _manager(public_dir)._check_public_privacy()]  # noqa: SLF001
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

    report = [line.render() for line in _manager(public_dir)._check_public_privacy()]  # noqa: SLF001
    assert any(line.startswith("[error] public-privacy:") for line in report)
    assert any(_TEST_TERM in line.lower() for line in report)

    # Root-level AGENTS.md (sibling of the package dir) is included in the scan.
    repo_root = tmp_path / "repo"
    repo_public_dir = repo_root / "dadaia_workspace" / "public"
    repo_public_dir.mkdir(parents=True)
    (repo_root / "AGENTS.md").write_text(f"host: {_TEST_TERM}\n", encoding="utf-8")
    root_report = [  # noqa: SLF001
        line.render() for line in _manager(repo_public_dir)._check_public_privacy()
    ]
    assert any("AGENTS.md" in line and _TEST_TERM in line.lower() for line in root_report)


def test_bytecode_cache_ignored_and_baseline_data_loads_with_version_header(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_denylist_env(monkeypatch, tmp_path)
    public_dir = tmp_path / "public"
    cache_dir = public_dir / "skills" / "sample" / "__pycache__"
    cache_dir.mkdir(parents=True)
    (cache_dir / "leak.pyc").write_bytes(_TEST_TERM.encode())
    (public_dir / "data").mkdir()
    (public_dir / "data" / "AGENTS.md").write_text("# clean\n", encoding="utf-8")

    assert [  # noqa: SLF001
        line.render() for line in _manager(public_dir)._check_public_privacy()
    ] == ["[ok] public-privacy"]

    # Packaged baseline data ships with a versioned, documented header.
    patterns = _load_privacy_baseline()
    assert patterns, "baseline must ship at least one structural pattern"
    ids = {p.id for p in patterns}
    assert {
        "ipv4-literal",
        "internal-hostname",
        "home-abs-path",
        "users-abs-path",
        "windows-users-path",
        "email-address",
    } <= ids


# ---------------------------------------------------------------------------
# SPEC v0.4.2 FR10/A10.2/A10.4 — baseline v5: every pattern stays single-line, the
# header version reads 5, and _header.excludes documents the new carve-outs and the
# /root boundary (D10).
# ---------------------------------------------------------------------------


def test_baseline_v5_header_and_single_line_patterns() -> None:
    """Intent: CONTRACT — v0.4.2 A10.2, A10.4."""
    import importlib.resources
    import json as _json

    resource = (
        importlib.resources.files("dadaia_workspace.infrastructure.data") / "privacy_baseline.json"
    )
    raw = _json.loads(resource.read_text(encoding="utf-8"))

    assert raw["_header"]["version"] == 5
    excludes_text = " ".join(raw["_header"]["excludes"])
    assert "/root" in excludes_text
    assert "Users" in excludes_text

    for pattern in raw["patterns"]:
        assert "\n" not in pattern["regex"], f"{pattern['id']}: regex must be single-line"
        if pattern.get("exclude_regex"):
            assert "\n" not in pattern["exclude_regex"], (
                f"{pattern['id']}: exclude_regex must be single-line"
            )


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

    if name == "dict_format":
        # Malformed JSON, a missing source path, and neither env nor workspace present
        # all resolve to an empty tuple (fail-open on the loader side, never a crash).
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
