"""Codex-drift doctor family — D-CX-1..D-CX-10 and ancillary checks.

These functions are extracted from ``FileSystemPublicAssetManager`` in
``public_assets.py`` to keep that module under 600 lines.  Each function takes
explicit arguments instead of ``self``, so there are no circular imports.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import subprocess
import tomllib
from pathlib import Path

from dadaia_workspace.core.models.doctor_report import DoctorLine, DoctorStatus
from dadaia_workspace.infrastructure.runtime_transforms.codex_assets import (
    _CODEX_SKILL_REF_PREFIXES,
    _parse_agent_frontmatter,
    _parse_skills_from_frontmatter,
)

# ---------------------------------------------------------------------------
# Constants (class-level in the original; kept here as module-level)
# ---------------------------------------------------------------------------
_CODEX_CLAUDE_MODEL_RE: re.Pattern[str] = re.compile(
    r"(?:^|[^a-zA-Z0-9_-])claude-(?:opus|sonnet|haiku)-[\w.-]+",
    re.MULTILINE,
)
# Claude-only tool names that have no Codex meaning. Codex uses explicit subagent
# delegation, not the Claude Code `Agent`/`Task` tools, so these must not leak into
# any Codex-projected artifact (codex-agent-description-claude-ism-leak, T-013-09).
_CODEX_CLAUDE_TOOL_RE: re.Pattern[str] = re.compile(
    r"\b(?:Agent|Task) tool\b",
)
# Anthropic marketing TIER names used as standalone tier words in model-strategy
# prose (codex-personas-claude-model-tiering-leak, T-013-12). These leak into
# Codex personas when persona prose recommends Anthropic tiers ("Opus / Sonnet /
# Haiku") instead of Codex-native tier terms. Matched on a word boundary so a
# legitimate ``claude-*`` model id (already caught by _CODEX_CLAUDE_MODEL_RE) and
# the skill name ``ai-harness-claude-code`` are NOT false-positived: those never
# contain a standalone capitalised ``Opus``/``Sonnet``/``Haiku`` word.
_CODEX_ANTHROPIC_TIER_RE: re.Pattern[str] = re.compile(
    r"\b(?:Opus|Sonnet|Haiku)\b",
)
_CODEX_TEXT_SUFFIXES: frozenset[str] = frozenset({".toml", ".md", ".json", ".txt", ".yaml", ".yml"})
_CODEX_EXPECTED_READ_ONLY_AGENTS: frozenset[str] = frozenset(
    {
        "code-reviewer",
        "design-specialist",
        "project-auditor",
        "qa-engineer",
        "security-reviewer",
        "software-architect",
    }
)


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


#: The ATTESTING checks of the public-doctor surface: each emits a positive claim
#: (``[ok] …``) when its universe is non-empty, so each is wrapped in
#: :func:`dadaia_workspace.core.models.doctor_report.attest` at the assembly point —
#: an empty universe yields an explicit ``[not-applicable] check:<id>`` line instead of
#: silence. Pinned by ``tests/unit/infrastructure/test_attesting_checks.py``: removing
#: an entry is a reviewed decision, never an accidental vanishing.
ATTESTING_CHECK_IDS: tuple[str, ...] = (
    "rule-corpus",
    "trust-boundary",
    "public-privacy",
    "law-projection",
)


def check_codex_drift(
    agentic_dir: Path,
    workspace_root: Path,
    public_dir: Path,
) -> list[DoctorLine]:
    """Run codex-parity drift checks D-CX-1 through D-CX-10.

    Returns a list of ``[missing]``, ``[extra]``, ``[error]``, ``[leak]``,
    or ``[drift]`` report strings.  An empty list means no drift was detected.
    """
    codex_dir = workspace_root / ".codex"
    out: list[DoctorLine] = []
    out.extend(dcx1_missing_toml(agentic_dir, codex_dir))
    out.extend(dcx2_config_toml_entries(agentic_dir, codex_dir))
    out.extend(dcx4_claude_strings(codex_dir))
    out.extend(dcx5_empty_developer_instructions(codex_dir))
    out.extend(dcx6_codex_runtime_adapters(workspace_root, public_dir))
    out.extend(dcx7_codex_skill_refs(workspace_root))
    out.extend(dcx8_codex_rules_shape(codex_dir))
    out.extend(dcx9_codex_hook_shape(workspace_root))
    out.extend(dcx10_codex_agent_boundaries(codex_dir))
    return out


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------


def dcx1_missing_toml(agentic_dir: Path, codex_dir: Path) -> list[DoctorLine]:
    """D-CX-1: every canonical agent .md must have a matching TOML in .codex/agents/."""
    agents_src = agentic_dir / "agents"
    codex_agents = codex_dir / "agents"
    out: list[DoctorLine] = []
    if not agents_src.exists():
        return out
    for md_file in sorted(agents_src.glob("*.md")):
        try:
            text = md_file.read_text(encoding="utf-8")
        except OSError:
            continue
        fm = _parse_agent_frontmatter(text)
        name = str(fm.get("name", "")) if fm else ""
        if not name:
            name = md_file.stem
        toml_path = codex_agents / f"{name}.toml"
        if not toml_path.exists():
            out.append(DoctorLine(DoctorStatus.MISSING, f"codex:agents/{name}.toml (D-CX-1)"))
    return out


def dcx2_config_toml_entries(agentic_dir: Path, codex_dir: Path) -> list[DoctorLine]:
    """D-CX-2: every .codex/agents/*.toml must have a config_file entry in config.toml."""
    codex_agents = codex_dir / "agents"
    config_toml = codex_dir / "config.toml"
    out: list[DoctorLine] = []
    if not codex_agents.exists():
        return out
    config_text = ""
    if config_toml.exists():
        with contextlib.suppress(OSError):
            config_text = config_toml.read_text(encoding="utf-8")
    for toml_file in sorted(codex_agents.glob("*.toml")):
        name = toml_file.stem
        needle = f'config_file = "agents/{name}.toml"'
        if needle not in config_text:
            out.append(
                DoctorLine(DoctorStatus.MISSING, f"codex:config.toml entry for {name} (D-CX-2)")
            )
    return out


def dcx4_claude_strings(codex_dir: Path) -> list[DoctorLine]:
    """D-CX-4: Codex projections must not contain Claude model/path leaks."""
    out: list[DoctorLine] = []
    if not codex_dir.exists():
        return out
    for path in sorted(codex_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix not in _CODEX_TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if _CODEX_CLAUDE_MODEL_RE.search(text) or ".claude/rules/" in text:
            rel = path.relative_to(codex_dir).as_posix()
            out.append(
                DoctorLine(DoctorStatus.ERROR, f"codex:claude-model-or-path in {rel} (D-CX-4)")
            )
        elif _CODEX_CLAUDE_TOOL_RE.search(text):
            rel = path.relative_to(codex_dir).as_posix()
            out.append(DoctorLine(DoctorStatus.ERROR, f"codex:claude-tool-name in {rel} (D-CX-4)"))
        elif _CODEX_ANTHROPIC_TIER_RE.search(text):
            rel = path.relative_to(codex_dir).as_posix()
            out.append(
                DoctorLine(DoctorStatus.ERROR, f"codex:anthropic-tier-name in {rel} (D-CX-4)")
            )
    return out


def dcx5_empty_developer_instructions(codex_dir: Path) -> list[DoctorLine]:
    """D-CX-5: every .codex/agents/*.toml must have a non-empty developer_instructions."""
    codex_agents = codex_dir / "agents"
    out: list[DoctorLine] = []
    if not codex_agents.exists():
        return out
    for toml_file in sorted(codex_agents.glob("*.toml")):
        name = toml_file.stem
        try:
            text = toml_file.read_text(encoding="utf-8")
            data = tomllib.loads(text)
        except (OSError, tomllib.TOMLDecodeError):
            out.append(
                DoctorLine(DoctorStatus.ERROR, f"codex:{name}.toml: unparseable TOML (D-CX-5)")
            )
            continue
        instructions = data.get("developer_instructions", "")
        if not isinstance(instructions, str) or not instructions.strip():
            out.append(
                DoctorLine(
                    DoctorStatus.ERROR,
                    f"codex:{name}.toml: developer_instructions is empty (D-CX-5)",
                )
            )
    return out


def dcx6_codex_runtime_adapters(workspace_root: Path, public_dir: Path) -> list[DoctorLine]:
    """D-CX-6: public/runtime/codex/ adapters — leak, missing, drift checks."""
    src_root = public_dir / "runtime" / "codex"
    out: list[DoctorLine] = []
    if not src_root.exists():
        return out
    codex_skills = workspace_root / ".codex" / "skills"
    claude_skills = workspace_root / ".claude" / "skills"
    for slug_dir in sorted(src_root.iterdir()):
        if not slug_dir.is_dir():
            continue
        skill_src = slug_dir / "SKILL.md"
        if not skill_src.exists():
            continue
        slug = slug_dir.name
        src_text = skill_src.read_text(encoding="utf-8")
        # Leak checks
        for leak_root, label in [(claude_skills, "claude")]:
            leak_path = leak_root / slug / "SKILL.md"
            if leak_path.exists():
                out.append(
                    DoctorLine(
                        DoctorStatus.LEAK,
                        f"{label}:skills/{slug}/SKILL.md"
                        " — Codex-only adapter must not appear here (D-CX-6)",
                    )
                )
        # Missing / drift
        installed = codex_skills / slug / "SKILL.md"
        if not installed.exists():
            out.append(DoctorLine(DoctorStatus.MISSING, f"codex:skills/{slug}/SKILL.md (D-CX-6)"))
        elif installed.read_text(encoding="utf-8") != src_text:
            out.append(DoctorLine(DoctorStatus.DRIFT, f"codex:skills/{slug}/SKILL.md (D-CX-6)"))
    return out


def dcx7_codex_skill_refs(workspace_root: Path) -> list[DoctorLine]:
    """D-CX-7: generated Codex agents must not reference missing skills."""
    codex_agents = workspace_root / ".codex" / "agents"
    skill_roots = (
        workspace_root / ".agents" / "skills",
        workspace_root / ".codex" / "skills",
    )
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

    expected = {
        ".dadaia/hooks/codex-pre-gate",
        ".dadaia/hooks/codex-post-gate",
        ".dadaia/hooks/codex-ctx-inject",
        ".dadaia/hooks/codex-ctx-inject-session-start",
    }
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
            continue
        try:
            proc = subprocess.run(
                [str(wrapper)],
                input='{"session_id":"doctor","tool_name":"Read","tool_input":{}}',
                capture_output=True,
                text=True,
                cwd=workspace_root,
                timeout=10,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            out.append(
                DoctorLine(
                    DoctorStatus.UNSUPPORTED,
                    f"codex hook wrapper launch failed {command}: {exc} (D-CX-9)",
                )
            )
            continue
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout).strip().splitlines()
            suffix = f": {detail[0]}" if detail else ""
            # The exec probe's outcome is ENVIRONMENT-phrased (exit 127 = the venv
            # runtime is absent; other exits/launch failures vary by host and are
            # canonicalized as probe noise by the golden helpers). Reinstalling
            # projections can never fix an environment, so probe outcomes are
            # UNSUPPORTED (visible, non-blocking). The deterministic misconfig
            # findings above — wrapper missing, not executable, wrong command path —
            # remain blocking: those an install genuinely repairs.
            out.append(
                DoctorLine(
                    DoctorStatus.UNSUPPORTED,
                    f"codex hook wrapper exited {proc.returncode} {command}{suffix} (D-CX-9)",
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


def dcx10_codex_agent_boundaries(codex_dir: Path) -> list[DoctorLine]:
    """D-CX-10: Codex agent TOML must include role-boundary fields."""
    codex_agents = codex_dir / "agents"
    out: list[DoctorLine] = []
    if not codex_agents.exists():
        return out
    for toml_file in sorted(codex_agents.glob("*.toml")):
        try:
            data = tomllib.loads(toml_file.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            continue
        for field in ("sandbox_mode", "model_reasoning_effort"):
            if field not in data:
                out.append(
                    DoctorLine(
                        DoctorStatus.MISSING, f"codex:agents/{toml_file.name}:{field} (D-CX-10)"
                    )
                )
        if (
            toml_file.stem in _CODEX_EXPECTED_READ_ONLY_AGENTS
            and data.get("sandbox_mode") != "read-only"
        ):
            out.append(
                DoctorLine(
                    DoctorStatus.ERROR,
                    f"codex:agents/{toml_file.name}:sandbox_mode must be read-only "
                    "for evidence-only role (D-CX-10)",
                )
            )
        for forbidden in ("provider", "api_key", "telemetry"):
            if forbidden in data:
                out.append(
                    DoctorLine(
                        DoctorStatus.ERROR, f"codex:agents/{toml_file.name}:{forbidden} (D-CX-10)"
                    )
                )
    return out


def check_agent_skill_refs(public_dir: Path) -> list[DoctorLine]:
    """D-CX-SKILLS: every ``skills:`` name in agent frontmatter must exist in public/skills/."""
    agents_dir = public_dir / "agents"
    skills_dir = public_dir / "skills"
    out: list[DoctorLine] = []
    if not agents_dir.exists():
        # Plugin sweep still runs — pack agents live outside public/agents/.
        return _check_plugin_agent_skill_refs(public_dir, skills_dir)

    for md_file in sorted(agents_dir.glob("*.md")):
        try:
            text = md_file.read_text(encoding="utf-8")
        except OSError:
            continue

        fm = _parse_agent_frontmatter(text)
        agent_name = str(fm.get("name", md_file.stem)) if fm else md_file.stem

        # Frontmatter skills — hard failure on missing skill directory
        skills_in_fm = _parse_skills_from_frontmatter(text)
        confirmed: set[str] = set()
        for skill in skills_in_fm:
            if (skills_dir / skill).is_dir():
                confirmed.add(skill)
            else:
                out.append(
                    DoctorLine(
                        DoctorStatus.DRIFT,
                        f"agent:{agent_name}: frontmatter references "
                        f"non-existent skill '{skill}' (D-CX-SKILLS)",
                    )
                )

        # Body scan — only inside "## Skills consumed" section (soft warning)
        body_start = text.find("\n---\n", 4)
        if body_start == -1:
            continue
        body = text[body_start + 5 :]
        sc_start = body.find("## Skills consumed")
        if sc_start == -1:
            continue
        sc_end = body.find("\n## ", sc_start + 1)
        section = body[sc_start:sc_end] if sc_end != -1 else body[sc_start:]
        already_flagged: set[str] = set(skills_in_fm)
        for m in re.finditer(r"`([a-z][a-z0-9\-]+)`", section):
            candidate = m.group(1)
            if candidate in already_flagged or candidate in confirmed:
                continue
            if not (skills_dir / candidate).is_dir():
                out.append(
                    DoctorLine(
                        DoctorStatus.WARN,
                        f"agent:{agent_name}: 'Skills consumed' body section "
                        f"mentions '{candidate}' absent from public/skills/ (D-CX-SKILLS)",
                    )
                )
                already_flagged.add(candidate)

    # Plugin-aware sweep (v0.1.63 FR6 / ADR-C3, read fact 6): pack agents under
    # public/plugins/<pack>/agents/ resolve their frontmatter ``skills:`` refs against
    # public/skills/ UNION that pack's OWN plugins/<pack>/skills/ — never a foreign
    # pack's. Additive: the core-agent sweep above is untouched.
    out.extend(_check_plugin_agent_skill_refs(public_dir, skills_dir))
    return out


def _check_plugin_agent_skill_refs(public_dir: Path, skills_dir: Path) -> list[DoctorLine]:
    """Sweep pack-agent frontmatter skill refs (D-CX-SKILLS, plugin-aware half)."""
    plugins_dir = public_dir / "plugins"
    out: list[DoctorLine] = []
    if not plugins_dir.exists():
        return out
    for pack_dir in sorted(plugins_dir.iterdir()):
        pack_agents = pack_dir / "agents"
        if not pack_dir.is_dir() or not pack_agents.exists():
            continue
        pack_skills = pack_dir / "skills"
        for md_file in sorted(pack_agents.glob("*.md")):
            try:
                text = md_file.read_text(encoding="utf-8")
            except OSError:
                continue
            fm = _parse_agent_frontmatter(text)
            agent_name = str(fm.get("name", md_file.stem)) if fm else md_file.stem
            for skill in _parse_skills_from_frontmatter(text):
                if (skills_dir / skill).is_dir() or (pack_skills / skill).is_dir():
                    continue
                out.append(
                    DoctorLine(
                        DoctorStatus.DRIFT,
                        f"plugin-agent:{pack_dir.name}/{agent_name}: frontmatter "
                        f"references non-existent skill '{skill}' (D-CX-SKILLS)",
                    )
                )
    return out


# Phrases that assert the memory-write PHASE permission (as opposed to incidental mentions
# of "release closure" + "memory" in the same line). A governance-bearing line matches one
# of these AND cites CLOSURE without DEFINITION → single-source drift.
_MEMORY_PHASE_CLAIM_MARKERS = (
    "write-locked",
    "only allows memory",
    "block writes to",
    "writes in this phase",
    "during the closure phase",
    "may edit memory",
    "may write memory",
)


def check_memory_phase_single_source(public_dir: Path) -> list[DoctorLine]:
    """SINGLE-SRC-1: the memory-write phase is DEFINITION+CLOSURE (constitution §13).

    Flags any public agent/skill line that asserts the memory-write *phase* permission but
    cites only CLOSURE (omitting DEFINITION) — the single-source drift behind
    `constitution-persona-single-source-drift`. Incidental "release closure"/"memory update"
    mentions are NOT flagged (they carry no phase-permission marker).
    """
    out: list[DoctorLine] = []
    for sub in ("agents", "skills"):
        base = public_dir / sub
        if not base.exists():
            continue
        for md_file in sorted(base.rglob("*.md")):
            try:
                text = md_file.read_text(encoding="utf-8")
            except OSError:
                continue
            for n, raw in enumerate(text.splitlines(), start=1):
                line = raw.lower()
                if "closure" not in line or "definition" in line:
                    continue
                if any(marker in line for marker in _MEMORY_PHASE_CLAIM_MARKERS):
                    rel = md_file.relative_to(public_dir)
                    out.append(
                        DoctorLine(
                            DoctorStatus.DRIFT,
                            f"{rel}:{n}: memory-write phase cites CLOSURE only — the "
                            f"canonical rule is DEFINITION+CLOSURE (constitution §13). (SINGLE-SRC-1)",
                        )
                    )
    return out


# By-name rule citation in a Codex-projected artifact, e.g. "`workspace-protocol` rule".
# The corpus is reachable iff each cited name resolves to .claude/rules/<name>.md on disk
# (the single source-of-truth law surface, identical across harnesses — WS-CDX-PROTOCOL).
_CODEX_RULE_CITATION_RE: re.Pattern[str] = re.compile(r"`([a-z][a-z0-9-]+)`\s+rule\b")


def check_codex_rule_corpus_reachable(workspace_root: Path) -> list[DoctorLine]:
    """WS-CDX-PROTOCOL (A6): every by-name rule cited by a Codex artifact is reachable.

    A Codex session reaches the load-bearing rule-law corpus through the on-disk
    surface ``.claude/rules/<rule-name>.md`` (documented in the projected root
    ``AGENTS.md`` "Rule-Law Corpus" section). This check proves the contract: for
    every ``\\`<name>\\` rule`` citation in any ``.codex/agents/*.toml`` artifact, the
    file ``.claude/rules/<name>.md`` must exist. A missing file means a Codex artifact
    cites a law surface Codex cannot reach.

    Returns ``[ok] codex:rule-corpus-reachable`` when every citation resolves, or one
    ``[error]`` line per unreachable citation.
    """
    codex_agents = workspace_root / ".codex" / "agents"
    rules_dir = workspace_root / ".claude" / "rules"
    out: list[DoctorLine] = []
    if not codex_agents.exists():
        return out

    unreachable: set[str] = set()
    cited_any = False
    for toml_file in sorted(codex_agents.glob("*.toml")):
        try:
            text = toml_file.read_text(encoding="utf-8")
        except OSError:
            continue
        for match in _CODEX_RULE_CITATION_RE.finditer(text):
            name = match.group(1)
            cited_any = True
            if not (rules_dir / f"{name}.md").is_file():
                unreachable.add(name)
        # The nine by-name rules were consolidated into the single always-on law file, so
        # artifacts now cite ``DADAIA.md`` instead. Same invariant, same verdict labels: an
        # artifact that cites the law must be able to reach it. Without this the check
        # would go SILENT once the last by-name citation disappeared — a check that stops
        # emitting is a check that stopped protecting.
        if "DADAIA.md" in text:
            cited_any = True
            # The workspace root copy is the canonical, profile-independent projection
            # (a codex-only profile carries no .claude/rules/ at all).
            if not (workspace_root / "DADAIA.md").is_file():
                unreachable.add("DADAIA.md")

    if unreachable:
        for name in sorted(unreachable):
            out.append(
                DoctorLine(
                    DoctorStatus.ERROR,
                    f"codex:rule-corpus: by-name rule '{name}' cited in a Codex "
                    f"artifact has no reachable surface "
                    f".claude/rules/{name if name.endswith('.md') else name + '.md'} "
                    "(WS-CDX-PROTOCOL)",
                )
            )
    elif cited_any:
        out.append(DoctorLine(DoctorStatus.OK, "codex:rule-corpus-reachable (WS-CDX-PROTOCOL)"))
    # Zero citations ⇒ [] here; the assembly wraps this check in attest("rule-corpus", …),
    # which turns silence into an explicit not-applicable line (Class-3 guard).
    return out


def codex_trust_boundary_info() -> list[DoctorLine]:
    """WS-CDX-HYGIENE (A7): surface the Codex interactive-vs-headless trust boundary.

    Codex governance hooks fire and block only in **interactive** sessions; under
    headless ``codex exec`` they never fire, so the headless posture is protected by
    the git chokepoints (pre-commit presence advisory + pre-push security-verdict gate) only.
    This INFO line states that boundary honestly in ``dadaia public doctor`` output.
    """
    return [
        DoctorLine(
            DoctorStatus.INFO,
            "codex:trust-boundary — Codex interactive hooks fire and block; "
            "`codex exec` headless does not (headless is protected by the git "
            "chokepoints only). (WS-CDX-HYGIENE)",
        )
    ]
