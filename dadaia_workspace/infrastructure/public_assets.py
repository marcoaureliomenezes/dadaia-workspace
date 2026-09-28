"""Public asset manager — stages package assets and projects them to agent runtimes.

K3 (v0.5.1): install/doctor are now two folds over one ``ProjectionRule`` table
(``infrastructure/projection_rules.py``) — ``install`` writes ``render``, ``doctor``
compares against it. What remains here is genuinely bespoke: staging, plan
resolution, install-ledger reconciliation, and the harness-independent
doctor checks (privacy, entities-derivation).
"""

from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path

from dadaia_workspace.core.atomic_write import atomic_write
from dadaia_workspace.core.exceptions import PublicAssetError
from dadaia_workspace.core.harness_registry import (
    HARNESS_PROJECTION_DIRS,
    HARNESS_RECORDS,
    L1_ENTRY_HARNESSES,
)
from dadaia_workspace.core.model_registry import (
    CORE_AGENTS,
    AgentModelPolicyOverlay,
    AgentModelPolicyStoreError,
    ResolvedAgentModel,
    resolve_agent_model,
)
from dadaia_workspace.core.models.doctor_report import DoctorLine, DoctorStatus, attest
from dadaia_workspace.core.models.install_ledger import InstallLedger, LedgerEntry
from dadaia_workspace.core.workspace_layout import render_registry_tables
from dadaia_workspace.infrastructure.entity_doctor import (
    check_agent_skill_refs,
    check_entities_derivation,
)
from dadaia_workspace.infrastructure.install_plan import InstallPlan
from dadaia_workspace.infrastructure.json_agent_model_policy_store import (
    JsonAgentModelPolicyStore,
)
from dadaia_workspace.infrastructure.json_harness_profile_store import JsonHarnessProfileStore
from dadaia_workspace.infrastructure.json_install_ledger_store import JsonInstallLedgerStore
from dadaia_workspace.infrastructure.privacy_check import (
    check_public_privacy as _check_public_privacy_fn,
)
from dadaia_workspace.infrastructure.projection import (
    Transcript,
    doctor_rules,
    install_rules,
)
from dadaia_workspace.infrastructure.projection_rules import (
    harness_checks,
    projection_rules,
)
from dadaia_workspace.infrastructure.public_assets_common import (
    _COPY_DIRS,
    _entry_digest,
    _json_dump,
    iter_public_files,
)
from dadaia_workspace.infrastructure.workspace_guardrail import _is_source_repo_root

__all__ = [
    "FileSystemPublicAssetManager",
    "InstallPlan",
]


#: A skill script enforces a shipped schema from its OWN copy beside it.
#: ``stage`` copies the file in (never a symlink: it dies on Windows and in a zipped
#: skill; never an import: that is the coupling a self-contained script forbids), so the copy travels with
#: the staged skill folder and is projected and hash-checked with it. One line per
#: (shipped schema, skill script directory) pair.
_SKILL_SCRIPT_SCHEMAS: tuple[tuple[str, str], ...] = (
    ("schemas/bugs/bug-record-v1.schema.json", "skills/dd-bug-resolution/scripts/schemas"),
    ("schemas/backlog/backlog-v1.schema.json", "skills/dd-backlog-definition/scripts/schemas"),
    ("schemas/histo/histo-record-v1.schema.json", "skills/dd-backlog-definition/scripts/schemas"),
    (
        "schemas/releases/release-state-v1.schema.json",
        "skills/dd-release-implementation/scripts/schemas",
    ),
    (
        "schemas/histo/histo-record-v1.schema.json",
        "skills/dd-release-implementation/scripts/schemas",
    ),
    ("schemas/audits/finding-record-v1.schema.json", "skills/dd-audit-project/scripts/schemas"),
    ("schemas/histo/histo-record-v1.schema.json", "skills/dd-audit-project/scripts/schemas"),
)


#: The shared ledger modules each ledger script runs from its OWN copy beside it, the
#: same way (``_ledger.py`` imports ``_privacy.py``, a copy of ``core/redaction.py``,
#: the push gate's own matcher). (package-relative source, ``public/``-relative target).
_SKILL_SCRIPT_SHARED: tuple[tuple[str, str], ...] = tuple(
    (src, f"skills/{skill}/scripts/{name}")
    for skill in (
        "dd-bug-resolution",
        "dd-backlog-definition",
        "dd-audit-project",
        "dd-cli-library",
        "dd-spec-navigator",
        "dd-release-implementation",
    )
    for src, name in (
        ("core/redaction.py", "_privacy.py"),
        ("infrastructure/data/privacy_baseline.json", "privacy_baseline.json"),
        ("public/skills/dd-bug-resolution/scripts/_ledger.py", "_ledger.py"),
    )
    if not src.endswith(f"{skill}/scripts/{name}")
)


