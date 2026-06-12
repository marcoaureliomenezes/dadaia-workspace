"""Codex/OpenCode frontmatter-parsing and TOML/rules rendering free functions.

These functions are extracted from ``public_assets.py`` to keep that module under
600 lines.  All names remain importable from
``dadaia_workspace.infrastructure.public_assets`` via its re-export block.
"""

from __future__ import annotations

import re
from pathlib import Path

from dadaia_workspace.infrastructure.public_assets_common import _toml_escape

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# `opencode_model:` lets agents declare a cheaper model for the OpenCode projection.
_FRONTMATTER_OPENCODE_MODEL_RE = re.compile(r"^opencode_model:\s*(.+?)$", re.MULTILINE)
_FRONTMATTER_MODEL_VALUE_RE = re.compile(r"^(model:\s*)(.+?)$", re.MULTILINE)
_FRONTMATTER_OPENCODE_MODEL_FIELD_RE = re.compile(r"^opencode_model:[^\n]*\n", re.MULTILINE)
# `color:` is Claude Code-specific (panel tier accent) and causes a frontmatter parse
# failure in OpenCode 1.14.x. Strip it from the OpenCode projection only (FR-OC-1).
_FRONTMATTER_COLOR_RE = re.compile(r"^color:[^\n]*\n", re.MULTILINE)
# OpenCode v1.14+ expects `tools` to be an object or omitted — not an array.
_FRONTMATTER_TOOLS_RE = re.compile(r"^tools:\n(?:  - [^\n]+\n)*", re.MULTILINE)
# Single `  - <Tool>` list item inside a `tools:` YAML block.
_FRONTMATTER_TOOLS_LIST_ITEM_RE = re.compile(r"^  - ([^\n]+)$", re.MULTILINE)
# T-35: forbid the legacy `software-engineer` alias inside public/
_LEGACY_SE_ALIAS_RE = re.compile(
    r"subagent_type\s*[:=]\s*[\"']?software-engineer(?![-_a-z])",
    re.IGNORECASE,
)
# Parallel workflow detection
_FRONTMATTER_PARALLEL_GROUP_RE = re.compile(r"^\s*parallel_group:\s*\S", re.MULTILINE)

_CODEX_READ_ONLY_AGENTS = frozenset(
    {
        "code-reviewer",
        "design-specialist",
        "project-auditor",
        "qa-engineer",
        "security-reviewer",
        "software-architect",
    }
)
_CODEX_HIGH_EFFORT_AGENTS = frozenset({"ai-engineer", "project-manager", "product-engineer"})
_CODEX_SKILL_REF_PREFIXES = (
    "ai-harness-",
    "dev-server-registry",
    "design-ctx",
    "drift-detection",
    "frontend-ctx",
    "harness-primitives",
    "memory-ctx",
    "project-orchestration",
)

# T-OC-03 (FR-OC-2): project the agent's Claude `tools:` grants into an OpenCode
# per-agent `permission:` block.
_CLAUDE_TOOL_TO_OPENCODE_PERMISSION = {
    "Edit": "edit",
    "Write": "edit",
    "Bash": "bash",
    "WebFetch": "webfetch",
    "Agent": "task",
}
# Categories always emitted (allow if granted, deny otherwise)
_OPENCODE_PERMISSION_CATEGORIES = ("edit", "bash", "webfetch", "task")
# Claude tools with no OpenCode permission equivalent
_OPENCODE_UNSUPPORTED_TOOLS = ("WebSearch",)

# Whitelist of agent frontmatter fields that may be emitted to codex config.toml.
_TOML_SAFE_AGENT_FIELDS: frozenset[str] = frozenset({"name", "description", "model", "tools"})

# Matches a YAML list item under `tools:` (e.g. "  - Read")
_AGENT_FM_TOOLS_ITEM_RE = re.compile(r"^  - (.+)$", re.MULTILINE)
# Matches a simple `key: value` line in frontmatter (single-line value)
_AGENT_FM_SIMPLE_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*): (.+)$", re.MULTILINE)
# Matches a folded/literal scalar intro: `key: >` or `key: |`
_AGENT_FM_BLOCK_SCALAR_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*): [>|]$", re.MULTILINE)

