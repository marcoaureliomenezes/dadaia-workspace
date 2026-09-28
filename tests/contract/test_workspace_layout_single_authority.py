"""Intent: CONTRACT — core.workspace_layout single authority (bug dadaia-reconcile-quarantines-sanctioned-references-clone; 0.4.6 AC1); size: SMALL.

One authority per filesystem-layout invariant (2026-08-06 analysis). The root whitelist
diverged the day the root `AGENTS.md` map was added to the hook's copy and not the doctor's; the
``.dadaia/`` layout diverged six times as bare name lists (architect G, 0.4.6). These
tests pin that every consumer DERIVES from ``core/workspace_layout.py`` — identity where a
constant is re-exported, equality against the registry view where a consumer derives —
so divergence is unrepresentable. ``tests/contract/test_zone_registry.py`` adds the
package-wide ratchet that no second list can be born.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.contract


_NAME_SETS = frozenset(
    {"ROOT_ALLOWED_DIRS", "ROOT_ALLOWED_FILES", "DADAIA_ROOT_FILES", "STATES_CANON", "zone_names"}
)


@pytest.mark.parametrize("module", ["hooks/root_whitelist.py", "features/spec_context/doctor.py"])
def test_the_gate_and_the_doctor_ask_the_one_verdict(module: str) -> None:
    """sa-gate-allows-root-entries-the-reaper-moves#E9: both call
    ``workspace_layout.verdict`` and read none of the layout name sets themselves."""
    import ast

    source = Path(__file__).resolve().parents[2] / "dadaia_workspace" / module
    tree = ast.parse(source.read_text(encoding="utf-8"))
    attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    assert "verdict" in attrs
    assert (attrs | names) & _NAME_SETS == set()


def test_harness_dirs_derive_from_the_one_harness_registry() -> None:
    """0.4.7 FR3: "which root directory a harness owns" lives once, in
    ``core.harness_registry.HARNESS_PROJECTION_DIRS``. ``HARNESS_DIRS`` is the shared
    ``.agents`` tree plus that registry's values — never a second hand-kept name list,
    and a harness with an empty set (``kimi-code``) contributes nothing."""
    from dadaia_workspace.core import harness_registry, workspace_layout

    assert harness_registry.HARNESS_PROJECTION_DIRS["kimi-code"] == ()
    derived = {".agents"} | {
        d for dirs in harness_registry.HARNESS_PROJECTION_DIRS.values() for d in dirs
    }
    assert derived == workspace_layout.HARNESS_DIRS
    assert ".kimi-code" not in workspace_layout.HARNESS_DIRS


def test_gate_additive_prefixes_are_the_registry_view() -> None:
    """The gate's ``.dadaia/`` ADDITIVE class is the OUTPUT + EPHEMERAL rows of the
    registry (SPEC 0.4.6 FR1, architect A) — ``reports/`` left the class the moment its
    row left the registry, with no gate edit."""
    from dadaia_workspace.core import workspace_layout
    from dadaia_workspace.features.spec_context import gate_policy

    assert workspace_layout.additive_prefixes() == gate_policy._ADDITIVE_DADAIA_PREFIXES
    assert not hasattr(gate_policy, "_SPECS_ADDITIVE_PREFIXES")  # specs: SPECS_ADDITIVE_GLOBS
