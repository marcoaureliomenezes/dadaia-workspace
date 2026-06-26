"""E2E regression tests for opencode-runtime-parity-hardening-v1.

Exercises the REAL public asset pipeline (stage -> install -> doctor) against a
tmp workspace, so the actual agent transform and plugin projection are covered:

  T-OC-06 / FR-OC-6:
    - no `color:` in any .opencode/agents/*.md (all agents)
    - source agents with color metadata keep it only outside OpenCode
    - per-agent `permission:` block in .opencode projections (allow/deny mapping)
    - `.opencode/plugins/sdd-gate.ts` projected
    - `.opencode/plugins/ctx-inject.ts` uses the migrated chat.message signature
    - `dadaia public doctor` reports no [drift]/[missing]

  T-AC-08 / FR-AC-3:
    - `dadaia-handoff-emitter` present in the 6 migrated agents (source + projections)
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager

# No default public agents currently declare `color:` metadata.
COLOR_AGENTS: set[str] = set()
# Agents migrated to handoff-emitter in Track C.
MIGRATED_AGENTS = {
    "qa-engineer",
    "security-reviewer",
    "code-reviewer",
}


def _install(tmp_path: Path) -> tuple[FileSystemPublicAssetManager, Path]:
    workspace = tmp_path / "ws"
    mgr = FileSystemPublicAssetManager()
    mgr.install(workspace, target="all", force=True)
    return mgr, workspace


def _opencode_agents(workspace: Path) -> list[Path]:
    return sorted((workspace / ".opencode" / "agents").glob("*.md"))


def _claude_agents(workspace: Path) -> list[Path]:
    return sorted((workspace / ".claude" / "agents").glob("*.md"))


# ---------------------------------------------------------------------------
# T-OC-06 — color strip + parity
# ---------------------------------------------------------------------------


class TestColorStripParity:
    def test_no_color_in_any_opencode_agent(self, tmp_path: Path) -> None:
        _install(tmp_path)
        offenders = [
            p.name
            for p in _opencode_agents(tmp_path / "ws")
            if any(line.startswith("color:") for line in p.read_text("utf-8").splitlines())
        ]
        assert offenders == [], f"color: leaked into OpenCode projection: {offenders}"

    def test_color_preserved_in_claude_for_color_agents(self, tmp_path: Path) -> None:
        _install(tmp_path)
        for agent in COLOR_AGENTS:
            content = (tmp_path / "ws" / ".claude" / "agents" / f"{agent}.md").read_text("utf-8")
            assert any(line.startswith("color:") for line in content.splitlines()), (
                f"color: missing from Claude projection of {agent} (parity broken)"
            )

    def test_color_agents_exist_in_both_projections(self, tmp_path: Path) -> None:
        _install(tmp_path)
        oc = {p.stem for p in _opencode_agents(tmp_path / "ws")}
        cc = {p.stem for p in _claude_agents(tmp_path / "ws")}
        assert oc >= COLOR_AGENTS
        assert cc >= COLOR_AGENTS


# ---------------------------------------------------------------------------
# T-OC-06 — permission projection
# ---------------------------------------------------------------------------


class TestPermissionProjection:
    def test_permission_block_present_in_opencode(self, tmp_path: Path) -> None:
        _install(tmp_path)
        # software-engineer declares Read/Write/Edit/Bash/Glob.
        content = (tmp_path / "ws" / ".opencode" / "agents" / "software-engineer.md").read_text(
            "utf-8"
        )
        assert "permission:" in content
        assert "edit: allow" in content
        assert "bash: allow" in content

    def test_agent_without_bash_denies_bash(self, tmp_path: Path) -> None:
        _install(tmp_path)
        # product-engineer declares Read/Glob/Grep/Write/Edit — no Bash, no WebFetch.
        content = (tmp_path / "ws" / ".opencode" / "agents" / "product-engineer.md").read_text(
            "utf-8"
        )
        assert "bash: deny" in content
        assert "task: deny" in content

    def test_no_permission_block_in_claude(self, tmp_path: Path) -> None:
        _install(tmp_path)
        # permission: is OpenCode-only; Claude projection must not carry it.
        content = (tmp_path / "ws" / ".claude" / "agents" / "software-engineer.md").read_text(
            "utf-8"
        )
        assert "permission:" not in content


# ---------------------------------------------------------------------------
# T-OC-06 — plugins
# ---------------------------------------------------------------------------


class TestPluginProjection:
    def test_sdd_gate_plugin_projected(self, tmp_path: Path) -> None:
        _install(tmp_path)
        plugin = tmp_path / "ws" / ".opencode" / "plugins" / "sdd-gate.ts"
        assert plugin.is_file()
        text = plugin.read_text("utf-8")
        assert "tool.execute.before" in text
        # T-018-19 / ADR-7: the plugin invokes the Python governance hook directly
        # (no bash, no .sh dependency — required for stock-Windows governance).
        assert "dadaia_workspace.hooks.sdd_gate" in text
        assert "sdd-spec-gate.sh" not in text

    def test_ctx_inject_uses_migrated_signature(self, tmp_path: Path) -> None:
        _install(tmp_path)
        plugin = tmp_path / "ws" / ".opencode" / "plugins" / "ctx-inject.ts"
        text = plugin.read_text("utf-8")
        assert "chat.message" in text
        assert "output.parts" in text  # new mutate-output pattern


# ---------------------------------------------------------------------------
# T-23-04 — OpenCode Layer-1 gate content-invariant parity (WS-6)
# ---------------------------------------------------------------------------


class TestSddGatePluginContentInvariants:
    """The OpenCode `sdd-gate.ts` plugin must carry the SAME content invariants the
    PI Ring-1 extension test asserts (see test_public_assets
    `test_install_target_pi_projects_ring1_sdd_gate_extension`): single-gate
    delegation, the write/edit tool-name mapping, fail-open default, venv resolution
    without bash, and the explicit block-envelope check. These are the deeper
    invariants the existing `TestPluginProjection` projection/delegation checks do
    NOT cover — assert against the projected plugin's real body."""

    def _plugin_body(self, tmp_path: Path) -> str:
        _install(tmp_path)
        plugin = tmp_path / "ws" / ".opencode" / "plugins" / "sdd-gate.ts"
        assert plugin.is_file()
        return plugin.read_text("utf-8")

    def test_delegates_to_single_python_gate(self, tmp_path: Path) -> None:
        body = self._plugin_body(tmp_path)
        # Single source of truth — policy is never re-derived in TS.
        assert "dadaia_workspace.hooks.sdd_gate" in body
        assert "gate_policy" in body  # docstring names the Python policy it defers to

    def test_tool_name_mapping_to_canonical_write_edit_vocabulary(self, tmp_path: Path) -> None:
        body = self._plugin_body(tmp_path)
        # OpenCode's write/exec tool names (incl. naming variants) map to the gate's
        # canonical WRITE_TOOLS vocabulary; the canonical write/edit verbs and the
        # variant aliases must all be present.
        assert "WRITE_TOOLS" in body
        for tool in ("write", "edit", "write_file", "edit_file", "apply_patch"):
            assert f'"{tool}"' in body, f"missing write-tool mapping for {tool}"
        # Non-write tools are skipped (only WRITE_TOOLS are gated).
        assert "WRITE_TOOLS.has(input.tool)" in body

    def test_fail_open_default_any_error_allows(self, tmp_path: Path) -> None:
        body = self._plugin_body(tmp_path)
        # Only the deliberate SDD block is re-thrown; every other error is swallowed
        # (fail-open) — a crash must never block a legitimate edit.
        assert 'err.message.startsWith("[SDD GATE]")' in body
        assert "fail-open" in body.lower()

    def test_blocks_only_on_explicit_block_envelope(self, tmp_path: Path) -> None:
        body = self._plugin_body(tmp_path)
        # Blocks ONLY when the Python gate returns the explicit decision envelope,
        # surfaced as a thrown `[SDD GATE]` error.
        assert '"decision":"block"' in body or '"decision": "block"' in body
        assert "[SDD GATE]" in body
        assert "throw new Error" in body

    def test_venv_resolution_without_bash(self, tmp_path: Path) -> None:
        body = self._plugin_body(tmp_path)
        # ADR-7: the venv Python binary is resolved with NO bash dependency — no .sh
        # script is shelled out to.
        assert ".venv" in body and "python" in body.lower()
        assert "resolvePythonBin" in body
        # No `.sh` gate script is invoked — the prior shell entrypoint is gone; the
        # Python hook is invoked directly as a module (no `bash <script>.sh`).
        assert "sdd-spec-gate.sh" not in body
        assert "-m dadaia_workspace.hooks.sdd_gate" in body
        assert "Scripts" in body  # Windows venv fallback (cross-platform, no bash)