# ---------------------------------------------------------------------------
# Free functions
# ---------------------------------------------------------------------------


def _opencode_permission_block(frontmatter: str) -> str:
    """Build an OpenCode ``permission:`` frontmatter block from a Claude ``tools:`` list.

    Returns ``""`` when the agent declares no ``tools:`` block (nothing to map).
    """
    m = _FRONTMATTER_TOOLS_RE.search(frontmatter)
    if not m:
        return ""
    tools = {t.strip() for t in _FRONTMATTER_TOOLS_LIST_ITEM_RE.findall(m.group(0))}
    if not tools:
        return ""
    granted = {
        _CLAUDE_TOOL_TO_OPENCODE_PERMISSION[t]
        for t in tools
        if t in _CLAUDE_TOOL_TO_OPENCODE_PERMISSION
    }
    lines = ["permission:"]
    lines += [
        f"  {cat}: {'allow' if cat in granted else 'deny'}"
        for cat in _OPENCODE_PERMISSION_CATEGORIES
    ]
    lines += [f"# [opencode-unsupported]: {t}" for t in _OPENCODE_UNSUPPORTED_TOOLS if t in tools]
    return "\n".join(lines) + "\n"


def _render_agents_into_codex_config(agents_dir: Path) -> str:
    """Scan *agents_dir* for ``.md`` agent files and render TOML ``[agents.*]`` blocks.

    For each ``.md`` file (sorted for determinism):
    1. Parse YAML frontmatter via ``_parse_agent_frontmatter()``.
    2. If the result is non-empty (i.e., ``name`` key present), render via
       ``_render_agent_toml_block()``.
    3. Agents whose frontmatter cannot be parsed or are missing ``name`` are
       silently skipped (defensive — never breaks install).

    Returns the concatenated block string (may be empty string when no agents
    are found).
    """
    if not agents_dir.exists():
        return ""
    blocks: list[str] = []
    for md_file in sorted(agents_dir.glob("*.md")):
        try:
            text = md_file.read_text(encoding="utf-8")
            fm = _parse_agent_frontmatter(text)
            if not fm:
                continue
            name = str(fm.get("name", ""))
            if not name:
                continue
            blocks.append(_render_agent_toml_block(name, fm))
        except (OSError, ValueError):
            continue
    return "\n".join(blocks) + ("\n" if blocks else "")


def _render_codex_agent_toml(
    name: str,
    model: str,
    developer_instructions: str,
    description: str | None = None,
) -> str:
    """Serialize an agent as a TOML file for the Codex runtime.

    Emits Codex custom-agent fields:
    - ``name`` — basic string
    - ``description`` — basic string when available
    - ``model`` — basic string
    - ``sandbox_mode`` — conservative role boundary
    - ``model_reasoning_effort`` — explicit reasoning profile
    - ``developer_instructions`` — triple-quoted multiline basic string

    The function avoids external TOML serialiser dependencies; it builds the
    content manually and is safe for all printable Unicode in instructions text.

    In a TOML triple-quoted basic string, backslashes are escape characters.
    All literal backslashes in the body must be doubled (``\\``), and any
    embedded triple-double-quote sequences must be escaped character-by-character
    to prevent premature string termination.
    """
    # Step 1: escape backslashes first (must precede triple-quote escaping).
    escaped = developer_instructions.replace("\\", "\\\\")
    # Step 2: escape any embedded triple-double-quote sequences.
    escaped = escaped.replace('"""', '\\"\\"\\"')
    lines: list[str] = [
        f"name = {_toml_escape(name)}\n",
    ]
    if description:
        lines.append(f"description = {_toml_escape(description)}\n")
    sandbox_mode = "read-only" if name in _CODEX_READ_ONLY_AGENTS else "workspace-write"
    reasoning_effort = "high" if name in _CODEX_HIGH_EFFORT_AGENTS else "medium"
    lines.extend(
        [
            f"model = {_toml_escape(model)}\n",
            f"sandbox_mode = {_toml_escape(sandbox_mode)}\n",
            f"model_reasoning_effort = {_toml_escape(reasoning_effort)}\n",
            f'developer_instructions = """\n{escaped}\n"""\n',
        ]
    )
    return "".join(lines)


