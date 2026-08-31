"""Public asset manager — stages package assets and projects them to agent runtimes.

K3 (v0.5.1): install/doctor are now two folds over one ``ProjectionRule`` table
(``infrastructure/projection_rules.py``) — ``install`` writes ``render``, ``doctor``
compares against it. What remains here is genuinely bespoke: staging, plan
resolution, the consumer-repo guardrail fan-out (N-target, provenance-gated — not a
fixed-destination rule), install-ledger reconciliation, and the harness-independent
doctor checks (privacy, entities-derivation, memory-phase, rule-corpus, git-dirty).
"""

from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Iterable
from pathlib import Path, PurePosixPath
from typing import Literal

from dadaia_workspace.core.agent_model_templates import CORE_AGENTS, resolve_agent_model
from dadaia_workspace.core.atomic_write import atomic_write
from dadaia_workspace.core.exceptions import PublicAssetError
from dadaia_workspace.core.harness_registry import L1_ENTRY_HARNESSES, PROJECTION_TARGETS
from dadaia_workspace.core.models.agent_model_policy import (
    AgentModelPolicyOverlay,
    AgentModelPolicyStoreError,
    ResolvedAgentModel,
)
from dadaia_workspace.core.models.doctor_report import DoctorLine, DoctorStatus, attest
from dadaia_workspace.core.models.install_ledger import InstallLedger, LedgerEntry
from dadaia_workspace.core.workspace_layout import DADAIA_ADDITIVE_PREFIXES
from dadaia_workspace.infrastructure.codex_doctor import (
    check_agent_skill_refs,
    check_codex_rule_corpus_reachable,
    check_entities_derivation,
    check_memory_phase_single_source,
)
from dadaia_workspace.infrastructure.install_helpers import (
    remove_legacy_bind_epoch_state,
    remove_legacy_workflow_projections,
    remove_retired_core_rules,
)
from dadaia_workspace.infrastructure.install_plan import InstallPlan
from dadaia_workspace.infrastructure.json_agent_model_policy_store import (
    JsonAgentModelPolicyStore,
)
from dadaia_workspace.infrastructure.json_harness_profile_store import JsonHarnessProfileStore
from dadaia_workspace.infrastructure.json_install_ledger_store import JsonInstallLedgerStore
from dadaia_workspace.infrastructure.privacy_check import (  # noqa: F401
    _PRIVACY_DENYLIST_ENV,
    _PUBLIC_ASSET_IGNORED_DIRS,
    _PUBLIC_ASSET_IGNORED_SUFFIXES,
    _load_privacy_denylist,
)
from dadaia_workspace.infrastructure.privacy_check import (
    check_public_privacy as _check_public_privacy_fn,
)
from dadaia_workspace.infrastructure.projection import Transcript, doctor_rules, install_rules
from dadaia_workspace.infrastructure.projection_rules import (
    build_harnesses,
    projection_rules,
    prune_stale_codex_tomls,
)
from dadaia_workspace.infrastructure.public_assets_common import (  # noqa: F401
    _CLAUDE_DIRS,
    _COPY_DIRS,
    _SCHEMA_VERSION,
    _VALID_TARGETS,
    OverwritePolicy,
    _json_dump,
    _log_cleanup_error,
    _package_version,
    _sha256,
    _toml_escape,
    is_ignored_public_asset,
    iter_public_files,
)
from dadaia_workspace.infrastructure.runtime_config import codex_config as _build_codex_config
from dadaia_workspace.infrastructure.runtime_transforms.codex_assets import (  # noqa: F401
    _parse_agent_frontmatter,
    _parse_write_allowlist,
)
from dadaia_workspace.infrastructure.workspace_guardrail import (  # noqa: F401
    _CANONICAL_AGENTS_BANNER,
    _CLAUDE_MD_STUB,
    _agents_md_source,
    _carries_canonical_banner,
    _consumer_repos_for_root,
    _doctor_consumer_pair_lines,
    _install_consumer_repos_guardrail_pair,
    _install_guardrail_pair,
    _install_workspace_guardrail_pair,
    _install_workspace_root_guardrail_pair,
    _is_self_repo,
    _is_source_repo_root,
)

