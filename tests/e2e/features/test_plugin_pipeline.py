"""Per-pack sandboxed E2E for the v0.1.60 plugin-pack pipeline (T-60-50, AC-10).

Scaffolds a real workspace in-process via the ``dadaia`` CLI (``CliRunner`` + ``tmp_path``,
mirroring ``test_public_pipeline.py``) and walks the whole plugin surface end-to-end through
the *real* CLI verbs — ``dadaia init``, ``dadaia plugin install``, ``dadaia public install``,
``dadaia public doctor`` — never poking the manager for behaviour the CLI is meant to drive.

Scenarios (AC-10):
  (a) fresh no-plugin → the 3 plugin agents are stubs + descriptors-present-zero-plugin
      ``public doctor`` is green + golden (b) byte-lock (reuses the integration golden (b)
      fixtures + normalization);
  (b) ``plugin install frontend-design`` → both agents carry real pack bodies (Claude md +
      Codex ``gpt-5.3-codex`` toml) + ``installed_plugins.json`` correct + doctor green;
  (c) ``plugin install devops`` → ``devops-engineer`` real;
  (d) a following core ``public install --target all`` keeps the pack bodies (AC-4 precedence);
  (e/FR9, QA-4) a REGISTERED consumer repo with a hand-authored root ``AGENTS.md`` survives
      ``public install --target all`` byte-identical (BOTH paired doctor lines ``[foreign]``)
      and a real ``dadaia public doctor`` run EXITS 0, while a stale-canonical fixture gets
      ``[updated]``;
  (f/QA-5) double ``plugin install frontend-design`` no-ops (``installed_plugins.json``
      byte-unchanged — ledger idempotency);
  (g/QA-5) ``installed_plugins.json`` coexists with ``harness_profile.json`` without
      interference (claude-only profile + pack install → no ``.codex/`` orphan, both state
      files intact).

``tmp_path`` isolates every workspace from the repo (no ``.dadaia/`` inside any repo); the
suite runs ``-p no:cacheprovider``. The autouse ``_no_real_venv_in_tests`` conftest fixture
fakes the venv build so every ``dadaia init`` is a bare mkdir (no disk exhaustion).
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest
from typer.testing import CliRunner, Result

from dadaia_workspace.cli.main import app as cli_app
from dadaia_workspace.infrastructure.json_plugin_store import JsonPluginStore
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.workspace_guardrail import _CANONICAL_AGENTS_BANNER

# NEVER pass mix_stderr (removed in Click 8.2) — QA-atom law (v0.1.57).
_runner = CliRunner()

# The 3 plugin agents (constitution §14) and the harness stems they project to.
_PLUGIN_AGENTS = {
    "frontend-design": ("frontend-engineer", "design-specialist"),
    "devops": ("devops-engineer",),
}

# Discriminating H1 in each REAL pack body (public/plugins/**/agents/*.md, W3 / T-60-30).
_PACK_BODY_HEADING = {
    "frontend-engineer": "# Frontend Engineer [plugin]",
    "design-specialist": "# Design Specialist [plugin]",
    "devops-engineer": "# DevOps Engineer [plugin]",
}

# Hand-authored (repo-owned, no banner) vs stale-canonical (banner + old body) consumers.
_HAND_AUTHORED = "# My Game Repo\n\nHand-authored, repo-specific rules. NOT lib-originated.\n"


# ---------------------------------------------------------------------------
# Golden (b) reuse — the durable descriptors-present, zero-plugin byte-lock.
# Replicates the three-leak-class normalization of tests/integration/
# test_plugin_projection.py (the source of truth) and asserts against the SAME
# committed golden (b) fixtures, so scenario (a)'s byte-lock is the identical lock
# the integration layer owns. If either the normalization or the fixture drifts,
# this reproduction fails — a feature, not a hazard.
# ---------------------------------------------------------------------------

_GOLDEN_DIR = Path(__file__).resolve().parent.parent.parent / "integration" / "_golden"
_DOCTOR_GOLDEN_B = _GOLDEN_DIR / "plugin_doctor_report_golden_b_v0160.json"

_DCX9_WRAPPER_RE = re.compile(
    r"^\[error\] codex hook wrapper .*? (\.dadaia/hooks/\S+?):.*\(D-CX-9\)$"
)


def _norm_path_line(line: str, ws: Path) -> str:
    out = line.replace(ws.as_posix(), "<WS>").replace(str(ws), "<WS>")
    out = out.replace(
        "[ok] public-privacy (baseline structural scan, no operator denylist)",
        "[ok] public-privacy",
    )
    return out.replace("\\", "/")


def _is_env_doctor_line(line: str) -> bool:
    return "git-dirty" in line


def _canon_env_line(line: str) -> str:
    return _DCX9_WRAPPER_RE.sub(r"[error] codex hook wrapper probe failed \1 (D-CX-9)", line)


def _sort_line_lists(obj: object) -> object:
    if isinstance(obj, list) and all(isinstance(x, str) for x in obj):
        return sorted(_canon_env_line(x) for x in obj)
    if isinstance(obj, dict):
        return {k: _sort_line_lists(v) for k, v in obj.items()}
    return obj


def _capture_doctor(tmp_path: Path) -> list[str]:
    ws = tmp_path / "doctor_all_four"
    ws.mkdir()
    mgr = FileSystemPublicAssetManager()
    mgr.install(ws, target="all")
    report = mgr.doctor(ws)
    return [_norm_path_line(line, ws) for line in report if not _is_env_doctor_line(line)]


def _assert_matches_golden(path: Path, current_obj: object, what: str) -> None:
    current = (
        json.dumps(_sort_line_lists(current_obj), indent=2, ensure_ascii=False, sort_keys=True)
        + "\n"
    )
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
        f"{what} diverged from the committed v0.1.60 golden (b) — the descriptors-present "
        "zero-plugin baseline changed. Fix the consumer, never the golden."
    )


# ---------------------------------------------------------------------------
# CLI + workspace helpers
# ---------------------------------------------------------------------------


def _init(ws: Path, harness: str | None = None) -> Path:
    """Scaffold *ws* via the real ``dadaia init`` CLI (in-process, venv faked by conftest)."""
    args = ["init", "--workspace", str(ws)]
    if harness is not None:
        args += ["--harness", harness]
    result = _runner.invoke(cli_app, args)
    assert result.exit_code == 0, result.output
    return ws


def _cli(monkeypatch: pytest.MonkeyPatch, ws: Path, *args: str) -> Result:
    """Invoke a workspace-resolving CLI verb from inside *ws* (resolve_workspace_root walks cwd)."""
    monkeypatch.chdir(ws)
    return _runner.invoke(cli_app, list(args))


def _claude_agent_text(ws: Path, stem: str) -> str:
    return (ws / ".claude" / "agents" / f"{stem}.md").read_text(encoding="utf-8")


def _is_plugin_stub(content: str) -> bool:
    """A projected plugin stub declares ``plugin: true`` in frontmatter (the durable
    discriminator). W3 (T-60-30) rewrote the ``plugin-scope`` RULE to install-gated wording
    but intentionally left the stub AGENT bodies unchanged, so ``plugin: true`` — not any body
    phrase — is the stable stub marker (mirrors ``test_public_pipeline._is_plugin_stub``)."""
    if not content.startswith("---\n"):
        return False
    end = content.find("\n---\n", 4)
    if end == -1:
        return False
    return bool(re.search(r"^plugin:\s*true\b", content[4:end], re.MULTILINE))


def _assert_real_pack_body(ws: Path, stem: str) -> None:
    text = _claude_agent_text(ws, stem)
    assert not _is_plugin_stub(text), f"{stem} is still a stub after install"
    assert _PACK_BODY_HEADING[stem] in text, f"{stem} missing its real pack-body heading"
    assert "[PLUGIN REQUIRED]" not in text, f"{stem} still carries stub [PLUGIN REQUIRED]"


def _ledger_plugins(ws: Path) -> tuple[str, ...]:
    installed = JsonPluginStore().read(ws / ".dadaia" / "states")
    return installed.plugins if installed is not None else ()


def _no_doctor_blockers(report: list[str]) -> list[str]:
    return [ln for ln in report if ln.startswith(("[missing]", "[drift]", "[fail]"))]


def _register_consumers(ws: Path, entries: list[tuple[str, str]]) -> None:
    """Write spec_contexts.json (schema-v2) so the guardrail fan-out reaches *entries*.

    *entries* are ``(slug, agents_md_content)`` pairs; each consumer dir is created under
    ``<ws>/repos/<slug>/`` with the given root ``AGENTS.md``.
    """
    contexts = []
    for slug, agents_md in entries:
        repo = ws / "repos" / slug
        repo.mkdir(parents=True, exist_ok=True)
        (repo / "AGENTS.md").write_text(agents_md, encoding="utf-8")
        contexts.append(
            {
                "name": slug,
                "state": "alive",
                "repo_slug": slug,
                "repo_url": f"https://example.test/{slug}.git",
                "created_at": "2026-07-04T00:00:00Z",
                "alive_since": "2026-07-04T00:00:00Z",
                "dead_since": None,
                "current_branch": "main",
            }
        )
    (ws / ".dadaia" / "states" / "spec_contexts.json").write_text(
        json.dumps({"schema_version": "2", "contexts": contexts}, indent=2), encoding="utf-8"
    )


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _squash(output: str) -> str:
    """ANSI-strip + drop all whitespace — robust against Rich hard-wrapping long absolute
    paths across lines in a no-tty ``CliRunner`` capture (default width 80)."""
    return re.sub(r"\s+", "", _ANSI_RE.sub("", output))


# ---------------------------------------------------------------------------
# (a) fresh no-plugin — stubs + zero-plugin doctor green + golden (b) byte-lock
# ---------------------------------------------------------------------------


def test_a_fresh_no_plugin_stubs_doctor_green_and_golden_b_bytelock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws = _init(tmp_path / "ws", "all")

    # The 3 plugin agents project as stubs (plugin: true), NOT real pack bodies.
    for agents in _PLUGIN_AGENTS.values():
        for stem in agents:
            text = _claude_agent_text(ws, stem)
            assert _is_plugin_stub(text), f"{stem} should be a plugin stub in a no-plugin workspace"
            assert _PACK_BODY_HEADING[stem] not in text, f"{stem} unexpectedly carries a pack body"

    # No plugin installed → empty ledger (absent file ⇒ no packs).
    assert _ledger_plugins(ws) == ()

    # golden (b) byte-lock — installing zero plugins leaves the descriptors-present doctor
    # baseline byte-identical to the committed integration golden (b) (the richer surface;
    # the install-targets golden (b) is redundantly locked at the integration layer —
    # tests/integration/test_plugin_projection.py — so it is not re-run here to keep the
    # E2E module comfortably inside its ~10s wall-time bound).
    zero_plugin_doctor = _capture_doctor(tmp_path)
    _assert_matches_golden(_DOCTOR_GOLDEN_B, zero_plugin_doctor, "doctor golden b")

    # descriptors-present, zero-plugin doctor is GREEN — no [missing]/[drift] blockers (derived
    # from the same single golden capture; the real `dadaia public doctor` CLI exit-0 surface is
    # exercised by scenario (b) on an installed workspace and both (e) tests).
    assert _no_doctor_blockers(zero_plugin_doctor) == [], zero_plugin_doctor


# ---------------------------------------------------------------------------
# (b)+(c)+(d) install chain on ONE workspace — frontend-design (both agents real +
# codex plugin-tier render + ledger + doctor green), then devops (devops-engineer real),
# then a core `public install --target all` that keeps all pack bodies (AC-4 precedence).
# Merged into a single pipeline (one `dadaia init`) to keep the module well inside its
# ~10s wall-time bound; the (d) precedence sabotage still fails HERE, attributably.
# ---------------------------------------------------------------------------


def test_bcd_install_chain_and_core_reinstall_precedence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws = _init(tmp_path / "ws", "all")

    # (b) plugin install frontend-design → BOTH agents carry real pack bodies over the stub.
    result = _cli(monkeypatch, ws, "plugin", "install", "frontend-design")
    assert result.exit_code == 0, result.output
    _assert_real_pack_body(ws, "frontend-engineer")
    _assert_real_pack_body(ws, "design-specialist")
    # Codex render is on the sonnet/plugin tier (gpt-5.3-codex), NOT opus (gpt-5.5).
    for stem in _PLUGIN_AGENTS["frontend-design"]:
        toml = (ws / ".codex" / "agents" / f"{stem}.toml").read_text(encoding="utf-8")
        assert 'model = "gpt-5.3-codex"' in toml, f"{stem} codex render not on the plugin tier"
        assert "gpt-5.5" not in toml, f"{stem} codex render leaked the opus model"
    # Ledger records the pack (schema v1); doctor stays green with a pack installed.
    assert _ledger_plugins(ws) == ("frontend-design",)
    raw = json.loads(
        (ws / ".dadaia" / "states" / "installed_plugins.json").read_text(encoding="utf-8")
    )
    assert raw == {"schema_version": "1", "plugins": ["frontend-design"]}
    assert _cli(monkeypatch, ws, "public", "doctor").exit_code == 0

    # (c) plugin install devops → devops-engineer real; ledger accumulates the pack.
    assert _cli(monkeypatch, ws, "plugin", "install", "devops").exit_code == 0
    _assert_real_pack_body(ws, "devops-engineer")
    assert set(_ledger_plugins(ws)) == {"frontend-design", "devops"}

    # (d) a following core `public install --target all` MUST NOT silently revert an installed
    # pack agent to its stub (AC-4 precedence).
    result = _cli(monkeypatch, ws, "public", "install", "--target", "all")
    assert result.exit_code == 0, result.output
    for stem in ("frontend-engineer", "design-specialist", "devops-engineer"):
        _assert_real_pack_body(ws, stem)
    assert set(_ledger_plugins(ws)) == {"frontend-design", "devops"}


# ---------------------------------------------------------------------------
# (e/FR9, QA-4) registered hand-authored consumer — the INSTALL half (provenance gate, the
# banner-drop sabotage target) and the DOCTOR half (Ruling 16). The doctor half was xfail
# against the HIGH bug `public-doctor-flags-hand-authored-consumer-agents-md` (the FR9
# provenance gate was wired only into the unreferenced `_doctor_guardrail_pair`, never into the
# real `manager.doctor()` consumer fan-out). The T-60-45 fix round routed the consumer
# `repos/<slug>:` lines through the single `_doctor_consumer_pair_lines` authority that
# `manager.doctor()` now calls (removed from `runtime_expectations`), so this test PASSES and
# the xfail marker was removed.
# ---------------------------------------------------------------------------


def _install_with_registered_consumers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, Result]:
    """Init an all-harness workspace, register a hand-authored + a stale-canonical consumer,
    run the real `dadaia public install --target all`, and return (ws, install_result)."""
    ws = _init(tmp_path / "ws", "all")
    stale_canonical = _CANONICAL_AGENTS_BANNER + "\n# OLD workspace-law body\n"
    _register_consumers(ws, [("game", _HAND_AUTHORED), ("stale", stale_canonical)])
    result = _cli(monkeypatch, ws, "public", "install", "--target", "all")
    assert result.exit_code == 0, result.output
    return ws, result


def test_e_install_registered_hand_authored_consumer_survives_byte_identical(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    game_before = _HAND_AUTHORED
    ws, result = _install_with_registered_consumers(tmp_path, monkeypatch)
    game_agents = ws / "repos" / "game" / "AGENTS.md"
    stale_agents = ws / "repos" / "stale" / "AGENTS.md"

    # INSTALL side (provenance gate): the hand-authored consumer survives byte-identical, no
    # CLAUDE.md orphan; the stale-canonical (banner-bearing) copy is restored + [updated].
    # Install lines carry ABSOLUTE tmp paths that Rich hard-wraps, so match on the squashed blob.
    squashed = _squash(result.output)
    assert game_agents.read_text(encoding="utf-8") == game_before, (
        "hand-authored AGENTS.md clobbered"
    )
    assert not (ws / "repos" / "game" / "CLAUDE.md").exists(), "CLAUDE.md orphan beside foreign"
    assert "[foreign]" in squashed and "repos/game/AGENTS.md—leftuntouched" in squashed, (
        result.output
    )
    assert stale_agents.read_text(encoding="utf-8").startswith(_CANONICAL_AGENTS_BANNER)
    assert _sha(stale_agents) == _sha(ws / ".dadaia" / "agentic" / "data" / "AGENTS.md")
    assert "[updated]" in squashed and "repos/stale/AGENTS.md" in squashed, result.output


def test_e_public_doctor_exits_zero_for_hand_authored_consumer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws, _ = _install_with_registered_consumers(tmp_path, monkeypatch)

    # DOCTOR side (Ruling 16, CRITICAL): BOTH paired lines for the hand-authored consumer are
    # [foreign] and `dadaia public doctor` EXITS 0 — a hand-authored consumer repo is NOT a
    # perpetual drift. Doctor lines are written to stderr AND stdout; CliRunner merges them.
    doctor = _cli(monkeypatch, ws, "public", "doctor")
    out = doctor.output
    assert "[foreign] repos/game:AGENTS.md" in out, out
    assert "[foreign] repos/game:CLAUDE.md" in out, out
    assert doctor.exit_code == 0, (
        "`dadaia public doctor` must EXIT 0 for a registered hand-authored consumer repo "
        f"(Ruling 16). Output:\n{out}"
    )


# ---------------------------------------------------------------------------
# (f/QA-5) double plugin install — ledger idempotency (byte-unchanged)
# ---------------------------------------------------------------------------


def test_f_double_install_frontend_design_ledger_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws = _init(tmp_path / "ws", "all")
    ledger_path = ws / ".dadaia" / "states" / "installed_plugins.json"

    assert _cli(monkeypatch, ws, "plugin", "install", "frontend-design").exit_code == 0
    first = ledger_path.read_bytes()

    result = _cli(monkeypatch, ws, "plugin", "install", "frontend-design")
    assert result.exit_code == 0, result.output
    assert "already installed" in result.output, result.output

    assert ledger_path.read_bytes() == first, "re-install mutated installed_plugins.json"
    assert _ledger_plugins(ws) == ("frontend-design",)
    _assert_real_pack_body(ws, "frontend-engineer")


# ---------------------------------------------------------------------------
# (g/QA-5) installed_plugins.json coexists with harness_profile.json (profile×pack)
# ---------------------------------------------------------------------------


def test_g_installed_plugins_coexists_with_harness_profile_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws = _init(tmp_path / "ws", "claude")  # claude-only profile
    profile_path = ws / ".dadaia" / "states" / "harness_profile.json"
    profile_before = profile_path.read_bytes()
    assert json.loads(profile_before)["harnesses"] == ["claude"]

    result = _cli(monkeypatch, ws, "plugin", "install", "frontend-design")
    assert result.exit_code == 0, result.output

    # Both state files intact and independent: profile byte-unchanged, ledger records the pack.
    assert profile_path.read_bytes() == profile_before, "pack install mutated harness_profile.json"
    assert _ledger_plugins(ws) == ("frontend-design",)

    # Profile-scoped projection: the claude body is real; NO .codex/ orphan for an
    # out-of-profile harness.
    _assert_real_pack_body(ws, "frontend-engineer")
    assert not (ws / ".codex" / "agents" / "frontend-engineer.toml").exists(), "codex orphan"
    assert not (ws / ".codex").exists() or not any((ws / ".codex").rglob("frontend-engineer*"))


# ---------------------------------------------------------------------------
# (h/v0.1.63 T-63-11) install → uninstall → REINSTALL through the real CLI —
# uninstall restores the stubs + drops the ledger, and reinstall lands the real
# pack bodies again, proving uninstall leaves a fully re-installable state.
# @pytest.mark.slow, per-test wall-time bracket ≤ ~12s (QA63-2).
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_h_install_uninstall_reinstall_leaves_reinstallable_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import time

    start = time.monotonic()
    ws = _init(tmp_path / "ws", "all")

    # Install: real pack bodies land.
    assert _cli(monkeypatch, ws, "plugin", "install", "frontend-design").exit_code == 0
    _assert_real_pack_body(ws, "frontend-engineer")
    _assert_real_pack_body(ws, "design-specialist")
    assert _ledger_plugins(ws) == ("frontend-design",)

    # Uninstall via the real CLI verb: stubs restored, ledger dropped, doctor green.
    result = _cli(monkeypatch, ws, "plugin", "uninstall", "frontend-design")
    assert result.exit_code == 0, result.output
    assert "frontend-engineer" in result.output and "design-specialist" in result.output
    for stem in _PLUGIN_AGENTS["frontend-design"]:
        assert _is_plugin_stub(_claude_agent_text(ws, stem)), f"{stem} not a stub post-uninstall"
    assert _ledger_plugins(ws) == ()
    doctor = _cli(monkeypatch, ws, "plugin", "doctor")
    assert doctor.exit_code == 0, doctor.output
    assert "no plugin packs installed" in doctor.output
    assert _cli(monkeypatch, ws, "public", "doctor").exit_code == 0

    # Reinstall: the real bodies land AGAIN — the uninstalled state is re-installable.
    result = _cli(monkeypatch, ws, "plugin", "install", "frontend-design")
    assert result.exit_code == 0, result.output
    _assert_real_pack_body(ws, "frontend-engineer")
    _assert_real_pack_body(ws, "design-specialist")
    assert _ledger_plugins(ws) == ("frontend-design",)
    toml = (ws / ".codex" / "agents" / "frontend-engineer.toml").read_text(encoding="utf-8")
    assert 'model = "gpt-5.3-codex"' in toml, "reinstall did not re-land the pack codex render"

    elapsed = time.monotonic() - start
    assert elapsed < 12.0, f"reinstall e2e leg exceeded its ~12s bracket ({elapsed:.1f}s)"
