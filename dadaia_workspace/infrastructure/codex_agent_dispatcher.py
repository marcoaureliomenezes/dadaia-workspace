"""CodexAgentDispatcher — best-effort parallel dispatch for OpenAI Codex runtime."""

from pathlib import Path

from dadaia_workspace.core.exceptions import OrchestrationUnsupportedError
from dadaia_workspace.core.models.run_state import (
    DispatcherCapabilities,
    DispatcherMode,
    StageInvocation,
    StageResult,
    StageStatus,
)

# Features supported by this dispatcher.
_SUPPORTED_FEATURES: frozenset[str] = frozenset({"parallel", "sequential"})

# Features known but explicitly unsupported.
_UNSUPPORTED_FEATURES: frozenset[str] = frozenset({"gates_inline"})


def _render(invocation: StageInvocation) -> str:
    """Render an invocation document for the Codex runtime.

    When ``invocation.parallel_group`` is set, a note is appended explaining that
    Codex dispatches in best-effort mode using subagent tooling rather than native
    parallel dispatch.
    """
    parts = [
        f"# Stage invocation — {invocation.workflow_name} / {invocation.stage_id}",
        "",
        f"- run_id: `{invocation.run_id}`",
        f"- agent: `{invocation.agent}`",
        "- runtime: `codex`",
        f"- expected_output: `{invocation.expected_output_path}`",
    ]
    if invocation.parallel_group:
        parts.append(f"- parallel_group: `{invocation.parallel_group}`")
        parts.extend([
            "",
            "> **Note:** Codex best-effort parallel — subagent tool used instead of native "
            "parallel dispatch. This stage is part of a parallel_group but will be executed "
            "sequentially within this runtime.",
        ])
    parts.extend(["", "## Inputs"])
    if invocation.inputs:
        parts.extend(f"- **{k}**: {v}" for k, v in invocation.inputs.items())
    else:
        parts.append("- (no resolved inputs)")
    if invocation.must_include:
        parts.extend(["", "## Output must include"])
        parts.extend(f"- `{needle}`" for needle in invocation.must_include)
    parts.extend([
        "",
        "## How to execute",
        f"Invoke the agent `{invocation.agent}` using the Codex subagent tool. "
        f"Write the output to `{invocation.expected_output_path}`. "
        f"After completion, run `dadaia orchestrate resume {invocation.run_id}` "
        "to advance the run.",
    ])
    return "\n".join(parts) + "\n"


class CodexAgentDispatcher:
    """Dispatcher for OpenAI Codex runtime with best-effort parallel support.

    Codex does not provide a native parallel agent dispatch mechanism equivalent to
    Claude's Agent tool.  This dispatcher emulates parallelism by dispatching each
    invocation sequentially and recording a best-effort note in each invocation file.

    Capability matrix (ADR-3):
      - supports_parallel: True  (best-effort via subagent; not native)
      - supports_gates_inline: False  (gates require CLI confirmation loop)
      - mode: DispatcherMode.CODEX
    """

    def capabilities(self) -> DispatcherCapabilities:
        return DispatcherCapabilities(
            runtime_name="codex",
            supports_parallel=True,
            supports_gates_inline=False,
            mode=DispatcherMode.CODEX,
        )

    def check_capability(self, feature: str) -> None:
        """Assert that *feature* is supported by this dispatcher.

        Raises:
            OrchestrationUnsupportedError: When *feature* is explicitly unsupported or
                not recognised, with a human-readable message explaining the gap.
        """
        if feature in _SUPPORTED_FEATURES:
            return
        if feature in _UNSUPPORTED_FEATURES:
            raise OrchestrationUnsupportedError(
                f"Codex runtime does not support '{feature}'. "
                "Inline gate confirmation requires a CLI operator loop which is unavailable "
                "in the Codex environment. Use --runtime claude for workflows that require "
                "inline gates, or restructure the workflow to avoid gate dependencies."
            )
        raise OrchestrationUnsupportedError(
            f"Codex runtime does not recognise feature '{feature}'. "
            "Known unsupported features: gates_inline. "
            "Supported features: parallel (best-effort), sequential."
        )

    def dispatch(self, invocation: StageInvocation) -> StageResult:
        """Write the invocation file and return a result with status AWAITING_GATE.

        Args:
            invocation: The stage invocation descriptor.

        Returns:
            A :class:`StageResult` with ``status=AWAITING_GATE`` and the written path.
        """
        path = Path(invocation.invocation_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_render(invocation))
        return StageResult(
            run_id=invocation.run_id,
            stage_id=invocation.stage_id,
            status=StageStatus.AWAITING_GATE,
            output_path=str(path),
        )

    def dispatch_parallel(
        self, invocations: tuple[StageInvocation, ...]
    ) -> tuple[StageResult, ...]:
        """Dispatch all invocations sequentially (best-effort parallel).

        Codex does not support native parallel agent dispatch.  Each invocation is
        written to disk individually with a note explaining the best-effort limitation.
        This satisfies AC5: fan-out is attempted; no ``OrchestrationUnsupportedError``
        is raised.

        Args:
            invocations: Tuple of :class:`StageInvocation` objects to dispatch.

        Returns:
            A tuple of :class:`StageResult` objects, one per invocation, in the same
            order as the input.
        """
        return tuple(self.dispatch(inv) for inv in invocations)
