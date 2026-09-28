"""Codex-drift doctor checks (D-CX-7, D-CX-8); byte drift is the projection rules' job."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from dadaia_workspace.core.models.doctor_report import DoctorLine, DoctorStatus
from dadaia_workspace.infrastructure.runtime_transforms.codex_assets import (
    _CODEX_SKILL_REF_PREFIXES,
)


def dcx7_codex_skill_refs(workspace_root: Path) -> list[DoctorLine]:
    """D-CX-7: generated Codex agents must not reference a missing ``dd-`` skill or persona."""
    codex_agents = workspace_root / ".codex" / "agents"
    skills = workspace_root / ".agents" / "skills"
    personas = {md.stem for md in (workspace_root / ".agents" / "agents").glob("*.md")}
    out: list[DoctorLine] = []
    if not codex_agents.exists():
        return out
    for toml_file in sorted(codex_agents.glob("*.toml")):
        try:
            data = tomllib.loads(toml_file.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            continue
        instructions = data.get("developer_instructions", "")
        if not isinstance(instructions, str):
            continue
        for match in re.finditer(r"`([a-z][a-z0-9.\-]+)`", instructions):
            skill = match.group(1)
            if (
                skill.startswith(_CODEX_SKILL_REF_PREFIXES)
                and skill not in personas
                and not (skills / skill / "SKILL.md").exists()
            ):
                msg = f"codex:agents/{toml_file.name}: missing skill '{skill}' (D-CX-7)"
                out.append(DoctorLine(DoctorStatus.ERROR, msg))
    return out


def dcx8_codex_rules_shape(codex_dir: Path) -> list[DoctorLine]:
    """D-CX-8: a Markdown file in ``rules/`` is not Codex Rules (the ``.rules`` bytes are a rule)."""
    return [
        DoctorLine(
            DoctorStatus.EXTRA, f"codex:rules/{md.name}: markdown is not Codex Rules (D-CX-8)"
        )
        for md in sorted((codex_dir / "rules").glob("*.md"))
    ]
