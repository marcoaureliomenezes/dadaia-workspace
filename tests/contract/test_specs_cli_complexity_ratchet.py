"""Complexity ratchet for `cli/commands/specs.py` (T-050-05, FR1, A1.4).

Intent: CONTRACT — A1.4.

`#upgrade` and `#doctor` are the engine of the forensic's chain 1 —
`specs-upgrade-emits-atoms-violating-frontmatter-schema` bred four followers in eight
days (specs/releases/0.5.0/SPEC.md FR1). `specs upgrade` is NOT grown by this
release; `--recipe` renders in its own function so `#doctor`'s complexity does not
move either. Baseline (T-050-03, before this release's FR1 work): `#upgrade` CC 26,
`#doctor` CC 30. Lowering either ceiling is welcome; raising one requires a
same-commit justification.

A1.4 also names a zero-diff assertion over `features/migrate/upgrade.py` — FR1's own
rename automation is cut (fold 3, `software-architect` change 3), so that module must
stay byte-identical under this task. Pinned by content hash so any edit under this
release must justify itself here, not slip in silently.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from radon.complexity import cc_visit

pytestmark = pytest.mark.contract

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SPECS_CLI = _REPO_ROOT / "dadaia_workspace" / "cli" / "commands" / "specs.py"
_UPGRADE_MODULE = _REPO_ROOT / "dadaia_workspace" / "features" / "migrate" / "upgrade.py"

# Recorded ceilings (ratchet, T-050-03 baseline). Lowering is welcome; raising needs
# same-commit justification.
_UPGRADE_CEILING = 26
_DOCTOR_CEILING = 30

# Pinned at T-050-05 (before this task touched anything else in the tree) — proves
# `features/migrate/upgrade.py` is untouched by FR1's scaffold/doctor/--recipe work.
_UPGRADE_MODULE_SHA256 = "95fe07aefd68bfbd200e1559495dc46bc51ea44dcfa9b5462248a99dc4b2f319"


def _complexity_by_name(path: Path) -> dict[str, int]:
    source = path.read_text(encoding="utf-8")
    return {block.name: block.complexity for block in cc_visit(source)}


def test_upgrade_and_doctor_complexity_stay_at_or_below_baseline() -> None:
    """A1.4/V19/V35: `#upgrade` <= 26, `#doctor` <= 30."""
    scores = _complexity_by_name(_SPECS_CLI)
    assert "upgrade" in scores, "cli/commands/specs.py must still define `upgrade`"
    assert "doctor" in scores, "cli/commands/specs.py must still define `doctor`"
    assert scores["upgrade"] <= _UPGRADE_CEILING, (
        f"#upgrade CC {scores['upgrade']} exceeds the {_UPGRADE_CEILING} ratchet — "
        "`specs upgrade` must not grow (FR1, fold 3, software-architect change 3)."
    )
    assert scores["doctor"] <= _DOCTOR_CEILING, (
        f"#doctor CC {scores['doctor']} exceeds the {_DOCTOR_CEILING} ratchet — render "
        "--recipe in its own function so #doctor's complexity does not move (A1.3)."
    )


def test_migrate_upgrade_module_is_untouched_by_fr1() -> None:
    """A1.4: `features/migrate/upgrade.py` stays byte-identical under T-050-05 — the
    rename automation this module carries is explicitly cut from FR1's scope."""
    digest = hashlib.sha256(_UPGRADE_MODULE.read_bytes()).hexdigest()
    assert digest == _UPGRADE_MODULE_SHA256, (
        "features/migrate/upgrade.py changed — T-050-05 (FR1) explicitly does not grow "
        "`specs upgrade`; if this file legitimately changed for another FR/task, update "
        "this pinned hash in the same commit with that task's justification."
    )
