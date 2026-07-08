"""v0.1.63 FR2/FR3 — ``uninstall_plugin``: the exact inverse of ``install_plugin``.

AC-2 (the acceptance spine, UPGRADED per Ruling 63-F / QA63-1): an install→uninstall cycle
leaves the runtime surface equivalent to a never-installed workspace, asserted BOTH ways —
(i) same-run A-vs-B self-relative comparison, and (ii) side B's post-uninstall doctor surface
compared against the durable v0.1.60 golden (b) never-installed baseline (READ-ONLY fixture
reuse, zero regen — catches residue classes the same-run comparison is double-blind to,
because plugin doctor goes ledger-blind after the drop). Plus direct byte asserts in the
absent-profile all-targets leg: ``.codex/agents/{frontend-engineer,design-specialist}.toml``
byte-equal the fresh core-stub render and zero pack rule projections remain.

AC-3: double-uninstall no-op; files-before-ledger ordering observable (a failure injected at
the ledger write leaves the ledger entry present — never a silent half-state, ADR-U4);
multi-pack isolation. AC-4: claude-only profile never touches ``.codex/`` (ADR-U3).
AC-5: hand-edited projections are restored/removed NEVER silently (``[drift-restored]`` /
``[drift-removed]`` per file, ADR-U1); ``repos/**`` is never touched.

Layer: integration — real stage/install/doctor via ``FileSystemPublicAssetManager`` +
``tmp_path``. Normalization replicates the golden (b) three-leak-class law
(tests/integration/test_plugin_projection.py, the source of truth).
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from dadaia_workspace.core.models.harness_profile import HarnessProfile
from dadaia_workspace.core.models.plugin_pack import InstalledPlugins
from dadaia_workspace.infrastructure.json_harness_profile_store import JsonHarnessProfileStore
from dadaia_workspace.infrastructure.json_plugin_store import JsonPluginStore
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from tests.helpers.golden_platform import canon_env_line, is_env_doctor_line, norm_path_line

pytestmark = pytest.mark.integration

_HERE = Path(__file__).resolve().parent
_DOCTOR_GOLDEN_B = _HERE / "_golden" / "plugin_doctor_report_golden_b_v0160.json"

_PACK = "frontend-design"
_PACK_AGENTS = ("design-specialist", "frontend-engineer")
_PACK_SKILL_DIR = "browser-frontend-implementation"


# ---------------------------------------------------------------------------
# Golden (b) normalization — tests/helpers/golden_platform.py (v0.1.64 FR1; this file
# was a rebase-discovered 14th duplicate site, adopted alongside the 13).
# ---------------------------------------------------------------------------


def _norm_doctor(report: list[str], ws: Path) -> list[str]:
    return sorted(
        canon_env_line(norm_path_line(line, ws)) for line in report if not is_env_doctor_line(line)
    )


# ---------------------------------------------------------------------------
# Workspace helpers
# ---------------------------------------------------------------------------


def _fresh_ws(
    tmp_path: Path, name: str, harnesses: tuple[str, ...] | None = None
) -> tuple[Path, FileSystemPublicAssetManager]:
    """Stage + core-install a workspace (optionally profile-scoped BEFORE the install)."""
    ws = tmp_path / name
    ws.mkdir()
    if harnesses is not None:
        states = ws / ".dadaia" / "states"
        states.mkdir(parents=True)
        JsonHarnessProfileStore().write(states, HarnessProfile.of(harnesses))
    mgr = FileSystemPublicAssetManager()
    mgr.install(ws, target="all")
    return ws, mgr


def _ledger_plugins(ws: Path) -> tuple[str, ...]:
    ledger = JsonPluginStore().read(ws / ".dadaia" / "states")
    return ledger.plugins if ledger is not None else ()


def _pack_skill_files(ws: Path) -> list[Path]:
    root = ws / ".agents" / "skills" / _PACK_SKILL_DIR
    return sorted(root.rglob("*")) if root.exists() else []


# ---------------------------------------------------------------------------
# AC-2 — never-installed equivalence (the spine; Ruling 63-F upgraded)
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_ac2_install_uninstall_cycle_equals_never_installed(tmp_path: Path) -> None:
    """AC-2: side B (install→uninstall) == side A (never installed) == golden (b).

    Two workspaces in one run — @pytest.mark.slow, bracket ≤ ~15s (QA63-2). Absent-profile
    all-targets leg with the direct .codex byte asserts (QA63-1).

    Sabotage map (AC-8): (a) skip ledger drop ⇒ the ledger assert FAILS; (b) skip skill
    deletion ⇒ the zero-pack-files assert FAILS; (c) skip stub restore ⇒ the stub-body
    byte assert FAILS.
    """
    start = time.monotonic()
    ws_a, mgr_a = _fresh_ws(tmp_path, "never_installed")
    ws_b, mgr_b = _fresh_ws(tmp_path, "install_then_uninstall")

    mgr_b.install_plugin(ws_b, _PACK)
    # Sanity: install genuinely projected the pack (the cycle is non-vacuous).
    assert "[PLUGIN REQUIRED]" not in (
        ws_b / ".claude" / "agents" / "frontend-engineer.md"
    ).read_text(encoding="utf-8")
    assert _pack_skill_files(ws_b), "pack skill projection missing after install"

    mgr_b.uninstall_plugin(ws_b, _PACK)

    # Stub bodies restored byte-equal (claude md) — AC-8(c) discriminator.
    for stem in _PACK_AGENTS:
        a_md = (ws_a / ".claude" / "agents" / f"{stem}.md").read_bytes()
        b_md = (ws_b / ".claude" / "agents" / f"{stem}.md").read_bytes()
        assert b_md == a_md, f"{stem}.md is not the core stub after uninstall"
    # Direct byte asserts, absent-profile all-targets leg (QA63-1): the codex tomls
    # byte-equal the fresh core-stub render (side A IS the fresh render).
    for stem in _PACK_AGENTS:
        a_toml = (ws_a / ".codex" / "agents" / f"{stem}.toml").read_bytes()
        b_toml = (ws_b / ".codex" / "agents" / f"{stem}.toml").read_bytes()
        assert b_toml == a_toml, f"{stem}.toml is not the core-stub render after uninstall"

    # Zero pack files under .agents/skills/ — AC-8(b) discriminator.
    assert _pack_skill_files(ws_b) == [], "pack skill projections survived uninstall"
    # Zero pack rule projections remain: .claude/rules content sets are identical A vs B.
    rules_a = sorted(p.name for p in (ws_a / ".claude" / "rules").rglob("*") if p.is_file())
    rules_b = sorted(p.name for p in (ws_b / ".claude" / "rules").rglob("*") if p.is_file())
    assert rules_a == rules_b, "pack rule projections remain after uninstall"

    # Ledger clean — AC-8(a) discriminator.
    assert _ledger_plugins(ws_b) == (), "installed_plugins.json still lists the pack"
    raw = json.loads(
        (ws_b / ".dadaia" / "states" / "installed_plugins.json").read_text(encoding="utf-8")
    )
    assert raw["plugins"] == []

    # plugin doctor surface: ledger-driven ⇒ zero per-pack lines ([not-applicable] CLI-side).
    assert mgr_b.doctor_plugins(ws_b) == []

    # (i) Same-run self-relative equivalence: doctor runtime surface A == B.
    doctor_a = _norm_doctor(mgr_a.doctor(ws_a), ws_a)
    doctor_b = _norm_doctor(mgr_b.doctor(ws_b), ws_b)
    assert doctor_b == doctor_a, "post-uninstall doctor surface diverges from never-installed"

    # (ii) Absolute anchor (Ruling 63-F): side B == the durable v0.1.60 golden (b)
    # never-installed baseline — READ-ONLY fixture reuse, zero regen.
    golden = sorted(
        canon_env_line(line) for line in json.loads(_DOCTOR_GOLDEN_B.read_text(encoding="utf-8"))
    )
    assert doctor_b == golden, "post-uninstall doctor surface diverges from golden (b)"

    elapsed = time.monotonic() - start
    assert elapsed < 15.0, f"AC-2 equivalence test exceeded its ~15s bracket ({elapsed:.1f}s)"


# ---------------------------------------------------------------------------
# AC-3 — idempotency, files-before-ledger ordering, multi-pack isolation
# ---------------------------------------------------------------------------


def test_ac3_double_uninstall_is_a_noop(tmp_path: Path) -> None:
    """A second uninstall changes nothing — ledger + projected files byte-stable."""
    ws, mgr = _fresh_ws(tmp_path, "ws")
    mgr.install_plugin(ws, _PACK)
    mgr.uninstall_plugin(ws, _PACK)

    ledger_path = ws / ".dadaia" / "states" / "installed_plugins.json"
    ledger_before = ledger_path.read_bytes()
    stub_before = (ws / ".claude" / "agents" / "frontend-engineer.md").read_bytes()

    lines = mgr.uninstall_plugin(ws, _PACK)

    assert ledger_path.read_bytes() == ledger_before
    assert (ws / ".claude" / "agents" / "frontend-engineer.md").read_bytes() == stub_before
    # No mutation lines: everything is a [skip]-class no-op.
    assert all(not ln.startswith(("[ok]", "[rm]", "[drift", "[ledger]")) for ln in lines), lines


class _FailingWriteStore:
    """A PluginStore whose write raises — injects a failure AT the ledger step (ADR-U4)."""

    def __init__(self) -> None:
        self._inner = JsonPluginStore()

    def read(self, states_dir: Path) -> InstalledPlugins | None:
        return self._inner.read(states_dir)

    def write(self, states_dir: Path, installed: InstalledPlugins) -> None:
        raise RuntimeError("injected ledger-write failure (ADR-U4 ordering probe)")


def test_ac3_files_before_ledger_interrupted_uninstall_keeps_ledger_entry(
    tmp_path: Path,
) -> None:
    """ADR-U4 observable: files are restored FIRST; a ledger-write failure leaves the ledger
    entry present, so ``plugin doctor`` still surfaces the pack — never a silent half-state."""
    ws, mgr = _fresh_ws(tmp_path, "ws")
    mgr.install_plugin(ws, _PACK)

    failing = FileSystemPublicAssetManager(plugin_store=_FailingWriteStore())
    with pytest.raises(RuntimeError, match="injected ledger-write failure"):
        failing.uninstall_plugin(ws, _PACK)

    # File phase already ran: the claude agent is back to the stub…
    stub = (ws / ".claude" / "agents" / "frontend-engineer.md").read_text(encoding="utf-8")
    assert "[PLUGIN REQUIRED]" in stub, "file restore did not precede the ledger write"
    # …but the ledger STILL lists the pack (files first, ledger last) ⇒ doctor non-silent.
    assert _ledger_plugins(ws) == (_PACK,)
    assert mgr.doctor_plugins(ws), "plugin doctor went silent on the interrupted half-state"


def test_ac3_multi_pack_isolation_uninstall_devops_keeps_frontend_design(
    tmp_path: Path,
) -> None:
    """With both packs installed, uninstalling devops leaves frontend-design fully intact."""
    ws, mgr = _fresh_ws(tmp_path, "ws")
    mgr.install_plugin(ws, _PACK)
    mgr.install_plugin(ws, "devops")
    fe_body = (ws / ".claude" / "agents" / "frontend-engineer.md").read_bytes()
    assert b"[PLUGIN REQUIRED]" not in fe_body

    mgr.uninstall_plugin(ws, "devops")

    # devops-engineer restored to stub; frontend-design projections byte-intact.
    devops = (ws / ".claude" / "agents" / "devops-engineer.md").read_text(encoding="utf-8")
    assert "[PLUGIN REQUIRED]" in devops
    assert (ws / ".claude" / "agents" / "frontend-engineer.md").read_bytes() == fe_body
    assert _pack_skill_files(ws), "frontend-design skill projection was collaterally removed"
    assert _ledger_plugins(ws) == (_PACK,)
    assert any(f"plugin:{_PACK}:" in ln for ln in mgr.doctor_plugins(ws))
    assert not any("plugin:devops:" in ln for ln in mgr.doctor_plugins(ws))


# ---------------------------------------------------------------------------
# AC-4 — profile-scoped uninstall (ADR-U3, Ruling 13 symmetry)
# ---------------------------------------------------------------------------


def test_ac4_claude_only_profile_uninstall_never_touches_codex(tmp_path: Path) -> None:
    """In a claude-only profile, install→uninstall never creates or deletes under .codex/."""
    ws, mgr = _fresh_ws(tmp_path, "ws", harnesses=("claude",))
    assert not (ws / ".codex").exists()

    mgr.install_plugin(ws, _PACK)
    assert not (ws / ".codex").exists(), "claude-only install created a .codex orphan"

    mgr.uninstall_plugin(ws, _PACK)
    assert not (ws / ".codex").exists(), "claude-only uninstall created a .codex orphan"
    stub = (ws / ".claude" / "agents" / "frontend-engineer.md").read_text(encoding="utf-8")
    assert "[PLUGIN REQUIRED]" in stub


# ---------------------------------------------------------------------------
# AC-5 — drift never silent + repos/** untouched (ADR-U1)
# ---------------------------------------------------------------------------


def test_ac5_hand_edited_projections_emit_drift_lines_and_repos_untouched(
    tmp_path: Path,
) -> None:
    """A hand-edited pack agent md is [drift-restored]; a hand-edited pack skill is
    [drift-removed]; nothing under repos/ is ever touched by uninstall."""
    ws, mgr = _fresh_ws(tmp_path, "ws")
    consumer = ws / "repos" / "game" / "AGENTS.md"
    consumer.parent.mkdir(parents=True)
    consumer_body = "# Hand-authored consumer AGENTS.md\n"
    consumer.write_text(consumer_body, encoding="utf-8")

    mgr.install_plugin(ws, _PACK)

    agent_dst = ws / ".claude" / "agents" / "frontend-engineer.md"
    agent_dst.write_text("# tampered agent projection\n", encoding="utf-8")
    skill_files = _pack_skill_files(ws)
    skill_dst = next(p for p in skill_files if p.is_file())
    skill_dst.write_text("# tampered skill projection\n", encoding="utf-8")

    lines = mgr.uninstall_plugin(ws, _PACK)

    assert any(ln.startswith("[drift-restored]") and str(agent_dst) in ln for ln in lines), lines
    assert any(ln.startswith("[drift-removed]") and str(skill_dst) in ln for ln in lines), lines
    # Restored/removed anyway (lib-owned surface, ADR-U1).
    assert "[PLUGIN REQUIRED]" in agent_dst.read_text(encoding="utf-8")
    assert not skill_dst.exists()
    # repos/** untouched.
    assert consumer.read_text(encoding="utf-8") == consumer_body


def test_unstaged_pack_uninstall_is_ledger_only_and_non_silent(tmp_path: Path) -> None:
    """An unstaged pack ⇒ ledger-only removal with a non-silent [skip]-class line (FR2)."""
    ws = tmp_path / "ws"
    (ws / ".dadaia" / "states").mkdir(parents=True)
    JsonPluginStore().write(ws / ".dadaia" / "states", InstalledPlugins.of((_PACK,)))
    mgr = FileSystemPublicAssetManager()

    lines = mgr.uninstall_plugin(ws, _PACK)

    assert _ledger_plugins(ws) == ()
    assert any("not staged" in ln for ln in lines), lines
