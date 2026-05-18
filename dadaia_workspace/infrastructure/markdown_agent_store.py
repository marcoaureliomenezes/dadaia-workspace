"""MarkdownAgentStore — reads *.md agent files and returns raw frontmatter dicts.

This is the filesystem adapter consumed by features/agents/reader.py.
It mirrors the pattern established by MarkdownWorkflowStore but is intentionally
simpler: agent files have a flat frontmatter structure (no nested stage graphs),
so there is no validation or coercion here — that is the reader's responsibility.

Responsibilities of this module:
- Discover *.md files in a given directory.
- Split the YAML frontmatter block from the rest of the file.
- Parse frontmatter with pyyaml (safe_load).
- Return raw dicts; callers decide what to do with unknown keys.
- Log and skip files that are malformed, not raise.
"""

import logging
from pathlib import Path
from typing import Any

import yaml

_FRONTMATTER_DELIM = "---"
_SUFFIX = ".md"

logger = logging.getLogger(__name__)


def _split_frontmatter(text: str) -> str | None:
    """Extract the raw YAML frontmatter string from a Markdown file.

    Returns None if the file does not start with the frontmatter delimiter or
    if the closing delimiter is absent.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != _FRONTMATTER_DELIM:
        return None
    buffer: list[str] = []
    for line in lines[1:]:
        if line.strip() == _FRONTMATTER_DELIM:
            return "\n".join(buffer)
        buffer.append(line)
    # Closing delimiter was never found
    return None


def _parse_file(path: Path) -> dict[str, Any] | None:
    """Parse a single agent .md file and return its frontmatter as a dict.

    Returns None (logging a warning) if:
    - The file has no frontmatter delimiters.
    - The YAML is malformed.
    - The frontmatter does not parse to a mapping.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("agent_store: cannot read %s: %s", path, exc)
        return None

    raw = _split_frontmatter(text)
    if raw is None:
        logger.warning("agent_store: no frontmatter in %s — skipping", path.name)
        return None

    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        logger.warning("agent_store: malformed YAML in %s: %s — skipping", path.name, exc)
        return None

    if not isinstance(data, dict):
        logger.warning(
            "agent_store: frontmatter in %s is not a mapping (got %s) — skipping",
            path.name,
            type(data).__name__,
        )
        return None

    return data


class MarkdownAgentStore:
    """Reads *.md files from a directory and returns raw frontmatter dicts."""

    def __init__(self, agents_dir: Path) -> None:
        self._dir = agents_dir

    def _files(self) -> list[Path]:
        if not self._dir.exists() or not self._dir.is_dir():
            return []
        return sorted(self._dir.glob(f"*{_SUFFIX}"))

    def list_raw(self) -> list[dict[str, Any]]:
        """Return a list of raw frontmatter dicts for all parseable agent files."""
        results: list[dict[str, Any]] = []
        for path in self._files():
            data = _parse_file(path)
            if data is not None:
                results.append(data)
        return results
