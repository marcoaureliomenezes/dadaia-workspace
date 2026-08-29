"""Installation helper functions for the public-asset pipeline.

Extracted from ``FileSystemPublicAssetManager`` in ``public_assets.py`` to keep
that module under 600 lines.  These are thin free functions (or callables) that
the class delegates to; they take explicit Path arguments instead of ``self``.
"""

from __future__ import annotations

import contextlib
from collections.abc import Callable, Iterable
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
    _package_version,
    _sha256,
)
from dadaia_workspace.infrastructure.runtime_transforms.codex_assets import (
    _parse_write_allowlist,
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


#: The nine always-on rule files the library published before ``DADAIA.md``. Their law is
#: carried in full by the single system-prompt file; the projections are removed by name.
#: A blanket prune of the rules directory is NOT correct — it also hosts operator-authored
#: rules, which this migration does not own.
_RETIRED_CORE_RULES: tuple[str, ...] = (
    "backlog-ownership.md",
    "bug-hotfix-doctrine.md",
    "bug-registration-guardrail.md",
    "dadaia-workspace-dev-guardrail.md",
    "harness-skill-scope.md",
    "plugin-scope.md",
    "release-governance.md",
    "tmp-file-guardrail.md",
    "workspace-protocol.md",
)


def remove_legacy_bind_epoch_state(workspace_root: Path, installed: list[str]) -> None:
    """Remove the retired bind-epoch marker state dir (v0.5.0 FR1, F-09).

    The marker subsystem was deleted in v0.5.0 — nothing reads or writes
    ``.dadaia/states/bind_epoch/`` anymore, so markers left by earlier releases are
    orphan state in every upgraded workspace. Markers are single-line pid-chain files
    the bind CLI wrote; the directory holds nothing else, so a full sweep is safe.
    Named migration, kept one release (same regime as the other ``remove_*`` steps).
    """
    epoch_dir = workspace_root / ".dadaia" / "states" / "bind_epoch"
    if not epoch_dir.is_dir():
        return
    for path in sorted(p for p in epoch_dir.iterdir() if p.is_file()):
        path.unlink()
        installed.append(f"[rm] {path}")
    with contextlib.suppress(OSError):
        epoch_dir.rmdir()


def remove_retired_core_rules(workspace_root: Path, installed: list[str]) -> None:
    """Remove the pre-DADAIA.md core rule projections, by name, without touching others.

    Bug ``retired-lib-asset-leaves-orphan-projection``: ``copy_tree`` returns before its
    orphan-prune loop when the source directory no longer exists, so retiring a whole
    asset family never propagates to the instance. Until that is fixed generically, this
    named migration keeps the instance honest — the law must live in exactly one file.
    """
    rules_dir = workspace_root / ".claude" / "rules"
    if not rules_dir.is_dir():
        return
    for name in _RETIRED_CORE_RULES:
        path = rules_dir / name
        if path.is_file():
            path.unlink()
            installed.append(f"[rm] {path}")


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
    (F-6 — never empty or placeholder), keeping render output
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


def resolve_codex_agent_model(
    agent_name: str,
    staged_model: str | None,
    resolved: ResolvedAgentModel | None,
) -> tuple[str, str | None]:
    """Resolve the ``(claude_model, reasoning_effort)`` for one codex agent render.

    Precedence: resolved policy (core agents + installed pack agents) > staged
    authored ``model:`` > the legacy ``claude-sonnet-4-6`` default.

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
