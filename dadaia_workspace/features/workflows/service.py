"""WorkflowsService — features/workflows/service.py.

Wraps MarkdownWorkflowStore and provides DTO-mapped list + detail accessors
with a per-process in-memory mtime cache.

Cache keyed by (path, mtime, size); cache size bounded by file count in source
dir; ETag header is P2 follow-up.
"""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from dadaia_workspace.features.workflows.dadaia_catalog import DadaiaWorkflowDTO

from dadaia_workspace.core.models.workflow import (
    WorkflowSummaryDTO as WorkflowSummaryDTO,  # re-export
)
from dadaia_workspace.features.workflows.dag import render_dag_svg
from dadaia_workspace.infrastructure.markdown_workflow_store import MarkdownWorkflowStore

logger = logging.getLogger(__name__)

# Cache key: (absolute path str, mtime float, size int) → WorkflowDetailDTO
_CacheKey = tuple[str, float, int]
_cache: dict[_CacheKey, "WorkflowDetailDTO"] = {}

# Resolution order for workflows directory (mirrors agents reader pattern):
#   1. $DADAIA_WORKFLOWS_DIR env var
#   2. <workspace_root>/.dadaia/agentic/workflows/
#   3. <workspace_root>/.claude/workflows/
_SUFFIX = ".workflow.md"


def _resolve_workflows_dir(workspace_root: Path) -> Path | None:
    env_dir = os.environ.get("DADAIA_WORKFLOWS_DIR")
    if env_dir:
        logger.debug("workflow_service: using DADAIA_WORKFLOWS_DIR=%s", env_dir)
        return Path(env_dir)

    agentic = workspace_root / ".dadaia" / "agentic" / "workflows"
    if agentic.exists() and any(agentic.glob(f"*{_SUFFIX}")):
        logger.debug("workflow_service: using .dadaia/agentic/workflows/")
        return agentic

    claude = workspace_root / ".claude" / "workflows"
    if claude.exists() and any(claude.glob(f"*{_SUFFIX}")):
        logger.debug("workflow_service: using .claude/workflows/")
        return claude

    logger.debug("workflow_service: no workflows directory found under %s", workspace_root)
    return None


# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------


@dataclass
class StageDTO:
    id: str
    agent: str
    needs: list[str]
    parallel_group: str | None
    gate: bool
    expected_output_path: str | None
    must_include: list[str] | None
    on_failure: str


@dataclass
class WorkflowDetailDTO:
    name: str
    display_name: str
    description: str
    version: str
    schema_version: str
    stage_count: int
    agent_ids: list[str]
    has_parallel: bool
    has_gates: bool
    source_path: str
    inputs: list[dict[str, Any]]
    stages: list[StageDTO]
    lifecycle_phase: str = "Unmapped"
    diagram_svg: str = field(default="")


# ---------------------------------------------------------------------------
# DTO mapping helpers
# ---------------------------------------------------------------------------


def _stage_to_dto(stage: Any) -> StageDTO:  # noqa: ANN401
    return StageDTO(
        id=stage.id,
        agent=stage.agent,
        needs=list(stage.needs),
        parallel_group=stage.parallel_group,
        gate=stage.gate is not None,
        expected_output_path=stage.expected_output.path if stage.expected_output else None,
        must_include=list(stage.expected_output.must_include) if stage.expected_output else None,
        on_failure=stage.on_failure,
    )


def _agent_ids(stages: Any) -> list[str]:  # noqa: ANN401
    seen: dict[str, None] = {}
    for s in stages:
        seen[s.agent] = None
    return list(seen)


def _source_path(workflows_dir: Path, name: str) -> str:
    return str(workflows_dir / f"{name}{_SUFFIX}")


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------


