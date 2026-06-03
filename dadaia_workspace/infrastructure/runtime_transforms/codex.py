"""Codex runtime prompt transformer (ADR-2).

Provides :func:`transform_for_codex` — a deterministic function that adapts the
canonical body of an agent persona (with frontmatter already stripped) to the
Codex runtime.

Transformations applied (v1, per ADR-2 §Transformações obrigatórias):

1. Replace references to the Claude Code ``Agent`` tool with Codex-native
   multi-agent wording:
   - `` `Agent` tool `` → ``deferred multi-agent tool via tool_search``
   - ``Agent tool``     → ``deferred multi-agent tool via tool_search``
   - ``Agent.dispatch`` → ``multi-agent dispatch discovered via tool_search``
   - `` `Agent` ``      → ``multi-agent tool discovered via tool_search``

2. Preserve hook semantics. Claude-authored references to ``PreToolUse``,
   ``PostToolUse``, and ``UserPromptSubmit`` remain visible because Codex
   receives equivalent generated hooks where the runtime supports them.

3. Replace Claude model identifiers (``claude-*``) appearing in body text with
   their Codex equivalents from the model mapping table (ADR-5).  This prevents
   AC3 violations when agent body prose documents Claude model names in tables
   or capability descriptions.

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
    # "`Agent` tool" → Codex deferred tool-discovery wording.
    ("`Agent` tool", "deferred multi-agent tool via `tool_search`"),
    # "Agent tool" (unquoted) → Codex deferred tool-discovery wording.
    ("Agent tool", "deferred multi-agent tool via `tool_search`"),
    # "Agent.dispatch" → Codex dispatch wording.
    ("Agent.dispatch", "multi-agent dispatch discovered via `tool_search`"),
    # "`Agent`" alone (e.g. tool-table entries) → Codex tool-discovery wording.
    ("`Agent`", "multi-agent tool discovered via `tool_search`"),
)

# Pattern matching any ``claude-<identifier>`` token in body prose.
# Sorted longest-first so that more-specific identifiers take priority
# (e.g. ``claude-haiku-4-5-20251001`` before ``claude-haiku``).
_KNOWN_MODEL_RE: re.Pattern[str] = re.compile(
    r"(" + "|".join(re.escape(k) for k in sorted(MODEL_MAP, key=len, reverse=True)) + r")"
)

# Catch-all for any remaining ``claude-*`` identifiers not in MODEL_MAP
# (e.g. ``claude-haiku`` without version suffix).  These are replaced with the
# default Codex model name so that AC3 (zero ``claude-*`` in .codex/) is met.
_CLAUDE_GENERIC_RE: re.Pattern[str] = re.compile(r"claude-[\w.-]+")

# Default Codex model used when no exact mapping exists.
_CODEX_DEFAULT_MODEL = "gpt-5.3-codex"


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

    # Replace any remaining ``claude-*`` identifiers not covered by MODEL_MAP
    # (e.g. bare ``claude-haiku`` without version suffix) with the default model.
    result = _CLAUDE_GENERIC_RE.sub(_CODEX_DEFAULT_MODEL, result)

    return result
