"""MarkdownWorkflowStore — reads and validates *.workflow.md files."""

import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import yaml

from dadaia_workspace.core.exceptions import (
    WorkflowCycleError,
    WorkflowNotFoundError,
    WorkflowSchemaError,
)
from dadaia_workspace.core.models.workflow import (
    ExitCriterion,
    StageExpectedOutput,
    StageGate,
    StageInputBinding,
    WorkflowDefinition,
    WorkflowInput,
    WorkflowStage,
)

_FRONTMATTER_DELIM = "---"
_SUFFIX = ".workflow.md"
_AGENT_PLACEHOLDER_RE = re.compile(r"^\{\{\s*([a-zA-Z_][a-zA-Z_0-9]*)\s*\}\}$")


def _split_frontmatter(text: str) -> str:
    lines = text.splitlines()
    if not lines or lines[0].strip() != _FRONTMATTER_DELIM:
        raise WorkflowSchemaError("workflow file is missing YAML frontmatter delimiter")
    buffer: list[str] = []
    for line in lines[1:]:
        if line.strip() == _FRONTMATTER_DELIM:
            return "\n".join(buffer)
        buffer.append(line)
    raise WorkflowSchemaError("workflow frontmatter is not closed by a second '---' line")


def _coerce_inputs(raw: Any, workflow_name: str) -> tuple[WorkflowInput, ...]:  # noqa: ANN401
    if raw is None:
        return ()
    if not isinstance(raw, dict):
        raise WorkflowSchemaError(f"{workflow_name}: 'inputs' must be a mapping")
    items: list[WorkflowInput] = []
    for name, spec in raw.items():
        if not isinstance(spec, dict):
            raise WorkflowSchemaError(f"{workflow_name}.inputs.{name}: must be a mapping")
        required = bool(spec.get("required", False))
        default = spec.get("default")
        if not required and default is None and "default" not in spec:
            raise WorkflowSchemaError(
                f"{workflow_name}.inputs.{name}: optional inputs must declare 'default'"
            )
        items.append(
            WorkflowInput(
                name=name,
                type=str(spec.get("type", "string")),
                required=required,
                description=spec.get("description"),
                default=None if default is None else str(default),
            )
        )
    return tuple(items)


def _coerce_stage(raw: Any, workflow_name: str) -> WorkflowStage:  # noqa: ANN401
    if not isinstance(raw, dict):
        raise WorkflowSchemaError(f"{workflow_name}: each stage must be a mapping")
    stage_id = raw.get("id")
    agent = raw.get("agent")
    expected = raw.get("expected_output")
    if not stage_id or not isinstance(stage_id, str):
        raise WorkflowSchemaError(f"{workflow_name}: stage missing 'id'")
    if not agent or not isinstance(agent, str):
        raise WorkflowSchemaError(f"{workflow_name}.{stage_id}: stage missing 'agent'")
    if not isinstance(expected, dict) or "path" not in expected:
        raise WorkflowSchemaError(
            f"{workflow_name}.{stage_id}: stage missing 'expected_output.path'"
        )

    needs = tuple(raw.get("needs") or ())
    parallel_group = raw.get("parallel_group")
    inputs = tuple(
        StageInputBinding(
            kind=str(b.get("kind", "literal")),
            from_ref=str(b.get("from", "")),
            as_name=str(b.get("as", "")),
        )
        for b in (raw.get("inputs") or [])
    )
    gate_raw = raw.get("gate")
    gate = (
        StageGate(kind=str(gate_raw["kind"]), prompt=str(gate_raw.get("prompt", "")))
        if isinstance(gate_raw, dict)
        else None
    )
    must_include = tuple(expected.get("must_include") or ())
    return WorkflowStage(
        id=stage_id,
        agent=agent,
        expected_output=StageExpectedOutput(path=str(expected["path"]), must_include=must_include),
        needs=tuple(str(n) for n in needs),
        parallel_group=str(parallel_group) if parallel_group else None,
        inputs=inputs,
        gate=gate,
        on_failure=str(raw.get("on_failure", "stop")),
    )


def _coerce_exit_criteria(raw: Any) -> tuple[ExitCriterion, ...]:  # noqa: ANN401
    if not raw:
        return ()
    out: list[ExitCriterion] = []
    for item in raw:
        if not isinstance(item, dict) or len(item) != 1:
            raise WorkflowSchemaError("exit_criteria entries must be single-key mappings")
        ((kind, value),) = item.items()
        out.append(ExitCriterion(kind=str(kind), value=str(value)))
    return tuple(out)


