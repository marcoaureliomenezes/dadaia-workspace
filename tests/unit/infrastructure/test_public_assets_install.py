"""Install-time behavior extracted from ``public_assets`` (T-2, v0.1.75 split of
``test_public_assets.py`` by concern — 2/4: install).

Covers: the guardrail-pair targeting trio (workspace root vs consumer repos vs both),
the CLAUDE.md stub law, the shared T-PROP-01 hash-compare parametrized sweep across
four install surfaces (codex agents, claude settings.json, codex runtime adapters, the
guardrail pair), codex agents/rules/scripts install, self-repo skip, and force-rm-stale
for codex agents/workflows.
"""

from __future__ import annotations

import json
import sys
import tomllib
from collections.abc import Callable
from pathlib import Path
from unittest.mock import patch

import pytest

from dadaia_workspace.core.exceptions import PublicAssetError
from dadaia_workspace.infrastructure.public_assets import (
    _CLAUDE_MD_STUB,
    FileSystemPublicAssetManager,
    _install_consumer_repos_guardrail_pair,
    _install_workspace_guardrail_pair,
    _install_workspace_root_guardrail_pair,
)

_INSTALLED_VERSION = "1.2.3"
_OTHER_VERSION = "0.0.1"


def _make_agent_md(
    name: str, model: str = "claude-sonnet-4-6", tools: list[str] | None = None
) -> str:
    tools_block = ""
    if tools:
        items = "\n".join(f"  - {t}" for t in tools)
        tools_block = f"tools:\n{items}\n"
    return f"---\nname: {name}\nmodel: {model}\n{tools_block}---\n# Body of {name}\n"


def _register_context(workspace_root: Path, slug: str, state: str = "alive") -> None:
    states_dir = workspace_root / ".dadaia" / "states"
    states_dir.mkdir(parents=True, exist_ok=True)
    registry = states_dir / "spec_contexts.json"
    data = (
        json.loads(registry.read_text(encoding="utf-8"))
        if registry.exists()
        else {"schema_version": "2", "contexts": []}
    )
    data["contexts"].append(
        {
            "name": slug,
            "state": state,
            "repo_slug": slug,
            "repo_url": f"https://example.test/{slug}.git",
            "created_at": "2026-07-04T00:00:00Z",
            "alive_since": "2026-07-04T00:00:00Z" if state == "alive" else None,
            "dead_since": None if state == "alive" else "2026-07-04T00:00:00Z",
            "current_branch": "main",
        }
    )
    registry.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _add_marker_consumer(
    workspace_root: Path, slug: str, pkg_version: str = _OTHER_VERSION
) -> Path:
    consumer = workspace_root / "repos" / slug
    (consumer / ".dadaia" / "agentic").mkdir(parents=True, exist_ok=True)
    manifest = {"schema_version": "1", "package_version": pkg_version}
    (consumer / ".dadaia" / "agentic" / "manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    _register_context(workspace_root, slug)
    return consumer


def _make_source_file(tmp_path: Path, content: str = "# AGENTS\n") -> Path:
    src_dir = tmp_path / "_src"
    src_dir.mkdir(exist_ok=True)
    src = src_dir / "AGENTS.md"
    src.write_text(content, encoding="utf-8")
    return src


def _build_minimal_agentic_dir(tmp_path: Path) -> tuple[Path, Path]:
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)
    agentic_dir = workspace_root / ".dadaia" / "agentic"
    agentic_dir.mkdir(parents=True)
    manifest = {
        "schema_version": "1",
        "package_version": "0.0.0-test",
        "generated_at": "2026-01-01T00:00:00+00:00",
        "assets": [],
    }
    (agentic_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return agentic_dir, workspace_root


# ---------------------------------------------------------------------------
# Guardrail-pair targeting: root-only / consumer-only / combined
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "installer",
    [
        _install_workspace_guardrail_pair,
        _install_workspace_root_guardrail_pair,
        _install_consumer_repos_guardrail_pair,
    ],
    ids=["combined-writes-both", "root-only-writes-root", "consumer-only-writes-consumers"],
)
def test_guardrail_pair_targeting(tmp_path: Path, installer: Callable[..., None]) -> None:
    src = _make_source_file(tmp_path, "# AGENTS\n")
    consumer = _add_marker_consumer(tmp_path, "my-repo")
    installer(src, tmp_path, force=True)

    root_written = (tmp_path / "AGENTS.md").exists() and (tmp_path / "CLAUDE.md").exists()
    consumer_written = (consumer / "AGENTS.md").exists() and (consumer / "CLAUDE.md").exists()

    if installer is _install_workspace_guardrail_pair:
        assert root_written and consumer_written
    elif installer is _install_workspace_root_guardrail_pair:
        assert root_written and not consumer_written
    else:
        assert consumer_written and not root_written


