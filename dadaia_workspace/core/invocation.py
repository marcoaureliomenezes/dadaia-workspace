"""One Invocation — the single session/context/root/mode resolution authority.

Release 0.5.1 candidate K1 (2026-08-28 deepening audit): "which session, which
context, which root, which mode" used to be answered by eight deciders reading the
same files with four different staleness rules (``core.specs_resolver.resolve_context``,
``cli._specs_resolution`` re-adding two rungs, ``container.resolve_context`` (0
callers), ``container._context_specs_dir`` (a fifth rung), ``hooks.ctx_inject``'s own
two-step resolution, ``hooks.sdd_post_gate._bound_context``, ``hooks.sdd_gate``'s
``_context_slug``/``_resolve_mode``, and ``cli.commands.context``'s own session
loader+staleness check) — and the session record was keyed by one session id and read
back by another. This module is the replacement, not a ninth layer on top: everything
above now calls :func:`resolve` once and reads the fields it needs off the returned
:class:`Invocation`.

the root `AGENTS.md` map §3 context-resolution law, verbatim, plus rung 0 (a caller's own explicit
input, which the law has always allowed a verb to pass):

    rung 0  ``explicit``, or the context derived from an explicit write TARGET
            (``target_path``) under ``<workspace_root>/repos/<slug>/``.
    rung 1  ``DADAIA_CONTEXT``.
    rung 2  this session's own LIVE session record, keyed by the harness-native
            session id (:func:`resolve_session_id` — payload first, then env; never
            ``DADAIA_SESSION_ID``, which is identity-override only, resolved
            separately).
    rung 3  the repo containing the current working directory.

**The root-vs-target bug** (open bug
``sdd-gate-memory-phase-resolves-empty-when-cwd-is-a-linked-worktree-outside-repos``):
every rung above is only as correct as the ``workspace_root`` they all share, and the
OLD ladder derived that root from ``cwd`` alone — even when a ``target_path`` was
already known (the gate's own write target). A cwd sitting inside a nested, ALSO
sentinel-bearing sandbox workspace (a scratch worktree with its own
``.dadaia/states/spec_contexts.json``, e.g. a throwaway workspace built for a test or a
sub-agent) walks UP from that cwd and stops at the nested sandbox root — the wrong one
— even though the actual write target lives under a different, real, outer root
entirely. :func:`resolve` fixes this structurally: when a ``target_path`` is given, the
workspace root is walked from the TARGET's own location first (which structurally can
only land on the root that actually owns it), and only falls back to a cwd-based walk
when no target is given or the target-based walk fails. One root, resolved once,
consistently, for every rung in the same call — not "root from cwd, context from
target" as two independently-wrong answers that happen to usually agree.

Session records (bind/read/touch — GC lives in ``features.spec_context.doctor``, out of
K1 scope) are owned by :mod:`dadaia_workspace.core.session_store`, moved here from
``features.spec_context.session_identity`` in the same release: this module needs to
read a session record directly, and ``core`` cannot import ``features``.

Layering: a pure ``core`` leaf. It performs file I/O (the workspace/session/registry/
release-state reads every rung needs) — an authorized exception in
``tests/contract/test_core_file_io_purity.py`` (architect A9), same precedent as
``specs_resolver``/``workspace_resolver`` before it. No upward import (constitution
§6): hooks (P-12) and the CLI seam (``cli._specs_resolution``) are its sanctioned
direct importers (``bind-resolution-seam-is-a-single-home``, ZERO ``ignore_imports``).
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from dadaia_workspace.core.exceptions import WorkspaceNotInitializedError
from dadaia_workspace.core.models.spec_context import CONTEXT_NAME_RE
from dadaia_workspace.core.session_store import live_session
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root

__all__ = [
    "CONTEXT_NAME_RE",
    "HARNESS_SESSION_ID_ENV_VARS",
    "Bind",
    "Invocation",
    "all_repos",
    "alive_context_trees",
    "context_name_for_repo_slug",
    "repo_slug_for_context",
    "repo_slug_under_repos",
    "resolve",
    "resolve_bind",
    "resolve_context_specs_dir",
    "resolve_specs_dir",
    "resolve_session_id",
    "sanitize_session_id",
]

#: Harness-native session-id env vars, in resolution order — Claude before Codex.
#: ``CODEX_THREAD_ID`` is ordered AFTER ``CODEX_SESSION_ID`` deliberately: a modern
#: Codex tool subprocess exposes ``CODEX_THREAD_ID`` *instead of* ``CODEX_SESSION_ID``,
#: but when both happen to be present ``CODEX_SESSION_ID`` remains preferred.
HARNESS_SESSION_ID_ENV_VARS: tuple[str, ...] = (
    "CLAUDE_CODE_SESSION_ID",
    "CODEX_SESSION_ID",
    "CODEX_THREAD_ID",
)

_SESSION_ID_STRIP = re.compile(r"[^A-Za-z0-9_-]")


@dataclass(frozen=True)
class Bind:
    """The SESSION's own binding: the context it named, and every repo slug that
    context owns (its main repo plus its associated repos — ``all_repos()``).

    Unbound is ``context_name=None`` with an empty ``repos``: an unbound session is
    never scope-blocked, because the gate cannot attribute its writes to any context.
    """

    context_name: str | None = None
    repos: frozenset[str] = frozenset()


@dataclass(frozen=True)
class Invocation:
    """One resolved answer to "which session, which context, which root, which mode".

    ``workspace_root``/``context_name``/``specs_dir`` are ``None`` when unresolvable
    (every rung fails soft — matches the prior ladders' contract). ``repo_slug`` is the
    ``repos/<slug>`` on-disk directory for ``context_name`` (identical to
    ``context_name`` unless the registry names a different one). ``bind`` is the
    SESSION's OWN binding — a
    different question from ``context_name``, which the write TARGET may decide: the
    gate's scope rule compares the two. ``rung`` names which rung
    supplied ``context_name`` (``"explicit"``, ``"target_path"``, ``"env"``,
    ``"session"``, ``"cwd"``, or ``"none"``) — diagnostic, never consulted for policy.
    """

    workspace_root: Path | None
    session_id: str | None
    context_name: str | None
    repo_slug: str | None
    specs_dir: Path | None
    bind: Bind
    rung: str


# ---------------------------------------------------------------------------
# Session id — the ONE rule (payload first, then env; DADAIA_SESSION_ID overrides both).
# ---------------------------------------------------------------------------


def sanitize_session_id(raw: str | None) -> str:
    """Strip a session id to ``[A-Za-z0-9_-]`` (CWE-22 path-traversal defense)."""
    return _SESSION_ID_STRIP.sub("", raw or "")


def resolve_session_id(
    payload: Mapping[str, object] | None,
    env: Mapping[str, str],
    *,
    default: str = "",
) -> str:
    """Resolve the harness-native session id, sanitized — the ONE session-id rule.

    Order: the explicit ``DADAIA_SESSION_ID`` override (eval-flow contract, always
    first) -> the hook payload's ``session_id`` field (the harness's live truth for
    THIS invocation) -> :data:`HARNESS_SESSION_ID_ENV_VARS` (which may be INHERITED
    from a parent shell and stale) -> *default*. A CLI-minted ``sess_*`` id is never a
    member of this rule — minting (when a caller has no resolvable identity at all and
    still needs one to persist a record under, e.g. ``dadaia context bind --print-env``
    in a plain shell) is a distinct, write-side concern the CLI bind command owns for
    itself; it is never something a READER of session state should invent.
    """
    candidate = env.get("DADAIA_SESSION_ID") or str((payload or {}).get("session_id") or "")
    if not candidate:
        for name in HARNESS_SESSION_ID_ENV_VARS:
            candidate = env.get(name) or ""
            if candidate:
                break
    sanitized = sanitize_session_id(candidate)
    return sanitized or default


# ---------------------------------------------------------------------------
# Registry — context NAME <-> repo SLUG (single home, replaces the mirrored lookups).
# ---------------------------------------------------------------------------


def _registry_contexts(workspace_root: Path) -> list[dict[str, object]]:
    """Read the context registry's ``contexts`` list, fail-soft to ``[]``."""
    registry = workspace_root / ".dadaia" / "states" / "spec_contexts.json"
    try:
        data = json.loads(registry.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, ValueError):
        return []
    contexts = data.get("contexts", []) if isinstance(data, dict) else []
    return [e for e in contexts if isinstance(e, dict)] if isinstance(contexts, list) else []


