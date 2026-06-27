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
import re
import sys
from pathlib import Path
from typing import Any

from dadaia_workspace.core.models.agent import (
    AgentDTO,
    AgentNotFoundError,
    AgentPromptResult,
    InvalidAgentIdError,
)
from dadaia_workspace.core.protocols.agents_provider import AgentsProvider
from dadaia_workspace.infrastructure.markdown_agent_store import MarkdownAgentStore

# AgentDTO / AgentPromptResult / the error types now live in core/models/agent.py
# (NEW-02 boundary). Re-exported here so existing
# `from dadaia_workspace.features.agents.reader import AgentDTO` callers keep working.
__all__ = [
    "AgentDTO",
    "AgentNotFoundError",
    "AgentPromptResult",
    "AgentsProvider",
    "FileSystemAgentsProvider",
    "InvalidAgentIdError",
    "MissingTierError",
    "get_prompt",
    "read_canonical_agents",
]

logger = logging.getLogger(__name__)

# Allowlist of frontmatter keys that map to AgentDTO fields.
# Keys absent from this set are silently dropped after a warning log.
_ALLOWED_FIELDS: frozenset[str] = frozenset(
    {
        "name",
        "description",
        "tier",  # orchestration tier: 1 = orchestrator, 2 = curator, 3 = leaf specialist
        "skills",
        "tools",
        "model",
        "maxTurns",  # frontmatter key (camelCase)
        "max_turns",  # alternative snake_case spelling
        "input_contract",
        "paths",  # declarative path allowlist (AGT-32; not enforced this release)
        "color",  # optional display hint (game agents); not enforced
        "plugin",  # plugin STUB marker (constitution §14); excluded from panel roster
        "gate_role",  # §7 phase / review-gate role hint (panel lifecycle derivation)
        "activity_class",  # §1 activity class hint (not mapped to a DTO field yet)
        "lease_relationship",  # lease note (not mapped to a DTO field yet)
    }
)


class MissingTierError(ValueError):
    """Raised when an agent frontmatter has an invalid (non-int or out-of-range) 'tier' value.

    Note: a *missing* tier field is tolerated — it defaults to 3 with a stderr warning.
    This error is only raised when 'tier' is present but invalid (non-integer or not in
    {1, 2, 3}), so that typos produce loud failures while stale staged files are tolerated.
    """


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

    # Plugin stubs (``plugin: true``) carry no behavior and intentionally omit
    # the full frontmatter (tier/model/etc.). They are excluded from the panel
    # roster downstream, so suppress the missing-tier warning for them.
    is_plugin_stub = raw.get("plugin") is True

    # tier: int in {1, 2, 3}; missing → default 3 with warning; invalid → MissingTierError
    tier_raw = raw.get("tier")
    if tier_raw is None:
        if not is_plugin_stub:
            sys.stderr.write(
                f"agent_reader: WARNING — '{name}' is missing the 'tier' frontmatter field; "
                "defaulting to tier=3 (leaf specialist). "
                "Add 'tier: 3' (or 1/2) to silence this warning.\n"
            )
        tier = 3
    else:
        try:
            tier = int(tier_raw)
        except (ValueError, TypeError) as exc:
            raise MissingTierError(
                f"agent_reader: '{name}' has non-integer 'tier' value {tier_raw!r}"
            ) from exc
        if tier not in {1, 2, 3}:
            raise MissingTierError(
                f"agent_reader: '{name}' has invalid 'tier' value {tier!r} — must be 1, 2, or 3"
            )

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
    skills: list[str] = [str(s) for s in skills_raw] if isinstance(skills_raw, list) else []

    tools_raw = raw.get("tools")
    tools: list[str] = [str(t) for t in tools_raw] if isinstance(tools_raw, list) else []

    model_raw = raw.get("model")
    model: str | None = str(model_raw) if model_raw is not None else None

    input_contract_raw = raw.get("input_contract")
    input_contract: dict[str, Any] | None = (
        input_contract_raw if isinstance(input_contract_raw, dict) else None
    )

    paths_raw = raw.get("paths")
    paths: dict[str, list[str]] | None = paths_raw if isinstance(paths_raw, dict) else None

    plugin = bool(raw.get("plugin") is True)

    gate_role_raw = raw.get("gate_role")
    gate_role: str | None = str(gate_role_raw) if gate_role_raw is not None else None

    return AgentDTO(
        id=name,
        name=name,
        description=description.strip(),
        tier=tier,
        skills=skills,
        tools=tools,
        model=model,
        max_turns=max_turns,
        input_contract=input_contract,
        paths=paths,
        plugin=plugin,
        gate_role=gate_role,
    )


# ---------------------------------------------------------------------------
# Prompt fetch helpers (PR3-09)
# ---------------------------------------------------------------------------

