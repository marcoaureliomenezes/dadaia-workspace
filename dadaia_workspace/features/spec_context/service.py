"""SpecContextService — full Spec Context Project lifecycle."""

import contextlib
import logging
import re
import shutil
import sys
from dataclasses import replace
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from typing import Protocol

from dadaia_workspace.core import workspace_layout
from dadaia_workspace.core.cli_line import fix_line, shell_line
from dadaia_workspace.core.exceptions import (
    AssociatedRepoConflictError,
    AssociatedRepoNotFoundError,
    ContextAlreadyExistsError,
    ContextNotFoundError,
    ContextStateError,
    DadaiaError,
    GitSyncError,
    InvalidContextNameError,
    RepoUrlMissingError,
)
from dadaia_workspace.core.models.spec_context import (
    CONTEXT_NAME_RE,
    AssociatedRepo,
    ContextState,
    RepoLiveStatus,
    SpecContextProject,
)
from dadaia_workspace.core.specs_version import read_gitflow
from dadaia_workspace.core.template_history import was_shipped
from dadaia_workspace.features.spec_context import sweep
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
from dadaia_workspace.infrastructure.json_context_store import JsonContextStore
from dadaia_workspace.infrastructure.privacy_check import (
    scan_file_for_secrets as _scan_file_for_secrets,
)

_log = logging.getLogger(__name__)

#: What onboarding writes into a main repo — the only paths ``baseline`` commits.
_ONBOARDING = ("specs", "specs-bkp", "AGENTS.md")
_TAG_RE = re.compile(r"v?(\d+)\.(\d+)\.(\d+)")


