"""Consumer-repo discovery and AGENTS.md/CLAUDE.md guardrail install/doctor.

Extracted from ``public_assets.py`` to keep that module under 600 lines.
All names remain importable from ``dadaia_workspace.infrastructure.public_assets``
via its re-export block.
"""

from __future__ import annotations

import functools
import hashlib
import json
import shutil
import sys
import tomllib
from pathlib import Path
from typing import Literal

from dadaia_workspace.infrastructure.public_assets_common import (
    _atomic_write_text,
    _package_version,
)

# T-021-18: CLAUDE.md is the Claude Code bridge that imports @AGENTS.md — the single
# source of workspace law. Claude Code reads CLAUDE.md natively and follows the @-import
# to load AGENTS.md (see code.claude.com/docs/en/memory#agentsmd). One line is sufficient.
_CLAUDE_MD_STUB = "@AGENTS.md\n"


def _consumer_repos_for_root(workspace_root: Path) -> list[Path]:
    """Return marker-bearing consumer repo directories under ``workspace_root/repos/``.

    A directory qualifies when BOTH markers are present (R13):
    - ``<repo>/.dadaia/`` directory
    - ``<repo>/.dadaia/agentic/`` directory

    Non-qualifying directories emit a ``[skip]`` line to stderr.
    """
    repos_dir = workspace_root / "repos"
    if not repos_dir.is_dir():
        return []
    result: list[Path] = []
    for p in sorted(repos_dir.iterdir()):
        if not p.is_dir():
            continue
        if (p / ".dadaia").is_dir() and (p / ".dadaia" / "agentic").is_dir():
            result.append(p)
        else:
            sys.stderr.write(f"[skip] {p / 'AGENTS.md'} (no .dadaia/ marker)\n")
    return result


def _is_self_repo(consumer: Path) -> bool:
    """Return True when *consumer* is the dadaia-workspace repo itself (R14).

    Two independent checks, either of which is sufficient.

    Primary (manifest-based): compares ``package_version`` in the consumer's
    manifest against the currently installed package version.  A match means
    the consumer IS the dadaia-workspace source tree.

    Secondary (pyproject-based): if the consumer directory contains a
    ``pyproject.toml`` whose ``[tool.poetry] name`` or ``[project] name``
    equals ``"dadaia-workspace"``, treat it as self regardless of whether a
    manifest exists.  This closes the gap where a fresh clone (no
    ``.dadaia/agentic/manifest.json`` yet) could be mistakenly scaffolded into
    the library source tree.
    """
    # Secondary check: pyproject.toml name detection (manifest-independent)
    pyproject_path = consumer / "pyproject.toml"
    if pyproject_path.exists():
        try:
            data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
            poetry_name = data.get("tool", {}).get("poetry", {}).get("name", "")
            project_name = data.get("project", {}).get("name", "")
            if poetry_name == "dadaia-workspace" or project_name == "dadaia-workspace":
                return True
        except (tomllib.TOMLDecodeError, OSError):
            pass

    # Primary check: manifest version match
    manifest_path = consumer / ".dadaia" / "agentic" / "manifest.json"
    if not manifest_path.exists():
        return False
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        consumer_version = manifest.get("package_version", "")
        return bool(consumer_version and consumer_version == _package_version())
    except (json.JSONDecodeError, OSError):
        return False


def _is_source_repo_root(path: Path) -> bool:
    """Return True only for the dadaia-workspace source tree root.

    Unlike ``_is_self_repo()``, this intentionally ignores staged manifest
    versions. A normal temporary consumer workspace becomes version-matching
    after ``stage()``, and must still be installable. The source-root guard is
    only for the library checkout that contains the package source itself.
    """
    pyproject_path = path / "pyproject.toml"
    if not pyproject_path.exists():
        return False
    if not (path / "dadaia_workspace" / "public").is_dir():
        return False
    try:
        data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError):
        return False
    tool = data.get("tool")
    poetry_name = ""
    if isinstance(tool, dict):
        poetry = tool.get("poetry")
        if isinstance(poetry, dict):
            name = poetry.get("name")
            if isinstance(name, str):
                poetry_name = name

    project_name = ""
    project = data.get("project")
    if isinstance(project, dict):
        name = project.get("name")
        if isinstance(name, str):
            project_name = name
    return poetry_name == "dadaia-workspace" or project_name == "dadaia-workspace"