def _topo_sort(stages: tuple[WorkflowStage, ...]) -> tuple[str, ...]:
    ids = {s.id for s in stages}
    indeg: dict[str, int] = {s.id: 0 for s in stages}
    edges: dict[str, list[str]] = {s.id: [] for s in stages}
    for s in stages:
        for dep in s.needs:
            if dep not in ids:
                raise WorkflowSchemaError(
                    f"stage '{s.id}' needs '{dep}' which is not a known stage"
                )
            edges[dep].append(s.id)
            indeg[s.id] += 1
    queue = [sid for sid, d in indeg.items() if d == 0]
    order: list[str] = []
    while queue:
        node = queue.pop(0)
        order.append(node)
        for nxt in edges[node]:
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                queue.append(nxt)
    if len(order) != len(stages):
        remaining = [sid for sid, d in indeg.items() if d > 0]
        raise WorkflowCycleError(f"workflow has cyclic dependencies among stages: {remaining}")
    return tuple(order)


def _validate_parallel_groups(stages: tuple[WorkflowStage, ...]) -> None:
    by_group: dict[str, list[WorkflowStage]] = {}
    for s in stages:
        if s.parallel_group:
            by_group.setdefault(s.parallel_group, []).append(s)
    for group, members in by_group.items():
        member_ids = {s.id for s in members}
        for m in members:
            internal = [d for d in m.needs if d in member_ids]
            if internal:
                raise WorkflowSchemaError(
                    f"parallel_group '{group}' member '{m.id}' depends on group siblings: {internal}"
                )
            if m.gate is not None:
                raise WorkflowSchemaError(
                    f"parallel_group '{group}' member '{m.id}' cannot declare a 'gate' "
                    "(would deadlock the parallel batch)"
                )


def _parse(text: str, filename: str, agent_catalog: Iterable[str] | None) -> WorkflowDefinition:
    frontmatter = _split_frontmatter(text)
    try:
        data = yaml.safe_load(frontmatter)
    except yaml.YAMLError as e:
        raise WorkflowSchemaError(f"invalid YAML in {filename}: {e}") from e
    if not isinstance(data, dict):
        raise WorkflowSchemaError(f"{filename}: frontmatter must be a YAML mapping")

    name = data.get("name")
    if not name or not isinstance(name, str):
        raise WorkflowSchemaError(f"{filename}: missing 'name'")
    expected_stem = filename.removesuffix(_SUFFIX)
    if expected_stem.lower() != name.lower():
        raise WorkflowSchemaError(
            f"{filename}: filename stem '{expected_stem}' does not match name '{name}'"
        )
    stages_raw = data.get("stages")
    if not stages_raw or not isinstance(stages_raw, list):
        raise WorkflowSchemaError(f"{name}: 'stages' must be a non-empty list")
    stages = tuple(_coerce_stage(s, name) for s in stages_raw)
    inputs = _coerce_inputs(data.get("inputs"), name)

    seen: set[str] = set()
    for s in stages:
        if s.id in seen:
            raise WorkflowSchemaError(f"{name}: duplicate stage id '{s.id}'")
        seen.add(s.id)

    input_names = {i.name for i in inputs}
    if agent_catalog is not None:
        catalog = set(agent_catalog)
        for s in stages:
            placeholder = _AGENT_PLACEHOLDER_RE.match(s.agent)
            if placeholder:
                ref = placeholder.group(1)
                if ref not in input_names:
                    raise WorkflowSchemaError(
                        f"{name}.{s.id}: agent placeholder '{{{{{ref}}}}}' references "
                        f"unknown input — declare it under 'inputs'"
                    )
                continue
            if s.agent not in catalog:
                raise WorkflowSchemaError(
                    f"{name}.{s.id}: agent '{s.agent}' not present in public/agents/"
                )

    _topo_sort(stages)
    _validate_parallel_groups(stages)

    return WorkflowDefinition(
        name=name,
        description=str(data.get("description", "")),
        version=str(data.get("version", "0.0.0")),
        schema_version=str(data.get("schema_version", "1")),
        inputs=inputs,
        stages=stages,
        exit_criteria=_coerce_exit_criteria(data.get("exit_criteria")),
    )


class MarkdownWorkflowStore:
    def __init__(self, workflows_dir: Path, agent_catalog: Iterable[str] | None = None) -> None:
        self._dir = workflows_dir
        self._agent_catalog = tuple(agent_catalog) if agent_catalog is not None else None

    def _files(self) -> list[Path]:
        if not self._dir.exists():
            return []
        return sorted(self._dir.glob(f"*{_SUFFIX}"))

    def list(self) -> tuple[WorkflowDefinition, ...]:
        seen: dict[str, WorkflowDefinition] = {}
        for path in self._files():
            wf = _parse(path.read_text(encoding="utf-8"), path.name, self._agent_catalog)
            if wf.name in seen:
                raise WorkflowSchemaError(f"duplicate workflow name '{wf.name}'")
            seen[wf.name] = wf
        return tuple(seen.values())

    def get(self, name: str) -> WorkflowDefinition:
        for wf in self.list():
            if wf.name == name:
                return wf
        raise WorkflowNotFoundError(f"workflow '{name}' not found. Use `dadaia orchestrate list`.")

    def validate(self, name: str) -> tuple[str, ...]:
        try:
            self.get(name)
        except WorkflowSchemaError as e:
            return (str(e),)
        return ()
