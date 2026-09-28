"""Pure install helpers: the staging manifest and the persona renders."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from pathlib import Path

from dadaia_workspace.core.exceptions import PublicAssetError
from dadaia_workspace.core.model_registry import ResolvedAgentModel, codex_effort_for_claude_effort
from dadaia_workspace.infrastructure.public_assets_common import (
    _SCHEMA_VERSION,
    _package_version,
    _sha256,
)
from dadaia_workspace.infrastructure.runtime_transforms.codex_assets import (
    _parse_agent_frontmatter,
    _split_frontmatter,
)


def persona_read_only(frontmatter: Mapping[str, object]) -> bool:
    """The persona's ``read_only`` field; fail-closed when not ``true``/``false``."""
    declared = frontmatter.get("read_only")
    if declared not in ("true", "false"):
        raise PublicAssetError(
            "cannot render agent projection: frontmatter must declare "
            f"read_only as true or false, got {declared!r}"
        )
    return declared == "true"


def build_manifest(
    agentic_dir: Path,
    iter_files_fn: Callable[[Path], Iterable[Path]],
) -> dict[str, object]:
    """The staging manifest of every file under *agentic_dir*."""
    rels = {
        p: p.relative_to(agentic_dir).as_posix()
        for p in iter_files_fn(agentic_dir)
        if p.name != "manifest.json"
    }
    assets = [
        {"path": r, "sha256": _sha256(p), "type": r.split("/", 1)[0]} for p, r in rels.items()
    ]
    return {
        "schema_version": _SCHEMA_VERSION,
        "package_version": _package_version(),
        "assets": assets,
    }


def render_claude_agent(staged_text: str, resolved: ResolvedAgentModel) -> str:
    """A staged agent with derived frontmatter lines replaced by its resolved policy, last.

    ``effort:`` is omitted when unresolved — never empty.
    """
    frontmatter, rest = _split_frontmatter(staged_text)
    derived = ("model:", "effort:", "permissionMode:", "disallowedTools:")
    kept = [line for line in frontmatter.splitlines() if not line.startswith(derived)]
    if persona_read_only(_parse_agent_frontmatter(staged_text)):
        kept += ["permissionMode: default", "disallowedTools: [Edit, Write, NotebookEdit]"]
    else:
        kept.append("permissionMode: acceptEdits")
    kept.append(f"model: {resolved.model}")
    if resolved.effort is not None:
        kept.append(f"effort: {resolved.effort}")
    return "---\n" + "\n".join(kept) + "\n---\n" + rest


def resolve_codex_agent_model(
    agent_name: str,
    staged_model: object,
    resolved: ResolvedAgentModel | None,
) -> tuple[str, str]:
    """``(model, reasoning_effort)``: resolved policy, else the authored ``model:``, else refuse.

    The effort is the clamped policy effort, else ``medium``.
    """
    effort = resolved.effort if resolved is not None else None
    codex_effort = codex_effort_for_claude_effort(effort) if effort is not None else "medium"
    if resolved is not None:
        return resolved.model, codex_effort
    if staged_model:
        return str(staged_model), codex_effort
    raise PublicAssetError(
        f"cannot render agent '{agent_name}': it has neither an authored 'model:' nor a "
        "resolved agent-model policy model (fail-closed: no default model)"
    )
