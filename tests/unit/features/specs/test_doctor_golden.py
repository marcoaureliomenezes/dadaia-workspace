"""Golden byte-identical behavior lock for the FR1 SpecsDoctor decomposition (T-55-10, AC-2).

v0.1.55 FR1 splits the 2,830-line ``features/specs/doctor.py`` god module into a thin
``SpecsDoctor`` coordinator (owning ``check()``/``fix()`` ORDER) plus six single-responsibility
validator siblings and two shared leaf modules. The refactor MUST be behavior-preserving: the
coordinator's ``check()`` output and the ``dadaia specs doctor --json`` payload have to serialize
**byte-identically** to the pre-split tree, with the six families still emitted in the original
interleaved order.

This lock is captured DETERMINISTICALLY (AC-2 / R-4):

* **Fixed committed fixture root** — ``_golden/fixture_specs/`` triggers >=1 issue from EACH of
  the six validator families (structural / memory / release / closure_audit / governance /
  coherence) with the interleaved ``check()`` order visible.
* **Path normalization** — every absolute path (the CLI ``--json`` top-level ``specs_dir`` AND
  each issue ``path``) is replaced with the literal token ``<SPECS>`` so the golden is
  machine-independent.
* **Clock freeze** — ``date.today`` and ``datetime.now(tz=UTC)`` are pinned to 2026-07-15 so the
  two date-gated checks (release-SemVer severity flip; candidates hotfix staleness) are
  deterministic. The freeze is applied to every specs submodule that binds ``date``/``datetime``
  (the coordinator pre-split, and ``doctor_release``/``doctor_governance`` post-split), so this
  lock survives the decomposition without edits.

Regenerate the golden (ONLY when a deliberate behavior change is approved) with:
``UPDATE_DOCTOR_GOLDEN=1 pytest tests/unit/features/specs/test_doctor_golden.py``.
"""

from __future__ import annotations

import importlib
import json
import os
import re
from datetime import date, datetime, tzinfo
from pathlib import Path

import pytest

from dadaia_workspace.features.specs import SpecsDoctor, SpecsDoctorIssue

pytestmark = pytest.mark.unit

_HERE = Path(__file__).resolve().parent
_FIXTURE = _HERE / "_golden" / "fixture_specs"
_GOLDEN = _HERE / "_golden" / "doctor_golden_v0155.json"

_FROZEN_DATE = date(2026, 7, 15)
_FROZEN_DATETIME = datetime(2026, 7, 15, 12, 0, 0)

# Every specs submodule that may bind a module-level ``date``/``datetime`` name the checks call.
# doctor (coordinator, pre-split) + doctor_release (SemVer date-gate, post-split) +
# doctor_governance (candidates hotfix staleness, post-split).
_CLOCK_MODULE_NAMES = (
    "dadaia_workspace.features.specs.doctor",
    "dadaia_workspace.features.specs.doctor_release",
    "dadaia_workspace.features.specs.doctor_governance",
)

# code -> owning validator family (per the FR1 family mapping). Used to assert the fixture
# spans all six families, and to prove the split preserved family provenance.
_FAMILY_OF_CODE: dict[str, str] = {
    "SPEC-DOC-001": "coherence",
    "D-OC-1": "coherence",
    "SPECS-VERSION": "coherence",
    "SPEC-DOC-028": "coherence",
    "SPEC-DOC-029": "coherence",
    "SPEC-DOC-037": "coherence",
    "SPEC-DOC-002": "memory",
    "SPEC-DOC-002L": "memory",
    "SPEC-DOC-008": "memory",
    "CAT-1": "memory",
    "LINT-1": "memory",
    "SPEC-DOC-003": "release",
    "SPEC-DOC-004": "release",
    "SPEC-DOC-005": "release",
    "SPEC-DOC-009": "release",
    "SPEC-DOC-016": "release",
    "SPEC-DOC-024": "release",
    "SPEC-DOC-026": "release",
    "SPEC-DOC-027": "release",
    "SPEC-DOC-006": "closure_audit",
    "SPEC-DOC-007": "closure_audit",
    "SPEC-DOC-030": "closure_audit",
    "SPEC-DOC-034": "closure_audit",
    "SPEC-DOC-036": "closure_audit",
    "SPEC-DOC-038": "closure_audit",
    "SPEC-DOC-012": "governance",
    "SPEC-DOC-031": "governance",
    "SPEC-DOC-032": "governance",
    "SPEC-DOC-033": "governance",
    "SPEC-DOC-035": "governance",
    "TREE-1": "structural",
    "TREE-2": "structural",
    "TREE-3": "structural",
    "TREE-4": "structural",
    "TREE-5": "structural",
    "TREE-5M": "structural",
    "TREE-6": "structural",
    "TREE-7": "structural",
}

_ALL_FAMILIES = {
    "structural",
    "memory",
    "release",
    "closure_audit",
    "governance",
    "coherence",
}


class _FrozenDate(date):
    """A ``date`` subclass pinning ``today()`` — constructor + comparisons stay real."""

    @classmethod
    def today(cls) -> date:
        return _FROZEN_DATE


class _FrozenDateTime(datetime):
    """A ``datetime`` subclass pinning ``now()`` — ``strptime``/``replace``/arithmetic stay real."""

    @classmethod
    def now(cls, tz: tzinfo | None = None) -> datetime:
        return _FROZEN_DATETIME.replace(tzinfo=tz)


