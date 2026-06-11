"""Codex runtime prompt transformer (ADR-2).

Provides :func:`transform_for_codex` — a deterministic function that adapts the
canonical body of an agent persona (with frontmatter already stripped) to the
Codex runtime.

Transformations applied:

1. Replace references to the Claude Code ``Agent`` tool with explicit Codex
   subagent delegation wording. Codex has native custom agents/subagents; workflow
   Markdown remains documentation and does not auto-execute fan-out.

2. Preserve hook semantics. Claude-authored references to ``PreToolUse``,
   ``PostToolUse``, and ``UserPromptSubmit`` remain visible because Codex
   receives equivalent generated hooks where the runtime supports them.

3. Replace only known Claude model identifiers with their Codex equivalents
   from the model mapping table. Other ``claude-*`` identifiers are preserved
   because they may be legitimate skill names such as
   ``ai-harness-claude-code``.

4. Preserve all remaining content verbatim.

The function is intentionally free of side effects, I/O, and non-determinism.
"""

import re

from dadaia_workspace.infrastructure.runtime_transforms.model_mapping import MODEL_MAP

# ---------------------------------------------------------------------------
# Replacement table — ordered from most-specific to least-specific so that
# longer patterns take priority over shorter ones (e.g. "`Agent` tool" before
# "`Agent`").
# ---------------------------------------------------------------------------

_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    (".claude/rules/workspace-protocol.md", "AGENTS.md and projected workspace protocols"),
    ("`Agent` tool", "explicit Codex subagent delegation"),
    ("Agent tool", "explicit Codex subagent delegation"),
    ("Agent.dispatch", "explicit Codex subagent delegation"),
    ("`Agent`", "explicit Codex subagent delegation"),
)

# Pattern matching any ``claude-<identifier>`` token in body prose.
# Sorted longest-first so that more-specific identifiers take priority
# (e.g. ``claude-haiku-4-5-20251001`` before ``claude-haiku``).
_KNOWN_MODEL_RE: re.Pattern[str] = re.compile(
    r"(" + "|".join(re.escape(k) for k in sorted(MODEL_MAP, key=len, reverse=True)) + r")"
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

    # Replace known Claude model identifiers in body prose (ADR-5 / AC3).
    result = _KNOWN_MODEL_RE.sub(lambda m: MODEL_MAP[m.group(1)], result)

    return result