def test_self_repo_skipped_across_guardrail_installers(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    src = _make_source_file(tmp_path, "# AGENTS\n")
    with patch(
        "dadaia_workspace.infrastructure.workspace_guardrail._package_version",
        return_value=_INSTALLED_VERSION,
    ):
        _add_marker_consumer(tmp_path, "self-repo", pkg_version=_INSTALLED_VERSION)
        _install_workspace_guardrail_pair(src, tmp_path, force=True)
    assert not (tmp_path / "repos" / "self-repo" / "AGENTS.md").exists()
    captured = capsys.readouterr()
    assert "self-projection" in captured.err


# ---------------------------------------------------------------------------
# CLAUDE.md stub law: content, already-stub skip, stale update
# ---------------------------------------------------------------------------


def test_claude_md_stub_law(tmp_path: Path) -> None:
    src = _make_source_file(tmp_path)
    _install_workspace_root_guardrail_pair(src, tmp_path, force=True)
    assert (tmp_path / "CLAUDE.md").read_text(encoding="utf-8") == _CLAUDE_MD_STUB

    # Already-stub CLAUDE.md is a no-op under force=False.
    (tmp_path / "CLAUDE.md").write_text(_CLAUDE_MD_STUB, encoding="utf-8", newline="")
    installed_skip: list[str] = []
    _install_workspace_root_guardrail_pair(src, tmp_path, force=False, installed=installed_skip)
    assert (tmp_path / "CLAUDE.md").read_text(encoding="utf-8") == _CLAUDE_MD_STUB
    assert any("[skip]" in e and "CLAUDE" in e for e in installed_skip)

    # A stale (non-stub) CLAUDE.md is updated even under force=False.
    (tmp_path / "CLAUDE.md").write_text("# OLD CLAUDE\n", encoding="utf-8")
    installed_update: list[str] = []
    _install_workspace_root_guardrail_pair(src, tmp_path, force=False, installed=installed_update)
    assert (tmp_path / "CLAUDE.md").read_text(encoding="utf-8") == _CLAUDE_MD_STUB
    assert any("[ok]" in e and "CLAUDE" in e for e in installed_update)


# ---------------------------------------------------------------------------
# T-PROP-01 — the shared hash-compare sweep: identical content -> [skip],
# differing content -> [ok] (overwrite), across four install surfaces that used
# to carry 8 copy-pasted pairs of this same contract.
# ---------------------------------------------------------------------------


def _codex_agents_case(
    tmp_path: Path,
) -> tuple[Callable[[bool, list[str]], None], Path, str, str]:
    agentic_dir, workspace_root = _build_minimal_agentic_dir(tmp_path)
    agents_src = agentic_dir / "agents"
    agents_src.mkdir()
    (agents_src / "my-agent.md").write_text(_make_agent_md("my-agent"), encoding="utf-8")
    manager = FileSystemPublicAssetManager()
    manager._install_codex_agents(agentic_dir, workspace_root, force=True, installed=[])
    toml_path = workspace_root / ".codex" / "agents" / "my-agent.toml"
    canonical = toml_path.read_text(encoding="utf-8")

    def run(force: bool, installed: list[str]) -> None:
        manager._install_codex_agents(agentic_dir, workspace_root, force=force, installed=installed)

    return run, toml_path, canonical, "stale content differs\n"


def _claude_settings_case(
    tmp_path: Path,
) -> tuple[Callable[[bool, list[str]], None], Path, str, str]:
    agentic_dir, workspace_root = _build_minimal_agentic_dir(tmp_path)
    manager = FileSystemPublicAssetManager()
    manager._install_claude(agentic_dir, workspace_root, force=True, installed=[])
    settings_path = workspace_root / ".claude" / "settings.json"
    canonical = settings_path.read_text(encoding="utf-8")

    def run(force: bool, installed: list[str]) -> None:
        manager._install_claude(agentic_dir, workspace_root, force=force, installed=installed)

    # The stale content must be a file dadaia OWNS end to end, so the hash-compare sweep
    # asserts drift repair — NOT operator data loss. `{"existing": true}` used to sit here,
    # which made this sweep formally certify that operator JSON in settings.json is wiped
    # (bug claude-install-destroys-operator-settings). Operator-key preservation is now
    # asserted by test_install_preserves_operator_settings.
    stale = json.dumps({"hooks": {"PreToolUse": []}}, indent=2, sort_keys=True) + "\n"
    return run, settings_path, canonical, stale


def _codex_runtime_adapters_case(
    tmp_path: Path,
) -> tuple[Callable[[bool, list[str]], None], Path, str, str]:
    public_dir = tmp_path / "public"
    runtime_codex = public_dir / "runtime" / "codex" / "my-adapter"
    runtime_codex.mkdir(parents=True)
    canonical = "# NEW\n"
    (runtime_codex / "SKILL.md").write_text(canonical, encoding="utf-8")
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    manager = FileSystemPublicAssetManager()
    manager._public_dir = public_dir
    dst = workspace_root / ".codex" / "skills" / "my-adapter" / "SKILL.md"

    def run(force: bool, installed: list[str]) -> None:
        manager._install_codex_runtime_adapters(workspace_root, force=force, installed=installed)

    return run, dst, canonical, "# ORIGINAL\n"


def _guardrail_pair_case(
    tmp_path: Path,
) -> tuple[Callable[[bool, list[str]], None], Path, str, str]:
    src = _make_source_file(tmp_path, "# NEW\n")
    canonical = "# NEW\n"

    def run(force: bool, installed: list[str]) -> None:
        _install_workspace_root_guardrail_pair(src, tmp_path, force=force, installed=installed)

    return run, tmp_path / "AGENTS.md", canonical, "# OLD\n"


@pytest.mark.parametrize(
    "case_factory",
    [
        _codex_agents_case,
        _claude_settings_case,
        _codex_runtime_adapters_case,
        _guardrail_pair_case,
    ],
    ids=["codex-agents", "claude-settings", "codex-runtime-adapters", "guardrail-pair"],
)
def test_t_prop_01_hash_compare_sweep(
    tmp_path: Path, case_factory: Callable[[Path], tuple[Callable[..., None], Path, str, str]]
) -> None:
    """T-PROP-01: force=False + identical projected content is a no-op [skip]
    (mtime unchanged); force=False + stale/differing content is overwritten [ok]
    without needing --force. One shared parametrized sweep replaces 8 copy-pasted
    identical/different pairs across 4 install surfaces."""
    run, dst_path, canonical_content, stale_content = case_factory(tmp_path)

    # Force the projected file to the STALE content, then run force=False: must overwrite.
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    dst_path.write_text(stale_content, encoding="utf-8")
    installed_overwrite: list[str] = []
    run(False, installed_overwrite)
    assert dst_path.read_text(encoding="utf-8") == canonical_content
    assert any("[ok]" in e for e in installed_overwrite)
    assert not any("[skip]" in e for e in installed_overwrite)

    # Now the projected file matches canonical: force=False must be a no-op [skip].
    mtime_before = dst_path.stat().st_mtime
    installed_skip: list[str] = []
    run(False, installed_skip)
    assert dst_path.read_text(encoding="utf-8") == canonical_content
    assert dst_path.stat().st_mtime == mtime_before
    assert any("[skip]" in e for e in installed_skip)
    assert not any("[ok]" in e for e in installed_skip)


# ---------------------------------------------------------------------------
# _install_codex_agents / _install_codex_rules / _install_scripts / force-rm-stale
# ---------------------------------------------------------------------------


def test_install_codex_agents_shape_and_edge_cases(tmp_path: Path) -> None:
    """A valid agent renders valid TOML content; an agent without a name is
    skipped; an empty (or nonexistent) source agents dir writes nothing."""
    agentic_dir, workspace_root = _build_minimal_agentic_dir(tmp_path)
    agents_src = agentic_dir / "agents"
    agents_src.mkdir()
    (agents_src / "my-agent.md").write_text(_make_agent_md("my-agent"), encoding="utf-8")
    (agents_src / "noname.md").write_text("---\nmodel: gpt-4o\n---\nbody\n", encoding="utf-8")

    manager = FileSystemPublicAssetManager()
    installed: list[str] = []
    manager._install_codex_agents(agentic_dir, workspace_root, force=True, installed=installed)

    toml_path = workspace_root / ".codex" / "agents" / "my-agent.toml"
    assert toml_path.exists()
    data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
    assert data.get("name") == "my-agent"
    assert "developer_instructions" in data
    assert not (workspace_root / ".codex" / "agents" / "noname.toml").exists()
    assert any("[ok]" in e and "my-agent" in e for e in installed)

    empty_root = tmp_path / "empty-case"
    empty_root.mkdir()
    empty_agentic, empty_ws = _build_minimal_agentic_dir(empty_root)
    (empty_agentic / "agents").mkdir()
    empty_installed: list[str] = []
    manager._install_codex_agents(empty_agentic, empty_ws, force=True, installed=empty_installed)
    assert empty_installed == []

    # Regression companion to test_public_assets_render.py's precedence test: the
    # install path threads through the same source (data/AGENTS.md-driven tree).
    src_agentic, _ = _build_minimal_agentic_dir(tmp_path / "src-case")
    src_data_dir = src_agentic / "data"
    src_data_dir.mkdir()
    (src_data_dir / "AGENTS.md").write_text("# AGENTS\n", encoding="utf-8")
    assert manager._agents_md_source(src_agentic) is not None


def test_install_codex_rules(tmp_path: Path) -> None:
    """Native command-policy rules are always generated regardless of a rules/
    source dir; markdown protocol rules are never copied verbatim; and the
    generated policy carries BOTH the mandated venv-relative pattern AND the
    bare-name PATH fallback for dadaia-gated commands (bug
    codex-rules-dadaia-prefix-never-matches-venv-invocation)."""
    from dadaia_workspace.infrastructure.runtime_transforms.codex_assets import (
        _render_codex_command_policy_rules,
    )

    agentic_dir, workspace_root = _build_minimal_agentic_dir(tmp_path)
    rules_dir = agentic_dir / "rules"
    rules_dir.mkdir()
    (rules_dir / "exec.md").write_text("---\nname: exec\n---\nbody\n", encoding="utf-8")
    (rules_dir / "prose.md").write_text("# Prose (no frontmatter)\n", encoding="utf-8")
    installed: list[str] = []
    manager = FileSystemPublicAssetManager()
    manager._install_codex_rules(agentic_dir, workspace_root, force=True, installed=installed)
    assert (workspace_root / ".codex" / "rules" / "dadaia-command-policy.rules").exists()
    assert not (workspace_root / ".codex" / "rules" / "exec.md").exists()
    assert not (workspace_root / ".codex" / "rules" / "prose.md").exists()
    assert any("dadaia-command-policy.rules" in e for e in installed)
    assert len(installed) == 1

    rules = _render_codex_command_policy_rules()
    # The mandated venv invocation is the FIRST argv token in a pattern (T-013-10).
    assert 'pattern = [".dadaia/.venv/bin/dadaia", "public", "install"]' in rules
    assert 'pattern = [".dadaia/.venv/bin/dadaia", "context", "dead"]' in rules
    assert ".dadaia/.venv/bin/dadaia public install --target codex" in rules
    assert ".dadaia/.venv/bin/dadaia context dead dadaia-workspace" in rules
    # A bare-name `dadaia` fallback pattern remains for PATH invocations.
    assert 'pattern = ["dadaia", "public", "install"]' in rules
    assert 'pattern = ["dadaia", "context", "dead"]' in rules
    # Shape invariant kept (D-CX-8): prefix_rule, no command_allowed.
    assert "prefix_rule(" in rules
    assert "command_allowed(" not in rules


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="the 0o755 executable bit is a no-op on Windows; .sh scripts are "
    "POSIX-only and unused by the Windows Python governance hooks",
)
def test_install_scripts_chmod_applied(tmp_path: Path) -> None:
    agentic_dir, workspace_root = _build_minimal_agentic_dir(tmp_path)
    scripts_src = agentic_dir / "scripts"
    scripts_src.mkdir()
    (scripts_src / "test.sh").write_text("#!/bin/bash\n", encoding="utf-8")
    installed: list[str] = []
    manager = FileSystemPublicAssetManager()
    manager._install_scripts(agentic_dir, workspace_root, force=True, installed=installed)
    dst_script = workspace_root / ".dadaia" / "scripts" / "test.sh"
    assert dst_script.exists()
    mode = oct(dst_script.stat().st_mode)[-3:]
    assert mode == "755"


