"""The projected ``.claude/`` scaffold must be LOADABLE by Claude Code — not merely written.

Every existing assertion over this surface compares dadaia's output to dadaia's own
generator constants: install wrote what the generator produced, and doctor agrees. That is
internal self-consistency. It cannot catch a value that is wrong *for Claude Code* — an
invented hook event, a SessionStart matcher outside the accepted source vocabulary, a
frontmatter block the render seam string-spliced into invalid YAML, or a tool name that no
longer exists. Each of those fails SILENTLY: the hook never fires, or the sub-agent is
dropped, and every other test stays green.

These ratchets pin the scaffold against Claude Code's contract, held here as explicit
frozensets. When Claude Code's vocabulary genuinely changes, THIS file is the one place to
update — deliberately, not by regenerating a golden.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager
from dadaia_workspace.infrastructure.runtime_config import claude_settings

pytestmark = pytest.mark.contract

#: Hook events Claude Code dispatches. An event outside this set is accepted into
#: settings.json and then never fires.
_CLAUDE_HOOK_EVENTS = frozenset(
    {
        "PreToolUse",
        "PostToolUse",
        "UserPromptSubmit",
        "SessionStart",
        "SessionEnd",
        "Stop",
        "SubagentStop",
        "Notification",
        "PreCompact",
    }
)

#: The ``source`` values a SessionStart matcher may name.
_SESSION_START_SOURCES = frozenset({"startup", "resume", "clear", "compact", "fork"})

#: Tool names a sub-agent may declare, plus the all-tools wildcard.
_CLAUDE_TOOL_NAMES = frozenset(
    {
        "Read",
        "Write",
        "Edit",
        "MultiEdit",
        "NotebookEdit",
        "Bash",
        "Glob",
        "Grep",
        "WebFetch",
        "WebSearch",
        "Agent",
        "Task",
        "TodoWrite",
        "*",
    }
)

#: Model ids a sub-agent may declare — full ids and the bare aliases Claude Code accepts.
#: ``claude-opus-5`` is the operator's Layer-1 remap and is a real id (it is the model this
#: workspace's own sessions run on); it is listed deliberately, not by accident.
_CLAUDE_MODEL_IDS = frozenset(
    {
        "claude-opus-5",
        "claude-opus-4-8",
        "claude-opus-4-7",
        "claude-opus-4-6",
        "claude-fable-5",
        "claude-sonnet-5",
        "claude-sonnet-4-6",
        "claude-haiku-4-5",
        "opus",
        "sonnet",
        "haiku",
        "fable",
        "inherit",
    }
)


@pytest.fixture(scope="module")
def projected(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A real workspace with the claude projection installed, built once for the module."""
    workspace = tmp_path_factory.mktemp("claude-scaffold") / "ws"
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(workspace)
    manager = FileSystemPublicAssetManager()
    manager.stage(workspace)
    manager.install(workspace, target="claude")
    return workspace


