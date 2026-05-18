"""Canonical agent reader — features/agents/reader.py.

Reads agent definition files from the canonical location and returns
a list of AgentDTO objects.

Resolution order (first non-empty wins):
  1. $DADAIA_AGENTS_DIR env var (absolute or relative path)
  2. <workspace_root>/.dadaia/agentic/agents/
  3. <workspace_root>/.claude/agents/

The reader applies an allowlist to frontmatter fields: only fields listed in
_ALLOWED_FIELDS are mapped to AgentDTO — unknown keys are logged and dropped.

Resilience: files with malformed YAML or missing frontmatter are skipped with
a warning; they do not abort the read.
"""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dadaia_workspace.infrastructure.markdown_agent_store import MarkdownAgentStore

logger = logging.getLogger(__name__)

# Allowlist of frontmatter keys that map to AgentDTO fields.
# Keys absent from this set are silently dropped after a warning log.
_ALLOWED_FIELDS: frozenset[str] = frozenset(
    {
        "name",
        "description",
        "skills",
        "tools",
        "model",
        "opencode_model",
        "maxTurns",          # frontmatter key (camelCase)
        "max_turns",         # alternative snake_case spelling
        "input_contract",
    }
)


@dataclass
class AgentDTO:
    """Data-transfer object for a canonical agent definition.

    Fields correspond to the §5.1 shape from the R3 SPEC.
    """

    id: str
    name: str
    description: str
    skills: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    model: str | None = None
    opencode_model: str | None = None
    max_turns: int | None = None
    input_contract: dict[str, Any] | None = None


def _resolve_agents_dir(workspace_root: Path) -> Path | None:
    """Resolve the agent directory according to the 3-step resolution order.

    Returns the first directory that exists and contains at least one .md file,
    or None if no suitable directory is found.
    """
    env_dir = os.environ.get("DADAIA_AGENTS_DIR")
    if env_dir:
        candidate = Path(env_dir)
        logger.debug("agent_reader: using DADAIA_AGENTS_DIR=%s", candidate)
        return candidate

    agentic = workspace_root / ".dadaia" / "agentic" / "agents"
    if agentic.exists() and any(agentic.glob("*.md")):
        logger.debug("agent_reader: using .dadaia/agentic/agents/")
        return agentic

    claude = workspace_root / ".claude" / "agents"
    if claude.exists() and any(claude.glob("*.md")):
        logger.debug("agent_reader: using .claude/agents/")
        return claude

    logger.debug("agent_reader: no agent directory found under %s", workspace_root)
    return None


def _raw_to_dto(raw: dict[str, Any]) -> AgentDTO | None:
    """Convert a raw frontmatter dict to an AgentDTO, applying the allowlist.

    Returns None if the dict lacks the mandatory 'name' field.
    """
    # Detect and warn about unknown keys
    unknown = set(raw) - _ALLOWED_FIELDS
    if unknown:
        name_hint = raw.get("name", "<unknown>")
        logger.warning(
            "agent_reader: %s has unknown frontmatter fields %s — dropping",
            name_hint,
            sorted(unknown),
        )

    name = raw.get("name")
    if not name or not isinstance(name, str):
        logger.warning("agent_reader: agent file missing 'name' field — skipping")
        return None

    description = raw.get("description")
    if not description or not isinstance(description, str):
        description = ""

    # maxTurns (camelCase) takes priority over max_turns (snake_case)
    max_turns_raw = raw.get("maxTurns") or raw.get("max_turns")
    max_turns: int | None = None
    if max_turns_raw is not None:
        try:
            max_turns = int(max_turns_raw)
        except (ValueError, TypeError):
            logger.warning(
                "agent_reader: %s has non-integer maxTurns/max_turns value %r — ignoring",
                name,
                max_turns_raw,
            )

    skills_raw = raw.get("skills")
    skills: list[str] = (
        [str(s) for s in skills_raw] if isinstance(skills_raw, list) else []
    )

    tools_raw = raw.get("tools")
    tools: list[str] = (
        [str(t) for t in tools_raw] if isinstance(tools_raw, list) else []
    )

    model_raw = raw.get("model")
    model: str | None = str(model_raw) if model_raw is not None else None

    opencode_model_raw = raw.get("opencode_model")
    opencode_model: str | None = (
        str(opencode_model_raw) if opencode_model_raw is not None else None
    )

    input_contract_raw = raw.get("input_contract")
    input_contract: dict[str, Any] | None = (
        input_contract_raw if isinstance(input_contract_raw, dict) else None
    )

    return AgentDTO(
        id=name,
        name=name,
        description=description.strip(),
        skills=skills,
        tools=tools,
        model=model,
        opencode_model=opencode_model,
        max_turns=max_turns,
        input_contract=input_contract,
    )


def read_canonical_agents(workspace_root: Path) -> list[AgentDTO]:
    """Read all canonical agent definitions and return a list of AgentDTOs.

    Resolution order: $DADAIA_AGENTS_DIR → .dadaia/agentic/agents/ → .claude/agents/
    Malformed files are skipped with a warning. Unknown frontmatter fields are dropped.
    """
    agents_dir = _resolve_agents_dir(workspace_root)
    if agents_dir is None:
        return []

    store = MarkdownAgentStore(agents_dir)
    raw_list = store.list_raw()

    result: list[AgentDTO] = []
    for raw in raw_list:
        dto = _raw_to_dto(raw)
        if dto is not None:
            result.append(dto)

    logger.debug("agent_reader: loaded %d agents from %s", len(result), agents_dir)
    return result
