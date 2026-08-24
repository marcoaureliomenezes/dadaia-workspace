"""SpecContextService — full Spec Context Project lifecycle."""

import contextlib
import logging
import os
import re
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

from dadaia_workspace.core import specs_backup as _backup
from dadaia_workspace.core.exceptions import (
    ContextAlreadyExistsError,
    ContextNotFoundError,
    ContextStateError,
    DadaiaError,
    GitSyncError,
)
from dadaia_workspace.core.models.spec_context import (
    AssociatedRepo,
    ContextState,
    RepoLiveStatus,
    SpecContextProject,
)
from dadaia_workspace.core.protocols.context_store import ContextStore
from dadaia_workspace.core.protocols.git_client import GitClient

# Canonical scaffold source — lives inside the installed package
_PUBLIC_DIR = Path(__file__).parent.parent.parent / "public"
_SCAFFOLD_SRC = _PUBLIC_DIR / "scaffold"

_log = logging.getLogger(__name__)


class DeadReviewRequiredError(DadaiaError):
    """Raised when dead() finds untracked files but no explicit --commit consent.

    F-5 (sec audit): dead() must NOT auto-stage and push untracked non-gitignored
    files without review. When such files exist and the caller did not pass
    ``commit=True``, dead() refuses, pushes nothing, and leaves the repo on disk
    untouched. The message lists the offending files so the operator can review,
    gitignore, or delete them and then re-run with ``--commit`` to consent.
    """


class DeadSecretFoundError(DadaiaError):
    """Raised when --commit was given but a planted secret/IP/hostname is found.

    The privacy/secret scan runs over the content of the untracked files that
    ``--commit`` would newly commit. Any match blocks the push (repo left on disk,
    nothing committed or pushed). The message is redacted: it names the file and
    the rule that fired, never the secret value itself.
    """


class AssociatedRepoConflictError(DadaiaError):
    """Raised by ``add_repo`` when the slug cannot be registered as given (A17.3).

    Two distinct causes share this one error type (both are "the registry already
    has an opinion about this slug that `add` will not silently override"):
    the slug IS the context's own main repo slug, or the slug is already an
    associated repo registered with a *different* URL. Same-slug-same-url is NOT
    an error — see ``add_repo``'s idempotent no-op.
    """


class AssociatedRepoNotFoundError(DadaiaError):
    """Raised by ``remove_repo`` when the slug is not a registered associated repo
    of the context (A17.1: fails loudly on an unknown slug, never a silent no-op).
    """


class DeadUnpushedCommitsError(DadaiaError):
    """Raised when a repo in the set has local commits and NO remote to receive them
    (A16.2).

    FR16: ``dead()`` refuses when **any** repo — main or associated — is dirty or
    unpushed, naming which one, and checks every repo in the set BEFORE acting on any
    (no partial dead: a later repo's refusal must never follow an earlier repo already
    being synced and removed).

    ``unpushed`` is deliberately narrow: ``has_commits() and not has_remote()`` —
    commits that can genuinely never reach anywhere, not merely "ahead of the last
    push". dead()'s own Phase 2 (below) already auto-syncs and pushes pending commits
    whenever a remote exists — including the scaffold commit alive() itself just made
    (always locally unpushed by design, on every fresh repo). Refusing on
    ``GitClient.unpushed_commit_count() > 0`` regardless of ``has_remote()`` would
    therefore make dead() refuse right after every ordinary alive()-then-dead() call —
    a false-positive landmine, not a safety net. Only the truly unrecoverable case
    (commits with no remote at all) refuses; a remote-backed repo is left to Phase 2's
    existing auto-push.
    """


def _rmtree_chmod_retry(func: object, path: str, _exc: BaseException) -> None:
    """`shutil.rmtree` onexc handler: chmod-and-retry (v0.1.50 FR3).

    Git loose objects under ``.git/objects/`` are read-only (0444) by design;
    grant owner write on the failing path (and its parent dir, where the unlink
    permission actually lives) and retry the failed operation once.
    """
    import os
    import stat

    target = Path(path)
    with contextlib.suppress(OSError):
        os.chmod(target.parent, target.parent.stat().st_mode | stat.S_IWUSR | stat.S_IXUSR)
    with contextlib.suppress(OSError):
        os.chmod(target, stat.S_IWUSR | stat.S_IRUSR)
    func(path)  # type: ignore[operator]


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


# --------------------------------------------------------------------- secret scan
#
# Structural secret/identifier patterns reused as the privacy/secret engine for the
# dead() --commit review gate (F-5 / AC-R7-01). These are content-shape rules — no
# operator-specific terms are hardcoded here (dev-guardrail #4). The operator denylist
# baseline (R7b / T-010-20) lives in infrastructure/privacy_check.py and is orthogonal;
# this scan is the structural layer that blocks pushing newly-committed files that look
# like they carry a secret, private IP, or internal hostname.
_SECRET_SCAN_TEXT_SUFFIXES = {
    ".cfg",
    ".conf",
    ".css",
    ".env",
    ".html",
    ".ini",
    ".j2",
    ".js",
    ".json",
    ".md",
    ".py",
    ".sh",
    ".toml",
    ".ts",
    ".txt",
    ".yaml",
    ".yml",
    "",
}

