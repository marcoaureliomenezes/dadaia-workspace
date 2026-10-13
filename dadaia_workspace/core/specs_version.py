"""Specs-pattern versioning.

A Spec Context Project's ``specs/`` tree conforms to a *pattern version* — the
canonical structural layout the workspace expects. The library carries the single
source of truth (:data:`CANONICAL_SPECS_VERSION`); each project records its own
version in the ``specs_pattern_version`` field of ``specs/constitution.md``'s YAML
frontmatter.

A tree with no stamp is ``foreign``; :func:`state` is the one reader of all of it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from dadaia_workspace.core.cli_line import fix_line
from dadaia_workspace.core.frontmatter import Frontmatter, parse
from dadaia_workspace.core.gitflow import constitution_error, constitution_text, specs_tree_exists

#: Single source of truth for the current canonical specs-pattern version.
#: Bump this whenever the canon a tree must meet changes. A canon change that
#: keeps the stamp leaves every older tree reading ``canonical`` while the doctor is red.
CANONICAL_SPECS_VERSION = 12

#: The oldest stamp the upgrade starts from — and so the oldest a tree may
#: carry and still be a dadaia tree; anything older is foreign.
OLDEST_UPGRADABLE_VERSION = 6

#: The canon fingerprint each stamp was cut at — re-pinned only together with a stamp bump,
#: or while the stamp is unpublished (``test_a_canon_change_bumps_the_stamp`` computes it).
CANON_AT = {12: "b2840d2171decc97"}
State = Literal["absent", "malformed", "foreign", "upgradable", "canonical"]


def state(
    specs_dir: Path, text: str | None = None, *, root: Path | None = None, context: str = ""
) -> tuple[State, str | None]:
    """The ONE reader of a specs tree's state and its one fix (``None`` when canonical) — of
    *text* when given (a pushed commit's constitution, ``""`` when it carries none), else
    of the tree on disk. A constitution whose YAML or gitflow block fails is ``malformed``.
    The fix names *context* when given, else *specs_dir* itself."""
    if text is None and not specs_tree_exists(specs_dir):
        kind: State = "absent"
    elif reason := constitution_error(specs_dir, text):
        return "malformed", f"Operator action: repair the YAML frontmatter of {reason}"
    else:
        fm = parse(constitution_text(specs_dir) if text is None else text)
        stamp = fm.data.get("specs_pattern_version") if isinstance(fm, Frontmatter) else None
        stamp = stamp if isinstance(stamp, int) and not isinstance(stamp, bool) else 0
        if stamp >= CANONICAL_SPECS_VERSION:
            return "canonical", None
        kind = "upgradable" if stamp >= OLDEST_UPGRADABLE_VERSION else "foreign"
    consent = ("--replace-foreign",) if kind == "foreign" else ()
    target = ("--context", context) if context else ("--specs-dir", str(specs_dir))
    return kind, fix_line(root, "specs", "init", *target, *consent)
