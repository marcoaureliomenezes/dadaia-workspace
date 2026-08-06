"""Public asset manager — stages package assets and projects them to agent runtimes."""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
from collections.abc import Iterable
from pathlib import Path
from typing import Literal

from dadaia_workspace.core.agent_model_templates import CORE_AGENTS, resolve_agent_model
from dadaia_workspace.core.exceptions import PublicAssetError
from dadaia_workspace.core.execute_bit import PLATFORM_HAS_EXECUTE_BIT
from dadaia_workspace.core.harness_registry import L1_ENTRY_HARNESSES, PROJECTION_TARGETS
from dadaia_workspace.core.models.agent_model_policy import (
    AgentModelPolicyOverlay,
    AgentModelPolicyStoreError,
    ResolvedAgentModel,
)
from dadaia_workspace.core.models.plugin_pack import InstalledPlugins
from dadaia_workspace.core.protocols.plugin_store import PluginStore
from dadaia_workspace.infrastructure.codex_doctor import (
    check_agent_skill_refs,
    check_codex_drift,
    check_memory_phase_single_source,
    check_rule_corpus_reachable,
    codex_trust_boundary_info,
    dcx1_missing_toml,
    dcx2_config_toml_entries,
    dcx4_claude_strings,
    dcx5_empty_developer_instructions,
    dcx6_codex_runtime_adapters,
)
from dadaia_workspace.infrastructure.install_helpers import (
    build_agents_index,
    build_manifest,
    copy_file,
    copy_tree,
    install_agents_md,
    install_claude_agents,
    install_codex_agents,
    install_codex_runtime_adapters,
    install_dadaia_agents_md,
    install_handoff_agents_md,
    install_reports_agents_md,
    install_universal_skills,
    load_projection_ledger,
    remove_legacy_workflow_projections,
    render_claude_agent,
    resolve_codex_agent_model,
    runtime_expectations,
    save_projection_ledger,
    write_generated,
)
from dadaia_workspace.infrastructure.json_agent_model_policy_store import (
    JsonAgentModelPolicyStore,
)
from dadaia_workspace.infrastructure.json_harness_profile_store import JsonHarnessProfileStore
from dadaia_workspace.infrastructure.json_plugin_store import JsonPluginStore

# Several names below are imported purely for re-export, so tests and other
# consumers can keep importing them from public_assets after the T-017-11 split.
# Those import blocks are marked F401-exempt.
from dadaia_workspace.infrastructure.privacy_check import (  # noqa: F401
    _PRIVACY_DENYLIST_ENV,
    _PUBLIC_ASSET_IGNORED_DIRS,
    _PUBLIC_ASSET_IGNORED_SUFFIXES,
    _load_privacy_denylist,
)
from dadaia_workspace.infrastructure.privacy_check import (
    check_public_privacy as _check_public_privacy_fn,
)
from dadaia_workspace.infrastructure.public_assets_common import (  # noqa: F401
    _CLAUDE_DIRS,
    _COPY_DIRS,
    _KIMI_DIRS,
    _PI_DIRS,
    _SCHEMA_VERSION,
    _VALID_TARGETS,
    _atomic_write_text,
    _json_dump,
    _log_cleanup_error,
    _package_version,
    _sha256,
    _toml_escape,
)
from dadaia_workspace.infrastructure.runtime_config import (
    claude_settings as _build_claude_settings,
)
from dadaia_workspace.infrastructure.runtime_config import (
    codex_config as _build_codex_config,
)
from dadaia_workspace.infrastructure.runtime_config import (
    codex_hook_wrapper_contents as _build_codex_hook_wrapper_contents,
)
from dadaia_workspace.infrastructure.runtime_config import (
    codex_hooks as _build_codex_hooks,
)
from dadaia_workspace.infrastructure.runtime_config import (
    dadaia_owned_claude_settings as _dadaia_owned_claude_settings,
)
from dadaia_workspace.infrastructure.runtime_config import (
    foreign_claude_hook_commands as _foreign_claude_hook_commands,
)
from dadaia_workspace.infrastructure.runtime_config import (
    kimi_code_home,
    kimi_hook_shims,
    kimi_hooks_block,
    upsert_kimi_hooks_block,
)
from dadaia_workspace.infrastructure.runtime_config import (
    merge_claude_settings as _merge_claude_settings,
)
from dadaia_workspace.infrastructure.runtime_transforms.codex import transform_for_codex
from dadaia_workspace.infrastructure.runtime_transforms.codex_assets import (  # noqa: F401
    _parse_agent_frontmatter,
    _parse_write_allowlist,
    _render_agent_toml_block,
    _render_agents_config_file_blocks,
    _render_agents_into_codex_config,
    _render_codex_agent_toml,
    _render_codex_command_policy_rules,
)
from dadaia_workspace.infrastructure.runtime_transforms.model_mapping import map_model
from dadaia_workspace.infrastructure.workspace_guardrail import (  # noqa: F401
    _CANONICAL_AGENTS_BANNER,
    _CLAUDE_MD_STUB,
    _carries_canonical_banner,
    _consumer_repos_for_root,
    _doctor_consumer_pair_lines,
    _doctor_guardrail_pair,
    _install_consumer_repos_guardrail_pair,
    _install_guardrail_pair,
    _install_workspace_guardrail_pair,
    _install_workspace_root_guardrail_pair,
    _is_self_repo,
    _is_source_repo_root,
)

#: Non-silent doctor line for a runtime whose directory physically exists on disk but is
#: NOT in the persisted harness profile (A3, v0.1.58 FR3). Emitted in place of the scoped
#: drift block so a stale/hand-installed out-of-profile runtime never reads green-with-zero-
#: lines. ``[warn]`` is non-blocking (CLI exit stays 0) but visible.
_OUT_OF_PROFILE_WARN = "[warn] {harness}: out-of-profile runtime present (drift unchecked)"


def _restore_execute_bit(dst: Path) -> str | None:
    """Make *dst* executable; return a report line when it could not be made so.

    Bug r24-public-install-does-not-repair-kimi-shim-mode: this chmod used to sit inside a
    bare ``contextlib.suppress(OSError)``. Doctor diagnosed ``(not executable)`` and
    prescribed ``dadaia public install --target kimi-code``; the install exited 0, the bit
    was never restored, and the very next doctor reported the identical drift. The
    operator was told the remedy ran.

    An installer must not die over one mode bit, so the suppression itself was not the
    mistake — erasing the outcome was. The mode is read back rather than inferred from
    chmod returning cleanly, because a filesystem may accept the call and ignore it.
    """
    if not PLATFORM_HAS_EXECUTE_BIT:
        # The read-back below is the whole point of this function, and on Windows it can
        # only ever fail: chmod there toggles the read-only attribute and never sets an
        # execute bit, so every managed script would be installed with an [error] line
        # naming a mode the filesystem does not have (bug
        # doctor-reports-unrepairable-exec-bit-drift-on-windows).
        return None
    try:
        dst.chmod(0o755)
    except OSError as exc:
        return f"[error] {dst} not executable — chmod failed: {exc.strerror or exc}"
    try:
        if not dst.stat().st_mode & stat.S_IXUSR:
            return f"[error] {dst} not executable — the filesystem did not accept mode 755"
    except OSError as exc:
        return f"[error] {dst} not executable — mode unreadable: {exc.strerror or exc}"
    return None


