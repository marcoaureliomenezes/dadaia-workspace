"""Every producing create step bundles ``shared.output_handoff`` (v0.1.31 Wave A — T-31-A-07).

GRILL D-2 / SPEC Cluster 2 (C3 / R-B): a real worker is only told to emit its schema'd
payload + artifact refs when its fragment bundle cites the single ``shared.output_handoff``
contract. The producing-step set is **derived programmatically from each workflow's
``_SEQUENCE``** (not a hard-coded list) so the coverage claim cannot drift from the real
library: every non-review create step that produces a payload must carry the contract.

There is exactly ONE output-handoff fragment family — no parallel ``create_handoff``
fragment (D-2).

RED today: ``release_scope`` bundles only ``shared.grill_questionnaire`` and
``plan_create`` / ``tasks_create`` / ``backlog_author`` bundle no output contract.
``spec_create`` already carries it.
"""

from __future__ import annotations

from dadaia_workspace.features.lifecycle.fragments.loader import list_fragments
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


def test_release_producing_create_steps_cover_the_expected_labels() -> None:
    # The programmatic derivation must surface exactly the four release-definition
    # producing create steps named in the SPEC.
    labels = {s.label for s in _release_producing_create_steps()}  # type: ignore[attr-defined]
    assert labels == {"release_scope", "spec_create", "plan_create", "tasks_create"}


def test_every_release_producing_create_step_bundles_output_handoff() -> None:
    for step in _release_producing_create_steps():
        assert _OUTPUT_HANDOFF in step.shared_fragment_ids, (  # type: ignore[attr-defined]
            f"{step.label} must bundle {_OUTPUT_HANDOFF}"  # type: ignore[attr-defined]
        )


def test_release_scope_keeps_its_grill_questionnaire_alongside_output_handoff() -> None:
    release_scope = next(s for s in RELEASE_SEQUENCE if s.label == "release_scope")
    assert "shared.grill_questionnaire" in release_scope.shared_fragment_ids
    assert _OUTPUT_HANDOFF in release_scope.shared_fragment_ids


def test_backlog_author_bundles_output_handoff() -> None:
    step = _backlog_authoring_step()
    assert _OUTPUT_HANDOFF in step.shared_fragment_ids  # type: ignore[attr-defined]


def test_single_output_handoff_fragment_family_no_create_handoff() -> None:
    # D-2 / A10: there is exactly ONE output-handoff fragment family and NO parallel
    # ``create_handoff`` fragment.
    fragment_ids = {f.id for f in list_fragments()}
    assert _OUTPUT_HANDOFF in fragment_ids
    create_handoff = {fid for fid in fragment_ids if "create_handoff" in fid}
    assert create_handoff == set(), f"unexpected create_handoff fragment(s): {create_handoff}"
