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
    ContextLockedError,
    ContextNotFoundError,
    ContextStateError,
    DadaiaError,
    GitSyncError,
)
from dadaia_workspace.core.lock_liveness import is_stale
from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.core.protocols.context_store import ContextStore
from dadaia_workspace.core.protocols.git_client import GitClient
from dadaia_workspace.features.spec_context import lease as _lease
from dadaia_workspace.features.spec_context.locking import (
    context_lock,
    workspace_lock,
)

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
    """Return rule names that match *path*'s content (empty list ⇒ clean).

    Binary / unreadable / unsupported-suffix files are skipped (returns ``[]``).
    Never returns the matched secret value — only the rule name, so callers can
    build a redacted report.
    """
    if path.suffix.lower() not in _SECRET_SCAN_TEXT_SUFFIXES:
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []
    hits: list[str] = []
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

    def _has_implementation_lock(self, name: str) -> bool:
        """Return True if a live (non-stale) lease record exists for the named context.

        v0.1.6: delegates to lease.is_held() (single-record TTL-lease).
        Performs inline GC: if the record is stale, deletes it before returning False.
        """
        rec = _lease.read_record(self._workspace_root, name)
        if rec is None:
            return False
        if is_stale(rec):
            # Inline GC: delete the stale record (no CAS needed for deletion).
            with contextlib.suppress(OSError):
                _lease._record_path(self._workspace_root, name).unlink(missing_ok=True)
            return False
        return True

    # ------------------------------------------------------------------ create

    def create(self, name: str, repo_slug: str, repo_url: str) -> SpecContextProject:
        with workspace_lock(self._workspace_root):
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
        Sets alive_since=now, clears dead_since=None.

        Lock 2 (context_lock) wraps ALL per-repo filesystem operations: git clone,
        branch checkout, branch read, scaffold copytree/mkdir, and AGENTS.md copy.
        Lock 2 is released BEFORE Lock 1 is acquired — never held simultaneously
        (no AB-BA deadlock possible with doctor.fix() which nests L2 inside L1).

        Lock 1 (workspace_lock) wraps only the JSON load→mutate→dump.
        """
        # Pre-flight read (no lock) to get repo_slug for Lock 2 acquisition
        ctx = self._store.get(name)
        if ctx is None:
            raise ContextNotFoundError(f"Context '{name}' not found.")

        # Idempotent: already ALIVE — no-op (no lock needed)
        if ctx.state == ContextState.ALIVE:
            return ctx

        repo_slug = ctx.repo_slug
        repo_path = self._repo_path(repo_slug)

        # Lock 2: serialize ALL per-repo filesystem ops for this slug.
        # Released before Lock 1 is requested — no simultaneous L1+L2 hold here.
        actual_branch: str | None = None
        with context_lock(self._workspace_root, repo_slug):
            # Re-read ctx inside Lock 2 so we use the freshest repo_url / current_branch.
            ctx_l2 = self._store.get(name)
            if ctx_l2 is None:
                raise ContextNotFoundError(f"Context '{name}' not found.")

            # Clone if repo absent
            if not repo_path.exists():
                self._git.clone(ctx_l2.repo_url, repo_path)

            # Checkout target branch if stored in context
            if ctx_l2.current_branch:
                try:
                    self._git.checkout(repo_path, ctx_l2.current_branch)
                except Exception as exc:
                    print(
                        f"WARNING: could not checkout branch {ctx_l2.current_branch!r}: {exc}",
                        file=sys.stderr,
                    )

            # Read actual branch from disk
            try:
                actual_branch = self._git.current_branch(repo_path)
            except Exception:
                actual_branch = None

            # Scaffold specs/. A fresh tree is copied whole; a pre-existing tree is
            # SAFE-PRESERVED — snapshot it to specs_bkp/preserve-<UTC>/ before merging
            # in any missing canonical files (never overwriting operator content). The
            # backup is retained only when the merge actually adds files (FR-S06 path a).
            specs_dir = self._specs_dir(repo_slug)
            if not specs_dir.exists():
                # Fresh scaffold: copy the whole scaffold source tree.
                if _SCAFFOLD_SRC.exists():
                    shutil.copytree(_SCAFFOLD_SRC, specs_dir)
                else:
                    for subdir in ("", "memory", "features"):
                        (specs_dir / subdir).mkdir(parents=True, exist_ok=True)
            else:
                # specs/ already exists — back up first, then merge missing canonical
                # files without overwriting operator content (never silently skip).
                if _SCAFFOLD_SRC.exists():
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
                        # No change — the snapshot is unnecessary; do not litter specs_bkp/.
                        shutil.rmtree(preserved, ignore_errors=True)
                        _log.info("scaffold merge into pre-existing specs/: no missing files found")

            # Copy repo-AGENTS.md template if not already present
            repo_agents_dst = repo_path / "AGENTS.md"
            repo_agents_src = _PUBLIC_DIR / "templates" / "repo-AGENTS.md"
            if not repo_agents_dst.exists() and repo_agents_src.exists():
                shutil.copy2(repo_agents_src, repo_agents_dst)
        # Lock 2 released here — before acquiring Lock 1.

        # Lock 1: load → mutate → dump
        with workspace_lock(self._workspace_root):
            # Re-read inside lock in case another thread updated the state
            ctx_fresh = self._store.get(name)
            if ctx_fresh is None:
                raise ContextNotFoundError(f"Context '{name}' not found.")
            if ctx_fresh.state == ContextState.ALIVE:
                return ctx_fresh  # another thread already transitioned

            alive_ctx = SpecContextProject(
                name=ctx_fresh.name,
                state=ContextState.ALIVE,
                repo_slug=ctx_fresh.repo_slug,
                repo_url=ctx_fresh.repo_url,
                created_at=ctx_fresh.created_at,
                alive_since=_now(),
                dead_since=None,
                current_branch=actual_branch,
            )
            self._store.update(alive_ctx)

        return alive_ctx

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

        Raises ContextLockedError if a live lease record exists for this context.

        Review gate (F-5 / AC-R7-01): if the repo has untracked non-gitignored
        files and *commit* is False, dead() REFUSES — it raises
        ``DeadReviewRequiredError`` listing the files, pushes nothing, and leaves
        the repo on disk untouched. Passing ``commit=True`` is explicit operator
        consent to commit+push those files; before pushing, their content is run
        through the structural secret scan and any match raises
        ``DeadSecretFoundError`` (push blocked, repo untouched). Tracked-but-dirty
        modifications keep the existing auto-sync behaviour (FR-R7: only untracked
        content is gated). A clean tree behaves exactly as before.

        Lock 1 wraps the JSON write (spec_contexts.json update).
        Lock 2 wraps git push and shutil.rmtree (OUTSIDE Lock 1).
        """
        ctx = self._store.get(name)
        if ctx is None:
            raise ContextNotFoundError(f"Context '{name}' not found.")
        if ctx.state != ContextState.ALIVE:
            raise ContextStateError(f"Context '{name}' is not ALIVE. It cannot be made DEAD.")

        # Block if a live lease record exists for this context (T-10b AC-T10b-4 / T-11 AC-T11-9)
        if self._has_implementation_lock(name):
            raise ContextLockedError(
                f"Context '{name}' has an active implementation lock. "
                "Release the implementation session before calling dead()."
            )

        repo_path = self._repo_path(ctx.repo_slug)
        branch_before_sync: str | None = None

        # Review gate (F-5): evaluate untracked content BEFORE any lock, commit,
        # push, or rmtree, so a refusal leaves the repo entirely untouched on disk.
        if repo_path.exists() and self._git.is_git_root(repo_path):
            self._enforce_dead_review_gate(name, repo_path, commit=commit)

        # Git sync + rmtree under Lock 2 (OUTSIDE Lock 1)
        if repo_path.exists():
            import contextlib
            import os

            with context_lock(self._workspace_root, ctx.repo_slug):
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
                # Detect non-writable files before calling rmtree
                non_writable = [
                    str(f)
                    for f in repo_path.rglob("*")
                    if f.is_file() and not os.access(f, os.W_OK)
                ]
                if non_writable:
                    sample = non_writable[:3]
                    raise GitSyncError(
                        f"Cannot remove '{repo_path}': {len(non_writable)} non-writable "
                        f"file(s) found (e.g. {sample}). "
                        f"Run: sudo chown -R $USER '{repo_path}'"
                    )
                shutil.rmtree(repo_path)

        # Lock 1: load → mutate → dump (JSON write only)
        with workspace_lock(self._workspace_root):
            dead_ctx = SpecContextProject(
                name=ctx.name,
                state=ContextState.DEAD,
                repo_slug=ctx.repo_slug,
                repo_url=ctx.repo_url,
                created_at=ctx.created_at,
                alive_since=None,
                dead_since=_now(),
                current_branch=branch_before_sync,
            )
            self._store.update(dead_ctx)

        return dead_ctx

    # ------------------------------------------------------------------ delete

    def delete(self, name: str) -> None:
        with workspace_lock(self._workspace_root):
            ctx = self._store.get(name)
            if ctx is None:
                raise ContextNotFoundError(f"Context '{name}' not found.")
            if ctx.state == ContextState.ALIVE:
                raise ContextStateError(
                    f"Context '{name}' is active. Run 'dadaia context dead {name}' before deleting."
                )
            self._store.delete(name)
