"""Every producing create step bundles ``shared.output_handoff`` (v0.1.31 Wave A — T-31-A-07).

GRILL D-2 / SPEC Cluster 2 (C3 / R-B): a real worker is only told to emit its schema'd
payload + artifact refs when its fragment bundle cites the single ``shared.output_handoff``
contract. The producing-step set is **derived programmatically from each workflow's
``_SEQUENCE``** (not a hard-coded list) so the coverage claim cannot drift from the real
library: every non-review create step that produces a payload must carry the contract.

The single-output-handoff-family (no parallel ``create_handoff``) invariant is asserted
directly on the fragment source in ``test_output_handoff_fragment_canonical.py`` (library-wide
grep) — not repeated here.
"""

from __future__ import annotations

from dadaia_workspace.features.lifecycle.workflows.backlog_definition import (
    _SEQUENCE as BACKLOG_SEQUENCE,
)
from dadaia_workspace.features.lifecycle.workflows.backlog_definition import (
    BacklogStepKind,
)
from dadaia_workspace.features.lifecycle.workflows.release_definition import (
    _SEQUENCE as RELEASE_SEQUENCE,
)

_OUTPUT_HANDOFF = "shared.output_handoff"


def _release_producing_create_steps() -> tuple[object, ...]:
    """Non-review release-definition steps that PRODUCE a payload (create steps).

    Derived from ``_SEQUENCE``: a producing create step names a fragment, is not a
    review, and declares a ``produces`` schema. The terminal Python commit gate
    (``fragment_id=None``) and the review steps are excluded.
    """
    return tuple(
        s
        for s in RELEASE_SEQUENCE
        if s.fragment_id is not None and not s.is_review and s.produces is not None
    )


def _backlog_authoring_step() -> object:
    """The backlog authoring MODEL create step — the producing step the gate reads.

    Derived from ``_SEQUENCE``: the MODEL step labelled ``backlog_author`` (the
    ``intake_grill`` / ``conflict_resolution_grill`` MODEL steps are grills, not
    producing create steps).
    """
    return next(
        s
        for s in BACKLOG_SEQUENCE
        if s.kind is BacklogStepKind.MODEL and s.label == "backlog_author"
    )


def test_every_producing_create_step_across_workflows_bundles_output_handoff() -> None:
    # The programmatic derivation must surface exactly the four release-definition
    # producing create steps named in the SPEC, and every one — plus backlog's authoring
    # step — must bundle the single output-handoff contract. release_scope keeps its
    # grill_questionnaire alongside it (not replaced by it).
    labels = {s.label for s in _release_producing_create_steps()}  # type: ignore[attr-defined]
    assert labels == {"release_scope", "spec_create", "plan_create", "tasks_create"}

    for step in _release_producing_create_steps():
        assert _OUTPUT_HANDOFF in step.shared_fragment_ids, (  # type: ignore[attr-defined]
            f"{step.label} must bundle {_OUTPUT_HANDOFF}"  # type: ignore[attr-defined]
        )

    release_scope = next(s for s in RELEASE_SEQUENCE if s.label == "release_scope")
    assert "shared.grill_questionnaire" in release_scope.shared_fragment_ids
    assert _OUTPUT_HANDOFF in release_scope.shared_fragment_ids

    backlog_step = _backlog_authoring_step()
    assert _OUTPUT_HANDOFF in backlog_step.shared_fragment_ids  # type: ignore[attr-defined]
