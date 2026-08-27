"""v0.1.77 T-1 (RED) — dynamic bind-visibility contract + seam-boundary assertion.

SPEC FR1/FR2/FR3/FR4 (backlog ``central-bind-resolution-seam``, recurrence family F2: 8
reports, 5 partial per-command fixes v0.1.47->v0.1.71, still recurring). The contract "a
successful ``dadaia context bind`` is visible to every resolver-driven command" was never
fixed centrally — each fix patched one command surface and the family kept recurring
(median re-report <11h). This module is the class-level structural lock:

1. A DYNAMIC Typer-app walk (``typer.main.get_command`` over the real ``cli.main.app``,
   recursing on ``.commands`` structurally rather than an ``isinstance(click.Group)``
   check — Typer 0.19's vendored ``typer._click`` shim fails that isinstance check even
   though the object walks exactly like a Click group) discovers every leaf subcommand,
   with NO static list — a future verb registered anywhere in the app tree is discovered
   automatically.

2. Each leaf command's Click parameters are inspected programmatically
   (``click.Parameter.name``/``.default``) to classify ``context``/``specs_dir``-named
   options. FR2's "no hardcoded default" assertion is a pure structural check: the
   *literal string* ``"dadaia-workspace"`` as a Click default is ALWAYS the bug (a
   resolver never legitimately defaults to a specific context name baked into the CLI —
   the whole point of the seam is that "no explicit input" resolves through bind/env,
   never a hardcoded literal). This makes the RED assertion resilient to a future verb:
   any new ``context``/``specs_dir`` option ever authored with that literal default fails
   the walk, by construction, with no maintenance of a name list.

3. AST reachability (module-local, fixed-point over same-module function defs) decides
   whether a ``context``/``specs_dir``-named parameter is genuinely RESOLVER-DRIVEN (its
   value flows, by keyword-name match, into a call to the seam family:
   ``resolve_specs_dir_for_cli`` / ``resolve_context_for_cli`` / any
   ``container.build_*``/``container.resolve_*`` attribute call) as opposed to same-named
   but semantically unrelated parameters that this project's own source distinguishes
   deliberately. At this fold ``known_non_resolver`` (part (b), below) is EMPTY: every
   currently-registered ``context``/``specs_dir`` param IS resolver-driven, including
   ``bugs append --context`` (left the non-resolver set in v0.1.82 — its value routes
   through ``resolve_context_for_cli`` for LEDGER-destination resolution, and — since
   v0.5.0 T-050-08 — the resolved specs_dir also reaches
   ``container.build_bug_record_store``/``build_bug_archive_store``, one more seam
   edge on the same already-resolver-driven param, not a new one).
   The reachability check is itself dynamic (graph search over the real source), not a
   hand-maintained exclude list, so a future non-resolver ``context``/``specs_dir`` param
   is correctly excluded automatically, and a future resolver-driven one is correctly
   included automatically.

RED against HEAD (v0.1.77 T-1): part (a) below fails today because 15 lifecycle verbs
default ``--context`` to the literal ``"dadaia-workspace"``. Part (b) (the seam-boundary
assertion) is checked as a structural stand-in for the executed-path probe in
``tests/integration/cli/test_bind_resolution_seam_executed_path.py`` — that companion
module runs the REAL bind + verb invocation end-to-end for the resolver-driven command
modules (bugs, specs, and context).
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Protocol

import pytest
import typer

from dadaia_workspace.cli.main import app
from tests.helpers.scan_population import assert_populated

pytestmark = pytest.mark.contract


class _ClickParam(Protocol):
    """Structural shape of a Click/Typer parameter this contract inspects."""

    name: str | None
    default: object


class _ClickCommand(Protocol):
    """Structural shape of a Click/Typer leaf command this contract inspects."""

    params: list[_ClickParam]
    callback: object


_REPO_ROOT = Path(__file__).resolve().parents[2]
_CLI_DIR = _REPO_ROOT / "dadaia_workspace" / "cli"

#: The literal hardcoded default the whole family of bugs shares (FR2). ANY
#: context/specs_dir-named Click option defaulting to this literal is the violation —
#: no resolver-driven verb may bake a specific context name into its own default.
_HARDCODED_DEFAULT = "dadaia-workspace"

#: Parameter names this contract treats as resolution-shaped inputs (FR1/FR3 — the seam
#: family). Any OTHER param name is out of scope for this contract (e.g. --release-id).
_RESOLUTION_PARAM_NAMES = frozenset({"context", "specs_dir"})

#: The seam functions/attribute-call families a resolver-driven parameter must reach
#: (by keyword or positional name-match) to count as consuming the canonical seam. T-1 is
#: RED on ``resolve_context_for_cli`` (T-2 introduces it); ``resolve_specs_dir_for_cli`` and
#: the ``container.build_*``/``container.resolve_*`` families already exist at HEAD.
_SEAM_FUNCTION_NAMES = frozenset({"resolve_specs_dir_for_cli", "resolve_context_for_cli"})

#: ``container.build_*``/``container.resolve_*`` factories whose ``context`` kwarg is a
#: documented FILTER (equality-narrows an already-resolved list, e.g.
#: ``LifecycleRun.context ==``), never a specs-dir/bound-context RESOLUTION input — the
#: general "reaches a container.build_*/resolve_* call" heuristic below would otherwise
#: false-positive on these (their factory happens to accept ``context`` as a plain
#: pass-through kwarg with no ``resolve_context`` in its own body). Verified by
#: reading each factory's source at v0.1.77 T-2 time; a factory added here must be
#: re-verified whenever its body changes, since this is a manually-audited exception list,
#: not an automatically-derived one.
_FILTER_ONLY_CONTAINER_FACTORIES = frozenset({"container.build_workflow_handoff_doctor"})


def _walk_leaf_commands() -> list[tuple[tuple[str, ...], _ClickCommand]]:
    """Every leaf (non-group) command in the real app tree, dynamically discovered.

    Recurses on ``getattr(cmd, "commands", None)`` rather than
    ``isinstance(cmd, click.Group)``: Typer's vendored ``typer._click`` shim produces
    ``TyperGroup`` objects that do NOT satisfy ``isinstance(x, click.Group)`` against the
    real ``click`` package (a version-shim mismatch, not an architectural signal) even
    though they walk exactly like a Click group. The structural check is honest and
    future-proof against either shim shape.
    """
    root = typer.main.get_command(app)
    out: list[tuple[tuple[str, ...], _ClickCommand]] = []

    def _walk(cmd: object, prefix: tuple[str, ...]) -> None:
        commands = getattr(cmd, "commands", None)
        if commands is not None:
            for name, sub in commands.items():
                _walk(sub, (*prefix, name))
        else:
            out.append((prefix, cmd))  # type: ignore[arg-type]

    _walk(root, ())
    return out


def _resolution_params(cmd: _ClickCommand) -> list[_ClickParam]:
    """This command's Click parameters named ``context`` or ``specs_dir``."""
    return [p for p in cmd.params if p.name in _RESOLUTION_PARAM_NAMES]


