"""AC-1 grep contract (v0.1.64 FR2): the 13-site consolidation must not regress.

No test file may re-declare a consolidated platform-invariance helper (a stale local
copy silently diverges from the shared truth — the exact debt FR1 paid down), and the
fragile cross-test-module import of ``test_install_target_goldens`` must stay dead.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_TESTS_ROOT = Path(__file__).resolve().parent.parent.parent
_CANONICAL_MODULE = _TESTS_ROOT / "helpers" / "golden_platform.py"

# Every consolidated helper name, in both the shared (bare) and the historical
# (underscore-prefixed local-copy) spellings.
_CONSOLIDATED_NAMES = (
    "norm_path_line",
    "norm_panel_body",
    "canon_env_line",
    "sort_line_lists",
    "is_env_doctor_line",
    "assert_golden",
    "assert_matches_golden",
    "norm_stderr",
)
_DEF_RE = re.compile(r"^def _?(?:" + "|".join(_CONSOLIDATED_NAMES) + r")\(", re.MULTILINE)

_CROSS_IMPORT = "from tests.unit.infrastructure.test_install_target_goldens import"

# SPEC v0.1.64 FR2: the bespoke normalizers are NOT force-migrated — each carries
# test-specific scrubs (e.g. test_fragment_gate_goldens' _assert_golden takes a
# workspace_root and applies fragment-specific normalization). Explicit, cited exemptions
# only; any NEW file re-declaring a consolidated helper still fails this contract.
_BESPOKE_EXEMPT = frozenset(
    {
        "unit/features/lifecycle/test_fragment_gate_goldens.py",
        "unit/features/panel/test_api_golden.py",
        "unit/features/specs/test_doctor_golden.py",
    }
)


def _test_files() -> list[Path]:
    files = [p for p in _TESTS_ROOT.rglob("*.py") if "_golden" not in p.parts]
    assert files, "test tree not found"
    return files


def test_no_test_file_redeclares_a_consolidated_helper() -> None:
    offenders: list[str] = []
    for path in _test_files():
        rel = path.relative_to(_TESTS_ROOT).as_posix()
        if path == _CANONICAL_MODULE or rel in _BESPOKE_EXEMPT:
            continue
        for match in _DEF_RE.finditer(path.read_text(encoding="utf-8")):
            offenders.append(f"{path.relative_to(_TESTS_ROOT)}: {match.group(0)}...)")
    assert not offenders, (
        "stale local copy of a consolidated golden_platform helper — import it from "
        f"tests.helpers.golden_platform instead: {offenders}"
    )


def test_cross_test_module_import_stays_dead() -> None:
    offenders = [
        str(path.relative_to(_TESTS_ROOT))
        for path in _test_files()
        if path.name != "test_no_local_helper_copies.py"
        and _CROSS_IMPORT in path.read_text(encoding="utf-8")
    ]
    assert not offenders, (
        f"fragile cross-test-module import of test_install_target_goldens is back: {offenders}"
    )