def _render_codex_command_policy_rules() -> str:
    """Return a Codex-native Starlark command policy.

    This is intentionally narrow. The larger dadaia behavioral protocols remain
    Markdown guidance in AGENTS.md, skills, agents, and workflows; only command
    approval/denial belongs in ``.codex/rules/*.rules``.
    """
    return """# Generated by "dadaia public install --target codex".

prefix_rule(
    pattern = [["rg", "ls", "find", "cat", "sed"]],
    decision = "allow",
    justification = "Read-only local inspection commands are safe in the dadaia workspace.",
    match = ["rg Codex", "ls -la", "find specs -maxdepth 2 -type f", "cat AGENTS.md", "sed -n 1,80p AGENTS.md"],
)

prefix_rule(
    pattern = ["git", ["status", "diff", "log", "show"]],
    decision = "allow",
    justification = "Local git inspection is safe and needed for review.",
    match = ["git status --short", "git diff", "git log --oneline", "git show HEAD"],
    not_match = ["git push", "git commit"],
)

prefix_rule(
    pattern = ["git", "push"],
    decision = "prompt",
    justification = "Publishing branches requires explicit operator approval after review gates.",
    match = ["git push origin feature/x"],
)

# prefix_rule matches the argv prefix LITERALLY (no PATH lookup, no basename
# normalization). The workspace mandates the venv-absolute invocation
# `.dadaia/.venv/bin/dadaia ...` (bare `dadaia` is intentionally off-PATH), so a
# pattern whose first token is `dadaia` would never fire in a compliant session.
# We therefore gate BOTH the venv-relative argv0 form actually used in this
# workspace's docs AND the bare name (for any non-compliant PATH invocation), and
# prove the real form in `match=`.
prefix_rule(
    pattern = [".dadaia/.venv/bin/dadaia", "public", "install"],
    decision = "prompt",
    justification = "Public install rewrites generated runtime projections.",
    match = [".dadaia/.venv/bin/dadaia public install --target codex", ".dadaia/.venv/bin/dadaia public install --target all"],
    not_match = [".dadaia/.venv/bin/dadaia public doctor"],
)

prefix_rule(
    pattern = ["dadaia", "public", "install"],
    decision = "prompt",
    justification = "Public install rewrites generated runtime projections (bare-name fallback).",
    match = ["dadaia public install --target codex", "dadaia public install --target all"],
)

prefix_rule(
    pattern = [".dadaia/.venv/bin/dadaia", "context", "dead"],
    decision = "prompt",
    justification = "Making a context dead syncs and removes a repository from disk.",
    match = [".dadaia/.venv/bin/dadaia context dead dadaia-workspace"],
    not_match = [".dadaia/.venv/bin/dadaia context show --json"],
)

prefix_rule(
    pattern = ["dadaia", "context", "dead"],
    decision = "prompt",
    justification = "Making a context dead syncs and removes a repository from disk (bare-name fallback).",
    match = ["dadaia context dead dadaia-workspace"],
)

prefix_rule(
    pattern = [["rm", "mv", "cp", "chmod", "chown", "sudo", "docker", "systemctl"]],
    decision = "prompt",
    justification = "Potentially destructive or host-affecting commands require review.",
    match = ["rm -rf tmp", "mv a b", "cp a b", "chmod 600 file", "sudo systemctl status app"],
)
"""


def _render_agents_config_file_blocks(agents_dir: Path) -> str:
    """Generate ``[agents."<name>"] config_file = ...`` TOML blocks.

    Replaces the inline agent block rendering.  For each canonical agent
    (determined by the ``.md`` file listing) a two-line TOML block is emitted:

    .. code-block:: toml

        [agents."<name>"]
        config_file = "agents/<name>.toml"

    Agents whose ``.md`` cannot be parsed (missing ``name``) are skipped.
    """
    if not agents_dir.exists():
        return ""
    blocks: list[str] = []
    for md_file in sorted(agents_dir.glob("*.md")):
        try:
            text = md_file.read_text(encoding="utf-8")
            fm = _parse_agent_frontmatter(text)
            if not fm:
                continue
            name = str(fm.get("name", ""))
            if not name:
                continue
            key_escaped = name.replace("\\", "\\\\").replace('"', '\\"')
            blocks.append(f'[agents."{key_escaped}"]\n')
            blocks.append(f'config_file = "agents/{name}.toml"\n')
        except (OSError, ValueError):
            continue
    return "".join(blocks)


