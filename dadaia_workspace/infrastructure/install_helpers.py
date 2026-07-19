"""Installation helper functions for the public-asset pipeline.

Extracted from ``FileSystemPublicAssetManager`` in ``public_assets.py`` to keep
that module under 600 lines.  These are thin free functions (or callables) that
the class delegates to; they take explicit Path arguments instead of ``self``.
"""

from __future__ import annotations

import contextlib
import hashlib
import shutil
from collections.abc import Callable, Iterable, Mapping
from datetime import UTC, datetime
from pathlib import Path

from dadaia_workspace.core.agent_model_templates import CORE_AGENTS
from dadaia_workspace.core.exceptions import PublicAssetError
from dadaia_workspace.core.models.agent_model_policy import (
    ResolvedAgentModel,
    codex_effort_for_claude_effort,
)
from dadaia_workspace.infrastructure.public_assets_common import (
    _SCHEMA_VERSION,
    _atomic_write_text,
    _package_version,
    _sha256,
)
from dadaia_workspace.infrastructure.runtime_transforms.codex_assets import (
    _parse_agent_frontmatter,
    _parse_write_allowlist,
    _render_codex_agent_toml,
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
    """Install universal skills into ``.agents/`` for all runtimes."""
    copy_tree(
        agentic_dir / "skills",
        workspace_root / ".agents" / "skills",
        force,
        installed,
        iter_files_fn,
    )


def remove_legacy_workflow_projections(
    workspace_root: Path,
    installed: list[str],
) -> None:
    """Remove retired Markdown workflow projections without touching operator files."""
    for harness_dir in (".agents", ".claude", ".codex", ".kimi-code"):
        legacy_dir = workspace_root / harness_dir / "workflows"
        if not legacy_dir.is_dir():
            continue
        for path in sorted(legacy_dir.glob("*.workflow.md")):
            path.unlink()
            installed.append(f"[rm] {path}")
        # Preserve a non-empty directory: non-workflow/operator files are outside
        # this migration's ownership.
        with contextlib.suppress(OSError):
            legacy_dir.rmdir()


# ---------------------------------------------------------------------------
# Render-at-install seam (v0.1.65 FR5/D-6)
# ---------------------------------------------------------------------------


def render_claude_agent(staged_text: str, resolved: ResolvedAgentModel) -> str:
    """Compose a staged generic agent body + its resolved policy (the D-6 seam).

    The SINGLE injection point shared by install-write, doctor-compare, and panel
    Apply: any pre-existing top-level ``model:``/``effort:`` frontmatter lines are
    stripped (pack bodies author ``model:`` as their pack default — D-5), then the
    resolved ``model:`` and ``effort:`` are appended deterministically as the LAST
    lines of the frontmatter block. ``effort:`` is OMITTED entirely when unresolved
    (F-6 plugin asymmetry — never empty or placeholder), keeping render output
    deterministic for the doctor render-compare.

    Raises:
        PublicAssetError: when *staged_text* carries no closed YAML frontmatter
            block (a canonical agent body always does).
    """
    if not staged_text.startswith("---\n"):
        raise PublicAssetError(
            "cannot render agent projection: staged body has no YAML frontmatter block"
        )
    end_idx = staged_text.find("\n---\n", 4)
    if end_idx == -1:
        raise PublicAssetError(
            "cannot render agent projection: staged frontmatter block is not closed"
        )
    frontmatter = staged_text[4 : end_idx + 1]
    rest = staged_text[end_idx + 5 :]
    kept = [line for line in frontmatter.splitlines() if not line.startswith(("model:", "effort:"))]
    kept.append(f"model: {resolved.model}")
    if resolved.effort is not None:
        kept.append(f"effort: {resolved.effort}")
    return "---\n" + "\n".join(kept) + "\n---\n" + rest


def install_claude_agents(
    agentic_dir: Path,
    claude_dir: Path,
    force: bool,
    installed: list[str],
    iter_files_fn: Callable[[Path], Iterable[Path]],
    resolved_models: Mapping[str, ResolvedAgentModel],
) -> None:
    """Project staged agents into ``.claude/agents/`` through the render seam (FR5).

    Core agents (present in *resolved_models*) are RENDERED — staged generic body +
    resolved ``(model, effort)`` — via ``write_generated`` hash-compare; any other
    staged body (the plugin stubs) is copied verbatim. ``--force`` therefore
    re-RENDERS a diverged projection back to the render output, never to raw staged
    bytes (F-5). Orphan projections are pruned exactly like ``copy_tree``.
    """
    src_dir = agentic_dir / "agents"
    dst_dir = claude_dir / "agents"
    if not src_dir.exists():
        return
    managed: set[Path] = set()
    for src in iter_files_fn(src_dir):
        rel = src.relative_to(src_dir)
        managed.add(rel)
        resolved = resolved_models.get(src.stem)
        if resolved is None or src.suffix != ".md":
            copy_file(src, dst_dir / rel, force, installed)
        else:
            content = render_claude_agent(src.read_text(encoding="utf-8"), resolved)
            write_generated(dst_dir / rel, content, force, installed)
    for dst in iter_files_fn(dst_dir):
        if dst.relative_to(dst_dir) not in managed:
            dst.unlink(missing_ok=True)
            installed.append(f"[prune] {dst}")
    for d in sorted((p for p in dst_dir.rglob("*") if p.is_dir()), reverse=True):
        if not any(d.iterdir()):
            d.rmdir()


def resolve_codex_agent_model(
    agent_name: str,
    staged_model: str | None,
    resolved: ResolvedAgentModel | None,
) -> tuple[str, str | None]:
    """Resolve the ``(claude_model, reasoning_effort)`` for one codex agent render.

    Precedence: resolved policy (core agents + installed pack agents) > staged
    authored ``model:`` (plugin bodies — F-3 keeps this path) > the legacy
    ``claude-sonnet-4-6`` default (plugin STUBS only, which author no model).

    Raises:
        PublicAssetError: F-3 fail-closed — a CORE agent supplied with neither a
            staged ``model:`` nor a resolved policy model must never render on a
            silent default (a wiring miss must never ship wrong codex models
            under green tests).
    """
    if resolved is not None:
        effort = (
            codex_effort_for_claude_effort(resolved.effort) if resolved.effort is not None else None
        )
        return resolved.model, effort
    if staged_model:
        return staged_model, None
    if agent_name in CORE_AGENTS:
        raise PublicAssetError(
            f"cannot render codex agent '{agent_name}': core agent has neither a "
            "staged 'model:' nor a resolved agent-model policy model (F-3 fail-closed "
            "— the render pipeline must be supplied the resolved policy)"
        )
    return "claude-sonnet-4-6", None


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
    agents_md_source_fn: Callable[[Path], Path | None],
) -> Iterable[tuple[Path | None, Path, str, bool]]:
    """Yield (src, dst, label, transform) tuples for doctor comparison.

    transform=True means dst was produced by a content transform (e.g. the
    generated CLAUDE.md stub) and must be compared by content rather than by
    file hash.
    """
    agents_md = agents_md_source_fn(agentic_dir)
    if agents_md is not None:
        yield (agents_md, workspace_root / "AGENTS.md", "root:AGENTS.md", False)
        yield (None, workspace_root / "CLAUDE.md", "root:CLAUDE.md", True)
        # v0.1.60 FR9 (bug public-doctor-flags-hand-authored-consumer-agents-md): the
        # consumer-repo guardrail pairs are NO LONGER doctored here. They flow through the
        # single provenance-aware authority `_doctor_consumer_pair_lines`, invoked directly by
        # `manager.doctor()`, so a hand-authored (no-banner) consumer AGENTS.md reads [foreign]
        # (never [drift]/[missing]) and `public doctor` exits 0 (Ruling 16). Keeping a parallel
        # sha-compare here would re-open the clobber-adjacent perpetual-drift regression.

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
    resolved_models: Mapping[str, ResolvedAgentModel] | None = None,
) -> None:
    """Generate .codex/agents/<agent-id>.toml for each canonical agent.

    The codex projection consumes the SAME resolved config as the claude render
    (G-3, v0.1.65 FR5): *resolved_models* supplies the per-agent resolved
    ``(model, effort)``; the codex model id derives from the registry mapping and
    ``model_reasoning_effort`` from the D-3 clamp of the resolved effort. A CORE
    agent with neither a staged ``model:`` nor a resolved policy model fails
    closed (F-3 — see :func:`resolve_codex_agent_model`).
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
    expected_tomls = {md_file.with_suffix(".toml").name for md_file in agents_src.glob("*.md")}
    # Prune stale .toml unconditionally (rc-4 / T-017-32 — fixes orphan projections): an
    # agent removed from source must not leave an orphan projection, regardless of --force.
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
        staged_model_raw = fm.get("model")
        staged_model = str(staged_model_raw) if staged_model_raw else None
        resolved = resolved_models.get(agent_name) if resolved_models is not None else None
        claude_model, reasoning_effort = resolve_codex_agent_model(
            agent_name, staged_model, resolved
        )
        codex_model = map_model(claude_model)
        description = fm.get("description")
        # The description is the Codex spawn-trigger surface; it must pass through
        # the SAME replacement table as the body so no Claude-ism (e.g. "Agent tool")
        # ships on it (codex-agent-description-claude-ism-leak, T-013-09).
        codex_description = (
            transform_for_codex(str(description), agent_name) if description else None
        )
        toml_content = _render_codex_agent_toml(
            agent_name,
            codex_model,
            body,
            description=codex_description,
            claude_model=claude_model,
            reasoning_effort=reasoning_effort,
        )
        dst = agents_dst / f"{agent_name}.toml"
        if dst.exists() and not force:
            dst_sha = _sha256(dst)
            src_sha = hashlib.sha256(toml_content.encode("utf-8")).hexdigest()
            if dst_sha == src_sha:
                installed.append(f"[skip] {dst}")
            else:
                # _atomic_write_text writes LF-exact (newline="") so the bytes on
                # disk match the LF hash above; a plain write_text would emit CRLF
                # on Windows and the skip would never fire. See FR-RC2-2.
                _atomic_write_text(dst, toml_content)
                installed.append(f"[ok]   {dst}")
        else:
            _atomic_write_text(dst, toml_content)
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
