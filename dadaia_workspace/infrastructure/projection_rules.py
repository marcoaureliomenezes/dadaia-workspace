"""``projection_rules(plan)`` — the ONE table every projection family renders from.

K3 (v0.5.1): the harness is a real seam (Claude Code, Codex, Kimi Code vary
independently — three production adapters), never a hypothetical one. Each
:class:`HarnessProjection` adapter owns exactly two things: which
:class:`~dadaia_workspace.infrastructure.projection.ProjectionRule` entries it
contributes for a given
:class:`~dadaia_workspace.infrastructure.install_plan.InstallPlan`, and which doctor
lines fall outside a byte-compare (a structural/semantic claim a single rendered file
cannot express, e.g. "does this TOML's cited skill exist"). :func:`projection_rules`
assembles the harness-independent rules (the guardrail pair, the law file, the shared
skills tree, the ``.dadaia/**`` ``AGENTS.md`` family) alongside each active
harness's own — one call builds the exact same table ``install()`` writes and
``doctor()`` compares.
"""

from __future__ import annotations

import json
import os
import stat as stat_module
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Protocol

from dadaia_workspace.core.exceptions import PublicAssetError
from dadaia_workspace.core.harness_registry import L1_ENTRY_HARNESSES
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

#: Read-only mode for projected law files (`.dadaia/AGENTS.md`) — closes the Bash-redirect
#: write path the gate does not parse. A human operator can still chmod and edit.


class HarnessProjection(Protocol):
    """One Layer-1 entry harness's projection surface — the real seam (K3): three
    production adapters vary independently, so a Protocol earns its keep here (unlike
    a single-adapter seam, which would be indirection alone)."""

    id: str
    dirs: tuple[str, ...]

    def rules(self, plan: InstallPlan) -> tuple[ProjectionRule, ...]:
        """The full rule set this harness projects for *plan*."""
        ...

    def checks(self, workspace_root: Path) -> list[DoctorLine]:
        """Doctor lines beyond the rule table — a structural/semantic claim a single
        byte-compare cannot express."""
        ...


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


def _claude_agent_rules(agentic_dir: Path, workspace_root: Path) -> tuple[ProjectionRule, ...]:
    """``.claude/agents/<name>.md`` — one relative symlink per rendered persona."""
    src_dir = agentic_dir / "agents"
    authored = workspace_root / ".agents" / "agents"
    dst_dir = workspace_root / ".claude" / "agents"
    return tuple(
        _link_rule(
            f"claude:agents/{src.relative_to(src_dir).as_posix()}",
            "claude",
            dst_dir / src.relative_to(src_dir),
            authored / src.relative_to(src_dir),
        )
        for src in iter_public_files(src_dir)
    )


def _claude_skill_rules(agentic_dir: Path, workspace_root: Path) -> tuple[ProjectionRule, ...]:
    """``.claude/skills/<skill>`` — one relative symlink per authored skill directory."""
    src_dir = agentic_dir / "skills"
    authored = workspace_root / ".agents" / "skills"
    dst_dir = workspace_root / ".claude" / "skills"
    if not src_dir.is_dir():
        return ()
    return tuple(
        _link_rule(
            f"claude:skills/{skill.name}", "claude", dst_dir / skill.name, authored / skill.name
        )
        for skill in sorted(src_dir.iterdir())
        if skill.is_dir()
    )


def _claude_settings_rule(workspace_root: Path) -> ProjectionRule:
    """``.claude/settings.json`` — an ``owned-slice`` compare (K3): the render MERGES
    the operator's file, folding in only the dadaia hook wiring and preserving every
    other top-level key and every non-dadaia hook entry untouched — the SAME algorithm
    (install=write(render), doctor=compare(render)) that governs a plain byte-compare,
    because the merge is a fixed point on already-canonical content.
    """
    dst = workspace_root / ".claude" / "settings.json"

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

    return ProjectionRule(
        label="claude:settings.json",
        harness="claude",
        dst=dst,
        render=_render,
        compare="owned-slice",
    )