def test_codex_force_install_removes_stale_agents_and_workflows(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    manager = FileSystemPublicAssetManager()
    manager.stage(workspace)
    stale_agent = workspace / ".codex" / "agents" / "stale-agent.toml"
    stale_agent.parent.mkdir(parents=True, exist_ok=True)
    stale_agent.write_text('model = "gpt-5.3-codex"\n', encoding="utf-8")
    stale_workflow = workspace / ".codex" / "workflows" / "stale.workflow.md"
    stale_workflow.parent.mkdir(parents=True, exist_ok=True)
    stale_workflow.write_text("# stale\n", encoding="utf-8")

    installed = manager.install(workspace, target="codex", force=True)

    assert not stale_agent.exists()
    assert not stale_workflow.exists()
    assert any("[rm]" in item and "stale-agent.toml" in item for item in installed)
    assert any("[rm]" in item and "stale.workflow.md" in item for item in installed)


def test_install_preserves_operator_settings(tmp_path: Path) -> None:
    """``.claude/settings.json`` belongs to the OPERATOR; dadaia owns only its own hooks.

    Bug ``claude-install-destroys-operator-settings``: a plain install wrote the whole file
    from the generator, erasing ``permissions``, ``model``, ``env`` and any operator hook —
    silently, while printing ``[ok]``. Worse, ``doctor`` labelled the operator's own config
    ``[drift]``, and the documented remedy for drift is to run install, so the tool routed
    the operator into the destruction.

    Asserts the four things the merge must guarantee: foreign top-level keys survive,
    foreign hook EVENTS survive, a foreign entry INSIDE a dadaia-wired event survives, and
    dadaia's own wiring is still canonical.
    """
    agentic_dir, workspace_root = _build_minimal_agentic_dir(tmp_path)
    manager = FileSystemPublicAssetManager()
    manager._install_claude(agentic_dir, workspace_root, force=True, installed=[])
    settings_path = workspace_root / ".claude" / "settings.json"

    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    settings["permissions"] = {"allow": ["Bash(git status:*)"]}
    settings["model"] = "claude-opus-4-8"
    settings["hooks"]["Stop"] = [{"hooks": [{"type": "command", "command": "operator.sh"}]}]
    settings["hooks"]["PreCompact"] = [
        {"hooks": [{"type": "command", "command": "operator-precompact.sh"}]}
    ]
    settings["hooks"]["PreToolUse"].append(
        {"matcher": "Read", "hooks": [{"type": "command", "command": "operator-audit.sh"}]}
    )
    settings_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")

    manager._install_claude(agentic_dir, workspace_root, force=False, installed=[])
    after = json.loads(settings_path.read_text(encoding="utf-8"))

    assert after.get("permissions") == {"allow": ["Bash(git status:*)"]}
    assert after.get("model") == "claude-opus-4-8"
    assert after["hooks"].get("Stop") == [
        {"hooks": [{"type": "command", "command": "operator.sh"}]}
    ]
    commands = [entry["hooks"][0]["command"] for entry in after["hooks"]["PreToolUse"]]
    assert "operator-audit.sh" in commands, commands
    assert any("dadaia_workspace.hooks.pre_gate" in c for c in commands), commands
    # doctor stays green — an operator key is not drift — but it is NOT blind: a foreign
    # command inside a gated event runs on every write, so it is surfaced as a visible,
    # non-blocking advisory. Preserving the operator's hooks must not mean hiding them.
    # Asserted on the settings doctor directly: the full ``doctor()`` gates this block on
    # "claude in the harness profile", which this minimal fixture does not carry.
    lines = manager._doctor_claude_settings(workspace_root)
    assert lines[0] == "[ok] claude:settings.json", lines
    warns = [line for line in lines if line.startswith("[warn]")]
    assert warns, f"a foreign PreToolUse hook must be surfaced: {lines}"
    assert "operator-audit.sh" in warns[0], warns
    assert "PreToolUse" in warns[0], warns
    # The sweep must cover EVERY event in the file, not only the four dadaia wires: Stop,
    # PreCompact, SessionEnd, SubagentStop and Notification are executed by Claude Code
    # just the same, so a foothold there is equally live and must be equally visible.
    assert "operator.sh" in warns[0], warns
    assert "Stop" in warns[0], warns
    assert "operator-precompact.sh" in warns[0], warns
    assert "PreCompact" in warns[0], warns
    # Advisory only: [warn] must not fail the doctor.
    assert not [line for line in lines if line.startswith(("[drift]", "[missing]"))], lines


def test_install_refuses_to_clobber_unreadable_settings(tmp_path: Path) -> None:
    """Unparseable ``settings.json`` is refused loudly, never overwritten.

    Overwriting is the one outcome the operator can neither detect nor undo, so a file we
    cannot merge into must stop the install with an actionable message.
    """
    agentic_dir, workspace_root = _build_minimal_agentic_dir(tmp_path)
    manager = FileSystemPublicAssetManager()
    manager._install_claude(agentic_dir, workspace_root, force=True, installed=[])
    settings_path = workspace_root / ".claude" / "settings.json"
    settings_path.write_text("{ not json at all", encoding="utf-8")

    with pytest.raises(PublicAssetError, match="not readable JSON"):
        manager._install_claude(agentic_dir, workspace_root, force=True, installed=[])
    assert settings_path.read_text(encoding="utf-8") == "{ not json at all"