def _staged_bytes(src: Path) -> bytes:
    """What ``stage`` writes for the public asset *src* and what ``doctor`` compares the
    staged copy against: every Markdown rule asset with its registry tables rendered,
    every other asset byte for byte."""
    raw = src.read_bytes()
    if src.suffix == ".md":
        return render_registry_tables(raw.decode("utf-8")).encode("utf-8")
    return raw


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
    def _reachable_without_link(path: Path, ws: Path) -> bool:
        """True iff every directory between *ws* and *path* is a real directory.

        A ledgered relpath whose parent became a SYMLINK is no longer the path the
        ledger recorded: following it would unlink a file inside the authored
        ``.agents/`` tree the link points at (bug class
        ``doctor-walks-symlinked-zone-root-into-a-repo-tree``). Such an entry is retired
        from the ledger untouched — the link rule that replaced it is already recorded.
        """
        for parent in path.parents:
            if parent == ws:
                return True
            if parent.is_symlink():
                return False
        return False

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
            for src in iter_public_files(self._public_dir / name):
                dst = agentic_dir / src.relative_to(self._public_dir)
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
            staged.append(f"[stage] {agentic_dir / name}")

        for schema_rel, scripts_rel in _SKILL_SCRIPT_SCHEMAS:
            schema_src = self._public_dir / schema_rel
            if not schema_src.exists():
                continue
            dst = agentic_dir / scripts_rel / Path(schema_rel).name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(schema_src, dst)
            staged.append(f"[stage] {dst}")

        for src_rel, dst_rel in _SKILL_SCRIPT_SHARED:
            if not (self._public_dir.parent / src_rel).exists():
                continue
            dst = agentic_dir / dst_rel
            shutil.copy2(self._public_dir.parent / src_rel, dst)
            staged.append(f"[stage] {dst}")

        for src in self._staged_sources():
            expected = _staged_bytes(src)
            if expected != src.read_bytes():
                dst = agentic_dir / src.relative_to(self._public_dir)
                atomic_write(dst, expected)
                staged.append(f"[render] {dst}")

        # LF-exact, atomic writes: staged JSON is hash-compared by doctor, so it must
        # not pick up Windows CRLF translation (FR-RC2-2).
        from dadaia_workspace.infrastructure.install_helpers import build_manifest

        manifest_path = agentic_dir / "manifest.json"
        atomic_write(manifest_path, _json_dump(build_manifest(agentic_dir, iter_public_files)))
        staged.append(f"[stage] {manifest_path}")
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
        harness: str | None = None,
        force: bool = False,
    ) -> list[str]:
        self._validate_install_harness(harness)
        self._guard_source_root_install(workspace_root)

        agentic_dir = workspace_root / ".dadaia" / "agentic"
        installed: list[str] = []
        if not (agentic_dir / "manifest.json").exists():
            installed.extend(self.stage(workspace_root))

        plan = self._resolve_install_plan(workspace_root, agentic_dir, harness, force)
        rules = projection_rules(plan)
        transcript = install_rules(rules, force=plan.force)
        installed.extend(transcript.render())

        # LEDGER RECONCILIATION (bug retired-lib-asset-leaves-orphan-projection): the
        # desired state is diffed against the RECORD of what a prior install wrote —
        # never against whatever the current source happens to carry, which is blind to
        # a retired family. Full reconciliation (prune) runs on every whole install;
        # `harness add`'s one-harness install merges its entries and never prunes.
        self._reconcile_install_ledger(
            workspace_root, transcript, installed, full=plan.harness is None
        )

        return installed

    @staticmethod
    def _validate_install_harness(harness: str | None) -> None:
        if harness is None or harness in HARNESS_RECORDS:
            return
        valid = ", ".join(sorted(HARNESS_RECORDS))
        raise PublicAssetError(
            f"Unsupported public install harness '{harness}'. Expected one of: {valid}"
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
        harness: str | None,
        force: bool,
    ) -> InstallPlan:
        """Resolve ``install()``'s arguments ONCE (FR6): the single translation point.

        v0.1.65 FR5: the agent-model policy is loaded ONCE per install run and the core
        roster resolved through the single resolver (FR4). An invalid overlay raises the
        typed store error HERE — loud, before any projection write (NFR-4). A missing
        overlay resolves the `balanced` defaults.
        """
        overlay = self._load_agent_policy(workspace_root)
        resolved_models = self._resolved_core_models(overlay)

        # No harness named: project the roster of record — the shared authored set plus
        # every harness registered in the profile (0.4.7 FR2 — `harness add` is the one
        # way in). A named harness is `harness add`'s own scoped projection, never a flag.
        if harness is None:
            profile_harnesses = self._profile_harnesses(workspace_root)
            harness_targets: tuple[str, ...] = (
                "agents",
                *(h for h in L1_ENTRY_HARNESSES if h in profile_harnesses),
            )
        else:
            harness_targets = (harness,)

        active_harnesses = frozenset(item for item in harness_targets if item in L1_ENTRY_HARNESSES)

        return InstallPlan(
            workspace_root=workspace_root,
            agentic_dir=agentic_dir,
            harness=harness,
            force=force,
            harness_targets=harness_targets,
            active_harnesses=active_harnesses,
            overlay=overlay,
            resolved_models=resolved_models,
        )

    def _profile_harnesses(self, workspace_root: Path) -> set[str]:
        """Return the roster of record for *workspace_root*.

        Reads ``.dadaia/states/harness_profile.json`` via the same-layer
        ``JsonHarnessProfileStore`` adapter (infrastructure consuming infrastructure),
        whose ``resolve`` migrates a pre-profile workspace to the harness directories
        physically present at the root — never to the full roster.
        """
        states_dir = workspace_root / ".dadaia" / "states"
        return set(JsonHarnessProfileStore().resolve(states_dir, workspace_root).harnesses)

    # ------------------------------------------------------------------
    # Agent-model policy (v0.1.65 FR4/FR5) — loaded ONCE per install/doctor run
    # ------------------------------------------------------------------

    def _load_agent_policy(self, workspace_root: Path) -> AgentModelPolicyOverlay | None:
        """Load the operator overlay (``None`` when absent ⇒ ``balanced`` defaults).

        Raises the typed ``AgentModelPolicyStoreError`` on an invalid overlay — install
        fails loud BEFORE any projection write (NFR-4); doctor converts it to an ERROR
        line. Valid override targets are the ``CORE_AGENTS``.
        """
        return JsonAgentModelPolicyStore(workspace_root).load()

    @staticmethod
    def _resolved_core_models(
        overlay: AgentModelPolicyOverlay | None,
    ) -> dict[str, ResolvedAgentModel]:
        """Resolve the full core roster through the single resolver (FR4)."""
        return {agent: resolve_agent_model(agent, overlay) for agent in CORE_AGENTS}

    # ------------------------------------------------------------------
    # Ledger reconciliation
    # ------------------------------------------------------------------

    def _reconcile_install_ledger(
        self,
        workspace_root: Path,
        transcript: Transcript,
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

        Paths arrive TYPED only, from the rule table. A path under ``repos/`` a former
        release ledgered is forgotten, never pruned: install owns nothing in a repo.
        """
        states_dir = workspace_root / ".dadaia" / "states"
        ws = workspace_root.resolve()

        current: dict[str, LedgerEntry] = {}

        def _record(candidate: Path, kind: str) -> None:
            try:
                # The PARENT is resolved, never the entry itself: a projected symlink
                # must be ledgered at the path it occupies, not at the path it points
                # at (bug class doctor-walks-symlinked-zone-root-into-a-repo-tree).
                rel = (candidate.parent.resolve() / candidate.name).relative_to(ws)
            except (ValueError, OSError):
                return  # user-level files (e.g. $KIMI_CODE_HOME) are not workspace state
            rel_posix = rel.as_posix()
            if rel_posix.startswith(".dadaia/states/"):
                return  # never ledger the state dir (the ledger itself lives there)
            digest = _entry_digest(candidate)
            if digest is None:
                return
            family = rel.parts[0].lstrip(".") if len(rel.parts) > 1 else "root"
            current[rel_posix] = LedgerEntry(
                relpath=rel_posix, sha256=digest, family=family, kind=kind
            )

        for line in transcript.lines:
            _record(line.path, line.kind)

        previous = self._install_ledger_store.read(states_dir)
        owned = {
            rel: entry
            for rel, entry in (previous.by_relpath() if previous is not None else {}).items()
            if not rel.startswith("repos/")
        }
        merged: dict[str, LedgerEntry] = dict(owned)

        if full and previous is not None:
            for rel_posix, entry in owned.items():
                if rel_posix in current:
                    continue
                path = ws / entry.relpath
                if not self._reachable_without_link(path, ws):
                    merged.pop(rel_posix, None)
                    continue
                digest = _entry_digest(path)
                if digest is None:
                    merged.pop(rel_posix, None)
                    continue
                if digest == entry.sha256:
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

        for src in self._staged_sources():
            rel = src.relative_to(self._public_dir)
            reports.append(self._compare(src, agentic_dir / rel, f"stage:{rel.as_posix()}"))

        if not (agentic_dir / "manifest.json").exists():
            reports.append(DoctorLine(DoctorStatus.MISSING, "stage:manifest.json"))

        # Resolve the profile-scoped active harness set FIRST — absent profile ⇒
        # all-four (back-compat). An out-of-profile runtime whose directory physically
        # EXISTS on disk is never silent (A3): a `[warn]` line replaces the scoped
        # drift block so a stale/hand-installed runtime cannot read green-with-zero-
        # lines.
        active = self._profile_harnesses(workspace_root)

        # v0.1.65 FR7: load the agent-model policy ONCE per doctor run. An INVALID
        # overlay is a doctor ERROR line (and the render compare below degrades to the
        # `balanced` defaults); a MISSING overlay is silent and resolves the defaults
        # (NFR-4 — missing != invalid).
        overlay: AgentModelPolicyOverlay | None = None
        try:
            overlay = self._load_agent_policy(workspace_root)
        except AgentModelPolicyStoreError as exc:
            reports.append(DoctorLine(DoctorStatus.DRIFT, f"agent-model-policy ERROR: {exc}"))
        resolved_models = self._resolved_core_models(overlay)

        # The doctor plan is a whole install over the roster, scoped to the PERSISTED
        # profile — never an operator's scoped --target selection. It is never executed
        # (install_rules is never called against it); it exists only to build the SAME
        # rule table doctor_rules() compares.
        doctor_plan = InstallPlan(
            workspace_root=workspace_root,
            agentic_dir=agentic_dir,
            harness=None,
            force=False,
            harness_targets=("agents", *(h for h in L1_ENTRY_HARNESSES if h in active)),
            active_harnesses=frozenset(active),
            overlay=overlay,
            resolved_models=resolved_models,
        )
        rules = projection_rules(doctor_plan)
        reports.extend(doctor_rules(rules))
        for name in L1_ENTRY_HARNESSES:
            if name in active:
                reports.extend(harness_checks(name, workspace_root))
        # An out-of-profile runtime directory that physically exists is surfaced by a
        # `[warn]` line rather than staying silent (A3).
        for name, rel_dirs in HARNESS_PROJECTION_DIRS.items():
            if name not in active and any((workspace_root / d).exists() for d in rel_dirs):
                reports.append(_out_of_profile_warn(name))

        # Harness-independent checks stay unconditional: they read the package public
        # dir, not a runtime projection.
        reports.extend(check_agent_skill_refs(self._public_dir))
        reports.extend(attest("public-privacy", self._check_public_privacy()))
        reports.extend(attest("entities-derivation", check_entities_derivation(self._public_dir)))

        return reports

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _staged_sources(self) -> Iterable[Path]:
        return (f for name in _COPY_DIRS for f in iter_public_files(self._public_dir / name))

    def _compare(self, src: Path, dst: Path, label: str) -> DoctorLine:
        if not dst.exists():
            return DoctorLine(DoctorStatus.MISSING, f"{label}")
        if _staged_bytes(src) != dst.read_bytes():
            return DoctorLine(DoctorStatus.DRIFT, f"{label}")
        return DoctorLine(DoctorStatus.OK, f"{label}")

    def _check_public_privacy(self) -> list[DoctorLine]:
        """Fail doctor if public distributed assets contain known private identifiers."""
        return _check_public_privacy_fn(self._public_dir, iter_public_files)