class ClaudeHarness:
    """Claude Code adapter — one of the three real seams (K3). Agents and skills are
    per-entry symlinks onto the authored ``.agents/`` set, never a second copy."""

    id = "claude"
    dirs: tuple[str, ...] = _CLAUDE_DIRS

    def rules(self, plan: InstallPlan) -> tuple[ProjectionRule, ...]:
        claude_dir = plan.workspace_root / ".claude"
        dirs = self.dirs if plan.only is None else tuple(d for d in self.dirs if d == plan.only)
        rules: list[ProjectionRule] = []
        for name in dirs:
            if name == "agents":
                rules.extend(_claude_agent_rules(plan.agentic_dir, plan.workspace_root))
            elif name == "skills":
                rules.extend(_claude_skill_rules(plan.agentic_dir, plan.workspace_root))
            else:
                rules.extend(
                    _tree_bytes_rules(
                        plan.agentic_dir / name,
                        claude_dir / name,
                        harness="claude",
                        label_prefix=f"claude:{name}/",
                    )
                )
        if plan.only is None:
            rules.append(_claude_settings_rule(plan.workspace_root))
        return tuple(rules)

    def checks(self, workspace_root: Path) -> list[DoctorLine]:
        """The one claude check a byte-compare cannot express: a foreign hook command
        is preserved (never drift — the file is the operator's) but never silenced.
        """
        dst = workspace_root / ".claude" / "settings.json"
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
                "claude:settings.json: non-dadaia hook command(s) in gated event(s) — "
                + ", ".join(foreign),
            )
        ]


# ---------------------------------------------------------------------------
# Codex adapter
# ---------------------------------------------------------------------------


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


def _codex_agent_rules(
    agentic_dir: Path, codex_dir: Path, resolved_models: Mapping[str, ResolvedAgentModel]
) -> tuple[ProjectionRule, ...]:
    agents_src = agentic_dir / "agents"
    agents_dst = codex_dir / "agents"
    rules: list[ProjectionRule] = []
    for md_file in sorted(agents_src.glob("*.md")):
        fm = _parse_agent_frontmatter(md_file.read_text(encoding="utf-8"))
        agent_name = str(fm.get("name", "")) if fm else ""
        if not agent_name:
            continue
        resolved = resolved_models.get(agent_name)

        def _render(
            _current: bytes | None,
            _md_file: Path = md_file,
            _agent_name: str = agent_name,
            _resolved: ResolvedAgentModel | None = resolved,
        ) -> bytes:
            return _codex_agent_toml_bytes(_md_file, _agent_name, _resolved)

        rules.append(
            ProjectionRule(
                label=f"codex:agents/{agent_name}.toml",
                harness="codex",
                dst=agents_dst / f"{agent_name}.toml",
                render=_render,
            )
        )
    return tuple(rules)


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


def _codex_config_rule(agentic_dir: Path, codex_dir: Path) -> ProjectionRule:
    return _bytes_rule(
        "codex:config.toml",
        "codex",
        codex_dir / "config.toml",
        codex_config(agentic_dir).encode("utf-8"),
    )


def _codex_rules_file_rule(workspace_root: Path) -> ProjectionRule:
    return _bytes_rule(
        "codex:rules/dadaia-command-policy.rules",
        "codex",
        workspace_root / ".codex" / "rules" / "dadaia-command-policy.rules",
        _render_codex_command_policy_rules().encode("utf-8"),
    )


