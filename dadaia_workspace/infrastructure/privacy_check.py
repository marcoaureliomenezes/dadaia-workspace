"""Privacy denylist constants, loader, and public-asset privacy check.

Extracted from ``public_assets.py`` to keep that module under 600 lines.
All names remain importable from ``dadaia_workspace.infrastructure.public_assets``
via its re-export block.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Iterable
from pathlib import Path

from dadaia_workspace.core.exceptions import WorkspaceNotInitializedError
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root

_PUBLIC_ASSET_IGNORED_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
_PUBLIC_ASSET_IGNORED_SUFFIXES = {".pyc", ".pyo"}
_PUBLIC_PRIVACY_TEXT_SUFFIXES = {
    ".css",
    ".html",
    ".j2",
    ".js",
    ".json",
    ".md",
    ".py",
    ".sh",
    ".toml",
    ".ts",
    ".txt",
    ".yaml",
    ".yml",
}
# Operator-private privacy terms are NEVER hardcoded in this published library
# (dev-guardrail rule #4: no consumer-specific data in shipped source). Each
# workspace supplies its own terms via a runtime file kept OUT of the package:
#   1. $DADAIA_PRIVACY_DENYLIST            (path to a JSON file), or
#   2. <workspace_root>/.dadaia/states/privacy_denylist.json
#      where workspace_root is resolved by walking up from cwd looking for the
#      .dadaia/states/spec_contexts.json sentinel (via resolve_workspace_root).
# Format: [["term", "reason"], ...] or {"term": "reason", ...}. Absent -> no terms.
_PRIVACY_DENYLIST_ENV = "DADAIA_PRIVACY_DENYLIST"
_PRIVACY_DENYLIST_REL = Path(".dadaia") / "states" / "privacy_denylist.json"


def _load_privacy_denylist() -> tuple[tuple[str, str], ...]:
    """Load operator-private privacy terms from outside the published package.

    Resolution order:
    1. ``$DADAIA_PRIVACY_DENYLIST`` environment variable — path to a JSON file.
    2. ``<workspace_root>/.dadaia/states/privacy_denylist.json`` where
       *workspace_root* is resolved by walking up from ``cwd`` looking for the
       ``.dadaia/states/spec_contexts.json`` sentinel. Returns ``()`` when no
       workspace root is found (e.g. pip-installed in site-packages without an
       active workspace) or the file is absent / unreadable / malformed.
    """
    candidates: list[Path] = []
    env_path = os.environ.get(_PRIVACY_DENYLIST_ENV)
    if env_path:
        candidates.append(Path(env_path))
    # Resolve workspace root via cwd-based walk-up; never fall back to the lib repo.
    try:
        workspace_root = resolve_workspace_root()
        candidates.append(workspace_root / _PRIVACY_DENYLIST_REL)
    except WorkspaceNotInitializedError:
        pass  # No workspace found — file-based fallback is simply unavailable.
    for source in candidates:
        try:
            raw = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        terms: list[tuple[str, str]] = []
        if isinstance(raw, dict):
            terms = [(str(key), str(value)) for key, value in raw.items()]
        elif isinstance(raw, list):
            for item in raw:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    terms.append((str(item[0]), str(item[1])))
                elif isinstance(item, str):
                    terms.append((item, "private identifier"))
        if terms:
            return tuple(terms)
    return ()


def check_public_privacy(
    public_dir: Path,
    iter_files_fn: Callable[[Path], Iterable[Path]],
    is_ignored_fn: Callable[[Path], bool],
) -> list[str]:
    """Fail doctor if public distributed assets contain known private identifiers."""
    lib_root = public_dir.parent.parent
    roots: list[Path] = [public_dir]
    denylist = _load_privacy_denylist()
    if not denylist:
        return ["[ok] public-privacy"]
    root_agents = lib_root / "AGENTS.md"
    if root_agents.exists():
        roots.append(root_agents)

    findings: list[str] = []
    for root in roots:
        files: list[Path] = [root] if root.is_file() else list(iter_files_fn(root))
        for path in files:
            if is_ignored_fn(path):
                continue
            if path.suffix.lower() not in _PUBLIC_PRIVACY_TEXT_SUFFIXES:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            lowered = text.lower()
            for term, reason in denylist:
                if term.lower() in lowered:
                    rel = path.relative_to(lib_root) if path.is_relative_to(lib_root) else path
                    findings.append(
                        f"[error] public-privacy:{rel.as_posix()}: contains '{term}' ({reason})"
                    )
    if not findings:
        findings.append("[ok] public-privacy")
    return findings
