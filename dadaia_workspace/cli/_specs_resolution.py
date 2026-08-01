"""The single CLI bind-resolution seam (v0.1.50 FR4; generalized v0.1.77 FR1).

Every resolver-driven ``dadaia`` command resolves through this module — its specs
directory via :func:`resolve_specs_dir_for_cli`, or (v0.1.77) the bound CONTEXT NAME
itself via :func:`resolve_context_for_cli`. Both ALWAYS thread the current process's
ancestry pid chain into the core resolver, so bind-marker attribution works from any
ephemeral harness shell. Five per-command wrappers used to hand-copy the specs-dir call
and four of them omitted ``ancestry_pids`` (bug
``bugs-append-bound-session-falls-through-to-cwd-specs``): centralizing here makes the
omission structurally impossible.

v0.1.77 (backlog ``central-bind-resolution-seam``, recurrence family F2 — 8 reports, 5
partial per-command fixes v0.1.47->v0.1.71): a partial seam existed here
(``resolve_specs_dir_for_cli``, consumed by specs/bugs/memory/migrate/newartifacts) but
NOT the ~15 lifecycle verbs, whose ``--context`` Typer default was the hardcoded literal
``"dadaia-workspace"`` passed as if explicit — the bind was never consulted.
:func:`resolve_context_for_cli` is the single canonical order (SPEC FR1) every verb now
resolves through: explicit -> ``DADAIA_CONTEXT`` env -> this session's OWN record
(harness-native id / ancestry-marker membership, via
:func:`~dadaia_workspace.core.specs_resolver.resolve_bound_context_name` — never a
foreign session's bind, consistent with the v0.1.76 NO-LOCKS DOCTRINE's self-scoped
identity) -> first-ALIVE context (fail-soft; mirrors ``context show``'s pre-v0.1.77
no-arg fallback, folded into the seam here per SPEC FR1's explicit disposition).

v0.1.80 FR3 (backlog ``20260711-context-name-allowlist-at-resolution-rungs``, P4,
defense-in-depth per v0.1.77 security review INFO): the *explicit* and ``DADAIA_CONTEXT``
env rungs both feed a ``repos/<name>/specs`` path join further downstream (this module's
own :func:`resolve_specs_dir_for_cli`, and every ``container.build_*`` factory keyed by
context name), unvalidated. Both rungs are gated by the SAME ``[A-Za-z0-9_-]+`` allowlist
already enforced for bind-epoch marker filenames
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

from dadaia_workspace.core.exceptions import DadaiaError
from dadaia_workspace.core.specs_resolver import _CONTEXT_NAME_RE
from dadaia_workspace.core.specs_resolver import repo_slug_for_context as _core_repo_slug
from dadaia_workspace.core.specs_resolver import resolve_bound_context_name as _resolve_bound_name
from dadaia_workspace.core.specs_resolver import resolve_specs_dir as _core_resolve_specs_dir


class ContextNotSelectedError(DadaiaError, ValueError):
    """No context could be resolved and the verb requires one.

    A bare ``ValueError`` here read as an internal fault rather than an operator-facing
    condition with a clear remedy — the consumer-side validator reported it verbatim as an
    "unexpected ValueError". It is neither unexpected nor internal: the message already
    names the two commands that fix it.

    Inherits ``DadaiaError`` so the CLI renders one clean line (F-22), and keeps
    ``ValueError`` so the existing ``except ValueError`` call sites — ``context show``
    treats "nothing is selected" as a valid ANSWER, not an error — are unaffected. Same
    dual-inheritance precedent as ``InvalidResumeStepError``.
    """


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


#: Self-hosting source checkout slug. It is returned only when the current working
#: directory is recognizably this library checkout, never as a consumer-workspace fallback.
_SELF_HOSTING_SLUG = "dadaia-workspace"


def current_ancestry_pids() -> tuple[int, ...] | None:
    """This ``dadaia`` process's nearest-first ORDERED ancestry pid chain (bind attribution).

    W1-8 (v0.1.47): the persisted-bind fallback attributes a bind-epoch marker by
    ancestry-chain MEMBERSHIP. A marker written from an ephemeral harness shell
    records the bind process's chain (incl. the long-lived harness pid); this CLI
    runs under a DIFFERENT short-lived shell but shares that harness pid deeper in
    ITS chain. ORDER PRESERVED (bug ancestry-attribution-cross-session-ambiguity):
    the resolver scores each marker by its shallowest shared pid — session-unique
    pids (this process's harness) sit at low indices, host-level ancestors shared
    with foreign sessions at high ones — so the caller's own bind outranks foreign
    markers instead of collapsing to ambiguity. Any failure ⇒ ``None`` ⇒ the
    resolver degrades to single-getppid equality.
    """
    try:
        from dadaia_workspace import container

        return tuple(container.build_ancestry_pid_chain(os.getppid()))
    except Exception:  # noqa: BLE001 — attribution is best-effort; never break resolution.
        return None


def _is_self_hosting_checkout() -> bool:
    """Return whether cwd is the dadaia-workspace source checkout."""
    cwd = Path.cwd().resolve()
    return (
        cwd.name == _SELF_HOSTING_SLUG
        and (cwd / "dadaia_workspace").is_dir()
        and (cwd / "specs").is_dir()
    )


def resolve_context_for_cli(explicit: str | None) -> str:
    """Resolve the target Spec Context NAME (SPEC FR1 canonical order, v0.1.77).

    Order: *explicit* -> ``DADAIA_CONTEXT`` env -> this session's OWN bound record
    (harness-native id, then ancestry-marker membership — never a foreign session's
    bind) -> the self-hosting slug only from the recognizable source checkout. A
    consumer workspace without caller-owned selection raises an actionable error;
    it never borrows the first ALIVE context.

    v0.1.80 FR3: both the *explicit* and ``DADAIA_CONTEXT`` env rungs are validated
    against the ``[A-Za-z0-9_-]+`` context-name allowlist before use (defense-in-depth
    against a traversal-shaped name reaching the downstream ``repos/<name>/specs`` path
    join). A traversal-shaped *explicit* value raises :class:`ValueError` (deliberate
    call-site input — reject loudly). A traversal-shaped ``DADAIA_CONTEXT`` value is
    treated as unset (ambient environment — never crash the CLI over it) and resolution
    continues to the next rung.
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
    # A present-but-INVALID DADAIA_CONTEXT (``env_context`` truthy but rejected above)
    # must not silently reach ``resolve_bound_context_name`` below — that function
    # re-reads the same env var internally (its own explicit -> env -> session ->
    # persisted-bind order) and would otherwise return the same unvalidated value we
    # just rejected. Scope the env var out for the duration of this single delegated
    # call only, restoring it immediately after on every exit path (it is present, by
    # construction, whenever we reach this branch, so the restore is unconditional).
    if env_context:
        os.environ.pop("DADAIA_CONTEXT")
        try:
            resolved = _resolve_bound_name(ancestry_pids=current_ancestry_pids())
        finally:
            os.environ["DADAIA_CONTEXT"] = env_context
    else:
        resolved = _resolve_bound_name(ancestry_pids=current_ancestry_pids())
    if resolved:
        return resolved
    if _is_self_hosting_checkout():
        return _SELF_HOSTING_SLUG
    raise ContextNotSelectedError(
        "No caller-owned Spec Context is selected. Run "
        "'dadaia context bind <name> --mode <mode>' in this session or pass "
        "'--context <name>' explicitly. Use 'dadaia context list --json' to discover "
        "available contexts."
    )


def resolve_specs_dir_for_cli(specs_dir: str | None) -> Path:
    """Resolve the target specs/ dir (explicit flag → bound context → cwd/specs)."""
    return _core_resolve_specs_dir(specs_dir, ancestry_pids=current_ancestry_pids())
