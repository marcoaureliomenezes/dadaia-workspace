"""Complexity ratchet for `specs upgrade` and the one `dadaia doctor` (T-050-05, A1.4).

Intent: CONTRACT — A1.4 (the `#doctor`/`#upgrade` CC ratchet, permanent). The
`features/migrate/upgrade.py` zero-diff proof below is
Intent: SCAFFOLD — T-050-05 — expires: 0.6.0 (S1 FR23 firing amendment A7,
`specs/releases/0.5.0/reviews/S1-FR23-firing.md` §3 LOW finding: a hand-kept SHA-256
pin with no expiry is the `shipped-hashes.json` shape the forensic's P1/P4 condemn —
legitimate as a one-release zero-diff proof, not as a permanent guard).

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

import hashlib
from pathlib import Path

import pytest

pytest.importorskip("radon")  # CI does not install radon; ruff C901 is the CI-side ceiling
from radon.complexity import cc_visit  # noqa: E402

pytestmark = pytest.mark.contract

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SPECS_CLI = _REPO_ROOT / "dadaia_workspace" / "cli" / "commands" / "specs.py"
_DOCTOR_CLI = _REPO_ROOT / "dadaia_workspace" / "cli" / "commands" / "doctor.py"
_UPGRADE_MODULE = _REPO_ROOT / "dadaia_workspace" / "features" / "migrate" / "upgrade.py"

# Recorded ceilings (ratchet, T-050-03 baseline; `_DOCTOR_CEILING` re-pinned at the
# measured HEAD value by the S1 FR23 firing, A8 — "a ratchet that does not ratchet
# lets #doctor regrow to 30 silently"). Lowering is welcome; raising needs a
# same-commit justification.
_UPGRADE_CEILING = 8
_DOCTOR_CEILING = 6

# Pinned at T-050-05 (before that task touched anything else in the tree) — proved
# `features/migrate/upgrade.py` was untouched by FR1's scaffold/doctor/--recipe work.
# Re-pinned at v0.5.1 T-051-16 (K10): the retired migration-chain deletion legitimately
# rewrote this module (backup-first/chain-walk/re-stamp collapsed to the registry's
# "stamp v6 or refuse" rule) — same-commit justification per this test's own error
# message; the SCAFFOLD's 0.6.0 expiry (A7) is unaffected, this is a same-generation
# re-pin, not a renewal.
# Re-pinned at 0.4.7 T-047-58 (FR4): the English control vocabulary gives `specs upgrade`
# its status-token rewrite lane — an authorized, task-declared change to this module
# (same-commit justification per this test's own error message), not a renewal of the
# SCAFFOLD's 0.6.0 expiry.
# Re-pinned at 0.4.7 c11 T-047-101 (FR1): memory canon v7 retires `memory/TECHSTACK.md`,
# and a consumer tree stamped 6 reaches 7 only if something folds its body into
# ARCHITECTURE.md's `## Tech Stack` section — the 6 -> 7 hop this module now carries
# (`fold_tech_stack`), plus the re-stamp that hop requires. An authorized, task-declared
# change (P-20's same-commit justification), not a renewal of the SCAFFOLD's 0.6.0 expiry.
# Re-pinned at 0.4.8 T-048-05 (AC4.3, R6): a v6 tree must end v7 with its fixed law
# sections, so the hop restores them (`restore_fixed_sections`) and a re-stamp is no
# longer reported as a no-op — the S3 dead end. Authorized, task-declared change.
_UPGRADE_MODULE_SHA256 = "fbc6db82eafb0a15928372c6eb0300828df88763e0738f54f5dfd761207377c2"


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


def test_migrate_upgrade_module_is_untouched_by_fr1() -> None:
    """A1.4: `features/migrate/upgrade.py` stays byte-identical under T-050-05 — the
    rename automation this module carries is explicitly cut from FR1's scope.
    Re-pinned at 0.4.7 c5 T-047-49: the module gained the `_ideas/` removal lane.

    Intent: SCAFFOLD — T-050-05 — expires: 0.6.0 (S1 FR23 firing amendment A7)."""
    digest = hashlib.sha256(_UPGRADE_MODULE.read_bytes()).hexdigest()
    assert digest == _UPGRADE_MODULE_SHA256, (
        "features/migrate/upgrade.py changed — T-050-05 (FR1) explicitly does not grow "
        "`specs upgrade`; if this file legitimately changed for another FR/task, update "
        "this pinned hash in the same commit with that task's justification."
    )
