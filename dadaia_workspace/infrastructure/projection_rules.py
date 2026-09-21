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
import os
import stat as stat_module
from collections.abc import Callable, Mapping
from pathlib import Path

from dadaia_workspace.core.exceptions import PublicAssetError
from dadaia_workspace.core.harness_registry import (
    HARNESS_RECORDS,
    AgentTranscode,
    HarnessRecord,
    HookFormat,
)
from dadaia_workspace.core.models.agent_model_policy import ResolvedAgentModel
from dadaia_workspace.core.models.doctor_report import DoctorLine, DoctorStatus
from dadaia_workspace.infrastructure.codex_doctor import (
    codex_trust_boundary_info,
    dcx7_codex_skill_refs,
    dcx8_codex_rules_shape,
    dcx9_codex_hook_shape,
)
from dadaia_workspace.infrastructure.install_helpers import (
    activity_read_only,
    render_claude_agent,
    resolve_codex_agent_model,
)
from dadaia_workspace.infrastructure.install_plan import InstallPlan
from dadaia_workspace.infrastructure.projection import ProjectionRule, link_render
from dadaia_workspace.infrastructure.public_assets_common import (
    _CLAUDE_DIRS,
    iter_public_files,
)
from dadaia_workspace.infrastructure.runtime_config import (
    claude_settings,
    codex_config,
    codex_hook_wrapper_contents,
    codex_hooks,
    foreign_claude_hook_commands,
    kimi_code_home,
    kimi_hook_shims,
    kimi_hooks_block,
    merge_claude_settings,
    upsert_kimi_hooks_block,
)
from dadaia_workspace.infrastructure.runtime_transforms.codex import transform_for_codex
from dadaia_workspace.infrastructure.runtime_transforms.codex_assets import (
    _parse_agent_frontmatter,
    _render_codex_agent_toml,
    _render_codex_command_policy_rules,
)
from dadaia_workspace.infrastructure.runtime_transforms.model_mapping import map_model
from dadaia_workspace.infrastructure.workspace_guardrail import (
    _agents_md_source,
)

# ---------------------------------------------------------------------------
# Small building blocks
# ---------------------------------------------------------------------------


def _fixed_content_render(content: bytes) -> Callable[[bytes | None], bytes]:
    def _render(_current: bytes | None) -> bytes:
        return content

    return _render


def _bytes_rule(
    label: str,
    harness: str,
    dst: Path,
    content: bytes,
    *,
    mode: int | None = None,
) -> ProjectionRule:
    """A rule whose canonical content is fixed at rule-build time (``compare="bytes"``)."""
    return ProjectionRule(
        label=label,
        harness=harness,
        dst=dst,
        render=_fixed_content_render(content),
        compare="bytes",
        mode=mode,
    )


def _link_rule(label: str, harness: str, dst: Path, link_to: Path) -> ProjectionRule:
    """A rule that projects a RELATIVE symlink at *dst* onto the authored *link_to*.

    One authored set, N harness views: the executor falls back to a hash-verified copy
    where the platform refuses symlinks, and records which of the two it wrote.
    """
    return ProjectionRule(
        label=label, harness=harness, dst=dst, render=link_render, link_to=link_to
    )


def _tree_bytes_rules(
    src_dir: Path,
    dst_dir: Path,
    *,
    harness: str,
    label_prefix: str,
    mode: int | None = None,
) -> tuple[ProjectionRule, ...]:
    """One ``compare="bytes"`` rule per real file under *src_dir* (verbatim copy).

    A projection is a copy of the source, permissions included: an authored file that is
    executable projects executable (0.4.7 FR1 — a skill script the agent runs directly).
    The source's own exec bit is the whole rule; no path knows what a `scripts/` dir is.
    """
    rules: list[ProjectionRule] = []
    for src in iter_public_files(src_dir):
        rel = src.relative_to(src_dir)
        rules.append(
            _bytes_rule(
                f"{label_prefix}{rel.as_posix()}",
                harness,
                dst_dir / rel,
                src.read_bytes(),
                mode=mode if mode is not None else (0o755 if os.access(src, os.X_OK) else None),
            )
        )
    return tuple(rules)


