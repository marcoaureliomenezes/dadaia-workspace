"""FR3 profile-aware ``public install``-all + ``public doctor`` (T-58-30, v0.1.58 W3).

The persisted ``.dadaia/states/harness_profile.json`` (written by ``init --harness``, W2)
now scopes install-all and the doctor's inline projection block:

* **Install-all reads the profile** — ``install(target="all")`` installs only the profile's
  harnesses; an absent profile falls back to all-four (back-compat); an explicit
  ``--target X`` always overrides.
* **Doctor scopes the inline ``_compare`` block** — claude ``settings.json`` only when
  ``claude`` in profile; the codex projection + codex-parity drift (``check_codex_drift``
  D-CX-1..10 / ``codex_trust_boundary_info``) only when ``codex`` in profile; the
  ``.kimi-code/`` tree only when ``kimi-code`` in profile. The absent-profile path stays **byte-identical** to the
  W1 all-four doctor golden (Q2/A4).
* **Out-of-profile-but-present is never silent (A3)** — a runtime dir that physically exists
  outside the profile emits a ``[warn] <harness>: out-of-profile runtime present`` line,
  never green-with-zero-lines.

RED-first: every new-behaviour test here FAILS against the pre-fix tree (install-all always
all-four; doctor unconditionally checks all-four, emitting ``[missing] codex:agents/*.toml
(D-CX-1)`` ×12 for a claude-only tree). The absent-profile byte-equality and the
explicit-override tests are invariants that hold both before and after the fix.

Intent: CONTRACT — v0.4.5 A3.1, A3.2 (``byte-golden-test-inventory-roster-split``, FR3).
The absent-profile doctor golden below shares ``doctor_all_four_v0158.json`` with
``test_install_target_goldens.py`` and is filtered through the SAME derived roster
(``tests/helpers/public_asset_roster.py``) before comparison, so it too no longer
contains a per-public-asset file inventory (A3.2); the roster-derived inventory check
(A3.1) is re-asserted here for this file's own capture path.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.commands.public import app as public_app
from dadaia_workspace.core.models.harness_profile import HarnessProfile
from dadaia_workspace.infrastructure.json_harness_profile_store import JsonHarnessProfileStore
from dadaia_workspace.infrastructure.public_assets import (
    FileSystemPublicAssetManager,
    OverwritePolicy,
)
from tests.helpers import public_asset_roster

# Reuse the EXACT W1 golden normalizer + committed golden (Q2/A4 byte-equality lock) — the
# same path-normalization and git-dirty line exclusion the W1 doctor golden was captured
# with, so the absent-profile assertion below is a real byte-equality, not a paraphrase.
from tests.helpers.golden_platform import (
    is_env_doctor_line,
    norm_path_line,
    sort_line_lists,
)
from tests.helpers.scan_population import assert_populated


def _rendered(result: object) -> list[str]:
    """Legacy string view of a typed doctor result (DoctorReport | list[DoctorLine])."""
    if hasattr(result, "rendered"):
        return result.rendered()  # type: ignore[attr-defined, no-any-return]
    return [
        line.render() if hasattr(line, "render") else str(line)
        for line in result  # type: ignore[union-attr]
    ]


pytestmark = pytest.mark.unit

_DOCTOR_GOLDEN = Path(__file__).resolve().parent / "_golden" / "doctor_all_four_v0158.json"

_BLOCKER_PREFIXES = ("[missing]", "[drift]", "[fail]")


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _write_profile(ws: Path, harnesses: tuple[str, ...]) -> None:
    states = ws / ".dadaia" / "states"
    states.mkdir(parents=True, exist_ok=True)
    JsonHarnessProfileStore().write(states, HarnessProfile.of(harnesses))


def _seed_spec_contexts(ws: Path) -> None:
    """Write the sentinel ``resolve_workspace_root`` needs so the CLI resolves *ws*."""
    states = ws / ".dadaia" / "states"
    states.mkdir(parents=True, exist_ok=True)
    (states / "spec_contexts.json").write_text(
        json.dumps({"schema_version": "2", "contexts": []}, indent=2), encoding="utf-8"
    )


def _install_claude_only_tree(ws: Path) -> FileSystemPublicAssetManager:
    """Build a genuinely claude-only projection tree, independent of the install-profile fix."""
    mgr = FileSystemPublicAssetManager()
    mgr.install(ws, target="agents")
    mgr.install(ws, target="claude")
    _write_profile(ws, ("claude",))
    return mgr


def _scaffold_chokepoint_scripts(mgr: FileSystemPublicAssetManager, ws: Path) -> None:
    """Install the harness-independent git chokepoint scripts into ``.dadaia/scripts``."""
    agentic_dir = ws / ".dadaia" / "agentic"
    mgr._install_scripts(agentic_dir, ws, OverwritePolicy.PRESERVE, [])


def _install_codex_only_tree(ws: Path) -> FileSystemPublicAssetManager:
    """Build a genuinely codex-only projection tree (isolates the doctor claude-loop fix)."""
    mgr = FileSystemPublicAssetManager()
    mgr.install(ws, target="agents")
    mgr.install(ws, target="codex")
    _write_profile(ws, ("codex",))
    return mgr


def _install_kimi_only_tree(ws: Path) -> FileSystemPublicAssetManager:
    """Build a genuinely kimi-only projection tree (isolates the doctor claude-loop fix)."""
    mgr = FileSystemPublicAssetManager()
    mgr.install(ws, target="agents")
    mgr.install(ws, target="kimi-code")
    _scaffold_chokepoint_scripts(mgr, ws)
    _write_profile(ws, ("kimi-code",))
    return mgr


def _mentions_codex_or_kimi(line: str) -> bool:
    return "codex" in line or "kimi-code:" in line or ".codex" in line or "/.kimi-code" in line


def _mentions_claude(line: str) -> bool:
    return line.startswith("claude:") or "claude:" in line or "/.claude" in line


# ---------------------------------------------------------------------------
# AC-5 — install-all reads the profile (RED-first); absent-profile back-compat;
# explicit --target always overrides.
# ---------------------------------------------------------------------------


def test_claude_only_profile_install_all_writes_only_claude(tmp_path: Path) -> None:
    """AC-5 (install): a claude-only profile makes ``install(target="all")`` skip codex/kimi.

    RED-first: pre-fix, ``install(target="all")`` ignores the profile and scaffolds all-four,
    so ``.codex/`` / ``.kimi-code/`` ARE written and the assertions below FAIL.
    """
    ws = tmp_path / "ws"
    ws.mkdir()
    _write_profile(ws, ("claude",))

    FileSystemPublicAssetManager().install(ws, target="all")

    assert (ws / ".claude").exists(), "claude projection must be written for a claude profile"
    assert (ws / ".agents" / "skills").exists(), "shared agents skills root is always written"
    assert not (ws / ".codex").exists(), "codex projection must NOT be written (out of profile)"
    assert not (ws / ".kimi-code").exists(), "kimi projection must NOT be written (out of profile)"

    # A pre-v0.1.58 workspace (no profile file) still installs all-four (back-compat).
    ws2 = tmp_path / "ws2"
    ws2.mkdir()
    FileSystemPublicAssetManager().install(ws2, target="all")
    assert (ws2 / ".claude").exists()
    assert (ws2 / ".codex").exists()
    assert (ws2 / ".kimi-code").exists()

    # Explicit --target codex installs codex regardless of the profile.
    ws3 = tmp_path / "ws3"
    ws3.mkdir()
    _write_profile(ws3, ("claude",))
    FileSystemPublicAssetManager().install(ws3, target="codex")
    assert (ws3 / ".codex" / "config.toml").exists(), "explicit --target codex must override"


# ---------------------------------------------------------------------------
# AC-5 / Q1 / Q7 / W5 — profile-scoped doctor is green per profile (RED-first)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("install_tree", "expect_ok_line", "no_missing_predicate"),
    [
        pytest.param(
            _install_claude_only_tree,
            "[ok] claude:settings.json",
            lambda r: not (r.startswith(_BLOCKER_PREFIXES[0]) and _mentions_codex_or_kimi(r)),
            id="claude-only",
        ),
        pytest.param(
            _install_codex_only_tree,
            "[ok] codex:hooks.json",
            lambda r: not (r.startswith(_BLOCKER_PREFIXES[0]) and _mentions_claude(r)),
            id="codex-only",
        ),
        pytest.param(
            _install_kimi_only_tree,
            None,  # checked via startswith below
            lambda r: not (r.startswith(_BLOCKER_PREFIXES[0]) and _mentions_claude(r)),
            id="kimi-only",
        ),
    ],
)
def test_profile_scoped_doctor_is_green(
    tmp_path: Path, install_tree: object, expect_ok_line: str | None, no_missing_predicate: object
) -> None:
    """AC-5/Q1/Q7/W5 (report list): a per-profile doctor emits no out-of-profile [missing]
    lines (incl. the D-CX-1 codex:agents ×12 blocker for claude-only, and the unscoped
    runtime_expectations claude ×40 lines for codex/kimi-only) and is blocker-free."""
    ws = tmp_path / "ws"
    ws.mkdir()
    mgr = install_tree(ws)  # type: ignore[operator]

    reports = _rendered(mgr.doctor(ws))

    assert not any("codex:agents/" in r and "(D-CX-1)" in r for r in reports), (
        "profile-scoped doctor must not run check_codex_drift for an out-of-codex-profile tree"
    )
    assert all(no_missing_predicate(r) for r in reports)  # type: ignore[operator]
    blockers = [r for r in reports if r.startswith(_BLOCKER_PREFIXES)]
    assert blockers == [], f"profile-scoped doctor must be blocker-free, got: {blockers}"

    if expect_ok_line is not None:
        assert any(r == expect_ok_line for r in reports)
    else:  # kimi-only
        assert any(r.startswith("[ok] kimi-code:") for r in reports)

    assert not any(":workflows/" in report for report in reports)


@pytest.mark.parametrize(
    "install_tree",
    [_install_claude_only_tree, _install_codex_only_tree, _install_kimi_only_tree],
    ids=["claude-only", "codex-only", "kimi-only"],
)
def test_profile_scoped_cli_doctor_exits_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, install_tree: object
) -> None:
    """AC-5/W5/AC-8 (CLI surface): ``dadaia public doctor`` exits 0 for every per-profile
    workspace shape (claude-only/codex-only/kimi-only)."""
    ws = tmp_path / "ws"
    ws.mkdir()
    install_tree(ws)  # type: ignore[operator]
    _seed_spec_contexts(ws)
    monkeypatch.chdir(ws)

    result = CliRunner().invoke(public_app, ["doctor"])

    assert result.exit_code == 0, result.output


# ---------------------------------------------------------------------------
# A3 — an out-of-profile runtime present on disk is never silent (RED-first)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("install_tree", "stale_dir", "stale_filename", "stale_content", "token"),
    [
        pytest.param(
            _install_claude_only_tree,
            ".codex",
            "hooks.json",
            '{"stale": true}\n',
            "codex",
            id="stale-codex-on-claude-only",
        ),
        pytest.param(
            _install_claude_only_tree,
            ".kimi-code",
            "SYSTEM.md",
            "# stale\n",
            "kimi-code",
            id="stale-kimi-on-claude-only",
        ),
        pytest.param(
            _install_codex_only_tree,
            ".claude",
            "settings.json",
            '{"stale": true}\n',
            "claude",
            id="stale-claude-on-codex-only",
        ),
    ],
)
def test_out_of_profile_runtime_present_is_not_silent(
    tmp_path: Path,
    install_tree: object,
    stale_dir: str,
    stale_filename: str,
    stale_content: str,
    token: str,
) -> None:
    """A3: a runtime physically present outside the profile emits a non-silent
    ``out-of-profile`` line, never green-with-zero-lines. Scoping the
    runtime_expectations loop must not re-open this hole in either direction."""
    ws = tmp_path / "ws"
    ws.mkdir()
    mgr = install_tree(ws)  # type: ignore[operator]
    leftover = ws / stale_dir
    leftover.mkdir(parents=True, exist_ok=True)
    (leftover / stale_filename).write_text(stale_content, encoding="utf-8")

    reports = _rendered(mgr.doctor(ws))

    non_silent = [r for r in reports if token in r and "out-of-profile" in r]
    assert non_silent, (
        f"an out-of-profile {token} runtime present on disk must produce a non-silent line, "
        f"never green-with-zero-lines; got no such line in: {reports}"
    )


# ---------------------------------------------------------------------------
# Q2/A4 — absent-profile doctor is byte-identical to the W1 all-four golden
# ---------------------------------------------------------------------------


def test_absent_profile_doctor_byte_equals_all_four_golden(tmp_path: Path) -> None:
    """Q2/A4 / v0.4.5 A3.2: the absent-profile doctor path reproduces the W1 all-four
    doctor golden's POLICY byte-for-byte.

    This is the FR3 (v0.1.58) back-compat lock every pre-v0.1.58 workspace rides on. It
    uses the SAME normalizer (path-normalize + git-dirty exclusion) the W1 golden was
    captured with, filtered through the SAME derived roster
    (``tests/helpers/public_asset_roster.py``, v0.4.5 FR3) as
    ``test_install_target_goldens.py`` — the per-asset inventory dimension moved to the
    roster assertion (A3.1, ``test_absent_profile_doctor_stage_lines_match_the_public_asset_roster``
    below); this golden no longer contains a file inventory.
    """
    ws = tmp_path / "doctor_all_four"
    ws.mkdir()
    mgr = FileSystemPublicAssetManager()
    mgr.install(ws, target="all")

    report = _rendered(mgr.doctor(ws))
    normalized = [norm_path_line(line, ws) for line in report if not is_env_doctor_line(line)]
    roster = public_asset_roster.scan()
    policy = public_asset_roster.policy_only_doctor_lines(normalized, roster)

    golden = sort_line_lists(json.loads(_DOCTOR_GOLDEN.read_text(encoding="utf-8")))
    assert sort_line_lists(policy) == golden, (
        "absent-profile doctor diverged from the W1 all-four golden — FR3 broke back-compat."
    )


def test_absent_profile_doctor_stage_lines_match_the_public_asset_roster(
    tmp_path: Path,
) -> None:
    """Intent: CONTRACT — v0.4.5 A3.1

    Mirrors ``test_install_target_goldens.py::test_doctor_stage_lines_match_the_public_asset_roster``
    for this file's own capture path: the inventory dimension the golden above used to
    pin lives here instead, DERIVED by an independent scan
    (``public_asset_roster.scan()``), never a second hand-kept list.
    """
    roster = set(public_asset_roster.scan())
    # v0.4.5 FR5 (scan-test-vacuity-guard): a mis-rooted public/ scan would degrade
    # `roster` to empty, mirroring the same risk this file's counterpart in
    # test_install_target_goldens.py closes.
    assert_populated(roster, sentinel="skills/dd-cli-library/SKILL.md")
    ws = tmp_path / "doctor_all_four_roster"
    ws.mkdir()
    mgr = FileSystemPublicAssetManager()
    mgr.install(ws, target="all")
    report = _rendered(mgr.doctor(ws))
    normalized = [norm_path_line(line, ws) for line in report if not is_env_doctor_line(line)]
    stage_paths = public_asset_roster.stage_asset_paths(normalized)
    assert stage_paths == roster