def alive_context_names(workspace_root: Path) -> list[str]:
    """The NAME of every ALIVE context — what ``context bind`` accepts — fail-soft to
    ``[]`` (F008: the ONE fail-soft registry read family lives here — hooks import it,
    never a private re-parse; ``JsonContextStore`` stays the schema-gated CRUD authority)."""
    return [
        str(entry["name"])
        for entry in _registry_contexts(workspace_root)
        if str(entry.get("state", "")).lower() == "alive" and entry.get("name")
    ]


def _context_registered(workspace_root: Path, name: str) -> bool:
    """True while *name* is registered (missing registry -> ``False``; unreadable fails
    OPEN -> ``True``, so a transient FS hiccup never invalidates every live bind)."""
    registry = workspace_root / ".dadaia" / "states" / "spec_contexts.json"
    if not registry.is_file():
        return False
    try:
        data = json.loads(registry.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, ValueError):
        return True
    contexts = data.get("contexts", []) if isinstance(data, dict) else []
    if not isinstance(contexts, list):
        return True
    return any(
        isinstance(entry, dict) and (entry.get("name") == name or entry.get("repo_slug") == name)
        for entry in contexts
    )


def repo_slug_for_context(workspace_root: Path, name: str) -> str:
    """The ``repos/<slug>`` dir a context NAME lives in; falls back to *name* unchanged."""
    for entry in _registry_contexts(workspace_root):
        if entry.get("name") == name:
            slug = entry.get("repo_slug") or entry.get("repo")
            return slug if isinstance(slug, str) and slug else name
    return name


