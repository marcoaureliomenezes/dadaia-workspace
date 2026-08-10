"""Shared low-level helpers for the public-asset pipeline.

These names have NO dependency on the other public_assets_* sub-modules and are
therefore safe to import from any of them without risk of circular imports.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from enum import StrEnum
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from dadaia_workspace.core.harness_registry import INSTALL_TARGETS

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


# Shared layout constants for the install/stage pipeline. The valid ``--target``
# vocabulary is single-sourced in ``core/harness_registry`` (v0.1.58 FR1); this name is
# a back-compat re-export for tests/consumers that import ``_VALID_TARGETS`` from here.
_VALID_TARGETS = INSTALL_TARGETS
_COPY_DIRS = (
    "rules",
    "skills",
    "commands",
    "agents",
    "entities",
    "scripts",
    "schemas",
    "data",
    "scaffold",
    "templates",
    "runtime",
    "kimi-code",
)
_CLAUDE_DIRS = ("rules", "skills", "commands", "agents")
#: Subdirectories of the staged ``kimi-code/`` tree for ``--only`` filtering (v0.2.8).
#: Empty for now — the tree currently ships a single root ``AGENTS.md``.
_KIMI_DIRS: tuple[str, ...] = ()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def _atomic_write_text(dst: Path, content: str) -> None:
    """Write *content* to *dst* atomically via a sibling .tmp file + os.replace().

    Guarantees the destination either contains the full new content or is
    unchanged — prevents readers from observing a partially-written file.
    """
    tmp = dst.with_suffix(dst.suffix + ".tmp")
    # newline="" disables universal-newline translation so the bytes on disk are
    # exactly content.encode("utf-8"). Without it, Windows text mode rewrites "\n"
    # to "\r\n", which breaks write_generated's hash-compare skip (it hashes the
    # LF content against a binary read of the file) — every install would rewrite
    # every generated file. Keeps projected files LF on all platforms. See FR-RC2-2.
    tmp.write_text(content, encoding="utf-8", newline="")
    os.replace(tmp, dst)


def _log_cleanup_error(
    func: object,
    path: object,
    exc_info: tuple[type[BaseException], BaseException, Any] | tuple[None, None, None],
) -> None:
    """onerror= callback for shutil.rmtree — write a warning to stderr without re-raising.

    Replaces the anti-pattern ``ignore_errors=True`` (which silences real
    PermissionError / OSError) with a visible-but-non-fatal warning so that
    operators can act on stale files while the install still succeeds.
    """
    exc_class = type(exc_info[1]).__name__ if exc_info and exc_info[1] else "UnknownError"
    exc_msg = str(exc_info[1]) if exc_info and exc_info[1] else ""
    sys.stderr.write(f"[cleanup-warning] {path}: {exc_class}: {exc_msg}\n")