# ---------------------------------------------------------------------------
# Harness-independent rules: guardrail pair (root), law, dadaia-family AGENTS.md
# ---------------------------------------------------------------------------


def _guardrail_pair_rules(plan: InstallPlan) -> tuple[ProjectionRule, ...]:
    """The root ``AGENTS.md`` map — one rule, one destination (collapsed the
    pair: the Claude bridge stub is retired, Claude Code reads ``AGENTS.md`` natively).

    Consumer-repo fan-out (``repos/<slug>:AGENTS.md``) is provenance-gated, N-target
    discovery-based writing with foreign-authorship detection — a fundamentally
    different mechanism from "one rule, one destination" — and stays the bespoke
    ``workspace_guardrail._install_guardrail_pair`` path, invoked directly by the
    manager.
    """
    if "workspace" not in plan.guardrail_targets:
        return ()
    src = _agents_md_source(plan.agentic_dir)
    if src is None:
        return ()
    return (
        _bytes_rule(
            "root:AGENTS.md", "agents", plan.workspace_root / "AGENTS.md", src.read_bytes()
        ),
    )


#: (staged source name, destination relpath, doctor label) for the ``.dadaia/**``
#: ``AGENTS.md`` family — unconditional, harness-independent.
_DADAIA_FAMILY_AGENTS_MD: tuple[tuple[str, str, str], ...] = (
    ("handoff-AGENTS.md", ".dadaia/handoff/AGENTS.md", "handoff:AGENTS.md"),
    ("dadaia-AGENTS.md", ".dadaia/AGENTS.md", "dadaia:AGENTS.md"),
    ("tmp-AGENTS.md", ".dadaia/tmp/AGENTS.md", "dadaia:tmp/AGENTS.md"),
    ("states-AGENTS.md", ".dadaia/states/AGENTS.md", "dadaia:states/AGENTS.md"),
)


def _dadaia_family_agents_md_rules(plan: InstallPlan) -> tuple[ProjectionRule, ...]:
    rules: list[ProjectionRule] = []
    for source_name, rel_dst, label in _DADAIA_FAMILY_AGENTS_MD:
        src = plan.agentic_dir / "data" / source_name
        if src.is_file():
            rules.append(
                _bytes_rule(label, "agents", plan.workspace_root / rel_dst, src.read_bytes())
            )
    return tuple(rules)


def _skills_tree_rules(plan: InstallPlan) -> tuple[ProjectionRule, ...]:
    """The shared skills root (``.agents/skills/``) — the ONE authored copy. Codex and
    Kimi Code read it natively; Claude Code reaches it through the per-skill symlinks
    ``ClaudeHarness`` projects into ``.claude/skills/``.
    """
    return _tree_bytes_rules(
        plan.agentic_dir / "skills",
        plan.workspace_root / ".agents" / "skills",
        harness="agents",
        label_prefix="agents:skills/",
    )


# ---------------------------------------------------------------------------
# Claude Code adapter
# ---------------------------------------------------------------------------


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
        resolved = resolved_models.get(src.stem)
        if resolved is None or src.suffix != ".md":
            rules.append(_bytes_rule(label, "agents", dst_dir / rel, src.read_bytes()))
            continue
        staged_text = src.read_text(encoding="utf-8")

        def _render(
            _current: bytes | None,
            _text: str = staged_text,
            _resolved: ResolvedAgentModel = resolved,
        ) -> bytes:
            return render_claude_agent(_text, _resolved).encode("utf-8")

        rules.append(
            ProjectionRule(label=label, harness="agents", dst=dst_dir / rel, render=_render)
        )
    return tuple(rules)


# ---------------------------------------------------------------------------
# agent_transcode builders — one per enum value
# ---------------------------------------------------------------------------


def _no_rules(record: HarnessRecord, plan: InstallPlan) -> tuple[ProjectionRule, ...]:
    """``none``: reads the authored tree natively / registers no hooks — projects nothing."""
    del record, plan
    return ()


