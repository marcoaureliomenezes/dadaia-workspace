"""The evidence-per-disposition table lives beside the disposition vocabulary it is
keyed by, in ``core.models.histo`` — never a second copy inside a feature.

Intent: CONTRACT — 0.4.7 T-047-27 (code review c3 MEDIUM-6: ``features/specs/audit.py``
and ``features/backlog/document.py`` each defined a ``_REQUIRED_EVIDENCE`` of the same
name and shape, so the two ledgers' evidence rules could drift apart silently). One
rule, so the NEXT ledger that validates an exit is covered without a third grep.
Size: SMALL — reads the production tree, no I/O beyond it.
"""

from __future__ import annotations

import re
from pathlib import Path

from dadaia_workspace.core.models import histo

_ASSIGNMENT = re.compile(r"^_?REQUIRED_EVIDENCE\b", re.MULTILINE)
_SOURCE = Path(histo.__file__).resolve().parents[3]


def test_only_core_models_histo_defines_the_table() -> None:
    home = Path(histo.__file__).resolve()
    definers = sorted(
        path.relative_to(_SOURCE).as_posix()
        for path in (_SOURCE / "dadaia_workspace").rglob("*.py")
        if path.resolve() != home
        and "public/skills/" not in path.as_posix()
        and _ASSIGNMENT.search(path.read_text(encoding="utf-8"))
    )
    assert definers == []


def test_the_table_covers_every_ledger_vocabulary_that_validates_an_exit() -> None:
    for vocabulary in (histo.BACKLOG_HISTO_DISPOSITIONS, histo.FINDINGS_DISPOSITIONS):
        for disposition in vocabulary:
            assert histo.REQUIRED_EVIDENCE[disposition] in {"release", "reason"}


def test_a_shared_disposition_requires_the_same_evidence_in_both_ledgers() -> None:
    shared = set(histo.BACKLOG_HISTO_DISPOSITIONS) & set(histo.FINDINGS_DISPOSITIONS)
    assert shared == {"superseded", "rejected"}
    assert [histo.REQUIRED_EVIDENCE[word] for word in sorted(shared)] == ["reason", "release"]
