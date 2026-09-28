"""Leaf helpers for the public-asset pipeline (imports no sibling module)."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Iterable
from pathlib import Path

from dadaia_workspace.infrastructure.privacy_check import (
    _PUBLIC_ASSET_IGNORED_DIRS,
    _PUBLIC_ASSET_IGNORED_SUFFIXES,
)
from dadaia_workspace.infrastructure.provider_version import provider_version

_SCHEMA_VERSION = "1"


#: The staged families: each has a reader of ``.dadaia/agentic/``.
_COPY_DIRS = ("skills", "agents", "schemas", "data")
_CLAUDE_DIRS = ("skills", "agents")


def iter_public_files(root: Path) -> Iterable[Path]:
    """Every file under *root*, sorted — the ONE public-asset walk; build/cache artifacts
    are judged by their path below *root* only, never by where the package is installed
    (a CLI inside ``<ws>/.dadaia/.venv`` walks the same set as a source checkout)."""
    if not root.exists():
        return ()
    return (
        path
        for path in sorted(root.rglob("*"))
        if path.is_file()
        and path.suffix not in _PUBLIC_ASSET_IGNORED_SUFFIXES
        and not _PUBLIC_ASSET_IGNORED_DIRS.intersection(path.relative_to(root).parts)
    )


def read_link_target(path: Path) -> str:
    """A symlink's target in POSIX spelling on every OS."""
    return os.readlink(path).replace(os.sep, "/")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _entry_digest(path: Path) -> str | None:
    """The ledger digest of one entry; ``None`` for a directory.

    A symlink digests its target string, so a link and a copy stay distinguishable.
    """
    if path.is_symlink():
        return hashlib.sha256(read_link_target(path).encode("utf-8")).hexdigest()
    if path.is_file():
        return _sha256(path)
    return None


def _package_version() -> str:
    return provider_version() or "editable"


def _json_dump(data: object) -> str:
    return json.dumps(data, indent=2, sort_keys=True) + "\n"


def _toml_escape(value: object) -> str:
    """*value* as a TOML string: multi-line basic when it holds a newline, else basic."""
    s = str(value)
    if "\n" in s:
        return '"""' + s.replace('"""', '\\"\\"\\"') + '"""'
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