class InstallHooks(Protocol):
    """The one git-chokepoint installer ``alive()`` runs in every repo of the set —
    injected by the composition root (P-07: features compose through the container,
    never a sibling import). Installs where absent, never over an existing hook; raises
    when *repo_root* is not a git repository.
    """

    def __call__(self, repo_root: Path) -> object: ...


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
    "commits ahead of upstream" regardless of ``has_remote()`` would
    therefore make dead() refuse right after every ordinary alive()-then-dead() call —
    a false-positive landmine, not a safety net. Only the truly unrecoverable case
    (commits with no remote at all) refuses; a remote-backed repo is left to Phase 2's
    existing auto-push.
    """


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _require_allowlisted(label: str, value: str) -> None:
    if not CONTEXT_NAME_RE.fullmatch(value):
        raise InvalidContextNameError(
            f"invalid {label} {value!r}: use only letters, digits, '-' and '_' — the one "
            "allowlist every verb enforces, so a context that is registered is always usable."
        )


def slug_from_url(url: str) -> str:
    """The ONE slug rule (0.4.8 AC3.2): a clone URL's last path segment minus a trailing
    ``.git``, every char outside ``[A-Za-z0-9_-]`` replaced by ``-`` — so
    ``my.repo.git`` derives ``my-repo`` and any URL with a non-empty tail yields a slug
    the allowlist accepts. The context name defaults to the main repo's slug.
    """
    tail = url.rstrip("/").replace("\\", "/").rsplit("/", 1)[-1].rsplit(":", 1)[-1]
    tail = tail[: -len(".git")] if tail.endswith(".git") else tail
    slug = re.sub(r"[^A-Za-z0-9_-]", "-", tail)
    if not slug:
        raise InvalidContextNameError(f"cannot derive a repo directory name from {url!r}.")
    return slug


def install_git_hooks(repo_root: Path, *, force: bool = False) -> list[Path]:
    """Copy every ``workspace_layout.INSTALLED_GIT_HOOKS`` row into ``<repo>/.git/hooks``.

    The ONE git-chokepoint installer — `dadaia ci install-hook`, `context create` and
    `context alive` are its callers. An installed hook is overwritten only when *force*
    or when it is byte-identical to a version this library shipped (``shipped-hashes.json``
    — an upgrade refreshes it); never the operator's own hook (HOOKS-DRIFT-1 names
    it). Returns the hooks written; raises :class:`FileNotFoundError` when *repo_root* is
    not a git repository.
    """
    hooks_dir = repo_root / ".git" / "hooks"
    if not hooks_dir.is_dir():
        raise FileNotFoundError(f"{hooks_dir} not found (is this a git repository?)")
    scripts = workspace_layout.public_scripts_dir()
    written = []
    for target, source in workspace_layout.INSTALLED_GIT_HOOKS:
        dest, shipped = hooks_dir / target, scripts / source
        old = dest.read_text(encoding="utf-8", errors="replace") if dest.exists() else None
        if (
            force
            or old is None
            or (
                old != shipped.read_text(encoding="utf-8")
                and was_shipped(old, f"scripts/{source}", scripts.parent / "templates")
            )
        ):
            shutil.copyfile(shipped, dest)
            dest.chmod(0o755)
            written.append(dest)
    return written


class SpecContextService:
    def __init__(
        self,
        context_store: JsonContextStore,
        git_client: GitSubprocessClient,
        workspace_root: Path,
        install_hooks: InstallHooks,
    ) -> None:
        self._store = context_store
        self._git = git_client
        self._workspace_root = workspace_root
        self._install_hooks = install_hooks

    def _repos_dir(self) -> Path:
        return self._workspace_root / "repos"

    def _repo_path(self, repo_slug: str) -> Path:
        return self._repos_dir() / repo_slug

    # ------------------------------------------------------------------ create

    def create(
        self,
        main_repo_url: str,
        *,
        name: str | None = None,
        associated_urls: tuple[str, ...] = (),
    ) -> SpecContextProject:
        """Make a context ALIVE from its clone URLs in ONE transactional step (0.4.8 FR3).

        Every slug comes from :func:`slug_from_url`; *name* defaults to the main repo's.
        The record is validated first, then each repo is cloned — or adopted when
        ``repos/<slug>`` already holds a checkout whose ``origin`` is that URL — and
        hooked. Any failure removes every directory this call created and writes no
        record, so the corrected command re-runs cleanly (R3). Writes nothing inside a
        repo but the hook.
        """
        main_slug = slug_from_url(main_repo_url)
        ctx = SpecContextProject(
            name=name or main_slug,
            state=ContextState.ALIVE,
            repo_slug=main_slug,
            repo_url=main_repo_url,
            created_at=_now(),
            alive_since=_now(),
            dead_since=None,
            associated_repos=tuple(AssociatedRepo(slug_from_url(u), u) for u in associated_urls),
        )
        self._validate(ctx)
        created: list[Path] = []
        try:
            for repo in ctx.all_repos():
                dest = self._repo_path(repo.slug)
                if dest.exists():
                    if not self._git.is_git_root(dest) or self._git.remote_url(dest) != repo.url:
                        raise ContextStateError(
                            f"repos/{repo.slug} exists but is not a checkout of {repo.url} — "
                            "move it away or pick another URL."
                        )
                else:
                    self._git.clone(repo.url, dest)
                    created.append(dest)
                self._install_hooks(dest)
        except BaseException:
            for dest in created:
                sweep.rmtree(dest)
            raise
        branch: str | None = None
        with contextlib.suppress(Exception):
            branch = self._git.current_branch(self._repo_path(main_slug))
        ctx = replace(ctx, current_branch=branch)
        self._store.save(ctx)
        return ctx

    def register(self, ctx: SpecContextProject) -> SpecContextProject:
        """Insert an already-built record (``dadaia import``) — validated exactly as
        ``create`` validates, nothing materialized."""
        self._validate(ctx)
        self._store.save(ctx)
        return ctx

    def _validate(self, ctx: SpecContextProject) -> None:
        """The ONE refusal seam every inserted record passes: name and every slug
        allowlisted (``InvalidContextNameError``), name new (``ContextAlreadyExistsError``),
        every slug free — not the main slug repeated, not given twice, not owned by
        another context (``AssociatedRepoConflictError``). Writes nothing."""
        _require_allowlisted("context name", ctx.name)
        if self._store.get(ctx.name) is not None:
            raise ContextAlreadyExistsError(
                f"Context '{ctx.name}' already exists. Use a different name."
            )
        self._refuse_slug(ctx.name, ctx.repo_slug, ctx.repo_url)
        seen: set[str] = set()
        for repo in ctx.associated_repos:
            if repo.slug == ctx.repo_slug:
                raise AssociatedRepoConflictError(
                    f"'{repo.slug}' is context '{ctx.name}''s own main repo slug — it is "
                    "always included via all_repos() and can never also be an associated repo."
                )
            if repo.slug in seen:
                raise AssociatedRepoConflictError(
                    f"associated repo slug '{repo.slug}' given more than once."
                )
            seen.add(repo.slug)
            self._refuse_slug(ctx.name, repo.slug, repo.url)

    # ------------------------------------------------------------------ associated repos (FR17)

    def _refuse_slug(self, name: str, slug: str, url: str) -> None:
        """Refuse *slug* for *name* unless allowlisted, obtainable and unowned by any other
        context (its main repo or an associated repo): every ``repos/<slug>`` checkout lives
        in the ONE namespace ``alive()`` clones into and ``dead()`` walks and destroys, so
        the two writers into it — ``register`` and ``add_repo`` — guard here. Obtainable
        means a clone *url* or an existing ``repos/<slug>`` checkout ``alive()`` adopts."""
        _require_allowlisted("repo slug", slug)
        checkout = self._repo_path(slug)
        if not url and not (checkout.is_dir() and self._git.is_git_root(checkout)):
            raise RepoUrlMissingError(
                f"'{slug}' has no clone URL and no checkout at repos/{slug} — "
                "'context alive' could never obtain it."
            )
        for other in self._store.list_all():
            if other.name == name:
                continue
            if other.repo_slug == slug or any(r.slug == slug for r in other.associated_repos):
                raise AssociatedRepoConflictError(
                    f"'{slug}' is already owned by context '{other.name}' (as its own main "
                    "repo or one of its associated repos). 'repos/<slug>' is a namespace every "
                    f"context shares — registering it on '{name}' too would let 'dadaia "
                    f"context dead {name}' commit, push and delete '{other.name}''s working "
                    "tree. Choose a different slug, or coordinate with the owning context first."
                )

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
        self._refuse_slug(name, slug, repo_url)
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

    def _backfilled(self, ctx: SpecContextProject) -> SpecContextProject:
        """*ctx* with EVERY repo's empty URL back-filled from its on-disk origin — the one
        back-fill ``alive`` and ``dead`` share (bug
        context-dead-destroys-associated-repo-without-url: a main-repo-only back-fill let
        ``dead`` delete an associated checkout whose record kept url "")."""
        return replace(
            ctx,
            repo_url=self._backfill_repo_url(ctx.repo_slug, ctx.repo_url),
            associated_repos=tuple(
                AssociatedRepo(slug=r.slug, url=self._backfill_repo_url(r.slug, r.url))
                for r in ctx.associated_repos
            ),
        )

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

        `context show`, `context list --json` and the export branch refresh all resolve a repo's on-disk presence and live checked-out
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
        export render for "this context's repos" (FR18)."""
        return [self.repo_live_status(repo) for repo in ctx.all_repos()]

    # ------------------------------------------------------------------ alive (T-10b / T-11)

    def alive(self, name: str) -> SpecContextProject:
        """Transition a context from DEAD to ALIVE; clone every repo in the set if absent.

        Idempotent: calling alive() on an already-ALIVE context is a no-op beyond
        re-confirming every repo is present (no error, no re-clone of anything already
        on disk). Sets alive_since=now and clears dead_since. Concurrent races are
        accepted and surface through git; this operation never acquires a lock.

        FR16/A16.1/A16.3: every repo in the set — the main repo first, then each
        associated repo in order (``SpecContextProject.all_repos()``, the one accessor,
        A15.3) — is cloned if missing and gets the pre-push hook. Only the MAIN repo
        receives checkout and branch tracking. alive() writes no specs and commits
        nothing (0.4.8 AC3.7): the working tree is exactly what the remote holds.
        """
        ctx = self._store.get(name)
        if ctx is None:
            raise ContextNotFoundError(f"Context '{name}' not found.")

        for repo in self._backfilled(ctx).all_repos():
            repo_dest = self._repo_path(repo.slug)
            if not repo_dest.exists():
                if not repo.url:
                    if repo.slug == ctx.repo_slug:
                        steps = (f"delete {name}", f"create {name} --main-repo <clone-url>")
                    else:
                        steps = (
                            f"repo remove {name} {repo.slug}",
                            f"repo add {name} {repo.slug} --url <clone-url>",
                        )
                    ws = self._workspace_root
                    fix = " && ".join(fix_line(ws, "context", *step.split()) for step in steps)
                    raise RepoUrlMissingError(
                        f"'{repo.slug}' has no clone URL and no checkout at repos/{repo.slug} "
                        f"— 'context alive {name}' cannot obtain it.\nfix: {fix}"
                    )
                self._git.clone(repo.url, repo_dest)
            self._install_hooks(repo_dest)

        if ctx.state == ContextState.ALIVE:
            return ctx

        repo_slug = ctx.repo_slug
        repo_path = self._repo_path(repo_slug)

        actual_branch: str | None = None

        if ctx.current_branch:
            try:
                self._git.checkout(repo_path, ctx.current_branch)
            except Exception as exc:
                print(
                    f"WARNING: could not checkout branch {ctx.current_branch!r}: {exc}",
                    file=sys.stderr,
                )

        try:
            actual_branch = self._git.current_branch(repo_path)
        except Exception:
            actual_branch = None

        ctx_fresh = self._store.get(name)
        if ctx_fresh is None:
            raise ContextNotFoundError(f"Context '{name}' not found.")
        if ctx_fresh.state == ContextState.ALIVE:
            return ctx_fresh
        alive_ctx = replace(
            self._backfilled(ctx_fresh),
            state=ContextState.ALIVE,
            alive_since=_now(),
            dead_since=None,
            current_branch=actual_branch,
        )
        self._store.update(alive_ctx)

        return alive_ctx

    def refresh_hooks(self) -> None:
        """Install, or refresh a shipped copy of, every ALIVE repo's git hooks (upgrade)."""
        for ctx in self._store.list_all():
            for repo in ctx.all_repos() if ctx.state == ContextState.ALIVE else ():
                with contextlib.suppress(FileNotFoundError):
                    self._install_hooks(self._repo_path(repo.slug))

    # ------------------------------------------------------------------ baseline

    def baseline(self, name: str, *, message: str = "chore: publish the dadaia specs") -> str:
        """Publish an onboarded project (ADRs 0035, 0042) and return its work branch: ensure
        the gitflow's principal and integration branches on ``origin``, cut the work branch
        from the integration branch, commit only the onboarding paths, push it with
        upstream. Invoking it is the consent; a published project is a no-op (``""``)."""
        repo = self._repo_path(self.show(name).repo_slug)
        if not repo.is_dir() or not self._git.is_git_root(repo):
            raise ContextStateError(f"Context '{name}' has no Git repository at '{repo}'.")
        git = partial(self._git.git, repo)
        try:  # git's own identity rule (env, config, auto-detection) — never a second one
            for ident in ("GIT_AUTHOR_IDENT", "GIT_COMMITTER_IDENT"):
                git("var", ident)
        except GitSyncError as exc:
            key = "user.name" if "ident name" in str(exc) else "user.email"
            fix = shell_line("git", "-C", str(repo), "config", key, f"<{key}>")
            raise ContextStateError(f"Context '{name}': {exc}\nfix: {fix}") from None
        self._require_publishable(name, repo)
        try:
            git("fetch", "--prune", "--tags", "origin")
            flow, _ = read_gitflow(repo / "specs")
            if self._git.published(repo, flow.integration):
                return ""
            heads = git("for-each-ref", "--format=%(refname:lstrip=3)", "refs/remotes/origin")
            base = f"origin/{flow.principal}"
            if flow.principal not in heads.split():
                tree = git("hash-object", "-t", "tree", "--stdin", stdin="")
                base = git("commit-tree", tree, "-m", f"chore: birth of {flow.principal}")
            births = [  # by refspec: a local head is the operator's, never reset
                f"{git('rev-parse', base)}:refs/heads/{branch}"
                for branch in (flow.principal, flow.integration)
                if branch not in heads.split()
            ]
            if births:
                git("push", "origin", *births)
            tags = (_TAG_RE.fullmatch(t) for t in git("tag", "--sort=-v:refname").split())
            last = next((m for m in tags if m), None)
            patch = f"{last[1]}.{last[2]}.{int(last[3]) + 1}" if last else "0.1.0"
            work = f"{flow.work_prefix}{patch}"
            if self._git.current_branch(repo) != work:
                git("checkout", "--no-track", "-b", work, f"origin/{flow.integration}")
            paths = [p for p in _ONBOARDING if git("ls-files", "--", p) or (repo / p).exists()]
            self._git.commit_paths(repo, message, paths)
            self._git.push(repo)
        except GitSyncError as exc:
            rerun = fix_line(self._workspace_root, "context", "baseline", name)
            raise GitSyncError(f"{exc}\nfix: {rerun}") from None
        return work

    def _require_publishable(self, name: str, repo: Path) -> None:
        """Refuse, before any write, a change outside the onboarding paths (born repos:
        an unborn clone's foreign files are never committed) or a secret in an untracked
        file the publish would commit — each with a stash fix naming the real paths."""
        untracked = self._git.list_untracked(repo)
        changed = (
            [*self._git.git(repo, "diff", "--name-only", "-z", "HEAD").split("\0"), *untracked]
            if self._git.has_commits(repo)
            else []
        )
        foreign = sorted({p for p in changed if p and p.split("/")[0] not in _ONBOARDING})
        flagged = {
            rel: sorted(set(hits))
            for rel in untracked
            if rel.split("/")[0] in _ONBOARDING and (hits := _scan_file_for_secrets(repo / rel))
        }
        refusal = (
            f"changes outside {', '.join(_ONBOARDING)} are not published."
            if foreign
            else "secret scan blocked the publish (values redacted):\n"
            + "\n".join(f"  {rel}: {', '.join(hits)}" for rel, hits in flagged.items())
        )
        if foreign or flagged:
            fix = shell_line(
                "git", "-C", str(repo), "stash", "push", "-u", "--", *foreign or flagged
            )
            error = ContextStateError if foreign else DeadSecretFoundError
            raise error(f"Context '{name}': {refusal}\nfix: {fix}")

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
                f"'{repo_slug}' at '{repo_path}'; consent to committing its changes.\n"
                f"fix: {fix_line(self._workspace_root, 'context', 'dead', name, '--commit')}"
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
                "Review them, then delete/gitignore them or consent to committing them.\n"
                f"fix: {fix_line(self._workspace_root, 'context', 'dead', name, '--commit')}"
            )

        # commit=True: scan the content of the files we are about to newly commit.
        flagged = {
            rel: sorted(set(hits))
            for rel in untracked
            if (repo_path / rel).is_file() and (hits := _scan_file_for_secrets(repo_path / rel))
        }
        if flagged:
            report = "\n".join(f"  {rel}: {', '.join(hits)}" for rel, hits in flagged.items())
            fix = shell_line("git", "-C", str(repo_path), "stash", "push", "-u", "--", *flagged)
            raise DeadSecretFoundError(
                f"Context '{name}': repo '{repo_slug}' secret scan blocked dead() "
                f"--commit. {len(flagged)} untracked file(s) match a secret/identifier "
                "rule (values redacted):\n"
                f"{report}\n"
                f"Nothing was pushed.\nfix: {fix}"
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

        Concurrent races are accepted and surface through git; this operation
        never waits for or refuses another session.
        """
        ctx = self._store.get(name)
        if ctx is None:
            raise ContextNotFoundError(f"Context '{name}' not found.")
        if ctx.state != ContextState.ALIVE:
            raise ContextStateError(f"Context '{name}' is not ALIVE. It cannot be made DEAD.")

        # Back-fill every URL from the on-disk origin while the repos still exist
        # (FR-W2-03 b), BEFORE the rmtree below — a DEAD record stays re-obtainable.
        ctx = self._backfilled(ctx)
        repo_paths = [(repo.slug, self._repo_path(repo.slug)) for repo in ctx.all_repos()]

        # Phase 1 — preflight EVERY repo before mutating ANY (A16.2: no partial dead).
        for repo in ctx.all_repos():
            slug, repo_path = repo.slug, self._repo_path(repo.slug)
            if repo_path.exists() and not repo.url:
                raise RepoUrlMissingError(
                    f"Context '{name}': repo '{slug}' has no clone URL (no origin remote) — "
                    "removing it would leave nothing 'context alive' could clone back. "
                    f"Nothing was touched.\nfix: git -C repos/{slug} remote add origin <clone-url>"
                )
            if repo_path.exists() and self._git.is_git_root(repo_path):
                self._enforce_dead_review_gate(name, repo_path, commit=commit, repo_slug=slug)
                if self._git.has_commits(repo_path) and not self._git.has_remote(repo_path):
                    raise DeadUnpushedCommitsError(
                        f"Context '{name}': repo '{slug}' at '{repo_path}' has local "
                        "commits and no remote configured to receive them. dead() "
                        "refuses to remove it — configure a remote and push first, "
                        "then retry. Nothing was touched.\nfix: "
                        + shell_line("git", "-C", str(repo_path), "remote", "add", "origin")
                        + " <clone-url>"
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
            # An unborn clone has nothing published to sync; a born one has a remote
            # (Phase 1) to receive its dirty tree.
            if self._git.is_git_root(repo_path) and self._git.has_commits(repo_path):
                try:
                    if self._git.is_dirty(repo_path):
                        self._git.commit_all(repo_path, "chore: auto-sync before dead")
                    self._git.push(repo_path)
                except GitSyncError as exc:
                    fix = shell_line("git", "-C", str(repo_path), "remote", "set-url", "origin")
                    raise GitSyncError(
                        f"Git sync failed for context '{name}' repo '{slug}'; nothing was "
                        f"removed.\n{exc}\nfix: {fix} <clone-url>"
                    ) from exc
            sweep.rmtree(repo_path)

        dead_ctx = SpecContextProject(
            name=ctx.name,
            state=ContextState.DEAD,
            repo_slug=ctx.repo_slug,
            repo_url=ctx.repo_url,
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
        # (core.invocation._context_registered) — no marker artifact to clean up
        # here since T-50-04 (SPEC v0.5.0 FR1) retires the bind-epoch marker subsystem.