def context_name_for_repo_slug(workspace_root: Path, slug: str) -> str:
    """Inverse of :func:`repo_slug_for_context`: the NAME whose repo is *slug*.

    *slug* also matches an **associated** repo's slug (A16.4), resolving the same
    OWNING context's name a match on the main ``repo_slug`` would — a resolution walk
    starting inside ``repos/<associated-slug>/`` lands on the context, never treats the
    associated repo as a second context of its own (an associated repo carries no
    ``specs/`` bind).
    """
    for entry in _registry_contexts(workspace_root):
        entry_slug = entry.get("repo_slug") or entry.get("repo")
        if entry_slug == slug:
            name = entry.get("name")
            return name if isinstance(name, str) and name else slug
        associated = entry.get("associated_repos")
        if isinstance(associated, list) and any(
            isinstance(assoc, dict) and assoc.get("slug") == slug for assoc in associated
        ):
            name = entry.get("name")
            return name if isinstance(name, str) and name else slug
    return slug


def repo_slug_under_repos(workspace_root: Path, path: Path) -> str | None:
    """First path component of *path* under ``<workspace_root>/repos/``, sanitized
    (CWE-22/CWE-59), or ``None``. *path* need not exist."""
    repos_dir = workspace_root / "repos"
    try:
        rel = path.resolve().relative_to(repos_dir.resolve())
    except (ValueError, OSError):
        return None
    parts = rel.parts
    if not parts:
        return None
    slug = parts[0]
    return slug if CONTEXT_NAME_RE.fullmatch(slug) else None


# ---------------------------------------------------------------------------
# Workspace root — ONE resolver, target-path-first (the open-bug fix).
# ---------------------------------------------------------------------------