def _codex_hooks_json_rule(workspace_root: Path) -> ProjectionRule:
    return _bytes_rule(
        "codex:hooks.json",
        "codex",
        workspace_root / ".codex" / "hooks.json",
        (json.dumps(codex_hooks(workspace_root), indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )


def _codex_hook_wrapper_rules(workspace_root: Path) -> tuple[ProjectionRule, ...]:
    return tuple(
        _bytes_rule(
            f"dadaia:hooks/{name}",
            "codex",
            workspace_root / ".dadaia" / "hooks" / name,
            content.encode("utf-8"),
            mode=0o755,
        )
        for name, content in codex_hook_wrapper_contents().items()
    )


class CodexHarness:
    """Codex adapter — one of the three real seams (K3). Per-agent TOML and
    ``config.toml`` are compared byte-wise, exactly like a Claude agent render,
    replacing D-CX-1/2/4/5/10's shape/regex re-derivation of the same fact. Codex reads
    the shared ``.agents/skills`` tree natively, so it owns no skills copy.
    """

    id = "codex"
    dirs: tuple[str, ...] = ("rules", "agents")

    def rules(self, plan: InstallPlan) -> tuple[ProjectionRule, ...]:
        codex_dir = plan.workspace_root / ".codex"
        rules: list[ProjectionRule] = []
        if plan.only is None or plan.only == "rules":
            rules.append(_codex_rules_file_rule(plan.workspace_root))
        if plan.only is None or plan.only == "agents":
            rules.extend(_codex_agent_rules(plan.agentic_dir, codex_dir, plan.resolved_models))
            rules.append(_codex_config_rule(plan.agentic_dir, codex_dir))
        if plan.only is None:
            rules.append(_codex_hooks_json_rule(plan.workspace_root))
            rules.extend(_codex_hook_wrapper_rules(plan.workspace_root))
        return tuple(rules)

    def checks(self, workspace_root: Path) -> list[DoctorLine]:
        """D-CX-6/7/8/9 plus the version-qualified trust-boundary INFO line — all
        gated on codex being in profile, matching the historical ``"codex" in active``
        guard. ``check_codex_rule_corpus_reachable`` stays a top-level, UNCONDITIONAL
        doctor() attestation (never gated) — the ``rule-corpus`` id in
        ``ATTESTING_CHECK_IDS`` must never vanish for a codex-absent profile."""
        out: list[DoctorLine] = []
        out.extend(dcx7_codex_skill_refs(workspace_root))
        out.extend(dcx8_codex_rules_shape(workspace_root / ".codex"))
        out.extend(dcx9_codex_hook_shape(workspace_root))
        out.extend(codex_trust_boundary_info())
        return out


# ---------------------------------------------------------------------------
# Kimi Code adapter
# ---------------------------------------------------------------------------


def _kimi_config_block_rule(home: Path) -> ProjectionRule:
    def _render(current: bytes | None) -> bytes:
        existing = current.decode("utf-8") if current is not None else ""
        return upsert_kimi_hooks_block(existing, kimi_hooks_block(home)).encode("utf-8")

    return ProjectionRule(
        label="kimi-code:config.toml managed hooks block",
        harness="kimi-code",
        dst=home / "config.toml",
        render=_render,
        compare="managed-block",
    )


class KimiHarness:
    """Kimi Code adapter — one of the three real seams (K3). Kimi has no
    project-level config file: hook registration is a managed block folded into the
    user-level ``$KIMI_CODE_HOME/config.toml`` — the SAME fixed-point algorithm as
    every other rule, because ``upsert_kimi_hooks_block`` is already a pure
    ``render(existing) -> full content`` merge.
    """

    id = "kimi-code"
    dirs: tuple[str, ...] = ()

    def rules(self, plan: InstallPlan) -> tuple[ProjectionRule, ...]:
        rules: list[ProjectionRule] = []
        if plan.only is None:
            home = kimi_code_home()
            for name, content in kimi_hook_shims().items():
                rules.append(
                    _bytes_rule(
                        f"kimi-code:hooks/{name}",
                        "kimi-code",
                        home / "hooks" / name,
                        content.encode("utf-8"),
                        mode=0o755,
                    )
                )
            rules.append(_kimi_config_block_rule(home))
        return tuple(rules)

    def checks(self, workspace_root: Path) -> list[DoctorLine]:
        """Executability is not a byte-compare claim: a cleared exec bit on an
        otherwise-correct shim is repairable DRIFT, but a noexec-mounted
        ``$KIMI_CODE_HOME`` is UNSUPPORTED (reinstalling can never fix a mount option).
        """
        del workspace_root  # kimi hooks live at the user-level home, not the workspace
        home = kimi_code_home()
        out: list[DoctorLine] = []
        for name in kimi_hook_shims():
            dst = home / "hooks" / name
            label = f"kimi-code:hooks/{name}"
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


def build_harnesses() -> dict[str, HarnessProjection]:
    """The three real adapters (K3) — each one stateless since the Codex-only runtime
    adapter family was retired."""
    return {
        "claude": ClaudeHarness(),
        "codex": CodexHarness(),
        "kimi-code": KimiHarness(),
    }


def projection_rules(
    plan: InstallPlan, harnesses: Mapping[str, HarnessProjection]
) -> tuple[ProjectionRule, ...]:
    """Assemble the exact rule table ``install()`` writes and ``doctor()`` compares."""
    rules: list[ProjectionRule] = []
    rules.extend(_guardrail_pair_rules(plan))
    rules.extend(_dadaia_family_agents_md_rules(plan))
    # The authored ``.agents/`` set is projected for every target that reads it —
    # Codex and Kimi natively, Claude through the symlinks its adapter contributes.
    if {"agents", "codex", "claude"} & set(plan.harness_targets):
        if plan.only is None or plan.only == "skills":
            rules.extend(_skills_tree_rules(plan))
        if plan.only is None or plan.only == "agents":
            rules.extend(
                _agents_agent_rules(plan.agentic_dir, plan.workspace_root, plan.resolved_models)
            )
    for name in L1_ENTRY_HARNESSES:
        if name in plan.harness_targets:
            rules.extend(harnesses[name].rules(plan))
    return tuple(rules)
