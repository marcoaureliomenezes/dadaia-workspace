"""CLI-anchor derivation for the backlog subject registry — ``cli/`` composition helper.

The backlog canonical-subject registry treats ``dadaia <group> <verb>`` command ids as its
``cli``-kind anchors. Deriving that set means walking the live Typer app tree, which lives in
:mod:`dadaia_workspace.cli.main`. Keeping the walk **here in ``cli/``** (a composition
boundary, allowed to import ``cli.main``) means the feature layer never imports
``cli.main`` — ``build_registry`` accepts an already-derived ``frozenset[str]`` threaded in
at each composition boundary (FR1b). This closes the ``features.backlog.subject_registry ->
cli.main`` red chain that broke both ``features-no-infrastructure`` and
``features-no-subprocess`` transitively.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import typer


def derive_cli_anchors(app: typer.Typer | None = None) -> frozenset[str]:
    """Walk the Typer app tree into the set of ``<group> <verb>`` command ids.

    ``app`` defaults to the live ``dadaia`` Typer app (imported lazily here so the heavy
    ``cli.main`` module is only loaded at a real composition call, never at import time);
    tests pass a small fixture app. A registered command's id is the space-joined path of
    group names + the command name, e.g. ``backlog doctor``; a top-level command is its own
    bare name.
    """
    if app is None:
        from dadaia_workspace.cli.main import app as cli_app

        app = cli_app
    anchors: set[str] = set()
    _walk_typer(app, (), anchors, depth=0)
    return frozenset(anchors)


def _walk_typer(app: typer.Typer, prefix: tuple[str, ...], out: set[str], *, depth: int) -> None:
    if depth > 16:  # defensive recursion guard
        return
    for info in app.registered_commands:
        name = info.name or (info.callback.__name__ if info.callback else None)
        if name:
            out.add(" ".join((*prefix, name)))
    for group in app.registered_groups:
        sub = group.typer_instance
        if sub is None or group.name is None:
            continue
        _walk_typer(sub, (*prefix, group.name), out, depth=depth + 1)


__all__ = [
    "derive_cli_anchors",
]
