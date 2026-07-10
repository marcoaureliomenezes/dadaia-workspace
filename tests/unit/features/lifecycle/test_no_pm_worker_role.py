"""T-44-8 — no worker step (fragment layer) binds role=project-manager.

``project-manager`` is the Layer-1 orchestrator, never a Layer-2 worker persona (D-1).
After the v0.1.44 reassignment, no fragment frontmatter ``role:`` may name it
(``role: shared`` and ``role: python`` are not worker personas and are excluded).

D-1 (PM never a Layer-2 worker) retains two independent detectors: this fragment-side
rglob (the only fragment-rglob PM check) and the persona guardrail's catalog-side
``check_persona_resolution`` PROJECT_MANAGER finding (``test_persona_resolution_guardrail.py``)
— the catalog-layer duplicate here is dropped in its favor.
"""

from __future__ import annotations

import re
from pathlib import Path

_FRAGMENT_ROOT = (
    Path(__file__).resolve().parents[4] / "dadaia_workspace" / "public" / "lifecycle_fragments"
)


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
