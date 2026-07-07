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
from collections.abc import Callable
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Literal

from dadaia_workspace.infrastructure.public_assets_common import (
    _atomic_write_text,
    _package_version,
)

# T-021-18: CLAUDE.md is the Claude Code bridge that imports @AGENTS.md — the single
# source of workspace law. Claude Code reads CLAUDE.md natively and follows the @-import
# to load AGENTS.md (see code.claude.com/docs/en/memory#agentsmd). One line is sufficient.
_CLAUDE_MD_STUB = "@AGENTS.md\n"

# FR9 (v0.1.60) — provenance discriminator for the consumer-repo AGENTS.md fan-out.
# A consumer root AGENTS.md that BEGINS WITH this exact banner block is a provable
# ``dadaia public install`` projection (lib-owned, overwritable); anything else is
# hand-authored / repo-owned and MUST NEVER be clobbered (the HIGH bug
# public-install-clobbers-consumer-repo-agents-md). This is a FIXED LITERAL — never a
# runtime read of ``public/data`` — asserted byte-equal to the actual
# ``public/data/AGENTS.md`` banner by the contract test
# ``test_agents_banner_constant_matches_public_data`` (Ruling 15 / ADR-9). Only
# ``public install`` emits this banner, so its presence is deterministic provenance.
_CANONICAL_AGENTS_BANNER = (
    "> **AI agent rules.** This file is generated from\n"
    "> `dadaia_workspace/public/data/AGENTS.md` by `dadaia public install`.\n"
    "> Do not put project-specific instructions here. Put them in a scoped\n"
    "> `AGENTS.md` / `CLAUDE.md` inside the repo or directory they govern.\n"
)


def _carries_canonical_banner(dst: Path) -> bool:
    """True when *dst* begins with the generated provenance banner (a lib-owned copy).

    The byte-exact full-banner-block match minimizes accidental collision (ADR-9 residual
    risk). An unreadable / non-UTF-8 file is treated as foreign (never overwrite).
    """
    try:
        return dst.read_text(encoding="utf-8").startswith(_CANONICAL_AGENTS_BANNER)
    except (OSError, UnicodeDecodeError):
        return False


def _slug_is_safe(slug: str) -> bool:
    """FR5 (v0.1.62, ADR-6) — lexical validation of a registry ``repo_slug``.

    A safe slug is a SINGLE, RELATIVE, NON-DOT path component. Rejected forms:
    separators (``/`` or ``\\``), ``.`` / ``..``, absolute paths including
    Windows drive (``C:...``) and UNC (``\\\\host\\...``) forms. Both
    :class:`PurePosixPath` and :class:`PureWindowsPath` semantics are checked so
    the validation is platform-independent (a Windows-hostile slug is rejected
    on POSIX too, and vice versa). Purely lexical — never touches the filesystem.
    """
    if not slug or slug in {".", ".."}:
        return False
    if "/" in slug or "\\" in slug:
        return False
    if Path(slug).is_absolute() or PureWindowsPath(slug).is_absolute():
        return False
    if len(PurePosixPath(slug).parts) != 1 or len(PureWindowsPath(slug).parts) != 1:
        return False
    return not PureWindowsPath(slug).drive


def _reject_slug(slug: str) -> None:
    """FR5 non-silent rejection (A3 never-silent law): one stderr line, then skip."""
    sys.stderr.write(f"[reject] repo_slug '{slug}' (unsafe path component) — skipped\n")


