from __future__ import annotations

from dadaia_workspace.core.models.hygiene import HygieneCounters
from dadaia_workspace.core.models.lifecycle import LifecyclePhase
from dadaia_workspace.features.lifecycle.service import (
    ActiveReleaseState,
    BoundContext,
    GitPreflightState,
    LifecyclePreflightInput,
    LifecyclePreflightService,
    PresenceState,
    SpecsDoctorState,
)


def test_release_definition_output_feeds_implementation_preflight_with_git_warnings() -> None:
    """Producer-owned definition artifacts do not require a manual clean/push boundary."""
    result = LifecyclePreflightService().preflight(
        LifecyclePreflightInput(
            context="dadaia-workspace",
            release_id="v0.2.5",
            expected_phase=LifecyclePhase.IMPLEMENTATION,
            required_mode="implementation",
            current_step="implementation-preflight",
            binding=BoundContext(
                context="dadaia-workspace",
                release_id="v0.2.5",
                mode="implementation",
                session_id="sess-consumer",
            ),
            active_release=ActiveReleaseState(release_id="v0.2.5", phase="IMPLEMENTATION"),
            git=GitPreflightState(
                dirty_paths=(
                    "specs/releases/v0.2.5/SPEC.md",
                    "specs/releases/v0.2.5/PLAN.md",
                    "specs/releases/v0.2.5/TASKS.md",
                ),
                upstream_branch=None,
                unpushed_commit_count=3,
            ),
            specs_doctor=SpecsDoctorState(ok=True),
            presence=PresenceState(mode="implementation"),
            hygiene=HygieneCounters(),
            required_handoffs=(),
        )
    )

    assert result.ok is True
    assert result.blocked is None
    assert len(result.warnings) == 3
    assert any("dirty worktree is advisory" in warning for warning in result.warnings)
    assert any("missing upstream branch is advisory" in warning for warning in result.warnings)
    assert any("unpushed commits are advisory" in warning for warning in result.warnings)
