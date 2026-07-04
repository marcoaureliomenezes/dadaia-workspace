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

import json
import os
import re
from pathlib import Path

import pytest

from dadaia_workspace.core.models.harness_profile import HarnessProfile
from dadaia_workspace.infrastructure.json_harness_profile_store import JsonHarnessProfileStore
from dadaia_workspace.infrastructure.json_plugin_store import JsonPluginStore
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager

pytestmark = pytest.mark.integration

_HERE = Path(__file__).resolve().parent
_GOLDEN_DIR = _HERE / "_golden"
_INSTALL_GOLDEN_B = _GOLDEN_DIR / "plugin_install_targets_golden_b_v0160.json"
_DOCTOR_GOLDEN_B = _GOLDEN_DIR / "plugin_doctor_report_golden_b_v0160.json"

_INSTALL_TARGETS = ("all", "agents", "claude", "codex", "pi")


# ---------------------------------------------------------------------------
# Normalization helpers (v0.1.55 path/version + v0.1.58 three-leak-class law)
# ---------------------------------------------------------------------------


def _norm_path_line(line: str, ws: Path) -> str:
    out = line.replace(ws.as_posix(), "<WS>").replace(str(ws), "<WS>")
    out = out.replace(
        "[ok] public-privacy (baseline structural scan, no operator denylist)",
        "[ok] public-privacy",
    )
    return out.replace("\\", "/")


def _is_env_doctor_line(line: str) -> bool:
    return "git-dirty" in line


_DCX9_WRAPPER_RE = re.compile(
    r"^\[error\] codex hook wrapper .*? (\.dadaia/hooks/\S+?):.*\(D-CX-9\)$"
)


def _canon_env_line(line: str) -> str:
    return _DCX9_WRAPPER_RE.sub(r"[error] codex hook wrapper probe failed \1 (D-CX-9)", line)


def _sort_line_lists(obj: object) -> object:
    if isinstance(obj, list) and all(isinstance(x, str) for x in obj):
        return sorted(_canon_env_line(x) for x in obj)
    if isinstance(obj, dict):
        return {k: _sort_line_lists(v) for k, v in obj.items()}
    return obj


# ---------------------------------------------------------------------------
# Capture functions (descriptors present, ZERO plugin installed)
# ---------------------------------------------------------------------------


def _capture_install(tmp_path: Path) -> dict[str, list[str]]:
    mgr = FileSystemPublicAssetManager()
    result: dict[str, list[str]] = {}
    for target in _INSTALL_TARGETS:
        ws = tmp_path / f"install_{target}"
        ws.mkdir()
        installed = mgr.install(ws, target=target)
        result[target] = [_norm_path_line(line, ws) for line in installed]
    return result


def _capture_doctor(tmp_path: Path) -> list[str]:
    ws = tmp_path / "doctor_all_four"
    ws.mkdir()
    mgr = FileSystemPublicAssetManager()
    mgr.install(ws, target="all")
    report = mgr.doctor(ws)
    return [_norm_path_line(line, ws) for line in report if not _is_env_doctor_line(line)]


