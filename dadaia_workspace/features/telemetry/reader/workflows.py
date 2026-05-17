"""Workflow discovery reader — SKILL.md frontmatter parser (T-AM-09).

Walks ``.claude/skills/`` and ``.agents/skills/`` under *workspace_root*
recursively for ``SKILL.md`` files, parses their YAML frontmatter using the
stdlib ``re`` module (no pyyaml), and upserts the discovered workflows into
the telemetry store.

Design decisions:
    D-AM-09 — Walk .claude/skills/ and .agents/skills/.
    D12     — Read SKILL.md frontmatter (architect).
    Q-AM-2  — Best-effort substring match for agent linking (v1).

Privacy invariant: only frontmatter metadata is stored — no skill body content.
"""

from __future__ import annotations

import logging
import pathlib
import re
from dataclasses import dataclass

from dadaia_workspace.features.telemetry.store.dao import TelemetryDao
from dadaia_workspace.features.telemetry.store.models import Workflow, WorkflowAgent

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class ReadResult:
    """Summary of one workflow discovery cycle."""

    workflows_ingested: int = 0
    workflows_skipped: int = 0


# ---------------------------------------------------------------------------
# Frontmatter parser
# ---------------------------------------------------------------------------

_FRONTMATTER_RE = re.compile(r"^---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)
_KV_LINE_RE = re.compile(r"^(\w[\w\-]*)\s*:\s*(.*)$")


def _parse_frontmatter(text: str) -> dict[str, object] | None:
    """Extract YAML-like frontmatter from *text*.

    Returns a dict of key→value if frontmatter is present, else None.
    Only simple scalar values and bracket-list values are parsed.
    Multi-line values are not required for v1.
    Quoted strings (single or double) are unquoted.
    """
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return None

    result: dict[str, object] = {}
    for line in match.group(1).splitlines():
        line = line.rstrip()
        if not line or line.startswith("#"):
            continue
        m = _KV_LINE_RE.match(line)
        if not m:
            continue
        key = m.group(1)
        raw_val = m.group(2).strip()

        # Bracket list: [a, b, c]
        if raw_val.startswith("[") and raw_val.endswith("]"):
            inner = raw_val[1:-1]
            items = [_unquote(s.strip()) for s in inner.split(",") if s.strip()]
            result[key] = items
            continue

        result[key] = _unquote(raw_val)

    return result


def _unquote(s: str) -> str:
    """Remove surrounding single or double quotes from a string."""
    if len(s) >= 2 and s[0] in ('"', "'") and s[-1] == s[0]:
        return s[1:-1]
    return s


# ---------------------------------------------------------------------------
# Skill directories
# ---------------------------------------------------------------------------

_SKILL_DIRS = (".claude/skills", ".agents/skills")


def _find_skill_files(workspace_root: pathlib.Path) -> list[pathlib.Path]:
    """Recursively discover SKILL.md files under both skill directories."""
    found: list[pathlib.Path] = []
    for rel_dir in _SKILL_DIRS:
        skills_dir = workspace_root / rel_dir
        if not skills_dir.is_dir():
            continue
        found.extend(skills_dir.rglob("SKILL.md"))
    return found


# ---------------------------------------------------------------------------
# Core reader function
# ---------------------------------------------------------------------------


def read_workflows(
    workspace_root: pathlib.Path,
    dao: TelemetryDao,
    known_agent_names: list[str],
    now_iso: str,
) -> ReadResult:
    """Discover and ingest workflows from SKILL.md files under *workspace_root*.

    Args:
        workspace_root: Root of the workspace (e.g. ``pathlib.Path.cwd()``).
        dao: Telemetry DAO for persistence.
        known_agent_names: Agent names to match against skill body content.
        now_iso: ISO-8601 timestamp for ``discovered_at``/``last_seen_at``.

    Returns:
        ReadResult with counts of ingested/skipped workflows.
    """
    result = ReadResult()
    skill_files = _find_skill_files(workspace_root)

    for skill_path in skill_files:
        try:
            text = skill_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            logger.warning("Workflow reader: cannot read %s — %s", skill_path, exc)
            result.workflows_skipped += 1
            continue

        frontmatter = _parse_frontmatter(text)
        if frontmatter is None:
            logger.debug("Workflow reader: no frontmatter in %s — skipping", skill_path)
            result.workflows_skipped += 1
            continue

        name = frontmatter.get("name")
        if not name or not isinstance(name, str) or not name.strip():
            logger.debug(
                "Workflow reader: missing 'name' in frontmatter of %s — skipping", skill_path
            )
            result.workflows_skipped += 1
            continue

        name = name.strip()
        description_raw = frontmatter.get("description")
        description: str | None = str(description_raw).strip() if description_raw else None

        apply_to_raw = frontmatter.get("applyTo")
        apply_to: str | None
        if apply_to_raw is None:
            apply_to = None
        elif isinstance(apply_to_raw, list):
            apply_to = ",".join(str(x) for x in apply_to_raw)
        else:
            apply_to = str(apply_to_raw).strip() or None

        source_path = str(skill_path)

        dao.upsert_workflow(
            Workflow(
                name=name,
                source_path=source_path,
                description=description,
                apply_to=apply_to,
                discovered_at=now_iso,
                last_seen_at=now_iso,
            )
        )
        result.workflows_ingested += 1

        # Best-effort agent linking via case-insensitive substring match
        text_lower = text.lower()
        for agent_name in known_agent_names:
            if agent_name.lower() in text_lower:
                try:
                    dao.upsert_workflow_agent(
                        WorkflowAgent(workflow_name=name, agent_name=agent_name)
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.debug(
                        "Workflow reader: could not link agent %r to workflow %r — %s",
                        agent_name,
                        name,
                        exc,
                    )

    return result
