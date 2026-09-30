"""Complexity ratchet for `specs upgrade` and the one `dadaia doctor` (T-050-05, A1.4).

Intent: CONTRACT — A1.4 (the `#doctor`/`#upgrade` CC ratchet, permanent).

0.4.7 T-047-02 deleted `dadaia specs doctor`; its `#doctor` half of this ratchet follows
the surface to `cli/commands/doctor.py#doctor` — the ONE doctor command — and ratchets
DOWN 10 -> 8 at the measured value of the folded command. The ceiling never moved up: the
three commands became one and got simpler.

`#upgrade` and `#doctor` are the engine of the forensic's chain 1 —
`specs-upgrade-emits-atoms-violating-frontmatter-schema` bred four followers in eight
days (specs/releases/0.5.0/SPEC.md FR1). `specs upgrade` is NOT grown by this
release. Baseline (T-050-03, before this release's FR1 work): `#upgrade` CC 26,
`#doctor` CC 30, ratcheted DOWN at the S1 FR23 firing (A8) to the measured `radon`
value at HEAD (10) — a ratchet that never tightens re-arms the exact chain-1 engine
this test exists to close (`specs/releases/0.5.0/reviews/S1-FR23-firing.md` §4).
Lowering either ceiling is welcome; raising one requires a same-commit justification.

A1.4 also names a zero-diff assertion over `features/migrate/upgrade.py` — FR1's own
rename automation is cut (fold 3, `software-architect` change 3), so that module must
stay byte-identical under this task. Pinned by content hash so any edit under this
release must justify itself here, not slip in silently — SCAFFOLD, expires 0.6.0
(A7): a hand-kept hash with no expiry is itself the P1 `shipped-hashes.json` shape at
the test-tier level; V28 turns an unrenewed expiry RED at that release's closure.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("radon")  # CI does not install radon; ruff C901 is the CI-side ceiling
from radon.complexity import cc_visit  # noqa: E402

pytestmark = pytest.mark.contract

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SPECS_CLI = _REPO_ROOT / "dadaia_workspace" / "cli" / "commands" / "specs.py"
_DOCTOR_CLI = _REPO_ROOT / "dadaia_workspace" / "cli" / "commands" / "doctor.py"

# Recorded ceilings (ratchet, T-050-03 baseline; `_DOCTOR_CEILING` re-pinned at the
# measured HEAD value by the S1 FR23 firing, A8 — "a ratchet that does not ratchet
# lets #doctor regrow to 30 silently"). Lowering is welcome; raising needs a
# same-commit justification.
_UPGRADE_CEILING = 8
_DOCTOR_CEILING = 6


def _complexity_by_name(path: Path) -> dict[str, int]:
    source = path.read_text(encoding="utf-8")
    return {block.name: block.complexity for block in cc_visit(source)}


def test_upgrade_and_doctor_complexity_stay_at_or_below_baseline() -> None:
    """A1.4/V19/V35: `specs upgrade` <= 8, the one `dadaia doctor` <= 6."""
    scores = _complexity_by_name(_SPECS_CLI)
    doctor_scores = _complexity_by_name(_DOCTOR_CLI)
    assert "upgrade" in scores, "cli/commands/specs.py must still define `upgrade`"
    assert "doctor" in doctor_scores, "cli/commands/doctor.py must still define `doctor`"
    scores["doctor"] = doctor_scores["doctor"]
    assert scores["upgrade"] <= _UPGRADE_CEILING, (
        f"#upgrade CC {scores['upgrade']} exceeds the {_UPGRADE_CEILING} ratchet — "
        "`specs upgrade` must not grow (FR1, fold 3, software-architect change 3)."
    )
    assert scores["doctor"] <= _DOCTOR_CEILING, (
        f"#doctor CC {scores['doctor']} exceeds the {_DOCTOR_CEILING} ratchet — keep "
        "each rendering (json/quiet/human) in its own function so the one doctor command "
        "stays a composition, not a branch tree (T-047-02)."
    )
