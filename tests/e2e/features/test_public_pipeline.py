"""v0.1.65 FR1/AC-1, FR5/AC-8 (public asset pipeline): content-level
invariants of the real stage -> install projection, the doctor's drift/missing verdicts,
and the per-harness `dadaia init --harness` profiles. Stage/install rosters live in
tests/integration/test_public_assets.py::test_stage_manifest_and_install_all.
Size: LARGE — real projection I/O (FileSystemPublicAssetManager over tmp_path).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app as cli_app
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from tests.helpers.harness_profile import register_all

_runner = CliRunner()
#: Required YAML fields in every STAGED agent's frontmatter; `model`/`effort` are
#: injected at install time (FR1), never staged.
_REQUIRED_FRONTMATTER = {"name", "description", "tools"}


def _manager() -> FileSystemPublicAssetManager:
    return FileSystemPublicAssetManager()


def _frontmatter(content: str) -> str:
    end = content.find("\n---\n", 4) if content.startswith("---\n") else -1
    return content[4:end] if end != -1 else ""


def _parse_frontmatter_keys(content: str) -> set[str]:
    return {m.group(1) for m in re.finditer(r"^(\w[\w-]*):", _frontmatter(content), re.MULTILINE)}


def _parse_skills_list(content: str) -> list[str]:
    m = re.search(r"^skills:\n((?:  - [^\n]+\n)+)", content, re.MULTILINE)
    return [line.strip().lstrip("- ").strip() for line in m.group(1).splitlines()] if m else []


def _is_plugin_stub(content: str) -> bool:
    """A plugin stub (`plugin: true`) omits model, tools and body by design."""
    return bool(re.search(r"^plugin:\s*true\b", _frontmatter(content), re.MULTILINE))


def _staged_install(workspace: Path) -> FileSystemPublicAssetManager:
    mgr = _manager()
    register_all(workspace)
    mgr.install(workspace, force=True)
    return mgr


class TestContentConsistency:
    def test_agent_frontmatter_skill_refs_tools_and_skill_md_presence(self, tmp_path: Path) -> None:
        """Staged agents carry the required frontmatter and no `model:`/`effort:` (FR1);
        every skill an agent names has a staged SKILL.md; installed Claude agents keep
        `tools:`; every staged skill dir has a SKILL.md; the dev-server registry script
        (dd-cli-library) keeps its verbs."""
        workspace = tmp_path / "ws"
        _staged_install(workspace)
        agents_dir = workspace / ".dadaia" / "agentic" / "agents"
        skills_dir = workspace / ".dadaia" / "agentic" / "skills"
        for agent_file in sorted(agents_dir.glob("*.md")):
            content = agent_file.read_text(encoding="utf-8")
            unresolved = [
                s for s in _parse_skills_list(content) if not (skills_dir / s / "SKILL.md").exists()
            ]
            assert unresolved == [], agent_file.name
            if not _is_plugin_stub(content):
                keys = _parse_frontmatter_keys(content)
                assert keys >= _REQUIRED_FRONTMATTER and not keys & {"model", "effort"}, (
                    agent_file.name
                )
        for agent_file in sorted((workspace / ".claude" / "agents").glob("*.md")):
            content = agent_file.read_text(encoding="utf-8")
            assert _is_plugin_stub(content) or "tools:" in content, agent_file.name
        assert [
            d.name for d in skills_dir.iterdir() if d.is_dir() and not (d / "SKILL.md").exists()
        ] == []
        registry = (skills_dir / "dd-cli-library" / "scripts" / "registry.py").read_text(
            encoding="utf-8"
        )
        for verb in ("register", "release", "next", "clean"):
            assert f'sub.add_parser("{verb}")' in registry, verb


class TestDoctor:
    def test_doctor_reports_all_ok_after_clean_install(self, tmp_path: Path) -> None:
        mgr = _staged_install(tmp_path / "ws")
        report = [line.render() for line in mgr.doctor(tmp_path / "ws")]
        assert [line for line in report if line.startswith(("[drift]", "[missing]"))] == []

    @pytest.mark.parametrize(
        ("mutation", "agent"), [("drift", "dd-software-engineer"), ("missing", "dd-code-reviewer")]
    )
    def test_doctor_detects_drift_and_missing_after_runtime_mutation(
        self, tmp_path: Path, mutation: str, agent: str
    ) -> None:
        workspace = tmp_path / "ws"
        mgr = _staged_install(workspace)
        target = workspace / ".claude" / "agents" / f"{agent}.md"
        if mutation == "drift":
            target.write_text(
                target.read_text(encoding="utf-8") + "\n# drifted\n", encoding="utf-8"
            )
        else:
            target.unlink()
        report = [line.render() for line in mgr.doctor(workspace)]
        assert [line for line in report if f"[{mutation}]" in line and agent in line], report


def _ctx_inject_registered(claude_dir: Path) -> bool:
    settings = json.loads((claude_dir / "settings.json").read_text(encoding="utf-8"))
    commands = [
        h["command"]
        for entry in settings.get("hooks", {}).get("UserPromptSubmit", [])
        for h in entry.get("hooks", [])
    ]
    wrapper = claude_dir.parent / ".dadaia" / "hooks" / "claude-ctx-inject"
    return any(c.endswith("/.dadaia/hooks/claude-ctx-inject") for c in commands) and (
        "dadaia_workspace.hooks.ctx_inject" in wrapper.read_text(encoding="utf-8")
    )


class TestPerProfileInit:
    """FR5 / AC-8: the real `dadaia init --harness <one>` projects exactly that harness's
    tree (no un-chosen harness dir), persists the profile, and the profile-scoped
    `public doctor` is green on both surfaces (no [missing]/[drift]/[fail], exit 0).
    FR31/T-044-59: no `.claude/rules/` mirror; 0.4.7 FR3: kimi-code owns no workspace dir."""

    @pytest.mark.parametrize(
        ("harness", "present", "absent"),
        [
            pytest.param("claude", (".claude/agents", ".claude/skills"), (".claude/rules", ".codex", ".kimi-code"), id="claude"),
            pytest.param("codex", (".codex/agents", ".codex/hooks.json", ".codex/config.toml", ".dadaia/hooks/codex-*"), (".claude", ".kimi-code"), id="codex"),
            pytest.param("kimi-code", (".agents/skills",), (".kimi-code", ".claude", ".codex"), id="kimi-code"),
        ],
    )  # fmt: skip
    def test_a_single_harness_profile_projects_only_its_own_tree(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        harness: str,
        present: tuple[str, ...],
        absent: tuple[str, ...],
    ) -> None:
        ws = tmp_path / "ws"
        monkeypatch.chdir(tmp_path)
        result = _runner.invoke(cli_app, ["init", str(ws), "--harness", harness])
        assert result.exit_code == 0, result.output

        assert [p for p in present if not list(ws.glob(p))] == []
        assert [p for p in absent if (ws / p).exists()] == []
        assert harness != "claude" or _ctx_inject_registered(ws / ".claude")
        profile = ws / ".dadaia" / "states" / "harness_profile.json"
        assert json.loads(profile.read_text(encoding="utf-8"))["harnesses"] == [harness]
        report = [line.render() for line in _manager().doctor(ws)]
        assert [
            line for line in report if line.startswith(("[missing]", "[drift]", "[fail]"))
        ] == []
        monkeypatch.chdir(ws)
        doctor = _runner.invoke(cli_app, ["public", "doctor"])
        assert doctor.exit_code == 0, doctor.output


class TestLinkViewDoctor:
    """A broken harness view of the authored set is one ``[drift]`` line of the rule table.

    0.4.7 AC3.1/AC3.2 (T-047-57); §4a-7 (the rule table's
    ``_doctor_link`` is the one judge). Size: LARGE (real projection I/O).
    """

    @staticmethod
    def _a_linked_skill(workspace: Path) -> Path:
        entry = next(
            (p for p in sorted((workspace / ".claude" / "skills").iterdir()) if p.is_symlink()),
            None,
        )
        assert entry is not None, "install produced no .claude/skills symlink to break"
        return entry

    def test_retargeted_symlink_is_one_whole_drift_line_and_exit_1(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Through the CLI `public doctor` on a non-TTY with a 61-character root."""
        workspace = tmp_path / ("w" * max(1, 61 - len(str(tmp_path)) - 1))
        mgr = _manager()
        register_all(workspace)
        mgr.install(workspace, force=True)
        entry = self._a_linked_skill(workspace)
        foreign = tmp_path / "foreign"
        foreign.mkdir()
        entry.unlink()
        entry.symlink_to(foreign, target_is_directory=True)

        sentinel = workspace / ".dadaia" / "states" / "spec_contexts.json"
        sentinel.write_text('{"schema_version": "2", "contexts": []}', encoding="utf-8")
        monkeypatch.chdir(workspace)
        monkeypatch.delenv("COLUMNS", raising=False)
        assert len(str(workspace)) >= 61
        result = _runner.invoke(cli_app, ["public", "doctor"])

        assert result.exit_code == 1
        assert [line for line in result.output.splitlines() if "[drift]" in line] == [
            f"[drift] claude:skills/{entry.name} (symlink target '{foreign}' is not the "
            f"canonical '../../.agents/skills/{entry.name}')"
        ], result.output

    def test_symlink_replaced_by_a_drifted_copy_is_drift(self, tmp_path: Path) -> None:
        workspace = tmp_path / "ws"
        mgr = _manager()
        register_all(workspace)
        mgr.install(workspace, force=True)
        entry = self._a_linked_skill(workspace)
        authored = workspace / ".agents" / "skills" / entry.name
        entry.unlink()
        entry.mkdir()
        for source in sorted(authored.rglob("*")):
            if source.is_file():
                copied = entry / source.relative_to(authored)
                copied.parent.mkdir(parents=True, exist_ok=True)
                copied.write_bytes(source.read_bytes())
        skill_md = entry / "SKILL.md"
        skill_md.write_text(skill_md.read_text(encoding="utf-8") + "\ndrifted\n", encoding="utf-8")

        report = [line.render() for line in mgr.doctor(workspace)]

        assert [line for line in report if line.startswith("[drift]")] == [
            f"[drift] claude:skills/{entry.name} (copy diverged at SKILL.md)"
        ], "\n".join(report)
