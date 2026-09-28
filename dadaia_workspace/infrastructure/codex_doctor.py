"""Codex-drift doctor family — D-CX-1..D-CX-10 and ancillary checks.

These functions are extracted from ``FileSystemPublicAssetManager`` in
``public_assets.py`` to keep that module under 600 lines.  Each function takes
explicit arguments instead of ``self``, so there are no circular imports.
"""

from __future__ import annotations

import json
import os
import re
import tomllib
from pathlib import Path

from dadaia_workspace.core.harness_registry import HARNESS_RECORDS
from dadaia_workspace.core.models.doctor_report import DoctorLine, DoctorStatus
from dadaia_workspace.infrastructure.runtime_transforms.codex_assets import (
    _CODEX_SKILL_REF_PREFIXES,
)
from dadaia_workspace.infrastructure.runtime_transforms.hook_wrappers import (
    hook_wrapper_command,
    hook_wrapper_contents,
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
# correct. The remaining structural/semantic checks below (D-CX-6/7/8/9) stay: none
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
    """D-CX-8: Codex Rules must be Starlark ``.rules``, not Markdown protocols."""
    rules_dir = codex_dir / "rules"
    out: list[DoctorLine] = []
    if not rules_dir.exists():
        out.append(DoctorLine(DoctorStatus.MISSING, "codex:rules/ (D-CX-8)"))
        return out
    if not any(rules_dir.glob("*.rules")):
        out.append(DoctorLine(DoctorStatus.MISSING, "codex:rules/*.rules (D-CX-8)"))
    for rules_file in sorted(rules_dir.glob("*.rules")):
        try:
            text = rules_file.read_text(encoding="utf-8")
        except OSError:
            continue
        if "command_allowed(" in text:
            out.append(
                DoctorLine(
                    DoctorStatus.ERROR,
                    f"codex:rules/{rules_file.name}: undocumented command_allowed policy (D-CX-8)",
                )
            )
        if "prefix_rule(" not in text:
            out.append(
                DoctorLine(
                    DoctorStatus.ERROR,
                    f"codex:rules/{rules_file.name}: missing prefix_rule declarations (D-CX-8)",
                )
            )
    for md_file in sorted(rules_dir.glob("*.md")):
        out.append(
            DoctorLine(
                DoctorStatus.EXTRA,
                f"codex:rules/{md_file.name}: markdown is not Codex Rules (D-CX-8)",
            )
        )
    return out


def dcx9_codex_hook_shape(workspace_root: Path) -> list[DoctorLine]:
    """D-CX-9: generated Codex hooks must invoke executable wrapper commands."""
    hooks_path = workspace_root / ".codex" / "hooks.json"
    out: list[DoctorLine] = []
    try:
        hooks = json.loads(hooks_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return [DoctorLine(DoctorStatus.ERROR, "codex:hooks.json missing or invalid (D-CX-9)")]

    wrappers = hook_wrapper_contents(HARNESS_RECORDS["codex"])
    expected = {hook_wrapper_command(name) for name in wrappers}
    commands = set(_codex_hook_commands(hooks))
    missing = expected - commands
    for command in sorted(missing):
        out.append(DoctorLine(DoctorStatus.MISSING, f"codex:hooks.json command {command} (D-CX-9)"))

    stale = commands - expected
    for command in sorted(stale):
        out.append(
            DoctorLine(
                DoctorStatus.ERROR,
                f"codex:hooks.json command must use .dadaia/hooks wrapper, got "
                f"{command!r} (D-CX-9)",
            )
        )

    for command in sorted(commands & expected):
        wrapper = workspace_root / command
        if not wrapper.is_file():
            out.append(DoctorLine(DoctorStatus.MISSING, f"codex hook wrapper {command} (D-CX-9)"))
            continue
        if not os.access(wrapper, os.X_OK):
            out.append(
                DoctorLine(
                    DoctorStatus.ERROR, f"codex hook wrapper not executable {command} (D-CX-9)"
                )
            )
    return out


def _codex_hook_commands(value: object) -> list[str]:
    """Collect command strings from a Codex hooks.json structure."""
    commands: list[str] = []
    if isinstance(value, dict):
        command = value.get("command")
        if isinstance(command, str):
            commands.append(command)
        for child in value.values():
            commands.extend(_codex_hook_commands(child))
    elif isinstance(value, list):
        for item in value:
            commands.extend(_codex_hook_commands(item))
    return commands
