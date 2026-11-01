"""One derived skill-inventory oracle: the single roster of skills every reader uses.

Skill inventories kept by hand drift from the tree: a skill added, renamed or removed
is forgotten in one copy. Every consumer reads this one derived inventory instead.

This module is the single, DERIVED source of that inventory: it reuses
:func:`tests.helpers.public_asset_roster.scan` — itself a thin wrapper over
``iter_public_files`` (the EXACT enumeration ``install()``/``stage()``/
``doctor()`` use internally) — and extracts the top-level directory name under
``skills/`` from every real (non-ignored) file path already enumerated there.

A skill, product-side, IS "a directory under ``dadaia_workspace/public/skills/``" — the
same definition ``dadaia_workspace/infrastructure/codex_doctor.check_agent_skill_refs``
uses via ``(skills_dir / skill).is_dir()``. Deriving the name set from the roster's
already-proven file enumeration (rather than re-walking ``skills/`` a second,
independently-maintained time) keeps this oracle coupled to the ONE real walk instead of
adding a fourth scan that could itself drift from the other three.
"""

from __future__ import annotations

from pathlib import Path

from tests.helpers.public_asset_roster import default_public_dir, scan

_SKILLS_PREFIX = "skills/"


def skill_names(public_dir: Path | None = None) -> set[str]:
    """The exact set of skill directory names under ``public/skills/``.

    Derived from :func:`tests.helpers.public_asset_roster.scan`'s real file
    enumeration — never a hand-kept list. Defaults to the real package's
    ``dadaia_workspace/public/`` tree; a caller exercising a mutated COPY of
    ``public/`` (never the real tree) passes that copy's ``public/`` root explicitly,
    exactly as :func:`tests.helpers.public_asset_roster.scan` does.
    """
    root = public_dir if public_dir is not None else default_public_dir()
    names: set[str] = set()
    for rel in scan(root):
        if not rel.startswith(_SKILLS_PREFIX):
            continue
        name = rel[len(_SKILLS_PREFIX) :].split("/", 1)[0]
        if name:
            names.add(name)
    return names