class FileSystemPublicAssetManager:
    def __init__(self, plugin_store: PluginStore = JsonPluginStore()) -> None:
        # Injectable installed-plugins ledger seam (T-61-20 / FR4). The same-layer
        # ``JsonPluginStore()`` default is legal (infrastructure consuming
        # infrastructure); the composition root (``container.build_plugin_store``)
        # injects the port for CLI consumers.
        self._public_dir = Path(__file__).parent.parent / "public"
        self._plugin_store = plugin_store

    # ------------------------------------------------------------------
    # Thin delegators (T-017-11) — preserve the historical method surface
    # that tests/consumers call; the logic lives in the extracted modules
    # (install_helpers, codex_doctor, runtime_config, codex_assets).
    # ------------------------------------------------------------------

    def _copy_file(self, src: Path, dst: Path, force: bool, installed: list[str]) -> None:
        copy_file(src, dst, force, installed)

    def _copy_tree(
        self,
        src: Path,
        dst: Path,
        force: bool,
        installed: list[str],
        owned: Iterable[str] | None = None,
    ) -> set[str]:
        return copy_tree(src, dst, force, installed, self._iter_files, owned=owned)

    def _write_generated(self, dst: Path, content: str, force: bool, installed: list[str]) -> None:
        write_generated(dst, content, force, installed)

    def _runtime_expectations(
        self, agentic_dir: Path, workspace_root: Path
    ) -> Iterable[tuple[Path | None, Path, str, bool]]:
        return runtime_expectations(
            agentic_dir,
            workspace_root,
            self._iter_files,
            _CLAUDE_DIRS,
            self._agents_md_source,
        )

    def _install_codex_agents(
        self, agentic_dir: Path, workspace_root: Path, force: bool, installed: list[str]
    ) -> None:
        install_codex_agents(
            agentic_dir,
            workspace_root,
            force,
            installed,
            resolved_models=self._resolved_core_models(
                self._load_agent_policy(workspace_root, agentic_dir)
            ),
        )

    def _install_codex_runtime_adapters(
        self, workspace_root: Path, force: bool, installed: list[str]
    ) -> None:
        install_codex_runtime_adapters(
            self._public_dir, workspace_root, force, installed, copy_file
        )

    def _install_codex_rules(
        self, agentic_dir: Path, workspace_root: Path, force: bool, installed: list[str]
    ) -> None:
        dst_dir = workspace_root / ".codex" / "rules"
        dst_dir.mkdir(parents=True, exist_ok=True)
        if force:
            for stale in sorted(dst_dir.glob("*.md")):
                stale.unlink()
                installed.append(f"[rm]   {stale}")
        write_generated(
            dst_dir / "dadaia-command-policy.rules",
            _render_codex_command_policy_rules(),
            force,
            installed,
        )

    def _check_codex_drift(self, agentic_dir: Path, workspace_root: Path) -> list[str]:
        return check_codex_drift(agentic_dir, workspace_root, self._public_dir)

    def _dcx1_missing_toml(self, agentic_dir: Path, codex_dir: Path) -> list[str]:
        return dcx1_missing_toml(agentic_dir, codex_dir)

    def _dcx2_config_toml_entries(self, agentic_dir: Path, codex_dir: Path) -> list[str]:
        return dcx2_config_toml_entries(agentic_dir, codex_dir)

    def _dcx4_claude_strings(self, codex_dir: Path) -> list[str]:
        return dcx4_claude_strings(codex_dir)

    def _dcx5_empty_developer_instructions(self, codex_dir: Path) -> list[str]:
        return dcx5_empty_developer_instructions(codex_dir)

    def _dcx6_codex_runtime_adapters(self, workspace_root: Path) -> list[str]:
        return dcx6_codex_runtime_adapters(workspace_root, self._public_dir)

    def _claude_settings(self, workspace_root: Path) -> dict[str, object]:
        return _build_claude_settings(workspace_root)

    def _codex_config(self, agentic_dir: Path) -> str:
        return _build_codex_config(agentic_dir)

    def _codex_hooks(self, workspace_root: Path) -> dict[str, object]:
        return _build_codex_hooks(workspace_root)

    def _profile_harnesses(self, workspace_root: Path) -> set[str] | None:
        """Return the persisted harness set, or ``None`` when no profile file exists.

        Reads ``.dadaia/states/harness_profile.json`` via the same-layer
        ``JsonHarnessProfileStore`` adapter (infrastructure consuming infrastructure). An
        absent profile ⇒ ``None``, and every consumer treats ``None`` as the full all-four
        install/doctor scope (back-compat with pre-v0.1.58 workspaces).
        """
        states_dir = workspace_root / ".dadaia" / "states"
        profile = JsonHarnessProfileStore().read(states_dir)
        return set(profile.harnesses) if profile is not None else None

    # ------------------------------------------------------------------
    # Agent-model policy (v0.1.65 FR4/FR5) — loaded ONCE per install/doctor run
    # ------------------------------------------------------------------

    def _load_agent_policy(
        self, workspace_root: Path, agentic_dir: Path
    ) -> AgentModelPolicyOverlay | None:
        """Load the operator overlay (``None`` when absent ⇒ ``balanced`` defaults).

        Raises the typed ``AgentModelPolicyStoreError`` on an invalid overlay — install
        fails loud BEFORE any projection write (NFR-4); doctor converts it to an ERROR
        line. Valid override targets are the 9 core agents plus the installed packs'
        agents (FR3).
        """
        plugin_names = frozenset(
            self._plugin_agent_stems(agentic_dir, self._installed_plugins(workspace_root))
        )
        return JsonAgentModelPolicyStore(workspace_root, plugin_agent_names=plugin_names).load()

    @staticmethod
    def _resolved_core_models(
        overlay: AgentModelPolicyOverlay | None,
    ) -> dict[str, ResolvedAgentModel]:
        """Resolve the full core roster through the single resolver (FR4)."""
        return {agent: resolve_agent_model(agent, overlay) for agent in CORE_AGENTS}

    def _resolve_pack_agent(
        self, md_path: Path, overlay: AgentModelPolicyOverlay | None
    ) -> ResolvedAgentModel | None:
        """Resolve an installed pack agent: override > pack-provided default (D-5).

        Returns ``None`` when the pack body authors no ``model:`` (defensive — the
        projection then falls back to the legacy verbatim/staged-model path).
        """
        fm = _parse_agent_frontmatter(md_path.read_text(encoding="utf-8"))
        staged_model = str(fm.get("model", "")) or None
        if staged_model is None:
            return None
        agent_name = str(fm.get("name", "")) or md_path.stem
        return resolve_agent_model(agent_name, overlay, pack_default=staged_model)

    # ------------------------------------------------------------------
    # Plugin packs (v0.1.60 FR3) — projection, precedence, doctor
    # ------------------------------------------------------------------

    def _installed_plugins(self, workspace_root: Path) -> tuple[str, ...]:
        """Return the installed plugin-pack names from the ledger (empty when absent).

        An absent ``installed_plugins.json`` ⇒ no packs installed. This is the single
        precedence source read by ``install`` (core projection precedence) and ``doctor``;
        when it is empty EVERY plugin code path is a strict no-op, so the zero-plugin
        install/doctor surface is byte-identical to golden (b).
        """
        states_dir = workspace_root / ".dadaia" / "states"
        ledger = self._plugin_store.read(states_dir)
        return ledger.plugins if ledger is not None else ()

    def _plugin_agent_stems(self, agentic_dir: Path, packs: tuple[str, ...]) -> set[str]:
        """Return the agent-file stems owned by the installed packs (from the staged tree)."""
        stems: set[str] = set()
        for pack in packs:
            for md in (agentic_dir / "plugins" / pack / "agents").glob("*.md"):
                stems.add(md.stem)
        return stems

    def _codex_toml_from_md(
        self, md_path: Path, resolved: ResolvedAgentModel | None = None
    ) -> tuple[str, str] | None:
        """Render an agent md into its ``(agent_name, .codex toml content)`` pair.

        Mirrors ``install_codex_agents`` for a single agent md: parse frontmatter, strip it,
        transform Claude-isms out of the body/description, resolve the ``(model, effort)``
        via :func:`resolve_codex_agent_model` (v0.1.65 FR5: *resolved* policy > staged
        authored ``model:`` > legacy stub default; a CORE agent with neither fails closed
        — F-3), map the Claude model to its Codex id, and render the TOML. Shared by the
        pack-body projection (install) and the core-stub restoration (uninstall, v0.1.63 FR2).
        """
        text = md_path.read_text(encoding="utf-8")
        fm = _parse_agent_frontmatter(text)
        if not fm:
            return None
        agent_name = str(fm.get("name", "")) or md_path.stem
        if text.startswith("---\n"):
            end_idx = text.find("\n---\n", 4)
            body = text[end_idx + 5 :] if end_idx != -1 else text
        else:
            body = text
        body = transform_for_codex(body, agent_name)
        staged_model = str(fm.get("model", "")) or None
        claude_model, reasoning_effort = resolve_codex_agent_model(
            agent_name, staged_model, resolved
        )
        description = fm.get("description")
        codex_description = (
            transform_for_codex(str(description), agent_name) if description else None
        )
        toml_content = _render_codex_agent_toml(
            agent_name,
            map_model(claude_model),
            body,
            description=codex_description,
            claude_model=claude_model,
            reasoning_effort=reasoning_effort,
        )
        return agent_name, toml_content

    def _render_codex_pack_agent(
        self,
        md_path: Path,
        workspace_root: Path,
        force: bool,
        installed: list[str],
        resolved: ResolvedAgentModel | None = None,
    ) -> None:
        """Render a pack agent's ``.codex/agents/<name>.toml`` from its body."""
        rendered = self._codex_toml_from_md(md_path, resolved=resolved)
        if rendered is None:
            return
        agent_name, toml_content = rendered
        write_generated(
            workspace_root / ".codex" / "agents" / f"{agent_name}.toml",
            toml_content,
            force,
            installed,
        )

    def _project_installed_plugins(
        self,
        agentic_dir: Path,
        workspace_root: Path,
        active: set[str],
        force: bool,
        installed: list[str],
        overlay: AgentModelPolicyOverlay | None = None,
    ) -> None:
        """Project every installed pack's agents/skills/rules over the core projections.

        Profile-scoped (Ruling 13): a pack agent lands in a runtime ONLY when that harness is
        in *active*, so a claude-only workspace never gets a ``.codex/`` orphan (AC-15). The
        pack agent body OVERWRITES the projected core stub (ADR-4 stub replacement); because
        this runs AFTER the core projection loop it is the projection-precedence step
        (AC-4 clobber-safety). A no-op when no pack is installed (byte-lock golden (b)).

        v0.1.65 FR5: pack agents render through the same seam as core agents —
        override > pack-provided default (D-5), with the F-6 effort asymmetry
        (``effort:`` omitted when no override supplies one).
        """
        packs = self._installed_plugins(workspace_root)
        if not packs:
            return
        for pack in packs:
            pack_dir = agentic_dir / "plugins" / pack
            if not pack_dir.is_dir():
                continue
            for md in sorted((pack_dir / "agents").glob("*.md")):
                resolved = self._resolve_pack_agent(md, overlay)
                if "claude" in active:
                    if resolved is None:
                        copy_file(
                            md, workspace_root / ".claude" / "agents" / md.name, force, installed
                        )
                    else:
                        write_generated(
                            workspace_root / ".claude" / "agents" / md.name,
                            render_claude_agent(md.read_text(encoding="utf-8"), resolved),
                            force,
                            installed,
                        )
                if "codex" in active:
                    self._render_codex_pack_agent(
                        md, workspace_root, force, installed, resolved=resolved
                    )
            for skill in sorted(self._iter_files(pack_dir / "skills")):
                if skill.name == ".gitkeep":
                    continue
                rel = skill.relative_to(pack_dir / "skills")
                copy_file(skill, workspace_root / ".agents" / "skills" / rel, force, installed)
            if "claude" in active:
                for rule in sorted(self._iter_files(pack_dir / "rules")):
                    if rule.name == ".gitkeep":
                        continue
                    rel = rule.relative_to(pack_dir / "rules")
                    copy_file(rule, workspace_root / ".claude" / "rules" / rel, force, installed)

    def install_plugin(
        self, workspace_root: Path, pack_name: str, force: bool = False
    ) -> list[str]:
        """Enable a plugin pack: record the ledger and project it (profile-scoped).

        Records *pack_name* in ``installed_plugins.json`` via the injected ``PluginStore``
        port (idempotent — a re-install adds nothing) and projects the installed packs from the
        already-staged ``.dadaia/agentic/plugins/`` tree into the profile-scoped runtime
        projections. Re-install is a no-op (hash-compare ``[skip]`` on every file). Staging is
        the caller's responsibility (``dadaia init`` / ``public install`` always stage first);
        when a pack has not been staged, the ledger is still recorded and projection is a
        no-op for that pack.
        """
        agentic_dir = workspace_root / ".dadaia" / "agentic"
        installed: list[str] = []
        states_dir = workspace_root / ".dadaia" / "states"
        store = self._plugin_store
        ledger = store.read(states_dir) or InstalledPlugins.empty()
        store.write(states_dir, ledger.with_added(pack_name))
        profile = self._profile_harnesses(workspace_root)
        active = set(L1_ENTRY_HARNESSES) if profile is None else profile
        overlay = self._load_agent_policy(workspace_root, agentic_dir)
        self._project_installed_plugins(
            agentic_dir, workspace_root, active, force, installed, overlay=overlay
        )
        return installed

    @staticmethod
    def _prune_empty_dirs(start: Path, stop: Path) -> None:
        """Remove now-empty directories from *start* up to (exclusive) *stop*."""
        current = start
        while current != stop and current.is_dir() and not any(current.iterdir()):
            current.rmdir()
            current = current.parent

    def uninstall_plugin(self, workspace_root: Path, pack_name: str) -> list[str]:
        """Disable a plugin pack — the exact inverse of :meth:`install_plugin` (v0.1.63 FR2).

        Enumerates the staged pack tree (``.dadaia/agentic/plugins/<pack>/``) as the removal
        set, profile-scoped exactly like install (ADR-U3): each pack agent's projection is
        re-projected back to the CORE STUB (claude md copy + codex stub toml render); each
        pack-only skill/rule projection is deleted (with now-empty dirs pruned). A drifted
        (hand-edited) projected pack file is restored/removed anyway — the runtime projection
        surface is lib-owned — but never silently: a ``[drift-restored]``/``[drift-removed]``
        line is emitted per file (ADR-U1). An unstaged pack degrades to a ledger-only removal
        with a non-silent line. Ordering is FILES FIRST, LEDGER LAST (ADR-U4): an interrupted
        uninstall leaves the ledger entry present so ``plugin doctor`` still surfaces the
        pack's file state. Idempotent end-to-end.
        """
        agentic_dir = workspace_root / ".dadaia" / "agentic"
        states_dir = workspace_root / ".dadaia" / "states"
        pack_dir = agentic_dir / "plugins" / pack_name
        out: list[str] = []
        profile = self._profile_harnesses(workspace_root)
        active = set(L1_ENTRY_HARNESSES) if profile is None else profile

        if not pack_dir.is_dir():
            out.append(f"[skip] pack '{pack_name}' is not staged — ledger-only removal")
        else:
            overlay = self._load_agent_policy(workspace_root, agentic_dir)
            # Pack agents: restore the core stub over the pack body (profile-scoped).
            for md in sorted((pack_dir / "agents").glob("*.md")):
                stub_src = agentic_dir / "agents" / md.name
                resolved = self._resolve_pack_agent(md, overlay)
                if "claude" in active:
                    dst = workspace_root / ".claude" / "agents" / md.name
                    # The projected pack claude file is the RENDER output (FR5), so
                    # drift is measured against the rendered pack body, not raw bytes.
                    expected_pack = (
                        render_claude_agent(md.read_text(encoding="utf-8"), resolved)
                        if resolved is not None
                        else md.read_text(encoding="utf-8")
                    )
                    if (
                        dst.exists()
                        and dst.read_text(encoding="utf-8") != expected_pack
                        and (not stub_src.exists() or dst.read_bytes() != stub_src.read_bytes())
                    ):
                        out.append(f"[drift-restored] {dst}")
                    if stub_src.exists():
                        copy_file(stub_src, dst, False, out)
                if "codex" in active:
                    dst = workspace_root / ".codex" / "agents" / f"{md.stem}.toml"
                    stub_render = self._codex_toml_from_md(stub_src) if stub_src.exists() else None
                    pack_render = self._codex_toml_from_md(md, resolved=resolved)
                    if dst.exists():
                        current = dst.read_text(encoding="utf-8")
                        if (pack_render is None or current != pack_render[1]) and (
                            stub_render is None or current != stub_render[1]
                        ):
                            out.append(f"[drift-restored] {dst}")
                    if stub_render is not None:
                        write_generated(dst, stub_render[1], False, out)
            # Pack-only skill projections: delete (+ prune now-empty dirs).
            skills_root = workspace_root / ".agents" / "skills"
            for skill in sorted(self._iter_files(pack_dir / "skills")):
                if skill.name == ".gitkeep":
                    continue
                rel = skill.relative_to(pack_dir / "skills")
                dst = skills_root / rel
                if dst.exists():
                    if dst.read_bytes() != skill.read_bytes():
                        out.append(f"[drift-removed] {dst}")
                    dst.unlink()
                    out.append(f"[rm]   {dst}")
                    self._prune_empty_dirs(dst.parent, skills_root)
            # Pack-only rule projections (claude-scoped, mirroring install).
            if "claude" in active:
                rules_root = workspace_root / ".claude" / "rules"
                for rule in sorted(self._iter_files(pack_dir / "rules")):
                    if rule.name == ".gitkeep":
                        continue
                    rel = rule.relative_to(pack_dir / "rules")
                    dst = rules_root / rel
                    if dst.exists():
                        if dst.read_bytes() != rule.read_bytes():
                            out.append(f"[drift-removed] {dst}")
                        dst.unlink()
                        out.append(f"[rm]   {dst}")
                        self._prune_empty_dirs(dst.parent, rules_root)

        # LEDGER LAST (ADR-U4): dropped only after every file operation completed.
        store = self._plugin_store
        ledger = store.read(states_dir) or InstalledPlugins.empty()
        if pack_name in ledger.plugins:
            store.write(states_dir, ledger.with_removed(pack_name))
            out.append(f"[ledger] removed '{pack_name}' from installed_plugins.json")
        return out

    def _doctor_installed_plugins(
        self,
        agentic_dir: Path,
        workspace_root: Path,
        active: set[str],
        overlay: AgentModelPolicyOverlay | None = None,
    ) -> list[str]:
        """Report ``[ok]``/``[drift]``/``[missing]`` per installed-pack projected file.

        A stale or out-of-manifest installed-pack file is never silent (AC-5). A no-op when
        no pack is installed, so the zero-plugin doctor surface stays byte-identical to
        golden (b).
        """
        packs = self._installed_plugins(workspace_root)
        out: list[str] = []
        for pack in packs:
            pack_dir = agentic_dir / "plugins" / pack
            for md in sorted((pack_dir / "agents").glob("*.md")):
                name = md.stem
                if "claude" in active:
                    dst = workspace_root / ".claude" / "agents" / f"{name}.md"
                    label = f"plugin:{pack}:claude/agents/{name}.md"
                    # v0.1.65 FR5/FR7: the installed pack projection is the RENDER
                    # output (override > pack default), so the doctor expectation is
                    # the rendered content, not raw pack bytes.
                    resolved = self._resolve_pack_agent(md, overlay)
                    if resolved is None:
                        out.append(self._compare(md, dst, label))
                    else:
                        expected = render_claude_agent(md.read_text(encoding="utf-8"), resolved)
                        out.append(self._compare_content(expected, dst, label))
                if "codex" in active:
                    toml = workspace_root / ".codex" / "agents" / f"{name}.toml"
                    label = f"plugin:{pack}:codex/agents/{name}.toml"
                    out.append(f"[ok] {label}" if toml.exists() else f"[missing] {label}")
            for skill in sorted(self._iter_files(pack_dir / "skills")):
                if skill.name == ".gitkeep":
                    continue
                rel = skill.relative_to(pack_dir / "skills")
                dst = workspace_root / ".agents" / "skills" / rel
                out.append(
                    self._compare(skill, dst, f"plugin:{pack}:agents/skills/{rel.as_posix()}")
                )
            if "claude" in active:
                for rule in sorted(self._iter_files(pack_dir / "rules")):
                    if rule.name == ".gitkeep":
                        continue
                    rel = rule.relative_to(pack_dir / "rules")
                    dst = workspace_root / ".claude" / "rules" / rel
                    out.append(
                        self._compare(rule, dst, f"plugin:{pack}:claude/rules/{rel.as_posix()}")
                    )
        return out

    def doctor_plugins(self, workspace_root: Path) -> list[str]:
        """Public wrapper: per-installed-pack projected-file doctor lines (profile-scoped)."""
        agentic_dir = workspace_root / ".dadaia" / "agentic"
        profile = self._profile_harnesses(workspace_root)
        active = set(L1_ENTRY_HARNESSES) if profile is None else profile
        try:
            overlay = self._load_agent_policy(workspace_root, agentic_dir)
        except AgentModelPolicyStoreError:
            overlay = None  # `public doctor` reports the invalid overlay separately
        return self._doctor_installed_plugins(agentic_dir, workspace_root, active, overlay)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def stage(self, workspace_root: Path) -> list[str]:
        if not self._public_dir.exists():
            raise PublicAssetError(f"Public assets directory not found: {self._public_dir}")

        agentic_dir = workspace_root / ".dadaia" / "agentic"
        if agentic_dir.exists():
            shutil.rmtree(agentic_dir)
        agentic_dir.mkdir(parents=True, exist_ok=True)

        staged: list[str] = []
        for name in _COPY_DIRS:
            src = self._public_dir / name
            if not src.exists():
                continue
            dst = agentic_dir / name
            if src.is_dir():
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
            staged.append(f"[stage] {dst}")

        # LF-exact, atomic writes: staged JSON is hash-compared by doctor, so it must
        # not pick up Windows CRLF translation (FR-RC2-2).
        manifest_path = agentic_dir / "manifest.json"
        _atomic_write_text(manifest_path, _json_dump(build_manifest(agentic_dir, self._iter_files)))
        staged.append(f"[stage] {manifest_path}")

        index_path = agentic_dir / "agents.index.json"
        _atomic_write_text(index_path, _json_dump(build_agents_index(agentic_dir)))
        staged.append(f"[stage] {index_path}")
        return staged

    def list_all(self) -> dict[str, list[str]]:
        """Return all public asset names grouped by category directory."""
        result: dict[str, list[str]] = {}
        if not self._public_dir.exists():
            return result
        for category_dir in sorted(self._public_dir.iterdir()):
            if not category_dir.is_dir():
                continue
            result[category_dir.name] = [entry.name for entry in sorted(category_dir.iterdir())]
        return result

    def install(
        self,
        workspace_root: Path,
        target: str = "all",
        force: bool = False,
        scope: Literal["all", "repos-only", "workspace-only"] = "all",
        only: str | None = None,
    ) -> list[str]:
        if target not in _VALID_TARGETS:
            valid = ", ".join(sorted(_VALID_TARGETS))
            raise PublicAssetError(
                f"Unsupported public install target '{target}'. Expected one of: {valid}"
            )
        if (
            _is_source_repo_root(workspace_root)
            and os.environ.get("DADAIA_ALLOW_SOURCE_ROOT_PUBLIC_INSTALL") != "1"
        ):
            raise PublicAssetError(
                "Refusing to project public runtime assets into the dadaia-workspace source "
                "repository root. Use a temporary workspace for install smoke tests, or set "
                "DADAIA_ALLOW_SOURCE_ROOT_PUBLIC_INSTALL=1 for an explicit local-only override."
            )

        agentic_dir = workspace_root / ".dadaia" / "agentic"
        installed: list[str] = []
        if not (agentic_dir / "manifest.json").exists():
            installed.extend(self.stage(workspace_root))

        # v0.1.65 FR5: load the agent-model policy ONCE per install run and resolve the
        # core roster through the single resolver (FR4). An invalid overlay raises the
        # typed store error HERE — loud, before any projection write (NFR-4). A missing
        # overlay resolves the `balanced` defaults.
        overlay = self._load_agent_policy(workspace_root, agentic_dir)
        resolved_models = self._resolved_core_models(overlay)

        # Install-all reads the persisted profile (Ruling D, FR3): a claude-only workspace
        # installs only the claude projection. An absent profile ⇒ all-four (back-compat).
        # An explicit --target X always overrides (it never reaches this branch).
        if target == "all":
            profile_harnesses = self._profile_harnesses(workspace_root)
            if profile_harnesses is None:
                targets: tuple[str, ...] = PROJECTION_TARGETS
            else:
                targets = ("agents", *(h for h in L1_ENTRY_HARNESSES if h in profile_harnesses))
        else:
            targets = (target,)
        data_agents_md = agentic_dir / "data" / "AGENTS.md"
        if data_agents_md.exists():
            guard_targets: dict[str, set[Literal["workspace", "repos"]]] = {
                "all": {"workspace", "repos"},
                "workspace-only": {"workspace"},
                "repos-only": {"repos"},
            }
            _install_guardrail_pair(
                data_agents_md,
                workspace_root,
                force,
                installed,
                targets=guard_targets.get(scope, {"workspace", "repos"}),
            )
        elif scope in ("all", "workspace-only"):
            install_agents_md(agentic_dir, workspace_root, force, installed, self._agents_md_source)

        install_dadaia_agents_md(agentic_dir, workspace_root, force, installed)
        install_reports_agents_md(agentic_dir, workspace_root, force, installed)
        install_handoff_agents_md(agentic_dir, workspace_root, force, installed)

        for item in targets:
            if item == "agents":
                if only is None or only == "skills":
                    install_universal_skills(
                        agentic_dir, workspace_root, force, installed, self._iter_files
                    )
            elif item == "claude":
                self._install_claude(
                    agentic_dir,
                    workspace_root,
                    force,
                    installed,
                    only=only,
                    resolved_models=resolved_models,
                )
            elif item == "codex":
                self._install_codex(
                    agentic_dir,
                    workspace_root,
                    force,
                    installed,
                    only=only,
                    resolved_models=resolved_models,
                )
            elif item == "pi":
                self._install_pi(agentic_dir, workspace_root, force, installed, only=only)
            elif item == "kimi-code":
                self._install_kimi_code(agentic_dir, workspace_root, force, installed, only=only)

        # The git-chokepoint scripts are harness-independent: EVERY Layer-1 harness
        # target gets them (v0.2.8 hermes bug kimi-only-init-public-doctor-missing-
        # managed-scripts — a pi-only or kimi-only workspace must also read doctor-green;
        # the doctor's dadaia:scripts/* lines are unconditional, so a per-harness install
        # that skipped them left single-harness workspaces permanently red).
        if target in {"all", *L1_ENTRY_HARNESSES}:
            self._install_scripts(agentic_dir, workspace_root, force, installed)
            # The by-name rule-law corpus is harness-independent for the same reason:
            # the projected root AGENTS.md — which EVERY harness reads — cites rules by
            # name and sends the agent to `.claude/rules/<name>.md`. A codex-only, pi-only
            # or kimi-only workspace used to get those citations with no corpus behind
            # them: the agent follows the pointer, finds nothing, and is told nothing
            # (bug r11-codex-only-reconcile-rule-corpus-missing). `.claude/` here is the
            # canonical HOME of the corpus, not a Claude-runtime projection.
            # `--only <dir>` narrows what a projection writes; it must narrow this too.
            if only is None or only == "rules":
                key = (workspace_root / ".claude" / "rules").relative_to(workspace_root).as_posix()
                ledger = load_projection_ledger(workspace_root)
                ledger[key] = sorted(
                    copy_tree(
                        agentic_dir / "rules",
                        workspace_root / ".claude" / "rules",
                        force,
                        installed,
                        self._iter_files,
                        owned=ledger.get(key),
                    )
                )
                save_projection_ledger(workspace_root, ledger)

        # Projection precedence (FR3, AC-4): after the core projection, overlay any installed
        # pack's real body over its stub — scoped to the harnesses actually being projected —
        # so a routine `public install` never silently reverts an installed pack agent to its
        # stub. A no-op when no pack is installed (byte-lock golden (b)).
        active_harnesses = {item for item in targets if item in L1_ENTRY_HARNESSES}
        self._project_installed_plugins(
            agentic_dir, workspace_root, active_harnesses, force, installed, overlay=overlay
        )

        # Markdown workflow projections were retired in v0.2.3. Remove only their
        # canonical file shape; preserve any unrelated/operator-owned directory content.
        remove_legacy_workflow_projections(workspace_root, installed)

        return installed

    def doctor(self, workspace_root: Path) -> list[str]:
        if not self._public_dir.exists():
            raise PublicAssetError(f"Public assets directory not found: {self._public_dir}")

        agentic_dir = workspace_root / ".dadaia" / "agentic"
        reports: list[str] = []

        for src in self._iter_files(self._public_dir):
            rel = src.relative_to(self._public_dir)
            reports.append(self._compare(src, agentic_dir / rel, f"stage:{rel.as_posix()}"))

        if not (agentic_dir / "manifest.json").exists():
            reports.append("[missing] stage:manifest.json")

        index_path = agentic_dir / "agents.index.json"
        if not index_path.exists():
            reports.append("[missing] stage:agents.index.json")
        else:
            try:
                json.loads(index_path.read_text(encoding="utf-8"))
                reports.append("[ok] stage:agents.index.json")
            except (json.JSONDecodeError, OSError):
                reports.append("[drift] stage:agents.index.json (invalid JSON)")

        # Resolve the profile-scoped active harness set FIRST — it scopes BOTH the
        # runtime_expectations projection loop below (its claude:* projection lines) AND the
        # inline generated-config block further down. Absent profile ⇒ all-four (back-compat,
        # byte-identical to the W1 all-four doctor golden). An out-of-profile runtime whose
        # directory physically EXISTS on disk is never silent (A3): a `[warn]` line from the
        # inline block replaces the scoped drift block so a stale/hand-installed runtime
        # cannot read green-with-zero-lines.
        profile_harnesses = self._profile_harnesses(workspace_root)
        active = set(L1_ENTRY_HARNESSES) if profile_harnesses is None else profile_harnesses
        claude_active = "claude" in active

        # Plugin precedence (FR3): an installed pack's claude agent projection is the PACK
        # body, so its `claude:agents/<name>.md` line is reported by the plugin block below
        # (compared vs the pack body) — skipping it in the core loop avoids a false [drift]
        # against the stub. Empty when no pack is installed ⇒ zero skips (byte-lock golden b).
        installed_packs = self._installed_plugins(workspace_root)
        plugin_agent_stems = self._plugin_agent_stems(agentic_dir, installed_packs)

        # v0.1.65 FR7: load the agent-model policy ONCE per doctor run. An INVALID
        # overlay is a doctor ERROR line (and the render compare below degrades to the
        # `balanced` defaults); a MISSING overlay is silent and resolves the defaults
        # (NFR-4 — missing != invalid).
        overlay: AgentModelPolicyOverlay | None = None
        try:
            overlay = self._load_agent_policy(workspace_root, agentic_dir)
        except AgentModelPolicyStoreError as exc:
            reports.append(f"[drift] agent-model-policy ERROR: {exc}")
        resolved_models = self._resolved_core_models(overlay)

        for expected_src, dst, label, transform in runtime_expectations(
            agentic_dir,
            workspace_root,
            self._iter_files,
            _CLAUDE_DIRS,
            self._agents_md_source,
        ):
            # FR3 boundary completion (W5, T-58-50): runtime_expectations yields the
            # claude:<dir>/* projection expectations unconditionally. For a codex-only /
            # pi-only profile those files are genuinely absent, so an unscoped loop emits
            # `[missing] claude:*` (40 lines) and the doctor false-fails (CLI exit 1) — the
            # exact boundary W3 flagged for W5. Scope the claude:* projection lines to
            # `claude in profile`; the shared agents:skills/*, the AGENTS.md guardrail pairs,
            # and the harness-independent chokepoint dadaia:scripts/* lines stay
            # unconditional. A `.claude/` physically present outside the profile is still
            # surfaced non-silently by the inline block's `[warn]` (A3), so scoping the
            # projection lines here hides no real drift, and the all-four (absent-profile)
            # path is unchanged (claude ∈ all-four ⇒ the loop runs fully → golden byte-lock).
            if not claude_active and label.startswith("claude:"):
                continue
            if (
                plugin_agent_stems
                and label.startswith("claude:agents/")
                and label.endswith(".md")
                and label[len("claude:agents/") : -len(".md")] in plugin_agent_stems
            ):
                continue
            if expected_src is None and transform:
                reports.append(self._compare_content(_CLAUDE_MD_STUB, dst, label))
            elif expected_src is None:
                reports.append(f"[unsupported] {label}")
            elif (
                label.startswith("claude:agents/")
                and label.endswith(".md")
                and expected_src.stem in resolved_models
            ):
                # v0.1.65 FR7/D-6 — THE pinned interception (F-2): non-plugin core
                # `claude:agents/*.md` projections are compared against
                # render(staged generic + resolved policy), never raw staged bytes,
                # so a policy re-render is [ok] and a hand-edit is [drift]. The
                # `stage:agents/*.md` (generic↔generic) lines and every non-agent
                # label stay on the raw `_compare` path above/below — `_compare`
                # itself is never patched. Codex TOML is NOT doctor-byte-compared
                # (F-1): its correctness is the T-65-08 install-time lockstep test.
                expected = render_claude_agent(
                    expected_src.read_text(encoding="utf-8"),
                    resolved_models[expected_src.stem],
                )
                reports.append(self._compare_content(expected, dst, label))
            else:
                reports.append(self._compare(expected_src, dst, label))

        # Consumer-repo guardrail pair (FR9, bug public-doctor-flags-hand-authored-consumer-
        # agents-md): the `repos/<slug>:AGENTS.md`/`:CLAUDE.md` lines flow through the SINGLE
        # provenance-aware authority — a hand-authored (no-banner) consumer reads [foreign] on
        # BOTH paired lines (never [drift]/[missing]), so `public doctor` exits 0 (Ruling 16).
        # `runtime_expectations` no longer emits these lines (no parallel legacy path).
        consumer_source = self._agents_md_source(agentic_dir)
        if consumer_source is not None:
            reports.extend(
                _doctor_consumer_pair_lines(consumer_source, workspace_root, emit_stderr=False)
            )

        # Installed-pack projected-file doctoring (FR3, AC-5): a stale/out-of-manifest
        # installed-pack file is never silent. Empty when no pack is installed ⇒ zero lines
        # (byte-lock golden b).
        reports.extend(self._doctor_installed_plugins(agentic_dir, workspace_root, active, overlay))

        # Profile-scoped inline projection block (FR3). The `active`/`profile_harnesses`
        # resolution above is reused here (claude settings.json / codex hooks+config+rules /
        # the .pi/ tree each gated on membership; a physically-present out-of-profile runtime
        # emits the A3 `[warn]` line).

        # Claude generated-config projection — scoped to `claude in profile`.
        if "claude" in active:
            reports.extend(self._doctor_claude_settings(workspace_root))
            reports.extend(self._doctor_unmanaged_claude_files(agentic_dir, workspace_root))
        elif (workspace_root / ".claude").exists():
            reports.append(_OUT_OF_PROFILE_WARN.format(harness="claude"))

        # Codex generated-config projection — scoped to `codex in profile`.
        if "codex" in active:
            reports.append(
                self._compare_content(
                    _json_dump(_build_codex_hooks(workspace_root)),
                    workspace_root / ".codex" / "hooks.json",
                    "codex:hooks.json",
                )
            )
            for name, content in _build_codex_hook_wrapper_contents().items():
                reports.append(
                    self._compare_content(
                        content,
                        workspace_root / ".dadaia" / "hooks" / name,
                        f"dadaia:hooks/{name}",
                    )
                )
            reports.append(
                self._compare_content(
                    _build_codex_config(agentic_dir),
                    workspace_root / ".codex" / "config.toml",
                    "codex:config.toml",
                )
            )
            reports.append(
                self._compare_content(
                    _render_codex_command_policy_rules(),
                    workspace_root / ".codex" / "rules" / "dadaia-command-policy.rules",
                    "codex:rules/dadaia-command-policy.rules",
                )
            )
        elif (workspace_root / ".codex").exists():
            reports.append(_OUT_OF_PROFILE_WARN.format(harness="codex"))

        # PI (Layer-2 worker harness) — scoped to `pi in profile`.
        pi_staged = agentic_dir / "pi"
        pi_projected = workspace_root / ".pi"
        if "pi" in active:
            for staged in self._iter_files(pi_staged):
                rel = staged.relative_to(pi_staged)
                reports.append(self._compare(staged, pi_projected / rel, f"pi:{rel.as_posix()}"))
        elif pi_projected.exists():
            reports.append(_OUT_OF_PROFILE_WARN.format(harness="pi"))

        # Kimi Code (Layer-1 entry harness, v0.2.8) — scoped to `kimi-code in profile`.
        kimi_staged = agentic_dir / "kimi-code"
        kimi_projected = workspace_root / ".kimi-code"
        if "kimi-code" in active:
            for staged in self._iter_files(kimi_staged):
                rel = staged.relative_to(kimi_staged)
                reports.append(
                    self._compare(staged, kimi_projected / rel, f"kimi-code:{rel.as_posix()}")
                )
            reports.extend(self._check_kimi_user_hooks())
        elif kimi_projected.exists():
            reports.append(_OUT_OF_PROFILE_WARN.format(harness="kimi-code"))

        reports.extend(self._check_managed_script_modes(workspace_root))

        # Harness-independent checks stay unconditional. The rule-corpus check
        # early-returns on an absent .codex/agents; skill/memory/privacy checks read the
        # package public dir, not a runtime projection.
        # Codex-parity drift (D-CX-1..10) + trust-boundary info are codex-specific and MUST
        # gate on `codex in profile` (Q1): check_codex_drift iterates the staged agents and
        # emits `[missing] codex:agents/<name>.toml (D-CX-1)` ×12 for ANY codex-absent tree,
        # which would make a claude-only/pi-only `public doctor` exit 1 (AC-5 unachievable).
        if "codex" in active:
            reports.extend(check_codex_drift(agentic_dir, workspace_root, self._public_dir))
        # Harness-independent: the corpus lives in .claude/rules and is cited from every
        # harness's artifacts, so this must NOT gate on codex (bug
        # rule-corpus-reachability-unchecked-on-claude-path).
        reports.extend(check_rule_corpus_reachable(workspace_root))
        if "codex" in active:
            reports.extend(codex_trust_boundary_info())
        reports.extend(check_agent_skill_refs(self._public_dir))
        reports.extend(check_memory_phase_single_source(self._public_dir))
        reports.extend(self._check_public_privacy())

        try:
            git_result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD", "--", str(self._public_dir)],
                capture_output=True,
                text=True,
                cwd=self._public_dir.parent.parent,
                timeout=5,
            )
            if git_result.returncode == 0:
                for dirty_path in git_result.stdout.splitlines():
                    if dirty_path.strip():
                        reports.append(f"[warn] git-dirty: {dirty_path.strip()}")
            elif git_result.returncode == 128:
                reports.append("[not-applicable] git-dirty check (not a git repo)")
        except FileNotFoundError:
            reports.append("[not-applicable] git-dirty check (git not found)")
        except subprocess.TimeoutExpired:
            reports.append("[warn] git-dirty check timed out")

        for harness_dir in (".agents", ".claude", ".codex", ".kimi-code"):
            legacy_dir = workspace_root / harness_dir / "workflows"
            for legacy in sorted(legacy_dir.glob("*.workflow.md")):
                reports.append(
                    f"[extra] retired-workflow-projection:{legacy.relative_to(workspace_root)}"
                )

        return reports

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _agents_md_source(self, agentic_dir: Path) -> Path | None:
        for path in (agentic_dir / "templates" / "AGENTS.md", agentic_dir / "data" / "AGENTS.md"):
            if path.exists():
                return path
        return None

    def _consumer_repos(self, workspace_root: Path) -> list[Path]:
        return _consumer_repos_for_root(workspace_root)

    def _is_self_repo(self, consumer: Path) -> bool:
        return _is_self_repo(consumer)

    def _install_claude(
        self,
        agentic_dir: Path,
        workspace_root: Path,
        force: bool,
        installed: list[str],
        only: str | None = None,
        resolved_models: dict[str, ResolvedAgentModel] | None = None,
    ) -> None:
        claude_dir = workspace_root / ".claude"
        if resolved_models is None:
            # Direct callers (tests / the panel agents-only re-render) that skip
            # ``install()`` still render through the resolved policy (FR5).
            resolved_models = self._resolved_core_models(
                self._load_agent_policy(workspace_root, agentic_dir)
            )
        dirs = _CLAUDE_DIRS if only is None else tuple(d for d in _CLAUDE_DIRS if d == only)
        # Pruning is scoped to what a previous projection recorded as ours, so an
        # operator-authored rule/agent/skill is never deleted (bug
        # claude-install-prunes-operator-authored-files).
        ledger = load_projection_ledger(workspace_root)
        for name in dirs:
            key = (claude_dir / name).relative_to(workspace_root).as_posix()
            if name == "agents":
                # v0.1.65 FR5: core agents are RENDERED (staged generic body +
                # resolved policy) through the D-6 seam; stubs copy verbatim.
                ledger[key] = sorted(
                    install_claude_agents(
                        agentic_dir,
                        claude_dir,
                        force,
                        installed,
                        self._iter_files,
                        resolved_models,
                        owned=ledger.get(key),
                    )
                )
                continue
            ledger[key] = sorted(
                copy_tree(
                    agentic_dir / name,
                    claude_dir / name,
                    force,
                    installed,
                    self._iter_files,
                    owned=ledger.get(key),
                )
            )
        save_projection_ledger(workspace_root, ledger)
        if only is None:
            self._install_claude_settings(claude_dir, workspace_root, force, installed)

    def install_claude_settings(self, workspace_root: Path) -> list[str]:
        """Public seam for the one canonical ``settings.json`` writer (port method).

        ``init`` used to hand-roll its own writer that registered ctx-inject and nothing
        else, so ``init --skip-assets`` produced a settings.json with no PreToolUse gate
        at all and exited 0 (bug ``init-skip-assets-writes-gateless-claude-settings``).
        Both paths now go through here, so "the two writers agree" is structural instead
        of a claim in a comment.
        """
        installed: list[str] = []
        claude_dir = workspace_root / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)
        self._install_claude_settings(claude_dir, workspace_root, force=False, installed=installed)
        return installed

    def _doctor_unmanaged_claude_files(self, agentic_dir: Path, workspace_root: Path) -> list[str]:
        """Name every ``.claude/`` file that is present but not lib-originated.

        Bug ``claude-doctor-blind-to-unmanaged-projection-files``: doctor only ever walked
        staging→projection, so a file the library does not ship produced no line at all
        and doctor exited 0. ``.claude/rules`` is loaded into every session's context, so
        an unmanaged file there is an instruction-injection surface; after the ownership
        fix it also survives every install. It must be seen.

        These are ``[warn]`` (visible, exit-0) rather than errors on purpose: the
        Workspace Root Law's operator exception makes an operator-authored rule/agent/
        skill legitimate, and a check that turns doctor red on a sanctioned file would
        just teach the operator to stop reading doctor.
        """
        claude_dir = workspace_root / ".claude"
        lines: list[str] = []
        for name in _CLAUDE_DIRS:
            src_dir, dst_dir = agentic_dir / name, claude_dir / name
            if not dst_dir.exists():
                continue
            staged = (
                {src.relative_to(src_dir).as_posix() for src in self._iter_files(src_dir)}
                if src_dir.exists()
                else set()
            )
            for dst in sorted(self._iter_files(dst_dir)):
                rel = dst.relative_to(dst_dir).as_posix()
                if rel not in staged:
                    lines.append(
                        f"[warn] claude:{name}/{rel} unmanaged (not lib-originated; "
                        "it is loaded into session context and install will not remove it)"
                    )
        return lines

    def _install_claude_settings(
        self, claude_dir: Path, workspace_root: Path, force: bool, installed: list[str]
    ) -> None:
        """Fold dadaia's hook wiring into ``.claude/settings.json``, preserving the rest.

        ``settings.json`` belongs to the OPERATOR — Claude Code documents it as the home of
        ``permissions``, ``model``, ``env`` and their own hooks. The previous whole-file
        write erased all of it silently while printing ``[ok]``
        (bug ``claude-install-destroys-operator-settings``). An unparseable file is never
        clobbered: we refuse loudly instead, because overwriting is the one outcome the
        operator can neither detect nor undo.
        """
        dst = claude_dir / "settings.json"
        existing: dict[str, object] | None = None
        if dst.exists():
            try:
                loaded = json.loads(dst.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, ValueError, OSError) as exc:
                raise PublicAssetError(
                    f"{dst} is not readable JSON ({exc}). It carries operator settings, so "
                    "dadaia will not overwrite it. Fix or move the file, then re-run install."
                ) from None
            existing = loaded if isinstance(loaded, dict) else None
        write_generated(
            dst, _json_dump(_merge_claude_settings(existing, workspace_root)), force, installed
        )

    def _doctor_claude_settings(self, workspace_root: Path) -> list[str]:
        """Doctor ONLY the dadaia-owned hook wiring inside ``.claude/settings.json``.

        Comparing the whole file made an operator's own ``permissions`` key read ``[drift]``
        — and the documented remedy for drift is to re-run install, which is exactly what
        used to destroy it.
        """
        label = "claude:settings.json"
        dst = workspace_root / ".claude" / "settings.json"
        if not dst.exists():
            return [f"[missing] {label}"]
        try:
            loaded = json.loads(dst.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError, OSError):
            return [f"[drift] {label} (not readable JSON)"]
        if not isinstance(loaded, dict):
            return [f"[drift] {label} (not a JSON object)"]
        canonical = _build_claude_settings(workspace_root)
        if _dadaia_owned_claude_settings(loaded) != _dadaia_owned_claude_settings(canonical):
            return [f"[drift] {label}"]
        reports = [f"[ok] {label}"]
        # Preserving the operator's hooks must not mean going BLIND to them. Narrowing the
        # comparison to the owned slice (so an operator key is no longer called drift) also
        # silenced a foreign entry added to a dadaia-wired event — a local hook-injection
        # foothold. It is the operator's file, so this is never [drift]; it is surfaced as a
        # non-blocking [warn] naming every foreign command, so "doctor green" cannot hide it.
        foreign = _foreign_claude_hook_commands(loaded, canonical)
        if foreign:
            reports.append(
                f"[warn] {label}: non-dadaia hook command(s) in gated event(s) — "
                + ", ".join(foreign)
            )
        return reports

    def _install_codex(
        self,
        agentic_dir: Path,
        workspace_root: Path,
        force: bool,
        installed: list[str],
        only: str | None = None,
        resolved_models: dict[str, ResolvedAgentModel] | None = None,
    ) -> None:
        codex_dir = workspace_root / ".codex"
        if resolved_models is None:
            resolved_models = self._resolved_core_models(
                self._load_agent_policy(workspace_root, agentic_dir)
            )
        if only is None or only == "rules":
            self._install_codex_rules(agentic_dir, workspace_root, force, installed)
        if only is None or only == "skills":
            install_universal_skills(
                agentic_dir, workspace_root, force, installed, self._iter_files
            )
        if only is None or only == "agents":
            install_codex_agents(
                agentic_dir, workspace_root, force, installed, resolved_models=resolved_models
            )
            install_codex_runtime_adapters(
                self._public_dir, workspace_root, force, installed, copy_file
            )
        if only is None:
            hooks_dir = workspace_root / ".dadaia" / "hooks"
            for name, content in _build_codex_hook_wrapper_contents().items():
                dst = hooks_dir / name
                write_generated(dst, content, force, installed)
                # These wrappers ARE the PreToolUse gate. A silent chmod failure here is a
                # gate that stops firing while install reports success — the same shape as
                # r24-public-install-does-not-repair-kimi-shim-mode, found by sweeping the
                # class rather than waiting for the next report.
                failure = _restore_execute_bit(dst)
                if failure is not None:
                    installed.append(failure)
            write_generated(
                codex_dir / "hooks.json",
                _json_dump(_build_codex_hooks(workspace_root)),
                force,
                installed,
            )
            write_generated(
                codex_dir / "config.toml",
                _build_codex_config(agentic_dir),
                force,
                installed,
            )

    def _install_pi(
        self,
        agentic_dir: Path,
        workspace_root: Path,
        force: bool,
        installed: list[str],
        only: str | None = None,
    ) -> None:
        """Project the staged ``pi/`` tree into ``<workspace_root>/.pi/``.

        The staged ``pi/`` assets (``SYSTEM.md``, ``settings.json`` and the
        ``prompts/`` affordance dir) are plain md/json — a straight hash-compare copy
        with orphan-pruning, idempotent on re-install.

        The PI harness is a Layer-2 worker; its files carry no workspace-specific or
        operator-local values, so the copy is verbatim (no generated config file).
        """
        pi_src = agentic_dir / "pi"
        pi_dst = workspace_root / ".pi"
        if only is None:
            copy_tree(pi_src, pi_dst, force, installed, self._iter_files)
            return
        # `only` filters to a single staged subdirectory (e.g. "prompts").
        if only in _PI_DIRS:
            copy_tree(pi_src / only, pi_dst / only, force, installed, self._iter_files)

    def _install_kimi_code(
        self,
        agentic_dir: Path,
        workspace_root: Path,
        force: bool,
        installed: list[str],
        only: str | None = None,
    ) -> None:
        """Project the staged ``kimi-code/`` tree into ``<workspace_root>/.kimi-code/`` and
        upsert the user-level Kimi hook wiring (v0.2.8).

        The workspace tree (``AGENTS.md``) is a verbatim hash-compare copy like the pi
        projection. The hook *registration* cannot live in the workspace — Kimi Code has
        no project-level config file — so it is upserted into the user-level
        ``$KIMI_CODE_HOME/config.toml`` managed block, and the four workspace-agnostic
        shims are written under ``$KIMI_CODE_HOME/hooks/`` (see
        ``infrastructure/runtime_config.py``).
        """
        kimi_src = agentic_dir / "kimi-code"
        kimi_dst = workspace_root / ".kimi-code"
        if only is None:
            copy_tree(kimi_src, kimi_dst, force, installed, self._iter_files)
            self._install_kimi_user_hooks(force, installed)
            return
        # `only` filters to a single staged subdirectory (none today — _KIMI_DIRS is empty).
        if only in _KIMI_DIRS:
            copy_tree(kimi_src / only, kimi_dst / only, force, installed, self._iter_files)

    def _install_kimi_user_hooks(self, force: bool, installed: list[str]) -> None:
        """Write the kimi shims (chmod 755) and upsert the managed config.toml block."""
        home = kimi_code_home()
        for name, content in kimi_hook_shims().items():
            dst = home / "hooks" / name
            write_generated(dst, content, force, installed)
            failure = _restore_execute_bit(dst)
            if failure is not None:
                installed.append(failure)
        config_path = home / "config.toml"
        existing = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
        updated = upsert_kimi_hooks_block(existing, kimi_hooks_block(home))
        if updated != existing:
            _atomic_write_text(config_path, updated)
            installed.append(f"[ok]   {config_path}")
        else:
            installed.append(f"[skip] {config_path}")

    def _install_scripts(
        self, agentic_dir: Path, workspace_root: Path, force: bool, installed: list[str]
    ) -> None:
        copy_tree(
            agentic_dir / "scripts",
            workspace_root / ".dadaia" / "scripts",
            force,
            installed,
            self._iter_files,
        )
        scripts_dir = workspace_root / ".dadaia" / "scripts"
        if scripts_dir.exists():
            for script in sorted(scripts_dir.glob("*.sh")):
                # The git chokepoints, including the pre-push security-verdict gate. This
                # chmod was unguarded, so one unwritable file aborted the entire install
                # with a traceback instead of naming the file (F-22 class).
                failure = _restore_execute_bit(script)
                if failure is not None:
                    installed.append(failure)

    def _iter_files(self, root: Path) -> Iterable[Path]:
        if not root.exists():
            return ()
        return (
            path
            for path in sorted(root.rglob("*"))
            if path.is_file() and not self._is_ignored_public_asset(path)
        )

    def _is_ignored_public_asset(self, path: Path) -> bool:
        return path.suffix in _PUBLIC_ASSET_IGNORED_SUFFIXES or bool(
            _PUBLIC_ASSET_IGNORED_DIRS.intersection(path.parts)
        )

    def _compare(self, src: Path, dst: Path, label: str) -> str:
        if not dst.exists():
            return f"[missing] {label}"
        if _sha256(src) != _sha256(dst):
            return f"[drift] {label}"
        return f"[ok] {label}"

    def _compare_content(self, expected: str, dst: Path, label: str) -> str:
        if not dst.exists():
            return f"[missing] {label}"
        if dst.read_text(encoding="utf-8") != expected:
            return f"[drift] {label}"
        return f"[ok] {label}"

    def _check_managed_script_modes(self, workspace_root: Path) -> list[str]:
        """Report a git-chokepoint script that git could not execute.

        The ``dadaia:scripts/*`` doctor lines compare CONTENT, so a script stripped of its
        execute bit read ``[ok]`` while git silently could not run it. These are the git
        chokepoints — ``pre-push-ci-gate.sh`` carries the pre-push security-verdict gate and
        the CI preflight — so a mode-only corruption disables an enforcing gate and the
        command whose whole job is to report workspace soundness said nothing.

        The sibling surface has been checked all along: ``codex_doctor`` reports a Codex
        hook wrapper that is not executable. One instance checked and the sibling left out
        is the shape this repository keeps rediscovering; this closes it for the chokepoints.
        """
        if not PLATFORM_HAS_EXECUTE_BIT:
            # Nothing to inspect and nothing to repair: git carries the executable flag in
            # its index here, not in the filesystem. Reporting drift a chmod can never
            # clear turns doctor into a permanent red (bug
            # doctor-reports-unrepairable-exec-bit-drift-on-windows).
            return []
        scripts_dir = workspace_root / ".dadaia" / "scripts"
        if not scripts_dir.is_dir():
            return []
        reports: list[str] = []
        for script in sorted(scripts_dir.glob("*.sh")):
            try:
                executable = bool(script.stat().st_mode & stat.S_IXUSR)
            except OSError as exc:
                reports.append(f"[error] dadaia:scripts/{script.name} mode unreadable: {exc}")
                continue
            if not executable:
                reports.append(
                    f"[drift] dadaia:scripts/{script.name} (not executable) — git cannot "
                    "run this chokepoint; repair with `dadaia public install --target all`"
                )
        return reports

    def _check_kimi_user_hooks(self) -> list[str]:
        """Doctor the user-level kimi wiring: shim currency + managed config block.

        Shims are content-compared against the generated bodies (and must stay
        executable); the config block is compared through the same upsert the
        installer performs, so a missing/stale block reads ``[missing]``/``[drift]``
        and foreign config content outside the markers never false-fails.
        """
        home = kimi_code_home()
        reports: list[str] = []
        for name, content in kimi_hook_shims().items():
            dst = home / "hooks" / name
            label = f"kimi-code:hooks/{name}"
            line = self._compare_content(content, dst, label)
            if line.startswith("[ok]") and PLATFORM_HAS_EXECUTE_BIT and not os.access(dst, os.X_OK):
                # The installer chmods 0o755, so cleared mode bits ARE repairable drift.
                # Intact mode bits with X_OK denied means the MOUNT forbids execution
                # (noexec) — reinstalling can never fix that, so reporting it as drift
                # sent every consumer into a repair loop and failed `reconcile` with
                # rollback_required (bug kimi-hooks-noexec-home-reported-as-repairable-drift).
                if dst.stat().st_mode & stat.S_IXUSR:
                    line = (
                        f"[unsupported] {label} (filesystem mounted noexec — the exec bits "
                        "are set but the mount forbids execution; point KIMI_CODE_HOME at a "
                        "path on an executable filesystem)"
                    )
                else:
                    line = f"[drift] {label} (not executable)"
            reports.append(line)
        config_path = home / "config.toml"
        block_label = "kimi-code:config.toml managed hooks block"
        if not config_path.exists():
            reports.append(f"[missing] {block_label}")
        else:
            existing = config_path.read_text(encoding="utf-8")
            expected = upsert_kimi_hooks_block(existing, kimi_hooks_block(home))
            status = "[ok]" if expected == existing else "[drift]"
            reports.append(f"{status} {block_label}")
        return reports

    def _check_public_privacy(self) -> list[str]:
        """Fail doctor if public distributed assets contain known private identifiers."""
        return _check_public_privacy_fn(
            self._public_dir, self._iter_files, self._is_ignored_public_asset
        )
