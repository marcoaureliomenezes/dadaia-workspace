"""One builder per ``AgentTranscode`` — how each harness sees the authored persona set.

There is exactly ONE rendered persona set in a workspace, under ``.agents/agents/``.
A harness either reads it natively, links each entry into a directory of its own, or
transcodes it into a dialect of its own. This module holds those builders as pure
functions keyed by the record's ``agent_transcode`` value, so registering a harness is
a data row in ``core/harness_registry.py`` and never a class, a branch or a name here.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from dadaia_workspace.core.exceptions import PublicAssetError
from dadaia_workspace.core.harness_registry import AgentTranscode, HarnessRecord
from dadaia_workspace.core.models.agent_model_policy import ResolvedAgentModel
from dadaia_workspace.infrastructure.install_helpers import (
    activity_read_only,
    resolve_codex_agent_model,
)
from dadaia_workspace.infrastructure.install_plan import InstallPlan
from dadaia_workspace.infrastructure.projection import (
    ProjectionRule,
    bytes_rule,
    link_rule,
    tree_bytes_rules,
)
from dadaia_workspace.infrastructure.public_assets_common import (
    _CLAUDE_DIRS,
    iter_public_files,
)
from dadaia_workspace.infrastructure.runtime_config import codex_config
from dadaia_workspace.infrastructure.runtime_transforms.codex import transform_for_codex
from dadaia_workspace.infrastructure.runtime_transforms.codex_assets import (
    _parse_agent_frontmatter,
    _render_codex_agent_toml,
    _render_codex_command_policy_rules,
)
from dadaia_workspace.infrastructure.runtime_transforms.model_mapping import map_model

#: The authored persona tree every view below points at or reads from.
_AUTHORED_AGENTS = (".agents", "agents")


def no_rules(record: HarnessRecord, plan: InstallPlan) -> tuple[ProjectionRule, ...]:
    """The harness reads the authored tree natively — it projects no view of its own."""
    del record, plan
    return ()


def _split_frontmatter(text: str) -> tuple[str, str]:
    """(frontmatter body without its fences, the rest) of a canonical agent file."""
    if not text.startswith("---\n"):
        raise PublicAssetError("cannot transcode agent: staged body has no YAML frontmatter block")
    end_idx = text.find("\n---\n", 4)
    if end_idx == -1:
        raise PublicAssetError("cannot transcode agent: staged frontmatter block is not closed")
    return text[4 : end_idx + 1], text[end_idx + 5 :]


def md_symlink_rules(record: HarnessRecord, plan: InstallPlan) -> tuple[ProjectionRule, ...]:
    """Agents and skills are per-entry relative symlinks onto the authored ``.agents/``
    set, never a second copy; the harness's other content dirs copy verbatim."""
    harness_dir = plan.workspace_root / str(record.directory)
    authored = plan.workspace_root / ".agents"
    src_agents = plan.agentic_dir / "agents"
    src_skills = plan.agentic_dir / "skills"
    dirs = _CLAUDE_DIRS if plan.only is None else tuple(d for d in _CLAUDE_DIRS if d == plan.only)
    rules: list[ProjectionRule] = []
    for name in dirs:
        if name == "agents":
            rules.extend(_agent_link_rules(record, harness_dir / "agents", authored, src_agents))
        elif name == "skills":
            skills = sorted(src_skills.iterdir()) if src_skills.is_dir() else []
            rules.extend(
                link_rule(
                    f"{record.name}:skills/{skill.name}",
                    record.name,
                    harness_dir / "skills" / skill.name,
                    authored / "skills" / skill.name,
                )
                for skill in skills
                if skill.is_dir()
            )
        else:
            rules.extend(
                tree_bytes_rules(
                    plan.agentic_dir / name,
                    harness_dir / name,
                    harness=record.name,
                    label_prefix=f"{record.name}:{name}/",
                )
            )
    return tuple(rules)


def _agent_link_rules(
    record: HarnessRecord, dst_dir: Path, authored: Path, src_agents: Path
) -> tuple[ProjectionRule, ...]:
    """One relative link per authored persona file, into *dst_dir*."""
    return tuple(
        link_rule(
            f"{record.name}:agents/{src.relative_to(src_agents).as_posix()}",
            record.name,
            dst_dir / src.relative_to(src_agents),
            authored / "agents" / src.relative_to(src_agents),
        )
        for src in iter_public_files(src_agents)
    )


def cursor_md_rules(record: HarnessRecord, plan: InstallPlan) -> tuple[ProjectionRule, ...]:
    """Cursor reads Markdown personas from its own directory — one link per authored
    file, the same hash-verified copy fallback, no second rendered copy."""
    if plan.only is not None and plan.only != "agents":
        return ()
    return _agent_link_rules(
        record,
        plan.workspace_root / str(record.directory) / "agents",
        plan.workspace_root / ".agents",
        plan.agentic_dir / "agents",
    )


#: The whole frontmatter vocabulary a Copilot custom agent understands; every other
#: authored key is dadaia dispatch metadata and is dropped from its view.
_COPILOT_FRONTMATTER_KEYS: frozenset[str] = frozenset({"name", "description", "tools"})


