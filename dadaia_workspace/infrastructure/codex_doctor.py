"""Codex-drift doctor family — D-CX-1..D-CX-10 and ancillary checks.

These functions are extracted from ``FileSystemPublicAssetManager`` in
``public_assets.py`` to keep that module under 600 lines.  Each function takes
explicit arguments instead of ``self``, so there are no circular imports.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from dadaia_workspace.core.models.doctor_report import DoctorLine, DoctorStatus
from dadaia_workspace.infrastructure.runtime_transforms.codex_assets import (
    _CODEX_SKILL_REF_PREFIXES,
)

# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Individual checks
#
# D-CX-1 (missing toml), D-CX-2 (config.toml entries), D-CX-4 (claude-string leaks),
# D-CX-5 (empty developer_instructions) and D-CX-10 (boundary fields) are RETIRED
# (K3, v0.5.1): each re-derived "is this projected TOML correct" from its shape via a
# narrow field/regex check. Since the codex per-agent TOML and config.toml are now
# ProjectionRule entries compared byte-wise against their renderer
# (``infrastructure/projection_rules.py``), an incorrect byte IS the drift signal —
# a missing file is `[missing]`, any content difference is `[drift]` — and the
# renderer itself (never patched by a hand-edit) is what a dev-time test proves
# correct. The remaining structural/semantic checks below (D-CX-7/8) stay: none
# of them is expressible as "does this one rendered file's bytes match".
# ---------------------------------------------------------------------------


def dcx7_codex_skill_refs(workspace_root: Path) -> list[DoctorLine]:
    """D-CX-7: generated Codex agents must not reference a missing ``dd-`` member.

    Since 0.4.7 a ``dd-`` token names either a skill directory or one of the three
    personas — both live under the authored ``.agents/`` set, so both resolve here.
    """
    codex_agents = workspace_root / ".codex" / "agents"
    skill_roots = (workspace_root / ".agents" / "skills",)
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
            if not skill.startswith(_CODEX_SKILL_REF_PREFIXES):
                continue
            if skill in personas:
                continue
            if not any((root / skill / "SKILL.md").exists() for root in skill_roots):
                out.append(
                    DoctorLine(
                        DoctorStatus.ERROR,
                        f"codex:agents/{toml_file.name}: missing skill '{skill}' (D-CX-7)",
                    )
                )
    return out


def dcx8_codex_rules_shape(codex_dir: Path) -> list[DoctorLine]:
    """D-CX-8: a Markdown file in ``rules/`` is not Codex Rules (the ``.rules`` bytes are a rule)."""
    return [
        DoctorLine(
            DoctorStatus.EXTRA, f"codex:rules/{md.name}: markdown is not Codex Rules (D-CX-8)"
        )
        for md in sorted((codex_dir / "rules").glob("*.md"))
    ]