def _root_from(start: Path) -> Path | None:
    try:
        return resolve_workspace_root(start)
    except WorkspaceNotInitializedError:
        return None


def _resolve_root(*, env: Mapping[str, str], cwd: Path, target_path: Path | None) -> Path | None:
    """``WORKSPACE_ROOT`` env wins unconditionally (hook transport, never a resolution
    rung — kept byte-identical to the five prior copies: no ``.resolve()`` applied to
    an explicit override). Otherwise, when a write TARGET is known, the root is walked
    from the target's own location FIRST — the open-bug fix: a cwd that happens to sit
    inside a nested, independently sentinel-bearing sandbox workspace must never shadow
    the real root that actually owns the target. Falls back to a cwd-based walk when no
    target is given or the target-based walk found nothing."""
    override = env.get("WORKSPACE_ROOT")
    if override:
        return Path(override)
    if target_path is not None:
        start = target_path if target_path.is_dir() else target_path.parent
        root = _root_from(start)
        if root is not None:
            return root
    return _root_from(cwd)


# ---------------------------------------------------------------------------
# Session record liveness — rung 2.
# ---------------------------------------------------------------------------


def _live_session_context(workspace_root: Path, session_id: str | None) -> str | None:
    """Rung 2: this session's own LIVE record, keyed by *session_id*. Fails soft on
    missing/stale/deleted-context."""
    if not session_id:
        return None
    record = live_session(workspace_root, session_id)
    if record is None:
        return None
    context = record.get("context")
    context = str(context) if context else None
    if context and not _context_registered(workspace_root, context):
        return None
    return context


def all_repos(workspace_root: Path, context_name: str) -> frozenset[str]:
    """Every repo slug *context_name* owns: its main repo plus its associated repos.

    The Bind's SCOPE. An unknown context owns nothing; an unreadable registry owns
    nothing either — and an empty scope never blocks, because the scope rule only
    fires for a slug some OTHER context demonstrably owns.
    """
    for entry in _registry_contexts(workspace_root):
        if entry.get("name") != context_name:
            continue
        slugs = {entry.get("repo_slug") or entry.get("repo") or context_name}
        associated = entry.get("associated_repos")
        if isinstance(associated, list):
            slugs |= {
                assoc["slug"]
                for assoc in associated
                if isinstance(assoc, dict) and isinstance(assoc.get("slug"), str)
            }
        return frozenset(s for s in slugs if isinstance(s, str) and s)
    return frozenset()


def resolve_bind(
    workspace_root: Path | None, session_id: str | None, env: Mapping[str, str]
) -> Bind:
    """Resolve the SESSION's own binding — ``DADAIA_CONTEXT`` then this session's live
    record, and nothing else. Deliberately NOT cwd-derived: sitting inside a repo is
    not a bind, and a session that never bound must never be scope-blocked."""
    name = env.get("DADAIA_CONTEXT") or None
    if name is None and workspace_root is not None:
        name = _live_session_context(workspace_root, session_id)
    if not name or workspace_root is None:
        return Bind()
    return Bind(context_name=name, repos=all_repos(workspace_root, name))


# ---------------------------------------------------------------------------
# The one entry point.
# ---------------------------------------------------------------------------


