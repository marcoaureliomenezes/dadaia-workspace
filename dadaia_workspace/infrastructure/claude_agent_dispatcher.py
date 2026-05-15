"""ClaudeAgentDispatcher — mode=native; prepares invocation.md for host agent to read."""

from pathlib import Path

from dadaia_workspace.core.models.run_state import (
    DispatcherCapabilities,
    DispatcherMode,
    StageInvocation,
    StageResult,
    StageStatus,
)


def _render_invocation(inv: StageInvocation, runtime_label: str) -> str:
    header_lines = [
        f"# Stage invocation — {inv.workflow_name} / {inv.stage_id}",
        "",
        f"- run_id: `{inv.run_id}`",
        f"- agent: `{inv.agent}`",
        f"- runtime: `{runtime_label}`",
        f"- expected_output: `{inv.expected_output_path}`",
    ]
    if inv.parallel_group:
        header_lines.append(
            f"- parallel_group: `{inv.parallel_group}` — "
            "dispatch all members in a single host-agent message"
        )
    header_lines.append("")
    header_lines.append("## Inputs")
    if inv.inputs:
        for k, v in inv.inputs.items():
            header_lines.append(f"- **{k}**: {v}")
    else:
        header_lines.append("- (no resolved inputs)")
    header_lines.append("")
    if inv.must_include:
        header_lines.append("## Output must include")
        for needle in inv.must_include:
            header_lines.append(f"- `{needle}`")
        header_lines.append("")
    header_lines.append("## How to execute")
    header_lines.append(
        f"Invoke the agent `{inv.agent}` using your runtime's native delegation tool. "
        f"Write the output to `{inv.expected_output_path}`. "
        "After completion, run `dadaia orchestrate resume "
        f"{inv.run_id}` to advance the run."
    )
    return "\n".join(header_lines) + "\n"


class ClaudeAgentDispatcher:
    def __init__(self, runtime_label: str = "claude") -> None:
        self._runtime_label = runtime_label

    def capabilities(self) -> DispatcherCapabilities:
        return DispatcherCapabilities(
            runtime_name=self._runtime_label,
            supports_parallel=True,
            supports_gates_inline=False,
            mode=DispatcherMode.NATIVE,
        )

    def dispatch(self, invocation: StageInvocation) -> StageResult:
        path = Path(invocation.invocation_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_render_invocation(invocation, self._runtime_label))
        return StageResult(
            run_id=invocation.run_id,
            stage_id=invocation.stage_id,
            status=StageStatus.AWAITING_GATE,
            output_path=str(path),
        )

    def dispatch_parallel(
        self, invocations: tuple[StageInvocation, ...]
    ) -> tuple[StageResult, ...]:
        return tuple(self.dispatch(inv) for inv in invocations)