# R-2 (v0.1.10 rc-2 sec audit LOW): cryptographic key / certificate material is
# commonly stored in binary-suffix files (.pem can be text, .key/.p12/.pfx are
# typically binary) that the text-suffix scan above skips. A private-key file in
# an untracked dead()-push set is a finding *by its suffix alone* — regardless of
# whether the bytes happen to be UTF-8 decodable. PEM files are also content-scanned
# (they overlap with the text path) so a real key block is caught both ways.
_SECRET_SCAN_KEY_SUFFIXES = {
    ".pem",
    ".key",
    ".p12",
    ".pfx",
    ".crt",
    ".cer",
    ".der",
    ".keystore",
    ".jks",
}

# (rule-name, compiled-pattern). Names are surfaced in the error; values never are.
_SECRET_SCAN_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private-key-block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("aws-access-key-id", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("slack-token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    (
        "generic-secret-assignment",
        re.compile(
            r"(?i)(?:password|passwd|secret|api[_-]?key|access[_-]?token|"
            r"private[_-]?key)\s*[:=]\s*['\"]?[A-Za-z0-9/+_\-]{8,}",
        ),
    ),
    (
        "private-ipv4",
        re.compile(
            r"\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}"
            r"|192\.168\.\d{1,3}\.\d{1,3}"
            r"|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b",
        ),
    ),
    (
        "internal-hostname",
        re.compile(r"(?i)\b[a-z0-9][a-z0-9-]*\.(?:internal|local|lan|corp|intranet)\b"),
    ),
)


def _scan_file_for_secrets(path: Path) -> list[str]:
    """Return rule names that match *path* (empty list ⇒ clean).

    Two layers (R-2):

    1. **Suffix presence** — a cryptographic key / certificate suffix
       (``.pem``/``.key``/``.p12``/``.pfx``/...) is itself a finding
       (``cert-key-file-suffix``), because such a file does not belong in an
       untracked dead()-push set regardless of its byte content. This catches
       binary key material the text scan below skips.
    2. **Content rules** — for text-decodable files (the text-suffix allowlist,
       plus PEM/key files that happen to be ASCII), the structural secret rules
       run over the decoded content.

    Binary / unreadable / unsupported-suffix files that are not key material are
    skipped. Never returns the matched secret value — only the rule name, so
    callers can build a redacted report.
    """
    suffix = path.suffix.lower()
    hits: list[str] = []

    is_key_file = suffix in _SECRET_SCAN_KEY_SUFFIXES
    if is_key_file:
        # Presence of cert/key material is a finding by itself.
        hits.append("cert-key-file-suffix")

    # Content-scan only files we can decode: the text allowlist, plus key files
    # (PEM is frequently ASCII — a decodable .pem also triggers private-key-block).
    if suffix not in _SECRET_SCAN_TEXT_SUFFIXES and not is_key_file:
        return hits
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return hits
    for rule_name, pattern in _SECRET_SCAN_RULES:
        if pattern.search(text):
            hits.append(rule_name)
    return hits


def _merge_scaffold_into(
    scaffold_src: Path,
    target_dir: Path,
    *,
    timestamp: str | None = None,
) -> list[str]:
    """Walk *scaffold_src* and copy only files/dirs that are MISSING in *target_dir*.

    Never overwrites any existing file.  Returns the list of relative paths that were
    added (empty list when nothing was missing).

    If *timestamp* is None the current UTC time is used.  Callers may inject a fixed
    timestamp for deterministic testing.
    """
    if timestamp is None:
        timestamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")

    added: list[str] = []
    for src_path in scaffold_src.rglob("*"):
        rel = src_path.relative_to(scaffold_src)
        dst_path = target_dir / rel
        if src_path.is_dir():
            if not dst_path.exists():
                dst_path.mkdir(parents=True, exist_ok=True)
                _log.info("scaffold merge: created directory %s", rel)
        else:
            if not dst_path.exists():
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(src_path), str(dst_path))
                added.append(str(rel))
                _log.info("scaffold merge: added missing file %s", rel)
    return added


