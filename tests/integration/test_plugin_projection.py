"""Golden (b) + pack projection (T-60-20, v0.1.60 W2) — AC-3/AC-4/AC-5/AC-15.

**Golden (b) — the DURABLE descriptors-present, zero-plugin-installed byte-lock (Ruling 14 /
AC-5).** Captured with the W1 pack descriptors present (`public/plugins/**/pack.json`) but
BEFORE any projection/precedence code, this is the baseline consumers see post-upgrade: with
the descriptor source present but no pack installed, `public_assets.install()` (all targets)
and `public_assets.doctor()` replay byte-identical to golden (b). Unlike golden (a) (the
transient core-scoped refactor-lock that FILTERS `stage:plugins/*`), golden (b) is the FULL
new baseline and INCLUDES the `stage:plugins/*` descriptor-source parity lines — those are
captured INTO golden (b) (SPEC AC-5: not a violation). The projection code (added after this
golden commits) MUST leave the zero-plugin path byte-identical to golden (b); "installing zero
plugins changes nothing" is the durable lock.

Three locks, three distinct roles: golden (a) = pre-descriptor core-scoped refactor-lock
(plugin-blind, transient); golden (b) = descriptors-present zero-plugin full baseline
(durable); the AC-3/4/15 tests below = the projected-body behaviour once a pack IS installed.

**Normalization — identical three-leak-class platform-invariance as golden (a)** (v0.1.55
path/version + v0.1.58 host-state cwd-walk / directory-iteration multiset / OS-phrased
exec-probe), env `git-dirty` lines dropped. The ONLY difference from golden (a) is that
golden (b) does NOT filter `stage:plugins/*` (they are its baseline).

**Layer:** integration — real stage/install/doctor via `FileSystemPublicAssetManager` +
`tmp_path` (QA-8b).

Regenerate (ONLY on a deliberate, reviewed behaviour change) with:
``UPDATE_INSTALL_GOLDENS=1 pytest tests/integration/test_plugin_projection.py``.
A byte diff without that flag is a behaviour regression — fix the consumer, never the golden.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.core.models.harness_profile import HarnessProfile
from dadaia_workspace.infrastructure.json_harness_profile_store import JsonHarnessProfileStore
from dadaia_workspace.infrastructure.json_plugin_store import JsonPluginStore
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from tests.helpers.golden_platform import assert_golden, is_env_doctor_line, norm_path_line

pytestmark = pytest.mark.integration

_HERE = Path(__file__).resolve().parent
_GOLDEN_DIR = _HERE / "_golden"
_INSTALL_GOLDEN_B = _GOLDEN_DIR / "plugin_install_targets_golden_b_v0160.json"
_DOCTOR_GOLDEN_B = _GOLDEN_DIR / "plugin_doctor_report_golden_b_v0160.json"

_INSTALL_TARGETS = ("all", "agents", "claude", "codex", "pi", "kimi-code")


def _redirect_kimi_home(monkeypatch: pytest.MonkeyPatch, ws: Path) -> None:
    """Root the kimi-code user-level wiring inside the fixture workspace (v0.2.8).

    Same rationale as ``test_install_target_goldens._redirect_kimi_home``: the kimi
    shims/config-block paths appear in install/doctor lines and must normalize to
    ``<WS>`` — and the real user config is never touched.
    """
    monkeypatch.setenv("KIMI_CODE_HOME", str(ws / "kimi-home"))


# ---------------------------------------------------------------------------
# Normalization helpers (v0.1.55 path/version + v0.1.58 three-leak-class law):
# consolidated into tests/helpers/golden_platform.py (v0.1.64 FR1).
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Capture functions (descriptors present, ZERO plugin installed)
# ---------------------------------------------------------------------------


def _capture_install(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, list[str]]:
    mgr = FileSystemPublicAssetManager()
    result: dict[str, list[str]] = {}
    for target in _INSTALL_TARGETS:
        ws = tmp_path / f"install_{target}"
        ws.mkdir()
        _redirect_kimi_home(monkeypatch, ws)
        installed = mgr.install(ws, target=target)
        result[target] = [norm_path_line(line, ws) for line in installed]
    return result


def _capture_doctor(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> list[str]:
    ws = tmp_path / "doctor_all_four"
    ws.mkdir()
    _redirect_kimi_home(monkeypatch, ws)
    mgr = FileSystemPublicAssetManager()
    mgr.install(ws, target="all")
    report = mgr.doctor(ws)
    return [norm_path_line(line, ws) for line in report if not is_env_doctor_line(line)]


def _golden_b_message(what: str) -> str:
    return (
        f"{what} diverged from the committed v0.1.60 golden (b) — installing zero plugins "
        "changed the descriptors-present baseline. Fix the consumer, never the golden."
    )


# ---------------------------------------------------------------------------
# Golden (b) tests — the durable descriptors-present zero-plugin byte-lock
# ---------------------------------------------------------------------------


def test_descriptors_present_zero_plugin_install_equals_golden_b(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-5: install() (all targets) with descriptors present + no plugin == golden (b)."""
    assert_golden(
        _INSTALL_GOLDEN_B,
        _capture_install(tmp_path, monkeypatch),
        "plugin-golden-b-install-targets",
        message=_golden_b_message("plugin-golden-b-install-targets"),
    )


