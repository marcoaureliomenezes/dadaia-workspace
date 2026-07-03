"""Golden byte-identical guard for the FR2 governed-catalog seam split (T-54-11, AC-2).

v0.1.54 FR2 extracted the governed catalog assembly out of
``features/workflows/dadaia_catalog`` into ``features/lifecycle/governed_catalog`` to break
the ``workflows <-> lifecycle`` import cycle. The refactor MUST be behavior-preserving: the
public accessor :func:`list_dadaia_workflows` (and every workflow's server-rendered diagram
SVG) has to serialize **byte-identically** to the pre-split tree.

The golden fixture ``_golden/dadaia_catalog_v0154.json`` was captured from
``list_dadaia_workflows()`` on the pre-refactor tree (the commit before the seam split). This
test re-serializes the *current* output the exact same way and asserts it equals the golden
byte-for-byte — a wrong split (dropped step, altered purpose copy, changed SVG) fails loudly.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from dadaia_workspace.features.workflows.dadaia_catalog import list_dadaia_workflows

pytestmark = pytest.mark.unit

_GOLDEN = Path(__file__).with_name("_golden") / "dadaia_catalog_v0154.json"


def _current_payload() -> dict[str, object]:
    """Serialize the current catalog output identically to the pre-refactor capture."""
    workflows = [dataclasses.asdict(w) for w in list_dadaia_workflows()]
    detail_svgs = {w["name"]: w["diagram_svg"] for w in workflows}
    return {"list": workflows, "detail_svgs": detail_svgs}


def test_list_dadaia_workflows_is_byte_identical_to_pre_split_golden() -> None:
    """The seam split preserves list_dadaia_workflows() output + diagram SVG byte-for-byte."""
    golden_text = _GOLDEN.read_text(encoding="utf-8")
    current_text = json.dumps(_current_payload(), sort_keys=True, indent=2)
    assert current_text == golden_text, (
        "list_dadaia_workflows() output diverged from the pre-FR2-split golden fixture — the "
        "governed_catalog seam extraction changed observable catalog behavior."
    )


def test_golden_covers_every_workflow_diagram_svg() -> None:
    """Sanity: the golden pins a non-empty diagram SVG for every rendered workflow.

    Guards against a golden that silently captured empty SVGs (which would make the
    byte-identity assertion vacuous for the diagram path AC-2 explicitly names).
    """
    golden = json.loads(_GOLDEN.read_text(encoding="utf-8"))
    svgs = golden["detail_svgs"]
    assert svgs, "golden fixture carries no diagram SVGs"
    for name, svg in svgs.items():
        assert svg.startswith("<svg"), f"golden diagram SVG for {name} is not real SVG markup"
