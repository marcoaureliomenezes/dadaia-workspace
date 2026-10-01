"""DoctorService — the one scan and reaper of the workspace instance (0.4.6 FR3/FR4).

``check()`` reports the context invariants (INV-4/5/6, CTX-URL-1, VENV-1).
``scan()`` is the ONE walk over the instance — one traversal primitive
(``features.spec_context.sweep``) serves both it and ``fix()``, driven by the zone registry
(``core.workspace_layout.DADAIA_ZONES``): root, harness dirs, the ``.dadaia/`` top level,
the closed-canon zones, the TTL zones (only expired entries and holds) — each finding one
``WS-<zone>-<verdict>`` code. ``expire()`` — the SessionStart lane and ``fix()``'s first
step — seeds missing level-1 core and takes each TTL-expired entry by its zone class;
``fix()`` then holds the slop.

Bug class (the six-bug ``.dadaia/`` ledger, workspace-doctor-root4-false-positive-dadaia-hooks
.. dadaia-reconcile-quarantines-sanctioned-references-clone): the doctor kept its own name
lists and disagreed with what init/install create. Nothing here spells a zone name — every
allow set, TTL and canon is a view of the registry.
"""

import os
import stat
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum
from functools import partial
from pathlib import Path

from dadaia_workspace.core import context_registry, session_store, workspace_layout
from dadaia_workspace.core.cli_line import fix_line, shell_line
from dadaia_workspace.core.doctor_rules import Rule, SectionFinding
from dadaia_workspace.core.exceptions import SchemaVersionError
from dadaia_workspace.core.harness_registry import (
    HARNESS_PROJECTION_DIRS,
)
from dadaia_workspace.core.models.doctor_report import DoctorLine
from dadaia_workspace.core.models.harness_profile import HarnessProfile
from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.core.platform import PLATFORM
from dadaia_workspace.core.workspace_layout import Zone, ZoneClass
from dadaia_workspace.features.spec_context import sweep
from dadaia_workspace.features.spec_context.service import git_hooks_dir
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
from dadaia_workspace.infrastructure.json_context_store import JsonContextStore
from dadaia_workspace.infrastructure.json_harness_profile_store import JsonHarnessProfileStore
from dadaia_workspace.infrastructure.ledger_scripts import worktree_rows


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


_DETAIL = {
    FindingVerdict.CANON: "",
    FindingVerdict.OPERATOR: "(named in .dadaiaignore)",
    FindingVerdict.SLOP: "(not in the root law or .dadaiaignore)",
}
_CANONICAL = frozenset({FindingVerdict.CANON, FindingVerdict.OPERATOR, FindingVerdict.REAPED})

#: What a TTL expiry does, by the zone's class: an OUTPUT entry may be unseen work (a
#: no-operator bug proposal), so it is held; an EPHEMERAL one is deleted (AC2.10, AC2.12).
_EXPIRY_ACT = {ZoneClass.OUTPUT: sweep.hold, ZoneClass.EPHEMERAL: sweep.remove}

#: Directory names that end the repo-tree walk: a nested VCS/venv/dependency tree is
#: never ours to classify and is where the walk's cost would otherwise live.
_REPO_WALK_PRUNED: frozenset[str] = frozenset({".git", ".venv", "node_modules"})
#: ``workspace_layout.verdict``'s inputs after the entry: the operator globs, then the slugs.
_Rules = tuple[tuple[str, ...], frozenset[str], frozenset[str]]


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
    #: The clearing command when ``doctor --fix`` cannot clear this entry itself.
    fix: str = ""

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


def _worktree(verdict: str, message: str, fix: str = "") -> SectionFinding:
    """A worktree finding: printed, never an error, never acted on by ``--fix`` (AC1.10)."""
    return SectionFinding("WORKTREE", verdict, message, False, False, fix, fixable=False)


def _invariant(code: str, message: str, fix: str = "", *, fixable: bool = False) -> SectionFinding:
    """A context invariant: always error-class, outside the scored entry set."""
    return SectionFinding(code, "error", message, False, True, fix, fixable)