def resolve(
    *,
    explicit: str | None = None,
    target_path: Path | None = None,
    payload: Mapping[str, object] | None = None,
    env: Mapping[str, str],
    cwd: Path,
    clock: Callable[[], float] | None = None,
) -> Invocation:
    """Resolve session, context, root and Bind ONCE — the single decider.

    *explicit*/*target_path* are rung 0 (a caller-supplied context name, or the context
    implied by an explicit write TARGET under ``repos/<slug>/`` — a repo write IS
    explicit input, so ``repos/x/...`` resolves ``x`` even while ``DADAIA_CONTEXT=y``).
    *payload* is a hook's already-parsed stdin envelope (``None`` for a CLI caller — the
    session id then resolves from *env* alone). *clock* is accepted for interface
    symmetry with the record-liveness predicate it threads through; unused directly
    here (:func:`~dadaia_workspace.core.record_liveness.is_stale` defaults to
    ``datetime.now``).
    """
    del clock  # reserved for a future injectable clock; is_stale defaults to utcnow.

    workspace_root = _resolve_root(env=env, cwd=cwd, target_path=target_path)
    session_id = resolve_session_id(payload, env) or None

    context_name: str | None = None
    rung = "none"

    if explicit:
        context_name, rung = explicit, "explicit"
    elif workspace_root is not None and target_path is not None:
        slug = repo_slug_under_repos(workspace_root, target_path)
        if slug:
            context_name = context_name_for_repo_slug(workspace_root, slug)
            rung = "target_path"

    if context_name is None:
        env_context = env.get("DADAIA_CONTEXT")
        if env_context:
            context_name, rung = env_context, "env"

    if context_name is None and workspace_root is not None:
        session_context = _live_session_context(workspace_root, session_id)
        if session_context:
            context_name, rung = session_context, "session"

    if context_name is None and workspace_root is not None:
        slug = repo_slug_under_repos(workspace_root, cwd)
        if slug:
            context_name = context_name_for_repo_slug(workspace_root, slug)
            rung = "cwd"

    repo_slug: str | None = None
    specs_dir: Path | None = None
    if workspace_root is not None and context_name:
        repo_slug = repo_slug_for_context(workspace_root, context_name)
        specs_dir = (workspace_root / "repos" / repo_slug / "specs").resolve()

    return Invocation(
        workspace_root=workspace_root,
        session_id=session_id,
        context_name=context_name,
        repo_slug=repo_slug,
        specs_dir=specs_dir,
        bind=resolve_bind(workspace_root, session_id, env),
        rung=rung,
    )


# ---------------------------------------------------------------------------
# CLI-facing helpers — thin wrappers over resolve(), the process-ambient callers.
# ---------------------------------------------------------------------------


def resolve_specs_dir(specs_dir: str | None) -> Path:
    """Resolve a specs/ dir: explicit input, else :func:`resolve` (no ``cwd/specs``
    fallback — the root `AGENTS.md` map §3 grants no such rung); unresolved reaches the error below.

    T-044-40 (bug ``symlinked-specs-root-is-followed-by-migration-and-repair``): a
    symlinked *explicit* root is refused HERE, once, at the one seam every
    resolver-driven verb shares — never re-decided per write site.
    """
    if specs_dir:
        path = Path(specs_dir)
        if path.is_symlink():
            # Deferred import — see the terminal error below for why.
            import typer

            raise typer.BadParameter(
                f"Refusing a symlinked specs root: {path} is a symlink. Point "
                "--specs-dir at the real directory instead of a link to it."
            )
        return path.resolve()

    inv = resolve(env=os.environ, cwd=Path.cwd())
    if inv.specs_dir is not None:
        return inv.specs_dir

    # Deferred import: hooks import this module on their hot path (F-01, v0.5.0 code
    # review) and must not pay typer's import cost for a CLI-only error type.
    import typer

    raise typer.BadParameter(
        "Could not resolve specs_dir. Pass --specs-dir or bind a context with "
        "`eval $(dadaia context bind <name> --print-env)`."
    )


def resolve_context_specs_dir(workspace_root: Path, context: str) -> Path:
    """A context's ``specs/`` tree: ``workspace_root/repos/<slug>/specs``, whether or not
    it exists yet — a context with no tree is onboarding level 2, never a silent redirect
    to another tree (0.4.8 R4). Derives from ``workspace_root``, never cwd."""
    return workspace_root / "repos" / repo_slug_for_context(workspace_root, context) / "specs"


def alive_context_trees(workspace_root: Path) -> dict[str, Path]:
    """Every ALIVE context NAME -> its ``specs/`` tree, in registry order — the
    onboarding derivation's input (0.4.8 FR6)."""
    return {
        name: resolve_context_specs_dir(workspace_root, name)
        for name in alive_context_names(workspace_root)
    }
