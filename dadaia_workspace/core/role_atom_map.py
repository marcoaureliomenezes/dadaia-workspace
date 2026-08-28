"""Declarative role → memory-atom map DATA (v0.1.62 FR2 / ADR-4 — `core` leaf).

The single source of the role → memory-atom mapping. Consumer:

* ``features/reports/validation.py`` — the handoff-v1.2 ``self_pull`` role-map coverage
  check (a mapped agent's atom ref must appear in ``self_pull.refs``).

Pure data, stdlib-only — no imports at all.
"""

from __future__ import annotations

#: The declarative role → memory-atom map. Each value is the atom's path relative to the
#: active context's ``specs_dir`` (so the recorded/expected handoff ref is
#: ``specs/<value>``). A role not listed here (e.g. ``software-engineer``,
#: ``security-reviewer``, ``project-auditor``) carries no mapped atom: the harness injects
#: nothing for it, and the v1.2 coverage check imposes no requirement on it.
ROLE_ATOM_MAP: dict[str, str] = {
    "software-architect": "memory/ARCHITECTURE.md",
    "qa-engineer": "memory/QUALITY.md",
    "product-engineer": "memory/product/catalog.json",
}

__all__ = ["ROLE_ATOM_MAP"]
