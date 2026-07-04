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


def _mentions_codex_or_pi(line: str) -> bool:
    return "codex" in line or "pi:" in line or ".codex" in line or "/.pi" in line


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

    golden = json.loads(_DOCTOR_GOLDEN.read_text(encoding="utf-8"))
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
