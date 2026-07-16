"""SpecContextService — full Spec Context Project lifecycle."""

import contextlib
import logging
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
from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
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
        if self._store.get(name) is not None:
            raise ContextAlreadyExistsError(
                f"Context '{name}' already exists. Use a different name."
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

    # ------------------------------------------------------------------ alive (T-10b / T-11)

    def alive(self, name: str) -> SpecContextProject:
        """Transition a context from DEAD to ALIVE; clone repo if absent.

        Idempotent: calling alive() on an already-ALIVE context is a no-op (no error).
        Sets alive_since=now and clears dead_since. Concurrent races are accepted and
        surfaced by advisory presence; this operation never acquires a lock.
        """
        ctx = self._store.get(name)
        if ctx is None:
            raise ContextNotFoundError(f"Context '{name}' not found.")

        if ctx.state == ContextState.ALIVE:
            return ctx

        repo_slug = ctx.repo_slug
        repo_path = self._repo_path(repo_slug)

        actual_branch: str | None = None
        backfilled_url: str = ctx.repo_url
        ctx_latest = self._store.get(name)
        if ctx_latest is None:
            raise ContextNotFoundError(f"Context '{name}' not found.")

        if not repo_path.exists():
            self._git.clone(ctx_latest.repo_url, repo_path)

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

        specs_dir = self._specs_dir(repo_slug)
        if not specs_dir.exists():
            if _SCAFFOLD_SRC.exists():
                shutil.copytree(_SCAFFOLD_SRC, specs_dir)
            else:
                for subdir in ("", "memory", "features"):
                    (specs_dir / subdir).mkdir(parents=True, exist_ok=True)
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
            else:
                shutil.rmtree(preserved, ignore_errors=True)
                _log.info("scaffold merge into pre-existing specs/: no missing files found")

        repo_agents_dst = repo_path / "AGENTS.md"
        repo_agents_src = _PUBLIC_DIR / "templates" / "repo-AGENTS.md"
        if not repo_agents_dst.exists() and repo_agents_src.exists():
            shutil.copy2(repo_agents_src, repo_agents_dst)

        # Commit the scaffold alive() itself just wrote (bug alive-scaffold-blocks-dead,
        # validation-027 F-06): leaving tool-created files untracked made an immediate
        # dead() refuse via the untracked-consent guard, so create->alive->dead could
        # never complete on a fresh context. Only tool-authored files are involved here;
        # operator-created untracked files still hit dead()'s guard as designed (F-5).
        with contextlib.suppress(Exception):
            if self._git.is_git_root(repo_path) and self._git.is_dirty(repo_path):
                self._git.commit_all(
                    repo_path, "chore(scaffold): dadaia context alive specs baseline"
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
            # canonical post-alive state — success, not refusal. Only a dirty tree
            # on top of existing history refuses: operator content must never be
            # swept into a "baseline" commit.
            if self._git.is_dirty(repo_path):
                raise ContextStateError(
                    f"Context '{name}' already has Git history with uncommitted changes; "
                    "baseline never commits on top of existing history. Commit or stash "
                    "your changes first."
                )
            if push:
                if not self._git.has_remote(repo_path):
                    raise GitSyncError(f"Context '{name}' has no remote; baseline cannot push.")
                self._git.push(repo_path)
            return ctx
        if not self._git.is_dirty(repo_path):
            raise ContextStateError(
                f"Context '{name}' has no scaffold content to commit as a baseline."
            )

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

    # ------------------------------------------------------------------ dead (T-10b / T-11)

    def _enforce_dead_review_gate(self, name: str, repo_path: Path, *, commit: bool) -> None:
        """Gate dead() on untracked content (F-5 / AC-R7-01).

        No untracked files ⇒ no-op (clean-tree / tracked-only path unchanged).
        Untracked files + not *commit* ⇒ raise DeadReviewRequiredError (refuse).
        Untracked files + *commit* ⇒ secret-scan their content; any match raises
        DeadSecretFoundError. This runs before any commit/push/rmtree so a refusal
        leaves the repo untouched.
        """
        try:
            untracked = self._git.list_untracked(repo_path)
        except Exception:
            # Fail-closed for the gate: if we cannot enumerate untracked files we
            # cannot prove the tree is clean. Without consent, refuse.
            if commit:
                return
            raise DeadReviewRequiredError(
                f"Context '{name}': could not verify the working tree of '{repo_path}'. "
                "Re-run with --commit to consent to committing+pushing any changes, "
                "or clean the tree first."
            ) from None

        if not untracked:
            return  # clean tree (no untracked files) — behave exactly as before

        if not commit:
            shown = untracked[:20]
            more = "" if len(untracked) <= 20 else f"\n  ... and {len(untracked) - 20} more"
            listing = "\n".join(f"  {f}" for f in shown)
            raise DeadReviewRequiredError(
                f"Context '{name}' has {len(untracked)} untracked file(s) that dead() "
                f"would otherwise commit and push WITHOUT review:\n"
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
                f"Context '{name}': secret scan blocked dead() --commit. "
                f"{len(flagged)} untracked file(s) match a secret/identifier rule "
                "(values redacted):\n"
                f"{report}\n"
                "Remove or redact the flagged content, then re-run. Nothing was pushed."
            )

    def dead(self, name: str, *, commit: bool = False) -> SpecContextProject:
        """Transition a context from ALIVE to DEAD; sets dead_since, removes repo.

        Review gate (F-5 / AC-R7-01): if the repo has untracked non-gitignored
        files and *commit* is False, dead() REFUSES — it raises
        ``DeadReviewRequiredError`` listing the files, pushes nothing, and leaves
        the repo on disk untouched. Passing ``commit=True`` is explicit operator
        consent to commit+push those files; before pushing, their content is run
        through the structural secret scan and any match raises
        ``DeadSecretFoundError`` (push blocked, repo untouched). Tracked-but-dirty
        modifications keep the existing auto-sync behaviour (FR-R7: only untracked
        content is gated). A clean tree behaves exactly as before.

        Concurrent races are accepted and surfaced by advisory presence; this operation
        never waits for or refuses another session.
        """
        ctx = self._store.get(name)
        if ctx is None:
            raise ContextNotFoundError(f"Context '{name}' not found.")
        if ctx.state != ContextState.ALIVE:
            raise ContextStateError(f"Context '{name}' is not ALIVE. It cannot be made DEAD.")

        repo_path = self._repo_path(ctx.repo_slug)
        branch_before_sync: str | None = None
        # Back-fill repo_url from the on-disk origin remote while the repo still
        # exists (FR-W2-03 b / T-011-08), BEFORE the rmtree below removes it — a
        # DEAD record with a known URL stays portable for a future alive clone.
        backfilled_url: str = self._backfill_repo_url(ctx.repo_slug, ctx.repo_url)

        # Review gate (F-5): evaluate untracked content before any commit,
        # push, or rmtree, so a refusal leaves the repo entirely untouched on disk.
        if repo_path.exists() and self._git.is_git_root(repo_path):
            self._enforce_dead_review_gate(name, repo_path, commit=commit)

        # Git sync + rmtree. Races are accepted by the NO-LOCKS doctrine.
        if repo_path.exists():
            with contextlib.suppress(Exception):
                branch_before_sync = self._git.current_branch(repo_path)
            if self._git.is_git_root(repo_path):
                if self._git.is_dirty(repo_path):
                    try:
                        self._git.commit_all(repo_path, "chore: auto-sync before dead")
                    except GitSyncError as exc:
                        raise GitSyncError(
                            f"Git sync failed for context '{name}' at '{repo_path}'. "
                            "Resolve the issue and retry dead()."
                        ) from exc
                if self._git.has_remote(repo_path):
                    try:
                        self._git.push(repo_path)
                    except GitSyncError as exc:
                        raise GitSyncError(
                            f"Git push failed for context '{name}' at '{repo_path}'. "
                            "Resolve the issue and retry dead()."
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
