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
import shutil
import subprocess
import tomllib
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from dadaia_workspace.core.harness_registry import L1_ENTRY_HARNESSES
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
    "entities-derivation",
    "foreign-projections",
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
        return []

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

    return out


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

    **STATIC reference integrity only (A22.3).** This check answers "does the cited
    file exist on disk" — nothing here proves a live Codex session actually LOADS that
    file into its effective prompt. That is a different claim (effective prompt
    visibility), answered by ``codex_trust_boundary_info`` below for the hook-fire
    boundary, and by ``features/certification/service.py``'s live ``codex exec`` probe
    (A22.4) for genuine runtime behavior. Do not read an ``[ok]`` here as proof of
    anything beyond on-disk reachability.

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


# The exact codex-cli version for which "projected command hooks fire and block in
# BOTH the interactive TUI and headless `codex exec`" was live-verified (executed-path
# probe, cited in the `ai-harness-codex` skill §9 and the T-043-32 scoping note). A
# stale, unqualified claim carried forward by assumption past a CLI upgrade is exactly
# what FR22c (A22.3) fixes: `codex_trust_boundary_info` asserts this positive fact
# ONLY when the runtime-probed version matches this constant exactly; any other
# observed version — or no observed version at all — degrades honestly instead.
# Update this constant only after a fresh, reviewed live probe (`dadaia certify`'s
# codex-live-probe check, A22.4) reconfirms the fact for a newer version.
_CODEX_HOOKS_LIVE_CERTIFIED_VERSION = "codex-cli 0.144.4"


