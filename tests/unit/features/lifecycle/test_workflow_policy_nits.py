"""WS-NITS regression tests (T-30-C-05 / A17).

Pins two of the three v0.1.29 code-reviewer nits closed:

  (i)   ``_DEFAULT_PROFILE_BY_HARNESS_PURPOSE`` has ONE home — ``dadaia_catalog`` imports the
        resolver's ``DEFAULT_PROFILE_BY_HARNESS_PURPOSE`` (no second table);
  (iii) the panel ``_semantic_check`` mirrors the WMP doctor's explicit 3-map union, so the
        two agree on a harness-only overlay (no parse-side-effect-only coverage), including
        that a harness-only overlay resolves cleanly (the positive case folded in).

(ii) — the docstring naming ``governed_workflow_catalog`` — is a plain doc grep with no
behavioral surface and is not repeated here.
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.core.models.workflow_execution import (
    DEFAULT_CONTEXT,
    WorkflowModelPolicyOverlay,
)
from dadaia_workspace.features.lifecycle import policy_resolver
from dadaia_workspace.features.lifecycle.policy_doctor import run_policy_doctor
from dadaia_workspace.features.panel.views.workflow_policy import _semantic_check
from dadaia_workspace.features.workflows import dadaia_catalog
from dadaia_workspace.features.workflows.dadaia_catalog import governed_workflow_catalog


def test_default_profile_map_has_one_home() -> None:
    # (i) the catalog binds the resolver's map object — not a copy / second table.
    assert (
        dadaia_catalog.DEFAULT_PROFILE_BY_HARNESS_PURPOSE
        is policy_resolver.DEFAULT_PROFILE_BY_HARNESS_PURPOSE
    )
    # the catalog module no longer defines a private twin.
    assert not hasattr(dadaia_catalog, "_DEFAULT_PROFILE_BY_HARNESS_PURPOSE")


def _harness_only_overlay() -> WorkflowModelPolicyOverlay:
    # A workflow that appears ONLY in the harness maps (no profile-override 'steps' entry).
    return WorkflowModelPolicyOverlay(
        policy_id="default",
        contexts={},
        default_harness_overlay={DEFAULT_CONTEXT: {"implementation": "pi"}},
        step_harness_overlay={DEFAULT_CONTEXT: {"implementation": {"implement": "pi"}}},
    )


def _resolver_factory(catalog):  # type: ignore[no-untyped-def]
    from dadaia_workspace.features.lifecycle.policy_resolver import (
        WorkflowExecutionPolicyResolver,
    )

    def factory(context: str, *, overlay: WorkflowModelPolicyOverlay | None = None):  # type: ignore[no-untyped-def]
        return WorkflowExecutionPolicyResolver(catalog=catalog, overlay=overlay)

    return factory


class _FakeOverlayStore:
    """A WMP-doctor store stand-in returning a fixed in-memory overlay (no disk).

    Implements the full :class:`WorkflowModelPolicyStorePort` surface so it is structurally
    assignable to the injected ``store`` param; the doctor only calls :meth:`load`, so
    :meth:`parse` / :meth:`save` are unreachable stubs.
    """

    def __init__(self, overlay: WorkflowModelPolicyOverlay) -> None:
        self._overlay = overlay

    def load(self) -> WorkflowModelPolicyOverlay:
        return self._overlay

    def parse(self, raw: dict[str, object]) -> WorkflowModelPolicyOverlay:
        raise NotImplementedError  # pragma: no cover - unused by the doctor

    def save(self, overlay: WorkflowModelPolicyOverlay) -> None:
        raise NotImplementedError  # pragma: no cover - unused by the doctor


def test_panel_semantic_check_agrees_with_wmp_doctor_and_covers_harness_only_workflow(
    tmp_path: Path,
) -> None:
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    catalog = governed_workflow_catalog()

    # (iii) positive case: a harness-only overlay names 'implementation' only in the
    # harness maps. The 3-map union means _semantic_check resolves it (and passes — pi is
    # a valid harness for the implement step), proving it does not rely on the contexts
    # map alone.
    valid_overlay = _harness_only_overlay()
    valid_result = _semantic_check(_resolver_factory(catalog), valid_overlay, DEFAULT_CONTEXT)
    assert valid_result is None

    # negative case: an overlay that names an UNKNOWN workflow only in the harness map
    # must be flagged by BOTH the panel _semantic_check and the WMP doctor (agreement, no
    # side-effect gap).
    invalid_overlay = WorkflowModelPolicyOverlay(
        policy_id="default",
        contexts={},
        default_harness_overlay={DEFAULT_CONTEXT: {"no-such-workflow": "pi"}},
    )
    panel_result = _semantic_check(_resolver_factory(catalog), invalid_overlay, DEFAULT_CONTEXT)
    assert panel_result is not None
    assert "no-such-workflow" in str(panel_result)

    # Doctor half: the WMP doctor's _resolve_overlay visits the SAME 3-map union and flags
    # the same workflow. We inject the in-memory overlay via a fake store so both halves see
    # the identical overlay object (the on-disk to_dict round-trip is exercised elsewhere).
    findings = run_policy_doctor(catalog=catalog, store=_FakeOverlayStore(invalid_overlay))
    overlay_findings = [f for f in findings if "no-such-workflow" in f.message]
    assert overlay_findings, f"WMP doctor must also flag the unknown workflow: {findings}"
