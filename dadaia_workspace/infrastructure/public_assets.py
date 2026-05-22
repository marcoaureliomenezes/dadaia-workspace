"""Public asset manager — stages package assets and projects them to agent runtimes."""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
import shutil
import sys
import tomllib
from collections.abc import Iterable
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Literal

from dadaia_workspace.core.exceptions import PublicAssetError

_SCHEMA_VERSION = "1"
# T-41: CLAUDE.md is a 1-line stub that delegates to AGENTS.md.
# Claude Code does not yet support `@AGENTS.md` include syntax natively, so we
# use a comment-style redirect that is human-readable and forwards readers.
_CLAUDE_MD_STUB = "# See AGENTS.md for workspace rules and agent personas.\n"
# OpenCode v1.14+ expects `tools` to be an object or omitted — not an array.
# Strip it from agent frontmatter when deploying to the opencode projection.
_FRONTMATTER_TOOLS_RE = re.compile(r"^tools:\n(?:  - [^\n]+\n)*", re.MULTILINE)
# `opencode_model:` lets agents declare a cheaper model for the OpenCode projection.
_FRONTMATTER_OPENCODE_MODEL_RE = re.compile(r"^opencode_model:\s*(.+?)$", re.MULTILINE)
_FRONTMATTER_MODEL_VALUE_RE = re.compile(r"^(model:\s*)(.+?)$", re.MULTILINE)
_FRONTMATTER_OPENCODE_MODEL_FIELD_RE = re.compile(r"^opencode_model:[^\n]*\n", re.MULTILINE)
# T-35: forbid the legacy `software-engineer` alias inside public/ (split into
# `software-engineer-python` and `software-engineer-node`). Matches subagent_type:
# software-engineer with no trailing -python/-node suffix.
_LEGACY_SE_ALIAS_RE = re.compile(
    r"subagent_type\s*[:=]\s*[\"']?software-engineer(?![-_a-z])",
    re.IGNORECASE,
)
_VALID_TARGETS = {"all", "agents", "claude", "codex", "opencode"}
_COPY_DIRS = (
    "rules",
    "skills",
    "commands",
    "agents",
    "scripts",
    "schemas",
    "data",
    "scaffold",
    "templates",
    "plugins",
    "runtime",
    "workflows",
)
_CLAUDE_DIRS = ("rules", "skills", "commands", "agents", "workflows")
_OPENCODE_DIRS = ("commands", "skills", "agents", "plugins", "workflows")
_FRONTMATTER_PARALLEL_GROUP_RE = re.compile(r"^\s*parallel_group:\s*\S", re.MULTILINE)

# Whitelist of agent frontmatter fields that may be emitted to codex config.toml.
_TOML_SAFE_AGENT_FIELDS: frozenset[str] = frozenset({"name", "description", "model", "tools"})

# Matches a YAML list item under `tools:` (e.g. "  - Read")
_AGENT_FM_TOOLS_ITEM_RE = re.compile(r"^  - (.+)$", re.MULTILINE)
# Matches a simple `key: value` line in frontmatter (single-line value)
_AGENT_FM_SIMPLE_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*): (.+)$", re.MULTILINE)
# Matches a folded/literal scalar intro: `key: >` or `key: |`
_AGENT_FM_BLOCK_SCALAR_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*): [>|]$", re.MULTILINE)


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


def _render_agents_into_codex_config(agents_dir: Path) -> str:
    """Scan *agents_dir* for ``.md`` agent files and render TOML ``[agents.*]`` blocks.

    For each ``.md`` file (sorted for determinism):
    1. Parse YAML frontmatter via ``_parse_agent_frontmatter()``.
    2. If the result is non-empty (i.e., ``name`` key present), render via
       ``_render_agent_toml_block()``.
    3. Agents whose frontmatter cannot be parsed or are missing ``name`` are
       silently skipped (defensive — never breaks install).

    Returns the concatenated block string (may be empty string when no agents
    are found).
    """
    if not agents_dir.exists():
        return ""
    blocks: list[str] = []
    for md_file in sorted(agents_dir.glob("*.md")):
        try:
            text = md_file.read_text(encoding="utf-8")
            fm = _parse_agent_frontmatter(text)
            if not fm:
                continue
            name = str(fm.get("name", ""))
            if not name:
                continue
            blocks.append(_render_agent_toml_block(name, fm))
        except (OSError, ValueError):
            continue
    return "\n".join(blocks) + ("\n" if blocks else "")


def _render_codex_agent_toml(
    name: str,
    model: str,
    developer_instructions: str,
    description: str | None = None,
) -> str:
    """Serialize an agent as a TOML file for the Codex runtime.

    Emits four fields:
    - ``name`` — basic string
    - ``description`` — basic string when available
    - ``model`` — basic string
    - ``developer_instructions`` — triple-quoted multiline basic string

    The function avoids external TOML serialiser dependencies; it builds the
    content manually and is safe for all printable Unicode in instructions text.

    In a TOML triple-quoted basic string, backslashes are escape characters.
    All literal backslashes in the body must be doubled (``\\``), and any
    embedded triple-double-quote sequences must be escaped character-by-character
    to prevent premature string termination.
    """
    # Step 1: escape backslashes first (must precede triple-quote escaping).
    escaped = developer_instructions.replace("\\", "\\\\")
    # Step 2: escape any embedded triple-double-quote sequences.
    escaped = escaped.replace('"""', '\\"\\"\\"')
    lines: list[str] = [
        f"name = {_toml_escape(name)}\n",
    ]
    if description:
        lines.append(f"description = {_toml_escape(description)}\n")
    lines.extend(
        [
            f"model = {_toml_escape(model)}\n",
            f'developer_instructions = """\n{escaped}\n"""\n',
        ]
    )
    return "".join(lines)


def _render_agents_config_file_blocks(agents_dir: Path) -> str:
    """Generate ``[agents."<name>"] config_file = ...`` TOML blocks.

    Replaces the inline agent block rendering.  For each canonical agent
    (determined by the ``.md`` file listing) a two-line TOML block is emitted:

    .. code-block:: toml

        [agents."<name>"]
        config_file = "agents/<name>.toml"

    Agents whose ``.md`` cannot be parsed (missing ``name``) are skipped.
    """
    if not agents_dir.exists():
        return ""
    blocks: list[str] = []
    for md_file in sorted(agents_dir.glob("*.md")):
        try:
            text = md_file.read_text(encoding="utf-8")
            fm = _parse_agent_frontmatter(text)
            if not fm:
                continue
            name = str(fm.get("name", ""))
            if not name:
                continue
            key_escaped = name.replace("\\", "\\\\").replace('"', '\\"')
            blocks.append(f'[agents."{key_escaped}"]\n')
            blocks.append(f'config_file = "agents/{name}.toml"\n')
        except (OSError, ValueError):
            continue
    return "".join(blocks)