def _param_name(param: _ClickParam) -> str:
    """Narrow a resolution-shaped param's ``.name`` to ``str`` (never ``None`` here — it
    already matched ``_RESOLUTION_PARAM_NAMES`` membership, a set of non-``None`` strings)."""
    assert param.name is not None
    return param.name


def _verb_label(path: tuple[str, ...], param: _ClickParam) -> str:
    """``dadaia <path> --<option>`` label used in every assertion message/set below."""
    return f"{'.'.join(('dadaia', *path))} --{_param_name(param).replace('_', '-')}"


# --- AST reachability: is a context/specs_dir parameter resolver-driven? -------------


def _module_path_for_command_path(path: tuple[str, ...]) -> Path | None:
    """Map a CLI verb path (e.g. ``("lifecycle", "preflight")``) to its source module.

    Every command group in ``cli/main.py`` is backed by exactly one
    ``cli/commands/<group>.py`` module (bugs/release/backlog live in ``newartifacts.py`` /
    ``bugs.py`` — special-cased). Falls back to ``None`` (excluded from AST reachability,
    never silently treated as resolver-driven) when no source module is found — the FR2
    literal-default check does not depend on this mapping at all.
    """
    if not path:
        return None
    group = path[0]
    special = {
        "release": _CLI_DIR / "commands" / "newartifacts.py",
        "backlog": _CLI_DIR / "commands" / "newartifacts.py",
        "bugs": _CLI_DIR / "commands" / "bugs.py",
        "memory": _CLI_DIR / "commands" / "memory.py",
    }
    if group in special:
        return special[group]
    candidate = _CLI_DIR / "commands" / f"{group}.py"
    return candidate if candidate.is_file() else None