def _md_symlink_rules(record: HarnessRecord, plan: InstallPlan) -> tuple[ProjectionRule, ...]:
    """``claude-md-symlink``: agents and skills are per-entry relative symlinks onto the
    authored ``.agents/`` set, never a second copy; other content dirs copy verbatim."""
    harness_dir = plan.workspace_root / str(record.directory)
    authored = plan.workspace_root / ".agents"
    src_agents = plan.agentic_dir / "agents"
    src_skills = plan.agentic_dir / "skills"
    dirs = _CLAUDE_DIRS if plan.only is None else tuple(d for d in _CLAUDE_DIRS if d == plan.only)
    rules: list[ProjectionRule] = []
    for name in dirs:
        if name == "agents":
            rules.extend(
                _link_rule(
                    f"{record.name}:agents/{src.relative_to(src_agents).as_posix()}",
                    record.name,
                    harness_dir / "agents" / src.relative_to(src_agents),
                    authored / "agents" / src.relative_to(src_agents),
                )
                for src in iter_public_files(src_agents)
            )
        elif name == "skills":
            skills = sorted(src_skills.iterdir()) if src_skills.is_dir() else []
            rules.extend(
                _link_rule(
                    f"{record.name}:skills/{skill.name}",
                    record.name,
                    harness_dir / "skills" / skill.name,
                    authored / "skills" / skill.name,
                )
                for skill in skills
                if skill.is_dir()
            )
        else:
            rules.extend(
                _tree_bytes_rules(
                    plan.agentic_dir / name,
                    harness_dir / name,
                    harness=record.name,
                    label_prefix=f"{record.name}:{name}/",
                )
            )
    return tuple(rules)


def _codex_agent_toml_bytes(
    md_path: Path, agent_name: str, resolved: ResolvedAgentModel | None
) -> bytes:
    """The ONE codex-agent renderer — mirrors the historical ``install_codex_agents``
    per-file body exactly (frontmatter parse, strip, Codex transform, resolve
    ``(model, effort)``, render TOML). Shared by install (write) and doctor (compare)
    through the :class:`ProjectionRule` seam, replacing D-CX-1/2/4/5/10's shape/regex
    re-derivation of the same fact.
    """
    text = md_path.read_text(encoding="utf-8")
    fm = _parse_agent_frontmatter(text)
    if text.startswith("---\n"):
        end_idx = text.find("\n---\n", 4)
        body = text[end_idx + 5 :] if end_idx != -1 else text
    else:
        body = text
    body = transform_for_codex(body, agent_name)
    staged_model_raw = fm.get("model") if fm else None
    staged_model = str(staged_model_raw) if staged_model_raw else None
    claude_model, reasoning_effort = resolve_codex_agent_model(agent_name, staged_model, resolved)
    codex_model = map_model(claude_model)
    description = fm.get("description") if fm else None
    codex_description = transform_for_codex(str(description), agent_name) if description else None
    toml_content = _render_codex_agent_toml(
        agent_name,
        codex_model,
        body,
        description=codex_description,
        claude_model=claude_model,
        reasoning_effort=reasoning_effort,
        read_only=activity_read_only(fm),
    )
    return toml_content.encode("utf-8")


def _toml_transcode_rules(record: HarnessRecord, plan: InstallPlan) -> tuple[ProjectionRule, ...]:
    """``codex-toml``: per-agent TOML, ``config.toml`` and the command-policy rules file,
    all compared byte-wise. The shared ``.agents/skills`` tree is read natively."""
    harness_dir = plan.workspace_root / str(record.directory)
    rules: list[ProjectionRule] = []
    if plan.only is None or plan.only == "rules":
        rules.append(
            _bytes_rule(
                f"{record.name}:rules/dadaia-command-policy.rules",
                record.name,
                harness_dir / "rules" / "dadaia-command-policy.rules",
                _render_codex_command_policy_rules().encode("utf-8"),
            )
        )
    if plan.only is None or plan.only == "agents":
        agents_src = plan.agentic_dir / "agents"
        for md_file in sorted(agents_src.glob("*.md")):
            fm = _parse_agent_frontmatter(md_file.read_text(encoding="utf-8"))
            agent_name = str(fm.get("name", "")) if fm else ""
            if not agent_name:
                continue
            resolved = plan.resolved_models.get(agent_name)

            def _render(
                _current: bytes | None,
                _md_file: Path = md_file,
                _agent_name: str = agent_name,
                _resolved: ResolvedAgentModel | None = resolved,
            ) -> bytes:
                return _codex_agent_toml_bytes(_md_file, _agent_name, _resolved)

            rules.append(
                ProjectionRule(
                    label=f"{record.name}:agents/{agent_name}.toml",
                    harness=record.name,
                    dst=harness_dir / "agents" / f"{agent_name}.toml",
                    render=_render,
                )
            )
        rules.append(
            _bytes_rule(
                f"{record.name}:config.toml",
                record.name,
                harness_dir / "config.toml",
                codex_config(plan.agentic_dir).encode("utf-8"),
            )
        )
    return tuple(rules)


