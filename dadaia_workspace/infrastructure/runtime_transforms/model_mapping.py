"""Claude-to-Codex model identifier mapping (ADR-5).

The canonical agent frontmatter uses Claude model identifiers (e.g.
``claude-sonnet-4-6``).  Codex TOML files must not contain any ``claude-*``
strings (AC3).  This module provides the authoritative translation table and a
helper that raises explicitly on unknown identifiers so that ``dadaia public
install --target codex`` fails loudly rather than silently emitting a bad model
field.
"""

MODEL_MAP: dict[str, str] = {
    "claude-fable-5": "gpt-5.5",
    "claude-opus-4-7": "gpt-5.5",
    "claude-opus-4-8": "gpt-5.5",
    "claude-sonnet-4-6": "gpt-5.3-codex",
    "claude-haiku-4-5-20251001": "gpt-5.4-mini",
}


def map_model(claude_id: str) -> str:
    """Return the Codex model identifier for *claude_id*.

    Args:
        claude_id: A Claude model identifier as it appears in agent frontmatter
            (e.g. ``"claude-sonnet-4-6"``).

    Returns:
        The corresponding Codex model identifier string.

    Raises:
        ValueError: If *claude_id* is not present in :data:`MODEL_MAP`.
    """
    if claude_id not in MODEL_MAP:
        raise ValueError(f"No Codex mapping for model: {claude_id!r}")
    return MODEL_MAP[claude_id]