def _function_defs(tree: ast.Module) -> dict[str, ast.FunctionDef]:
    """Every top-level ``def`` in a module, by name (module-local reachability graph)."""
    return {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node in tree.body
    }


def _assignment_closure(func: ast.FunctionDef, seed: str) -> set[str]:
    """Fixed-point set of local names transitively assigned FROM *seed*, within *func*'s
    own body (simple-assignment propagation — e.g. ``ctx = context or ...``,
    ``ctx = context``). Only ``Name`` references inside the assigned value are considered
    (a value built from anything else — an f-string, an attribute access, ...  — does not
    propagate taint, since it is no longer literally "the same value the caller passed").
    """
    tainted = {seed}
    changed = True
    while changed:
        changed = False
        for node in ast.walk(func):
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            value = node.value
            if value is None:
                continue
            referenced = {n.id for n in ast.walk(value) if isinstance(n, ast.Name)}
            if not referenced & tainted:
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name) and target.id not in tainted:
                    tainted.add(target.id)
                    changed = True
    return tainted


def _names_reaching_seam(func: ast.FunctionDef) -> set[str]:
    """Local variable/parameter names inside *func* that are passed BY NAME (positional
    ``Name`` argument or ``keyword`` whose value is that ``Name``) into a call to one of
    ``_SEAM_FUNCTION_NAMES``, OR into any ``container.build_*``/``container.resolve_*``
    attribute call EXCEPT the documented filter-only factories in
    ``_FILTER_ONLY_CONTAINER_FACTORIES`` (the container's other factories internally
    resolve through ``resolve_context`` — reaching one of them IS reaching the
    seam family; the filter-only ones do not)."""
    reached: set[str] = set()
    for node in ast.walk(func):
        if not isinstance(node, ast.Call):
            continue
        callee_name: str | None = None
        func_node = node.func
        if isinstance(func_node, ast.Name):
            callee_name = func_node.id
        elif isinstance(func_node, ast.Attribute):
            receiver = func_node.value
            if (
                isinstance(receiver, ast.Name)
                and receiver.id == "container"
                and (func_node.attr.startswith("build_") or func_node.attr.startswith("resolve_"))
            ):
                callee_name = f"container.{func_node.attr}"
        if callee_name is None:
            continue
        if callee_name in _FILTER_ONLY_CONTAINER_FACTORIES:
            continue
        is_seam_call = callee_name in _SEAM_FUNCTION_NAMES or callee_name.startswith("container.")
        if not is_seam_call:
            continue
        args = list(node.args) + [kw.value for kw in node.keywords]
        for arg in args:
            if isinstance(arg, ast.Name):
                reached.add(arg.id)
    return reached


def _tainted_reaches_seam(func: ast.FunctionDef, seed: str) -> bool:
    """True iff *seed* (or any name in its same-function assignment closure — e.g.
    ``ctx = context or os.environ.get(...)``) is ever passed into a seam call inside
    *func*."""
    closure = _assignment_closure(func, seed)
    return bool(closure & _names_reaching_seam(func))


