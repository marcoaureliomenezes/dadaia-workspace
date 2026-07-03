"""WS-NITS regression tests (T-30-C-05 / A17).

Pins the three v0.1.29 code-reviewer nits closed:

  (i)   ``_DEFAULT_PROFILE_BY_HARNESS_PURPOSE`` has ONE home — ``dadaia_catalog`` imports the
        resolver's ``DEFAULT_PROFILE_BY_HARNESS_PURPOSE`` (no second table);
  (ii)  the ``policy_resolver`` module docstring names ``governed_workflow_catalog`` as the
        production resolver source;
  (iii) the panel ``_semantic_check`` mirrors the WMP doctor's explicit 3-map union, so the
        two agree on a harness-only overlay (no parse-side-effect-only coverage).
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


def test_resolver_docstring_names_governed_catalog() -> None:
    # (ii) the production resolver source is documented as governed_workflow_catalog.
    doc = policy_resolver.__doc__ or ""
    assert "governed_workflow_catalog" in doc


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


def test_semantic_check_covers_harness_only_workflow() -> None:
    # (iii) a harness-only overlay names 'implementation' only in the harness maps. The
    # 3-map union means _semantic_check resolves it (and passes — pi is a valid harness for
    # the implement step), proving it does not rely on the contexts map alone.
    catalog = governed_workflow_catalog()
    overlay = _harness_only_overlay()
    result = _semantic_check(_resolver_factory(catalog), overlay, DEFAULT_CONTEXT)
    # pi default_harness + pi implement harness resolves cleanly (pi profiles exist).
    assert result is None


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


def test_semantic_check_agrees_with_wmp_doctor_on_invalid_harness_only_overlay(
    tmp_path: Path,
) -> None:
    # An overlay that names an UNKNOWN workflow only in the harness map must be flagged by
    # BOTH the panel _semantic_check and the WMP doctor (agreement, no side-effect gap).
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    overlay = WorkflowModelPolicyOverlay(
        policy_id="default",
        contexts={},
        default_harness_overlay={DEFAULT_CONTEXT: {"no-such-workflow": "pi"}},
    )
    catalog = governed_workflow_catalog()

    # Panel half: _semantic_check now visits the harness-map workflow and flags it.
    panel_result = _semantic_check(_resolver_factory(catalog), overlay, DEFAULT_CONTEXT)
    assert panel_result is not None
    assert "no-such-workflow" in str(panel_result)

    # Doctor half: the WMP doctor's _resolve_overlay visits the SAME 3-map union and flags
    # the same workflow. We inject the in-memory overlay via a fake store so both halves see
    # the identical overlay object (the on-disk to_dict round-trip is exercised elsewhere).
    findings = run_policy_doctor(catalog=catalog, store=_FakeOverlayStore(overlay))
    overlay_findings = [f for f in findings if "no-such-workflow" in f.message]
    assert overlay_findings, f"WMP doctor must also flag the unknown workflow: {findings}"
