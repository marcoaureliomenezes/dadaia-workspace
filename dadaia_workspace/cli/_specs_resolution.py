"""The single CLI bind-resolution seam (v0.1.50 FR4; generalized v0.1.77 FR1).

Every resolver-driven ``dadaia`` command resolves through this module — its specs
directory via :func:`resolve_specs_dir_for_cli`, or (v0.1.77) the bound CONTEXT NAME
itself via :func:`resolve_context_for_cli`. A thin call onto the single resolution
authority (release K1, the "One Invocation" deepening, 2026-08-28 audit):
:mod:`dadaia_workspace.core.invocation`. This module's OWN job is the CLI-specific
allowlist validation FR3 documents below — resolution itself has exactly one home now.

v0.1.80 FR3 (backlog ``20260711-context-name-allowlist-at-resolution-rungs``, P4,
defense-in-depth per v0.1.77 security review INFO): the *explicit* and ``DADAIA_CONTEXT``
env rungs both feed a ``repos/<name>/specs`` path join further downstream (this module's
own :func:`resolve_specs_dir_for_cli`, and every ``container.build_*`` factory keyed by
context name), unvalidated. Both rungs are gated by the SAME ``[A-Za-z0-9_-]+`` allowlist
the resolution authority already enforces on every repo-slug path component
(:data:`~dadaia_workspace.core.invocation.CONTEXT_NAME_RE`, mirrored in
``features.spec_context.presence._valid_name``) BEFORE either value is used — an
operator-controlled input has no privilege elevation here (the operator can already touch
any path directly), so this is defense-in-depth, not a privilege boundary. The two rungs
get DIFFERENT dispositions on a traversal-shaped value: *explicit* is deliberate call-site
input, so it raises a clear, actionable :class:`ValueError`; ``DADAIA_CONTEXT`` is ambient
shell state (inherited/stale environment an operator may not have set deliberately for
THIS invocation), so an invalid value is treated as unset and resolution continues to the
next rung — never a crash over environment the operator didn't knowingly provide.
"""

from __future__ import annotations

import os
from pathlib import Path

from dadaia_workspace.core.invocation import CONTEXT_NAME_RE as _CONTEXT_NAME_RE
from dadaia_workspace.core.invocation import (
    HARNESS_SESSION_ID_ENV_VARS as _HARNESS_SESSION_ID_ENV_VARS,
)
from dadaia_workspace.core.invocation import repo_slug_for_context as _core_repo_slug
from dadaia_workspace.core.invocation import resolve as _resolve_invocation
from dadaia_workspace.core.invocation import (
    resolve_context_specs_dir as _core_resolve_context_specs_dir,
)
from dadaia_workspace.core.invocation import resolve_session_id as _core_resolve_session_id
from dadaia_workspace.core.invocation import resolve_specs_dir as _core_resolve_specs_dir
from dadaia_workspace.core.invocation import sanitize_session_id as _sanitize_session_id

#: Re-exports so a verb never reaches ``core.invocation`` directly (FR3,
#: ``bind-resolution-seam-is-a-single-home``). The contract takes ZERO ignore_imports,
#: so every consumer of the harness-session-id env-var list, the sid sanitizer, or the
#: name->repo-slug mapping routes through this seam.
HARNESS_SESSION_ID_ENV_VARS = _HARNESS_SESSION_ID_ENV_VARS
sanitize_session_id = _sanitize_session_id


def repo_slug_for_context(workspace_root: Path, name: str) -> str:
    """The on-disk ``repos/<slug>`` directory for a context NAME (registry-backed).

    A context's NAME and its repo SLUG are two identities; deriving the directory from
    the name is the defect class fixed in the 0.4.2 arc. Verbs call this seam so the one
    registry-backed resolution stays the single source of truth.
    """
    return _core_repo_slug(workspace_root, name)