def _param_reaches_seam(module_path: Path, func_name: str, param_name: str) -> bool:
    """Fixed-point reachability: does *param_name* (a parameter of *func_name*) flow, by
    name, into a seam call either directly in *func_name*'s body or via any module-local
    helper function *func_name* calls (recursively, bounded by the module's own function
    set — module-local reachability only, never cross-module)."""
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    defs = _function_defs(tree)
    if func_name not in defs:
        return False

    # Fixed point: start with {param_name} as the "tainted" name set for func_name, then
    # propagate through calls to other module-local functions whose corresponding
    # positional/keyword argument is a tainted name.
    visited_calls: set[tuple[str, str]] = set()  # (function, tainted-name) already expanded

    def _explore(fn_name: str, tainted: str) -> bool:
        key = (fn_name, tainted)
        if key in visited_calls:
            return False
        visited_calls.add(key)
        fn = defs.get(fn_name)
        if fn is None:
            return False
        if _tainted_reaches_seam(fn, tainted):
            return True
        closure = _assignment_closure(fn, tainted)
        # Propagate into module-local helper calls: if any name in the tainted closure is
        # passed (by Name, positionally or by keyword) to a call whose callee is another
        # function defined in this module, recurse with the callee's corresponding
        # parameter name.
        for node in ast.walk(fn):
            if not isinstance(node, ast.Call):
                continue
            func_node = node.func
            if not isinstance(func_node, ast.Name):
                continue
            callee_name = func_node.id
            callee_def = defs.get(callee_name)
            if callee_def is None or callee_name == fn_name:
                continue
            callee_params = [a.arg for a in callee_def.args.args]
            callee_params += [a.arg for a in callee_def.args.kwonlyargs]
            # Positional match.
            for idx, arg in enumerate(node.args):
                if (
                    isinstance(arg, ast.Name)
                    and arg.id in closure
                    and idx < len(callee_params)
                    and _explore(callee_name, callee_params[idx])
                ):
                    return True
            # Keyword match.
            for kw in node.keywords:
                if (
                    kw.arg is not None
                    and isinstance(kw.value, ast.Name)
                    and kw.value.id in closure
                    and kw.arg in callee_params
                    and _explore(callee_name, kw.arg)
                ):
                    return True
        return False

    return _explore(func_name, param_name)


def _cli_function_name(cmd: _ClickCommand) -> str | None:
    """Best-effort recovery of the Python function name backing a Typer command.

    Typer stores the original callback on ``.callback``; its ``__name__`` is the
    module-level function name AST reachability keys on.
    """
    callback = cmd.callback
    return getattr(callback, "__name__", None) if callback is not None else None


def _is_resolver_driven(path: tuple[str, ...], cmd: _ClickCommand, param_name: str) -> bool:
    """True iff *param_name* on the command at *path* is a genuine resolution input
    (AST-reachable to the seam family), per the module-local reachability graph."""
    module_path = _module_path_for_command_path(path)
    func_name = _cli_function_name(cmd)
    if module_path is None or func_name is None:
        return False
    return _param_reaches_seam(module_path, func_name, param_name)


# --- Part (a): FR2 — no resolver-driven verb carries the hardcoded literal default ----


def test_no_resolver_driven_verb_hardcodes_the_dadaia_workspace_default() -> None:
    """RED at HEAD: 15 lifecycle verbs default ``--context`` to the literal string
    ``"dadaia-workspace"`` (grep-verifiable; this assertion is the executable form).
    Structural — no name list to maintain: ANY future context/specs_dir option ever
    authored with this literal default fails here, by construction (FR4 — no further
    per-command patches accepted for family F2)."""
    commands = _walk_leaf_commands()
    # v0.4.5 FR5 (scan-test-vacuity-guard): a broken Typer app tree could dynamically
    # walk to zero leaf commands, under which `offenders` below stays empty vacuously.
    assert_populated([path for path, _cmd in commands], sentinel=("bugs", "append"))
    offenders: list[str] = []
    for path, cmd in commands:
        for param in _resolution_params(cmd):
            if param.default == _HARDCODED_DEFAULT:
                offenders.append(_verb_label(path, param))
    assert not offenders, (
        "resolver-driven verb(s) carry the hardcoded literal default "
        f"{_HARDCODED_DEFAULT!r} instead of resolving through the seam (SPEC FR2):\n"
        + "\n".join(sorted(offenders))
        + "\n\nUnset the Typer default to None; resolution must flow through "
        "cli._specs_resolution.resolve_context_for_cli / resolve_specs_dir_for_cli."
    )