__all__ = ["FileSystemPublicAssetManager", "InstallPlan", "OverwritePolicy"]


#: Non-silent doctor line for a runtime whose directory physically exists on disk but is
#: NOT in the persisted harness profile (A3, v0.1.58 FR3). Emitted in place of the scoped
#: drift block so a stale/hand-installed out-of-profile runtime never reads green-with-zero-
#: lines. ``[warn]`` is non-blocking (CLI exit stays 0) but visible.
def _out_of_profile_warn(harness: str) -> DoctorLine:
    return DoctorLine(
        DoctorStatus.WARN, f"{harness}: out-of-profile runtime present (drift unchecked)"
    )


class FileSystemPublicAssetManager:
    def __init__(
        self,
        install_ledger_store: JsonInstallLedgerStore = JsonInstallLedgerStore(),
    ) -> None:
        self._public_dir = Path(__file__).parent.parent / "public"
        self._install_ledger_store = install_ledger_store

    @staticmethod
    def _prune_empty_dirs(start: Path, stop: Path) -> None:
        """Remove now-empty directories from *start* up to (exclusive) *stop*."""
        current = start
        while current != stop and current.is_dir() and not any(current.iterdir()):
            current.rmdir()
            current = current.parent

    def stage(self, workspace_root: Path) -> list[str]:
        import shutil

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
        from dadaia_workspace.infrastructure.install_helpers import (
            build_agents_index,
            build_manifest,
        )

        manifest_path = agentic_dir / "manifest.json"
        atomic_write(manifest_path, _json_dump(build_manifest(agentic_dir, self._iter_files)))
        staged.append(f"[stage] {manifest_path}")

        index_path = agentic_dir / "agents.index.json"
        atomic_write(index_path, _json_dump(build_agents_index(agentic_dir)))
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

    # ------------------------------------------------------------------
    # install() — resolve ONE InstallPlan, build the rule table, write it.
    # ------------------------------------------------------------------

    def install(
        self,
        workspace_root: Path,
        target: str = "all",
        force: bool = False,
        scope: Literal["all", "repos-only", "workspace-only"] = "all",
        only: str | None = None,
    ) -> list[str]:
        self._validate_install_target(target)
        self._guard_source_root_install(workspace_root)

        agentic_dir = workspace_root / ".dadaia" / "agentic"
        installed: list[str] = []
        if not (agentic_dir / "manifest.json").exists():
            installed.extend(self.stage(workspace_root))

        plan = self._resolve_install_plan(
            workspace_root, agentic_dir, target, OverwritePolicy.of(force), scope, only
        )
        harnesses = build_harnesses(self._public_dir)
        rules = projection_rules(plan, harnesses)
        transcript = install_rules(rules, force=plan.overwrite.force)
        installed.extend(transcript.render())

        # Codex per-agent TOML pruning is independent of the rule table (a rule
        # exists only for what SHOULD be there — pruning what should NOT is a
        # separate, unconditional migration, unchanged from the historical
        # `install_codex_agents` behavior).
        if "codex" in plan.harness_targets and plan.only in (None, "agents"):
            expected = frozenset(
                r.dst.name for r in rules if r.harness == "codex" and r.dst.parent.name == "agents"
            )
            prune_stale_codex_tomls(workspace_root / ".codex", expected, installed)

        # DADAIA.md lands via the rule table above; the remaining harness-independent
        # migrations are unconditional cleanup, unchanged.
        remove_retired_core_rules(workspace_root, installed)
        remove_legacy_workflow_projections(workspace_root, installed)
        remove_legacy_bind_epoch_state(workspace_root, installed)

        # Consumer-repo guardrail fan-out (bespoke: N-target discovery + provenance
        # gating, never a fixed-destination rule).
        guardrail_managed: list[Path] = []
        if "repos" in plan.guardrail_targets:
            data_agents_md = agentic_dir / "data" / "AGENTS.md"
            if data_agents_md.is_file():
                guardrail_managed = _install_guardrail_pair(
                    data_agents_md,
                    workspace_root,
                    plan.overwrite.force,
                    installed,
                    targets={"repos"},
                )

        # LEDGER RECONCILIATION (bug retired-lib-asset-leaves-orphan-projection): the
        # desired state is diffed against the RECORD of what a prior install wrote —
        # never against whatever the current source happens to carry, which is blind to
        # a retired family. Full reconciliation (prune) runs only on an all-target,
        # all-scope install; a scoped install merges its entries and never prunes.
        self._reconcile_install_ledger(
            workspace_root,
            transcript,
            guardrail_managed,
            installed,
            full=(plan.target == "all" and plan.scope == "all"),
        )

        return installed

    @staticmethod
    def _validate_install_target(target: str) -> None:
        if target not in _VALID_TARGETS:
            valid = ", ".join(sorted(_VALID_TARGETS))
            raise PublicAssetError(
                f"Unsupported public install target '{target}'. Expected one of: {valid}"
            )

    @staticmethod
    def _guard_source_root_install(workspace_root: Path) -> None:
        if (
            _is_source_repo_root(workspace_root)
            and os.environ.get("DADAIA_ALLOW_SOURCE_ROOT_PUBLIC_INSTALL") != "1"
        ):
            raise PublicAssetError(
                "Refusing to project public runtime assets into the dadaia-workspace source "
                "repository root. Use a temporary workspace for install smoke tests, or set "
                "DADAIA_ALLOW_SOURCE_ROOT_PUBLIC_INSTALL=1 for an explicit local-only override."
            )

    def _resolve_install_plan(
        self,
        workspace_root: Path,
        agentic_dir: Path,
        target: str,
        overwrite: OverwritePolicy,
        scope: Literal["all", "repos-only", "workspace-only"],
        only: str | None,
    ) -> InstallPlan:
        """Resolve ``install()``'s arguments ONCE (FR6): the single translation point.

        v0.1.65 FR5: the agent-model policy is loaded ONCE per install run and the core
        roster resolved through the single resolver (FR4). An invalid overlay raises the
        typed store error HERE — loud, before any projection write (NFR-4). A missing
        overlay resolves the `balanced` defaults.
        """
        overlay = self._load_agent_policy(workspace_root, agentic_dir)
        resolved_models = self._resolved_core_models(overlay)

        # Install-all reads the persisted profile (Ruling D, FR3): a claude-only workspace
        # installs only the claude projection. An absent profile ⇒ all-four (back-compat).
        # An explicit --target X always overrides (it never reaches this branch).
        if target == "all":
            profile_harnesses = self._profile_harnesses(workspace_root)
            if profile_harnesses is None:
                harness_targets: tuple[str, ...] = PROJECTION_TARGETS
            else:
                harness_targets = (
                    "agents",
                    *(h for h in L1_ENTRY_HARNESSES if h in profile_harnesses),
                )
        else:
            harness_targets = (target,)

        active_harnesses = frozenset(item for item in harness_targets if item in L1_ENTRY_HARNESSES)

        return InstallPlan(
            workspace_root=workspace_root,
            agentic_dir=agentic_dir,
            target=target,
            scope=scope,
            only=only,
            overwrite=overwrite,
            guardrail_targets=frozenset(
                {
                    "all": ("workspace", "repos"),
                    "workspace-only": ("workspace",),
                    "repos-only": ("repos",),
                }[scope]
            ),
            harness_targets=harness_targets,
            active_harnesses=active_harnesses,
            overlay=overlay,
            resolved_models=resolved_models,
        )

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
        line. Valid override targets are the 9 core agents.
        """
        del agentic_dir
        return JsonAgentModelPolicyStore(workspace_root).load()

    @staticmethod
    def _resolved_core_models(
        overlay: AgentModelPolicyOverlay | None,
    ) -> dict[str, ResolvedAgentModel]:
        """Resolve the full core roster through the single resolver (FR4)."""
        return {agent: resolve_agent_model(agent, overlay) for agent in CORE_AGENTS}

    def _codex_config(self, agentic_dir: Path) -> str:
        return _build_codex_config(agentic_dir)

    # ------------------------------------------------------------------
    # Ledger reconciliation
    # ------------------------------------------------------------------

    def _reconcile_install_ledger(
        self,
        workspace_root: Path,
        transcript: Transcript,
        extra_managed: list[Path],
        installed: list[str],
        *,
        full: bool,
    ) -> None:
        """Record what this run projected; prune what a PRIOR run projected and the
        library no longer ships.

        Safety invariant (never weakened): a path is pruned only when it (a) appears in
        the previous ledger, (b) is absent from the current projection set, and (c) still
        carries the ledgered sha on disk. An operator-modified orphan is retained and
        surfaced with a ``[warn]``; a missing/corrupt previous ledger bootstraps —
        record everything, prune nothing.

        Paths arrive TYPED only: the rule table via ``transcript.paths()``, the bespoke
        consumer-repo guardrail fan-out via *extra_managed* (its return value). The
        historical two-prefix string re-parse of *installed* is deleted (F006): it
        silently dropped ``[updated]`` restores — a restored consumer AGENTS.md never
        reached the ledger.
        """
        states_dir = workspace_root / ".dadaia" / "states"
        ws = workspace_root.resolve()

        current: dict[str, LedgerEntry] = {}

        def _record(candidate: Path) -> None:
            try:
                rel = candidate.resolve().relative_to(ws)
            except (ValueError, OSError):
                return  # user-level files (e.g. $KIMI_CODE_HOME) are not workspace state
            rel_posix = rel.as_posix()
            if rel_posix.startswith(".dadaia/states/"):
                return  # never ledger the state dir (the ledger itself lives there)
            if not candidate.is_file():
                return
            family = rel.parts[0].lstrip(".") if len(rel.parts) > 1 else "root"
            current[rel_posix] = LedgerEntry(
                relpath=rel_posix, sha256=_sha256(candidate), family=family
            )

        for path in transcript.paths():
            _record(path)

        for path in extra_managed:
            _record(path)

        previous = self._install_ledger_store.read(states_dir)
        merged: dict[str, LedgerEntry] = {}
        if previous is not None:
            merged.update(previous.by_relpath())

        if full and previous is not None:
            for rel_posix, entry in previous.by_relpath().items():
                if rel_posix in current:
                    continue
                path = ws / entry.relpath
                if not path.is_file():
                    merged.pop(rel_posix, None)
                    continue
                if _sha256(path) == entry.sha256:
                    path.unlink()
                    installed.append(f"[prune] {path}")
                    self._prune_empty_dirs(path.parent, ws)
                    merged.pop(rel_posix, None)
                else:
                    installed.append(f"[warn] operator-modified orphan retained: {path}")
                    merged.pop(rel_posix, None)

        merged.update(current)
        self._install_ledger_store.write(
            states_dir,
            InstallLedger.of(sorted(merged.values(), key=lambda e: e.relpath)),
        )

    # ------------------------------------------------------------------
    # doctor() — build the SAME rule table (a full-scope plan) and compare it.
    # ------------------------------------------------------------------

    def doctor(self, workspace_root: Path) -> list[DoctorLine]:
        if not self._public_dir.exists():
            raise PublicAssetError(f"Public assets directory not found: {self._public_dir}")

        agentic_dir = workspace_root / ".dadaia" / "agentic"
        reports: list[DoctorLine] = []

        for src in self._iter_files(self._public_dir):
            rel = src.relative_to(self._public_dir)
            reports.append(self._compare(src, agentic_dir / rel, f"stage:{rel.as_posix()}"))

        if not (agentic_dir / "manifest.json").exists():
            reports.append(DoctorLine(DoctorStatus.MISSING, "stage:manifest.json"))

        index_path = agentic_dir / "agents.index.json"
        if not index_path.exists():
            reports.append(DoctorLine(DoctorStatus.MISSING, "stage:agents.index.json"))
        else:
            try:
                json.loads(index_path.read_text(encoding="utf-8"))
                reports.append(DoctorLine(DoctorStatus.OK, "stage:agents.index.json"))
            except (json.JSONDecodeError, OSError):
                reports.append(
                    DoctorLine(DoctorStatus.DRIFT, "stage:agents.index.json (invalid JSON)")
                )

        # Resolve the profile-scoped active harness set FIRST — absent profile ⇒
        # all-four (back-compat). An out-of-profile runtime whose directory physically
        # EXISTS on disk is never silent (A3): a `[warn]` line replaces the scoped
        # drift block so a stale/hand-installed runtime cannot read green-with-zero-
        # lines.
        profile_harnesses = self._profile_harnesses(workspace_root)
        active = set(L1_ENTRY_HARNESSES) if profile_harnesses is None else profile_harnesses

        # v0.1.65 FR7: load the agent-model policy ONCE per doctor run. An INVALID
        # overlay is a doctor ERROR line (and the render compare below degrades to the
        # `balanced` defaults); a MISSING overlay is silent and resolves the defaults
        # (NFR-4 — missing != invalid).
        overlay: AgentModelPolicyOverlay | None = None
        try:
            overlay = self._load_agent_policy(workspace_root, agentic_dir)
        except AgentModelPolicyStoreError as exc:
            reports.append(DoctorLine(DoctorStatus.DRIFT, f"agent-model-policy ERROR: {exc}"))
        resolved_models = self._resolved_core_models(overlay)

        # The doctor plan is "install(target=all, scope=all)" scoped to the PERSISTED
        # profile — never an operator's scoped --target selection. It is never executed
        # (install_rules is never called against it); it exists only to build the SAME
        # rule table doctor_rules() compares.
        doctor_plan = InstallPlan(
            workspace_root=workspace_root,
            agentic_dir=agentic_dir,
            target="all",
            scope="all",
            only=None,
            overwrite=OverwritePolicy.PRESERVE,
            guardrail_targets=frozenset({"workspace", "repos"}),
            harness_targets=("agents", *(h for h in L1_ENTRY_HARNESSES if h in active)),
            active_harnesses=frozenset(active),
            overlay=overlay,
            resolved_models=resolved_models,
        )
        harnesses = build_harnesses(self._public_dir)
        rules = projection_rules(doctor_plan, harnesses)
        reports.extend(doctor_rules(rules))
        for name in L1_ENTRY_HARNESSES:
            if name in active:
                reports.extend(harnesses[name].checks(workspace_root))
        # An out-of-profile runtime directory that physically exists is surfaced by a
        # `[warn]` line rather than staying silent (A3).
        harness_dirs = {"claude": ".claude", "codex": ".codex", "kimi-code": ".kimi-code"}
        for name, rel_dir in harness_dirs.items():
            if name not in active and (workspace_root / rel_dir).exists():
                reports.append(_out_of_profile_warn(name))

        # Consumer-repo guardrail pair (FR9, bug public-doctor-flags-hand-authored-consumer-
        # agents-md): the `repos/<slug>:AGENTS.md`/`:CLAUDE.md` lines flow through the SINGLE
        # provenance-aware authority — a hand-authored (no-banner) consumer reads [foreign] on
        # BOTH paired lines (never [drift]/[missing]), so `public doctor` exits 0 (Ruling 16).
        consumer_source = self._agents_md_source(agentic_dir)
        if consumer_source is not None:
            reports.extend(
                _doctor_consumer_pair_lines(consumer_source, workspace_root, emit_stderr=False)
            )

        # Harness-independent checks stay unconditional. The rule-corpus check
        # early-returns on an absent .codex/agents; skill/memory/privacy checks read the
        # package public dir, not a runtime projection. `rule-corpus` stays a TOP-LEVEL,
        # unconditional attestation (never gated on codex-in-profile — ATTESTING_CHECK_IDS
        # must never vanish silently for a codex-absent profile); `trust-boundary` stays
        # gated (moved into CodexHarness.checks() above, matching the historical guard).
        reports.extend(attest("rule-corpus", check_codex_rule_corpus_reachable(workspace_root)))
        reports.extend(check_agent_skill_refs(self._public_dir))
        reports.extend(check_memory_phase_single_source(self._public_dir))
        reports.extend(attest("public-privacy", self._check_public_privacy()))
        reports.extend(attest("entities-derivation", check_entities_derivation(self._public_dir)))
        reports.extend(
            attest("foreign-projections", self._check_foreign_projections(workspace_root))
        )

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
                        reports.append(
                            DoctorLine(DoctorStatus.WARN, f"git-dirty: {dirty_path.strip()}")
                        )
            elif git_result.returncode == 128:
                reports.append(
                    DoctorLine(DoctorStatus.NOT_APPLICABLE, "git-dirty check (not a git repo)")
                )
        except FileNotFoundError:
            reports.append(
                DoctorLine(DoctorStatus.NOT_APPLICABLE, "git-dirty check (git not found)")
            )
        except subprocess.TimeoutExpired:
            reports.append(DoctorLine(DoctorStatus.WARN, "git-dirty check timed out"))

        for harness_dir in (".agents", ".claude", ".codex", ".kimi-code"):
            legacy_dir = workspace_root / harness_dir / "workflows"
            for legacy in sorted(legacy_dir.glob("*.workflow.md")):
                reports.append(
                    DoctorLine(
                        DoctorStatus.EXTRA,
                        f"retired-workflow-projection:{legacy.relative_to(workspace_root)}",
                    )
                )

        return reports

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _agents_md_source(self, agentic_dir: Path) -> Path | None:
        return _agents_md_source(agentic_dir)

    def _consumer_repos(self, workspace_root: Path) -> list[Path]:
        return _consumer_repos_for_root(workspace_root)

    def _is_self_repo(self, consumer: Path) -> bool:
        return _is_self_repo(consumer)

    def _iter_files(self, root: Path) -> Iterable[Path]:
        return iter_public_files(root)

    def _is_ignored_public_asset(self, path: Path) -> bool:
        return is_ignored_public_asset(path)

    def _compare(self, src: Path, dst: Path, label: str) -> DoctorLine:
        if not dst.exists():
            return DoctorLine(DoctorStatus.MISSING, f"{label}")
        if _sha256(src) != _sha256(dst):
            return DoctorLine(DoctorStatus.DRIFT, f"{label}")
        return DoctorLine(DoctorStatus.OK, f"{label}")

    def _compare_content(self, expected: str, dst: Path, label: str) -> DoctorLine:
        if not dst.exists():
            return DoctorLine(DoctorStatus.MISSING, f"{label}")
        if dst.read_text(encoding="utf-8") != expected:
            return DoctorLine(DoctorStatus.DRIFT, f"{label}")
        return DoctorLine(DoctorStatus.OK, f"{label}")

    def _check_public_privacy(self) -> list[DoctorLine]:
        """Fail doctor if public distributed assets contain known private identifiers."""
        return _check_public_privacy_fn(
            self._public_dir, self._iter_files, self._is_ignored_public_asset
        )

    def _check_foreign_projections(self, workspace_root: Path) -> list[DoctorLine]:
        """Surface unmanaged files inside lib-managed projection dirs (read-only).

        Bug ``claude-doctor-blind-to-unmanaged-projection-files``: an extra file in
        ``.claude/rules/`` produced zero doctor lines. This is the install-ledger
        reconciliation run READ-ONLY — no second scanner, no allowlist: a managed dir is
        exactly a directory the ledger owns a file in (so an operator-created skill dir
        is naturally out of scope), and a file there the ledger does not own reads
        ``[foreign]`` — visible but non-blocking (Ruling 16: operator authorship is
        legitimate). No ledger ⇒ no authority to scan against ⇒ empty universe (``attest``
        stamps ``[not-applicable]``).
        """
        states_dir = workspace_root / ".dadaia" / "states"
        ledger = self._install_ledger_store.read(states_dir)
        if ledger is None:
            return []
        owned = ledger.by_relpath()
        managed_dirs = sorted(
            {
                parent
                for rel in owned
                if (parent := PurePosixPath(rel).parent.as_posix()) != "."
                and not any(f"{parent}/".startswith(p) for p in DADAIA_ADDITIVE_PREFIXES)
            }
        )
        lines: list[DoctorLine] = []
        for rel_dir in managed_dirs:
            dir_path = workspace_root / rel_dir
            if not dir_path.is_dir():
                continue
            for child in sorted(dir_path.iterdir()):
                if not child.is_file():
                    continue
                rel = f"{rel_dir}/{child.name}"
                if rel not in owned:
                    lines.append(
                        DoctorLine(
                            DoctorStatus.FOREIGN, f"{rel} — not lib-managed (operator file kept)"
                        )
                    )
        if not lines:
            lines.append(DoctorLine(DoctorStatus.OK, "ledger:foreign-scan (managed dirs clean)"))
        return lines
