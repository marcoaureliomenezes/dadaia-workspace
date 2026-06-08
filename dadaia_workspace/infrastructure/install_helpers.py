"""Installation helper functions for the public-asset pipeline.

Extracted from ``FileSystemPublicAssetManager`` in ``public_assets.py`` to keep
that module under 600 lines.  These are thin free functions (or callables) that
the class delegates to; they take explicit Path arguments instead of ``self``.
"""

from __future__ import annotations

import hashlib
import shutil
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from pathlib import Path

from dadaia_workspace.infrastructure.public_assets_common import (
    _SCHEMA_VERSION,
    _atomic_write_text,
    _package_version,
    _sha256,
)
from dadaia_workspace.infrastructure.runtime_transforms.codex_assets import (
    _parse_agent_frontmatter,
    _parse_write_allowlist,
    _prepare_agent_for_opencode,
    _render_codex_agent_toml,
)
from dadaia_workspace.infrastructure.workspace_guardrail import (
    _consumer_repos_for_root,
    _is_self_repo,
)

# ---------------------------------------------------------------------------
# Stage helpers (moved from FileSystemPublicAssetManager internal methods)
# ---------------------------------------------------------------------------


def build_agents_index(agentic_dir: Path) -> dict[str, list[str]]:
    """Map every staged agent to its ``paths.write_allowlist`` globs (T-016-00)."""
    agents_dir = agentic_dir / "agents"
    index: dict[str, list[str]] = {}
    if not agents_dir.exists():
        return index
    for md_file in sorted(agents_dir.glob("*.md")):
        index[md_file.stem] = _parse_write_allowlist(md_file.read_text(encoding="utf-8"))
    return index


def validate_workflows(agentic_dir: Path) -> None:
    """Validate all staged workflow files via MarkdownWorkflowStore."""
    workflows_dir = agentic_dir / "workflows"
    if not workflows_dir.exists():
        return
    from dadaia_workspace.core.exceptions import PublicAssetError, WorkflowSchemaError
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


def build_manifest(
    agentic_dir: Path,
    iter_files_fn: Callable[[Path], Iterable[Path]],
) -> dict[str, object]:
    """Build the staging manifest dict from all files under *agentic_dir*."""
    assets: list[dict[str, str]] = []
    for path in iter_files_fn(agentic_dir):
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


def install_agents_md(
    agentic_dir: Path,
    workspace_root: Path,
    force: bool,
    installed: list[str],
    agents_md_source_fn: Callable[[Path], Path | None],
) -> None:
    """Install the root AGENTS.md from the staged templates or data directory."""
    src = agents_md_source_fn(agentic_dir)
    if src is not None:
        copy_file(src, workspace_root / "AGENTS.md", force, installed)


def install_reports_agents_md(
    agentic_dir: Path,
    workspace_root: Path,
    force: bool,
    installed: list[str],
) -> None:
    """Install the reports-AGENTS.md into .dadaia/reports/AGENTS.md."""
    src = agentic_dir / "data" / "reports-AGENTS.md"
    if src.exists():
        reports_dir = workspace_root / ".dadaia" / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        copy_file(src, reports_dir / "AGENTS.md", force, installed)


def install_handoff_agents_md(
    agentic_dir: Path,
    workspace_root: Path,
    force: bool,
    installed: list[str],
) -> None:
    """Install the handoff-AGENTS.md into .dadaia/handoff/AGENTS.md."""
    src = agentic_dir / "data" / "handoff-AGENTS.md"
    if src.exists():
        handoff_dir = workspace_root / ".dadaia" / "handoff"
        handoff_dir.mkdir(parents=True, exist_ok=True)
        copy_file(src, handoff_dir / "AGENTS.md", force, installed)


def install_dadaia_agents_md(
    agentic_dir: Path,
    workspace_root: Path,
    force: bool,
    installed: list[str],
) -> None:
    """Install the various .dadaia/**/AGENTS.md files from staged data assets."""
    mappings = (
        ("dadaia-AGENTS.md", workspace_root / ".dadaia" / "AGENTS.md"),
        ("tmp-AGENTS.md", workspace_root / ".dadaia" / "tmp" / "AGENTS.md"),
        ("states-AGENTS.md", workspace_root / ".dadaia" / "states" / "AGENTS.md"),
    )
    for source_name, dst in mappings:
        src = agentic_dir / "data" / source_name
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            copy_file(src, dst, force, installed)


def install_universal_skills(
    agentic_dir: Path,
    workspace_root: Path,
    force: bool,
    installed: list[str],
    iter_files_fn: Callable[[Path], Iterable[Path]],
) -> None:
    """Install skills and workflows into .agents/ for all runtimes."""
    copy_tree(
        agentic_dir / "skills",
        workspace_root / ".agents" / "skills",
        force,
        installed,
        iter_files_fn,
    )
    copy_tree(
        agentic_dir / "workflows",
        workspace_root / ".agents" / "workflows",
        force,
        installed,
        iter_files_fn,
    )