# --- Part (b): FR1/FR3 — every genuinely resolver-driven verb reaches the seam --------


def test_every_resolver_driven_verb_reaches_the_seam_family() -> None:
    """Every ``context``/``specs_dir`` parameter that AST-reachability classifies as
    resolver-driven (flows into a seam-family call, directly or via a module-local
    helper) must reach ``resolve_specs_dir_for_cli`` / ``resolve_context_for_cli`` / a
    ``container.build_*``/``container.resolve_*`` factory. A parameter classified
    NON-resolver-driven (metadata/filter — e.g. ``bugs append --context``,
    ``lifecycle status --context``) is asserted excluded, so the classifier itself is
    pinned honest against source drift, not just today's headline assertion.

    This is the seam-boundary stand-in for the executed-path probe (companion module
    ``tests/integration/cli/test_bind_resolution_seam_executed_path.py`` runs the real
    CliRunner + bind flow for a representative verb per command module)."""
    seam_reaching: list[str] = []
    not_seam_reaching: list[str] = []
    for path, cmd in _walk_leaf_commands():
        for param in _resolution_params(cmd):
            label = _verb_label(path, param)
            if _is_resolver_driven(path, cmd, _param_name(param)):
                seam_reaching.append(label)
            else:
                not_seam_reaching.append(label)

    # Sanity: the walk must have found candidates at all (a total collapse would silently
    # pass an empty contract — fail loudly instead).
    assert seam_reaching or not_seam_reaching, "dynamic walk found zero context/specs_dir params"

    # Every classified-resolver-driven param must be AST-reachable to the seam (this is
    # true by construction of `_is_resolver_driven`, restated here as the load-bearing
    # assertion so a future refactor of the classifier cannot silently invert it).
    assert all(
        _is_resolver_driven(path, cmd, _param_name(param))
        for path, cmd in _walk_leaf_commands()
        for param in _resolution_params(cmd)
        if _verb_label(path, param) in seam_reaching
    )

    # The known non-resolver params stay excluded (classifier honesty pin — fails loudly
    # if source drift changes their shape without updating this contract's understanding).
    # `dadaia.bugs.append --context` left this set in v0.1.82: the event's context is
    # now a ROUTING key resolved through the seam (bug
    # bugs-append-ledger-ignores-context-flag), no longer inert event metadata.
    # `dadaia.specs.init --specs-dir` left this set in T-045-21/FR8: the explicit branch
    # now routes through `_resolve_specs_dir` (the same seam every other resolver-driven
    # verb shares) so a symlinked target is refused there too — reusing that seam's
    # existing refusal instead of a second, independent symlink check (A8.2).
    known_non_resolver: set[str] = set()
    unexpected_non_resolver = set(not_seam_reaching) - known_non_resolver
    assert not unexpected_non_resolver, (
        "context/specs_dir param(s) classified as NON-resolver-driven that are not in "
        f"the known exclusion set: {sorted(unexpected_non_resolver)}. Either the AST "
        "reachability walker has a gap (a real resolver-driven verb is not reaching the "
        "seam — FR1/FR4 violation) or this is a genuine new metadata/filter param that "
        "should be added to `known_non_resolver` with a documented rationale."
    )
    missing_known = known_non_resolver - set(not_seam_reaching)
    assert not missing_known, (
        f"expected non-resolver param(s) {sorted(missing_known)} are no longer classified "
        "as non-resolver-driven — either they were removed (drop from `known_non_resolver`) "
        "or they now reach the seam (good — also fine to drop, they just moved categories)."
    )