def _render_agent_toml_block(name: str, fm: dict[str, object]) -> str:
    """Render a ``[agents."<name>"]`` TOML table block from parsed frontmatter *fm*.

    Keys are always quoted for safety (required for hyphenated names like
    ``software-engineer``). Missing or None fields are omitted. The ``tools``
    field, if present, is emitted as a TOML array of basic strings.

    Names containing ``]`` or newline characters are rejected (cannot appear
    safely inside a TOML table header, even with quoting). Double-quotes and
    backslashes are escaped with a leading backslash so the header is valid
    TOML (e.g. a name like ``a"b`` becomes ``[agents."a\\"b"]``).
    """
    if "]" in name:
        raise ValueError(f"Agent name contains invalid character ']': {name!r}")
    if "\n" in name:
        raise ValueError(f"Agent name contains newline character: {name!r}")
    # Escape backslash first (must precede quote escape to avoid double-escaping)
    key_escaped = name.replace("\\", "\\\\").replace('"', '\\"')
    lines: list[str] = [f'[agents."{key_escaped}"]\n']
    for field in ("name", "description", "model"):
        val = fm.get(field)
        if val is None:
            continue
        lines.append(f"{field} = {_toml_escape(val)}\n")
    tools_val = fm.get("tools")
    if tools_val is not None and isinstance(tools_val, list):
        items = ", ".join(_toml_escape(t) for t in tools_val)
        lines.append(f"tools = [{items}]\n")
    return "".join(lines)


def _parse_agent_frontmatter(text: str) -> dict[str, object]:
    """Parse YAML frontmatter from an agent .md file using stdlib regex only.

    Extracts the block between the first pair of ``---`` fences. Supports:
    - Simple ``key: value`` scalar fields (string values).
    - Folded scalar ``key: >`` — continuation lines are joined with a space.
    - YAML list under ``tools:`` — items prefixed with ``  - `` (two-space indent).

    Unknown fields (outside ``_TOML_SAFE_AGENT_FIELDS``) are silently dropped.
    Returns an empty dict if ``name`` is missing or frontmatter is absent.
    """
    if not text.startswith("---\n"):
        return {}
    end_idx = text.find("\n---\n", 4)
    if end_idx == -1:
        return {}
    frontmatter = text[4 : end_idx + 1]

    result: dict[str, object] = {}
    lines = frontmatter.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        # Detect block scalar (folded `>` or literal `|`)
        block_m = _AGENT_FM_BLOCK_SCALAR_RE.match(line)
        if block_m:
            key = block_m.group(1)
            # Collect continuation lines (indented)
            body_lines: list[str] = []
            i += 1
            while i < len(lines) and (lines[i].startswith("  ") or lines[i] == ""):
                body_lines.append(lines[i].strip())
                i += 1
            # Join non-empty continuation lines with a space (folded scalar semantics)
            value = " ".join(part for part in body_lines if part)
            if key in _TOML_SAFE_AGENT_FIELDS:
                result[key] = value
            continue

        # Detect tools list  (`tools:\n  - item\n  - item`)
        if line == "tools:":
            items: list[str] = []
            i += 1
            while i < len(lines) and _AGENT_FM_TOOLS_ITEM_RE.match(lines[i]):
                m = _AGENT_FM_TOOLS_ITEM_RE.match(lines[i])
                if m:
                    items.append(m.group(1).strip())
                i += 1
            if "tools" in _TOML_SAFE_AGENT_FIELDS:
                result["tools"] = items
            continue

        # Simple scalar
        simple_m = _AGENT_FM_SIMPLE_RE.match(line)
        if simple_m:
            key = simple_m.group(1)
            value_str = simple_m.group(2).strip()
            if key in _TOML_SAFE_AGENT_FIELDS:
                result[key] = value_str
        i += 1

    # Require `name` — without it, the block cannot be rendered
    if "name" not in result:
        return {}
    return result