def _probe_installed_codex_version(timeout: float = 5.0) -> str | None:
    """Best-effort ``codex --version`` runtime probe (A22.3).

    Returns the raw stdout (stripped) of an installed ``codex`` binary reachable on
    ``PATH``, or ``None`` when the binary is absent, fails to launch, exits non-zero,
    or does not answer within *timeout* seconds. Never raises — a probe failure IS the
    "codex absent" observation, not a doctor crash (same discipline as the D-CX-9 hook
    wrapper probe above).
    """
    codex_bin = shutil.which("codex")
    if codex_bin is None:
        return None
    try:
        proc = subprocess.run(  # noqa: S603
            [codex_bin, "--version"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    version = proc.stdout.strip()
    return version or None


def codex_trust_boundary_info(
    *, version_probe: Callable[[], str | None] = _probe_installed_codex_version
) -> list[DoctorLine]:
    """WS-CDX-HYGIENE (A7/A22.3): version-qualified Codex hook-fire trust boundary.

    This reports EFFECTIVE PROMPT VISIBILITY — does an actually-running Codex session
    honor the projected hooks at all — a different claim from
    ``check_codex_rule_corpus_reachable``'s STATIC reference integrity (do the cited
    files merely exist on disk). The reported text is always version-qualified against
    a runtime ``codex --version`` probe (``version_probe``, injectable for tests;
    production wiring always uses ``_probe_installed_codex_version``) and never
    asserts hook-fire behavior for a version this probe did not itself observe: absent
    Codex, and any version other than ``_CODEX_HOOKS_LIVE_CERTIFIED_VERSION``, both
    degrade to an explicit UNVERIFIED line pointing at `dadaia certify`'s live probe
    (A22.4) instead of guessing.
    """
    raw_version = version_probe()
    if raw_version is None:
        return [
            DoctorLine(
                DoctorStatus.INFO,
                "codex:trust-boundary — no installed Codex CLI observed on PATH "
                "('codex --version' unreachable); the interactive-vs-headless "
                "hook-fire boundary is UNVERIFIED for this environment (the git "
                "chokepoints — pre-commit presence advisory + pre-push "
                "security-verdict gate — remain independent defense-in-depth "
                "regardless). (WS-CDX-HYGIENE)",
            )
        ]
    if raw_version == _CODEX_HOOKS_LIVE_CERTIFIED_VERSION:
        return [
            DoctorLine(
                DoctorStatus.INFO,
                f"codex:trust-boundary — installed {raw_version} matches the last "
                "live-certified version: projected command hooks fire and block in "
                "BOTH the interactive TUI and headless `codex exec` (the git "
                "chokepoints remain independent defense-in-depth). (WS-CDX-HYGIENE)",
            )
        ]
    return [
        DoctorLine(
            DoctorStatus.INFO,
            f"codex:trust-boundary — installed {raw_version} has not been "
            "live-certified for hook-fire behavior (last certified: "
            f"{_CODEX_HOOKS_LIVE_CERTIFIED_VERSION}); the interactive-vs-headless "
            "claim is UNVERIFIED for this version — rerun `dadaia certify`'s "
            "codex-live-probe check to reconfirm before relying on it (the git "
            "chokepoints remain independent defense-in-depth regardless). "
            "(WS-CDX-HYGIENE)",
        )
    ]


# A `dadaia_workspace.<dotted.tail>` module reference embedded in a Deterministic
# Behavior's free-text implementation description (e.g. "PreToolUse hook via
# dadaia_workspace.hooks.pre_gate"). ENT-DERIVE-1 (A22.5) resolves every such
# reference against the real source tree, so a behavior whose enforcing module
# silently disappears — the concrete "a hook stops enforcing" drift — is DRIFT, not a
# quiet pass through harness-key-only coverage.
_ENT_DERIVE_MODULE_REF_RE: re.Pattern[str] = re.compile(
    r"\bdadaia_workspace\.([a-zA-Z_][a-zA-Z0-9_.]*)"
)


def _behavior_module_ref_missing(dotted_tail: str, package_root: Path) -> bool:
    """True when ``dadaia_workspace.<dotted_tail>`` resolves to no source file.

    *package_root* is ``public_dir.parent`` — the ``dadaia_workspace`` package
    directory itself in production, or an isolated scratch root in a mutation
    fixture. Neither a bare module file (``hooks/pre_gate.py``) nor a package
    (``hooks/pre_gate/__init__.py``) existing means the reference is broken.
    """
    rel = Path(*dotted_tail.split("."))
    module_file = package_root / rel.with_suffix(".py")
    package_init = package_root / rel / "__init__.py"
    return not module_file.is_file() and not package_init.is_file()


def _behavior_content_drift(behavior: dict[str, Any], package_root: Path) -> list[DoctorLine]:
    """Behavioral-fidelity DRIFT lines for one Deterministic Behavior (A22.5).

    Beyond harness-key coverage (checked by the caller), every
    ``dadaia_workspace.<module>`` reference embedded in any of this behavior's
    implementation descriptions must still resolve to a real source file.
    """
    out: list[DoctorLine] = []
    implementations = behavior.get("implementations", {})
    if not isinstance(implementations, Mapping):
        return out
    for harness_name, impl_text in implementations.items():
        if not isinstance(impl_text, str):
            continue
        for match in _ENT_DERIVE_MODULE_REF_RE.finditer(impl_text):
            dotted_tail = match.group(1)
            if _behavior_module_ref_missing(dotted_tail, package_root):
                out.append(
                    DoctorLine(
                        DoctorStatus.DRIFT,
                        f"entities-derivation: behavior '{behavior.get('id')}' "
                        f"implementation for '{harness_name}' references module "
                        f"'dadaia_workspace.{dotted_tail}' which no longer exists "
                        f"(ENT-DERIVE-1)",
                    )
                )
    return out


def _persona_content_drift(agent_id: str, agents_dir: Path) -> list[DoctorLine]:
    """Behavioral-fidelity DRIFT lines for one correctly-bijected sub-agent (A22.5).

    Filename-stem bijection alone cannot see a stub file at the right path, or an
    internal identity swap (frontmatter ``name:`` diverging from its own filename)
    — both are content-level drift a name-only check is blind to.
    """
    agent_file = agents_dir / f"{agent_id}.md"
    try:
        text = agent_file.read_text(encoding="utf-8")
    except OSError as exc:
        return [
            DoctorLine(
                DoctorStatus.ERROR,
                f"entities-derivation: core sub-agent '{agent_id}' unreadable "
                f"({exc.__class__.__name__}) (ENT-DERIVE-1)",
            )
        ]
    fm = _parse_agent_frontmatter(text)
    declared_name = fm.get("name") if fm else None
    if not declared_name:
        return [
            DoctorLine(
                DoctorStatus.DRIFT,
                f"entities-derivation: core sub-agent '{agent_id}' has no parseable "
                f"frontmatter identity — stub or malformed (ENT-DERIVE-1)",
            )
        ]
    if declared_name != agent_id:
        return [
            DoctorLine(
                DoctorStatus.DRIFT,
                f"entities-derivation: core sub-agent '{agent_id}' frontmatter name "
                f"'{declared_name}' does not match its filename — identity drift "
                f"(ENT-DERIVE-1)",
            )
        ]
    return []


def _entities_registry_shape_problem(raw: Any) -> str | None:
    """The single shape-tolerance seam for ``check_entities_derivation`` (ENT-DERIVE-1).

    Returns a human-readable description of the first shape violation found, or
    ``None`` when ``raw`` is safe for every ``.get``/iteration the caller performs
    downstream. Deliberately does not validate ``rules``/``universal`` — this check
    never reads those sections (only ``schema_version``, ``personas`` and
    ``behaviors[*].implementations``), so nothing beyond that is shape-checked here.
    """
    if not isinstance(raw, dict):
        return f"registry top level is a JSON {type(raw).__name__}, expected an object"

    personas = raw.get("personas", [])
    if not isinstance(personas, list) or not all(isinstance(p, dict) for p in personas):
        return "'personas' is not a list of JSON objects"

    behaviors = raw.get("behaviors", [])
    if not isinstance(behaviors, list) or not all(isinstance(b, dict) for b in behaviors):
        return "'behaviors' is not a list of JSON objects"

    for behavior in behaviors:
        implementations = behavior.get("implementations", {})
        if not isinstance(implementations, Mapping):
            return (
                f"behavior '{behavior.get('id')}' implementations is a "
                f"{type(implementations).__name__}, expected a JSON object"
            )

    return None


def check_entities_derivation(public_dir: Path) -> list[DoctorLine]:
    """ENT-DERIVE-1 (constitution §12.5): the abstract-entity registry grounds the scaffold.

    Independent verifier read — deliberately does NOT share the features-layer loader
    (``features.panel.entities``), so a loader bug cannot vouch for itself. Attests:

    1. ``public/entities/registry.json`` exists, parses, and carries the expected schema.
    2. Persona ↔ core sub-agent bijection: every ``public/agents/*.md`` derives from a
       Persona and every Persona has its derived sub-agent — BY NAME, plus, for every
       correctly-bijected pair, the sub-agent's own frontmatter is parseable and its
       ``name:`` matches its filename (:func:`_persona_content_drift`, A22.5). A stub
       file or a copy-paste identity swap at the right filename is DRIFT even though
       filename-only bijection would pass it.
    3. Every Deterministic Behavior is derived for exactly the entry harnesses, AND
       every ``dadaia_workspace.<module>`` reference embedded in an implementation's
       free-text description still resolves to a real source file
       (:func:`_behavior_content_drift`, A22.5) — a hook (or any other enforcing
       module) that silently disappears while its registry entry is left untouched is
       DRIFT, not a quiet pass through harness-key-only coverage.

    Any violation is DRIFT/ERROR (blocking): a scaffolded core implementation without
    its abstract entity is forbidden, not advisory.
    """
    registry_path = public_dir / "entities" / "registry.json"
    try:
        raw_registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [
            DoctorLine(
                DoctorStatus.ERROR,
                f"entities-derivation: registry unreadable at entities/registry.json "
                f"({exc.__class__.__name__}) (ENT-DERIVE-1)",
            )
        ]

    # Shape-validate the parsed JSON HERE, once, so every line below this seam may
    # assume the shape it needs — no isinstance scattered downstream. A malformed-but
    # -valid-JSON registry (wrong top-level type, non-dict entries, a string standing
    # in for a mapping) must never reach ``.get``/``set(...)`` and raise
    # AttributeError/TypeError, and must never be silently misread into a wrong DRIFT
    # line (e.g. ``set("codex")`` iterating characters as if they were harness ids).
    shape_problem = _entities_registry_shape_problem(raw_registry)
    if shape_problem is not None:
        return [
            DoctorLine(
                DoctorStatus.ERROR,
                f"entities-derivation: {shape_problem} (ENT-DERIVE-1)",
            )
        ]
    registry: dict[str, Any] = raw_registry

    if registry.get("schema_version") != "agentic-entities-v1":
        return [
            DoctorLine(
                DoctorStatus.ERROR,
                "entities-derivation: registry schema_version is not "
                "'agentic-entities-v1' (ENT-DERIVE-1)",
            )
        ]

    out: list[DoctorLine] = []
    personas = {str(p.get("id")) for p in registry.get("personas", [])}
    agents_dir = public_dir / "agents"
    scaffolded = {p.stem for p in agents_dir.glob("*.md")} if agents_dir.exists() else set()
    for orphan in sorted(scaffolded - personas):
        out.append(
            DoctorLine(
                DoctorStatus.DRIFT,
                f"entities-derivation: core sub-agent '{orphan}' has no abstract "
                f"Persona in the registry (ENT-DERIVE-1)",
            )
        )
    for dead in sorted(personas - scaffolded):
        out.append(
            DoctorLine(
                DoctorStatus.DRIFT,
                f"entities-derivation: Persona '{dead}' has no derived core "
                f"sub-agent under public/agents/ (ENT-DERIVE-1)",
            )
        )
    # Behavioral fidelity (A22.5): every correctly-bijected pair also gets its
    # content opened — a name-only pass cannot see a stub file or an identity swap.
    for matched_id in sorted(personas & scaffolded):
        out.extend(_persona_content_drift(matched_id, agents_dir))

    harnesses = set(L1_ENTRY_HARNESSES)
    package_root = public_dir.parent
    for behavior in registry.get("behaviors", []):
        implemented = set(behavior.get("implementations", {}))
        if implemented != harnesses:
            out.append(
                DoctorLine(
                    DoctorStatus.DRIFT,
                    f"entities-derivation: behavior '{behavior.get('id')}' is derived for "
                    f"{sorted(implemented)}, expected every entry harness "
                    f"{sorted(harnesses)} (ENT-DERIVE-1)",
                )
            )
        # Behavioral fidelity (A22.5): harness-key coverage is necessary, never
        # sufficient — also follow every module reference back to a real file.
        out.extend(_behavior_content_drift(behavior, package_root))

    if not out:
        out.append(
            DoctorLine(
                DoctorStatus.OK,
                f"entities-derivation: {len(personas)} Personas ↔ {len(scaffolded)} core "
                f"sub-agents; {len(registry.get('behaviors', []))} Deterministic Behaviors "
                f"derived for all entry harnesses (ENT-DERIVE-1)",
            )
        )
    return out
