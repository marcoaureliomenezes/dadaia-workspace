"""Intent: CONTRACT — sa-gate-blind-on-cursor-copilot-devin (0.5.0 WP-12, sa-gate-blind-on-cursor-copilot-devin#B7, ADR 0054).

registry.json's sdd-gate implementation for each harness with a rendered hook file names
the pre-action event that file registers for the gate; a dialect declaring an ungated
action is declared "gate not enforced" there — never a coverage claim the render lacks.
Size: SMALL.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.core.harness_registry import HARNESS_RECORDS
from dadaia_workspace.infrastructure.runtime_transforms.hook_wrappers import HOOK_DIALECTS

pytestmark = pytest.mark.contract

_REGISTRY = Path(__file__).resolve().parents[2] / "dadaia_workspace/public/entities/registry.json"


def test_b7_the_registry_states_what_each_rendered_gate_is() -> None:
    rules = json.loads(_REGISTRY.read_text(encoding="utf-8"))["behaviors"]
    claims = next(r for r in rules if r["id"] == "sdd-gate")["implementations"]
    for name, record in HARNESS_RECORDS.items():
        dialect = HOOK_DIALECTS[record.hooks]
        gate_events = {e for f in dialect.files for e, lane, _ in f.events if lane == "pre-gate"}
        for event in gate_events:
            assert event in claims[name], (name, event)
        assert ("gate not enforced" in claims[name]) is bool(dialect.ungated), name