def _consumer_repos_for_root(workspace_root: Path) -> list[Path]:
    """Return consumer repo directories registered in ``spec_contexts.json``.

    Detection is registry-based (v0.1.58 FR4, Ruling G). Reads
    ``<workspace_root>/.dadaia/states/spec_contexts.json`` (schema v2) and derives
    ``<workspace_root>/repos/<repo_slug>/`` for every registered context whose
    directory exists on disk — **alive OR dead** (Ruling H). The old in-repo
    ``.dadaia/agentic/`` marker requirement is DROPPED: the repo-cleanliness law
    forbids ``.dadaia/`` inside a repo working tree, so the marker made the
    fan-out dead by construction (a compliant workspace never had it).

    Contexts listed in the registry but absent under ``repos/`` are skipped
    silently (no error, no stderr line). Duplicate ``repo_slug`` values collapse
    to a single path. The ``_is_self_repo`` skip (the dadaia-workspace source
    tree) is applied by the callers, not here.

    Never raises: a missing / unreadable / malformed / non-v2 registry yields an
    empty list — the fan-out and doctor degrade to workspace-root-only, never
    crash.
    """
    registry = workspace_root / ".dadaia" / "states" / "spec_contexts.json"
    if not registry.is_file():
        return []
    try:
        data = json.loads(registry.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, dict):
        return []
    contexts = data.get("contexts")
    if not isinstance(contexts, list):
        return []
    repos_dir = workspace_root / "repos"
    result: list[Path] = []
    seen: set[str] = set()
    for ctx in contexts:
        if not isinstance(ctx, dict):
            continue
        slug = ctx.get("repo_slug")
        if not isinstance(slug, str) or not slug or slug in seen:
            continue
        seen.add(slug)
        if not _slug_is_safe(slug):
            # FR5: lexical containment — a hostile slug never reaches the join.
            # Non-silent (distinct from the silent skip of absent dirs); fail-open.
            _reject_slug(slug)
            continue
        candidate = repos_dir / slug
        if candidate.is_dir():
            result.append(candidate)
    return sorted(result)


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
    the installed package version (or whose ``pyproject.toml`` names
    ``dadaia-workspace``) are skipped — they are the dadaia-workspace source tree.

    Consumer detection is registry-based (v0.1.58 FR4): the repos written are
    those registered in ``spec_contexts.json`` whose dir exists on disk. A
    context absent under ``repos/`` is skipped silently. The function never
    raises on missing/unexpected paths.

    Ruling L (A5): the consumer-repo ROOT ``AGENTS.md`` is lib-owned canonical.
    A divergent (hand-edited) consumer copy is restored to canonical, and the
    overwrite is reported with a DISTINCT ``[updated] <path> (overwrote divergent
    workspace-law copy)`` line — never a silent ``[ok]``. The workspace-root pair
    keeps its ``[ok]`` overwrite semantics. Nested subtree ``AGENTS.md`` files are
    never touched (only the repo root is written).

    Args:
        source: Absolute path to ``data/AGENTS.md`` (the single source of truth).
        workspace_root: Workspace root directory.
        force: When True, overwrite existing files; when False, skip if identical.
        installed: Optional list mutated with ``"[ok]   <path>"`` / ``"[skip] ..."``
            / ``"[updated] ..."`` strings.
        targets: Which targets to write. Defaults to ``{"workspace", "repos"}``.
    """
    if installed is None:
        installed = []
    if targets is None:
        targets = {"workspace", "repos"}

    src_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    stub_sha = hashlib.sha256(_CLAUDE_MD_STUB.encode()).hexdigest()

    def _write_one(
        dst: Path,
        expected_sha: str,
        write_fn: Callable[[], object],
        is_consumer: bool,
    ) -> None:
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            if hashlib.sha256(dst.read_bytes()).hexdigest() == expected_sha:
                # Already canonical: force rewrites (byte-identical) else no-op.
                if force:
                    write_fn()
                    installed.append(f"[ok]   {dst}")
                else:
                    installed.append(f"[skip] {dst}")
                return
            # Existing file diverges from the canonical workspace-law copy.
            write_fn()
            if is_consumer:
                # Ruling L (A5): restore a divergent consumer copy with a DISTINCT,
                # visible line so the operator always sees a restoration happened.
                installed.append(f"[updated] {dst} (overwrote divergent workspace-law copy)")
            else:
                installed.append(f"[ok]   {dst}")
            return
        write_fn()
        installed.append(f"[ok]   {dst}")

    def _write_consumer_agents(dst: Path) -> bool:
        """FR9 provenance-gated consumer AGENTS.md write. Returns True iff the sibling
        CLAUDE.md should be written (created / restored), False when the AGENTS.md is
        foreign (hand-authored) and left untouched.
        """
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.is_symlink():
            # FR6 (ADR-7): NEVER write through a destination-file symlink — checked
            # BEFORE exists() so a DANGLING link is refused too (never "absent → create").
            installed.append(f"[foreign] {dst} — left untouched (symlink)")
            return False
        if not dst.exists():
            # Case 3 (absent): create — an empty slot has nothing to clobber.
            shutil.copy2(source, dst)
            installed.append(f"[ok]   {dst}")
            return True
        if hashlib.sha256(dst.read_bytes()).hexdigest() == src_sha:
            if force:
                shutil.copy2(source, dst)
                installed.append(f"[ok]   {dst}")
            else:
                installed.append(f"[skip] {dst}")
            return True
        if _carries_canonical_banner(dst):
            # Case 1 (banner match): stale canonical projection → restore + DISTINCT line.
            shutil.copy2(source, dst)
            installed.append(f"[updated] {dst} (overwrote divergent workspace-law copy)")
            return True
        # Case 2 (no banner): FOREIGN / repo-owned → NEVER overwrite (the bug fix).
        installed.append(f"[foreign] {dst} — left untouched")
        return False

    def _write_consumer_claude(dst: Path, sibling_written: bool) -> None:
        """FR9: the CLAUDE.md bridge follows its sibling's fate.

        Written ONLY when the sibling AGENTS.md was created/restored; when AGENTS.md is
        foreign, no CLAUDE.md is dropped (the orphan-drop the bug flags). A foreign
        (non-stub) existing CLAUDE.md is always left untouched.
        """
        if dst.is_symlink():
            # FR6 (ADR-7): a symlinked CLAUDE.md (incl. dangling) is never written through.
            installed.append(f"[foreign] {dst} — left untouched (symlink)")
            return
        if sibling_written:
            dst.parent.mkdir(parents=True, exist_ok=True)
            if not dst.exists():
                _atomic_write_text(dst, _CLAUDE_MD_STUB)
                installed.append(f"[ok]   {dst}")
            elif dst.read_text(encoding="utf-8") == _CLAUDE_MD_STUB:
                if force:
                    _atomic_write_text(dst, _CLAUDE_MD_STUB)
                    installed.append(f"[ok]   {dst}")
                else:
                    installed.append(f"[skip] {dst}")
            else:
                installed.append(f"[foreign] {dst} — left untouched")
        elif dst.exists() and dst.read_text(encoding="utf-8") != _CLAUDE_MD_STUB:
            installed.append(f"[foreign] {dst} — left untouched")

    def _write_pair(target_dir: Path, is_consumer: bool) -> None:
        agents_dst = target_dir / "AGENTS.md"
        claude_dst = target_dir / "CLAUDE.md"
        if is_consumer:
            # FR9: provenance-gated — never clobber a hand-authored consumer AGENTS.md.
            sibling_written = _write_consumer_agents(agents_dst)
            _write_consumer_claude(claude_dst, sibling_written)
            return
        # Workspace root: lib-owned canonical (unchanged Ruling-L overwrite semantics).
        _write_one(agents_dst, src_sha, lambda: shutil.copy2(source, agents_dst), is_consumer)
        _write_one(
            claude_dst,
            stub_sha,
            lambda: _atomic_write_text(claude_dst, _CLAUDE_MD_STUB),
            is_consumer,
        )

    if "workspace" in targets:
        _write_pair(workspace_root, is_consumer=False)

    if "repos" in targets:
        repos_dir = workspace_root / "repos"
        for consumer in _consumer_repos_for_root(workspace_root):
            if consumer.parent != repos_dir:
                # FR5 (ADR-6) belt-and-braces: write-time containment assert — the
                # lexical join must stay directly inside repos/. Skip, never write,
                # never raise (trivially true post-validation).
                _reject_slug(consumer.name)
                continue
            if _is_self_repo(consumer):
                v = _package_version()
                sys.stderr.write(
                    f"[skip] {consumer / 'AGENTS.md'} (self-projection — package_version={v})\n"
                )
                continue
            _write_pair(consumer, is_consumer=True)


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


def _doctor_consumer_pair_lines(
    source: Path,
    workspace_root: Path,
    *,
    emit_stderr: bool = True,
) -> list[str]:
    """The SINGLE authority for provenance-aware CONSUMER guardrail-pair doctor lines (FR9).

    This is the one classification used by BOTH ``manager.doctor()`` (the real
    ``dadaia public doctor`` consumer fan-out — the ``repos/<slug>:`` lines are no longer
    emitted by ``runtime_expectations``) AND :func:`_doctor_guardrail_pair`. There is no
    parallel legacy consumer-doctor path.

    Per registry-detected consumer repo (self-repo skipped):
      * **AGENTS.md** — absent → ``[missing]``; no canonical banner → ``[foreign]`` (repo-owned,
        NOT a drift); banner-bearing → ``[ok]``/``[drift]`` vs *source*.
      * **CLAUDE.md** — paired (Ruling 16, CRITICAL): when the AGENTS.md line is ``[foreign]``
        the CLAUDE.md line is ALSO ``[foreign]`` (whether absent OR a foreign non-stub) — never
        ``[missing]``/``[drift]`` — so ``public doctor`` (exits 1 on any ``[missing]``/``[drift]``,
        ``public.py:161-172``) EXITS 0 for a hand-authored consumer repo. Otherwise the stub
        check applies (``[ok]``/``[drift]``/``[missing]``).

    Never ``[skip]`` for a real consumer repo.
    """
    source_sha = hashlib.sha256(source.read_bytes()).hexdigest()

    def _emit(line: str) -> str:
        if emit_stderr:
            sys.stderr.write(line + "\n")
        return line

    lines: list[str] = []
    for consumer in _consumer_repos_for_root(workspace_root):
        if _is_self_repo(consumer):
            continue
        slug = consumer.name
        agents_dst = consumer / "AGENTS.md"
        a_label = f"repos/{slug}:AGENTS.md"
        if agents_dst.is_symlink():
            # FR6: symlink-aware doctor — a symlinked pair FILE is [foreign] (never
            # [ok]/[drift]/[missing]) so doctor exits 0 and never prescribes an
            # install that would be refused. Symlinked consumer DIRS remain legit.
            agents_line = f"[foreign] {a_label}"
        elif not agents_dst.exists():
            agents_line = f"[missing] {a_label}"
        elif not _carries_canonical_banner(agents_dst):
            agents_line = f"[foreign] {a_label}"
        elif hashlib.sha256(agents_dst.read_bytes()).hexdigest() != source_sha:
            agents_line = f"[drift] {a_label}"
        else:
            agents_line = f"[ok] {a_label}"
        lines.append(_emit(agents_line))

        claude_dst = consumer / "CLAUDE.md"
        c_label = f"repos/{slug}:CLAUDE.md"
        if agents_line.startswith("[foreign]") or claude_dst.is_symlink():
            claude_line = f"[foreign] {c_label}"
        elif not claude_dst.exists():
            claude_line = f"[missing] {c_label}"
        elif claude_dst.read_text(encoding="utf-8") != _CLAUDE_MD_STUB:
            claude_line = f"[drift] {c_label}"
        else:
            claude_line = f"[ok] {c_label}"
        lines.append(_emit(claude_line))
    return lines


def _doctor_guardrail_pair(
    source: Path,
    workspace_root: Path,
) -> list[str]:
    """Return doctor parity lines for the guardrail pair projection.

    Emits 2 root lines + the provenance-aware consumer pair lines from the single authority
    :func:`_doctor_consumer_pair_lines` (so this helper and ``manager.doctor()`` classify
    consumers identically — no dead parallel path). Lines are also written to stderr for CLI
    visibility.

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
    lines.extend(_doctor_consumer_pair_lines(source, workspace_root, emit_stderr=True))
    return lines
