"""CliAgentDispatcher — default fallback; also covers OpenCode (best-effort) and Codex (unsupported)."""

from pathlib import Path

from dadaia_workspace.core.exceptions import OrchestrationUnsupportedError
from dadaia_workspace.core.models.run_state import (
    DispatcherCapabilities,
    DispatcherMode,
    StageInvocation,
    StageResult,
    StageStatus,
)


def _render(invocation: StageInvocation, runtime_label: str, note: str | None) -> str:
    parts = [
        f"# Stage invocation — {invocation.workflow_name} / {invocation.stage_id}",
        "",
        f"- run_id: `{invocation.run_id}`",
        f"- agent: `{invocation.agent}`",
        f"- runtime: `{runtime_label}`",
        f"- expected_output: `{invocation.expected_output_path}`",
    ]
    if invocation.parallel_group:
        parts.append(f"- parallel_group: `{invocation.parallel_group}`")
    if note:
        parts.extend(["", f"> **Note:** {note}"])
    parts.extend(["", "## Inputs"])
    if invocation.inputs:
        parts.extend(f"- **{k}**: {v}" for k, v in invocation.inputs.items())
    else:
        parts.append("- (no resolved inputs)")
    parts.extend(
        [
            "",
            "## How to execute",
            "This run is in `cli-only` (or best-effort) mode. The operator must execute the "
            f"agent `{invocation.agent}` manually (or via the host runtime), write the result "
            f"to `{invocation.expected_output_path}`, then run "
            f"`dadaia orchestrate resume {invocation.run_id}`.",
        ]
    )
    return "\n".join(parts) + "\n"


class CliAgentDispatcher:
    def __init__(self, runtime_label: str = "cli") -> None:
        self._runtime_label = runtime_label

    def capabilities(self) -> DispatcherCapabilities:
        return DispatcherCapabilities(
            runtime_name=self._runtime_label,
            supports_parallel=False,
            supports_gates_inline=False,
            mode=DispatcherMode.CLI_ONLY,
        )

    def dispatch(self, invocation: StageInvocation) -> StageResult:
        path = Path(invocation.invocation_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_render(invocation, self._runtime_label, None))
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


class OpenCodeAgentDispatcher(CliAgentDispatcher):
    """Best-effort runtime: writes invocation files but signals partial parity for parallel groups."""

    def __init__(self) -> None:
        super().__init__(runtime_label="opencode")

    def capabilities(self) -> DispatcherCapabilities:
        return DispatcherCapabilities(
            runtime_name=self._runtime_label,
            supports_parallel=False,
            supports_gates_inline=False,
            mode=DispatcherMode.BEST_EFFORT_SEQUENTIAL,
        )

    def dispatch(self, invocation: StageInvocation) -> StageResult:
        path = Path(invocation.invocation_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        note = None
        if invocation.parallel_group:
            note = (
                "OpenCode does not support true parallel agent dispatch. "
                "This stage will be executed sequentially within the parallel_group."
            )
        path.write_text(_render(invocation, self._runtime_label, note))
        return StageResult(
            run_id=invocation.run_id,
            stage_id=invocation.stage_id,
            status=StageStatus.AWAITING_GATE,
            output_path=str(path),
        )


class CodexAgentDispatcher(CliAgentDispatcher):
    """Codex has no Agent-style delegation tool; rejects workflows with parallel groups."""

    def __init__(self) -> None:
        super().__init__(runtime_label="codex")

    def capabilities(self) -> DispatcherCapabilities:
        return DispatcherCapabilities(
            runtime_name=self._runtime_label,
            supports_parallel=False,
            supports_gates_inline=False,
            mode=DispatcherMode.UNSUPPORTED,
        )

    def dispatch_parallel(
        self, invocations: tuple[StageInvocation, ...]
    ) -> tuple[StageResult, ...]:
        if any(inv.parallel_group for inv in invocations):
            raise OrchestrationUnsupportedError(
                "runtime 'codex' does not support parallel_group dispatch. "
                "Use --runtime claude or rewrite the workflow without parallel_group."
            )
        return super().dispatch_parallel(invocations)