#: One builder per :class:`AgentTranscode` value — the dispatch that replaced a class
#: per harness.
_AGENT_RULE_BUILDERS: dict[
    AgentTranscode, Callable[[HarnessRecord, InstallPlan], tuple[ProjectionRule, ...]]
] = {
    AgentTranscode.NONE: _no_rules,
    AgentTranscode.CLAUDE_MD_SYMLINK: _md_symlink_rules,
    AgentTranscode.CODEX_TOML: _toml_transcode_rules,
}


def prune_stale_codex_tomls(
    codex_dir: Path, expected: frozenset[str], installed: list[str]
) -> None:
    """Remove a ``.codex/agents/*.toml`` whose agent no longer exists in source.

    Unconditional (rc-4 / T-017-32): an agent removed from source must not leave an
    orphan projection, regardless of ``--force``. *expected* is the set of TOML
    filenames the current rule table just projected.
    """
    agents_dst = codex_dir / "agents"
    if not agents_dst.is_dir():
        return
    for stale in sorted(agents_dst.glob("*.toml")):
        if stale.name not in expected:
            stale.unlink()
            installed.append(f"[rm]   {stale}")


# ---------------------------------------------------------------------------
# hooks builders — one per enum value, plus the checks a byte-compare cannot express
# ---------------------------------------------------------------------------


def _settings_merge_rules(record: HarnessRecord, plan: InstallPlan) -> tuple[ProjectionRule, ...]:
    """``claude-settings``: an ``owned-slice`` compare — the render MERGES the operator's
    file, folding in only the dadaia hook wiring and leaving every other top-level key and
    non-dadaia hook entry untouched. Still one algorithm, because the merge is a fixed
    point on already-canonical content."""
    if plan.only is not None:
        return ()
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
    foreign = foreign_claude_hook_commands(loaded, claude_settings(workspace_root))
    if not foreign:
        return []
    return [
        DoctorLine(
            DoctorStatus.WARN,
            f"{record.name}:settings.json: non-dadaia hook command(s) in gated event(s) — "
            + ", ".join(foreign),
        )
    ]


def _hooks_json_rules(record: HarnessRecord, plan: InstallPlan) -> tuple[ProjectionRule, ...]:
    """``codex-hooks``: a project-level ``hooks.json`` plus the shared wrapper scripts the
    harness shells out to."""
    if plan.only is not None:
        return ()
    workspace_root = plan.workspace_root
    rules = [
        _bytes_rule(
            f"{record.name}:hooks.json",
            record.name,
            workspace_root / str(record.directory) / "hooks.json",
            (json.dumps(codex_hooks(workspace_root), indent=2, sort_keys=True) + "\n").encode(
                "utf-8"
            ),
        )
    ]
    rules.extend(
        _bytes_rule(
            f"dadaia:hooks/{name}",
            record.name,
            workspace_root / ".dadaia" / "hooks" / name,
            content.encode("utf-8"),
            mode=0o755,
        )
        for name, content in codex_hook_wrapper_contents().items()
    )
    return tuple(rules)


def _hooks_json_checks(record: HarnessRecord, workspace_root: Path) -> list[DoctorLine]:
    """D-CX-6/7/8/9 plus the version-qualified trust-boundary INFO line — all gated on the
    harness being in profile. ``check_codex_rule_corpus_reachable`` stays a top-level,
    UNCONDITIONAL doctor() attestation (never gated): the ``rule-corpus`` id in
    ``ATTESTING_CHECK_IDS`` must never vanish for an out-of-profile harness."""
    out: list[DoctorLine] = []
    out.extend(dcx7_codex_skill_refs(workspace_root))
    out.extend(dcx8_codex_rules_shape(workspace_root / str(record.directory)))
    out.extend(dcx9_codex_hook_shape(workspace_root))
    out.extend(codex_trust_boundary_info())
    return out


