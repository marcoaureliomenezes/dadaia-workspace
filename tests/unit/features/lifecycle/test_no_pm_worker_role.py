"""T-44-8 — no worker step (fragment-layer OR catalog-layer) binds role=project-manager.

``project-manager`` is the Layer-1 orchestrator, never a Layer-2 worker persona (D-1).
After the v0.1.44 reassignment, neither a fragment frontmatter ``role:`` nor a workflow
catalog / pipeline step's ``role`` may name it (``role: shared`` and ``role: python`` are
not worker personas and are excluded).
"""

from __future__ import annotations

import re
from pathlib import Path

from dadaia_workspace.core.models.lifecycle import AgentRuntimeKind
from dadaia_workspace.features.lifecycle import pipeline
from dadaia_workspace.features.lifecycle.workflows import (
    audit,
    backlog_definition,
    bug_report,
    release_definition,
    research,
)

_FRAGMENT_ROOT = (
    Path(__file__).resolve().parents[4] / "dadaia_workspace" / "public" / "lifecycle_fragments"
)

_SEQUENCES = {
    "release_definition": release_definition._SEQUENCE,
    "audit": audit._SEQUENCE,
    "bug_report": bug_report._SEQUENCE,
    "research": research._SEQUENCE,
    "backlog_definition": backlog_definition._SEQUENCE,
    "pipeline": pipeline.implementation_ladder(AgentRuntimeKind.FAKE),
}


def test_no_non_shared_fragment_role_is_project_manager() -> None:
    offenders: list[str] = []
    for path in sorted(_FRAGMENT_ROOT.rglob("*.md")):
        if path.name == "_README.md":
            continue
        text = path.read_text(encoding="utf-8")
        match = re.search(r"^role:\s*(.+)$", text, re.MULTILINE)
        assert match is not None, f"fragment {path} has no `role:` frontmatter"
        role = match.group(1).strip()
        if role == "shared":
            continue
        roles = {part.strip() for part in role.split(",")}
        if "project-manager" in roles:
            offenders.append(str(path.relative_to(_FRAGMENT_ROOT)))
    assert offenders == [], f"fragments still binding role=project-manager: {offenders}"


def test_no_catalog_worker_step_binds_project_manager() -> None:
    offenders: list[str] = []
    for name, seq in _SEQUENCES.items():
        for step in seq:
            role = getattr(step, "role", "")
            if role in {"python", "shared"}:
                continue
            roles = {part.strip() for part in role.split(",")}
            if "project-manager" in roles:
                offenders.append(f"{name}.{getattr(step, 'label', '?')}")
    assert offenders == [], f"catalog worker steps still binding role=project-manager: {offenders}"
