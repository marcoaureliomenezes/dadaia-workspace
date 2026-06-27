"""Public asset manager — stages package assets and projects them to agent runtimes."""

from __future__ import annotations

import contextlib
import json
import os
import shutil
import subprocess
from collections.abc import Iterable
from pathlib import Path
from typing import Literal

from dadaia_workspace.core.exceptions import PublicAssetError
from dadaia_workspace.infrastructure.bug_reporter import report_doctor_finding
from dadaia_workspace.infrastructure.codex_doctor import (
    check_agent_skill_refs,
    check_codex_drift,
    check_codex_rule_corpus_reachable,
    check_memory_phase_single_source,
    classify_workflows,
    codex_trust_boundary_info,
    dcx1_missing_toml,
    dcx2_config_toml_entries,
    dcx3_workflow_drift,
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
    install_codex_agents,
    install_codex_runtime_adapters,
    install_dadaia_agents_md,
    install_handoff_agents_md,
    install_reports_agents_md,
    install_universal_skills,
    remove_stale_files,
    runtime_expectations,
    validate_workflows,
    write_generated,
)

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
from dadaia_workspace.infrastructure.runtime_transforms.codex_assets import (  # noqa: F401
    _parse_agent_frontmatter,
    _parse_write_allowlist,
    _render_agent_toml_block,
    _render_agents_config_file_blocks,
    _render_agents_into_codex_config,
    _render_codex_agent_toml,
    _render_codex_command_policy_rules,
)
from dadaia_workspace.infrastructure.workspace_guardrail import (  # noqa: F401
    _CLAUDE_MD_STUB,
    _consumer_repos_for_root,
    _doctor_guardrail_pair,
    _install_consumer_repos_guardrail_pair,
    _install_guardrail_pair,
    _install_workspace_guardrail_pair,
    _install_workspace_root_guardrail_pair,
    _is_self_repo,
    _is_source_repo_root,
)