class SpecContextService:
    def __init__(
        self,
        context_store: ContextStore,
        git_client: GitClient,
        workspace_root: Path,
    ) -> None:
        self._store = context_store
        self._git = git_client
        self._workspace_root = workspace_root

    def _repos_dir(self) -> Path:
        return self._workspace_root / "repos"

    def _repo_path(self, repo_slug: str) -> Path:
        return self._repos_dir() / repo_slug

    def _specs_dir(self, repo_slug: str) -> Path:
        return self._repo_path(repo_slug) / "specs"

    # ------------------------------------------------------------------ create

    def create(self, name: str, repo_slug: str, repo_url: str) -> SpecContextProject:
        """Register a new Spec Context Project in state ``DEAD``.

        Refuses a *name* already registered (``ContextAlreadyExistsError``) and a
        *repo_slug* already owned by ANOTHER context — as its own main repo or one
        of its associated repos (``AssociatedRepoConflictError``,
        context-create-accepts-slug-owned-by-another-context): the second registry
        seam that writes into the shared ``repos/<slug>`` namespace, mirroring
        ``add_repo``'s F-1 guard (see ``_foreign_slug_owner``). Without it, two
        contexts could register the same ``repos/<slug>`` checkout and arm
        ``dead()`` of either one to commit, push and delete the other's working
        tree.
        """
        if self._store.get(name) is not None:
            raise ContextAlreadyExistsError(
                f"Context '{name}' already exists. Use a different name."
            )
        owner = self._foreign_slug_owner(name, repo_slug)
        if owner is not None:
            raise AssociatedRepoConflictError(
                f"'{repo_slug}' is already registered by context '{owner}' (as its "
                "own main repo or one of its associated repos). 'repos/<slug>' "
                "is a namespace every context shares — creating context "
                f"'{name}' with it too would let 'dadaia context dead {name}' "
                f"commit, push and delete '{owner}''s working tree. Choose a "
                "different slug, or coordinate with the owning context first."
            )
        ctx = SpecContextProject(
            name=name,
            state=ContextState.DEAD,
            repo_slug=repo_slug,
            repo_url=repo_url,
            created_at=_now(),
            alive_since=None,
            dead_since=None,
        )
        self._store.save(ctx)
        return ctx

    # ------------------------------------------------------------------ update_url

    def update_url(self, name: str, repo_url: str) -> SpecContextProject:
        """Repair a context's ``repo_url`` through the store ``update()`` API.

        FR-W2-03 (c) / T-011-08: the operator repair verb for the VPS-migration
        scenario where no on-disk repo is present to back-fill from. Preserves the
        record shape and writes through the atomic store. Raises
        ``ContextNotFoundError`` if the context does not exist.
        """
        ctx = self._store.get(name)
        if ctx is None:
            raise ContextNotFoundError(f"Context '{name}' not found.")
        updated = SpecContextProject(
            name=ctx.name,
            state=ctx.state,
            repo_slug=ctx.repo_slug,
            repo_url=repo_url,
            created_at=ctx.created_at,
            alive_since=ctx.alive_since,
            dead_since=ctx.dead_since,
            current_branch=ctx.current_branch,
            associated_repos=ctx.associated_repos,
        )
        self._store.update(updated)
        return updated

    # ------------------------------------------------------------------ associated repos (FR17)

    def _foreign_slug_owner(self, name: str, slug: str) -> str | None:
        """Return the name of another context that already owns *slug*, or ``None``.

        "Owns" means *slug* is that other context's own main repo slug, or one of
        its registered associated repos. Every context's ``repos/<slug>`` checkout
        lives in the ONE namespace every context shares (A15.3/FR17) — the same
        assumption ``dead()`` makes when it walks ``all_repos()`` and
        commit_all()s/push()es/rmtree()s every entry it finds. ``create`` (the
        main ``--repo`` slug) and ``add_repo`` (associated slugs) are the TWO
        seams that write into that shared namespace, so both consult this
        predicate to keep the assumption true (T-044-45 F-1 / bug
        context-repo-add-accepts-foreign-context-slug at ``add_repo``, mirrored
        at ``create`` by bug context-create-accepts-slug-owned-by-another-context)
        — never a second guard added inside ``dead()`` itself, which would be
        checking the destructive side of a boundary that should never have been
        crossable in the first place.
        """
        for other in self._store.list_all():
            if other.name == name:
                continue
            if other.repo_slug == slug or any(r.slug == slug for r in other.associated_repos):
                return other.name
        return None

    def add_repo(self, name: str, slug: str, repo_url: str = "") -> tuple[SpecContextProject, bool]:
        """Register an associated repo on a context (A17.1/A17.3).

        Returns ``(context, was_added)``. Idempotent: re-adding the exact same
        ``slug``/``repo_url`` pair is a no-op success (``was_added=False``, the
        stored context is returned unchanged) — never a duplicate entry. The same
        slug already registered with a *different* URL raises
        ``AssociatedRepoConflictError`` rather than silently overwriting it: this
        method is the ONE way to register an associated repo's URL (FR15/A15.3's
        one-accessor discipline extended to writes), so the recovery path is
        remove-then-add, never a second divergent "update" verb. The context's own
        main repo slug can never be added as an associated repo (A17.3) — it is
        already included via ``all_repos()``. Nor can a slug already owned by
        ANOTHER context — as that context's main repo or one of its associated
        repos — be registered here (T-044-45 F-1): ``repos/<slug>`` is a namespace
        every context shares, and ``dead()`` destroys every repo in
        ``all_repos()`` with no further ownership check, so a slug collision here
        is a live path to destroying a foreign working tree. ``create
        --associated`` (``cli/commands/context.py``) reuses this method verbatim,
        so it inherits both refusals with no second code path.
        """
        ctx = self._store.get(name)
        if ctx is None:
            raise ContextNotFoundError(f"Context '{name}' not found.")
        if slug == ctx.repo_slug:
            raise AssociatedRepoConflictError(
                f"'{slug}' is context '{name}''s own main repo slug (--repo at "
                "create time) — it is always included via all_repos() and can "
                "never also be registered as an associated repo."
            )
        owner = self._foreign_slug_owner(name, slug)
        if owner is not None:
            raise AssociatedRepoConflictError(
                f"'{slug}' is already registered by context '{owner}' (as its "
                "own main repo or one of its associated repos). 'repos/<slug>' "
                "is a namespace every context shares — registering it on "
                f"'{name}' too would let 'dadaia context dead {name}' commit, "
                f"push and delete '{owner}''s working tree. Choose a different "
                "slug, or coordinate with the owning context first."
            )
        existing = next((r for r in ctx.associated_repos if r.slug == slug), None)
        if existing is not None:
            if existing.url == repo_url:
                return ctx, False
            raise AssociatedRepoConflictError(
                f"Associated repo '{slug}' is already registered on context "
                f"'{name}' with a different URL ({existing.url!r} != "
                f"{repo_url!r}). 'repo add' never overwrites a URL silently — "
                f"run 'dadaia context repo remove {name} {slug}' first, then "
                "re-add with the intended URL."
            )
        updated = SpecContextProject(
            name=ctx.name,
            state=ctx.state,
            repo_slug=ctx.repo_slug,
            repo_url=ctx.repo_url,
            created_at=ctx.created_at,
            alive_since=ctx.alive_since,
            dead_since=ctx.dead_since,
            current_branch=ctx.current_branch,
            associated_repos=(*ctx.associated_repos, AssociatedRepo(slug=slug, url=repo_url)),
        )
        self._store.update(updated)
        return updated, True

    def remove_repo(self, name: str, slug: str) -> SpecContextProject:
        """Remove an associated repo from a context's registry (A17.1/A17.2).

        Registry-only: never touches disk or the git port — an on-disk checkout at
        ``repos/<slug>`` (if any) is left exactly as it was; the CLI layer states
        what it leaves behind (A17.2). Raises ``ContextNotFoundError`` for an
        unknown context and ``AssociatedRepoNotFoundError`` for a slug that is not
        currently registered — including a second ``remove`` of the same slug,
        which is the loud-failure half of A17.1's idempotency, not a silent no-op.
        """
        ctx = self._store.get(name)
        if ctx is None:
            raise ContextNotFoundError(f"Context '{name}' not found.")
        if not any(r.slug == slug for r in ctx.associated_repos):
            raise AssociatedRepoNotFoundError(
                f"Associated repo '{slug}' is not registered on context '{name}'."
            )
        updated = SpecContextProject(
            name=ctx.name,
            state=ctx.state,
            repo_slug=ctx.repo_slug,
            repo_url=ctx.repo_url,
            created_at=ctx.created_at,
            alive_since=ctx.alive_since,
            dead_since=ctx.dead_since,
            current_branch=ctx.current_branch,
            associated_repos=tuple(r for r in ctx.associated_repos if r.slug != slug),
        )
        self._store.update(updated)
        return updated

    # ------------------------------------------------------------------ back-fill

    def _backfill_repo_url(self, repo_slug: str, current_url: str) -> str:
        """Return the on-disk ``origin`` URL when the record URL is empty.

        FR-W2-03 (b) / T-011-08: ``alive``/``dead`` back-fill ``repo_url`` from
        ``git remote get-url origin`` when the record's URL is empty and a repo is
        on disk (the repo knows its own remote). Goes exclusively through the
        per-context git-ops port — no raw subprocess in features. Returns the
        existing URL unchanged when it is already set, when no repo is on disk, or
        when the repo has no ``origin`` remote.
        """
        if current_url:
            return current_url
        repo_path = self._repo_path(repo_slug)
        if not repo_path.exists() or not self._git.is_git_root(repo_path):
            return current_url
        try:
            discovered = self._git.remote_url(repo_path)
        except Exception:
            return current_url
        return discovered or current_url

    # ------------------------------------------------------------------ list / show

    def list_all(self) -> list[SpecContextProject]:
        return self._store.list_all()

    def show(self, name: str) -> SpecContextProject:
        ctx = self._store.get(name)
        if ctx is None:
            raise ContextNotFoundError(f"Context '{name}' not found.")
        return ctx

    # ------------------------------------------------------------------ branch resolution (FR18)

    def repo_live_status(self, repo: AssociatedRepo) -> RepoLiveStatus:
        """THE single branch-resolution implementation (A18.3).

        `context show`, `context list --json`, the export branch refresh and the
        panel card all resolve a repo's on-disk presence and live checked-out
        branch through this ONE method — never a second ad hoc git-subprocess call
        at a CLI or feature boundary. That duplication is exactly what produced bug
        `context-list-current-branch-stale-for-alive-repo`: ``show`` queried git
        live while ``list`` read only the stored snapshot, so the two verbs could
        disagree on the same field name. Collapsing both onto this one seam makes
        that disagreement structurally impossible rather than patched by adding a
        refresh call to the divergent path.

        A repo that is not cloned, or whose live git query fails, degrades to
        ``on_disk=False`` / ``current_branch=None`` rather than raising — every
        caller here is a best-effort display/export surface.
        """
        repo_path = self._repo_path(repo.slug)
        on_disk = repo_path.exists() and self._git.is_git_root(repo_path)
        branch: str | None = None
        if on_disk:
            with contextlib.suppress(Exception):
                branch = self._git.current_branch(repo_path) or None
        return RepoLiveStatus(slug=repo.slug, url=repo.url, on_disk=on_disk, current_branch=branch)

    def repos_live_status(self, ctx: SpecContextProject) -> list[RepoLiveStatus]:
        """Live status for every repo in ``ctx.all_repos()`` (main first, then every
        associated repo in registration order) — the ONE set ``show``/``list``/
        export/panel render for "this context's repos" (FR18)."""
        return [self.repo_live_status(repo) for repo in ctx.all_repos()]

    # ------------------------------------------------------------------ alive (T-10b / T-11)

    def alive(self, name: str) -> SpecContextProject:
        """Transition a context from DEAD to ALIVE; clone every repo in the set if absent.

        Idempotent: calling alive() on an already-ALIVE context is a no-op beyond
        re-confirming every repo is present (no error, no re-clone of anything already
        on disk). Sets alive_since=now and clears dead_since. Concurrent races are
        accepted and surfaced by advisory presence; this operation never acquires a lock.

        FR16/A16.1/A16.3: every repo in the set — the main repo first, then each
        associated repo in order (``SpecContextProject.all_repos()``, the one accessor,
        A15.3) — is cloned if missing. Only the MAIN repo (below) receives the specs/
        scaffold, ``AGENTS.md`` and ``tests/AGENTS.md``, checkout, and branch tracking:
        an associated repo is cloned CLEAN, with no scaffold and no ``specs/`` bind of
        its own — specs/bind/memory/releases/backlog resolve from the main repo only
        (FR19/G13). This loop replaces the prior main-repo-only clone check; it is not
        a second path beside it.
        """
        ctx = self._store.get(name)
        if ctx is None:
            raise ContextNotFoundError(f"Context '{name}' not found.")

        ctx_latest = self._store.get(name)
        if ctx_latest is None:
            raise ContextNotFoundError(f"Context '{name}' not found.")

        for repo in ctx_latest.all_repos():
            repo_dest = self._repo_path(repo.slug)
            if not repo_dest.exists():
                self._git.clone(repo.url, repo_dest)

        if ctx.state == ContextState.ALIVE:
            return ctx

        repo_slug = ctx.repo_slug
        repo_path = self._repo_path(repo_slug)

        actual_branch: str | None = None
        backfilled_url: str = ctx.repo_url

        if ctx_latest.current_branch:
            try:
                self._git.checkout(repo_path, ctx_latest.current_branch)
            except Exception as exc:
                print(
                    f"WARNING: could not checkout branch {ctx_latest.current_branch!r}: {exc}",
                    file=sys.stderr,
                )

        try:
            actual_branch = self._git.current_branch(repo_path)
        except Exception:
            actual_branch = None

        backfilled_url = self._backfill_repo_url(repo_slug, ctx_latest.repo_url)

        # Bug context-alive-sweeps-unrelated-worktree-changes (MEDIUM): the scaffold
        # commit below must stage EXACTLY the paths this method creates/modifies below
        # — never a blanket ``git add -A``/``-u`` sweep that would silently fold in
        # pre-existing unrelated dirty tracked files (e.g. an operator's mid-edit
        # docker-compose.yml). `touched` accumulates only those repo-relative paths.
        touched: list[str] = []

        specs_dir = self._specs_dir(repo_slug)
        if not specs_dir.exists():
            if _SCAFFOLD_SRC.exists():
                shutil.copytree(_SCAFFOLD_SRC, specs_dir)
            else:
                for subdir in ("", "memory", "features"):
                    (specs_dir / subdir).mkdir(parents=True, exist_ok=True)
            # Entirely new tree — every path under it is scaffold-authored.
            touched.append("specs")
        elif _SCAFFOLD_SRC.exists():
            preserved = _backup.preserve_specs(specs_dir)
            added = _merge_scaffold_into(_SCAFFOLD_SRC, specs_dir)
            if added:
                _log.info(
                    "scaffold merge into pre-existing specs/: %d file(s) added: %s "
                    "(pre-existing tree preserved at %s)",
                    len(added),
                    added,
                    preserved,
                )
                # Pre-existing specs/ may carry its own unrelated dirty files — stage
                # only the individual files the merge actually added, never the whole
                # directory.
                touched.extend(Path("specs", rel).as_posix() for rel in added)
            else:
                shutil.rmtree(preserved, ignore_errors=True)
                _log.info("scaffold merge into pre-existing specs/: no missing files found")

        # v0.4.3 T-043-21/FR17: mirror the tests/AGENTS.md sibling seam's hardened
        # posture (below) onto this write too — it previously carried ZERO symlink
        # refusals. The containing repo DIRECTORY must not itself be a symlink (it
        # would escape the repos/ tree, same posture as `workspace_guardrail`'s
        # consumer-repo containment).
        #
        # v0.4.3 T-043-23 security-review rework (FR17 LOW, CWE-367 TOCTOU/CWE-59 link
        # following, handoff 2026-08-17T173112Z-security-reviewer-v0.4.3-alpha-2-delta):
        # the destination-file check used to be a SEPARATE `is_symlink()`/`.exists()`
        # probe followed by a DISTINCT `shutil.copy2` call — two syscalls with a window
        # between them where a same-user process could swap the destination for a
        # symlink and have the template written straight through it. Replaced with a
        # SINGLE atomic `os.open()` carrying `O_CREAT|O_EXCL|O_NOFOLLOW`: "already
        # exists", "is a symlink" (dangling or not) and "was swapped mid-window" are now
        # ONE indivisible refusal, never three separately-timed checks.
        repo_agents_dst = repo_path / "AGENTS.md"
        repo_agents_src = _PUBLIC_DIR / "templates" / "repo-AGENTS.md"
        if not repo_path.is_symlink() and repo_agents_src.exists():
            open_flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0)
            try:
                fd = os.open(repo_agents_dst, open_flags, 0o644)
            except OSError:
                pass  # exists, is a symlink, or was raced mid-window — refused, no-op.
            else:
                with os.fdopen(fd, "wb") as fh:
                    fh.write(repo_agents_src.read_bytes())
                touched.append("AGENTS.md")

        # v0.7.0 FR3 (T-070-07): the scoped test law lands ONLY where a tests/ tree
        # already exists — alive() never invents the directory (a stray tests/ would
        # be planted in every non-Python consumer), and never overwrites a repo's own
        # scoped law. Plain copy, byte-identical: no rendering at this seam.
        tests_agents_dst = repo_path / "tests" / "AGENTS.md"
        tests_agents_src = _PUBLIC_DIR / "templates" / "tests-AGENTS.md"
        tests_dir = repo_path / "tests"
        if (
            tests_dir.is_dir()
            and not tests_dir.is_symlink()  # a symlinked tests/ escapes the repo tree
            and not tests_agents_dst.exists()
            # A DANGLING destination symlink reports not-exists yet copy2 would write
            # through it (workspace_guardrail refuses destination-file symlinks — the
            # same posture holds at this seam).
            and not tests_agents_dst.is_symlink()
            and tests_agents_src.exists()
        ):
            shutil.copy2(tests_agents_src, tests_agents_dst)
            touched.append(Path("tests", "AGENTS.md").as_posix())

        # Commit the scaffold alive() itself just wrote (bug alive-scaffold-blocks-dead,
        # validation-027 F-06): leaving tool-created files untracked made an immediate
        # dead() refuse via the untracked-consent guard, so create->alive->dead could
        # never complete on a fresh context. Only tool-authored files are involved here;
        # operator-created untracked files still hit dead()'s guard as designed (F-5).
        # commit_paths (never commit_all) keeps this scoped to `touched` alone — any
        # pre-existing unrelated dirty tracked file stays untouched and uncommitted
        # (bug context-alive-sweeps-unrelated-worktree-changes).
        with contextlib.suppress(Exception):
            if touched and self._git.is_git_root(repo_path) and self._git.is_dirty(repo_path):
                self._git.commit_paths(
                    repo_path,
                    "chore(scaffold): dadaia context alive specs baseline",
                    tuple(touched),
                )

        ctx_fresh = self._store.get(name)
        if ctx_fresh is None:
            raise ContextNotFoundError(f"Context '{name}' not found.")
        if ctx_fresh.state == ContextState.ALIVE:
            return ctx_fresh
        alive_ctx = SpecContextProject(
            name=ctx_fresh.name,
            state=ContextState.ALIVE,
            repo_slug=ctx_fresh.repo_slug,
            repo_url=ctx_fresh.repo_url or backfilled_url,
            created_at=ctx_fresh.created_at,
            alive_since=_now(),
            dead_since=None,
            current_branch=actual_branch,
            associated_repos=ctx_fresh.associated_repos,
        )
        self._store.update(alive_ctx)

        return alive_ctx

    # ------------------------------------------------------------------ baseline

    def baseline(
        self,
        name: str,
        *,
        message: str = "chore: establish dadaia scaffold baseline",
        push: bool = False,
    ) -> SpecContextProject:
        """Create the explicit initial Git commit for an ALIVE unborn repository."""
        ctx = self._store.get(name)
        if ctx is None:
            raise ContextNotFoundError(f"Context '{name}' not found.")
        if ctx.state != ContextState.ALIVE:
            raise ContextStateError(
                f"Context '{name}' is not ALIVE. Run 'dadaia context alive {name}' first."
            )

        repo_path = self._repo_path(ctx.repo_slug)
        if not repo_path.exists() or not self._git.is_git_root(repo_path):
            raise ContextStateError(
                f"Context '{name}' has no materialized Git repository at '{repo_path}'."
            )
        if self._git.has_commits(repo_path):
            # Convergent contract (bug baseline-refuses-alive-scaffold-commit):
            # alive() commits its own scaffold, so history + clean tree is the
            # canonical post-alive state — success, not refusal. A dirty tree on top
            # of history converges too when EVERY dirty path is scaffold-shaped
            # (specs/** or AGENTS.md) — the official alive → `specs init` → baseline
            # sequence leaves exactly those tool-authored files (bug
            # context-baseline-rejects-official-scaffold-followup). Anything else
            # refuses: operator content must never be swept into a baseline commit.
            if self._git.is_dirty(repo_path):
                dirty = tuple(self._git.diff_name_only(repo_path))
                scaffold_shaped = bool(dirty) and all(
                    rel == "AGENTS.md" or rel.startswith("specs/") for rel in dirty
                )
                if not scaffold_shaped:
                    raise ContextStateError(
                        f"Context '{name}' already has Git history with uncommitted "
                        "changes outside the scaffold envelope (specs/**, AGENTS.md); "
                        "baseline never sweeps operator content. Commit or stash your "
                        "changes first."
                    )
                self._require_no_untracked_secrets(name, repo_path)
                self._git.commit_all(repo_path, message)
            if push:
                if not self._git.has_remote(repo_path):
                    raise GitSyncError(f"Context '{name}' has no remote; baseline cannot push.")
                self._git.push(repo_path)
            return ctx
        if not self._git.is_dirty(repo_path):
            raise ContextStateError(
                f"Context '{name}' has no scaffold content to commit as a baseline."
            )

        self._require_no_untracked_secrets(name, repo_path)

        self._git.commit_all(repo_path, message)
        if not self._git.has_commits(repo_path):
            raise GitSyncError(
                f"Initial baseline commit was not created for context '{name}'. "
                "Configure Git user.name/user.email and retry."
            )
        if push:
            if not self._git.has_remote(repo_path):
                raise GitSyncError(
                    f"Context '{name}' has no remote; baseline was committed locally but not pushed."
                )
            self._git.push(repo_path)
        return ctx

    def _require_no_untracked_secrets(self, name: str, repo_path: Path) -> None:
        """Secret-scan every untracked file; raise before any baseline commit sweeps one."""
        flagged: list[str] = []
        for rel in self._git.list_untracked(repo_path):
            path = repo_path / rel
            if path.is_file():
                hits = _scan_file_for_secrets(path)
                if hits:
                    flagged.append(f"  {rel}: {', '.join(sorted(set(hits)))}")
        if flagged:
            raise DeadSecretFoundError(
                f"Context '{name}': secret scan blocked initial baseline (values redacted):\n"
                + "\n".join(flagged)
            )

    # ------------------------------------------------------------------ dead (T-10b / T-11)

    def _enforce_dead_review_gate(
        self, name: str, repo_path: Path, *, commit: bool, repo_slug: str
    ) -> None:
        """Gate dead() on untracked content (F-5 / AC-R7-01), one repo of the set.

        No untracked files ⇒ no-op (clean-tree / tracked-only path unchanged).
        Untracked files + not *commit* ⇒ raise DeadReviewRequiredError (refuse).
        Untracked files + *commit* ⇒ secret-scan their content; any match raises
        DeadSecretFoundError. This runs before any commit/push/rmtree so a refusal
        leaves every repo untouched (A16.2: called from dead()'s preflight sweep over
        the whole set — main and every associated repo alike — before any of them is
        acted on). *repo_slug* is folded into every raised message so a multi-repo
        refusal names which repo of the set it is (A16.2).
        """
        try:
            untracked = self._git.list_untracked(repo_path)
        except Exception:
            # Fail-closed for the gate: if we cannot enumerate untracked files we
            # cannot prove the tree is clean. Without consent, refuse.
            if commit:
                return
            raise DeadReviewRequiredError(
                f"Context '{name}': could not verify the working tree of repo "
                f"'{repo_slug}' at '{repo_path}'. Re-run with --commit to consent to "
                "committing+pushing any changes, or clean the tree first."
            ) from None

        if not untracked:
            return  # clean tree (no untracked files) — behave exactly as before

        if not commit:
            shown = untracked[:20]
            more = "" if len(untracked) <= 20 else f"\n  ... and {len(untracked) - 20} more"
            listing = "\n".join(f"  {f}" for f in shown)
            raise DeadReviewRequiredError(
                f"Context '{name}': repo '{repo_slug}' has {len(untracked)} untracked "
                f"file(s) that dead() would otherwise commit and push WITHOUT review:\n"
                f"{listing}{more}\n"
                "Review them, then either delete/gitignore them, or re-run with "
                "'dadaia context dead "
                f"{name} --commit' to explicitly consent to committing and pushing them."
            )

        # commit=True: scan the content of the files we are about to newly commit.
        flagged: list[str] = []
        for rel in untracked:
            file_path = repo_path / rel
            if not file_path.is_file():
                continue
            hits = _scan_file_for_secrets(file_path)
            if hits:
                flagged.append(f"  {rel}: {', '.join(sorted(set(hits)))}")
        if flagged:
            report = "\n".join(flagged)
            raise DeadSecretFoundError(
                f"Context '{name}': repo '{repo_slug}' secret scan blocked dead() "
                f"--commit. {len(flagged)} untracked file(s) match a secret/identifier "
                "rule (values redacted):\n"
                f"{report}\n"
                "Remove or redact the flagged content, then re-run. Nothing was pushed."
            )

    def dead(self, name: str, *, commit: bool = False) -> SpecContextProject:
        """Transition a context from ALIVE to DEAD; sets dead_since, removes every repo.

        FR16/A16.2: covers the whole set — the main repo, then every associated repo
        (``SpecContextProject.all_repos()``, the one accessor, A15.3) — in **two**
        passes over the same loop, never a second resolution path:

        1. **Preflight** every repo in the set, mutating nothing. Untracked
           non-gitignored files and *commit* is False ⇒ ``DeadReviewRequiredError``,
           naming the repo (F-5 / AC-R7-01). ``commit=True`` runs the secret scan over
           those files' content; any match ⇒ ``DeadSecretFoundError``, naming the repo.
           A repo carrying local commits with **no remote at all** to receive them
           (``has_commits() and not has_remote()``) ⇒ ``DeadUnpushedCommitsError``,
           naming the repo — removing it would destroy those commits irrecoverably (see
           ``DeadUnpushedCommitsError`` for why this check stays narrower than "any
           commit ahead of the last push"). Any refusal here leaves **every** repo in
           the set untouched (no partial dead).
        2. **Act** on every repo only once every repo has cleared the preflight:
           tracked-but-dirty modifications auto-sync (commit + push, FR-R7 — only
           untracked content is gated), then the repo is removed. A clean tree behaves
           exactly as before.

        Concurrent races are accepted and surfaced by advisory presence; this operation
        never waits for or refuses another session.
        """
        ctx = self._store.get(name)
        if ctx is None:
            raise ContextNotFoundError(f"Context '{name}' not found.")
        if ctx.state != ContextState.ALIVE:
            raise ContextStateError(f"Context '{name}' is not ALIVE. It cannot be made DEAD.")

        # Back-fill repo_url from the on-disk origin remote while the repo still
        # exists (FR-W2-03 b / T-011-08), BEFORE the rmtree below removes it — a
        # DEAD record with a known URL stays portable for a future alive clone.
        backfilled_url: str = self._backfill_repo_url(ctx.repo_slug, ctx.repo_url)

        repo_paths = [(repo.slug, self._repo_path(repo.slug)) for repo in ctx.all_repos()]

        # Phase 1 — preflight EVERY repo before mutating ANY (A16.2: no partial dead).
        for slug, repo_path in repo_paths:
            if repo_path.exists() and self._git.is_git_root(repo_path):
                self._enforce_dead_review_gate(name, repo_path, commit=commit, repo_slug=slug)
                if self._git.has_commits(repo_path) and not self._git.has_remote(repo_path):
                    raise DeadUnpushedCommitsError(
                        f"Context '{name}': repo '{slug}' at '{repo_path}' has local "
                        "commits and no remote configured to receive them. dead() "
                        "refuses to remove it — configure a remote and push first, "
                        "then retry. Nothing was touched."
                    )

        # Phase 2 — git sync + rmtree for every repo. Races are accepted by the
        # NO-LOCKS doctrine.
        branch_before_sync: str | None = None
        for slug, repo_path in repo_paths:
            if not repo_path.exists():
                continue
            if slug == ctx.repo_slug:
                with contextlib.suppress(Exception):
                    branch_before_sync = self._git.current_branch(repo_path)
            if self._git.is_git_root(repo_path):
                if self._git.is_dirty(repo_path):
                    try:
                        self._git.commit_all(repo_path, "chore: auto-sync before dead")
                    except GitSyncError as exc:
                        raise GitSyncError(
                            f"Git sync failed for context '{name}' repo '{slug}' at "
                            f"'{repo_path}'. Resolve the issue and retry dead()."
                        ) from exc
                if self._git.has_remote(repo_path):
                    try:
                        self._git.push(repo_path)
                    except GitSyncError as exc:
                        raise GitSyncError(
                            f"Git push failed for context '{name}' repo '{slug}' at "
                            f"'{repo_path}'. Resolve the issue and retry dead()."
                        ) from exc
            shutil.rmtree(repo_path, onexc=_rmtree_chmod_retry)

        dead_ctx = SpecContextProject(
            name=ctx.name,
            state=ContextState.DEAD,
            repo_slug=ctx.repo_slug,
            repo_url=ctx.repo_url or backfilled_url,
            created_at=ctx.created_at,
            alive_since=None,
            dead_since=_now(),
            current_branch=branch_before_sync,
            associated_repos=ctx.associated_repos,
        )
        self._store.update(dead_ctx)

        return dead_ctx

    # ------------------------------------------------------------------ delete

    def delete(self, name: str) -> None:
        ctx = self._store.get(name)
        if ctx is None:
            raise ContextNotFoundError(f"Context '{name}' not found.")
        if ctx.state == ContextState.ALIVE:
            raise ContextStateError(
                f"Context '{name}' is active. Run 'dadaia context dead {name}' before deleting."
            )
        self._store.delete(name)
        # Bug context-delete-leaves-stale-session-bind: a session record pointing at a
        # DELETED context degrades to unbound via the resolver's own existence check
        # (core.specs_resolver._context_registered) — no marker artifact to clean up
        # here since T-50-04 (SPEC v0.5.0 FR1) retires the bind-epoch marker subsystem.