def _assert_golden(path: Path, current_obj: object, what: str) -> None:
    current_obj = _sort_line_lists(current_obj)
    current = json.dumps(current_obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if os.environ.get("UPDATE_INSTALL_GOLDENS"):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(current, encoding="utf-8")
        pytest.skip(f"regenerated {what} golden (UPDATE_INSTALL_GOLDENS set)")
    golden = (
        json.dumps(
            _sort_line_lists(json.loads(path.read_text(encoding="utf-8"))),
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n"
    )
    assert current == golden, (
        f"{what} diverged from the committed v0.1.60 golden (b) — installing zero plugins "
        "changed the descriptors-present baseline. Fix the consumer, never the golden."
    )


# ---------------------------------------------------------------------------
# Golden (b) tests — the durable descriptors-present zero-plugin byte-lock
# ---------------------------------------------------------------------------


def test_descriptors_present_zero_plugin_install_equals_golden_b(tmp_path: Path) -> None:
    """AC-5: install() (all targets) with descriptors present + no plugin == golden (b)."""
    _assert_golden(_INSTALL_GOLDEN_B, _capture_install(tmp_path), "plugin-golden-b-install-targets")


def test_absent_plugin_doctor_byte_equals_golden_b(tmp_path: Path) -> None:
    """AC-5: doctor() with descriptors present + no plugin installed == golden (b)."""
    _assert_golden(_DOCTOR_GOLDEN_B, _capture_doctor(tmp_path), "plugin-golden-b-doctor-report")


def test_golden_b_includes_descriptor_stage_lines(tmp_path: Path) -> None:
    """Guard: golden (b) is the descriptors-present baseline — it INCLUDES stage:plugins/*.

    This is what distinguishes golden (b) from the plugin-blind golden (a). If the
    descriptor-source lines ever vanish from golden (b), the byte-lock would stop covering
    the new staging inventory.
    """
    doctor = _capture_doctor(tmp_path)
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


def test_plugin_install_projects_real_body_over_stub(tmp_path: Path) -> None:
    """AC-3: install_plugin overwrites the core stub with the pack body + records the ledger.

    RED-first: pre-projection-code there was no projection at all (the W1 `_project_pack`
    seam was a no-op), so `.claude/agents/frontend-engineer.md` stayed the stub.
    """
    ws, mgr = _staged_workspace_with_pack_body(tmp_path)
    # Pre-install: the projected claude agent is the core stub.
    assert "[PLUGIN REQUIRED]" in _claude_agent(ws).read_text(encoding="utf-8")

    mgr.install_plugin(ws, _PACK)

    projected = _claude_agent(ws).read_text(encoding="utf-8")
    assert projected == _PACK_BODY
    assert "[PLUGIN REQUIRED]" not in projected
    # Ledger records the pack (not per-harness).
    ledger = JsonPluginStore().read(ws / ".dadaia" / "states")
    assert ledger is not None and ledger.plugins == (_PACK,)
    # Codex toml is the pack render on the sonnet/plugin tier (gpt-5.3-codex), not opus.
    codex_toml = (ws / ".codex" / "agents" / f"{_AGENT}.toml").read_text(encoding="utf-8")
    assert 'model = "gpt-5.3-codex"' in codex_toml
    assert "gpt-5.5" not in codex_toml


def test_plugin_install_is_idempotent(tmp_path: Path) -> None:
    """AC-3: a re-install is a no-op — every projected file is a hash-compare [skip]."""
    ws, mgr = _staged_workspace_with_pack_body(tmp_path)
    mgr.install_plugin(ws, _PACK)
    lines = mgr.install_plugin(ws, _PACK)
    assert all(not ln.startswith("[ok]   ") for ln in lines), lines
    assert _claude_agent(ws).read_text(encoding="utf-8") == _PACK_BODY


def test_core_install_keeps_pack_body_precedence(tmp_path: Path) -> None:
    """AC-4: a following core `install(target=all)` keeps the pack body, not the stub.

    RED-first: pre-precedence-code, a core install re-ran the stub projection over the pack
    body (the clobber the ledger-read now prevents).
    """
    ws, mgr = _staged_workspace_with_pack_body(tmp_path)
    mgr.install_plugin(ws, _PACK)
    assert _claude_agent(ws).read_text(encoding="utf-8") == _PACK_BODY

    mgr.install(ws, target="all", force=True)

    assert _claude_agent(ws).read_text(encoding="utf-8") == _PACK_BODY


def test_claude_only_profile_projects_no_codex_orphan(tmp_path: Path) -> None:
    """AC-15: in a claude-only profile, install_plugin projects only the claude agent."""
    ws, mgr = _staged_workspace_with_pack_body(tmp_path, harnesses=("claude",))
    mgr.install_plugin(ws, _PACK)

    assert _claude_agent(ws).read_text(encoding="utf-8") == _PACK_BODY
    # No .codex/ orphan — the claude-only profile never projects a codex agent.
    assert not (ws / ".codex" / "agents" / f"{_AGENT}.toml").exists()
    # The ledger records the pack, not a per-harness selection.
    ledger = JsonPluginStore().read(ws / ".dadaia" / "states")
    assert ledger is not None and ledger.plugins == (_PACK,)


def test_doctor_reports_installed_pack_ok(tmp_path: Path) -> None:
    """AC-5: doctor reports [ok] for the projected pack file (and no false drift on the stub)."""
    ws, mgr = _staged_workspace_with_pack_body(tmp_path)
    mgr.install_plugin(ws, _PACK)
    report = mgr.doctor(ws)
    assert f"[ok] plugin:{_PACK}:claude/agents/{_AGENT}.md" in report
    # The core loop no longer emits a stub-vs-projection line for the overridden agent.
    assert f"[drift] claude:agents/{_AGENT}.md" not in report


def test_doctor_non_silent_on_stale_pack_file(tmp_path: Path) -> None:
    """AC-5 + AC-11(c): a stale/absent installed-pack file is never silent."""
    ws, mgr = _staged_workspace_with_pack_body(tmp_path)
    mgr.install_plugin(ws, _PACK)

    # Tamper: drift.
    _claude_agent(ws).write_text("# tampered\n", encoding="utf-8")
    report = mgr.doctor(ws)
    assert f"[drift] plugin:{_PACK}:claude/agents/{_AGENT}.md" in report

    # Remove: missing.
    _claude_agent(ws).unlink()
    report = mgr.doctor(ws)
    assert f"[missing] plugin:{_PACK}:claude/agents/{_AGENT}.md" in report
