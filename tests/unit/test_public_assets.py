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
# Bug privacy-baseline-noreply-local-part-not-carved-out (HIGH, security-reviewer
# handoff 2026-08-17T143407Z-security-reviewer-v0.4.3-definition-push) — SPEC v0.4.3
# FR12/A12.2. The v5 email-address exclude_regex was anchored on the DOTTED no-reply
# subdomain only (e.g. the vendor's and GitHub's no-reply subdomains) and never carved
# out the LOCAL-PART form DADAIA.md mandates in every commit's Co-Authored-By trailer
# (local part 'noreply' at the vendor's bare apex domain) — a public, non-identifying
# vendor mailbox already published unmasked in thousands of this repo's own commit
# trailers. Any NEW tracked blob quoting it in prose (a release SPEC/TASKS document)
# was therefore refused by the push-range denylist scan. A12.2 pairs the fix with a
# counter-fixture: the carve-out must stay anchored to the EXACT address, never to the
# bare domain or to a 'noreply@' local part independent of domain (either would exempt
# an entire real mail domain, or every noreply@<anything>, respectively).
#
# Both literals are composed at RUNTIME, never contiguous in this module's own tracked
# source — the same technique already used above (_macos_home_literal/
# _windows_home_literal, bug push-gate-refuses-its-own-privacy-baseline-fixtures) and
# in test_repo_self_scan.py::_archive_fixture_literal.
# ---------------------------------------------------------------------------


def _mandated_noreply_trailer_address() -> str:
    """The exact law-mandated Co-Authored-By trailer address (DADAIA.md), composed at
    runtime so it never appears contiguously in this module's own tracked source."""
    local_part = "no" + "reply"
    domain = "anthropic" + "." + "com"
    return f"{local_part}@{domain}"


def _different_local_part_at_the_mandated_domain() -> str:
    """A genuine, DIFFERENT local part at the SAME apex domain — must still fire,
    proving the carve-out stays anchored to the exact address rather than the bare
    domain. Composed at runtime for the same reason as above."""
    local_part = "someone" + "else"
    domain = "anthropic" + "." + "com"
    return f"{local_part}@{domain}"


def test_email_address_pattern_excludes_the_mandated_noreply_trailer_address() -> None:
    """Intent: CONTRACT — privacy-baseline-noreply-local-part-not-carved-out (HIGH).

    Root-cause proof at the regex level (not only through the doctor plumbing): the
    exact law-mandated trailer address must both match the email-address SHAPE (it is
    a genuine email token) and be excluded by exclude_regex (it is a carved-out,
    non-identifying vendor mailbox)."""
    address = _mandated_noreply_trailer_address()
    patterns = {p.id: p for p in _load_privacy_baseline()}
    email_pattern = patterns["email-address"]

    match = email_pattern.regex.search(address)
    assert match is not None, "the address must still match the email-address SHAPE"
    assert match.group(0) == address

    assert email_pattern.exclude is not None
    assert email_pattern.exclude.search(match.group(0)), (
        "the exact law-mandated trailer address must be carved out by exclude_regex"
    )


def test_email_address_pattern_still_fires_for_a_different_local_part_at_the_mandated_domain() -> (
    None
):
    """Intent: CONTRACT — v0.4.3 A12.2 counter-fixture. The carve-out is anchored to
    the EXACT address, never the bare domain: a genuine mailbox at the same apex
    domain, with a DIFFERENT local part, must still be flagged."""
    address = _different_local_part_at_the_mandated_domain()
    patterns = {p.id: p for p in _load_privacy_baseline()}
    email_pattern = patterns["email-address"]

    match = email_pattern.regex.search(address)
    assert match is not None
    assert match.group(0) == address

    assert email_pattern.exclude is not None
    assert not email_pattern.exclude.search(match.group(0)), (
        "a different local part at the same domain must NOT be excluded"
    )