def _user_home_hook_rules(record: HarnessRecord, plan: InstallPlan) -> tuple[ProjectionRule, ...]:
    """``kimi-hooks``: no project-level config file — hook registration is a managed block
    folded into the user-level ``$KIMI_CODE_HOME/config.toml``, the same fixed-point
    algorithm as every other rule."""
    if plan.only is not None:
        return ()
    home = kimi_code_home()
    rules = [
        _bytes_rule(
            f"{record.name}:hooks/{name}",
            record.name,
            home / "hooks" / name,
            content.encode("utf-8"),
            mode=0o755,
        )
        for name, content in kimi_hook_shims().items()
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


def _user_home_hook_checks(record: HarnessRecord, workspace_root: Path) -> list[DoctorLine]:
    """Executability is not a byte-compare claim: a cleared exec bit is repairable DRIFT,
    but a noexec mount is UNSUPPORTED — reinstalling can never fix a mount option."""
    del workspace_root  # these hooks live at the user-level home, not the workspace
    home = kimi_code_home()
    out: list[DoctorLine] = []
    for name in kimi_hook_shims():
        dst = home / "hooks" / name
        label = f"{record.name}:hooks/{name}"
        if not dst.is_file() or os.access(dst, os.X_OK):
            continue
        if dst.stat().st_mode & stat_module.S_IXUSR:
            out.append(
                DoctorLine(
                    DoctorStatus.UNSUPPORTED,
                    f"{label} (filesystem mounted noexec — the exec bits are set "
                    "but the mount forbids execution; point KIMI_CODE_HOME at a path "
                    "on an executable filesystem)",
                )
            )
        else:
            out.append(DoctorLine(DoctorStatus.DRIFT, f"{label} (not executable)"))
    return out


def _no_checks(record: HarnessRecord, workspace_root: Path) -> list[DoctorLine]:
    del record, workspace_root
    return []


#: One builder per :class:`HookFormat` value.
_HOOK_RULE_BUILDERS: dict[
    HookFormat, Callable[[HarnessRecord, InstallPlan], tuple[ProjectionRule, ...]]
] = {
    HookFormat.NONE: _no_rules,
    HookFormat.CLAUDE_SETTINGS: _settings_merge_rules,
    HookFormat.CODEX_HOOKS: _hooks_json_rules,
    HookFormat.KIMI_HOOKS: _user_home_hook_rules,
}

#: The doctor residue per :class:`HookFormat` value — a structural/semantic claim a
#: single rendered file cannot express.
_HOOK_CHECKS: dict[HookFormat, Callable[[HarnessRecord, Path], list[DoctorLine]]] = {
    HookFormat.NONE: _no_checks,
    HookFormat.CLAUDE_SETTINGS: _settings_merge_checks,
    HookFormat.CODEX_HOOKS: _hooks_json_checks,
    HookFormat.KIMI_HOOKS: _user_home_hook_checks,
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
    return _HOOK_CHECKS[record.hooks](record, workspace_root)


def projection_rules(plan: InstallPlan) -> tuple[ProjectionRule, ...]:
    """Assemble the exact rule table ``install()`` writes and ``doctor()`` compares."""
    rules: list[ProjectionRule] = []
    rules.extend(_guardrail_pair_rules(plan))
    rules.extend(_dadaia_family_agents_md_rules(plan))
    if _AUTHORED_SET_TARGETS & set(plan.harness_targets):
        if plan.only is None or plan.only == "skills":
            rules.extend(_skills_tree_rules(plan))
        if plan.only is None or plan.only == "agents":
            rules.extend(
                _agents_agent_rules(plan.agentic_dir, plan.workspace_root, plan.resolved_models)
            )
    for name, record in HARNESS_RECORDS.items():
        if name not in plan.harness_targets:
            continue
        rules.extend(_AGENT_RULE_BUILDERS[record.agent_transcode](record, plan))
        rules.extend(_HOOK_RULE_BUILDERS[record.hooks](record, plan))
    return tuple(rules)
