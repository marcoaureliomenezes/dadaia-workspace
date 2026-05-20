"""Codex runtime prompt transformer (ADR-2).

Provides :func:`transform_for_codex` — a deterministic function that adapts the
canonical body of an agent persona (with frontmatter already stripped) to the
Codex runtime.

Transformations applied (v1, per ADR-2 §Transformações obrigatórias):

1. Replace references to the Claude Code ``Agent`` tool with Codex subagent
   equivalents:
   - `` `Agent` tool `` → `` `subagent` dispatch ``
   - ``Agent tool``     → ``subagent dispatch``
   - ``Agent.dispatch`` → ``subagent.dispatch``
   - `` `Agent` ``      → `` `subagent` ``   (tool-table entries)

2. Remove Claude-specific hook lines (``UserPromptSubmit``, ``PreToolUse hook``,
   ``PostToolUse hook``) if any appear in the body.

3. Preserve all remaining content verbatim.

The function is intentionally free of side effects, I/O, and non-determinism.
"""

import re

# ---------------------------------------------------------------------------
# Replacement table — ordered from most-specific to least-specific so that
# longer patterns take priority over shorter ones (e.g. "`Agent` tool" before
# "`Agent`").
# ---------------------------------------------------------------------------

_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    # "`Agent` tool" → "`subagent` dispatch"
    ("`Agent` tool", "`subagent` dispatch"),
    # "Agent tool" (unquoted) → "subagent dispatch"
    ("Agent tool", "subagent dispatch"),
    # "Agent.dispatch" → "subagent.dispatch"
    ("Agent.dispatch", "subagent.dispatch"),
    # "`Agent`" alone (e.g. tool-table entries) → "`subagent`"
    ("`Agent`", "`subagent`"),
)

# Lines that reference Claude-specific hooks are removed entirely.
_HOOK_PATTERN: re.Pattern[str] = re.compile(
    r"UserPromptSubmit\s+hook|PreToolUse\s+hook|PostToolUse\s+hook",
    re.IGNORECASE,
)


def transform_for_codex(canonical_body: str, agent_id: str) -> str:  # noqa: ARG001
    """Return *canonical_body* adapted for the Codex runtime.

    The *agent_id* parameter is accepted for future per-agent overrides but is
    not used in v1; all transformations are uniform across agents.

    Args:
        canonical_body: Markdown text of the agent persona with frontmatter
            already removed.
        agent_id: The agent identifier (e.g. ``"project-manager"``).

    Returns:
        A non-empty string (after :meth:`str.strip`) with Claude Code–specific
        references replaced by their Codex equivalents.  When the body contains
        no Claude-specific patterns the output is identical to the input.
    """
    result = canonical_body

    # Apply string replacements in priority order.
    for old, new in _REPLACEMENTS:
        result = result.replace(old, new)

    # Remove lines containing Claude-specific hook references.
    if _HOOK_PATTERN.search(result):
        lines = result.splitlines(keepends=True)
        result = "".join(
            line for line in lines if not _HOOK_PATTERN.search(line)
        )

    return result