class FileSystemPublicAssetManager:
    def __init__(self) -> None:
        self._public_dir = Path(__file__).parent.parent / "public"

    # ------------------------------------------------------------------
    # Thin delegators (T-017-11) — preserve the historical method surface
    # that tests/consumers call; the logic lives in the extracted modules
    # (install_helpers, codex_doctor, runtime_config, codex_assets).
    # ------------------------------------------------------------------

    def _copy_file(self, src: Path, dst: Path, force: bool, installed: list[str]) -> None:
        copy_file(src, dst, force, installed)

    def _copy_tree(self, src: Path, dst: Path, force: bool, installed: list[str]) -> None:
        copy_tree(src, dst, force, installed, self._iter_files)

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
        install_codex_agents(agentic_dir, workspace_root, force, installed)

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

    def _dcx3_workflow_drift(self, agentic_dir: Path, codex_dir: Path) -> list[str]:
        return dcx3_workflow_drift(agentic_dir, codex_dir)

    def _dcx4_claude_strings(self, codex_dir: Path) -> list[str]:
        return dcx4_claude_strings(codex_dir)

    def _dcx5_empty_developer_instructions(self, codex_dir: Path) -> list[str]:
        return dcx5_empty_developer_instructions(codex_dir)

    def _dcx6_codex_runtime_adapters(self, workspace_root: Path) -> list[str]:
        return dcx6_codex_runtime_adapters(workspace_root, self._public_dir)

    def _classify_workflows(self, agentic_dir: Path) -> list[str]:
        return classify_workflows(agentic_dir)

    def _claude_settings(self, workspace_root: Path) -> dict[str, object]:
        return _build_claude_settings(workspace_root)

    def _codex_config(self, agentic_dir: Path) -> str:
        return _build_codex_config(agentic_dir)

    def _codex_hooks(self, workspace_root: Path) -> dict[str, object]:
        return _build_codex_hooks(workspace_root)

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

        validate_workflows(agentic_dir)

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

        targets = ("agents", "claude", "codex", "pi") if target == "all" else (target,)
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
                self._install_claude(agentic_dir, workspace_root, force, installed, only=only)
            elif item == "codex":
                self._install_codex(agentic_dir, workspace_root, force, installed, only=only)
            elif item == "pi":
                self._install_pi(agentic_dir, workspace_root, force, installed, only=only)

        if target in {"all", "claude", "codex"}:
            self._install_scripts(agentic_dir, workspace_root, force, installed)

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

        for expected_src, dst, label, transform in runtime_expectations(
            agentic_dir,
            workspace_root,
            self._iter_files,
            _CLAUDE_DIRS,
            self._agents_md_source,
        ):
            if expected_src is None and transform:
                reports.append(self._compare_content(_CLAUDE_MD_STUB, dst, label))
            elif expected_src is None:
                reports.append(f"[unsupported] {label}")
            else:
                reports.append(self._compare(expected_src, dst, label))

        reports.append(
            self._compare_content(
                _json_dump(_build_claude_settings(workspace_root)),
                workspace_root / ".claude" / "settings.json",
                "claude:settings.json",
            )
        )
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
        # PI (Layer-2 worker harness): verbatim source↔staging↔projected comparison.
        pi_staged = agentic_dir / "pi"
        pi_projected = workspace_root / ".pi"
        for staged in self._iter_files(pi_staged):
            rel = staged.relative_to(pi_staged)
            reports.append(self._compare(staged, pi_projected / rel, f"pi:{rel.as_posix()}"))

        reports.extend(classify_workflows(agentic_dir))
        reports.extend(check_codex_drift(agentic_dir, workspace_root, self._public_dir))
        reports.extend(check_codex_rule_corpus_reachable(workspace_root))
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

        _PERSIST_PREFIXES = ("[missing]", "[drift]", "[fail]", "[warn]")
        for line in reports:
            stripped = line.strip()
            if any(stripped.startswith(p) for p in _PERSIST_PREFIXES):
                report_doctor_finding(workspace_root, "doctor-public", stripped)

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
    ) -> None:
        claude_dir = workspace_root / ".claude"
        dirs = _CLAUDE_DIRS if only is None else tuple(d for d in _CLAUDE_DIRS if d == only)
        for name in dirs:
            copy_tree(agentic_dir / name, claude_dir / name, force, installed, self._iter_files)
        if only is None:
            write_generated(
                claude_dir / "settings.json",
                _json_dump(_build_claude_settings(workspace_root)),
                force,
                installed,
            )

    def _install_codex(
        self,
        agentic_dir: Path,
        workspace_root: Path,
        force: bool,
        installed: list[str],
        only: str | None = None,
    ) -> None:
        codex_dir = workspace_root / ".codex"
        if only is None or only == "rules":
            self._install_codex_rules(agentic_dir, workspace_root, force, installed)
        if only is None or only == "workflows":
            if force:
                remove_stale_files(
                    agentic_dir / "workflows",
                    codex_dir / "workflows",
                    "*.workflow.md",
                    installed,
                )
            copy_tree(
                agentic_dir / "workflows",
                codex_dir / "workflows",
                force,
                installed,
                self._iter_files,
            )
        if only is None or only == "skills":
            install_universal_skills(
                agentic_dir, workspace_root, force, installed, self._iter_files
            )
        if only is None or only == "agents":
            install_codex_agents(agentic_dir, workspace_root, force, installed)
            install_codex_runtime_adapters(
                self._public_dir, workspace_root, force, installed, copy_file
            )
        if only is None:
            hooks_dir = workspace_root / ".dadaia" / "hooks"
            for name, content in _build_codex_hook_wrapper_contents().items():
                dst = hooks_dir / name
                write_generated(dst, content, force, installed)
                with contextlib.suppress(OSError):
                    dst.chmod(0o755)
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
            for script in scripts_dir.glob("*.sh"):
                script.chmod(0o755)

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

    def _check_public_privacy(self) -> list[str]:
        """Fail doctor if public distributed assets contain known private identifiers."""
        return _check_public_privacy_fn(
            self._public_dir, self._iter_files, self._is_ignored_public_asset
        )
