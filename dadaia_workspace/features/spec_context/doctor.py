"""DoctorService — the one scan and reaper of the workspace instance (0.4.6 FR3/FR4).

``check()`` reports the context invariants (INV-4/5/6, CTX-URL-1, VENV-1).
``scan()`` is the ONE walk over the instance — one traversal primitive
(``features.spec_context.sweep``) serves both it and ``fix()``, driven by the zone registry
(``core.workspace_layout.DADAIA_ZONES``): root, harness dirs, the ``.dadaia/`` top level,
the closed-canon zones, the TTL zones — every entry gets one finding verdict and one
``WS-<zone>-<verdict>`` code. ``fix()`` consumes the same findings in the fixed order.

Bug class (the six-bug ``.dadaia/`` ledger, workspace-doctor-root4-false-positive-dadaia-hooks
.. dadaia-reconcile-quarantines-sanctioned-references-clone): the doctor kept its own name
lists and disagreed with what init/install create. Nothing here spells a zone name — every
allow set, TTL and canon is a view of the registry.
"""

import fnmatch
import os
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from functools import partial
from pathlib import Path, PurePosixPath

from dadaia_workspace.core import session_store, workspace_layout
from dadaia_workspace.core.doctor_rules import Rule, SectionFinding
from dadaia_workspace.core.harness_registry import (
    HARNESS_PROJECTION_DIRS,
    L1_ENTRY_HARNESSES,
    PROJECTION_TARGETS,
)
from dadaia_workspace.core.kernel_tunables import DADAIA_BIN
from dadaia_workspace.core.models.harness_profile import HarnessProfile
from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.core.platform import PLATFORM
from dadaia_workspace.core.workspace_layout import Zone
from dadaia_workspace.features.spec_context import markers, sweep
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
from dadaia_workspace.infrastructure.json_context_store import JsonContextStore
from dadaia_workspace.infrastructure.json_harness_profile_store import JsonHarnessProfileStore
from dadaia_workspace.infrastructure.json_install_ledger_store import JsonInstallLedgerStore


class FindingVerdict(StrEnum):
    """The classification of one scanned entry; ``canon`` + ``operator`` count as canonical."""

    CANON = "canon"
    OPERATOR = "operator"
    SLOP = "slop"
    EXPIRED = "expired"
    MISSING = "missing"
    #: Held in ``.dadaia/reaped/`` — already off the working tree, awaiting TTL expiry.
    #: Canonical (the reaper has nothing left to take), but NOT scored and always
    #: printed: the operator has to see what was moved while the window is open.
    REAPED = "reaped"


_CANONICAL = frozenset({FindingVerdict.CANON, FindingVerdict.OPERATOR, FindingVerdict.REAPED})

#: The zone the reaper HOLDS what it takes off the working tree. Deletion is reserved to
#: TTL expiry of this zone, so no scan verdict ever deletes anything directly — the shape
#: behind the CRITICAL doctor-ptr-gc-deletes-valid-lock-free-bind.
REAPED_ZONE = "reaped"

#: Directory names that end the repo-tree walk: a nested VCS/venv/dependency tree is
#: never ours to classify and is where the walk's cost would otherwise live.
_REPO_WALK_PRUNED: frozenset[str] = frozenset({".git", ".venv", "node_modules"})


@dataclass(frozen=True)
class Finding:
    """One scanned entry. ``path`` is root-relative at the root and inside the harness dirs,
    ``.dadaia``-relative inside a zone; ``target`` is the absolute path ``fix()`` acts on."""

    code: str
    path: str
    verdict: FindingVerdict
    fixable: bool
    detail: str
    target: Path

    @property
    def canonical(self) -> bool:
        return self.verdict in _CANONICAL

    @property
    def scored(self) -> bool:
        """Whether this entry is one of the entries compliance is measured over.

        A held entry already LEFT the working tree, so it is not part of what the scan
        scores — it is reported (FR6: the operator sees what was moved and how long is
        left to take it back) and counted nowhere. That is the whole rule: a hold is
        neither compliance nor failure, so it drops out of the fraction instead of
        needing a branch in the renderer, the exit rule or the score.
        """
        return self.verdict is not FindingVerdict.REAPED