# ---------------------------------------------------------------------------
# T-OC-06 — doctor clean
# ---------------------------------------------------------------------------


class TestDoctorNoDrift:
    def test_doctor_reports_no_drift_or_missing(self, tmp_path: Path) -> None:
        mgr, workspace = _install(tmp_path)
        lines = mgr.doctor(workspace)
        bad = [ln for ln in lines if "[drift]" in ln or "[missing]" in ln]
        assert bad == [], "doctor reported drift/missing after force install:\n" + "\n".join(bad)


# ---------------------------------------------------------------------------
# T-AC-08 — handoff-emitter migration
# ---------------------------------------------------------------------------


class TestHandoffEmitterMigration:
    def test_source_agents_have_handoff_emitter(self) -> None:
        # Source of truth: dadaia_workspace/public/agents/<name>.md
        repo_root = Path(__file__).resolve().parents[3]
        agents_dir = repo_root / "dadaia_workspace" / "public" / "agents"
        for agent in MIGRATED_AGENTS:
            content = (agents_dir / f"{agent}.md").read_text("utf-8")
            assert "dadaia-handoff-emitter" in content, f"{agent} source missing handoff-emitter"

    def test_opencode_projection_has_handoff_emitter(self, tmp_path: Path) -> None:
        _install(tmp_path)
        for agent in MIGRATED_AGENTS:
            content = (tmp_path / "ws" / ".opencode" / "agents" / f"{agent}.md").read_text("utf-8")
            assert "dadaia-handoff-emitter" in content, f"{agent} opencode projection missing skill"

    def test_claude_projection_has_handoff_emitter(self, tmp_path: Path) -> None:
        _install(tmp_path)
        for agent in MIGRATED_AGENTS:
            content = (tmp_path / "ws" / ".claude" / "agents" / f"{agent}.md").read_text("utf-8")
            assert "dadaia-handoff-emitter" in content, f"{agent} claude projection missing skill"