def _render_agent_toml_block(name: str, fm: dict[str, object]) -> str:
    """Render a ``[agents."<name>"]`` TOML table block from parsed frontmatter *fm*.

    Keys are always quoted for safety (required for hyphenated names like
    ``software-engineer``). Missing or None fields are omitted. The ``tools``
    field, if present, is emitted as a TOML array of basic strings.

    Names containing ``]`` or newline characters are rejected (cannot appear
    safely inside a TOML table header, even with quoting). Double-quotes and
    backslashes are escaped with a leading backslash so the header is valid
    TOML (e.g. a name like ``a"b`` becomes ``[agents."a\\"b"]``).
    """
    if "]" in name:
        raise ValueError(f"Agent name contains invalid character ']': {name!r}")
    if "\n" in name:
        raise ValueError(f"Agent name contains newline character: {name!r}")
    # Escape backslash first (must precede quote escape to avoid double-escaping)
    key_escaped = name.replace("\\", "\\\\").replace('"', '\\"')
    lines: list[str] = [f'[agents."{key_escaped}"]\n']
    for field in ("name", "description", "model"):
        val = fm.get(field)
        if val is None:
            continue
        lines.append(f"{field} = {_toml_escape(val)}\n")
    tools_val = fm.get("tools")
    if tools_val is not None and isinstance(tools_val, list):
        items = ", ".join(_toml_escape(t) for t in tools_val)
        lines.append(f"tools = [{items}]\n")
    return "".join(lines)


def _parse_agent_frontmatter(text: str) -> dict[str, object]:
    """Parse YAML frontmatter from an agent .md file using stdlib regex only.

    Extracts the block between the first pair of ``---`` fences. Supports:
    - Simple ``key: value`` scalar fields (string values).
    - Folded scalar ``key: >`` — continuation lines are joined with a space.
    - YAML list under ``tools:`` — items prefixed with ``  - `` (two-space indent).

    Unknown fields (outside ``_TOML_SAFE_AGENT_FIELDS``) are silently dropped.
    Returns an empty dict if ``name`` is missing or frontmatter is absent.
    """
    if not text.startswith("---\n"):
        return {}
    end_idx = text.find("\n---\n", 4)
    if end_idx == -1:
        return {}
    frontmatter = text[4 : end_idx + 1]

    result: dict[str, object] = {}
    lines = frontmatter.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        # Detect block scalar (folded `>` or literal `|`)
        block_m = _AGENT_FM_BLOCK_SCALAR_RE.match(line)
        if block_m:
            key = block_m.group(1)
            # Collect continuation lines (indented)
            body_lines: list[str] = []
            i += 1
            while i < len(lines) and (lines[i].startswith("  ") or lines[i] == ""):
                body_lines.append(lines[i].strip())
                i += 1
            # Join non-empty continuation lines with a space (folded scalar semantics)
            value = " ".join(part for part in body_lines if part)
            if key in _TOML_SAFE_AGENT_FIELDS:
                result[key] = value
            continue

        # Detect tools list  (`tools:\n  - item\n  - item`)
        if line == "tools:":
            items: list[str] = []
            i += 1
            while i < len(lines) and _AGENT_FM_TOOLS_ITEM_RE.match(lines[i]):
                m = _AGENT_FM_TOOLS_ITEM_RE.match(lines[i])
                if m:
                    items.append(m.group(1).strip())
                i += 1
            if "tools" in _TOML_SAFE_AGENT_FIELDS:
                result["tools"] = items
            continue

        # Simple scalar
        simple_m = _AGENT_FM_SIMPLE_RE.match(line)
        if simple_m:
            key = simple_m.group(1)
            value_str = simple_m.group(2).strip()
            if key in _TOML_SAFE_AGENT_FIELDS:
                result[key] = value_str
        i += 1

    # Require `name` — without it, the block cannot be rendered
    if "name" not in result:
        return {}
    return result