def resolve_context_for_cli(explicit: str | None) -> str:
    """Resolve the target Spec Context NAME (SPEC FR1 canonical order, v0.1.77; delegates
    to :func:`dadaia_workspace.core.invocation.resolve` for the rung ladder itself).

    Order: *explicit* -> ``DADAIA_CONTEXT`` env -> the single authority's rung 2 (this
    session's own LIVE record, keyed by the harness-native session id) -> the repo
    containing the current working directory. A consumer workspace without caller-owned
    selection raises an actionable error; it never borrows the first ALIVE context.

    v0.1.80 FR3: both the *explicit* and ``DADAIA_CONTEXT`` env rungs are validated
    against the ``[A-Za-z0-9_-]+`` context-name allowlist before use (defense-in-depth
    against a traversal-shaped name reaching the downstream ``repos/<name>/specs`` path
    join). A traversal-shaped *explicit* value raises :class:`ValueError` (deliberate
    call-site input — reject loudly). A traversal-shaped ``DADAIA_CONTEXT`` value never
    crashes the CLI with a traceback — but it does ABORT resolution with the terminal
    :class:`ValueError` (pinned by test): the authority's own rung 1 re-reads the SAME
    env var and echoes the invalid value back, the allowlist check on ``resolved``
    rejects the echo, and rungs 2-3 are deliberately NOT reachable past a set-but-invalid
    env var — silently ignoring an operator's explicit (mistyped) selection would resolve
    a context they did not choose.
    """
    if explicit:
        if not _CONTEXT_NAME_RE.fullmatch(explicit):
            raise ValueError(
                f"Invalid context name {explicit!r}: context names must match "
                f"{_CONTEXT_NAME_RE.pattern!r} (letters, digits, '_', '-' only). "
                "Pass a valid Spec Context Project name."
            )
        return explicit
    env_context = os.environ.get("DADAIA_CONTEXT")
    if env_context and _CONTEXT_NAME_RE.fullmatch(env_context):
        return env_context
    resolved = _resolve_invocation(env=os.environ, cwd=Path.cwd()).context_name
    if resolved and _CONTEXT_NAME_RE.fullmatch(resolved):
        return resolved
    raise ValueError(
        "No caller-owned Spec Context is selected. Run "
        "'dadaia context bind <name> --mode <mode>' in this session or pass "
        "'--context <name>' explicitly. Use 'dadaia context list --json' to discover "
        "available contexts."
    )


def resolve_context_specs_dir_for_cli(workspace_root: Path, context: str) -> Path:
    """Seam wrapper over the ONE context->specs resolver (T-053-01/F003): registry
    ``repo_slug`` mapping + self-hosting root fallback. CLI verbs import THIS, never
    ``core.invocation`` directly (bind-resolution-seam-is-a-single-home)."""
    return _core_resolve_context_specs_dir(workspace_root, context)


def resolve_specs_dir_for_cli(specs_dir: str | None) -> Path:
    """Resolve the target specs/ dir (explicit flag, else the resolution authority)."""
    return _core_resolve_specs_dir(specs_dir)


def resolve_session_id_for_cli() -> str:
    """This process's own session id through the one rule over ``os.environ``
    (no hook payload: a CLI entrypoint); ``""`` when no channel resolves."""
    return _core_resolve_session_id(None, os.environ)


def resolve_workspace_root_for_cli(target_path: Path) -> Path:
    """The workspace root above *target_path* — the single root walk
    (:func:`dadaia_workspace.core.invocation.resolve`'s ``target_path``-first rung,
    ``WORKSPACE_ROOT`` env included, cwd fallback). Falls back to *target_path* itself
    when nothing is found (an uninitialized/consumer tree). The seam a git-hook-spawned
    ``dadaia ci`` verb (a harness-FREE child, no session, no ``DADAIA_CONTEXT``) uses to
    resolve its workspace without importing ``core.invocation`` directly
    (``bind-resolution-seam-is-a-single-home``)."""
    return (
        _resolve_invocation(target_path=target_path, env=os.environ, cwd=Path.cwd()).workspace_root
        or target_path
    )