# ---------------------------------------------------------------------------
# File-copy utilities
# ---------------------------------------------------------------------------


def copy_file(src: Path, dst: Path, force: bool, installed: list[str]) -> None:
    """Copy *src* to *dst*, respecting hash-compare skip logic (T-PROP-01)."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and not force:
        src_sha = _sha256(src)
        dst_sha = _sha256(dst)
        if src_sha == dst_sha:
            installed.append(f"[skip] {dst}")
            return
    shutil.copy2(src, dst)
    installed.append(f"[ok]   {dst}")


def write_generated(dst: Path, content: str, force: bool, installed: list[str]) -> None:
    """Write generated *content* to *dst*, respecting hash-compare logic (T-PROP-01)."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and not force:
        content_bytes = content.encode("utf-8")
        src_sha = hashlib.sha256(content_bytes).hexdigest()
        dst_sha = _sha256(dst)
        if src_sha == dst_sha:
            installed.append(f"[skip] {dst}")
            return
    _atomic_write_text(dst, content)
    installed.append(f"[ok]   {dst}")


def copy_tree(
    src_dir: Path,
    dst_dir: Path,
    force: bool,
    installed: list[str],
    iter_files_fn: Callable[[Path], Iterable[Path]],
) -> None:
    """Copy all files from *src_dir* to *dst_dir*, pruning orphan projections."""
    if not src_dir.exists():
        return
    managed: set[Path] = set()
    for src in iter_files_fn(src_dir):
        rel = src.relative_to(src_dir)
        managed.add(rel)
        copy_file(src, dst_dir / rel, force, installed)
    for dst in iter_files_fn(dst_dir):
        if dst.relative_to(dst_dir) not in managed:
            dst.unlink(missing_ok=True)
            installed.append(f"[prune] {dst}")
    for d in sorted((p for p in dst_dir.rglob("*") if p.is_dir()), reverse=True):
        if not any(d.iterdir()):
            d.rmdir()


def remove_stale_files(src_dir: Path, dst_dir: Path, pattern: str, installed: list[str]) -> None:
    """Remove stale files from *dst_dir* whose names no longer exist in *src_dir*."""
    if not dst_dir.exists():
        return
    expected = {src.name for src in src_dir.glob(pattern)} if src_dir.exists() else set()
    for stale in sorted(dst_dir.glob(pattern)):
        if stale.name not in expected:
            stale.unlink()
            installed.append(f"[rm]   {stale}")


# ---------------------------------------------------------------------------
# Runtime expectations (yields for doctor comparison)
# ---------------------------------------------------------------------------


def runtime_expectations(
    agentic_dir: Path,
    workspace_root: Path,
    iter_files_fn: Callable[[Path], Iterable[Path]],
    claude_dirs: tuple[str, ...],
    opencode_dirs: tuple[str, ...],
    agents_md_source_fn: Callable[[Path], Path | None],
) -> Iterable[tuple[Path | None, Path, str, bool]]:
    """Yield (src, dst, label, transform) tuples for doctor comparison.

    transform=True means dst was produced by a content transform (e.g. OpenCode
    agent tools-strip) and must be compared by content rather than by file hash.
    """
    agents_md = agents_md_source_fn(agentic_dir)
    if agents_md is not None:
        yield (agents_md, workspace_root / "AGENTS.md", "root:AGENTS.md", False)
        yield (None, workspace_root / "CLAUDE.md", "root:CLAUDE.md", True)
        for consumer in _consumer_repos_for_root(workspace_root):
            if _is_self_repo(consumer):
                continue
            slug = consumer.name
            yield (agents_md, consumer / "AGENTS.md", f"repos/{slug}:AGENTS.md", False)
            yield (None, consumer / "CLAUDE.md", f"repos/{slug}:CLAUDE.md", True)

    reports_agents_md = agentic_dir / "data" / "reports-AGENTS.md"
    if reports_agents_md.exists():
        yield (
            reports_agents_md,
            workspace_root / ".dadaia" / "reports" / "AGENTS.md",
            "reports:AGENTS.md",
            False,
        )

    handoff_agents_md = agentic_dir / "data" / "handoff-AGENTS.md"
    if handoff_agents_md.exists():
        yield (
            handoff_agents_md,
            workspace_root / ".dadaia" / "handoff" / "AGENTS.md",
            "handoff:AGENTS.md",
            False,
        )

    dadaia_agents = (
        ("dadaia-AGENTS.md", workspace_root / ".dadaia" / "AGENTS.md", "dadaia:AGENTS.md"),
        (
            "tmp-AGENTS.md",
            workspace_root / ".dadaia" / "tmp" / "AGENTS.md",
            "dadaia:tmp/AGENTS.md",
        ),
        (
            "states-AGENTS.md",
            workspace_root / ".dadaia" / "states" / "AGENTS.md",
            "dadaia:states/AGENTS.md",
        ),
    )
    for source_name, dst, label in dadaia_agents:
        src = agentic_dir / "data" / source_name
        if src.exists():
            yield (src, dst, label, False)

    for src in iter_files_fn(agentic_dir / "skills"):
        rel = src.relative_to(agentic_dir / "skills")
        yield (
            src,
            workspace_root / ".agents" / "skills" / rel,
            f"agents:skills/{rel.as_posix()}",
            False,
        )

    for name in claude_dirs:
        base = agentic_dir / name
        for src in iter_files_fn(base):
            rel = src.relative_to(base)
            yield (
                src,
                workspace_root / ".claude" / name / rel,
                f"claude:{name}/{rel.as_posix()}",
                False,
            )

    for name in opencode_dirs:
        base = agentic_dir / name
        for src in iter_files_fn(base):
            rel = src.relative_to(base)
            is_opencode_agent = name == "agents"
            yield (
                src,
                workspace_root / ".opencode" / name / rel,
                f"opencode:{name}/{rel.as_posix()}",
                is_opencode_agent,
            )

    yield (None, workspace_root / ".opencode" / "hooks", "opencode:hooks", False)

    scripts_base = agentic_dir / "scripts"
    for src in iter_files_fn(scripts_base):
        rel = src.relative_to(scripts_base)
        yield (
            src,
            workspace_root / ".dadaia" / "scripts" / rel,
            f"dadaia:scripts/{rel.as_posix()}",
            False,
        )