def copilot_agent_md_bytes(md_path: Path) -> bytes:
    """The authored persona rendered as a Copilot custom agent: its three known
    frontmatter keys (with their block values) plus the body, verbatim."""
    frontmatter, body = _split_frontmatter(md_path.read_text(encoding="utf-8"))
    kept: list[str] = []
    keeping = False
    for line in frontmatter.splitlines():
        if line[:1].isspace() or line.startswith("-"):
            if keeping:
                kept.append(line)
            continue
        keeping = line.split(":", 1)[0] in _COPILOT_FRONTMATTER_KEYS
        if keeping:
            kept.append(line)
    return ("---\n" + "\n".join(kept) + "\n---\n" + body).encode("utf-8")


def copilot_agent_md_rules(record: HarnessRecord, plan: InstallPlan) -> tuple[ProjectionRule, ...]:
    """``<dir>/agents/<name>.agent.md`` per authored persona — and nothing else under
    the harness directory, which the repository's own workflows already share."""
    if plan.only is not None and plan.only != "agents":
        return ()
    dst_dir = plan.workspace_root / str(record.directory) / "agents"
    rules: list[ProjectionRule] = []
    for md_file in sorted((plan.agentic_dir / "agents").glob("*.md")):
        fm = _parse_agent_frontmatter(md_file.read_text(encoding="utf-8"))
        agent_name = str(fm.get("name", "")) if fm else ""
        if not agent_name:
            continue

        def _render(_current: bytes | None, _md_file: Path = md_file) -> bytes:
            return copilot_agent_md_bytes(_md_file)

        rules.append(
            ProjectionRule(
                label=f"{record.name}:agents/{agent_name}.agent.md",
                harness=record.name,
                dst=dst_dir / f"{agent_name}.agent.md",
                render=_render,
            )
        )
    return tuple(rules)


def codex_agent_toml_bytes(
    md_path: Path, agent_name: str, resolved: ResolvedAgentModel | None
) -> bytes:
    """The ONE codex-agent renderer: frontmatter parse, strip, Codex transform, resolve
    ``(model, effort)``, render TOML. Shared by install (write) and doctor (compare)
    through the :class:`ProjectionRule` seam.
    """
    text = md_path.read_text(encoding="utf-8")
    fm = _parse_agent_frontmatter(text)
    if text.startswith("---\n"):
        end_idx = text.find("\n---\n", 4)
        body = text[end_idx + 5 :] if end_idx != -1 else text
    else:
        body = text
    body = transform_for_codex(body, agent_name)
    staged_model_raw = fm.get("model") if fm else None
    staged_model = str(staged_model_raw) if staged_model_raw else None
    claude_model, reasoning_effort = resolve_codex_agent_model(agent_name, staged_model, resolved)
    codex_model = map_model(claude_model)
    description = fm.get("description") if fm else None
    codex_description = transform_for_codex(str(description), agent_name) if description else None
    toml_content = _render_codex_agent_toml(
        agent_name,
        codex_model,
        body,
        description=codex_description,
        claude_model=claude_model,
        reasoning_effort=reasoning_effort,
        read_only=activity_read_only(fm),
    )
    return toml_content.encode("utf-8")


def toml_transcode_rules(record: HarnessRecord, plan: InstallPlan) -> tuple[ProjectionRule, ...]:
    """Per-agent TOML, ``config.toml`` and the command-policy rules file, all compared
    byte-wise. The shared ``.agents/skills`` tree is read natively."""
    harness_dir = plan.workspace_root / str(record.directory)
    rules: list[ProjectionRule] = []
    if plan.only is None or plan.only == "rules":
        rules.append(
            bytes_rule(
                f"{record.name}:rules/dadaia-command-policy.rules",
                record.name,
                harness_dir / "rules" / "dadaia-command-policy.rules",
                _render_codex_command_policy_rules().encode("utf-8"),
            )
        )
    if plan.only is None or plan.only == "agents":
        agents_src = plan.agentic_dir / "agents"
        for md_file in sorted(agents_src.glob("*.md")):
            fm = _parse_agent_frontmatter(md_file.read_text(encoding="utf-8"))
            agent_name = str(fm.get("name", "")) if fm else ""
            if not agent_name:
                continue
            resolved = plan.resolved_models.get(agent_name)

            def _render(
                _current: bytes | None,
                _md_file: Path = md_file,
                _agent_name: str = agent_name,
                _resolved: ResolvedAgentModel | None = resolved,
            ) -> bytes:
                return codex_agent_toml_bytes(_md_file, _agent_name, _resolved)

            rules.append(
                ProjectionRule(
                    label=f"{record.name}:agents/{agent_name}.toml",
                    harness=record.name,
                    dst=harness_dir / "agents" / f"{agent_name}.toml",
                    render=_render,
                )
            )
        rules.append(
            bytes_rule(
                f"{record.name}:config.toml",
                record.name,
                harness_dir / "config.toml",
                codex_config(plan.agentic_dir).encode("utf-8"),
            )
        )
    return tuple(rules)


#: One builder per :class:`AgentTranscode` value — the dispatch that replaced a class
#: per harness. A transcode with no view of its own maps to :func:`no_rules`, stated
#: here rather than left to a missing key.
AGENT_RULE_BUILDERS: dict[
    AgentTranscode, Callable[[HarnessRecord, InstallPlan], tuple[ProjectionRule, ...]]
] = {
    AgentTranscode.NONE: no_rules,
    AgentTranscode.CLAUDE_MD_SYMLINK: md_symlink_rules,
    AgentTranscode.CODEX_TOML: toml_transcode_rules,
    AgentTranscode.CURSOR_MD: cursor_md_rules,
    AgentTranscode.DEVIN_MD: no_rules,
    AgentTranscode.COPILOT_AGENT_MD: copilot_agent_md_rules,
}