def _cache_key(path: Path) -> _CacheKey | None:
    try:
        stat = path.stat()
        return (str(path), stat.st_mtime, stat.st_size)
    except OSError:
        return None


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class WorkflowsService:
    """Wraps MarkdownWorkflowStore; provides list_summaries() and get_detail().

    Per-process in-memory cache keyed by (path, mtime, size).
    """

    def __init__(self, workspace_root: Path) -> None:
        self._workspace_root = workspace_root
        self._workflows_dir: Path | None = None
        self._store: MarkdownWorkflowStore | None = None

    def _ensure_store(self) -> tuple[Path, MarkdownWorkflowStore] | None:
        workflows_dir = _resolve_workflows_dir(self._workspace_root)
        if workflows_dir is None:
            return None
        if self._workflows_dir != workflows_dir:
            self._workflows_dir = workflows_dir
            self._store = MarkdownWorkflowStore(workflows_dir)
        assert self._store is not None
        return workflows_dir, self._store

    def list_summaries(self) -> list[WorkflowSummaryDTO]:
        result = self._ensure_store()
        if result is None:
            return []
        workflows_dir, store = result
        summaries: list[WorkflowSummaryDTO] = []
        for wf in store.list():
            source_file = workflows_dir / f"{wf.name}{_SUFFIX}"
            summaries.append(
                WorkflowSummaryDTO(
                    name=wf.name,
                    display_name=wf.name,
                    description=wf.description,
                    version=wf.version,
                    schema_version=wf.schema_version,
                    stage_count=len(wf.stages),
                    agent_ids=_agent_ids(wf.stages),
                    has_parallel=any(s.parallel_group for s in wf.stages),
                    has_gates=any(s.gate is not None for s in wf.stages),
                    source_path=str(source_file),
                    lifecycle_phase=wf.lifecycle_phase,
                )
            )
        return summaries

    # -- dadaia-workflow catalog (WS-8 / ADR-E) --------------------------
    #
    # The methods below describe the *real* Python-owned dadaia-workflows
    # (release_definition, implementation, deferred) — purpose, per-step
    # harness/model options, availability, and a server-rendered SVG + Mermaid
    # diagram — for the panel catalog. They are wholly additive: the legacy
    # ``*.workflow.md`` accessors above (``list_summaries`` / ``get_detail``)
    # are untouched. The catalog is pure data assembly over the authoritative
    # workflow definitions, so it needs neither the markdown store nor a
    # workspace-root resolution.

    def list_dadaia_workflows(self) -> list["DadaiaWorkflowDTO"]:
        """Return every dadaia-workflow, fully described, in catalog order."""
        from dadaia_workspace.features.workflows.dadaia_catalog import list_dadaia_workflows

        return list_dadaia_workflows()

    def get_dadaia_workflow(self, name: str) -> "DadaiaWorkflowDTO | None":
        """Return one fully-described dadaia-workflow by name, or ``None``."""
        from dadaia_workspace.features.workflows.dadaia_catalog import get_dadaia_workflow

        return get_dadaia_workflow(name)

    def get_detail(self, name: str) -> "WorkflowDetailDTO | None":
        result = self._ensure_store()
        if result is None:
            return None
        workflows_dir, store = result
        source_file = workflows_dir / f"{name}{_SUFFIX}"

        # Check cache
        key = _cache_key(source_file)
        if key is not None and key in _cache:
            logger.debug("workflow_service: cache hit for %s", name)
            return _cache[key]

        # Evict stale entry for this path if any key matches the path
        stale = [k for k in list(_cache) if k[0] == str(source_file)]
        for k in stale:
            del _cache[k]

        try:
            wf = store.get(name)
        except Exception:
            logger.debug("workflow_service: workflow not found: %s", name)
            return None

        inputs_list: list[dict[str, Any]] = [
            {
                "name": inp.name,
                "type": inp.type,
                "required": inp.required,
                "description": inp.description,
                "default": inp.default,
            }
            for inp in wf.inputs
        ]
        stage_dtos = [_stage_to_dto(s) for s in wf.stages]
        diagram = render_dag_svg(stage_dtos)
        dto = WorkflowDetailDTO(
            name=wf.name,
            display_name=wf.name,
            description=wf.description,
            version=wf.version,
            schema_version=wf.schema_version,
            stage_count=len(wf.stages),
            agent_ids=_agent_ids(wf.stages),
            has_parallel=any(s.parallel_group for s in wf.stages),
            has_gates=any(s.gate is not None for s in wf.stages),
            source_path=str(source_file),
            inputs=inputs_list,
            stages=stage_dtos,
            lifecycle_phase=wf.lifecycle_phase,
            diagram_svg=diagram,  # server-rendered SVG from dag.py (PR3-13)
        )

        if key is not None:
            _cache[key] = dto
        return dto