class DoctorService:
    def __init__(
        self,
        context_store: JsonContextStore,
        git_client: GitSubprocessClient,
        workspace_root: Path,
        projection: Callable[[Path], tuple[list[DoctorLine], str]] | None = None,
    ) -> None:
        self._projection = projection
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

    def check_projection(self) -> list[SectionFinding]:
        """PROJECTION: `public doctor`'s own verdict — one error naming every blocking line."""
        lines, fix = self._projection(self._workspace_root) if self._projection else ([], "")
        message = "; ".join(line.render() for line in lines if line.status.blocking)
        return [SectionFinding("PROJECTION", "drift", message, False, True, fix)] if fix else []

    def check_installed_hooks(self, context: str | None = None) -> list[SectionFinding]:
        """HOOKS-DRIFT-1: an ALIVE repo's hook where git runs hooks is not byte-for-byte the
        shipped one (hand-edited, missing or stale) — the one backstop outside every harness
        hook. A non-git repo is never a finding; *context* scopes the repos (0.4.8 R5)."""
        issues: list[SectionFinding] = []
        for top in self._alive_repo_tops(context):
            hooks_dir = git_hooks_dir(top)
            if hooks_dir is None:
                continue
            for target, source in workspace_layout.INSTALLED_GIT_HOOKS:
                shipped = workspace_layout.public_scripts_dir() / source
                installed = hooks_dir / target
                try:
                    drifted = installed.read_bytes() != shipped.read_bytes()
                except OSError:
                    drifted = True
                if drifted:
                    rel = str(top)  # absolute: the fix runs from any cwd
                    issues.append(
                        _invariant(
                            "HOOKS-DRIFT-1",
                            f"{Path(os.path.relpath(installed, self._workspace_root)).as_posix()} differs from the shipped "
                            f"{source} — the chokepoint is enforcing something other "
                            "than what this release ships.",
                            fix_line(
                                self._workspace_root, "ci", "install-hook", "--force", "--repo", rel
                            ),
                        )
                    )
        return issues

    def _check_venv_health(self) -> list[SectionFinding]:
        """VENV-1 — the workspace venv exists with an executable ``dadaia`` entrypoint.

        FR-W3-02 (ADR-G4). Windows-safe — the scripts dir / exe suffix come from ``PLATFORM``
        and the exec check uses ``os.access``. Not fixable: rebuilding a venv is an operator
        action (``dadaia init`` / re-bootstrap), never an auto-repair.
        """
        venv_bin = self._dadaia / ".venv" / PLATFORM.venv_scripts_dir
        if not venv_bin.is_dir():
            return [
                _invariant(
                    "VENV-1",
                    f"Workspace venv missing: '{venv_bin}' does not exist.",
                    shell_line("uvx", "dadaia-workspace", "init", str(self._workspace_root)),
                )
            ]
        entry = venv_bin / f"dadaia{PLATFORM.venv_exe_suffix}"
        if not entry.is_file():
            return [
                _invariant(
                    "VENV-1",
                    f"Workspace venv entrypoint missing: '{entry}' not found.",
                    shell_line("uvx", "dadaia-workspace", "init", str(self._workspace_root)),
                )
            ]
        if not os.access(entry, os.X_OK):
            return [
                _invariant(
                    "VENV-1",
                    f"Workspace venv entrypoint not executable: '{entry}'.",
                    shell_line("chmod", "+x", str(entry)),
                )
            ]
        return []

    def check_worktrees(self, context: str | None = None) -> list[SectionFinding]:
        """AC1.10: the context's worktree rows, rendered — never judged or touched here."""
        if not (repos := {t.name for t in self._alive_repo_tops(context)}):
            return []
        found, failed, fix = worktree_rows(self._workspace_root)
        return [_worktree("warning", failed, fix)] if failed else [
            _worktree("warning" if r["warn"] else "info", f"{r['state']} {r['path']}"
                      + "".join(f"  {k}={r[k]}" for k in ("kind", "age_hours", "ahead", "dirty") if k in r), r["fix"])
            for r in found if r["repo"] in repos
        ]  # fmt: skip

    def check(self) -> list[SectionFinding]:
        issues: list[SectionFinding] = []
        try:
            contexts = self._store.list_all()
        except SchemaVersionError as refused:  # the registry's one grammar refused it
            return [_invariant("REG-SCHEMA", refused.problem, refused.fix)]

        # INV-4 (v2): ALIVE context must have repo on disk
        for ctx in contexts:
            for repo in ctx.all_repos() if ctx.state == ContextState.ALIVE else ():
                if not (self._repos_dir() / repo.slug).exists():
                    issues.append(
                        _invariant(
                            "INV-4",
                            f"Context '{ctx.name}' is alive but repo '{repo.slug}' not on disk",
                            fix_line(self._workspace_root, "context", "alive", ctx.name),
                        )
                    )

        # CTX-URL-1 (T-011-08 / FR-W2-03 d): an ALIVE context with an empty repo_url is
        # un-portable — an export/import + ``context alive`` on another machine would
        # ``git clone ""`` and fail.
        for ctx in contexts:
            if ctx.state == ContextState.ALIVE and not ctx.repo_url:
                issues.append(
                    _invariant(
                        "CTX-URL-1",
                        f"Context '{ctx.name}' is alive with an empty repo_url.",
                        fix_line(self._workspace_root, "context", "alive", ctx.name),
                    )
                )

        # INV-5 (v2): DEAD context must not have repo on disk
        for ctx in contexts:
            for repo in ctx.all_repos() if ctx.state == ContextState.DEAD else ():
                if (self._repos_dir() / repo.slug).exists():
                    issues.append(
                        _invariant(
                            "INV-5",
                            f"Context '{ctx.name}' is dead but repo '{repo.slug}' is on disk",
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
        dead = {c.name for c in contexts if c.state is ContextState.DEAD}
        for slug in sorted(owners):
            names = owners[slug]
            if len(names) > 1:  # the fix retires one owner: delete a dead one, else dead it
                owner = min(names, key=lambda n: (n not in dead, n))
                issues.append(
                    _invariant(
                        "INV-6",
                        f"Repo slug '{slug}' is owned by more than one context "
                        f"({', '.join(sorted(names))}): 'repos/<slug>' is shared, so "
                        "a dead() on one owner would take the others' working tree.",
                        fix_line(
                            self._workspace_root,
                            "context",
                            "delete" if owner in dead else "dead",
                            owner,
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
        globs, _, invalid = workspace_layout.operator_globs(self._workspace_root)
        rules = (globs, *context_registry.registered_slugs(self._workspace_root))
        findings: list[Finding] = [*self._missing_core(), *self._scan_dadaiaignore(invalid)]
        findings.extend(self._scan_places(rules))
        findings.extend(self._scan_repo_trees())
        unreadable = frozenset(session_store.unreadable_records(self._workspace_root))
        for zone in workspace_layout.zones_with_canon():
            findings.extend(self._scan_canon_zone(zone, rules, unreadable))
        return (*findings, *self.scan_ttl())

    def scan_ttl(self) -> tuple[Finding, ...]:
        """The TTL zones alone: expired entries and holds, one lstat per zone entry."""
        now = time.time()
        return tuple(
            f for zone in workspace_layout.zones_with_ttl() for f in self._scan_ttl_zone(zone, now)
        )

    def _contexts(self) -> list[SpecContextProject]:
        """The registered contexts, or NOTHING when the registry cannot be read.

        The store's contract — degrade to inaction, never to deletion — applied at the one
        place both readers share: an unreadable or older-shaped registry makes the pass do
        less, never raise (and never lets the INV-5 lane act on a half-parsed registry)."""
        try:
            return list(self._store.list_all())
        except (KeyError, OSError, SchemaVersionError, TypeError, ValueError):
            return []

    def _alive_repo_tops(self, context: str | None = None) -> list[Path]:
        """Every ALIVE registered repo's top — main plus associated — that exists on disk.
        A DEAD context's repo is INV-5's business, not the tree walk's.

        Reads the registry through :meth:`_contexts`, which degrades to inaction."""
        tops: list[Path] = []
        for ctx in self._contexts():
            if ctx.state is not ContextState.ALIVE or context not in (None, ctx.name):
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

    def _judged(self, entry: Path, rules: _Rules) -> tuple[FindingVerdict, str]:
        """``workspace_layout.verdict`` — the gate's own answer — plus the report detail."""
        rel = entry.relative_to(self._workspace_root).as_posix()
        judged = FindingVerdict(workspace_layout.verdict(rel, entry.is_dir(), *rules))
        return judged, _DETAIL[judged]

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

    def _missing_core(self) -> list[Finding]:
        """Level-1 core absent from disk — the root seeds, the provisioned zones, the harness
        profile: one stat each, no walk, so the SessionStart lane can afford it (ADR 0096)."""
        root, dadaia = self._workspace_root, self._dadaia
        profile = JsonHarnessProfileStore.path(self._states)
        core = [
            *(("root", root, root / name, "(seeded by --fix)") for name in workspace_layout.LEVEL1_SEEDS),
            *((z.name, dadaia, dadaia / z.name, "(created by --fix)") for z in workspace_layout.provisioned_zones()),
            (profile.parent.name, dadaia, profile, "(seeded by --fix from the projection dirs present)"),
        ]  # fmt: skip
        return [
            self._finding(zone, base, target, FindingVerdict.MISSING, detail)
            for zone, base, target, detail in core
            if not workspace_layout.occupied(target)
        ]

    def _scan_dadaiaignore(self, invalid: tuple[str, ...]) -> list[Finding]:
        """An invalid line is reported, never fixed — the file is the operator's (ADRs 0092,
        0093, 0145)."""
        target = self._workspace_root / workspace_layout.DADAIAIGNORE
        return [
            self._finding(
                "root", self._workspace_root, target, FindingVerdict.SLOP,
                f"(invalid line {line!r}: no !, **, / or .. — ADR 0093; the operator edits it)",
                fixable=False,
            )
            for line in invalid
        ]  # fmt: skip

    def _scan_places(self, rules: _Rules) -> list[Finding]:
        """One walk over the four places ``verdict`` judges by name: the root, ``.dadaia/``,
        ``repos/`` and ``worktrees/``."""
        root = self._workspace_root
        places = (("root", root, root), ("dadaia", self._dadaia, self._dadaia),
                  ("repos", root, root / "repos"), ("worktrees", root, root / "worktrees"))  # fmt: skip
        out: list[Finding] = []
        for zone, base, directory in places:
            for entry in sweep.walk(directory):
                verdict, detail = self._judged(entry, rules)
                credential = verdict is FindingVerdict.SLOP and entry.name == ".env"
                if credential:  # ADR 0146: the library never touches a credential file
                    detail = "(credentials live outside the workspace: the operator moves it out or names it in .dadaiaignore)"
                fixable = False if credential else None
                out.append(self._finding(zone, base, entry, verdict, detail, fixable=fixable))
        return out

    def _scan_canon_zone(
        self, zone: Zone, rules: _Rules, unreadable: frozenset[Path]
    ) -> list[Finding]:
        out: list[Finding] = []
        for entry in sweep.walk(self._dadaia / zone.name):
            verdict, detail = self._judged(entry, rules)
            if entry in unreadable:  # the record owner's answer: a corrupt record is slop
                verdict, detail = FindingVerdict.SLOP, "(unreadable session record)"
            out.append(self._finding(zone.name, self._dadaia, entry, verdict, detail))
        return out

    def _scan_ttl_zone(self, zone: Zone, now: float) -> list[Finding]:
        """Expired entries, whole, and each live hold in ``reaped/``; the zone's ``AGENTS.md``
        is never a candidate (bug public-install-restores-expired-zone-agents-reblocks-preflight)."""
        assert zone.ttl_seconds is not None
        ttl, zone_dir = zone.ttl_seconds, self._dadaia / zone.name
        out: list[Finding] = []
        for entry, stamp in _ttl_walk(zone_dir, now - ttl, depth=2):
            if entry == zone_dir / "AGENTS.md":
                continue
            age = now - stamp
            if age <= ttl:
                if zone.name != sweep.REAPED_ZONE:
                    continue
                # Held: days ROUNDED UP, a minute-old hold has its whole window left.
                detail = f"({-(-int(ttl - age) // 86_400)}d left)"
                out.append(
                    self._finding(zone.name, self._dadaia, entry, FindingVerdict.REAPED, detail)
                )
                continue
            detail = f"(mtime {timedelta(seconds=age).days}d > ttl {timedelta(seconds=ttl).days}d)"
            if not sweep.linked_worktree(self._workspace_root, entry):  # a WORKTREE `foreign` row
                out.append(
                    self._finding(zone.name, self._dadaia, entry, FindingVerdict.EXPIRED, detail)
                )
        return out

    # ------------------------------------------------------------------
    # fix() — the one reaper, in the fixed FR4 order
    # ------------------------------------------------------------------

    def expire(self) -> list[str]:
        """The SessionStart lane (``--expired-only``): missing level-1 core seeded (ADR 0096),
        stale session records deleted, then each TTL-expired zone entry taken by its zone
        class — an OUTPUT entry held in ``reaped/``, an EPHEMERAL one deleted (AC2.10). It
        costs one lstat per zone entry and walks no repo."""
        actions = [
            line
            for finding in self._missing_core()
            for line in sweep.guarded(finding.code, finding.path, partial(self._seed, finding))
        ]
        # The record owner selects the expired records (F002); the one deleter removes them.
        for record in session_store.stale_records(self._workspace_root):
            step = partial(sweep.remove, self._workspace_root, record, record.name)
            actions.extend(sweep.guarded("GRAVEYARD-GC", record.name, step))
        now = time.time()
        for zone in workspace_layout.zones_with_ttl():
            for finding in self._scan_ttl_zone(zone, now):
                if finding.verdict is FindingVerdict.EXPIRED:
                    act = _EXPIRY_ACT[zone.cls]
                    step = partial(act, self._workspace_root, finding.target, finding.path)
                    actions.extend(sweep.guarded(finding.code, finding.path, step))
        return actions

    def fix(self) -> list[str]:
        """The full reaper: :meth:`expire` (seed first, so the scan judges after it) -> MOVE
        slop to ``reaped/`` -> reap dead contexts' repos (INV-5).

        Nothing here deletes a live entry. Slop is MOVED and holds its 7 days in
        ``.dadaia/reaped/<YYYYMMDD>/<workspace-relative-path>``, the clock starting at the
        move; direct deletion is reserved to TTL expiry. That is the structural answer to
        the CRITICAL ``doctor-ptr-gc-deletes-valid-lock-free-bind``: a misclassification
        now costs a week of holding, not the operator's state. Every step on an entry runs
        through the ONE sweep guard: it reports what it did or that it skipped, never
        aborts, and never touches a location outside the workspace."""
        try:  # an unreadable registry (REG-SCHEMA): every lane acts on nothing (AC3.9)
            context_registry.entries(self._workspace_root)
        except SchemaVersionError:
            return []
        actions = self.expire()
        actions.extend(self._reap(self.scan()))  # judged after the seed: a new .dadaiaignore counts
        for ctx in self._contexts():
            for repo in ctx.all_repos() if ctx.state is ContextState.DEAD else ():
                if (repo_path := self._repos_dir() / repo.slug).exists():
                    actions.extend(self._reap_dead_repo(ctx, repo_path))
        return actions

    def _reap(self, findings: tuple[Finding, ...]) -> list[str]:
        """MOVE every slop entry into the reaped zone. Never deletes."""
        actions: list[str] = []
        for finding in findings:
            if finding.verdict is not FindingVerdict.SLOP or not finding.fixable:
                continue
            step = partial(sweep.hold, self._workspace_root, finding.target, finding.path)
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
        label = f"repos/{repo_path.name}"
        if repo_path.resolve().parent != self._repos_dir().resolve():
            return [f"INV-5: skipped '{label}' (outside repos/)"]
        current = self._store.get(ctx.name)
        if current is None or current.state is not ContextState.DEAD:
            return []
        step = partial(
            sweep.hold, self._workspace_root, repo_path, label, note=f" (context {ctx.name})"
        )
        return sweep.guarded("INV-5", label, step)

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
        elif (seed := workspace_layout.LEVEL1_SEEDS.get(finding.path)) is not None:
            finding.target.write_text(seed(self._workspace_root), encoding="utf-8")
        else:
            finding.target.mkdir(parents=True, exist_ok=True)
        return f"created '{finding.path}'"


def _ttl_walk(directory: Path, expiry: float, *, depth: int) -> list[tuple[Path, float]]:
    """``(entry, mtime)`` per zone entry, each judged by its OWN ``lstat`` and never descended
    into: a file, or a directory at *depth* (``tmp/<agent>/<YYYYMMDD>``, ``handoff/<ctx>/<file>``,
    ``reaped/<YYYYMMDD>/<top>``). A shallower directory whose entries all expired — none left
    means its own mtime expired — is itself one entry, reaped whole with its parents in one
    run (bug reaper-judges-ttl-by-walking-every-file)."""
    out: list[tuple[Path, float]] = []
    for entry in sweep.walk(directory):
        if (st := sweep.lstat(entry)) is None:
            continue
        is_dir = stat.S_ISDIR(st.st_mode)
        below = _ttl_walk(entry, expiry, depth=depth - 1) if depth > 1 and is_dir else None
        if below is None or (below or st.st_mtime < expiry) and all(t < expiry for _, t in below):
            out.append((entry, max((t for _, t in below or ()), default=st.st_mtime)))
        else:
            out.extend(below)
    return out


# ── the `workspace` section of the one doctor (0.4.7 FR5, T-047-02) ──────────────

SECTION = "workspace"

#: The verdicts that make a run exit 1 — the pre-0.4.7 `dadaia doctor` rule, unchanged.
ERROR_VERDICTS = frozenset({FindingVerdict.SLOP, FindingVerdict.EXPIRED, FindingVerdict.MISSING})


def workspace_rules(
    *, expired_only: bool = False, context: str | None = None
) -> tuple[Rule[DoctorService], ...]:
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
        return [] if expired_only else service.check()

    def installed_hooks(service: DoctorService) -> list[SectionFinding]:
        """HOOKS-DRIFT-1 — its own rule because its fix is its own runnable line."""
        return [] if expired_only else service.check_installed_hooks(context)

    def entries(service: DoctorService) -> list[SectionFinding]:
        findings = service.scan_ttl() if expired_only else service.scan()
        if expired_only:
            findings = tuple(f for f in findings if f.verdict is FindingVerdict.EXPIRED)
        return [
            SectionFinding(
                code=finding.code,
                verdict=finding.verdict.value,
                message=f"{finding.path}  {finding.detail}",
                canonical=finding.canonical and finding.scored,
                error=finding.verdict in ERROR_VERDICTS,
                fix=finding.fix,
                fixable=finding.fixable,
            )
            for finding in findings
        ]

    return (
        Rule(
            ("WS-INVARIANT",),
            SECTION,
            invariants,
            fix_help=("doctor", "--fix"),
        ),
        Rule(
            ("HOOKS-DRIFT-1",),
            SECTION,
            installed_hooks,
            fix_help=("ci", "install-hook", "--force", "--repo", "<repo>"),
        ),
        Rule(
            ("PROJECTION",),
            SECTION,
            lambda service: [] if expired_only else service.check_projection(),
            fix_help=("public", "install"),
        ),
        Rule(
            ("WORKTREE",),
            SECTION,
            lambda service: [] if expired_only else service.check_worktrees(context),
        ),
        Rule(
            ("WS-ENTRY",),
            SECTION,
            entries,
            fix_help=("doctor", "--fix"),
        ),
    )