# ---------------------------------------------------------------------------
# Codex agent generation
# ---------------------------------------------------------------------------


def install_codex_agents(
    agentic_dir: Path,
    workspace_root: Path,
    force: bool,
    installed: list[str],
) -> None:
    """Generate .codex/agents/<agent-id>.toml for each canonical agent."""
    from dadaia_workspace.infrastructure.runtime_transforms.codex import (
        transform_for_codex,
    )
    from dadaia_workspace.infrastructure.runtime_transforms.model_mapping import (
        map_model,
    )

    agents_src = agentic_dir / "agents"
    agents_dst = workspace_root / ".codex" / "agents"
    agents_dst.mkdir(parents=True, exist_ok=True)
    expected_tomls = {md_file.with_suffix(".toml").name for md_file in agents_src.glob("*.md")}
    if force:
        for stale in sorted(agents_dst.glob("*.toml")):
            if stale.name not in expected_tomls:
                stale.unlink()
                installed.append(f"[rm]   {stale}")

    for md_file in sorted(agents_src.glob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        fm = _parse_agent_frontmatter(text)
        if not fm:
            continue
        agent_name = str(fm.get("name", ""))
        if not agent_name:
            continue
        if text.startswith("---\n"):
            end_idx = text.find("\n---\n", 4)
            body = text[end_idx + 5 :] if end_idx != -1 else text
        else:
            body = text
        body = transform_for_codex(body, agent_name)
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
            dst_sha = _sha256(dst)
            src_sha = hashlib.sha256(toml_content.encode("utf-8")).hexdigest()
            if dst_sha == src_sha:
                installed.append(f"[skip] {dst}")
            else:
                dst.write_text(toml_content, encoding="utf-8")
                installed.append(f"[ok]   {dst}")
        else:
            dst.write_text(toml_content, encoding="utf-8")
            installed.append(f"[ok]   {dst}")


def install_codex_runtime_adapters(
    public_dir: Path,
    workspace_root: Path,
    force: bool,
    installed: list[str],
    copy_file_fn: Callable[[Path, Path, bool, list[str]], None],
) -> None:
    """Copy Codex-only adapter SKILL.md files from public/runtime/codex/ to .codex/skills/."""
    src_root = public_dir / "runtime" / "codex"
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
        copy_file_fn(skill_src, skill_dst, force, installed)


def copy_agents_for_opencode(
    src_dir: Path,
    dst_dir: Path,
    force: bool,
    installed: list[str],
    iter_files_fn: Callable[[Path], Iterable[Path]],
) -> None:
    """Copy agent .md files stripping the ``tools`` array from frontmatter."""
    if not src_dir.exists():
        return
    for src in iter_files_fn(src_dir):
        dst = dst_dir / src.relative_to(src_dir)
        dst.parent.mkdir(parents=True, exist_ok=True)
        content = _prepare_agent_for_opencode(src.read_text(encoding="utf-8"))
        if dst.exists() and not force:
            dst_sha = _sha256(dst)
            src_sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
            if dst_sha == src_sha:
                installed.append(f"[skip] {dst}")
                continue
        dst.write_text(content, encoding="utf-8")
        installed.append(f"[ok]   {dst}")