def test_baseline_excludes_the_mandated_noreply_trailer_address_through_the_doctor_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """End-to-end confirmation through ``_check_public_privacy`` (not only the bare
    regex): a document that merely quotes the law-mandated trailer address in prose
    reports clean — no ``[error]`` line."""
    _disable_operator_denylist(monkeypatch, tmp_path)
    address = _mandated_noreply_trailer_address()
    public_dir = tmp_path / "public"
    (public_dir / "data").mkdir(parents=True)
    (public_dir / "data" / "AGENTS.md").write_text(
        f"every commit trailer names Co-Authored-By: Claude Fable 5 <{address}>\n",
        encoding="utf-8",
    )
    assert _manager(public_dir)._check_public_privacy() == [_BASELINE_OK_MARKER]  # noqa: SLF001


def test_baseline_still_flags_a_different_local_part_at_the_mandated_domain_through_the_doctor_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Negative twin, end-to-end: a genuine mailbox at the same apex domain with a
    DIFFERENT local part is still reported as a genuine finding."""
    _disable_operator_denylist(monkeypatch, tmp_path)
    address = _different_local_part_at_the_mandated_domain()
    public_dir = tmp_path / "public"
    (public_dir / "data").mkdir(parents=True)
    (public_dir / "data" / "AGENTS.md").write_text(
        f"contact {address} for support\n", encoding="utf-8"
    )

    report = [line.render() for line in _manager(public_dir)._check_public_privacy()]  # noqa: SLF001
    assert any(line.startswith("[error] public-privacy:") for line in report)
    assert any(address in line for line in report)


# ---------------------------------------------------------------------------
# Bug reconciliation-merge-body-scan-unamendable-main-squash (HIGH, security-reviewer
# handoff 2026-08-18T041422Z-security-reviewer-v0.4.3-ship-push-r4). The FR6
# reconciliation merge of origin/main into develop, mandatory after every squash-merge
# to main, publishes ZERO blobs and TWO path-less commit objects; the v0.4.3 commit-body
# scan layer refused main's already-published GitHub squash-merge commit because its
# 115 KB body quotes two synthetic /home/<name> literals from code-reviewer's own
# v0.11.0 pre-PR review prose (describing the FR1 substring-amnesty repro) — literals
# that were, AT THE TIME OF THAT REVIEW, the exact values
# tests/unit/features/chokepoints/test_denylist_scan.py's
# _POSITIVE_HOME_PATH_SUPERSTRING/_POSITIVE_HOME_PATH_SUBSTRING fixtures used
# ("synthxabcd"/"synthxa"). A body hit on an already-published, GitHub-authored commit
# has no applicable remedy (amend would rewrite published main history; a body match
# carries no path, so the path-based amnesty can never suppress it) — the only
# root-cause fix is to carve the exact historical literals out of the home-abs-path
# exclude_regex. Both literals must be carved out: scan_objects reports at most one Hit
# per object (first match by ascending line), so excluding only the longer literal
# would merely shift the refusal to the shorter one quoted one line later in the same
# body. Note: test_denylist_scan.py's fixtures have SINCE been renamed to a different
# synthetic pair precisely so this new carve-out does not silently suppress THEIR
# regression coverage (its own module docstring explains why) — the two variables
# below hold the frozen, historical literal VALUES, not a live cross-reference to that
# file's current fixture values.
# ---------------------------------------------------------------------------


def _reconciliation_fixture_home_literal() -> str:
    """The longer of the two synthetic fixture literals quoted in main's already-
    published squash-commit body (code-reviewer's v0.11.0 pre-PR review prose) —
    composed at runtime so it never appears contiguously in this module's own tracked
    source. This is the frozen historical value
    test_denylist_scan.py's ``_POSITIVE_HOME_PATH_SUPERSTRING`` held at review time —
    that file has since been renamed to a different pair (see its module comment)."""
    return "/hom" + "e/synth" + "xabcd"


def _reconciliation_fixture_home_substring_literal() -> str:
    """The shorter, substring sibling literal quoted one line later in the SAME
    squash-commit body prose. This is the frozen historical value
    test_denylist_scan.py's ``_POSITIVE_HOME_PATH_SUBSTRING`` held at review time.
    Composed at runtime for the same reason as above."""
    return "/hom" + "e/synth" + "xa"


def _different_realistic_home_path_literal() -> str:
    """A realistic-shaped ``/home/<name>`` that is NOT one of the carved-out synthetic
    fixture literals — must still fire, proving the carve-out stays anchored to the
    exact synthetic names rather than a broad ``/home/*`` relaxation. Composed at
    runtime for convention parity with the rest of this file (this particular literal
    is not on any carve-out list, so the composition is not load-bearing here, only
    consistent)."""
    return "/hom" + "e/jdoe42"


def test_home_abs_path_pattern_excludes_the_reconciliation_bug_synthetic_fixture_literals() -> None:
    """Intent: CONTRACT — reconciliation-merge-body-scan-unamendable-main-squash (HIGH).

    Root-cause proof at the regex level (not only through the doctor plumbing): BOTH
    synthetic fixture literals quoted in main's already-published squash-commit body
    must match the home-abs-path SHAPE (they are genuine /home/<name> tokens) AND be
    excluded by exclude_regex — carving out only the longer literal would leave
    scan_objects' first-hit-per-object semantics reporting the substring sibling on the
    very next line instead."""
    patterns = {p.id: p for p in _load_privacy_baseline()}
    home_pattern = patterns["home-abs-path"]

    for literal in (
        _reconciliation_fixture_home_literal(),
        _reconciliation_fixture_home_substring_literal(),
    ):
        match = home_pattern.regex.search(literal)
        assert match is not None, f"{literal!r} must still match the home-abs-path SHAPE"
        assert match.group(0) == literal
        assert home_pattern.exclude is not None
        assert home_pattern.exclude.search(match.group(0)), (
            f"{literal!r} is a synthetic, non-identifying fixture literal and must be "
            "carved out by exclude_regex"
        )


def test_home_abs_path_pattern_still_fires_for_a_different_realistic_name() -> None:
    """Intent: CONTRACT — regression counter-fixture for the bug above. The carve-out is
    anchored to the exact synthetic fixture names, never a broader /home/* relaxation: a
    realistic, non-carved-out /home/<name> must still be flagged."""
    literal = _different_realistic_home_path_literal()
    patterns = {p.id: p for p in _load_privacy_baseline()}
    home_pattern = patterns["home-abs-path"]

    match = home_pattern.regex.search(literal)
    assert match is not None
    assert match.group(0) == literal
    assert home_pattern.exclude is not None
    assert not home_pattern.exclude.search(match.group(0)), (
        "a realistic, non-carved-out /home/<name> must NOT be excluded"
    )


def test_baseline_excludes_the_reconciliation_bug_synthetic_fixtures_through_the_doctor_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """End-to-end confirmation through ``_check_public_privacy`` (not only the bare
    regex): a document quoting both synthetic fixture literals in the SAME prose shape
    as main's squash-commit body reports clean — no ``[error]`` line."""
    _disable_operator_denylist(monkeypatch, tmp_path)
    literal_a = _reconciliation_fixture_home_literal()
    literal_b = _reconciliation_fixture_home_substring_literal()
    public_dir = tmp_path / "public"
    (public_dir / "data").mkdir(parents=True)
    (public_dir / "data" / "AGENTS.md").write_text(
        f'substrings (repro: prior "{literal_a}" suppressed a new standalone\n'
        f'"{literal_b}"; prior superstring amnesty test prose continues here).\n',
        encoding="utf-8",
    )
    assert _manager(public_dir)._check_public_privacy() == [_BASELINE_OK_MARKER]  # noqa: SLF001


def test_baseline_still_flags_a_different_realistic_home_path_through_the_doctor_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Negative twin, end-to-end: a realistic, non-carved-out /home/<name> is still
    reported as a genuine finding — the carve-out did not relax the pattern broadly."""
    _disable_operator_denylist(monkeypatch, tmp_path)
    literal = _different_realistic_home_path_literal()
    public_dir = tmp_path / "public"
    (public_dir / "data").mkdir(parents=True)
    (public_dir / "data" / "AGENTS.md").write_text(
        f"backup lives at {literal}/data\n", encoding="utf-8"
    )

    report = [line.render() for line in _manager(public_dir)._check_public_privacy()]  # noqa: SLF001
    assert any(line.startswith("[error] public-privacy:") for line in report)
    assert any(literal in line for line in report)


# ---------------------------------------------------------------------------
# SPEC v0.4.2 FR10/A10.2/A10.4 — baseline v6: every pattern stays single-line, the
# header version reads 6, and _header.excludes documents the new carve-outs and the
# /root boundary (D10).
# ---------------------------------------------------------------------------


def test_baseline_v7_header_and_single_line_patterns() -> None:
    """Intent: CONTRACT — v0.4.2 A10.2, A10.4; v0.4.3 A12.2 (version bump 5->6),
    A12.5 (version bump 6->7, single-line patterns, extended _header rationale);
    T-043-23 security-review rework (version bump 7->8, internal-hostname carve-out
    narrowed to the .home label class); bug
    reconciliation-merge-body-scan-unamendable-main-squash (version bump 8->9,
    home-abs-path carve-out for the product's own synthetic fixture usernames)."""
    import importlib.resources
    import json as _json

    resource = (
        importlib.resources.files("dadaia_workspace.infrastructure.data") / "privacy_baseline.json"
    )
    raw = _json.loads(resource.read_text(encoding="utf-8"))

    assert raw["_header"]["version"] == 9
    excludes_text = " ".join(raw["_header"]["excludes"])
    assert "/root" in excludes_text
    assert "Users" in excludes_text
    assert "FR12/A12.3" in excludes_text  # the trailing-period rationale, extended
    assert "FR12/A12.4" in excludes_text  # the dotted-chain structural rule, extended
    assert "reconciliation-merge-body-scan-unamendable-main-squash" in excludes_text

    for pattern in raw["patterns"]:
        assert "\n" not in pattern["regex"], f"{pattern['id']}: regex must be single-line"
        if pattern.get("exclude_regex"):
            assert "\n" not in pattern["exclude_regex"], (
                f"{pattern['id']}: exclude_regex must be single-line"
            )
            # A12.1/A12.5: every carve-out documents a single-line rationale.
            rationale = pattern.get("exclude_rationale")
            assert isinstance(rationale, str) and rationale.strip(), (
                f"{pattern['id']}: exclude_regex requires a non-empty exclude_rationale"
            )
            assert "\n" not in rationale, f"{pattern['id']}: exclude_rationale must be single-line"


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


# ═════════════════════════════════════════════════════════════════════════════════
# v0.4.3 T-043-16/FR12 — the privacy baseline stops growing literal by literal.
# Intent: CONTRACT — v0.4.3 A12.1, A12.3, A12.4 (A12.2 is verified above/at HEAD, not
# re-implemented — the rider already shipped it; A12.5/A12.6 are covered by the
# existing v6->v7 header/single-line test and the doctor [ok] assertions throughout
# this file).
# ═════════════════════════════════════════════════════════════════════════════════


def test_shipped_baseline_every_carve_out_carries_a_documented_rationale() -> None:
    """A12.1 (shipped-baseline half): every packaged pattern with an ``exclude_regex``
    carve-out documents WHY via ``exclude_rationale`` — the doctor/CI check (below)
    must find nothing to flag on the REAL, shipped baseline."""
    from dadaia_workspace.infrastructure.privacy_check import _check_baseline_exclude_rationale

    assert _check_baseline_exclude_rationale(_load_privacy_baseline()) == []
    carve_outs = [p for p in _load_privacy_baseline() if p.exclude is not None]
    assert carve_outs, "the shipped baseline must carry at least one carve-out"
    assert all(p.exclude_rationale and p.exclude_rationale.strip() for p in carve_outs)


def test_baseline_carve_out_missing_a_rationale_is_reported_by_the_doctor_check() -> None:
    """A12.1 (the check itself): a carve-out (``exclude_regex`` set) with NO
    ``exclude_rationale`` is flagged by name; a pattern with no carve-out at all needs
    no rationale and is never flagged."""
    import re as _re

    from dadaia_workspace.infrastructure.privacy_check import (
        _BaselinePattern,
        _check_baseline_exclude_rationale,
    )

    undocumented = _BaselinePattern(
        id="zz-fixture-undocumented",
        regex=_re.compile("x"),
        reason="fixture",
        exclude=_re.compile("y"),
        exclude_rationale=None,
    )
    blank_rationale = _BaselinePattern(
        id="zz-fixture-blank",
        regex=_re.compile("x"),
        reason="fixture",
        exclude=_re.compile("y"),
        exclude_rationale="   ",
    )
    documented = _BaselinePattern(
        id="zz-fixture-documented",
        regex=_re.compile("x"),
        reason="fixture",
        exclude=_re.compile("y"),
        exclude_rationale="a genuine, documented reason",
    )
    no_carve_out = _BaselinePattern(
        id="zz-fixture-no-carve-out",
        regex=_re.compile("x"),
        reason="fixture",
        exclude=None,
        exclude_rationale=None,
    )

    findings = _check_baseline_exclude_rationale(
        (undocumented, blank_rationale, documented, no_carve_out)
    )

    flagged_ids = {line.render() for line in findings}
    assert any("zz-fixture-undocumented" in line for line in flagged_ids)
    assert any("zz-fixture-blank" in line for line in flagged_ids)
    assert not any("zz-fixture-documented" in line for line in flagged_ids)
    assert not any("zz-fixture-no-carve-out" in line for line in flagged_ids)
    assert len(findings) == 2


def test_baseline_rationale_check_is_wired_into_the_public_privacy_doctor_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A12.1 doctor wiring: the rationale check runs as part of the SAME
    ``_check_public_privacy`` the operator already reads — a clean tree with the real
    shipped baseline still reports the plain [ok] line (no rationale finding leaks
    into a healthy run)."""
    _disable_operator_denylist(monkeypatch, tmp_path)
    public_dir = tmp_path / "public"
    (public_dir / "data").mkdir(parents=True)
    (public_dir / "data" / "AGENTS.md").write_text("# clean generic content\n", encoding="utf-8")

    assert _manager(public_dir)._check_public_privacy() == [_BASELINE_OK_MARKER]  # noqa: SLF001


# ---------------------------------------------------------------------------
# A12.3 — CR-6: the Windows trailing-period escape no longer defeats the carve-out.
# Windows silently strips a trailing period (or space) from a path component, so
# "C:\Users\Public." IS, to Windows itself, the SAME path as "C:\Users\Public" — but
# the pre-fix exclude_regex required the placeholder to be followed immediately by
# end-of-string or a backslash, so a trailing period (routine prose punctuation, e.g.
# a sentence ending right after the path with no space) defeated the carve-out and
# produced a false-positive finding on ordinary documentation.
# ---------------------------------------------------------------------------


def test_windows_users_path_trailing_period_no_longer_defeats_the_placeholder_carve_out() -> None:
    """Root-cause proof at the regex level: the documented placeholder form, followed
    immediately by a trailing period (prose form, in this fixture the ENTIRE scanned
    text — the exact shape that pre-fix could not backtrack its way out of), must
    still be excluded."""
    patterns = {p.id: p for p in _load_privacy_baseline()}
    windows_pattern = patterns["windows-users-path"]

    prose = "backup lives at C:\\Users\\Public."
    match = windows_pattern.regex.search(prose)
    assert match is not None
    assert windows_pattern.exclude is not None
    assert windows_pattern.exclude.search(match.group(0)), (
        "a trailing period right after the placeholder (Windows treats it as "
        "insignificant) must not defeat the carve-out"
    )


def test_windows_users_path_trailing_period_prose_form_fixture_reports_ok_through_the_doctor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """End-to-end confirmation through ``_check_public_privacy``: the exact CR-6 prose
    fixture (the scanned file's content ends immediately after the trailing period)
    reports clean, not a false-positive finding."""
    _disable_operator_denylist(monkeypatch, tmp_path)
    public_dir = tmp_path / "public"
    (public_dir / "data").mkdir(parents=True)
    (public_dir / "data" / "AGENTS.md").write_text(
        "backup lives at C:\\Users\\Public.", encoding="utf-8"
    )
    assert _manager(public_dir)._check_public_privacy() == [_BASELINE_OK_MARKER]  # noqa: SLF001


def test_windows_users_path_trailing_period_still_fires_for_a_real_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Counter-fixture: the SAME trailing-period prose shape, but with a genuine
    (non-placeholder) name, must still be flagged — the fix widens the placeholder's
    OWN tolerance, it never widens which names count as placeholders."""
    _disable_operator_denylist(monkeypatch, tmp_path)
    public_dir = tmp_path / "public"
    (public_dir / "data").mkdir(parents=True)
    (public_dir / "data" / "AGENTS.md").write_text(
        "backup lives at C:\\Users\\zz-fixture-user.", encoding="utf-8"
    )
    report = [line.render() for line in _manager(public_dir)._check_public_privacy()]  # noqa: SLF001
    assert any(line.startswith("[error] public-privacy:") for line in report)


# ---------------------------------------------------------------------------
# A12.4 / T-043-23 security-review rework — the internal-hostname dotted-chain
# carve-out is now scoped to the ``.home`` label class ONLY (Path.home(),
# pathlib.Path.home(), and any other uppercase-initial Python attribute chain
# ENDING in ``.home``), never a blanket "any uppercase-initial dotted chain"
# exclusion. Pre-rework the carve-out was UNANCHORED and applied via ``.search()``:
# one capitalised label ANYWHERE in the matched hostname excluded the WHOLE match,
# so a real, personal/corporate-name-bearing hostname (a macOS mDNS default, a
# Windows default hostname, a mixed-case corp subdomain, an all-uppercase label)
# silently passed both the public-privacy doctor gate and the push-range denylist
# scan (security-reviewer MEDIUM finding, CWE-625/CWE-183, handoff
# 2026-08-17T173112Z-security-reviewer-v0.4.3-alpha-2-delta). Narrowed per the
# handoff's Option A: ``(?:^|\.)[A-Z][A-Za-z0-9_]*\.home$`` — an uppercase-initial
# chain is excluded ONLY when it ends in ``.home`` (the shape
# ``Path.home()``/``pathlib.Path.home()`` actually needed); every OTHER TLD class
# (``.local``/``.internal``/``.lan``/``.intranet``/``.corp``) now fires regardless
# of case.
#
# Every hostname-shaped literal below is composed at RUNTIME via
# ``_hostname_literal`` — never contiguous in this module's own tracked source, the
# same technique ``_macos_home_literal``/``_windows_home_literal`` above and
# ``test_repo_self_scan.py::_archive_fixture_literal`` already use. This is ALSO the
# fix for the security-reviewer HIGH finding (CWE-532): the pre-rework all-lowercase
# label/TLD counter-fixture pairs below (formerly line 770 of this same tracked blob)
# were bare joined literals, matching the internal-hostname baseline pattern verbatim
# — this comment deliberately never spells the joined form out either, so the real
# pre-push denylist scan does not refuse THIS explanatory prose.
# ---------------------------------------------------------------------------


def _hostname_literal(*labels: str) -> str:
    """Compose a dotted hostname/attribute-chain literal from *labels* at runtime,
    joined with ``.`` — never written as one contiguous string in this module's own
    tracked source, so the internal-hostname baseline pattern never matches this
    FILE itself (T-043-23 security-review rework, HIGH CWE-532)."""
    return ".".join(labels)


def test_internal_hostname_dotted_chain_structural_rule_still_excludes_path_home() -> None:
    """Regression: the two PRE-EXISTING literal exclusions (Path.home,
    pathlib.Path.home) must still be excluded now that they are covered by the
    narrowed ``.home``-scoped structural rule rather than by their own literals."""
    patterns = {p.id: p for p in _load_privacy_baseline()}
    hostname_pattern = patterns["internal-hostname"]
    assert hostname_pattern.exclude is not None

    for value in (_hostname_literal("Path", "home"), _hostname_literal("pathlib", "Path", "home")):
        match = hostname_pattern.regex.search(f"call {value}() to resolve it")
        assert match is not None, f"{value} must still match the base hostname shape"
        assert hostname_pattern.exclude.search(match.group(0)), (
            f"{value} must still be excluded (structural .home rule, not a literal now)"
        )


def test_internal_hostname_dotted_chain_structural_rule_excludes_a_brand_new_home_chain() -> None:
    """A12.4 (narrowed): a PREVIOUSLY-UNSEEN uppercase-initial chain ENDING IN
    ``.home`` (never added as its own literal) is excluded by the SAME structural
    rule — proving genuine widening within the ``.home`` label class, not a renamed
    literal."""
    patterns = {p.id: p for p in _load_privacy_baseline()}
    hostname_pattern = patterns["internal-hostname"]
    assert hostname_pattern.exclude is not None

    chain = _hostname_literal("SomeClass", "home")
    match = hostname_pattern.regex.search(f"call {chain}() next")
    assert match is not None
    assert match.group(0) == chain
    assert hostname_pattern.exclude.search(match.group(0)), (
        "a brand-new uppercase-initial .home-suffixed chain must be excluded by "
        "the structural rule with no new literal added"
    )


def test_internal_hostname_uppercase_chain_no_longer_excluded_outside_the_home_class() -> None:
    """T-043-23 security-review rework counter-fixture (MEDIUM, CWE-625): an
    uppercase-initial dotted chain ENDING IN A NON-``.home`` TLD (the shape the
    pre-rework over-permissive "any uppercase label anywhere" rule used to carve
    out, composed below via ``_hostname_literal`` so it is never contiguous in this
    prose either) must now fire like any other genuine hostname."""
    patterns = {p.id: p for p in _load_privacy_baseline()}
    hostname_pattern = patterns["internal-hostname"]
    assert hostname_pattern.exclude is not None

    chain = _hostname_literal("SomeClass", "internal")
    match = hostname_pattern.regex.search(f"call {chain}() next")
    assert match is not None
    assert match.group(0) == chain
    assert not hostname_pattern.exclude.search(match.group(0)), (
        "an uppercase-initial chain outside the .home label class must fire "
        "like any other genuine hostname"
    )


@pytest.mark.parametrize(
    "hostname",
    [
        pytest.param(_hostname_literal("db1", "internal"), id="lowercase-internal"),
        pytest.param(_hostname_literal("fileserver", "corp"), id="lowercase-corp"),
        pytest.param(_hostname_literal("build-agent", "lan"), id="lowercase-lan-hyphenated"),
    ],
)
def test_internal_hostname_dotted_chain_structural_rule_preserves_narrowness(
    hostname: str,
) -> None:
    """A12.4 counter-fixture: an all-lowercase, genuinely hostname-shaped value (no
    segment starting uppercase) is NEVER excluded by the new structural rule —
    narrowness is preserved."""
    patterns = {p.id: p for p in _load_privacy_baseline()}
    hostname_pattern = patterns["internal-hostname"]
    assert hostname_pattern.exclude is not None

    match = hostname_pattern.regex.search(f"reach it at {hostname} from the VPN")
    assert match is not None
    assert match.group(0) == hostname
    assert not hostname_pattern.exclude.search(match.group(0)), (
        f"{hostname} is a genuine lowercase internal hostname and must still be flagged"
    )


@pytest.mark.parametrize(
    "hostname",
    [
        pytest.param(
            _hostname_literal("Marcos-MacBook-Pro", "local"), id="macos-mdns-personal-name"
        ),
        pytest.param(_hostname_literal("DESKTOP-AB12CD", "local"), id="windows-default-hostname"),
        pytest.param(_hostname_literal("vpn", "Acme", "internal"), id="mixed-case-corp-name"),
        pytest.param(_hostname_literal("MYNAS", "lan"), id="all-uppercase-label"),
    ],
)
def test_internal_hostname_uppercase_initial_real_hostname_still_fires(hostname: str) -> None:
    """T-043-23 security-review rework (MEDIUM, CWE-625) — the four VERIFIED bypass
    values from the security handoff (a macOS mDNS default carrying the operator's
    given name, a Windows default hostname, a mixed-case corp name, and an
    all-uppercase label) must ALL fire post-narrowing — none of them ends in
    ``.home``, so none is excluded by the narrowed structural rule."""
    patterns = {p.id: p for p in _load_privacy_baseline()}
    hostname_pattern = patterns["internal-hostname"]
    assert hostname_pattern.exclude is not None

    match = hostname_pattern.regex.search(f"reach it at {hostname} from the VPN")
    assert match is not None
    assert match.group(0) == hostname
    assert not hostname_pattern.exclude.search(match.group(0)), (
        f"{hostname} is a genuine, personal/corporate-name-bearing hostname and "
        "must fire regardless of case (bypass verified by the security review)"
    )


def test_internal_hostname_dotted_chain_counter_fixture_fires_through_the_doctor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """End-to-end confirmation: the lowercase counter-fixture is a genuine finding
    through ``_check_public_privacy``, while the ``.home``-suffixed Python-identifier
    fixture stays clean — proving the narrowed structural rule is wired through, not
    just present at the bare-regex level."""
    _disable_operator_denylist(monkeypatch, tmp_path)

    clean_dir = tmp_path / "public-clean"
    (clean_dir / "data").mkdir(parents=True)
    (clean_dir / "data" / "AGENTS.md").write_text(
        f"call {_hostname_literal('SomeClass', 'home')}() to resolve the base path\n",
        encoding="utf-8",
    )
    assert _manager(clean_dir)._check_public_privacy() == [_BASELINE_OK_MARKER]  # noqa: SLF001

    dirty_dir = tmp_path / "public-dirty"
    (dirty_dir / "data").mkdir(parents=True)
    (dirty_dir / "data" / "AGENTS.md").write_text(
        f"reach it at {_hostname_literal('db1', 'internal')} from the VPN\n", encoding="utf-8"
    )
    report = [line.render() for line in _manager(dirty_dir)._check_public_privacy()]  # noqa: SLF001
    assert any(line.startswith("[error] public-privacy:") for line in report)


def test_internal_hostname_uppercase_initial_real_hostname_fires_through_the_doctor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """End-to-end confirmation (MEDIUM rework): an uppercase-initial, genuinely
    personal-name-bearing hostname is a real finding through
    ``_check_public_privacy`` post-narrowing — not only at the bare-regex level."""
    _disable_operator_denylist(monkeypatch, tmp_path)

    dirty_dir = tmp_path / "public-dirty-uppercase"
    (dirty_dir / "data").mkdir(parents=True)
    (dirty_dir / "data" / "AGENTS.md").write_text(
        f"reach it at {_hostname_literal('Marcos-MacBook-Pro', 'local')} on the LAN\n",
        encoding="utf-8",
    )
    report = [line.render() for line in _manager(dirty_dir)._check_public_privacy()]  # noqa: SLF001
    assert any(line.startswith("[error] public-privacy:") for line in report)
