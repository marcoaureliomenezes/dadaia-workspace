"""Agentic-entity registry loader — the abstract, harness-agnostic entity surface.

The registry (``dadaia_workspace/public/entities/registry.json``) is THE source the
scaffolded core surface derives from (constitution §12.5): sub-agents derive from
**Personas**, hooks from **Deterministic Behaviors**, rules from **Abstract Rules**;
skills and AGENTS.md are harness-agnostic by construction (universal). This module is
the one read path — the panel and the derivation contract both consume it, so the
registry can never fork into per-consumer copies.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_REGISTRY_PATH = Path(__file__).resolve().parents[2] / "public" / "entities" / "registry.json"

SCHEMA_VERSION = "agentic-entities-v1"


def load_registry() -> dict[str, Any]:
    """Load and shape-check the packaged abstract-entity registry.

    Raises:
        ValueError: on a missing file, unparseable JSON, or a wrong
            ``schema_version`` — the registry is core law surface and must fail
            LOUDLY, never degrade to an empty panel section.
    """
    try:
        raw = _REGISTRY_PATH.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"agentic-entity registry unreadable at {_REGISTRY_PATH}: {exc}") from exc
    data = json.loads(raw)
    if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"agentic-entity registry at {_REGISTRY_PATH} is not {SCHEMA_VERSION!r}")
    for key in ("personas", "behaviors", "rules", "universal"):
        if key not in data:
            raise ValueError(f"agentic-entity registry missing required section {key!r}")
    return data


def persona_ids(registry: dict[str, Any]) -> frozenset[str]:
    """All persona ids (core + plugin stubs)."""
    return frozenset(p["id"] for p in registry["personas"])


_SKILLS_ROOT = _REGISTRY_PATH.parent.parent / "skills"


def core_skills() -> list[tuple[str, str]]:
    """The scaffolded core skills as ``(name, description)`` pairs, sorted by name.

    Universal entities (constitution §12.5): every supported harness discovers
    them natively under ``.agents/skills/``, so their SOURCE list is the packaged
    ``public/skills/`` tree itself — no registry duplicate to drift from. The
    description is the SKILL.md frontmatter ``description`` value (plain or
    ``>``-folded scalar).
    """
    skills: list[tuple[str, str]] = []
    for skill_dir in sorted(_SKILLS_ROOT.iterdir()):
        manifest = skill_dir / "SKILL.md"
        if not skill_dir.is_dir() or not manifest.is_file():
            continue
        skills.append((skill_dir.name, _frontmatter_description(manifest)))
    return skills


def _frontmatter_description(manifest: Path) -> str:
    """Extract the frontmatter ``description`` value from a SKILL.md file."""
    lines = manifest.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return ""
    collected: list[str] = []
    in_description = False
    for line in lines[1:]:
        stripped = line.strip()
        if stripped == "---":
            break
        if in_description:
            if line.startswith((" ", "\t")) and stripped:
                collected.append(stripped)
                continue
            break
        if stripped.startswith("description:"):
            value = stripped.removeprefix("description:").strip()
            if value and value not in (">", "|", ">-", "|-"):
                return value
            in_description = True
    return " ".join(collected)
