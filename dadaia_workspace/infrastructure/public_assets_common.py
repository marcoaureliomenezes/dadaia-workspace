"""Shared low-level helpers for the public-asset pipeline.

These names have NO dependency on the other public_assets_* sub-modules and are
therefore safe to import from any of them without risk of circular imports.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Iterable
from enum import StrEnum
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from dadaia_workspace.infrastructure.privacy_check import (
    _PUBLIC_ASSET_IGNORED_DIRS,
    _PUBLIC_ASSET_IGNORED_SUFFIXES,
)

_SCHEMA_VERSION = "1"


class OverwritePolicy(StrEnum):
    """Whether a projected file that already exists on disk is replaced (FR6, T-30-10).

    Replaces the ``force: bool`` flag that used to travel through every private
    install-pipeline signature in ``public_assets.py``. ``FORCE`` is the historical
    ``force=True`` (clobber regardless of hash match); ``PRESERVE`` is the historical
    ``force=False`` default (hash-compare skip on a match, overwrite only on drift —
    the T-PROP-01 contract lives in the ``install_helpers``/``copy_file`` layer, which
    this enum does not change). ``install()``'s public ``force: bool`` parameter stays
    the port-conforming boundary; :meth:`of` is the ONE translation point.
    """

    FORCE = "force"
    PRESERVE = "preserve"

    @classmethod
    def of(cls, force: bool) -> OverwritePolicy:
        """Translate the port-conforming ``force: bool`` into a plan-carried policy."""
        return cls.FORCE if force else cls.PRESERVE

    @property
    def force(self) -> bool:
        """The raw ``bool`` the (out-of-scope) ``install_helpers``/``copy_file`` layer
        still expects — the ONE point where the policy is converted back."""
        return self is OverwritePolicy.FORCE


# Shared layout constants for the install/stage pipeline.
_COPY_DIRS = (
    "rules",
    "skills",
    "agents",
    "entities",
    "scripts",
    "schemas",
    "data",
    "scaffold",
    "templates",
)
_CLAUDE_DIRS = ("rules", "skills", "agents")


def is_ignored_public_asset(path: Path) -> bool:
    """True iff *path* is a build/cache artifact excluded from every public-asset walk."""
    return path.suffix in _PUBLIC_ASSET_IGNORED_SUFFIXES or bool(
        _PUBLIC_ASSET_IGNORED_DIRS.intersection(path.parts)
    )


def iter_public_files(root: Path) -> Iterable[Path]:
    """Every real (non-ignored) file under *root*, sorted — the ONE recursive walk
    ``stage()``/``install()``/``doctor()``/rule construction all share."""
    if not root.exists():
        return ()
    return (
        path
        for path in sorted(root.rglob("*"))
        if path.is_file() and not is_ignored_public_asset(path)
    )


def read_link_target(path: Path) -> str:
    """A symlink's target in its canonical POSIX spelling on every OS — the one reading the
    ledger digest, the doctor compare and the install skip agree on."""
    return os.readlink(path).replace(os.sep, "/")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _entry_digest(path: Path) -> str | None:
    """The ledgerable digest of one projected entry, or ``None`` when there is none.

    A symlink digests its TARGET STRING, never the bytes it points at: following the
    link would make a link and a copy of the same content indistinguishable, and would
    walk out of the workspace tree. A directory (the copy fallback's root) has no single
    digest — its files are ledgered individually.
    """
    if path.is_symlink():
        return hashlib.sha256(read_link_target(path).encode("utf-8")).hexdigest()
    if path.is_file():
        return _sha256(path)
    return None


def _package_version() -> str:
    try:
        return version("dadaia-workspace")
    except PackageNotFoundError:
        return "editable"


def _json_dump(data: object) -> str:
    return json.dumps(data, indent=2, sort_keys=True) + "\n"


def _toml_escape(value: object) -> str:
    """Escape *value* for safe emission as a TOML basic string (double-quoted).

    Rules applied (in order):
    1. Backslash -> double-backslash (must come first to avoid double-escaping)
    2. Double-quote -> backslash-double-quote
    3. Newline character -> the two-char escape sequence backslash-n

    For multi-line values the function falls back to a TOML triple-quoted
    multi-line basic string. If the value itself contains a triple-double-quote
    sequence, each occurrence is escaped character-by-character.

    Names containing ']' are rejected outright: they cannot be placed safely
    inside [agents."<name>"] TOML table headers even with quoting.
    """
    s = str(value)
    if "\n" in s:
        # Use triple-quoted literal; escape any embedded triple-quotes
        s_escaped = s.replace('"""', '\\"\\"\\"')
        return f'"""{s_escaped}"""'
    # Basic-string escaping for single-line values
    s = s.replace("\\", "\\\\")
    s = s.replace('"', '\\"')
    return f'"{s}"'
