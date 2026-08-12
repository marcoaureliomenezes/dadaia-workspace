"""The single CLI bind-resolution seam (v0.1.50 FR4; generalized v0.1.77 FR1).

Every resolver-driven ``dadaia`` command resolves through this module — its specs
directory via :func:`resolve_specs_dir_for_cli`, or (v0.1.77) the bound CONTEXT NAME
itself via :func:`resolve_context_for_cli`. Five per-command wrappers used to hand-copy
the specs-dir call, which is exactly the drift centralizing here prevents.

v0.1.77 (backlog ``central-bind-resolution-seam``, recurrence family F2 — 8 reports, 5
partial per-command fixes v0.1.47->v0.1.71): a partial seam existed here
(``resolve_specs_dir_for_cli``, consumed by specs/bugs/memory/migrate/newartifacts) but
NOT the ~15 lifecycle verbs, whose ``--context`` Typer default was the hardcoded literal
``"dadaia-workspace"`` passed as if explicit — the bind was never consulted.
:func:`resolve_context_for_cli` is the single canonical order (SPEC FR1) every verb now
resolves through: explicit -> ``DADAIA_CONTEXT`` env -> the single resolution authority's
rung 2 (this session's own LIVE record, keyed by the harness-native session id) -> the
repo containing cwd (the single authority's rung 3, SPEC v0.5.0 FR1 widening, which
subsumes and generalizes the old hardcoded self-hosting-checkout literal this seam used
to fall back to — T-50-05 deletes it).

v0.1.80 FR3 (backlog ``20260711-context-name-allowlist-at-resolution-rungs``, P4,
defense-in-depth per v0.1.77 security review INFO): the *explicit* and ``DADAIA_CONTEXT``
env rungs both feed a ``repos/<name>/specs`` path join further downstream (this module's
own :func:`resolve_specs_dir_for_cli`, and every ``container.build_*`` factory keyed by
context name), unvalidated. Both rungs are gated by the SAME ``[A-Za-z0-9_-]+`` allowlist
the resolution authority already enforces on every repo-slug path component
(:data:`~dadaia_workspace.core.specs_resolver._CONTEXT_NAME_RE`, mirrored in
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

from dadaia_workspace.core.specs_resolver import _CONTEXT_NAME_RE
from dadaia_workspace.core.specs_resolver import repo_slug_for_context as _core_repo_slug
from dadaia_workspace.core.specs_resolver import resolve_context as _resolve_context_authority
from dadaia_workspace.core.specs_resolver import resolve_specs_dir as _core_resolve_specs_dir

#: Re-exports so a verb never reaches ``core.specs_resolver`` directly (FR3,
#: ``bind-resolution-seam-is-a-single-home``). The contract takes ZERO ignore_imports,
#: so every consumer of the context-name allowlist or the name->repo-slug mapping routes
#: through this seam.
CONTEXT_NAME_RE = _CONTEXT_NAME_RE


def repo_slug_for_context(workspace_root: Path, name: str) -> str:
    """The on-disk ``repos/<slug>`` directory for a context NAME (registry-backed).

    A context's NAME and its repo SLUG are two identities; deriving the directory from
    the name is the defect class fixed in the 0.4.2 arc. Verbs call this seam so the one
    registry-backed resolution stays the single source of truth.
    """
    return _core_repo_slug(workspace_root, name)


def resolve_context_for_cli(explicit: str | None) -> str:
    """Resolve the target Spec Context NAME (SPEC FR1 canonical order, v0.1.77; T-50-02/04
    delegate the bound-session leg to the single resolution authority, SPEC v0.5.0 FR1 —
    the bind-epoch marker ladder this seam used to call FIRST is deleted).

    Order: *explicit* -> ``DADAIA_CONTEXT`` env -> the single authority's rung 2 (this
    session's own LIVE record, keyed by the harness-native session id) -> the repo
    containing the current working directory (the single authority's rung 3, SPEC v0.5.0
    FR1's *intended widening*). A consumer workspace without caller-owned selection
    raises an actionable error; it never borrows the first ALIVE context, and T-50-05
    deletes the old hardcoded self-hosting-checkout special case — rung 3 already
    generalizes it (any registered ``repos/<slug>``, not only one literally named
    ``dadaia-workspace``).

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
    a context they did not choose (T-50-05; replaces the pop/restore env mutation).
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
    resolved = _resolve_context_authority()
    if resolved and _CONTEXT_NAME_RE.fullmatch(resolved):
        return resolved
    raise ValueError(
        "No caller-owned Spec Context is selected. Run "
        "'dadaia context bind <name> --mode <mode>' in this session or pass "
        "'--context <name>' explicitly. Use 'dadaia context list --json' to discover "
        "available contexts."
    )


def resolve_specs_dir_for_cli(specs_dir: str | None) -> Path:
    """Resolve the target specs/ dir (explicit flag, else the resolution authority)."""
    return _core_resolve_specs_dir(specs_dir)