def _parse_write_allowlist(text: str) -> list[str]:
    """Extract ``paths.write_allowlist`` globs from agent .md frontmatter (stdlib only).

    Used to pre-compile ``.dadaia/agentic/agents.index.json`` (T-016-00) so the SDD
    gate's RULE D performs an O(1) JSON lookup instead of an inline YAML parse on
    every PreToolUse. Returns ``[]`` when the agent declares no write_allowlist.
    """
    if not text.startswith("---\n"):
        return []
    end_idx = text.find("\n---\n", 4)
    if end_idx == -1:
        return []

    in_paths = False
    in_wl = False
    items: list[str] = []
    for line in text[4 : end_idx + 1].splitlines():
        if not line.strip():
            continue
        stripped = line.strip()
        indent = len(line) - len(line.lstrip())
        if indent == 0:
            in_paths = stripped == "paths:"
            in_wl = False
            continue
        if not in_paths:
            continue
        if in_wl and stripped.startswith("- "):
            items.append(stripped[2:].strip())
            continue
        # A sub-key under `paths:` (write_allowlist:, read_allowlist:, …).
        in_wl = stripped == "write_allowlist:"
    return items


def _parse_skills_from_frontmatter(text: str) -> list[str]:
    """Extract the ``skills:`` list from agent YAML frontmatter.

    Locates the ``skills:`` key inside the opening ``---`` block and collects
    indented ``  - <name>`` list items, stopping at the next top-level key or
    end of the frontmatter block.  Returns an empty list when frontmatter is
    absent or contains no ``skills:`` key.
    """
    if not text.startswith("---\n"):
        return []
    end_idx = text.find("\n---\n", 4)
    if end_idx == -1:
        return []
    frontmatter = text[4 : end_idx + 1]

    skills: list[str] = []
    in_skills = False
    for line in frontmatter.splitlines():
        if line.rstrip() == "skills:":
            in_skills = True
            continue
        if in_skills:
            stripped = line.strip()
            if stripped.startswith("- "):
                skills.append(stripped[2:].strip())
            elif line and not line.startswith(" ") and not line.startswith("\t"):
                in_skills = False  # next top-level key — skills block ended
    return skills


def _strip_tools_from_frontmatter(content: str) -> str:
    """Strip the `tools` array from YAML frontmatter for OpenCode compatibility."""
    if not content.startswith("---\n"):
        return content
    end_idx = content.find("\n---\n", 4)
    if end_idx == -1:
        return content
    frontmatter = content[4 : end_idx + 1]
    cleaned = _FRONTMATTER_TOOLS_RE.sub("", frontmatter)
    return f"---\n{cleaned}---\n{content[end_idx + 5 :]}"


def _prepare_agent_for_opencode(content: str) -> str:
    """Prepare an agent .md file for the OpenCode projection.

    - Strips the `tools` array (OpenCode v1.14+ incompatibility with list form)
    - If `opencode_model:` is declared, swaps the `model:` value and removes the field
    """
    if not content.startswith("---\n"):
        return content
    end_idx = content.find("\n---\n", 4)
    if end_idx == -1:
        return content
    frontmatter = content[4 : end_idx + 1]
    body = content[end_idx + 5 :]

    # Derive the permission block from the ORIGINAL frontmatter (before tools is stripped).
    permission_block = _opencode_permission_block(frontmatter)

    m = _FRONTMATTER_OPENCODE_MODEL_RE.search(frontmatter)
    if m:
        opencode_model = m.group(1).strip()
        frontmatter = _FRONTMATTER_MODEL_VALUE_RE.sub(
            lambda match: f"{match.group(1)}{opencode_model}", frontmatter, count=1
        )
    frontmatter = _FRONTMATTER_TOOLS_RE.sub("", frontmatter)
    frontmatter = _FRONTMATTER_OPENCODE_MODEL_FIELD_RE.sub("", frontmatter)
    frontmatter = _FRONTMATTER_COLOR_RE.sub("", frontmatter)
    if permission_block:
        frontmatter = frontmatter + permission_block
    return f"---\n{frontmatter}---\n{body}"
