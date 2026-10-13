"""Workspace checks: rules about the repo's files that no pytest test judges."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from run import Check, Session, Tree

_QUICKSTART = ("docs/quickstart.md", "tests/fixtures/quickstart.md")


def quickstart_fixture_is_the_doc(tree: Tree) -> list[str]:
    """The e2e's quickstart fixture is byte-equal to ``docs/quickstart.md``."""
    doc, fixture = _QUICKSTART
    return [] if tree.read(doc) == tree.read(fixture) else [f"stale: {fixture} differs from {doc}"]


def _write(root: Path, rel: str, text: str) -> None:
    (root / rel).parent.mkdir(parents=True, exist_ok=True)
    (root / rel).write_text(text, encoding="utf-8")


def CONTROL(root: Path) -> Session:
    """The doc and its fixture, equal; violations only in an ignored file."""
    for rel in _QUICKSTART:
        _write(root, rel, "```bash\nuvx x\n```\n")
    return {}


def _stale(root: Path) -> None:
    CONTROL(root)
    _write(root, _QUICKSTART[1], "```bash\nuvx y\n```\n")


CHECKS: dict[str, Check] = {
    "workspace-quickstart-fixture": (quickstart_fixture_is_the_doc, {"stale": _stale}),
}