# ID validation regex per SPEC §5.2.
# Must match ^[a-z0-9](?:[a-z0-9_-]{0,63}[a-z0-9])?$
_AGENT_ID_RE: re.Pattern[str] = re.compile(r"^[a-z0-9](?:[a-z0-9_-]{0,63}[a-z0-9])?$")

_FRONTMATTER_DELIM = "---"


def _strip_frontmatter(text: str) -> str:
    """Return the Markdown body with the YAML frontmatter block removed.

    If the file does not start with a frontmatter delimiter, the full text is
    returned unchanged.  Leading/trailing whitespace on the body is stripped.
    """
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != _FRONTMATTER_DELIM:
        return text.strip()
    # Skip until the closing delimiter.
    for idx in range(1, len(lines)):
        if lines[idx].strip() == _FRONTMATTER_DELIM:
            body = "".join(lines[idx + 1 :])
            return body.strip()
    # No closing delimiter — return text as-is.
    return text.strip()


def get_prompt(agent_id: str, workspace_root: Path) -> tuple[str, Path]:
    """Resolve an agent ID to its system prompt and source path.

    Resolution order mirrors read_canonical_agents():
      1. $DADAIA_AGENTS_DIR env var
      2. <workspace_root>/.dadaia/agentic/agents/
      3. <workspace_root>/.claude/agents/

    Parameters
    ----------
    agent_id:
        The agent identifier string (e.g. ``"software-engineer"``).  Must match
        ``_AGENT_ID_RE``.
    workspace_root:
        Absolute path to the workspace root.

    Returns
    -------
    tuple[str, Path]
        A ``(prompt_body, source_path)`` pair where ``prompt_body`` is the
        plain-text body of the agent Markdown file with frontmatter stripped,
        and ``source_path`` is the resolved path to the file.

    Raises
    ------
    InvalidAgentIdError
        If ``agent_id`` fails the regex check or the resolved path escapes
        the base directory (path traversal attempt).
    AgentNotFoundError
        If the agent ID is valid but no ``.md`` file exists in any candidate
        directory.
    """
    # --- Validate agent_id against the regex ---
    if not _AGENT_ID_RE.match(agent_id):
        raise InvalidAgentIdError(f"agent_id {agent_id!r} does not match the required pattern")

    # --- Resolve candidate directory ---
    agents_dir = _resolve_agents_dir(workspace_root)
    if agents_dir is None:
        raise AgentNotFoundError(f"No agents directory found for agent_id={agent_id!r}")

    # --- Construct candidate path ---
    candidate = agents_dir / f"{agent_id}.md"

    # --- Defence-in-depth: path traversal check ---
    # Resolve both paths and assert candidate is inside agents_dir.
    try:
        resolved_candidate = candidate.resolve()
        resolved_base = agents_dir.resolve()
    except OSError as exc:
        raise InvalidAgentIdError(
            f"Path resolution failed for agent_id={agent_id!r}: {exc}"
        ) from exc

    if not resolved_candidate.is_relative_to(resolved_base):
        logger.warning(
            "get_prompt: path traversal attempt detected for agent_id=%r "
            "(resolved %s escapes base %s)",
            agent_id,
            resolved_candidate,
            resolved_base,
        )
        raise InvalidAgentIdError(f"Path traversal attempt detected for agent_id={agent_id!r}")

    # --- Check existence ---
    if not resolved_candidate.exists():
        raise AgentNotFoundError(
            f"No agent file found for agent_id={agent_id!r} at {resolved_candidate}"
        )

    # --- Read and strip frontmatter ---
    try:
        text = resolved_candidate.read_text(encoding="utf-8")
    except OSError as exc:
        raise AgentNotFoundError(
            f"Cannot read agent file for agent_id={agent_id!r}: {exc}"
        ) from exc

    body = _strip_frontmatter(text)
    return body, resolved_candidate


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
        try:
            dto = _raw_to_dto(raw)
        except MissingTierError as exc:
            logger.warning("agent_reader: skipping agent — %s", exc)
            continue
        if dto is not None:
            result.append(dto)

    logger.debug("agent_reader: loaded %d agents from %s", len(result), agents_dir)
    return result


class FileSystemAgentsProvider(AgentsProvider):
    """Filesystem-backed `AgentsProvider` — the production implementation.

    Thin adapter over the module-level reader functions so the panel can depend
    on the `core/protocols/agents_provider.AgentsProvider` protocol instead of
    importing these functions concretely (NEW-02 boundary). Wired in
    `container.build_panel_service`.
    """

    def read_canonical_agents(self, workspace_root: Path) -> list[AgentDTO]:
        return read_canonical_agents(workspace_root)

    def get_prompt(self, agent_id: str, workspace_root: Path) -> AgentPromptResult:
        body, source_path = get_prompt(agent_id, workspace_root)
        return AgentPromptResult(body=body, source_path=source_path)