def test_absent_plugin_doctor_byte_equals_golden_b_with_descriptor_stage_lines(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-5: doctor() with descriptors present + no plugin installed == golden (b);
    golden (b) is the descriptors-present baseline — it INCLUDES ``stage:plugins/*``
    (what distinguishes it from the plugin-blind golden (a); if the descriptor-source
    lines ever vanished from golden (b), the byte-lock would stop covering the new
    staging inventory)."""
    doctor = _capture_doctor(tmp_path, monkeypatch)
    assert_golden(
        _DOCTOR_GOLDEN_B,
        doctor,
        "plugin-golden-b-doctor-report",
        message=_golden_b_message("plugin-golden-b-doctor-report"),
    )
    assert any(ln == "[ok] stage:plugins/frontend-design/pack.json" for ln in doctor), doctor
    assert any(ln == "[ok] stage:plugins/devops/pack.json" for ln in doctor), doctor


# ---------------------------------------------------------------------------
# Projection behaviour (AC-3/AC-4/AC-15) — a synthetic pack BODY seeded into the
# staged tree. The real W3 pack bodies do not exist yet; the projection MECHANISM
# is exercised with a controlled fixture (standard integration testing).
# ---------------------------------------------------------------------------

_PACK = "frontend-design"
_AGENT = "frontend-engineer"
_PACK_BODY = """---
name: frontend-engineer
description: Frontend engineer plugin agent (synthetic W2 fixture).
tier: 3
model: claude-sonnet-4-6
tools: [Read, Write]
---

# Frontend Engineer (plugin pack body)

Real browser HTML/CSS/TS/React implementation body — NOT the core stub.
"""


#: v0.1.65 FR5 (T-65-08/09): the projected claude pack agent is the RENDER output —
#: the authored ``model:`` (the D-5 pack default) is re-emitted as the LAST
#: frontmatter line by the D-6 seam; ``effort:`` is omitted (no override — F-6).
_PACK_BODY_RENDERED = """---
name: frontend-engineer
description: Frontend engineer plugin agent (synthetic W2 fixture).
tier: 3
tools: [Read, Write]
model: claude-sonnet-4-6
---

# Frontend Engineer (plugin pack body)

Real browser HTML/CSS/TS/React implementation body — NOT the core stub.
"""


def _staged_workspace_with_pack_body(
    tmp_path: Path,
    harnesses: tuple[str, ...] | None = None,
) -> tuple[Path, FileSystemPublicAssetManager]:
    """Build a workspace whose staged ``frontend-design`` pack carries a real agent body.

    Optionally writes a harness profile (e.g. claude-only) BEFORE the core install so the
    projection is profile-scoped. Stages + core-installs (projects the stub), then seeds the
    pack agent body into the staged tree (simulating the W3 content).
    """
    ws = tmp_path / "ws"
    ws.mkdir()
    if harnesses is not None:
        states = ws / ".dadaia" / "states"
        states.mkdir(parents=True)
        JsonHarnessProfileStore().write(states, HarnessProfile.of(harnesses))
    mgr = FileSystemPublicAssetManager()
    mgr.install(ws, target="all")
    pack_agent = ws / ".dadaia" / "agentic" / "plugins" / _PACK / "agents" / f"{_AGENT}.md"
    pack_agent.parent.mkdir(parents=True, exist_ok=True)
    pack_agent.write_text(_PACK_BODY, encoding="utf-8")
    return ws, mgr


def _claude_agent(ws: Path) -> Path:
    return ws / ".claude" / "agents" / f"{_AGENT}.md"


def test_plugin_install_projects_body_idempotent_core_precedence_claude_only_and_doctor(
    tmp_path: Path,
) -> None:
    """AC-3: install_plugin overwrites the core stub with the pack body + records the
    ledger; a re-install is a no-op (every projected file hash-compare [skip]); AC-4: a
    following core `install(target=all)` keeps the pack body, not the stub (the clobber
    the ledger-read now prevents). AC-15: in a claude-only profile, install_plugin
    projects only the claude agent (no ``.codex/`` orphan). AC-5 + AC-11(c): doctor
    reports [ok] for a projected pack file (no false drift on the stub); a stale file
    reads [drift]; a removed file reads [missing] — a stale/absent installed-pack file
    is never silent.

    RED-first (pre-fix): there was no projection at all (the W1 ``_project_pack`` seam
    was a no-op), and a core install re-ran the stub projection over the pack body.
    """
    ws, mgr = _staged_workspace_with_pack_body(tmp_path)
    # Pre-install: the projected claude agent is the core stub.
    assert "[PLUGIN REQUIRED]" in _claude_agent(ws).read_text(encoding="utf-8")

    mgr.install_plugin(ws, _PACK)

    projected = _claude_agent(ws).read_text(encoding="utf-8")
    assert projected == _PACK_BODY_RENDERED
    assert "[PLUGIN REQUIRED]" not in projected
    ledger = JsonPluginStore().read(ws / ".dadaia" / "states")
    assert ledger is not None and ledger.plugins == (_PACK,)
    codex_toml = (ws / ".codex" / "agents" / f"{_AGENT}.toml").read_text(encoding="utf-8")
    assert 'model = "gpt-5.3-codex"' in codex_toml
    assert "gpt-5.5" not in codex_toml

    # Idempotent re-install: every projected file is a hash-compare [skip].
    lines = mgr.install_plugin(ws, _PACK)
    assert all(not ln.startswith("[ok]   ") for ln in lines), lines
    assert _claude_agent(ws).read_text(encoding="utf-8") == _PACK_BODY_RENDERED

    # Core install precedence: keeps the pack body, not the stub.
    mgr.install(ws, target="all", force=True)
    assert _claude_agent(ws).read_text(encoding="utf-8") == _PACK_BODY_RENDERED

    # AC-15: claude-only profile, own workspace — projects only the claude agent.
    profile_root = tmp_path / "profile-root"
    profile_root.mkdir()
    profile_ws, profile_mgr = _staged_workspace_with_pack_body(profile_root, harnesses=("claude",))
    profile_mgr.install_plugin(profile_ws, _PACK)

    assert _claude_agent(profile_ws).read_text(encoding="utf-8") == _PACK_BODY_RENDERED
    # No .codex/ orphan — the claude-only profile never projects a codex agent.
    assert not (profile_ws / ".codex" / "agents" / f"{_AGENT}.toml").exists()
    # The ledger records the pack, not a per-harness selection.
    profile_ledger = JsonPluginStore().read(profile_ws / ".dadaia" / "states")
    assert profile_ledger is not None and profile_ledger.plugins == (_PACK,)

    # AC-5 + AC-11(c): doctor [ok]/[drift]/[missing] on the pack file, own workspace.
    doctor_root = tmp_path / "doctor-root"
    doctor_root.mkdir()
    doctor_ws, doctor_mgr = _staged_workspace_with_pack_body(doctor_root)
    doctor_mgr.install_plugin(doctor_ws, _PACK)
    report = doctor_mgr.doctor(doctor_ws)
    assert f"[ok] plugin:{_PACK}:claude/agents/{_AGENT}.md" in report
    assert f"[drift] claude:agents/{_AGENT}.md" not in report

    doctor_agent = _claude_agent(doctor_ws)
    doctor_agent.write_text("# tampered\n", encoding="utf-8")
    report2 = doctor_mgr.doctor(doctor_ws)
    assert f"[drift] plugin:{_PACK}:claude/agents/{_AGENT}.md" in report2

    doctor_agent.unlink()
    report3 = doctor_mgr.doctor(doctor_ws)
    assert f"[missing] plugin:{_PACK}:claude/agents/{_AGENT}.md" in report3