@dataclass(frozen=True)
class DoctorIssue:
    code: str
    description: str
    fixable: bool


class DoctorService:
    def __init__(
        self,
        context_store: JsonContextStore,
        git_client: GitSubprocessClient,
        workspace_root: Path,
    ) -> None:
        self._store = context_store
        self._git = git_client
        self._workspace_root = workspace_root
        self._dadaia = workspace_root / ".dadaia"
        self._states = self._dadaia / "states"

    def _repos_dir(self) -> Path:
        return self._workspace_root / "repos"

    # ------------------------------------------------------------------
    # check() — the context invariants (unchanged by the zone walk)
    # ------------------------------------------------------------------

    def check_installed_hooks(self) -> list[DoctorIssue]:
        """HOOKS-DRIFT-1: an ALIVE repo's installed git hook differs from the shipped one.

        The git chokepoints are the ONE mechanical backstop that runs outside every
        harness hook (`.dadaia/AGENTS.md`). An installed copy that has drifted — hand-edited,
        never installed, or left behind by an older release — is a chokepoint silently
        enforcing yesterday's contract, and nothing else in the workspace can notice.
        Compared BYTE-WISE against ``public/scripts/``: the installer copies verbatim, so
        any difference at all is drift. A repo that is not a git checkout has no
        ``.git/hooks/`` to drift and is never a finding.
        """
        issues: list[DoctorIssue] = []
        for top in self._alive_repo_tops():
            hooks_dir = top / ".git" / "hooks"
            if not hooks_dir.is_dir():
                continue
            for target, source in workspace_layout.INSTALLED_GIT_HOOKS:
                shipped = workspace_layout.public_scripts_dir() / source
                installed = hooks_dir / target
                try:
                    drifted = installed.read_bytes() != shipped.read_bytes()
                except OSError:
                    drifted = True
                if drifted:
                    rel = top.relative_to(self._workspace_root).as_posix()
                    issues.append(
                        DoctorIssue(
                            code="HOOKS-DRIFT-1",
                            description=(
                                f"{rel}/.git/hooks/{target} differs from the shipped "
                                f"{source} — the chokepoint is enforcing something other "
                                "than what this release ships."
                            ),
                            fixable=False,
                        )
                    )
        return issues

    def _check_venv_health(self) -> list[DoctorIssue]:
        """VENV-1 — the workspace venv exists with an executable ``dadaia`` entrypoint.

        FR-W3-02 (ADR-G4). Windows-safe — the scripts dir / exe suffix come from ``PLATFORM``
        and the exec check uses ``os.access``. Not fixable: rebuilding a venv is an operator
        action (``dadaia init`` / re-bootstrap), never an auto-repair.
        """
        venv_bin = self._dadaia / ".venv" / PLATFORM.venv_scripts_dir
        if not venv_bin.is_dir():
            return [
                DoctorIssue(
                    code="VENV-1",
                    description=(
                        f"Workspace venv missing: '{venv_bin}' does not exist. Workspace "
                        "tooling (dadaia/pip/python -m dadaia_workspace) must run from this "
                        "venv. Re-bootstrap it (e.g. 'dadaia init' or the documented "
                        "venv setup)."
                    ),
                    fixable=False,
                )
            ]
        entry = venv_bin / f"dadaia{PLATFORM.venv_exe_suffix}"
        if not entry.is_file():
            return [
                DoctorIssue(
                    code="VENV-1",
                    description=(
                        f"Workspace venv entrypoint missing: '{entry}' not found. "
                        "Re-bootstrap the workspace venv."
                    ),
                    fixable=False,
                )
            ]
        if not os.access(entry, os.X_OK):
            return [
                DoctorIssue(
                    code="VENV-1",
                    description=(
                        f"Workspace venv entrypoint not executable: '{entry}'. "
                        "Restore the exec bit (chmod +x) or re-bootstrap the venv."
                    ),
                    fixable=False,
                )
            ]
        return []

    def check(self) -> list[DoctorIssue]:
        issues: list[DoctorIssue] = []
        contexts = self._store.list_all()

        # INV-4 (v2): ALIVE context must have repo on disk
        for ctx in contexts:
            if ctx.state == ContextState.ALIVE:
                repo_path = self._repos_dir() / ctx.repo_slug
                if not repo_path.exists():
                    issues.append(
                        DoctorIssue(
                            code="INV-4",
                            description=f"Context '{ctx.name}' is alive but repo '{ctx.repo_slug}' not on disk",
                            fixable=False,
                        )
                    )

        # CTX-URL-1 (T-011-08 / FR-W2-03 d): an ALIVE context with an empty repo_url is
        # un-portable — an export/import + ``context alive`` on another machine would
        # ``git clone ""`` and fail.
        for ctx in contexts:
            if ctx.state == ContextState.ALIVE and not ctx.repo_url:
                issues.append(
                    DoctorIssue(
                        code="CTX-URL-1",
                        description=(
                            f"Context '{ctx.name}' is alive but has an empty repo_url "
                            f"(un-portable). Re-run 'dadaia context alive {ctx.name}' "
                            "while the repo's origin remote is on disk to back-fill it; "
                            "with no such remote, 'dadaia context delete' and "
                            "'dadaia context create --url <url>' re-register it."
                        ),
                        fixable=False,
                    )
                )

        # INV-5 (v2): DEAD context must not have repo on disk
        for ctx in contexts:
            if ctx.state == ContextState.DEAD:
                repo_path = self._repos_dir() / ctx.repo_slug
                if repo_path.exists():
                    issues.append(
                        DoctorIssue(
                            code="INV-5",
                            description=f"Context '{ctx.name}' is dead but repo '{ctx.repo_slug}' is on disk",
                            fixable=True,
                        )
                    )

        # INV-6 (T-045-22): registry-wide slug-ownership uniqueness — report-only,
        # heals nothing (S3-FR9-ruling.md); surfaces a pre-migration collision.
        owners: dict[str, list[str]] = {}
        for ctx in contexts:
            owners.setdefault(ctx.repo_slug, []).append(ctx.name)
            for r in ctx.associated_repos:
                owners.setdefault(r.slug, []).append(ctx.name)
        for slug in sorted(owners):
            names = owners[slug]
            if len(names) > 1:
                issues.append(
                    DoctorIssue(
                        code="INV-6",
                        fixable=False,
                        description=(
                            f"Repo slug '{slug}' is owned by more than one context "
                            f"({', '.join(sorted(names))}). 'repos/<slug>' is a "
                            "namespace every context shares — 'dadaia context dead' "
                            "on any owner would commit, push and delete the others' "
                            "working tree. Remove it from all but one owner "
                            "('dadaia context repo remove') or re-create the context "
                            "with a different slug."
                        ),
                    )
                )

        issues.extend(self._check_venv_health())
        return issues

    # ------------------------------------------------------------------
    # scan() — the one walk
    # ------------------------------------------------------------------

    def scan(self) -> tuple[Finding, ...]:
        """Every entry of the instance, classified, in the fixed FR3 order."""
        globs = self._exception_globs()
        findings: list[Finding] = []
        findings.extend(self._scan_root(globs))
        findings.extend(self._scan_harness_dirs(globs))
        findings.extend(self._scan_dadaia_top())
        findings.extend(self._scan_repo_trees())
        for zone in workspace_layout.zones_with_canon():
            findings.extend(self._scan_canon_zone(zone))
        now = time.time()
        for zone in workspace_layout.zones_with_ttl():
            findings.extend(self._scan_ttl_zone(zone, now))
        return tuple(findings)

    def _contexts(self) -> list[SpecContextProject]:
        """The registered contexts, or NOTHING when the registry cannot be read.

        The store's contract — degrade to inaction, never to deletion — applied at the one
        place both readers share. It matters more now than it did: the reaper runs on
        ``sdd_post_gate``'s throttle, so an unreadable or older-shaped registry must make
        the pass do less, never raise on the write hot path (and never let the INV-5 lane
        act on a half-parsed registry)."""
        try:
            return list(self._store.list_all())
        except (KeyError, OSError, TypeError, ValueError):
            return []

    def _alive_repo_tops(self) -> list[Path]:
        """Every ALIVE registered repo's top — main plus associated — that exists on disk.
        A DEAD context's repo is INV-5's business, not the tree walk's.

        Reads the registry through :meth:`_contexts`, which degrades to inaction."""
        tops: list[Path] = []
        for ctx in self._contexts():
            if ctx.state is not ContextState.ALIVE:
                continue
            slugs = (ctx.repo_slug, *(repo.slug for repo in ctx.associated_repos))
            for slug in slugs:
                path = self._repos_dir() / slug
                if path.is_dir() and path not in tops:
                    tops.append(path)
        return tops

    def _scan_repo_trees(self) -> list[Finding]:
        """The repo-cleanliness walk (`repos/<slug>/AGENTS.md`), one finding per excluded entry.

        Canonical at a repo top is EVERYTHING not on ``REPO_TREE_EXCLUDED`` (Q5): a repo
        working tree carries source and its own artifacts, and an untracked source entry
        is never the doctor's to judge — so only the excluded names are reported, at the
        top AND at any depth, plus a nested ``.dadaia/`` (which corrupts context
        resolution for every tree-walking tool).

        ``_REPO_WALK_PRUNED`` is consulted FIRST: ``.git``, ``.venv`` and
        ``node_modules`` end the walk and are therefore never candidates (FR6). A
        virtualenv dies the moment it is moved — its interpreter paths are absolute —
        and this pass runs unattended.
        """
        excluded = frozenset(workspace_layout.REPO_TREE_EXCLUDED)
        out: list[Finding] = []
        for top in self._alive_repo_tops():
            pending = [top]
            while pending:
                for entry in sweep.walk(pending.pop()):
                    if entry.name in _REPO_WALK_PRUNED:
                        continue
                    if entry.name in excluded:
                        out.append(
                            self._finding(
                                "repos",
                                self._workspace_root,
                                entry,
                                FindingVerdict.SLOP,
                                "(a repo working tree carries source only — repos/<slug>/AGENTS.md)",
                            )
                        )
                        continue
                    if entry.is_dir() and not entry.is_symlink():
                        pending.append(entry)
        return out

    def _exception_globs(self) -> tuple[str, ...]:
        try:
            text = (self._workspace_root / workspace_layout.INSTANCE_EXCEPTIONS).read_text(
                encoding="utf-8"
            )
        except OSError:
            return ()
        return workspace_layout.parse_exception_globs(text)

    def _excepted(self, entry: Path, globs: tuple[str, ...]) -> bool:
        rel = entry.relative_to(self._workspace_root).as_posix()
        return any(fnmatch.fnmatch(entry.name, g) or fnmatch.fnmatch(rel, g) for g in globs)

    @staticmethod
    def _finding(
        zone: str,
        base: Path,
        target: Path,
        verdict: FindingVerdict,
        detail: str,
        *,
        fixable: bool | None = None,
    ) -> Finding:
        return Finding(
            code=f"WS-{zone.lstrip('.')}-{verdict.value}",
            path=target.relative_to(base).as_posix(),
            verdict=verdict,
            fixable=(verdict not in _CANONICAL) if fixable is None else fixable,
            detail=detail,
            target=target,
        )

    def _scan_root(self, globs: tuple[str, ...]) -> list[Finding]:
        out: list[Finding] = []
        for entry in sweep.walk(self._workspace_root):
            allowed = (
                workspace_layout.ROOT_ALLOWED_DIRS
                if entry.is_dir()
                else workspace_layout.ROOT_ALLOWED_FILES
            )
            if entry.name in allowed:
                verdict, detail = FindingVerdict.CANON, ""
            elif self._excepted(entry, globs):
                verdict, detail = FindingVerdict.OPERATOR, "(instance exception)"
            else:
                verdict, detail = FindingVerdict.SLOP, "(not in the root law or the exceptions)"
            out.append(self._finding("root", self._workspace_root, entry, verdict, detail))
        return out

    def _active_harnesses(self) -> tuple[str, ...]:
        """``agents`` always; the L1 harnesses of the persisted profile (absent ⇒ all)."""
        profile = JsonHarnessProfileStore().read(self._states)
        active = L1_ENTRY_HARNESSES if profile is None else profile.harnesses
        return tuple(t for t in PROJECTION_TARGETS if t not in L1_ENTRY_HARNESSES or t in active)

    def _scan_harness_dirs(self, globs: tuple[str, ...]) -> list[Finding]:
        """An entry is canon iff it is a projection target (the install ledger — what
        ``public install`` actually wrote); a directory holding a target is a path, not an
        entry; anything else is operator (exception glob) or slop. No readable ledger ⇒ the
        store's contract (degrade to inaction, never deletion) holds here too: ONE
        non-fixable ``missing`` finding, and no harness-dir entry is classified."""
        ledger = JsonInstallLedgerStore().read(self._states)
        if ledger is None:
            path = JsonInstallLedgerStore.path(self._states)
            detail = "(run dadaia public install)"
            return [
                self._finding(
                    self._states.name,
                    self._dadaia,
                    path,
                    FindingVerdict.MISSING,
                    detail,
                    fixable=False,
                )
            ]
        targets = frozenset(ledger.by_relpath())
        owned_dirs = frozenset(
            parent.as_posix() for rel in targets for parent in PurePosixPath(rel).parents
        )
        out: list[Finding] = []
        for harness in self._active_harnesses():
            root = self._workspace_root / f".{harness}"
            if not root.is_dir():
                continue
            pending = [root]
            while pending:
                directory = pending.pop()
                for entry in sweep.walk(directory):
                    rel = entry.relative_to(self._workspace_root).as_posix()
                    if rel in targets:
                        verdict, detail = FindingVerdict.CANON, ""
                    elif rel in owned_dirs and entry.is_dir() and not entry.is_symlink():
                        pending.append(entry)
                        continue
                    elif self._excepted(entry, globs):
                        verdict, detail = FindingVerdict.OPERATOR, "(instance exception)"
                    else:
                        verdict = FindingVerdict.SLOP
                        detail = "(not a projection target or an exception)"
                    out.append(self._finding(harness, self._workspace_root, entry, verdict, detail))
        return out

    def _scan_dadaia_top(self) -> list[Finding]:
        out: list[Finding] = []
        present: set[str] = set()
        for entry in sweep.walk(self._dadaia):
            if entry.is_dir() and entry.name in workspace_layout.zone_names():
                present.add(entry.name)
                verdict, detail = FindingVerdict.CANON, ""
            elif not entry.is_dir() and entry.name in workspace_layout.DADAIA_ROOT_FILES:
                verdict, detail = FindingVerdict.CANON, ""
            else:
                verdict, detail = FindingVerdict.SLOP, "(not a zone)"
            out.append(self._finding("dadaia", self._dadaia, entry, verdict, detail))
        for zone in workspace_layout.provisioned_zones():
            if zone.name not in present:
                out.append(
                    self._finding(
                        zone.name,
                        self._dadaia,
                        self._dadaia / zone.name,
                        FindingVerdict.MISSING,
                        "(created by --fix)",
                    )
                )
        return out

    def _scan_canon_zone(self, zone: Zone) -> list[Finding]:
        assert zone.canon is not None
        out: list[Finding] = []
        for entry in sweep.walk(self._dadaia / zone.name):
            if any(fnmatch.fnmatch(entry.name, g) for g in zone.canon):
                verdict, detail = FindingVerdict.CANON, ""
            else:
                verdict, detail = FindingVerdict.SLOP, "(outside the closed canon)"
            out.append(self._finding(zone.name, self._dadaia, entry, verdict, detail))
        profile = JsonHarnessProfileStore.path(self._states)
        if profile.parent == self._dadaia / zone.name and not profile.exists():
            detail = "(seeded by --fix from the projection dirs present)"
            out.append(
                self._finding(zone.name, self._dadaia, profile, FindingVerdict.MISSING, detail)
            )
        return out

    def _scan_ttl_zone(self, zone: Zone, now: float) -> list[Finding]:
        out: list[Finding] = []
        self._walk_ttl(zone, self._dadaia / zone.name, now, out, is_zone_root=True)
        return out

    def _walk_ttl(
        self, zone: Zone, directory: Path, now: float, out: list[Finding], *, is_zone_root: bool
    ) -> bool:
        """Append one finding per file (by lstat mtime, symlinks never followed) and per
        directory emptied by expiry; return whether *directory* is entirely expired."""
        assert zone.ttl_seconds is not None
        entries = sweep.walk(directory)
        if not entries:
            mtime = sweep.mtime(directory)
            return not is_zone_root and mtime is not None and now - mtime > zone.ttl_seconds
        all_expired = True
        for entry in entries:
            if entry.is_dir() and not entry.is_symlink():
                if self._walk_ttl(zone, entry, now, out, is_zone_root=False):
                    out.append(
                        self._finding(
                            zone.name,
                            self._dadaia,
                            entry,
                            FindingVerdict.EXPIRED,
                            "(emptied by expiry)",
                        )
                    )
                else:
                    all_expired = False
                continue
            mtime = sweep.mtime(entry)
            if mtime is None:
                continue
            age = now - mtime
            if is_zone_root and entry.name == "AGENTS.md":
                # The zone's own law file is canon by projection, never a TTL candidate
                # (bug public-install-restores-expired-zone-agents-reblocks-preflight).
                verdict, detail = FindingVerdict.CANON, ""
            elif age > zone.ttl_seconds:
                verdict = FindingVerdict.EXPIRED
                days = timedelta(seconds=age).days
                detail = f"(mtime {days}d > ttl {timedelta(seconds=zone.ttl_seconds).days}d)"
            elif zone.name == REAPED_ZONE:
                # Held, not slop and not expired: report where it came from and how long
                # the operator still has to take it back.
                verdict = FindingVerdict.REAPED
                # Days ROUNDED UP: a hold taken a minute ago has its whole window left,
                # and the last day reads "1d left", never "0d left" on a live entry.
                left = -(-int(zone.ttl_seconds - age) // 86_400)
                detail = f"({left}d left)"
            else:
                verdict, detail = FindingVerdict.CANON, ""
            if verdict is not FindingVerdict.EXPIRED:
                all_expired = False
            out.append(self._finding(zone.name, self._dadaia, entry, verdict, detail))
        return all_expired

    # ------------------------------------------------------------------
    # fix() — the one reaper, in the fixed FR4 order
    # ------------------------------------------------------------------

    def fix(self) -> list[str]:
        """The ONE reaper lane: marker reap -> session reap -> migrate -> seed missing ->
        MOVE slop to ``reaped/`` -> reap dead contexts' repos (INV-5) -> delete expired.

        There is no second, smaller lane. ``--expired-only`` used to buy one by stopping
        this method early; now that slop is HELD rather than deleted, the cheap lane and
        the full lane are the same acts, so the parameter is deleted and the CLI flag
        means only what it always should have: which findings the REPORT shows. The
        SessionStart lane and ``sdd_post_gate``'s throttle run exactly this.


        Nothing here deletes a live entry. Slop is MOVED and holds its 7 days in
        ``.dadaia/reaped/<YYYYMMDD>/<workspace-relative-path>``, the clock starting at the
        move; direct deletion is reserved to TTL expiry. That is the structural answer to
        the CRITICAL ``doctor-ptr-gc-deletes-valid-lock-free-bind``: a misclassification
        now costs a week of holding, not the operator's state. Every step on an entry runs
        through the ONE sweep guard: it reports what it did or that it skipped, never
        aborts, and never touches a location outside the workspace."""
        actions: list[str] = []

        # markers.reap_markers is the ONE reaper of spent throttle/sentinel markers.
        for name in markers.reap_markers(
            self._workspace_root, now=datetime.now(tz=UTC).timestamp()
        ):
            actions.append(f"MARKER-GC: deleted stale marker '{name}'")

        # The session-record owner's ONE reaper (core.session_store.reap_stale, F002).
        for sess_id in session_store.reap_stale(self._workspace_root):
            actions.append(f"GRAVEYARD-GC: deleted expired session file '{sess_id}.json'")

        actions.extend(self._migrate_exceptions())

        findings = self.scan()
        for finding in findings:
            if finding.verdict is FindingVerdict.MISSING and finding.fixable:
                actions.extend(
                    sweep.guarded(finding.code, finding.path, partial(self._seed, finding))
                )
        actions.extend(self._reap(findings))
        for ctx in self._contexts():
            repo_path = self._repos_dir() / ctx.repo_slug
            if ctx.state is ContextState.DEAD and repo_path.exists():
                actions.extend(self._reap_dead_repo(ctx, repo_path))
        actions.extend(self._delete(findings, FindingVerdict.EXPIRED))
        return actions

    def _reaped_destination(self, target: Path) -> Path:
        """``.dadaia/reaped/<YYYYMMDD>/<workspace-relative-path>`` — the origin path is the
        record of where the entry came from, so nothing else has to be written down."""
        day = datetime.now(tz=UTC).strftime("%Y%m%d")
        rel = target.relative_to(self._workspace_root)
        return self._dadaia / REAPED_ZONE / day / rel

    def _reap(self, findings: tuple[Finding, ...]) -> list[str]:
        """MOVE every slop entry into the reaped zone. Never deletes."""
        actions: list[str] = []
        for finding in findings:
            if finding.verdict is not FindingVerdict.SLOP:
                continue
            step = partial(
                sweep.move,
                self._workspace_root,
                finding.target,
                self._reaped_destination(finding.target),
                finding.path,
            )
            actions.extend(sweep.guarded(finding.code, finding.path, step))
        return actions

    def _reap_dead_repo(self, ctx: SpecContextProject, repo_path: Path) -> list[str]:
        """INV-5: reap ``repos/<slug>`` only when it resolves to a DIRECT child of
        ``repos/`` — a slug like ``..`` or a symlinked checkout resolves elsewhere and is
        refused (bug import-registers-unvalidated-slugs-that-doctor-fix-inv5-rmtrees) —
        and the context is still DEAD at the moment of the reap. The two liveness
        questions are policy and live here; the filesystem act is the primitive's.

        The leftover is MOVED, like every other reaped entry: a DEAD context whose repo is
        still on disk is exactly the case where an rmtree used to be irreversible."""
        label = f"repos/{ctx.repo_slug}"
        if repo_path.resolve().parent != self._repos_dir().resolve():
            return [f"INV-5: skipped '{label}' (outside repos/)"]
        current = self._store.get(ctx.name)
        if current is None or current.state is not ContextState.DEAD:
            return []
        step = partial(
            sweep.move,
            self._workspace_root,
            repo_path,
            self._reaped_destination(repo_path),
            label,
            note=f" (context {ctx.name})",
        )
        return sweep.guarded("INV-5", label, step)

    def _migrate_exceptions(self) -> list[str]:
        """FR6: ``root_exceptions.txt`` -> ``INSTANCE_EXCEPTIONS`` through the one parser;
        deleted in the release after every consumer has run it."""
        old = self._states / "root_exceptions.txt"
        new = self._workspace_root / workspace_layout.INSTANCE_EXCEPTIONS
        if not old.is_file() or new.exists():
            return []

        def migrate() -> str:
            globs = workspace_layout.parse_exception_globs(old.read_text(encoding="utf-8"))
            new.write_text("".join(f"{g}\n" for g in globs), encoding="utf-8")
            old.unlink()
            return f"migrated '{old.name}' -> '{new.name}' ({len(globs)} globs)"

        return sweep.guarded("EXCEPTIONS-MIGRATION", old.name, migrate)

    def _seed(self, finding: Finding) -> str:
        """A missing zone is a directory; the missing profile is written by the one store
        writer from the L1 harnesses whose projection dir exists at the root (FR8)."""
        if finding.target == JsonHarnessProfileStore.path(self._states):
            present = tuple(
                h
                for h, dirs in HARNESS_PROJECTION_DIRS.items()
                if any((self._workspace_root / d).is_dir() for d in dirs)
            )
            JsonHarnessProfileStore().write(self._states, HarnessProfile.of(present))
        else:
            finding.target.mkdir(parents=True, exist_ok=True)
        return f"created '{finding.path}'"

    def _delete(self, findings: tuple[Finding, ...], verdict: FindingVerdict) -> list[str]:
        actions: list[str] = []
        for finding in findings:
            if finding.verdict is verdict:
                actions.extend(
                    sweep.guarded(
                        finding.code,
                        finding.path,
                        partial(sweep.remove, self._workspace_root, finding.target, finding.path),
                    )
                )
        return actions


def reap(workspace_root: Path) -> list[str]:
    """The reaper lane, composed without the container (P-12).

    ``sdd_post_gate``'s throttle and the SessionStart lane call this: seed what is
    missing, move slop into ``reaped/``, delete what TTL expired. Hooks are sanctioned
    direct importers of a feature and its stores; the composition root is not on the
    write hot path.
    """
    states = workspace_root / ".dadaia" / "states"
    service = DoctorService(JsonContextStore(states), GitSubprocessClient(), workspace_root)
    return service.fix()


# ── the `workspace` section of the one doctor (0.4.7 FR5, T-047-02) ──────────────

SECTION = "workspace"

#: The verdicts that make a run exit 1 — the pre-0.4.7 `dadaia doctor` rule, unchanged.
ERROR_VERDICTS = frozenset({FindingVerdict.SLOP, FindingVerdict.EXPIRED, FindingVerdict.MISSING})


def workspace_rules(
    *, expired_only: bool = False
) -> tuple[Rule[DoctorService, SectionFinding], ...]:
    """This section's contribution to the ONE rule registry.

    Two rules, the service's two existing reads: the context invariants (`check()`,
    always error-class, outside the scored entry set) and the instance walk (`scan()`,
    one finding per entry, carrying its own `canon|operator|slop|expired|missing`
    verdict word — this section never translates into the specs/ledgers
    `error|warning|info` vocabulary, and neither does any renderer).

    ``expired_only`` SCOPES the section to the TTL lane: the invariants are skipped and
    only expired entries are scanned, so the score line reports that lane rather than
    the whole instance.
    """

    def invariants(service: DoctorService) -> list[SectionFinding]:
        if expired_only:
            return []
        return [
            SectionFinding(
                code=issue.code,
                verdict="error",
                message=issue.description,
                canonical=False,
                error=True,
            )
            for issue in service.check()
        ]

    def installed_hooks(service: DoctorService) -> list[SectionFinding]:
        """HOOKS-DRIFT-1 — its own rule because its fix is its own runnable line."""
        if expired_only:
            return []
        return [
            SectionFinding(
                code=issue.code,
                verdict="error",
                message=issue.description,
                canonical=False,
                error=True,
            )
            for issue in service.check_installed_hooks()
        ]

    def entries(service: DoctorService) -> list[SectionFinding]:
        findings = service.scan()
        if expired_only:
            findings = tuple(f for f in findings if f.verdict is FindingVerdict.EXPIRED)
        return [
            SectionFinding(
                code=finding.code,
                verdict=finding.verdict.value,
                message=f"{finding.path}  {finding.detail}",
                canonical=finding.canonical and finding.scored,
                error=finding.verdict in ERROR_VERDICTS,
            )
            for finding in findings
        ]

    return (
        Rule(
            ("WS-INVARIANT",),
            SECTION,
            invariants,
            fix_help=f"{DADAIA_BIN} doctor --fix",
        ),
        Rule(
            ("HOOKS-DRIFT-1",),
            SECTION,
            installed_hooks,
            fix_help=f"{DADAIA_BIN} ci install-hook --force",
        ),
        Rule(
            ("WS-ENTRY",),
            SECTION,
            entries,
            fix_help=f"{DADAIA_BIN} doctor --fix",
        ),
    )