def _frontmatter(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{path.name}: no frontmatter block"
    _, _, rest = text.partition("---\n")
    block, sep, _ = rest.partition("\n---")
    assert sep, f"{path.name}: unterminated frontmatter block"
    loaded = yaml.safe_load(block)
    assert isinstance(loaded, dict), f"{path.name}: frontmatter is not a mapping: {loaded!r}"
    return loaded


def test_every_projected_agent_frontmatter_is_loadable(projected: Path) -> None:
    """Claude Code drops a sub-agent whose frontmatter it cannot parse.

    ``render_claude_agent`` builds the projected frontmatter by string-splicing the model
    and effort lines into the staged body, so the render output — not the source — is what
    must parse. Nothing asserted that before: the only projection-side check was
    ``assert "tools:" in content``, a substring search over the whole file that passes on
    body prose.
    """
    agents = sorted((projected / ".claude" / "agents").glob("*.md"))
    assert agents, "the claude projection installed no agents"
    for path in agents:
        fm = _frontmatter(path)
        assert isinstance(fm.get("name"), str) and fm["name"], f"{path.name}: no name"
        assert fm["name"] == path.stem, f"{path.name}: name {fm['name']!r} != filename"
        desc = fm.get("description")
        assert isinstance(desc, str) and desc.strip(), f"{path.name}: no description"


def test_projected_agents_declare_only_real_tools_and_models(projected: Path) -> None:
    """An unknown tool name or model id is accepted into the file and then misbehaves."""
    for path in sorted((projected / ".claude" / "agents").glob("*.md")):
        fm = _frontmatter(path)
        tools = fm.get("tools")
        if tools is not None:
            names = [t.strip() for t in tools.split(",")] if isinstance(tools, str) else list(tools)
            unknown = sorted({str(n) for n in names} - _CLAUDE_TOOL_NAMES)
            assert not unknown, f"{path.name}: unknown tool name(s) {unknown}"
        model = fm.get("model")
        if model is not None:
            assert str(model) in _CLAUDE_MODEL_IDS, f"{path.name}: unknown model {model!r}"


def test_settings_hook_events_and_matchers_are_claude_code_valid(projected: Path) -> None:
    """An invented event or SessionStart source is written happily and never fires.

    The existing settings assertions hand-copy the generator's own constants back at it, so
    they catch a typo and nothing else. This checks the emitted values against Claude Code's
    vocabulary instead.
    """
    settings = json.loads((projected / ".claude" / "settings.json").read_text(encoding="utf-8"))
    hooks = settings["hooks"]
    unknown_events = sorted(set(hooks) - _CLAUDE_HOOK_EVENTS)
    assert not unknown_events, f"settings.json declares unknown hook event(s): {unknown_events}"
    for entry in hooks.get("SessionStart", []):
        source = entry.get("matcher", "")
        assert source in _SESSION_START_SOURCES, (
            f"SessionStart matcher {source!r} is not an accepted source "
            f"({sorted(_SESSION_START_SOURCES)}) — the hook would never fire"
        )
    for event in ("PreToolUse", "PostToolUse"):
        for entry in hooks.get(event, []):
            matcher = entry.get("matcher", "")
            if matcher in {"", "*"}:
                continue
            unknown_tools = sorted(set(matcher.split("|")) - _CLAUDE_TOOL_NAMES)
            assert not unknown_tools, f"{event} matcher names unknown tool(s): {unknown_tools}"


def test_pretooluse_matcher_covers_every_gated_write_tool(projected: Path) -> None:
    """The matcher and the gate's own write-tool classifier must not drift apart.

    They are two hardcoded lists in two modules with no link between them. A tool added to
    the gate's classifier while the matcher stops naming it means the gate is simply never
    invoked for that tool — a silent hole in a security boundary.
    """
    from dadaia_workspace.hooks import _common

    settings = claude_settings(projected)
    hooks = settings["hooks"]
    assert isinstance(hooks, dict)
    pre = hooks["PreToolUse"]
    assert isinstance(pre, list)
    matched: set[str] = set()
    for entry in pre:
        assert isinstance(entry, dict)
        matched |= set(str(entry.get("matcher", "")).split("|"))
    gated = {t for t in _common.WRITE_TOOLS if t in _CLAUDE_TOOL_NAMES}
    missing = sorted(gated - matched)
    assert not missing, (
        f"the gate classifies {missing} as write tools but the PreToolUse matcher does not "
        "name them — the gate would never run for those tools"
    )


def test_every_projected_skill_frontmatter_is_loadable(projected: Path) -> None:
    """A skill whose frontmatter will not parse loses its description and stops matching."""
    skills = sorted((projected / ".claude" / "skills").glob("*/SKILL.md"))
    assert skills, "the claude projection installed no skills"
    for path in skills:
        fm = _frontmatter(path)
        desc = fm.get("description")
        assert isinstance(desc, str) and desc.strip(), f"{path.parent.name}: no description"
        # Claude Code caps the matched description; an over-long one is silently truncated.
        assert len(desc) <= 1536, f"{path.parent.name}: description is {len(desc)} chars (cap 1536)"
