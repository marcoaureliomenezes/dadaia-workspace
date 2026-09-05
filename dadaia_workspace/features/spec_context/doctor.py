"""DoctorService — the one scan and reaper of the workspace instance (0.4.6 FR3/FR4).

``check()`` reports the context invariants (INV-4/5/6, CTX-URL-1, VENV-1, PRESENCE-GC).
``scan()`` is the ONE walk over the instance, driven by the zone registry
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
import shutil
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from functools import partial
from pathlib import Path, PurePosixPath

from dadaia_workspace.core import session_store, workspace_layout
from dadaia_workspace.core.harness_registry import L1_ENTRY_HARNESSES, PROJECTION_TARGETS
from dadaia_workspace.core.models.harness_profile import HarnessProfile
from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.core.platform import PLATFORM
from dadaia_workspace.core.workspace_layout import Creator, Zone
from dadaia_workspace.features.spec_context import presence
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


_CANONICAL = frozenset({FindingVerdict.CANON, FindingVerdict.OPERATOR})


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


@dataclass(frozen=True)
class Compliance:
    canonical: int
    total: int
    percent: int


def compliance(findings: tuple[Finding, ...]) -> Compliance:
    """The score line's numbers: canon + operator over every classified entry."""
    total = len(findings)
    canonical = sum(1 for f in findings if f.canonical)
    return Compliance(canonical, total, round(100 * canonical / total) if total else 100)


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

    def _check_presence_gc(self) -> list[DoctorIssue]:
        """PRESENCE-GC: report stale/corrupt advisory presence records (FR7). Read-only —
        the ONLY reclamation authority is presence.gc(), called by fix(); the same
        read-only predicate keeps check and fix from ever disagreeing."""
        issues: list[DoctorIssue] = []
        for ref in presence.stale_records(self._workspace_root):
            issues.append(
                DoctorIssue(
                    code="PRESENCE-GC",
                    description=(
                        f"[stale-presence] context '{ref.context}': advisory presence record "
                        f"for session '{ref.session_id}' is stale or corrupt — safe to reclaim. "
                        "Run 'dadaia doctor --fix' to garbage-collect it."
                    ),
                    fixable=True,
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
                            "(un-portable). Run 'dadaia context update "
                            f"{ctx.name} --url <url>' to set it, or re-run "
                            f"'dadaia context alive {ctx.name}' while the repo's origin "
                            "remote is on disk to back-fill it automatically."
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

        issues.extend(self._check_presence_gc())
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
        for zone in workspace_layout.zones_with_canon():
            findings.extend(self._scan_canon_zone(zone))
        now = time.time()
        for zone in workspace_layout.zones_with_ttl():
            findings.extend(self._scan_ttl_zone(zone, now))
        return tuple(findings)

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

    @staticmethod
    def _entries(directory: Path) -> list[Path]:
        """A root that is itself a symlink is never walked — the read side of ``_remove``'s
        "a symlink is unlinked, never followed"; ``iterdir`` would follow it and every entry of
        the target would pass the per-entry guard, its parent being inside the workspace."""
        if directory.is_symlink():
            return []
        try:
            return sorted(directory.iterdir())
        except OSError:
            return []

    def _scan_root(self, globs: tuple[str, ...]) -> list[Finding]:
        out: list[Finding] = []
        for entry in self._entries(self._workspace_root):
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
                for entry in self._entries(directory):
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
        for entry in self._entries(self._dadaia):
            if entry.is_dir() and entry.name in workspace_layout.zone_names():
                present.add(entry.name)
                verdict, detail = FindingVerdict.CANON, ""
            elif not entry.is_dir() and entry.name in workspace_layout.DADAIA_ROOT_FILES:
                verdict, detail = FindingVerdict.CANON, ""
            else:
                verdict, detail = FindingVerdict.SLOP, "(not a zone)"
            out.append(self._finding("dadaia", self._dadaia, entry, verdict, detail))
        for zone in workspace_layout.walked_zones():
            if zone.creator in (Creator.INIT, Creator.INSTALL) and zone.name not in present:
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
        for entry in self._entries(self._dadaia / zone.name):
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
        entries = self._entries(directory)
        if not entries:
            mtime = self._mtime(directory)
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
            mtime = self._mtime(entry)
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
            else:
                verdict, detail = FindingVerdict.CANON, ""
            if verdict is not FindingVerdict.EXPIRED:
                all_expired = False
            out.append(self._finding(zone.name, self._dadaia, entry, verdict, detail))
        return all_expired

    @staticmethod
    def _mtime(path: Path) -> float | None:
        """``lstat`` mtime, or ``None`` for an entry that vanished between ``iterdir`` and
        ``lstat`` — absent, never an exception (bug
        doctor-scan-raises-when-a-ttl-entry-vanishes-mid-walk)."""
        try:
            return path.lstat().st_mtime
        except OSError:
            return None

    # ------------------------------------------------------------------
    # fix() — the one reaper, in the fixed FR4 order
    # ------------------------------------------------------------------

    def fix(self, *, expired_only: bool = False) -> list[str]:
        """presence.gc -> session reap -> migrate -> seed missing -> delete expired -> [stop]
        -> delete slop -> remove dead contexts' repos (INV-5). Every step on an entry runs
        through ``_guarded``: it reports what it did or that it skipped, never aborts."""
        actions: list[str] = []

        # presence.gc() is the ONE reaper of stale presence records, throttle/sentinel
        # markers and now-empty presence context dirs (release 0.5.1 K2).
        gc_report = presence.gc(self._workspace_root, now=datetime.now(tz=UTC), own_session_id="")
        for key in gc_report.presence:
            actions.append(f"PRESENCE-GC: deleted stale presence record '{key}'")
        for name in gc_report.markers:
            actions.append(f"PRESENCE-GC: deleted stale marker '{name}'")
        for name in gc_report.empty_context_dirs:
            actions.append(f"PRESENCE-GC: removed empty presence context dir '{name}'")

        # The session-record owner's ONE reaper (core.session_store.reap_stale, F002).
        for sess_id in session_store.reap_stale(self._workspace_root):
            actions.append(f"GRAVEYARD-GC: deleted expired session file '{sess_id}.json'")

        actions.extend(self._migrate_exceptions())

        findings = self.scan()
        for finding in findings:
            if finding.verdict is FindingVerdict.MISSING and finding.fixable:
                actions.extend(
                    self._guarded(finding.code, finding.path, partial(self._seed, finding))
                )
        actions.extend(self._delete(findings, FindingVerdict.EXPIRED))
        if expired_only:
            return actions
        actions.extend(self._delete(findings, FindingVerdict.SLOP))

        for ctx in self._store.list_all():
            repo_path = self._repos_dir() / ctx.repo_slug
            if ctx.state is ContextState.DEAD and repo_path.exists():
                step = partial(self._remove_dead_repo, ctx, repo_path)
                actions.extend(self._guarded("INV-5", f"repos/{ctx.repo_slug}", step))
        return actions

    def _remove_dead_repo(self, ctx: SpecContextProject, repo_path: Path) -> str | None:
        """INV-5: rmtree ``repos/<slug>`` only when it resolves to a direct child of ``repos/``
        — a slug like ``..`` or a symlinked checkout resolves elsewhere and is refused (bug
        import-registers-unvalidated-slugs-that-doctor-fix-inv5-rmtrees) — and the context
        is still DEAD at the moment of deletion."""
        if repo_path.resolve().parent != self._repos_dir().resolve():
            return f"skipped 'repos/{ctx.repo_slug}' (outside repos/)"
        current = self._store.get(ctx.name)
        if current is None or current.state is not ContextState.DEAD:
            return None
        shutil.rmtree(repo_path)
        return f"removed stale repo '{ctx.repo_slug}' for dead context '{ctx.name}'"

    @staticmethod
    def _guarded(code: str, path: str, step: Callable[[], str | None]) -> list[str]:
        """One action line per step — what the step reports, or ``skipped`` with the errno
        when the process cannot perform it; the pass never aborts (bug
        doctor-fix-aborts-whole-pass-on-first-undeletable-entry, every fix step alike)."""
        try:
            done = step()
        except OSError as exc:
            return [f"{code}: skipped '{path}' (errno {exc.errno}: {exc.strerror})"]
        return [] if done is None else [f"{code}: {done}"]

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

        return self._guarded("EXCEPTIONS-MIGRATION", old.name, migrate)

    def _seed(self, finding: Finding) -> str:
        """A missing zone is a directory; the missing profile is written by the one store
        writer from the L1 harnesses whose projection dir exists at the root (FR8)."""
        if finding.target == JsonHarnessProfileStore.path(self._states):
            present = tuple(
                h for h in L1_ENTRY_HARNESSES if (self._workspace_root / f".{h}").is_dir()
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
                    self._guarded(finding.code, finding.path, partial(self._remove, finding))
                )
        return actions

    def _remove(self, finding: Finding) -> str | None:
        """Delete the entry iff its own location (never a symlink's destination) resolves
        inside the workspace; a symlink is unlinked, never followed; an entry already gone
        is nothing to report."""
        target = finding.target
        location = target.parent.resolve() / target.name
        try:
            location.relative_to(self._workspace_root.resolve())
        except ValueError:
            return f"skipped '{finding.path}' (outside the workspace)"
        if target.is_symlink() or target.is_file():
            target.unlink()
        elif target.is_dir():
            shutil.rmtree(target)
        else:
            return None
        return f"deleted '{finding.path}'"
