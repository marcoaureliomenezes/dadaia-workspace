"""CodexAgentDispatcher — reference-only handoffs for OpenAI Codex runtime."""

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
_SUPPORTED_FEATURES: frozenset[str] = frozenset({"sequential"})

# Features known but explicitly unsupported.
_UNSUPPORTED_FEATURES: frozenset[str] = frozenset({"parallel", "gates_inline"})


def _render(invocation: StageInvocation) -> str:
    """Render an invocation document for the Codex runtime.

    Codex currently has no workflow executor that can spawn project agents.
    These files are manual/reference handoffs only; the operator must run the
    named agent work and place the report at the expected output path.
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
        parts.extend(
            [
                "",
                "> **Note:** Codex reference-only mode does not spawn agents or "
                "execute parallel groups. This stage is part of a parallel_group, "
                "but this dispatcher only wrote a manual handoff file.",
            ]
        )
    parts.extend(["", "## Inputs"])
    if invocation.inputs:
        parts.extend(f"- **{k}**: {v}" for k, v in invocation.inputs.items())
    else:
        parts.append("- (no resolved inputs)")
    if invocation.must_include:
        parts.extend(["", "## Output must include"])
        parts.extend(f"- `{needle}`" for needle in invocation.must_include)
    parts.extend(
        [
            "",
            "## How to execute",
            f"Manually run or copy this handoff to the agent `{invocation.agent}`. "
            "No Codex agent process was spawned by `dadaia orchestrate`. "
            f"Write the output to `{invocation.expected_output_path}`. "
            f"After completion, run `dadaia orchestrate resume {invocation.run_id}` "
            "to advance the run.",
        ]
    )
    return "\n".join(parts) + "\n"


class CodexAgentDispatcher:
    """Dispatcher for OpenAI Codex runtime with reference-only handoff support.

    Codex does not provide this project with a supported workflow executor that can
    spawn named project agents. This dispatcher writes invocation files only. The
    operator must execute the work manually and resume the run after the expected
    report is present.

    Capability matrix:
      - supports_parallel: False  (manual/reference-only; no spawning)
      - supports_gates_inline: False  (gates require CLI confirmation loop)
      - mode: DispatcherMode.CLI_ONLY
    """

    def capabilities(self) -> DispatcherCapabilities:
        return DispatcherCapabilities(
            runtime_name="codex",
            supports_parallel=False,
            supports_gates_inline=False,
            mode=DispatcherMode.CLI_ONLY,
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
            if feature == "parallel":
                raise OrchestrationUnsupportedError(
                    "Codex runtime is reference-only for dadaia workflows and does not "
                    "spawn agents or execute parallel groups. It can write manual handoff "
                    "files; use --runtime claude for supported parallel delegation."
                )
            raise OrchestrationUnsupportedError(
                f"Codex runtime does not support '{feature}'. "
                "Inline gate confirmation requires a CLI operator loop which is unavailable "
                "in the Codex environment. Use --runtime claude for workflows that require "
                "inline gates, or restructure the workflow to avoid gate dependencies."
            )
        raise OrchestrationUnsupportedError(
            f"Codex runtime does not recognise feature '{feature}'. "
            "Known unsupported features: parallel, gates_inline. "
            "Supported features: sequential manual handoff."
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
        path.write_text(_render(invocation), encoding="utf-8")
        return StageResult(
            run_id=invocation.run_id,
            stage_id=invocation.stage_id,
            status=StageStatus.AWAITING_GATE,
            output_path=str(path),
        )

    def dispatch_parallel(
        self, invocations: tuple[StageInvocation, ...]
    ) -> tuple[StageResult, ...]:
        """Write reference handoff files for each invocation.

        Codex does not support agent spawning or native parallel agent dispatch in
        this project. Each invocation is written to disk individually with a note
        explaining the manual/reference-only limitation. No agent execution is
        implied by these results.

        Args:
            invocations: Tuple of :class:`StageInvocation` objects to dispatch.

        Returns:
            A tuple of :class:`StageResult` objects, one per invocation, in the same
            order as the input.
        """
        return tuple(self.dispatch(inv) for inv in invocations)