@pytest.fixture(autouse=True)
def _frozen_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    """Freeze ``date.today`` + ``datetime.now`` across every specs module that binds them."""
    for mod_name in _CLOCK_MODULE_NAMES:
        try:
            mod = importlib.import_module(mod_name)
        except ImportError:
            continue
        if hasattr(mod, "date"):
            monkeypatch.setattr(mod, "date", _FrozenDate, raising=False)
        if hasattr(mod, "datetime"):
            monkeypatch.setattr(mod, "datetime", _FrozenDateTime, raising=False)


def _capture() -> tuple[list[SpecsDoctorIssue], str]:
    """Run the doctor on the fixture and serialize the normalized CLI ``--json`` payload.

    Returns ``(issues, normalized_json_text)``. The doctor is constructed as a pure module —
    no ``public_dir`` / ``repo_root`` / ``workspace_state_dir`` injection — so the coherence
    registry, constitution file-ref, and lease/session backstop checks are deterministic
    no-ops and no subprocess (LINT-1) ever runs.
    """
    doctor = SpecsDoctor(_FIXTURE)
    issues = doctor.check()

    def _norm_path(value: str) -> str:
        # Platform-invariant path rendering: strip the fixture root, then canonicalize
        # separators so Windows (`\`) and POSIX (`/`) captures are byte-identical. The
        # golden locks refactor behavior, not OS path rendering.
        value = value.replace(str(_FIXTURE), "<SPECS>").replace(_FIXTURE.as_posix(), "<SPECS>")
        return value.replace(os.sep, "/") if os.sep != "/" else value

    def _norm_text(value: str) -> str:
        # Free-text messages may embed the fixture path RELATIVE tail with os.sep (Windows
        # renders "at <SPECS>\releases\v9.9.9"). Canonicalize ONLY <SPECS>-anchored tails —
        # a blanket backslash replace would corrupt legit regex content in other messages
        # (e.g. the SPEC-DOC-016 SemVer pattern's \d): "\d" and "\dir" are byte-identical
        # shapes at this level, so anchoring is the only safe disambiguation.
        value = value.replace(str(_FIXTURE), "<SPECS>").replace(_FIXTURE.as_posix(), "<SPECS>")
        return re.sub(
            r"(?<=<SPECS>)(?:\\[^\s\"\\]+)+",
            lambda m: m.group(0).replace("\\", "/"),
            value,
        )

    issue_dicts = []
    for i in issues:
        d = i.to_dict()
        path_value = d.get("path")
        if isinstance(path_value, str):
            d["path"] = _norm_path(path_value)
        desc_value = d.get("description")
        if isinstance(desc_value, str):
            d["description"] = _norm_text(desc_value)
        issue_dicts.append(d)
    payload = {
        "specs_dir": "<SPECS>",
        "issues": issue_dicts,
        "summary": {
            "errors": sum(1 for i in issues if i.severity.value == "error"),
            "warnings": sum(1 for i in issues if i.severity.value == "warning"),
        },
    }
    text = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)
    # Backstop for absolute fixture paths embedded in free-text messages: cover the raw,
    # the POSIX, and the JSON-escaped (Windows `\\`) renderings.
    normalized = (
        text.replace(json.dumps(str(_FIXTURE))[1:-1], "<SPECS>")
        .replace(_FIXTURE.as_posix(), "<SPECS>")
        .replace(str(_FIXTURE), "<SPECS>")
    )
    return issues, normalized


def test_doctor_output_is_byte_identical_to_golden() -> None:
    """The FR1 decomposition preserves check() + --json output byte-for-byte (AC-2)."""
    issues, current = _capture()
    if os.environ.get("UPDATE_DOCTOR_GOLDEN"):
        _GOLDEN.write_text(current + "\n", encoding="utf-8")
        pytest.skip("regenerated doctor golden (UPDATE_DOCTOR_GOLDEN set)")
    golden = _GOLDEN.read_text(encoding="utf-8")
    assert current + "\n" == golden, (
        "SpecsDoctor output diverged from the pre-split golden — the FR1 decomposition "
        "changed observable behavior (issue code/message/order/path). Fix the split, never "
        "the golden."
    )


def test_golden_spans_all_six_validator_families() -> None:
    """Sanity: the fixture triggers >=1 issue from EACH of the six families (AC-2).

    Guards against a golden that silently narrowed to a subset of families (which would make
    the byte-identity assertion vacuous for the untriggered families).
    """
    issues, _ = _capture()
    unknown = sorted({i.code for i in issues if i.code not in _FAMILY_OF_CODE})
    assert not unknown, f"golden fixture emitted codes with no family mapping: {unknown}"
    families = {_FAMILY_OF_CODE[i.code] for i in issues}
    assert families == _ALL_FAMILIES, (
        f"golden fixture must span all six validator families; got {sorted(families)}, "
        f"missing {sorted(_ALL_FAMILIES - families)}"
    )


def test_golden_preserves_interleaved_family_order() -> None:
    """The captured order must INTERLEAVE families (not be grouped family-by-family).

    A naive split that concatenates per-validator issue lists by family would group the codes;
    the coordinator owning the exact original ``check()`` sequence keeps them interleaved. This
    asserts the family sequence changes back-and-forth at least once (a real interleave), so a
    grouped-by-family regression fails even if the code SET is unchanged.
    """
    issues, _ = _capture()
    family_seq = [_FAMILY_OF_CODE[i.code] for i in issues]
    # collapse consecutive duplicates → the sequence of distinct family "runs"
    runs = [f for i, f in enumerate(family_seq) if i == 0 or f != family_seq[i - 1]]
    # a grouped output has each family appearing in exactly one run (len(runs) == distinct);
    # an interleaved output revisits at least one family → more runs than distinct families.
    assert len(runs) > len(set(runs)), (
        "captured issue order is grouped family-by-family, not interleaved — the coordinator "
        "must invoke validators in the original interleaved check() sequence"
    )