def _install_guardrail_pair(
    source: Path,
    workspace_root: Path,
    force: bool,
    installed: list[str] | None = None,
    targets: set[Literal["workspace", "repos"]] | None = None,
) -> None:
    """Write the AGENTS.md + CLAUDE.md guardrail pair to the requested targets.

    This is the single implementation for all three scope variants:
    - ``targets={"workspace", "repos"}`` — workspace root + all consumer repos (scope="all")
    - ``targets={"workspace"}``          — workspace root only (scope="workspace-only")
    - ``targets={"repos"}``              — consumer repos only (scope="repos-only")

    Hash-compare logic (T-PROP-01): files are overwritten only when the source
    SHA-256 differs from the destination, even when ``force=False``.

    Self-skip (R14): consumer repos whose manifest ``package_version`` matches
    the installed package version are skipped (they are the dadaia-workspace
    source tree).

    Marker-less repos under ``repos/`` emit ``[skip]`` to stderr and are never
    written.  The function never raises on missing/unexpected paths.

    Args:
        source: Absolute path to ``data/AGENTS.md`` (the single source of truth).
        workspace_root: Workspace root directory.
        force: When True, overwrite existing files; when False, skip if present.
        installed: Optional list mutated with ``"[ok]   <path>"`` strings.
        targets: Which targets to write. Defaults to ``{"workspace", "repos"}``.
    """
    if installed is None:
        installed = []
    if targets is None:
        targets = {"workspace", "repos"}

    src_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    stub_sha = hashlib.sha256(_CLAUDE_MD_STUB.encode()).hexdigest()

    def _write_pair(target_dir: Path) -> None:
        # AGENTS.md — full canonical content copied from source.
        agents_dst = target_dir / "AGENTS.md"
        agents_dst.parent.mkdir(parents=True, exist_ok=True)
        if agents_dst.exists() and not force:
            # Hash-compare: skip only when content is identical (T-PROP-01).
            if hashlib.sha256(agents_dst.read_bytes()).hexdigest() == src_sha:
                installed.append(f"[skip] {agents_dst}")
            else:
                shutil.copy2(source, agents_dst)
                installed.append(f"[ok]   {agents_dst}")
        else:
            shutil.copy2(source, agents_dst)
            installed.append(f"[ok]   {agents_dst}")
        # CLAUDE.md — 1-line stub only (T-41: delegates to AGENTS.md).
        claude_dst = target_dir / "CLAUDE.md"
        claude_dst.parent.mkdir(parents=True, exist_ok=True)
        if claude_dst.exists() and not force:
            # Hash-compare: skip only when stub content is identical (T-PROP-01).
            if hashlib.sha256(claude_dst.read_bytes()).hexdigest() == stub_sha:
                installed.append(f"[skip] {claude_dst}")
            else:
                _atomic_write_text(claude_dst, _CLAUDE_MD_STUB)
                installed.append(f"[ok]   {claude_dst}")
        else:
            _atomic_write_text(claude_dst, _CLAUDE_MD_STUB)
            installed.append(f"[ok]   {claude_dst}")

    if "workspace" in targets:
        _write_pair(workspace_root)

    if "repos" in targets:
        for consumer in _consumer_repos_for_root(workspace_root):
            if _is_self_repo(consumer):
                v = _package_version()
                sys.stderr.write(
                    f"[skip] {consumer / 'AGENTS.md'} (self-projection — package_version={v})\n"
                )
                continue
            _write_pair(consumer)


# ---------------------------------------------------------------------------
# Backward-compatible aliases — delegate to _install_guardrail_pair.
# These names are imported by tests and must remain importable.
# Using functools.partial avoids duplicate def statements while preserving
# the original call signatures (positional + keyword arguments all pass through).
# ---------------------------------------------------------------------------

_install_workspace_guardrail_pair = functools.partial(
    _install_guardrail_pair, targets={"workspace", "repos"}
)
"""Fan source out to workspace root + all consumer repos (scope="all")."""

_install_workspace_root_guardrail_pair = functools.partial(
    _install_guardrail_pair, targets={"workspace"}
)
"""Write the guardrail pair to workspace_root only (scope="workspace-only")."""

_install_consumer_repos_guardrail_pair = functools.partial(
    _install_guardrail_pair, targets={"repos"}
)
"""Write the guardrail pair to consumer repos only (scope="repos-only")."""


def _doctor_guardrail_pair(
    source: Path,
    workspace_root: Path,
) -> list[str]:
    """Return doctor parity lines for the guardrail pair projection.

    Emits 2 root lines + 2 lines per marker-bearing consumer (R13).
    Each line is ``[ok] <label>`` or ``[drift] <label>`` or ``[missing] <label>``.
    Lines are also written to stderr for CLI visibility.

    Labels: ``root:AGENTS.md``, ``root:CLAUDE.md``,
    ``repos/<slug>:AGENTS.md``, ``repos/<slug>:CLAUDE.md``.
    """
    source_sha = hashlib.sha256(source.read_bytes()).hexdigest()

    def _check(dst: Path, label: str) -> str:
        if not dst.exists():
            line = f"[missing] {label}"
        elif hashlib.sha256(dst.read_bytes()).hexdigest() != source_sha:
            line = f"[drift] {label}"
        else:
            line = f"[ok] {label}"
        sys.stderr.write(line + "\n")
        return line

    def _check_stub(dst: Path, label: str) -> str:
        """Verify that *dst* contains the expected 1-line CLAUDE.md stub (T-41)."""
        if not dst.exists():
            line = f"[missing] {label}"
        elif dst.read_text(encoding="utf-8") != _CLAUDE_MD_STUB:
            line = f"[drift] {label}"
        else:
            line = f"[ok] {label}"
        sys.stderr.write(line + "\n")
        return line

    lines: list[str] = []
    lines.append(_check(workspace_root / "AGENTS.md", "root:AGENTS.md"))
    lines.append(_check_stub(workspace_root / "CLAUDE.md", "root:CLAUDE.md"))

    for consumer in _consumer_repos_for_root(workspace_root):
        if _is_self_repo(consumer):
            continue
        slug = consumer.name
        lines.append(_check(consumer / "AGENTS.md", f"repos/{slug}:AGENTS.md"))
        lines.append(_check_stub(consumer / "CLAUDE.md", f"repos/{slug}:CLAUDE.md"))

    return lines
