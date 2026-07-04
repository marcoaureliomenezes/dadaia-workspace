"""FR3 profile-aware ``public install``-all + ``public doctor`` (T-58-30, v0.1.58 W3).

The persisted ``.dadaia/states/harness_profile.json`` (written by ``init --harness``, W2)
now scopes install-all and the doctor's inline projection block:

* **Install-all reads the profile** — ``install(target="all")`` installs only the profile's
  harnesses; an absent profile falls back to all-four (back-compat); an explicit
  ``--target X`` always overrides.
* **Doctor scopes the inline ``_compare`` block** — claude ``settings.json`` only when
  ``claude`` in profile; the codex projection + codex-parity drift (``check_codex_drift``
  D-CX-1..10 / ``codex_trust_boundary_info``) only when ``codex`` in profile; the ``.pi/``
  tree only when ``pi`` in profile. The absent-profile path stays **byte-identical** to the
  W1 all-four doctor golden (Q2/A4).
* **Out-of-profile-but-present is never silent (A3)** — a runtime dir that physically exists
  outside the profile emits a ``[warn] <harness>: out-of-profile runtime present`` line,
  never green-with-zero-lines.

RED-first: every new-behaviour test here FAILS against the pre-fix tree (install-all always
all-four; doctor unconditionally checks all-four, emitting ``[missing] codex:agents/*.toml
(D-CX-1)`` ×12 for a claude-only tree). The absent-profile byte-equality and the
explicit-override tests are invariants that hold both before and after the fix.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.commands.public import app as public_app
from dadaia_workspace.core.models.harness_profile import HarnessProfile
from dadaia_workspace.infrastructure.json_harness_profile_store import JsonHarnessProfileStore
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager

# Reuse the EXACT W1 golden normalizer + committed golden (Q2/A4 byte-equality lock) — the
# same path-normalization and git-dirty line exclusion the W1 doctor golden was captured
# with, so the absent-profile assertion below is a real byte-equality, not a paraphrase.
from tests.unit.infrastructure.test_install_target_goldens import (
    _DOCTOR_GOLDEN,
    _is_env_doctor_line,
    _norm_path_line,
    _sort_line_lists,
)

pytestmark = pytest.mark.unit

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
    """Build a genuinely claude-only projection tree, independent of the install-profile fix.

    Explicit ``agents`` + ``claude`` target installs give the shared ``.agents/skills`` root,
    the ``.claude/`` projection, and the git chokepoint scripts — but NO ``.codex/`` and NO
    ``.pi/``, regardless of whether ``install(target="all")`` reads the profile yet. The
    profile file is then written so ``doctor`` scopes to ``claude``. This keeps the doctor
    RED/GREEN attributable purely to the DOCTOR fix (not the install fix).
    """
    mgr = FileSystemPublicAssetManager()
    mgr.install(ws, target="agents")
    mgr.install(ws, target="claude")
    _write_profile(ws, ("claude",))
    return mgr


def _scaffold_chokepoint_scripts(mgr: FileSystemPublicAssetManager, ws: Path) -> None:
    """Install the harness-independent git chokepoint scripts into ``.dadaia/scripts``.

    W2 boundary (recorded): a pi-only / agents-only per-target subset install does NOT
    install the chokepoint scripts — the existing install rule projects them only for the
    ``{all, claude, codex}`` targets (FR2 "follow the existing rule"). FR3 keeps the scripts
    doctor check UNCONDITIONAL (the chokepoints are harness-independent), so a pi-only tree
    must have them present to read green. This mirrors what ``install(target="all")`` (the
    real ``dadaia public install`` path) does via ``_install_scripts`` — used here so the
    pi-only doctor-green assertion isolates the CLAUDE-loop scoping fix, not the scripts gap.
    """
    agentic_dir = ws / ".dadaia" / "agentic"
    mgr._install_scripts(agentic_dir, ws, False, [])


def _install_codex_only_tree(ws: Path) -> FileSystemPublicAssetManager:
    """Build a genuinely codex-only projection tree (isolates the doctor claude-loop fix).

    Explicit ``agents`` + ``codex`` target installs give the shared ``.agents/skills`` root,
    the ``.codex/`` projection, and the git chokepoint scripts (codex install triggers them)
    — but NO ``.claude/`` and NO ``.pi/``. The profile is then written so ``doctor`` scopes to
    ``codex``. RED/GREEN is attributable purely to the W5 claude-loop scoping (not install).
    """
    mgr = FileSystemPublicAssetManager()
    mgr.install(ws, target="agents")
    mgr.install(ws, target="codex")
    _write_profile(ws, ("codex",))
    return mgr


def _install_pi_only_tree(ws: Path) -> FileSystemPublicAssetManager:
    """Build a genuinely pi-only projection tree (isolates the doctor claude-loop fix).

    Explicit ``agents`` + ``pi`` target installs give the shared ``.agents/skills`` root and
    the ``.pi/`` post-trust projection — but NO ``.claude/`` and NO ``.codex/``. The pi target
    does NOT install the chokepoint scripts (W2 boundary), so they are scaffolded explicitly
    (they are harness-independent and FR3 keeps their doctor check unconditional). The profile
    is written so ``doctor`` scopes to ``pi``.
    """
    mgr = FileSystemPublicAssetManager()
    mgr.install(ws, target="agents")
    mgr.install(ws, target="pi")
    _scaffold_chokepoint_scripts(mgr, ws)
    _write_profile(ws, ("pi",))
    return mgr


def _mentions_codex_or_pi(line: str) -> bool:
    return "codex" in line or "pi:" in line or ".codex" in line or "/.pi" in line


def _mentions_claude(line: str) -> bool:
    return line.startswith("claude:") or "claude:" in line or "/.claude" in line


# ---------------------------------------------------------------------------
# AC-5 — install-all reads the profile (RED-first)
# ---------------------------------------------------------------------------


def test_claude_only_profile_install_all_writes_only_claude(tmp_path: Path) -> None:
    """AC-5 (install): a claude-only profile makes ``install(target="all")`` skip codex/pi.

    RED-first: pre-fix, ``install(target="all")`` ignores the profile and scaffolds all-four,
    so ``.codex/`` / ``.pi/`` ARE written and the assertions below FAIL.
    """
    ws = tmp_path / "ws"
    ws.mkdir()
    _write_profile(ws, ("claude",))

    FileSystemPublicAssetManager().install(ws, target="all")

    assert (ws / ".claude").exists(), "claude projection must be written for a claude profile"
    assert (ws / ".agents" / "skills").exists(), "shared agents skills root is always written"
    assert not (ws / ".codex").exists(), "codex projection must NOT be written (out of profile)"
    assert not (ws / ".pi").exists(), "pi projection must NOT be written (out of profile)"


def test_absent_profile_install_all_is_all_four_backcompat(tmp_path: Path) -> None:
    """A pre-v0.1.58 workspace (no profile file) still installs all-four (back-compat)."""
    ws = tmp_path / "ws"
    ws.mkdir()

    FileSystemPublicAssetManager().install(ws, target="all")

    assert (ws / ".claude").exists()
    assert (ws / ".codex").exists()
    assert (ws / ".pi").exists()


def test_explicit_target_codex_overrides_profile(tmp_path: Path) -> None:
    """AC-5 (override): explicit ``--target codex`` installs codex regardless of the profile."""
    ws = tmp_path / "ws"
    ws.mkdir()
    _write_profile(ws, ("claude",))

    FileSystemPublicAssetManager().install(ws, target="codex")

    assert (ws / ".codex" / "config.toml").exists(), "explicit --target codex must override"


# ---------------------------------------------------------------------------
# AC-5 / Q1 / Q7 — profile-scoped doctor is green for a claude-only tree (RED-first)
# ---------------------------------------------------------------------------


def test_claude_only_profile_doctor_is_green(tmp_path: Path) -> None:
    """AC-5/Q1/Q7 (report list): a claude-only doctor emits no codex/pi blocker + no D-CX-1.

    RED-first: pre-fix, ``doctor`` checks all-four unconditionally, so a claude-only tree
    reports ``[missing] codex:hooks.json``/``[missing] pi:*`` and the D-CX-1 ×12
    ``[missing] codex:agents/<name>.toml`` lines — the assertions below FAIL.
    """
    ws = tmp_path / "ws"
    ws.mkdir()
    mgr = _install_claude_only_tree(ws)

    reports = mgr.doctor(ws)

    # Q1: no D-CX-1 codex:agents line (the ×12 blocker that made AC-5 unachievable).
    assert not any("codex:agents/" in r and "(D-CX-1)" in r for r in reports), (
        "profile-scoped doctor must not run check_codex_drift for a claude-only profile"
    )
    # No [missing] for the out-of-profile codex/pi runtimes.
    assert not any(r.startswith("[missing]") and _mentions_codex_or_pi(r) for r in reports), (
        "no [missing] codex/pi line for a claude-only profile"
    )
    # Q7 (report list): no blocker line at all for a clean claude-only tree.
    blockers = [r for r in reports if r.startswith(_BLOCKER_PREFIXES)]
    assert blockers == [], f"claude-only doctor must be blocker-free, got: {blockers}"
    # The claude projection itself is still verified.
    assert any(r == "[ok] claude:settings.json" for r in reports)


def test_claude_only_cli_doctor_exits_zero(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """AC-5/Q7 (CLI surface): ``dadaia public doctor`` exits 0 for a claude-only workspace."""
    ws = tmp_path / "ws"
    ws.mkdir()
    _install_claude_only_tree(ws)
    _seed_spec_contexts(ws)
    monkeypatch.chdir(ws)

    result = CliRunner().invoke(public_app, ["doctor"])

    assert result.exit_code == 0, result.output


# ---------------------------------------------------------------------------
# W5 boundary completion (in-spirit FR3 "doctor scopes runtime expectations") —
# the runtime_expectations claude:* projection loop is scoped by `claude in profile`
# so a codex-only / pi-only doctor is green (no [missing] claude:* false-fail).
#
# W3 scoped only the inline _compare block + the codex-parity gate; the
# runtime_expectations claude/pi projection loop stayed UNCONDITIONAL (W3 handoff +
# T-58-30 ledger flagged this as a W5 boundary). Pre-fix, a codex-only / pi-only doctor
# emits 40 `[missing] claude:rules|skills|commands|agents|workflows/*` lines and the CLI
# exits 1 — AC-8's per-profile green doctor is UNACHIEVABLE. The one-line scope in
# doctor() (`if not claude_active and label.startswith("claude:"): continue`) completes it.
# ---------------------------------------------------------------------------


def test_codex_only_profile_doctor_is_green(tmp_path: Path) -> None:
    """W5/AC-8 (report list): a codex-only doctor emits no [missing] claude:* + is blocker-free.

    RED-first: pre-fix (unscoped runtime_expectations claude loop), a codex-only tree reports
    the ×40 `[missing] claude:rules|skills|commands|agents|workflows/*` lines — the assertions
    below FAIL and ``dadaia public doctor`` exits 1.
    """
    ws = tmp_path / "ws"
    ws.mkdir()
    mgr = _install_codex_only_tree(ws)

    reports = mgr.doctor(ws)

    # The W5 boundary: no [missing] claude:* projection line for an out-of-profile claude.
    assert not any(r.startswith("[missing]") and _mentions_claude(r) for r in reports), (
        "profile-scoped doctor must not emit [missing] claude:* for a codex-only profile"
    )
    # Q7 (report list): blocker-free for a clean codex-only tree.
    blockers = [r for r in reports if r.startswith(_BLOCKER_PREFIXES)]
    assert blockers == [], f"codex-only doctor must be blocker-free, got: {blockers}"
    # The codex projection itself is still verified (it is in-profile).
    assert any(r == "[ok] codex:hooks.json" for r in reports)
    # classify_workflows still emits its harness-independent [ok] claude:workflows/* lines
    # (non-blockers) — scoping must not have removed those.
    assert any(r.startswith("[ok] claude:workflows/") for r in reports)


def test_codex_only_cli_doctor_exits_zero(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """W5/AC-8 (CLI surface): ``dadaia public doctor`` exits 0 for a codex-only workspace."""
    ws = tmp_path / "ws"
    ws.mkdir()
    _install_codex_only_tree(ws)
    _seed_spec_contexts(ws)
    monkeypatch.chdir(ws)

    result = CliRunner().invoke(public_app, ["doctor"])

    assert result.exit_code == 0, result.output


def test_pi_only_profile_doctor_is_green(tmp_path: Path) -> None:
    """W5/AC-8 (report list): a pi-only doctor emits no [missing] claude:*/codex:* + is blocker-free.

    RED-first: pre-fix, a pi-only tree reports the ×40 `[missing] claude:*` lines (the
    unscoped runtime_expectations loop) — the claude assertion below FAILS and the CLI exits 1.
    """
    ws = tmp_path / "ws"
    ws.mkdir()
    mgr = _install_pi_only_tree(ws)

    reports = mgr.doctor(ws)

    assert not any(r.startswith("[missing]") and _mentions_claude(r) for r in reports), (
        "profile-scoped doctor must not emit [missing] claude:* for a pi-only profile"
    )
    assert not any(r.startswith(_BLOCKER_PREFIXES) and _mentions_codex_or_pi(r) for r in reports), (
        "no codex blocker for a pi-only profile (and pi is checked, not missing)"
    )
    blockers = [r for r in reports if r.startswith(_BLOCKER_PREFIXES)]
    assert blockers == [], f"pi-only doctor must be blocker-free, got: {blockers}"
    # The pi projection itself is still verified (it is in-profile).
    assert any(r.startswith("[ok] pi:") for r in reports)


def test_pi_only_cli_doctor_exits_zero(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """W5/AC-8 (CLI surface): ``dadaia public doctor`` exits 0 for a pi-only workspace."""
    ws = tmp_path / "ws"
    ws.mkdir()
    _install_pi_only_tree(ws)
    _seed_spec_contexts(ws)
    monkeypatch.chdir(ws)

    result = CliRunner().invoke(public_app, ["doctor"])

    assert result.exit_code == 0, result.output


def test_codex_only_out_of_profile_claude_on_disk_is_not_silent(tmp_path: Path) -> None:
    """A3 symmetry: a codex-only profile + a stale ``.claude/`` on disk stays non-silent.

    Scoping the runtime_expectations claude:* loop must NOT re-open the A3 hole: a physically
    present out-of-profile ``.claude/`` is still surfaced by the inline block's ``[warn]``,
    never green-with-zero-lines.
    """
    ws = tmp_path / "ws"
    ws.mkdir()
    mgr = _install_codex_only_tree(ws)
    claude_dir = ws / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    (claude_dir / "settings.json").write_text('{"stale": true}\n', encoding="utf-8")

    reports = mgr.doctor(ws)

    assert any("claude" in r and "out-of-profile" in r for r in reports), (
        "an out-of-profile claude runtime present on disk must produce a non-silent line"
    )


# ---------------------------------------------------------------------------
# Q2/A4 — absent-profile doctor is byte-identical to the W1 all-four golden
# ---------------------------------------------------------------------------


def test_absent_profile_doctor_byte_equals_all_four_golden(tmp_path: Path) -> None:
    """Q2/A4: the absent-profile doctor path reproduces the W1 all-four doctor golden byte-for-byte.

    This is the FR3 back-compat lock every pre-v0.1.58 workspace rides on. It uses the SAME
    normalizer (path-normalize + git-dirty exclusion) the W1 golden was captured with.
    """
    ws = tmp_path / "doctor_all_four"
    ws.mkdir()
    mgr = FileSystemPublicAssetManager()
    mgr.install(ws, target="all")

    report = mgr.doctor(ws)
    normalized = [_norm_path_line(line, ws) for line in report if not _is_env_doctor_line(line)]

    golden = _sort_line_lists(json.loads(_DOCTOR_GOLDEN.read_text(encoding="utf-8")))
    normalized = _sort_line_lists(normalized)
    assert normalized == golden, (
        "absent-profile doctor diverged from the W1 all-four golden — FR3 broke back-compat."
    )


# ---------------------------------------------------------------------------
# A3 — an out-of-profile runtime present on disk is never silent (RED-first)
# ---------------------------------------------------------------------------


def test_stale_out_of_profile_codex_on_disk_is_not_silent(tmp_path: Path) -> None:
    """A3: a claude-only profile + a stale ``.codex/`` on disk emits a non-silent codex line.

    RED-first: pre-fix, doctor checks codex unconditionally and never emits an
    ``out-of-profile`` line (it emits ``[drift]``/``[missing]`` codex lines instead), so the
    assertion FAILS. The (c″) sabotage — emitting ZERO lines for an on-disk out-of-profile
    runtime — also FAILS this test (reads green).
    """
    ws = tmp_path / "ws"
    ws.mkdir()
    mgr = _install_claude_only_tree(ws)
    # Operator hand-installed / re-profiled leftover: a stale codex runtime dir on disk.
    codex_dir = ws / ".codex"
    codex_dir.mkdir(parents=True, exist_ok=True)
    (codex_dir / "hooks.json").write_text('{"stale": true}\n', encoding="utf-8")

    reports = mgr.doctor(ws)

    non_silent = [r for r in reports if "codex" in r and "out-of-profile" in r]
    assert non_silent, (
        "an out-of-profile codex runtime present on disk must produce a non-silent line, "
        f"never green-with-zero-lines; got no such line in: {reports}"
    )


def test_out_of_profile_pi_present_is_not_silent(tmp_path: Path) -> None:
    """A3 (symmetry): a stale ``.pi/`` on disk under a claude-only profile is non-silent too."""
    ws = tmp_path / "ws"
    ws.mkdir()
    mgr = _install_claude_only_tree(ws)
    pi_dir = ws / ".pi"
    pi_dir.mkdir(parents=True, exist_ok=True)
    (pi_dir / "SYSTEM.md").write_text("# stale\n", encoding="utf-8")

    reports = mgr.doctor(ws)

    assert any("pi" in r and "out-of-profile" in r for r in reports), (
        "an out-of-profile pi runtime present on disk must produce a non-silent line"
    )
