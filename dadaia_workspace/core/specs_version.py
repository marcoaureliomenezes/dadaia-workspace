"""Specs-pattern versioning (FR-S01 / FR-S02).

A Spec Context Project's ``specs/`` tree conforms to a *pattern version* — the
canonical structural layout the workspace expects. The library carries the single
source of truth (:data:`CANONICAL_SPECS_VERSION`); each project records its own
version in the ``specs_pattern_version`` field of ``specs/constitution.md``'s YAML
frontmatter.

Absent-stamp semantics: a constitution with no frontmatter (or no
``specs_pattern_version`` key) is treated as **version 0** — pre-framework, the flat
layout that predates the tree-v2 migration. Doctor warns and recommends
``dadaia specs upgrade``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from dadaia_workspace.core.frontmatter import Frontmatter, parse
from dadaia_workspace.core.gitflow import constitution_error, constitution_text, specs_tree_exists

#: Single source of truth for the current canonical specs-pattern version.
#: Bump this when a new migration step is added to the registry (see ``registry.py``).
#: v3 = agent-tier-frontmatter (v0.1.72 FR1); v4 = bugs-single-file (v0.1.73 FR1 —
#: the operator's ONE-append-only-ledger contract); v5 = specs-canon-v6's tree shape
#: (T-050-05); v6 = this stamp, T-050-06A — the version number itself, deferred by
#: T-050-05 because the release-id axis flip was this task's write set;
#: v7 = memory canon v7 — ``memory/TECHSTACK.md`` left the canon and its body became
#: ``ARCHITECTURE.md``'s ``## Tech Stack`` section, which ``features/migrate`` folds.
CANONICAL_SPECS_VERSION = 7

#: The oldest stamp the one live upgrade hop starts from — and so the oldest a tree may
#: carry and still be a dadaia tree (SPEC 0.4.8 D7, D9); anything older is foreign.
OLDEST_UPGRADABLE_VERSION = 6

#: Version assigned to a tree with no stamp (pre-framework flat layout).
UNSTAMPED_VERSION = 0


def read_pattern_version(specs_dir: Path) -> int:
    """The constitution's ``specs_pattern_version``; :data:`UNSTAMPED_VERSION` (0) when
    the constitution, its frontmatter or the key is absent or unreadable."""
    fm = parse(constitution_text(specs_dir))
    value = fm.data.get("specs_pattern_version") if isinstance(fm, Frontmatter) else None
    return value if isinstance(value, int) and not isinstance(value, bool) else UNSTAMPED_VERSION


def classify(specs_dir: Path) -> Literal["absent", "malformed", "dadaia", "foreign"]:
    """``absent`` (no directory), ``malformed`` (:func:`constitution_error`), ``dadaia``
    (stamped >= 6) or ``foreign`` — a tree without a dadaia constitution (ADR 0047)."""
    if not specs_tree_exists(specs_dir):
        return "absent"
    if constitution_error(specs_dir):
        return "malformed"
    return "dadaia" if read_pattern_version(specs_dir) >= OLDEST_UPGRADABLE_VERSION else "foreign"
