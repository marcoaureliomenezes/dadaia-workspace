"""Public asset manager — stages package assets and projects them to agent runtimes."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from collections.abc import Iterable
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from dadaia_workspace.core.exceptions import PublicAssetError

_SCHEMA_VERSION = "1"
# OpenCode v1.14+ expects `tools` to be an object or omitted — not an array.
# Strip it from agent frontmatter when deploying to the opencode projection.
_FRONTMATTER_TOOLS_RE = re.compile(r"^tools:\n(?:  - [^\n]+\n)*", re.MULTILINE)
# `opencode_model:` lets agents declare a cheaper model for the OpenCode projection.
_FRONTMATTER_OPENCODE_MODEL_RE = re.compile(r"^opencode_model:\s*(.+?)$", re.MULTILINE)
_FRONTMATTER_MODEL_VALUE_RE = re.compile(r"^(model:\s*)(.+?)$", re.MULTILINE)
_FRONTMATTER_OPENCODE_MODEL_FIELD_RE = re.compile(r"^opencode_model:[^\n]*\n", re.MULTILINE)
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


def _render_agent_toml_block(name: str, fm: dict[str, object]) -> str:
    """Render a ``[agents."<name>"]`` TOML table block from parsed frontmatter *fm*.

    Keys are always quoted for safety (required for hyphenated names like
    ``software-engineer``). Missing or None fields are omitted. The ``tools``
    field, if present, is emitted as a TOML array of basic strings.

    Names containing ``]`` are rejected (cannot appear safely in a TOML key).
    """
    if "]" in name:
        raise ValueError(f"Agent name contains invalid character ']': {name!r}")
    lines: list[str] = [f'[agents."{name}"]\n']
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

    def install(self, workspace_root: Path, target: str = "all", force: bool = False) -> list[str]:
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
            if expected_src is None:
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
                self._codex_config(),
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

        return reports

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
        self._copy_tree(agentic_dir / "rules", codex_dir / "rules", force, installed)
        self._copy_tree(agentic_dir / "workflows", codex_dir / "workflows", force, installed)
        self._install_universal_skills(agentic_dir, workspace_root, force, installed)
        self._write_generated(
            codex_dir / "hooks.json",
            _json_dump(self._codex_hooks(workspace_root)),
            force,
            installed,
        )
        self._write_generated(
            codex_dir / "config.toml",
            self._codex_config(),
            force,
            installed,
        )

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
            rel = src.relative_to(agentic_dir / "rules")
            yield (
                src,
                workspace_root / ".codex" / "rules" / rel,
                f"codex:rules/{rel.as_posix()}",
                False,
            )

        yield (None, workspace_root / ".codex" / "agents", "codex:agents", False)

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

    def _codex_config(self) -> str:
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
