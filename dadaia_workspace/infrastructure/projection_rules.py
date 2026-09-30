"""``projection_rules(plan)`` — the ONE table every projection family renders from.

0.4.7 FR2: the harness seam is a *record*, not a class. Each
:class:`~dadaia_workspace.core.harness_registry.HarnessRecord` names how its harness
consumes the authored persona set (``agent_transcode``) and which format its hook
registration serializes into (``hooks``); this module holds one builder per enum value
and dispatches on it. :func:`projection_rules` assembles the harness-independent rules
(the guardrail pair, the law file, the shared skills tree, the ``.dadaia/**``
``AGENTS.md`` family) alongside each active record's own — one call builds the exact
same table ``install()`` writes and ``doctor()`` compares. :func:`harness_checks` holds
the residue a byte-compare cannot express (a structural/semantic claim, e.g. "does this
TOML's cited skill exist"), keyed by the same ``hooks`` value.

There is no per-harness branch here and no harness name in this file: a harness fact
lives in ``core/harness_registry.py`` or nowhere.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from pathlib import Path

from dadaia_workspace.core.exceptions import PublicAssetError
from dadaia_workspace.core.harness_registry import (
    HARNESS_RECORDS,
    AgentTranscode,
    HarnessRecord,
    HookFormat,
)
from dadaia_workspace.core.model_registry import ResolvedAgentModel
from dadaia_workspace.core.models.doctor_report import DoctorLine, DoctorStatus
from dadaia_workspace.infrastructure.agent_transcodes import AGENT_RULE_BUILDERS, no_rules
from dadaia_workspace.infrastructure.codex_doctor import (
    dcx7_codex_skill_refs,
    dcx8_codex_rules_shape,
)
from dadaia_workspace.infrastructure.install_helpers import (
    render_claude_agent,
    resolve_codex_agent_model,
)
from dadaia_workspace.infrastructure.install_plan import InstallPlan
from dadaia_workspace.infrastructure.projection import (
    ProjectionRule,
    bytes_rule,
    tree_bytes_rules,
)
from dadaia_workspace.infrastructure.public_assets_common import iter_public_files
from dadaia_workspace.infrastructure.runtime_config import (
    claude_hooks,
    foreign_claude_hook_commands,
    kimi_code_home,
    kimi_hooks_block,
    merge_claude_settings,
    upsert_kimi_hooks_block,
)
from dadaia_workspace.infrastructure.runtime_transforms.codex_assets import _parse_agent_frontmatter
from dadaia_workspace.infrastructure.runtime_transforms.hook_wrappers import (
    hook_documents,
    hook_wrapper_contents,
)

# ---------------------------------------------------------------------------
# Harness-independent rules: guardrail pair (root), law, dadaia-family AGENTS.md
# ---------------------------------------------------------------------------


def _guardrail_pair_rules(plan: InstallPlan) -> tuple[ProjectionRule, ...]:
    """The root ``AGENTS.md`` map — one source (``data/AGENTS.md``), one destination;
    ``public install`` never writes under ``repos/`` (repo law is ``specs init``'s)."""
    src = plan.agentic_dir / "data" / "AGENTS.md"
    if not src.is_file():
        return ()
    return (
        bytes_rule("root:AGENTS.md", "agents", plan.workspace_root / "AGENTS.md", src.read_bytes()),
    )


#: (staged source name, destination relpath, doctor label) for the runtime-zone
#: ``AGENTS.md`` family (``.dadaia/**``, ``worktrees/``) — unconditional, harness-independent.
_DADAIA_FAMILY_AGENTS_MD: tuple[tuple[str, str, str], ...] = (
    ("handoff-AGENTS.md", ".dadaia/handoff/AGENTS.md", "handoff:AGENTS.md"),
    ("dadaia-AGENTS.md", ".dadaia/AGENTS.md", "dadaia:AGENTS.md"),
    ("tmp-AGENTS.md", ".dadaia/tmp/AGENTS.md", "dadaia:tmp/AGENTS.md"),
    ("states-AGENTS.md", ".dadaia/states/AGENTS.md", "dadaia:states/AGENTS.md"),
    ("worktrees-AGENTS.md", "worktrees/AGENTS.md", "worktrees:AGENTS.md"),
)


def _dadaia_family_agents_md_rules(plan: InstallPlan) -> tuple[ProjectionRule, ...]:
    rules: list[ProjectionRule] = []
    for source_name, rel_dst, label in _DADAIA_FAMILY_AGENTS_MD:
        src = plan.agentic_dir / "data" / source_name
        if src.is_file():
            rules.append(
                bytes_rule(label, "agents", plan.workspace_root / rel_dst, src.read_bytes())
            )
    return tuple(rules)


def _skills_tree_rules(plan: InstallPlan) -> tuple[ProjectionRule, ...]:
    """The shared skills root (``.agents/skills/``) — the ONE authored copy. Codex and
    Kimi Code read it natively; Claude Code reaches it through the per-skill symlinks
    ``ClaudeHarness`` projects into ``.claude/skills/``.
    """
    return tree_bytes_rules(
        plan.agentic_dir / "skills",
        plan.workspace_root / ".agents" / "skills",
        harness="agents",
        label_prefix="agents:skills/",
    )


def _agents_agent_rules(
    agentic_dir: Path, workspace_root: Path, resolved_models: Mapping[str, ResolvedAgentModel]
) -> tuple[ProjectionRule, ...]:
    """``.agents/agents/`` — the ONE rendered persona set every harness view points at.

    ``render_claude_agent`` stays the single render seam (model, effort and permission
    fields appended to the staged body); what changed is where its output lands.
    """
    src_dir = agentic_dir / "agents"
    dst_dir = workspace_root / ".agents" / "agents"
    rules: list[ProjectionRule] = []
    for src in iter_public_files(src_dir):
        rel = src.relative_to(src_dir)
        label = f"agents:agents/{rel.as_posix()}"
        if src.suffix != ".md":
            rules.append(bytes_rule(label, "agents", dst_dir / rel, src.read_bytes()))
            continue

        def _render(
            _current: bytes | None,
            _src: Path = src,
            _resolved: ResolvedAgentModel | None = resolved_models.get(src.stem),
        ) -> bytes:
            text = _src.read_text(encoding="utf-8")
            if _resolved is not None:
                return render_claude_agent(text, _resolved).encode("utf-8")
            # An authored model renders verbatim; a persona with none is refused.
            resolve_codex_agent_model(_src.stem, _parse_agent_frontmatter(text).get("model"), None)
            return _src.read_bytes()

        rules.append(
            ProjectionRule(label=label, harness="agents", dst=dst_dir / rel, render=_render)
        )
    return tuple(rules)


# ---------------------------------------------------------------------------
# hooks builders — one per enum value, plus the checks a byte-compare cannot express
# ---------------------------------------------------------------------------


def _settings_merge_rules(record: HarnessRecord, plan: InstallPlan) -> tuple[ProjectionRule, ...]:
    """``claude-settings``: an ``owned-slice`` compare — the render MERGES the operator's
    file, folding in only the dadaia hook wiring and leaving every other top-level key and
    non-dadaia hook entry untouched. Still one algorithm, because the merge is a fixed
    point on already-canonical content."""
    workspace_root = plan.workspace_root
    dst = workspace_root / str(record.directory) / "settings.json"

    def _render(current: bytes | None) -> bytes:
        existing: dict[str, object] | None = None
        if current is not None:
            try:
                loaded = json.loads(current.decode("utf-8"))
            except (json.JSONDecodeError, ValueError, UnicodeDecodeError) as exc:
                raise PublicAssetError(
                    f"{dst} is not readable JSON ({exc}). It carries operator settings, so "
                    "dadaia will not overwrite it. Fix or move the file, then re-run install."
                ) from None
            existing = loaded if isinstance(loaded, dict) else None
        merged = merge_claude_settings(existing, workspace_root)
        return (json.dumps(merged, indent=2, sort_keys=True) + "\n").encode("utf-8")

    return (
        ProjectionRule(
            label=f"{record.name}:settings.json",
            harness=record.name,
            dst=dst,
            render=_render,
            compare="owned-slice",
        ),
        *_wrapper_rules(record, workspace_root),
    )


def _settings_merge_checks(record: HarnessRecord, workspace_root: Path) -> list[DoctorLine]:
    """The one check a byte-compare cannot express: a foreign hook command is preserved
    (never drift — the file is the operator's) but never silenced."""
    dst = workspace_root / str(record.directory) / "settings.json"
    if not dst.is_file():
        return []
    try:
        loaded = json.loads(dst.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(loaded, dict):
        return []
    foreign = foreign_claude_hook_commands(loaded, claude_hooks())
    if not foreign:
        return []
    return [
        DoctorLine(
            DoctorStatus.WARN,
            f"{record.name}:settings.json: non-dadaia hook command(s) in gated event(s) — "
            + ", ".join(foreign),
        )
    ]


def _wrapper_rules(record: HarnessRecord, workspace_root: Path) -> tuple[ProjectionRule, ...]:
    """The on-disk executables a record's hook format needs — the generalisation of the
    former codex-only wrapper rule.

    A harness that registers a command string gets ONE executable path per behaviour
    lane, with no arguments and no env-prefix syntax in its registration file. Which
    lanes exist, and whether the wrapper translates the gate's answer into the harness's
    shape, is the format's row in ``HOOK_DIALECTS`` — never a branch here.
    """
    return tuple(
        bytes_rule(
            f"dadaia:hooks/{name}",
            record.name,
            workspace_root / ".dadaia" / "hooks" / name,
            content.encode("utf-8"),
            mode=0o755,
        )
        for name, content in hook_wrapper_contents(record).items()
    )


def _hook_files_rules(record: HarnessRecord, plan: InstallPlan) -> tuple[ProjectionRule, ...]:
    """A format whose whole registration is one or more JSON files citing wrappers."""
    workspace_root = plan.workspace_root
    directory = workspace_root / str(record.directory)
    rules = [
        bytes_rule(
            f"{record.name}:{relpath}",
            record.name,
            directory / relpath,
            (json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        )
        for relpath, document in hook_documents(record).items()
    ]
    rules.extend(_wrapper_rules(record, workspace_root))
    return tuple(rules)


def _codex_checks(record: HarnessRecord, workspace_root: Path) -> list[DoctorLine]:
    """D-CX-7/8 — gated on the harness being in profile."""
    codex_dir = workspace_root / str(record.directory)
    return [*dcx7_codex_skill_refs(workspace_root), *dcx8_codex_rules_shape(codex_dir)]


def _user_home_hook_rules(record: HarnessRecord, plan: InstallPlan) -> tuple[ProjectionRule, ...]:
    """``kimi-hooks``: no project-level config file — hook registration is a managed block
    folded into the user-level ``$KIMI_CODE_HOME/config.toml``, the same fixed-point
    algorithm as every other rule."""
    home = kimi_code_home()
    rules = [
        bytes_rule(
            f"{record.name}:hooks/{name}",
            record.name,
            home / "hooks" / name,
            content.encode("utf-8"),
            mode=0o755,
        )
        for name, content in hook_wrapper_contents(record).items()
    ]

    def _render(current: bytes | None) -> bytes:
        existing = current.decode("utf-8") if current is not None else ""
        return upsert_kimi_hooks_block(existing, kimi_hooks_block(home)).encode("utf-8")

    rules.append(
        ProjectionRule(
            label=f"{record.name}:config.toml managed hooks block",
            harness=record.name,
            dst=home / "config.toml",
            render=_render,
            compare="managed-block",
        )
    )
    return tuple(rules)


#: One builder per :class:`HookFormat` value — total, so no harness can fall through a
#: missing key. ``no_rules`` remains reachable for a format that genuinely registers
#: nothing; every format that registers a plain JSON file shares ``_hook_files_rules``,
#: which reads that file's events and entry shape from ``HOOK_DIALECTS``.
HOOK_RULE_BUILDERS: dict[
    HookFormat, Callable[[HarnessRecord, InstallPlan], tuple[ProjectionRule, ...]]
] = {
    HookFormat.NONE: no_rules,
    HookFormat.CLAUDE_SETTINGS: _settings_merge_rules,
    HookFormat.CODEX_HOOKS: _hook_files_rules,
    HookFormat.KIMI_HOOKS: _user_home_hook_rules,
    HookFormat.CURSOR_HOOKS: _hook_files_rules,
    HookFormat.DEVIN_HOOKS: _hook_files_rules,
    HookFormat.COPILOT_HOOKS: _hook_files_rules,
}


def harnesses_with_a_hook_derivation() -> frozenset[str]:
    """The registered harnesses whose hook format renders something today.

    A deterministic behaviour reaches a harness only through its hook derivation, so
    this is what the entity registry may claim an implementation for. Derived from the
    builder table, never listed: a format that grows a builder joins the set for free.
    """
    return frozenset(
        name
        for name, record in HARNESS_RECORDS.items()
        if HOOK_RULE_BUILDERS[record.hooks] is not no_rules
    )


#: The doctor residue a byte-compare cannot express, per :class:`HookFormat`.
_HOOK_CHECKS: dict[HookFormat, Callable[[HarnessRecord, Path], list[DoctorLine]]] = {
    HookFormat.CLAUDE_SETTINGS: _settings_merge_checks,
    HookFormat.CODEX_HOOKS: _codex_checks,
}

#: Which targets pull in the authored ``.agents/`` persona + skills set: the shared
#: target itself, plus every harness that transcodes it into a view of its own.
_AUTHORED_SET_TARGETS: frozenset[str] = frozenset(
    {"agents"}
    | {
        record.name
        for record in HARNESS_RECORDS.values()
        if record.agent_transcode is not AgentTranscode.NONE
    }
)


def harness_checks(name: str, workspace_root: Path) -> list[DoctorLine]:
    """The doctor lines for harness *name* that its rule table cannot express."""
    record = HARNESS_RECORDS[name]
    check = _HOOK_CHECKS.get(record.hooks)
    return check(record, workspace_root) if check else []


def projection_rules(plan: InstallPlan) -> tuple[ProjectionRule, ...]:
    """Assemble the exact rule table ``install()`` writes and ``doctor()`` compares."""
    rules: list[ProjectionRule] = []
    rules.extend(_guardrail_pair_rules(plan))
    rules.extend(_dadaia_family_agents_md_rules(plan))
    if _AUTHORED_SET_TARGETS & set(plan.harness_targets):
        rules.extend(_skills_tree_rules(plan))
        rules.extend(
            _agents_agent_rules(plan.agentic_dir, plan.workspace_root, plan.resolved_models)
        )
    for name, record in HARNESS_RECORDS.items():
        if name not in plan.harness_targets:
            continue
        rules.extend(AGENT_RULE_BUILDERS[record.agent_transcode](record, plan))
        rules.extend(HOOK_RULE_BUILDERS[record.hooks](record, plan))
    return tuple(rules)