def _atomic_write_text(dst: Path, content: str) -> None:
    """Write *content* to *dst* atomically via a sibling .tmp file + os.replace().

    Guarantees the destination either contains the full new content or is
    unchanged — prevents readers from observing a partially-written file.
    """
    tmp = dst.with_suffix(dst.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
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


def _strip_tools_from_frontmatter(content: str) -> str:
    """Strip the `tools` array from YAML frontmatter for OpenCode compatibility."""
    if not content.startswith("---\n"):
        return content
    end_idx = content.find("\n---\n", 4)
    if end_idx == -1:
        return content
    frontmatter = content[4 : end_idx + 1]
    cleaned = _FRONTMATTER_TOOLS_RE.sub("", frontmatter)
    return f"---\n{cleaned}---\n{content[end_idx + 5 :]}"


def _prepare_agent_for_opencode(content: str) -> str:
    """Prepare an agent .md file for the OpenCode projection.

    - Strips the `tools` array (OpenCode v1.14+ incompatibility with list form)
    - If `opencode_model:` is declared, swaps the `model:` value and removes the field
    """
    if not content.startswith("---\n"):
        return content
    end_idx = content.find("\n---\n", 4)
    if end_idx == -1:
        return content
    frontmatter = content[4 : end_idx + 1]
    body = content[end_idx + 5 :]

    m = _FRONTMATTER_OPENCODE_MODEL_RE.search(frontmatter)
    if m:
        opencode_model = m.group(1).strip()
        frontmatter = _FRONTMATTER_MODEL_VALUE_RE.sub(
            lambda match: f"{match.group(1)}{opencode_model}", frontmatter, count=1
        )
    frontmatter = _FRONTMATTER_TOOLS_RE.sub("", frontmatter)
    frontmatter = _FRONTMATTER_OPENCODE_MODEL_FIELD_RE.sub("", frontmatter)
    return f"---\n{frontmatter}---\n{body}"


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

    Compares ``package_version`` in the consumer's manifest against the
    currently installed package version.  A match means the consumer IS the
    dadaia-workspace source tree — we must never overwrite its source files.
    """
    manifest_path = consumer / ".dadaia" / "agentic" / "manifest.json"
    if not manifest_path.exists():
        return False
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        consumer_version = manifest.get("package_version", "")
        return bool(consumer_version and consumer_version == _package_version())
    except (json.JSONDecodeError, OSError):
        return False


def _install_workspace_guardrail_pair(
    source: Path,
    workspace_root: Path,
    force: bool,
    installed: list[str] | None = None,
) -> None:
    """Fan ``source`` (``data/AGENTS.md``) out to workspace root + all consumer repos.

    Projection targets per call (Option C, ADR):
    1. ``workspace_root / "AGENTS.md"``
    2. ``workspace_root / "CLAUDE.md"``
    3. ``<consumer> / "AGENTS.md"`` — for each marker-bearing consumer (R13)
    4. ``<consumer> / "CLAUDE.md"`` — same consumer

    Self-skip (R14): if a consumer's manifest ``package_version`` matches our
    own, that consumer is the dadaia-workspace source repo — skip both files
    to avoid overwriting the source.

    Marker-less repos under ``repos/`` emit ``[skip]`` to stderr and are never
    written.  The function never raises on missing/unexpected paths.

    Args:
        source: Absolute path to ``data/AGENTS.md`` (the single source of truth).
        workspace_root: Workspace root directory.
        force: When True, overwrite existing files; when False, skip if present.
        installed: Optional list mutated with ``"[ok]   <path>"`` strings.
    """
    if installed is None:
        installed = []

    # Read source bytes once; compute SHA-256 for integrity tracking.
    source_bytes = source.read_bytes()
    _src_sha = hashlib.sha256(source_bytes).hexdigest()  # available for callers

    def _write_pair(target_dir: Path) -> None:
        # AGENTS.md — full canonical content copied from source.
        agents_dst = target_dir / "AGENTS.md"
        agents_dst.parent.mkdir(parents=True, exist_ok=True)
        if agents_dst.exists() and not force:
            installed.append(f"[skip] {agents_dst}")
        else:
            shutil.copy2(source, agents_dst)
            installed.append(f"[ok]   {agents_dst}")
        # CLAUDE.md — 1-line stub only (T-41: delegates to AGENTS.md).
        claude_dst = target_dir / "CLAUDE.md"
        claude_dst.parent.mkdir(parents=True, exist_ok=True)
        if claude_dst.exists() and not force:
            installed.append(f"[skip] {claude_dst}")
        else:
            _atomic_write_text(claude_dst, _CLAUDE_MD_STUB)
            installed.append(f"[ok]   {claude_dst}")

    # Workspace-root write set (always).
    _write_pair(workspace_root)

    # Consumer-repo enumeration (R13).
    for consumer in _consumer_repos_for_root(workspace_root):
        if _is_self_repo(consumer):
            v = _package_version()
            sys.stderr.write(
                f"[skip] {consumer / 'AGENTS.md'} (self-projection — package_version={v})\n"
            )
            continue
        _write_pair(consumer)


def _install_workspace_root_guardrail_pair(
    source: Path,
    workspace_root: Path,
    force: bool,
    installed: list[str] | None = None,
) -> None:
    """Write the guardrail pair to *workspace_root* only (no consumer repos).

    Variant of ``_install_workspace_guardrail_pair`` that skips the consumer-repo
    enumeration.  Used when ``scope="workspace-only"`` is passed to
    ``FileSystemPublicAssetManager.install()``.

    Args:
        source: Absolute path to ``data/AGENTS.md`` (the single source of truth).
        workspace_root: Workspace root directory.
        force: When True, overwrite existing files; when False, skip if present.
        installed: Optional list mutated with ``"[ok]   <path>"`` strings.
    """
    if installed is None:
        installed = []

    agents_dst = workspace_root / "AGENTS.md"
    agents_dst.parent.mkdir(parents=True, exist_ok=True)
    if agents_dst.exists() and not force:
        installed.append(f"[skip] {agents_dst}")
    else:
        shutil.copy2(source, agents_dst)
        installed.append(f"[ok]   {agents_dst}")

    claude_dst = workspace_root / "CLAUDE.md"
    claude_dst.parent.mkdir(parents=True, exist_ok=True)
    if claude_dst.exists() and not force:
        installed.append(f"[skip] {claude_dst}")
    else:
        _atomic_write_text(claude_dst, _CLAUDE_MD_STUB)
        installed.append(f"[ok]   {claude_dst}")


def _install_consumer_repos_guardrail_pair(
    source: Path,
    workspace_root: Path,
    force: bool,
    installed: list[str] | None = None,
) -> None:
    """Write the guardrail pair to each marker-bearing consumer repo only.

    Skips the workspace-root write.  Used when ``scope="repos-only"`` is passed
    to ``FileSystemPublicAssetManager.install()``.

    Self-skip (R14): if a consumer's manifest ``package_version`` matches our
    own, that consumer is the dadaia-workspace source repo — skip it.

    Args:
        source: Absolute path to ``data/AGENTS.md`` (the single source of truth).
        workspace_root: Workspace root directory.
        force: When True, overwrite existing files; when False, skip if present.
        installed: Optional list mutated with ``"[ok]   <path>"`` strings.
    """
    if installed is None:
        installed = []

    for consumer in _consumer_repos_for_root(workspace_root):
        if _is_self_repo(consumer):
            v = _package_version()
            sys.stderr.write(
                f"[skip] {consumer / 'AGENTS.md'} (self-projection — package_version={v})\n"
            )
            continue

        agents_dst = consumer / "AGENTS.md"
        agents_dst.parent.mkdir(parents=True, exist_ok=True)
        if agents_dst.exists() and not force:
            installed.append(f"[skip] {agents_dst}")
        else:
            shutil.copy2(source, agents_dst)
            installed.append(f"[ok]   {agents_dst}")

        claude_dst = consumer / "CLAUDE.md"
        claude_dst.parent.mkdir(parents=True, exist_ok=True)
        if claude_dst.exists() and not force:
            installed.append(f"[skip] {claude_dst}")
        else:
            _atomic_write_text(claude_dst, _CLAUDE_MD_STUB)
            installed.append(f"[ok]   {claude_dst}")


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


class FileSystemPublicAssetManager:
    def __init__(self) -> None:
        self._public_dir = Path(__file__).parent.parent / "public"

    def stage(self, workspace_root: Path) -> list[str]:
        if not self._public_dir.exists():
            raise PublicAssetError(f"Public assets directory not found: {self._public_dir}")

        agentic_dir = workspace_root / ".dadaia" / "agentic"
        if agentic_dir.exists():
            shutil.rmtree(agentic_dir)
        agentic_dir.mkdir(parents=True, exist_ok=True)

        staged: list[str] = []
        for name in _COPY_DIRS:
            src = self._public_dir / name
            if not src.exists():
                continue
            dst = agentic_dir / name
            if src.is_dir():
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
            staged.append(f"[stage] {dst}")

        self._validate_workflows(agentic_dir)

        manifest_path = agentic_dir / "manifest.json"
        manifest_path.write_text(_json_dump(self._build_manifest(agentic_dir)), encoding="utf-8")
        staged.append(f"[stage] {manifest_path}")
        return staged

    def _validate_workflows(self, agentic_dir: Path) -> None:
        """Validate every *.workflow.md against schema; abort stage if any fails."""
        workflows_dir = agentic_dir / "workflows"
        if not workflows_dir.exists():
            return
        from dadaia_workspace.core.exceptions import WorkflowSchemaError
        from dadaia_workspace.infrastructure.markdown_workflow_store import (
            MarkdownWorkflowStore,
        )

        agent_catalog: list[str] = sorted(p.stem for p in (agentic_dir / "agents").glob("*.md"))
        store = MarkdownWorkflowStore(workflows_dir, agent_catalog=agent_catalog or None)
        try:
            store.list()
        except WorkflowSchemaError as e:
            raise PublicAssetError(
                "workflow schema validation failed during `dadaia public stage`: "
                f"{e}. Fix the offending workflow file in public/workflows/ and rerun."
            ) from e

    def install(
        self,
        workspace_root: Path,
        target: str = "all",
        force: bool = False,
        scope: Literal["all", "repos-only", "workspace-only"] = "all",
    ) -> list[str]:
        if target not in _VALID_TARGETS:
            valid = ", ".join(sorted(_VALID_TARGETS))
            raise PublicAssetError(
                f"Unsupported public install target '{target}'. Expected one of: {valid}"
            )

        agentic_dir = workspace_root / ".dadaia" / "agentic"
        installed: list[str] = []
        if not (agentic_dir / "manifest.json").exists():
            installed.extend(self.stage(workspace_root))

        targets = ("agents", "claude", "codex", "opencode") if target == "all" else (target,)
        data_agents_md = agentic_dir / "data" / "AGENTS.md"
        if data_agents_md.exists():
            # Option C (ADR): scope-aware fan-out to workspace-root pair and/or
            # marker-bearing consumer repos.
            if scope == "all":
                # Full fan-out: workspace-root pair + all consumer repos.
                _install_workspace_guardrail_pair(data_agents_md, workspace_root, force, installed)
            elif scope == "workspace-only":
                # Workspace-root guardrail pair only — skip consumer repos.
                _install_workspace_root_guardrail_pair(
                    data_agents_md, workspace_root, force, installed
                )
            elif scope == "repos-only":
                # Consumer repos only — skip workspace-root pair.
                _install_consumer_repos_guardrail_pair(
                    data_agents_md, workspace_root, force, installed
                )
        else:
            # Legacy / scaffold path: templates/AGENTS.md → workspace-root only.
            if scope in ("all", "workspace-only"):
                self._install_agents_md(agentic_dir, workspace_root, force, installed)
        self._install_reports_agents_md(agentic_dir, workspace_root, force, installed)

        for item in targets:
            if item == "agents":
                self._install_universal_skills(agentic_dir, workspace_root, force, installed)
            elif item == "claude":
                self._install_claude(agentic_dir, workspace_root, force, installed)
            elif item == "codex":
                self._install_codex(agentic_dir, workspace_root, force, installed)
            elif item == "opencode":
                self._install_opencode(agentic_dir, workspace_root, force, installed)

        if target in {"all", "claude", "codex"}:
            self._install_scripts(agentic_dir, workspace_root, force, installed)

        return installed

    def doctor(self, workspace_root: Path) -> list[str]:
        if not self._public_dir.exists():
            raise PublicAssetError(f"Public assets directory not found: {self._public_dir}")

        agentic_dir = workspace_root / ".dadaia" / "agentic"
        reports: list[str] = []

        for src in self._iter_files(self._public_dir):
            rel = src.relative_to(self._public_dir)
            reports.append(self._compare(src, agentic_dir / rel, f"stage:{rel.as_posix()}"))

        if not (agentic_dir / "manifest.json").exists():
            reports.append("[missing] stage:manifest.json")

        for expected_src, dst, label, transform in self._runtime_expectations(
            agentic_dir, workspace_root
        ):
            if expected_src is None and transform:
                # T-41: CLAUDE.md is a 1-line stub — verify content matches stub exactly.
                reports.append(self._compare_content(_CLAUDE_MD_STUB, dst, label))
            elif expected_src is None:
                reports.append(f"[unsupported] {label}")
            elif transform:
                content = _prepare_agent_for_opencode(expected_src.read_text(encoding="utf-8"))
                reports.append(self._compare_content(content, dst, label))
            else:
                reports.append(self._compare(expected_src, dst, label))

        reports.append(
            self._compare_content(
                _json_dump(self._claude_settings(workspace_root)),
                workspace_root / ".claude" / "settings.json",
                "claude:settings.json",
            )
        )
        reports.append(
            self._compare_content(
                _json_dump(self._codex_hooks(workspace_root)),
                workspace_root / ".codex" / "hooks.json",
                "codex:hooks.json",
            )
        )
        reports.append(
            self._compare_content(
                self._codex_config(agentic_dir),
                workspace_root / ".codex" / "config.toml",
                "codex:config.toml",
            )
        )
        reports.append(
            self._compare_content(
                _json_dump(self._opencode_config(workspace_root)),
                workspace_root / "opencode.json",
                "opencode:opencode.json",
            )
        )

        reports.extend(self._classify_workflows(agentic_dir))
        reports.extend(self._lint_legacy_software_engineer())
        reports.extend(self._check_codex_drift(agentic_dir, workspace_root))

        return reports

    # ------------------------------------------------------------------
    # Codex drift checks (D-CX-1 … D-CX-5)
    # ------------------------------------------------------------------

    # Matches the bare identifier `claude-` only when it is NOT immediately
    # preceded by an alphanumeric character, hyphen, or underscore.  This
    # avoids false positives inside words like `config_claude_sonnet` while
    # still catching standalone references such as `claude-sonnet-4-6`.
    _CODEX_CLAUDE_RE: re.Pattern[str] = re.compile(
        r"(?:^|[^a-zA-Z0-9_-])claude-", re.MULTILINE
    )
    # File extensions considered "text" for D-CX-4 scanning.
    _CODEX_TEXT_SUFFIXES: frozenset[str] = frozenset({".toml", ".md", ".json", ".txt", ".yaml", ".yml"})

    def _check_codex_drift(self, agentic_dir: Path, workspace_root: Path) -> list[str]:
        """Run codex-parity drift checks D-CX-1 through D-CX-6.

        Returns a list of ``[missing]``, ``[extra]``, ``[error]``, ``[leak]``,
        or ``[drift]`` report strings.  An empty list means no drift was
        detected.  The caller extends the main doctor report with these strings
        so that ``any(r.startswith(("[missing", "[extra", "[error", "[leak",
        "[drift")) for r in reports)`` reliably signals a non-zero exit.
        """
        codex_dir = workspace_root / ".codex"
        out: list[str] = []
        out.extend(self._dcx1_missing_toml(agentic_dir, codex_dir))
        out.extend(self._dcx2_config_toml_entries(agentic_dir, codex_dir))
        out.extend(self._dcx3_workflow_drift(agentic_dir, codex_dir))
        out.extend(self._dcx4_claude_strings(codex_dir))
        out.extend(self._dcx5_empty_developer_instructions(codex_dir))
        out.extend(self._dcx6_codex_runtime_adapters(workspace_root))
        return out

    def _dcx1_missing_toml(self, agentic_dir: Path, codex_dir: Path) -> list[str]:
        """D-CX-1: every canonical agent .md must have a matching TOML in .codex/agents/.

        For each ``<agent-name>.md`` in the agentic agents directory the
        corresponding ``.codex/agents/<agent-name>.toml`` must exist.  Uses
        ``_parse_agent_frontmatter()`` to extract the canonical ``name`` field;
        agents whose frontmatter lacks ``name`` are skipped (defensive — they
        are already flagged by other checks).
        """
        agents_src = agentic_dir / "agents"
        codex_agents = codex_dir / "agents"
        out: list[str] = []
        if not agents_src.exists():
            return out
        for md_file in sorted(agents_src.glob("*.md")):
            try:
                text = md_file.read_text(encoding="utf-8")
            except OSError:
                continue
            fm = _parse_agent_frontmatter(text)
            name = str(fm.get("name", "")) if fm else ""
            if not name:
                # Use stem as fallback for the report label so the operator
                # can locate the offending file even without a valid name.
                name = md_file.stem
            toml_path = codex_agents / f"{name}.toml"
            if not toml_path.exists():
                out.append(f"[missing] codex:agents/{name}.toml (D-CX-1)")
        return out

    def _dcx2_config_toml_entries(self, agentic_dir: Path, codex_dir: Path) -> list[str]:
        """D-CX-2: every .codex/agents/*.toml must have a config_file entry in config.toml.

        Reads ``.codex/config.toml`` as plain text and checks for the literal
        string ``config_file = "agents/<name>.toml"`` for each TOML found in
        ``.codex/agents/``.  Plain-text matching avoids parsing the full TOML
        table structure (which is complex given quoted-key headers).
        """
        codex_agents = codex_dir / "agents"
        config_toml = codex_dir / "config.toml"
        out: list[str] = []
        if not codex_agents.exists():
            return out
        config_text = ""
        if config_toml.exists():
            with contextlib.suppress(OSError):
                config_text = config_toml.read_text(encoding="utf-8")
        for toml_file in sorted(codex_agents.glob("*.toml")):
            name = toml_file.stem
            needle = f'config_file = "agents/{name}.toml"'
            if needle not in config_text:
                out.append(f"[missing] codex:config.toml entry for {name} (D-CX-2)")
        return out

    def _dcx3_workflow_drift(self, agentic_dir: Path, codex_dir: Path) -> list[str]:
        """D-CX-3: .codex/workflows/ must mirror the canonical workflow set exactly.

        Compares file names (not content) between the agentic canonical
        workflows directory and ``.codex/workflows/``.  Both missing files
        (canonical present, codex absent) and extra files (codex present,
        canonical absent) are reported as drift.
        """
        canonical_dir = agentic_dir / "workflows"
        codex_wf = codex_dir / "workflows"
        out: list[str] = []

        canonical_names: set[str] = set()
        if canonical_dir.exists():
            canonical_names = {f.name for f in canonical_dir.glob("*.workflow.md")}

        codex_names: set[str] = set()
        if codex_wf.exists():
            codex_names = {f.name for f in codex_wf.glob("*.workflow.md")}

        for name in sorted(canonical_names - codex_names):
            out.append(f"[missing] codex:workflows/{name} (D-CX-3)")
        for name in sorted(codex_names - canonical_names):
            out.append(f"[extra] codex:workflows/{name} (D-CX-3)")
        return out

    def _dcx4_claude_strings(self, codex_dir: Path) -> list[str]:
        """D-CX-4: no file inside .codex/ may contain the bare string ``claude-``.

        Scans all text files (by extension) under ``.codex/`` recursively.
        Any match of the pattern ``(?:^|[^a-zA-Z0-9_-])claude-`` is reported.
        Binary files and non-text extensions are skipped to avoid false
        positives from compiled artifacts.
        """
        out: list[str] = []
        if not codex_dir.exists():
            return out
        for path in sorted(codex_dir.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix not in self._CODEX_TEXT_SUFFIXES:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if self._CODEX_CLAUDE_RE.search(text):
                rel = path.relative_to(codex_dir).as_posix()
                out.append(f"[error] codex:claude-string in {rel} (D-CX-4)")
        return out

    def _dcx5_empty_developer_instructions(self, codex_dir: Path) -> list[str]:
        """D-CX-5: every .codex/agents/*.toml must have a non-empty developer_instructions.

        Parses each TOML file via ``tomllib.loads()`` (stdlib, Python 3.11+)
        and checks that ``developer_instructions`` is present and non-empty
        after stripping leading/trailing whitespace.
        """
        codex_agents = codex_dir / "agents"
        out: list[str] = []
        if not codex_agents.exists():
            return out
        for toml_file in sorted(codex_agents.glob("*.toml")):
            name = toml_file.stem
            try:
                text = toml_file.read_text(encoding="utf-8")
                data = tomllib.loads(text)
            except (OSError, tomllib.TOMLDecodeError):
                out.append(f"[error] codex:{name}.toml: unparseable TOML (D-CX-5)")
                continue
            instructions = data.get("developer_instructions", "")
            if not isinstance(instructions, str) or not instructions.strip():
                out.append(
                    f"[error] codex:{name}.toml: developer_instructions is empty (D-CX-5)"
                )
        return out

    def _dcx6_codex_runtime_adapters(self, workspace_root: Path) -> list[str]:
        """D-CX-6: public/runtime/codex/ adapters — leak, missing, drift checks.

        For each <slug>/SKILL.md in public/runtime/codex/:
        - [leak] if the file appears in .claude/skills/<slug>/SKILL.md
        - [leak] if the file appears in .opencode/skills/<slug>/SKILL.md
        - [missing] if .codex/skills/<slug>/SKILL.md does not exist
        - [drift] if .codex/skills/<slug>/SKILL.md content differs from source
        """
        src_root = self._public_dir / "runtime" / "codex"
        out: list[str] = []
        if not src_root.exists():
            return out
        codex_skills = workspace_root / ".codex" / "skills"
        claude_skills = workspace_root / ".claude" / "skills"
        opencode_skills = workspace_root / ".opencode" / "skills"
        for slug_dir in sorted(src_root.iterdir()):
            if not slug_dir.is_dir():
                continue
            skill_src = slug_dir / "SKILL.md"
            if not skill_src.exists():
                continue
            slug = slug_dir.name
            src_text = skill_src.read_text(encoding="utf-8")
            # Leak checks
            for leak_root, label in [(claude_skills, "claude"), (opencode_skills, "opencode")]:
                leak_path = leak_root / slug / "SKILL.md"
                if leak_path.exists():
                    out.append(
                        f"[leak] {label}:skills/{slug}/SKILL.md"
                        " — Codex-only adapter must not appear here (D-CX-6)"
                    )
            # Missing / drift
            installed = codex_skills / slug / "SKILL.md"
            if not installed.exists():
                out.append(f"[missing] codex:skills/{slug}/SKILL.md (D-CX-6)")
            elif installed.read_text(encoding="utf-8") != src_text:
                out.append(f"[drift] codex:skills/{slug}/SKILL.md (D-CX-6)")
        return out

    def _lint_legacy_software_engineer(self) -> list[str]:
        """T-35: reject the legacy `software-engineer` subagent alias in public/.

        The alias was split into `software-engineer-python` and
        `software-engineer-node`. Any reintroduction is a regression.
        """
        out: list[str] = []
        if not self._public_dir.exists():
            return out
        for path in self._iter_files(self._public_dir):
            # Skip non-textual / binary candidates.
            if path.suffix not in {".md", ".yaml", ".yml", ".json", ".toml", ".txt"}:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if _LEGACY_SE_ALIAS_RE.search(text):
                rel = path.relative_to(self._public_dir).as_posix()
                out.append(
                    f"[LINT] Legacy alias 'software-engineer' in {rel}. "
                    "Use 'software-engineer-python' or 'software-engineer-node'."
                )
        return out

    def _classify_workflows(self, agentic_dir: Path) -> list[str]:
        out: list[str] = []
        workflows_dir = agentic_dir / "workflows"
        if not workflows_dir.exists():
            return out
        for wf in sorted(workflows_dir.glob("*.workflow.md")):
            text = wf.read_text(encoding="utf-8")
            has_parallel = bool(_FRONTMATTER_PARALLEL_GROUP_RE.search(text))
            tag = f"workflows/{wf.name}"
            if has_parallel:
                out.append(f"[partial] opencode:{tag} (parallel_group sequentially)")
            else:
                out.append(f"[ok] opencode:{tag}")
            out.append(f"[not-applicable] codex:{tag} (no workflow runtime)")
            out.append(f"[ok] claude:{tag}")
        return out

    def _build_manifest(self, agentic_dir: Path) -> dict[str, object]:
        assets: list[dict[str, str]] = []
        for path in self._iter_files(agentic_dir):
            if path.name == "manifest.json":
                continue
            rel = path.relative_to(agentic_dir).as_posix()
            assets.append({"path": rel, "sha256": _sha256(path), "type": rel.split("/", 1)[0]})

        return {
            "schema_version": _SCHEMA_VERSION,
            "package_version": _package_version(),
            "generated_at": datetime.now(tz=UTC).isoformat(),
            "assets": assets,
        }

    def _install_agents_md(
        self, agentic_dir: Path, workspace_root: Path, force: bool, installed: list[str]
    ) -> None:
        src = self._agents_md_source(agentic_dir)
        if src is not None:
            self._copy_file(src, workspace_root / "AGENTS.md", force, installed)

    def _install_reports_agents_md(
        self, agentic_dir: Path, workspace_root: Path, force: bool, installed: list[str]
    ) -> None:
        src = agentic_dir / "data" / "reports-AGENTS.md"
        if src.exists():
            reports_dir = workspace_root / ".dadaia" / "reports"
            reports_dir.mkdir(parents=True, exist_ok=True)
            self._copy_file(src, reports_dir / "AGENTS.md", force, installed)

    def _install_universal_skills(
        self, agentic_dir: Path, workspace_root: Path, force: bool, installed: list[str]
    ) -> None:
        self._copy_tree(
            agentic_dir / "skills", workspace_root / ".agents" / "skills", force, installed
        )
        self._copy_tree(
            agentic_dir / "workflows",
            workspace_root / ".agents" / "workflows",
            force,
            installed,
        )

    def _install_claude(
        self, agentic_dir: Path, workspace_root: Path, force: bool, installed: list[str]
    ) -> None:
        claude_dir = workspace_root / ".claude"
        for name in _CLAUDE_DIRS:
            self._copy_tree(agentic_dir / name, claude_dir / name, force, installed)

        settings_path = claude_dir / "settings.json"
        if settings_path.exists() and not force:
            installed.append(f"[skip] {settings_path}")
        else:
            self._write_generated(
                settings_path, _json_dump(self._claude_settings(workspace_root)), True, installed
            )

    def _install_codex(
        self, agentic_dir: Path, workspace_root: Path, force: bool, installed: list[str]
    ) -> None:
        codex_dir = workspace_root / ".codex"
        self._install_codex_rules(agentic_dir, workspace_root, force, installed)
        self._install_codex_workflows(agentic_dir, workspace_root, force, installed)
        self._install_universal_skills(agentic_dir, workspace_root, force, installed)
        self._install_codex_agents(agentic_dir, workspace_root, force, installed)
        self._install_codex_runtime_adapters(workspace_root, force, installed)
        self._write_generated(
            codex_dir / "hooks.json",
            _json_dump(self._codex_hooks(workspace_root)),
            force,
            installed,
        )
        self._write_generated(
            codex_dir / "config.toml",
            self._codex_config(agentic_dir),
            force,
            installed,
        )

    def _install_codex_rules(
        self, agentic_dir: Path, workspace_root: Path, force: bool, installed: list[str]
    ) -> None:
        """Copy only executable rules (those with YAML frontmatter) to .codex/rules/.

        Behavioral prose rules (ADR-1/D2) — i.e. files without frontmatter — are
        excluded from the Codex projection.  This prevents rules like
        ``game-agents-coordination.md`` and ``game-developer-scope.md`` from
        polluting the Codex rule surface.
        """
        src_dir = agentic_dir / "rules"
        dst_dir = workspace_root / ".codex" / "rules"
        if not src_dir.exists():
            return
        dst_dir.mkdir(parents=True, exist_ok=True)
        for src in sorted(src_dir.glob("*.md")):
            try:
                text = src.read_text(encoding="utf-8")
            except OSError:
                continue
            # Only project rules that start with YAML frontmatter (executable rules).
            if not text.startswith("---\n"):
                installed.append(f"[skip-behavioral] {src.name}")
                continue
            dst = dst_dir / src.name
            self._copy_file(src, dst, force, installed)

    def _install_codex_workflows(
        self, agentic_dir: Path, workspace_root: Path, force: bool, installed: list[str]
    ) -> None:
        """Project all canonical workflows to .codex/workflows/.

        FR9/ADR-4: the Codex runtime receives the full canonical workflow set so
        that operators can reference them.  Previously the workflows directory was
        removed; that behaviour is replaced by this projection.
        """
        self._copy_tree(
            agentic_dir / "workflows",
            workspace_root / ".codex" / "workflows",
            force,
            installed,
        )

    def _install_codex_agents(
        self, agentic_dir: Path, workspace_root: Path, force: bool, installed: list[str]
    ) -> None:
        """Generate .codex/agents/<agent-id>.toml for each canonical agent.

        For each ``.md`` file in ``agentic_dir/agents/``:
        1. Parse frontmatter to extract ``name`` and ``model``.
        2. Extract the body (everything after the second ``---`` fence).
        3. Pass the body through ``transform_for_codex()`` to replace Claude-
           specific references.
        4. Map the model via ``map_model()`` (raises ``ValueError`` on unknown
           identifier — fail loudly rather than emit ``claude-*`` strings).
        5. Serialize as TOML via ``_render_codex_agent_toml()``.
        6. Write to ``.codex/agents/<name>.toml``.

        Files are skipped (not overwritten) when ``force=False`` and the TOML
        already exists.
        """
        from dadaia_workspace.infrastructure.runtime_transforms.codex import (
            transform_for_codex,
        )
        from dadaia_workspace.infrastructure.runtime_transforms.model_mapping import (
            map_model,
        )

        agents_src = agentic_dir / "agents"
        agents_dst = workspace_root / ".codex" / "agents"
        agents_dst.mkdir(parents=True, exist_ok=True)

        for md_file in sorted(agents_src.glob("*.md")):
            text = md_file.read_text(encoding="utf-8")
            fm = _parse_agent_frontmatter(text)
            if not fm:
                continue
            agent_name = str(fm.get("name", ""))
            if not agent_name:
                continue

            # Extract body: text after the second '---' fence.
            if text.startswith("---\n"):
                end_idx = text.find("\n---\n", 4)
                body = text[end_idx + 5:] if end_idx != -1 else text
            else:
                body = text

            # Transform for Codex runtime.
            body = transform_for_codex(body, agent_name)

            # Map model — raises ValueError on unknown Claude identifier.
            claude_model = str(fm.get("model", "claude-sonnet-4-6"))
            codex_model = map_model(claude_model)

            description = fm.get("description")
            toml_content = _render_codex_agent_toml(
                agent_name,
                codex_model,
                body,
                description=str(description) if description else None,
            )

            dst = agents_dst / f"{agent_name}.toml"
            if dst.exists() and not force:
                installed.append(f"[skip] {dst}")
            else:
                dst.write_text(toml_content, encoding="utf-8")
                installed.append(f"[ok]   {dst}")

    def _install_codex_runtime_adapters(
        self, workspace_root: Path, force: bool, installed: list[str]
    ) -> None:
        """Copy Codex-only adapter SKILL.md files from public/runtime/codex/ to .codex/skills/.

        ADR-CX-001: source is public/runtime/codex/<slug>/SKILL.md.
        ADR-CX-003: these files must NOT appear in .claude/ or .opencode/.
        """
        src_root = self._public_dir / "runtime" / "codex"
        if not src_root.exists():
            return
        dst_root = workspace_root / ".codex" / "skills"
        dst_root.mkdir(parents=True, exist_ok=True)
        for slug_dir in sorted(src_root.iterdir()):
            if not slug_dir.is_dir():
                continue
            skill_src = slug_dir / "SKILL.md"
            if not skill_src.exists():
                continue
            skill_dst = dst_root / slug_dir.name / "SKILL.md"
            skill_dst.parent.mkdir(parents=True, exist_ok=True)
            self._copy_file(skill_src, skill_dst, force, installed)

    def _install_opencode(
        self, agentic_dir: Path, workspace_root: Path, force: bool, installed: list[str]
    ) -> None:
        opencode_dir = workspace_root / ".opencode"
        for name in _OPENCODE_DIRS:
            if name == "agents":
                self._copy_agents_for_opencode(
                    agentic_dir / name, opencode_dir / name, force, installed
                )
            else:
                self._copy_tree(agentic_dir / name, opencode_dir / name, force, installed)
        self._write_generated(
            workspace_root / "opencode.json",
            _json_dump(self._opencode_config(workspace_root)),
            force,
            installed,
        )

    def _copy_agents_for_opencode(
        self, src_dir: Path, dst_dir: Path, force: bool, installed: list[str]
    ) -> None:
        """Copy agent .md files stripping the `tools` array from frontmatter."""
        if not src_dir.exists():
            return
        for src in self._iter_files(src_dir):
            dst = dst_dir / src.relative_to(src_dir)
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists() and not force:
                installed.append(f"[skip] {dst}")
                continue
            content = _prepare_agent_for_opencode(src.read_text(encoding="utf-8"))
            dst.write_text(content, encoding="utf-8")
            installed.append(f"[ok]   {dst}")

    def _install_scripts(
        self, agentic_dir: Path, workspace_root: Path, force: bool, installed: list[str]
    ) -> None:
        self._copy_tree(
            agentic_dir / "scripts", workspace_root / ".dadaia" / "scripts", force, installed
        )
        scripts_dir = workspace_root / ".dadaia" / "scripts"
        if scripts_dir.exists():
            for script in scripts_dir.glob("*.sh"):
                script.chmod(0o755)

    def _runtime_expectations(
        self, agentic_dir: Path, workspace_root: Path
    ) -> Iterable[tuple[Path | None, Path, str, bool]]:
        """Yield (src, dst, label, transform) tuples for doctor comparison.

        transform=True means dst was produced by _strip_tools_from_frontmatter(src)
        and must be compared by content rather than by SHA256 of the original src.
        """
        agents_md = self._agents_md_source(agentic_dir)
        if agents_md is not None:
            yield (agents_md, workspace_root / "AGENTS.md", "root:AGENTS.md", False)
            # T-41: CLAUDE.md is a 1-line stub — use "stub" sentinel to trigger content check.
            yield (None, workspace_root / "CLAUDE.md", "root:CLAUDE.md", True)
            # Consumer-repo parity (R13 + R14): one pair per marker-bearing repo.
            for consumer in _consumer_repos_for_root(workspace_root):
                if _is_self_repo(consumer):
                    continue
                slug = consumer.name
                yield (
                    agents_md,
                    consumer / "AGENTS.md",
                    f"repos/{slug}:AGENTS.md",
                    False,
                )
                # T-41: CLAUDE.md in consumer repos is also a 1-line stub.
                yield (
                    None,
                    consumer / "CLAUDE.md",
                    f"repos/{slug}:CLAUDE.md",
                    True,
                )

        reports_agents_md = agentic_dir / "data" / "reports-AGENTS.md"
        if reports_agents_md.exists():
            yield (
                reports_agents_md,
                workspace_root / ".dadaia" / "reports" / "AGENTS.md",
                "reports:AGENTS.md",
                False,
            )

        for src in self._iter_files(agentic_dir / "skills"):
            rel = src.relative_to(agentic_dir / "skills")
            yield (
                src,
                workspace_root / ".agents" / "skills" / rel,
                f"agents:skills/{rel.as_posix()}",
                False,
            )

        for name in _CLAUDE_DIRS:
            base = agentic_dir / name
            for src in self._iter_files(base):
                rel = src.relative_to(base)
                yield (
                    src,
                    workspace_root / ".claude" / name / rel,
                    f"claude:{name}/{rel.as_posix()}",
                    False,
                )

        for src in self._iter_files(agentic_dir / "rules"):
            # T-18 / ADR-1/D2: only executable rules (those with YAML frontmatter)
            # are projected to .codex/rules/. Behavioral prose rules are skipped.
            try:
                rule_text = src.read_text(encoding="utf-8")
            except OSError:
                continue
            if not rule_text.startswith("---\n"):
                continue
            rel = src.relative_to(agentic_dir / "rules")
            yield (
                src,
                workspace_root / ".codex" / "rules" / rel,
                f"codex:rules/{rel.as_posix()}",
                False,
            )

        for name in _OPENCODE_DIRS:
            base = agentic_dir / name
            for src in self._iter_files(base):
                rel = src.relative_to(base)
                # OpenCode agents have tools: stripped — compare transformed content
                is_opencode_agent = name == "agents"
                yield (
                    src,
                    workspace_root / ".opencode" / name / rel,
                    f"opencode:{name}/{rel.as_posix()}",
                    is_opencode_agent,
                )

        yield (None, workspace_root / ".opencode" / "hooks", "opencode:hooks", False)

    def _agents_md_source(self, agentic_dir: Path) -> Path | None:
        for path in (agentic_dir / "templates" / "AGENTS.md", agentic_dir / "data" / "AGENTS.md"):
            if path.exists():
                return path
        return None

    def _consumer_repos(self, workspace_root: Path) -> list[Path]:
        """Return marker-bearing consumer repo directories under ``repos/``.

        A directory qualifies when BOTH markers are present:
        - ``<repo>/.dadaia/`` directory (signals dadaia-aware consumer)
        - ``<repo>/.dadaia/agentic/`` directory (signals full agentic setup)

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
                sys.stderr.write(f"[skip] {p}/AGENTS.md (no .dadaia/ marker)\n")
        return result

    def _is_self_repo(self, consumer: Path) -> bool:
        """Return True when *consumer* is the dadaia-workspace repo itself.

        R14 self-skip: compare ``package_version`` in the consumer's own
        manifest against the currently installed package version.  A match
        means the consumer IS the dadaia-workspace source tree — we must
        never overwrite ``data/AGENTS.md`` by projecting back onto ourselves.
        """
        manifest_path = consumer / ".dadaia" / "agentic" / "manifest.json"
        if not manifest_path.exists():
            return False
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            consumer_version = manifest.get("package_version", "")
            return bool(consumer_version and consumer_version == _package_version())
        except (json.JSONDecodeError, OSError):
            return False

    def _copy_tree(self, src_dir: Path, dst_dir: Path, force: bool, installed: list[str]) -> None:
        if not src_dir.exists():
            return
        for src in self._iter_files(src_dir):
            self._copy_file(src, dst_dir / src.relative_to(src_dir), force, installed)

    def _copy_file(self, src: Path, dst: Path, force: bool, installed: list[str]) -> None:
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists() and not force:
            installed.append(f"[skip] {dst}")
            return
        shutil.copy2(src, dst)
        installed.append(f"[ok]   {dst}")

    def _write_generated(self, dst: Path, content: str, force: bool, installed: list[str]) -> None:
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists() and not force:
            installed.append(f"[skip] {dst}")
            return
        _atomic_write_text(dst, content)
        installed.append(f"[ok]   {dst}")

    def _compare(self, src: Path, dst: Path, label: str) -> str:
        if not dst.exists():
            return f"[missing] {label}"
        if _sha256(src) != _sha256(dst):
            return f"[drift] {label}"
        return f"[ok] {label}"

    def _compare_content(self, expected: str, dst: Path, label: str) -> str:
        if not dst.exists():
            return f"[missing] {label}"
        if dst.read_text(encoding="utf-8") != expected:
            return f"[drift] {label}"
        return f"[ok] {label}"

    def _iter_files(self, root: Path) -> Iterable[Path]:
        if not root.exists():
            return ()
        return (path for path in sorted(root.rglob("*")) if path.is_file())

    def _claude_settings(self, workspace_root: Path) -> dict[str, object]:
        return {
            "hooks": {
                "PreToolUse": [
                    {
                        "hooks": [
                            {
                                "command": str(
                                    workspace_root / ".dadaia" / "scripts" / "sdd-spec-gate.sh"
                                ),
                                "type": "command",
                            }
                        ],
                        "matcher": "",
                    }
                ],
                "UserPromptSubmit": [
                    {
                        "hooks": [
                            {
                                "command": str(
                                    workspace_root / ".dadaia" / "scripts" / "ctx-inject.sh"
                                ),
                                "type": "command",
                            }
                        ],
                        "matcher": "",
                    }
                ],
            }
        }

    def _codex_config(self, agentic_dir: Path) -> str:
        lines = ['# Generated by "dadaia public install --target codex".\n', "\n"]
        lines.append("approved_commands = [\n")
        for cmd in (
            "docker",
            "make",
            "git",
            "ls",
            "find",
            "cat",
            "grep",
            "curl",
            "python3",
            "systemctl",
            "journalctl",
        ):
            lines.append(f'  "{cmd}",\n')
        lines.append("]\n")
        # FR7: emit [agents.<name>] config_file blocks — one per canonical agent.
        # Each agent's full definition lives in .codex/agents/<name>.toml.
        agents_blocks = _render_agents_config_file_blocks(agentic_dir / "agents")
        if agents_blocks:
            lines.append("\n")
            lines.append(agents_blocks)
        # T-PB-4: emit [skills] table after all [agents.*] blocks
        lines.append("\n")
        lines.append("[skills]\n")
        lines.append('paths = [".agents/skills"]\n')
        return "".join(lines)

    def _codex_hooks(self, workspace_root: Path) -> dict[str, object]:
        return {
            "PreToolUse": [
                {
                    "matcher": {
                        "tool": [
                            "write_file",
                            "edit_file",
                            "apply_patch",
                            "Write",
                            "Edit",
                            "MultiEdit",
                        ]
                    },
                    "command": str(workspace_root / ".dadaia" / "scripts" / "sdd-spec-gate.sh"),
                }
            ]
        }

    def _opencode_config(self, workspace_root: Path) -> dict[str, object]:
        instructions: list[str] = ["AGENTS.md", "CLAUDE.md"]
        primary_json = workspace_root / ".dadaia" / "states" / "primary_context.json"
        if primary_json.exists():
            try:
                ctx = json.loads(primary_json.read_text(encoding="utf-8"))
                repo_slug = ctx.get("repo_slug", "")
                if repo_slug and (workspace_root / "repos" / repo_slug / "AGENTS.md").exists():
                    instructions.append(f"repos/{repo_slug}/AGENTS.md")
            except (json.JSONDecodeError, KeyError):
                pass
        return {
            "$schema": "https://opencode.ai/config.json",
            "instructions": instructions,
            "permission": "allow",
        }
