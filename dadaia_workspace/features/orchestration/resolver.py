"""InputResolver — pure function mapping (workflow inputs + run state) to stage inputs."""

from dadaia_workspace.core.exceptions import WorkflowSchemaError
from dadaia_workspace.core.models.run_state import RunManifest
from dadaia_workspace.core.models.workflow import WorkflowDefinition, WorkflowStage


def resolve_stage_inputs(
    workflow: WorkflowDefinition,
    manifest: RunManifest,
    stage: WorkflowStage,
) -> dict[str, str]:
    """Return the concrete inputs delivered to `stage`. Pure: same args ⇒ same result."""
    out: dict[str, str] = {}
    workflow_inputs = {**manifest.inputs}
    for wf_in in workflow.inputs:
        if wf_in.name not in workflow_inputs and wf_in.default is not None:
            workflow_inputs[wf_in.name] = wf_in.default

    stage_outputs = {s.id: s.output_path for s in manifest.stages if s.output_path}

    for binding in stage.inputs:
        if binding.kind == "workflow_input":
            key = binding.from_ref.removeprefix("$.inputs.")
            if key not in workflow_inputs:
                raise WorkflowSchemaError(
                    f"stage '{stage.id}' references missing workflow input '{key}'"
                )
            out[binding.as_name] = workflow_inputs[key]
        elif binding.kind == "stage_output":
            ref = binding.from_ref.removeprefix("stages.").removesuffix(".output")
            if ref not in stage_outputs:
                raise WorkflowSchemaError(
                    f"stage '{stage.id}' references output of '{ref}' which has not run yet"
                )
            out[binding.as_name] = stage_outputs[ref] or ""
        elif binding.kind in {"path", "literal"}:
            out[binding.as_name] = binding.from_ref
        else:
            raise WorkflowSchemaError(
                f"stage '{stage.id}' uses unknown input kind '{binding.kind}'"
            )
    return out


def render_output_path(
    template: str,
    *,
    run_id: str,
    context: str,
    run_ts: str,
    extra: dict[str, str] | None = None,
) -> str:
    result = (
        template.replace("{run_id}", run_id)
        .replace("{context}", context)
        .replace("{run_ts}", run_ts)
    )
    if extra:
        for key, value in extra.items():
            result = result.replace(f"{{{key}}}", value)
    return result
