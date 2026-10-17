"""Public-doctor model-resolution check: one line naming the applied template."""

from __future__ import annotations

from dadaia_workspace.core.model_registry import DEFAULT_TEMPLATE_ID, AgentModelPolicyOverlay
from dadaia_workspace.core.models.doctor_report import DoctorLine, DoctorStatus


def check_model_resolution(overlay: AgentModelPolicyOverlay | None = None) -> list[DoctorLine]:
    """One ``[ok]`` line naming the template the overlay applies, else the default."""
    applied = (overlay.applied_template if overlay else None) or DEFAULT_TEMPLATE_ID
    return [DoctorLine(DoctorStatus.OK, f"model-resolution: template {applied}")]
