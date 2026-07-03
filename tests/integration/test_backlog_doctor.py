"""Integration tests for ``backlog doctor`` (T-25-06, SPEC §3.4, §3.7, §3.8).

The four BL-* checks are exercised by a **single parameterized** test (one fixture matrix) —
NOT four copy-pasted functions (SPEC §3.8 #8). A planted violation per check ERRORs; a clean
tree passes (no findings). Roots injected over a ``tmp_path`` fixture specs-dir.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.features.backlog.doctor import (
    BacklogDoctorCode,
    Severity,
    run_backlog_doctor,
)

pytestmark = pytest.mark.integration

# A minimal source root the registry scans for code anchors.
_SOURCE = "class Widget:\n    pass\n\n\nclass Gadget:\n    pass\n"

# A valid bound intent the survivors share — points at a real code anchor.
_VALID_INTENT_WIDGET = (
    "intents:\n  - subject: { kind: code, ref: pkg/m.py#Widget }\n    change: refactor Widget\n"
)


def _build_specs(tmp_path: Path) -> tuple[Path, Path]:
    specs = tmp_path / "specs"
    (specs / "backlog").mkdir(parents=True)
    (specs / "memory" / "product").mkdir(parents=True)
    (specs / "memory" / "product" / "catalog.json").write_text(
        json.dumps({"features": [{"slug": "alpha-feature"}]}), encoding="utf-8"
    )
    src = tmp_path / "src"
    (src / "pkg").mkdir(parents=True)
    (src / "pkg" / "m.py").write_text(_SOURCE, encoding="utf-8")
    return specs, src


def _write_item(specs: Path, slug: str, frontmatter: str) -> None:
    (specs / "backlog" / f"{slug}.md").write_text(
        f"---\nstatus: idea\n{frontmatter}---\n\n# {slug}\n", encoding="utf-8"
    )


def _run(specs: Path, src: Path) -> list:
    return run_backlog_doctor(
        specs_dir=specs,
        source_root=src,
        catalog_path=specs / "memory" / "product" / "catalog.json",
        alias_map_path=specs / "no-aliases.txt",
        archive_root=specs / "_archive",
        cli_anchors=frozenset(),
    )


# ── clean tree passes (acceptance §3.7.4) ───────────────────────────────────────


def test_clean_tree_has_no_findings(tmp_path: Path) -> None:
    specs, src = _build_specs(tmp_path)
    _write_item(specs, "clean-one", _VALID_INTENT_WIDGET)
    _write_item(
        specs,
        "clean-two",
        "intents:\n  - subject: { kind: code, ref: pkg/m.py#Gadget }\n    change: tweak Gadget\n",
    )
    findings = _run(specs, src)
    assert findings == [], [f.to_dict() for f in findings]


# ── one parameterized matrix over the four BL-* checks (SPEC §3.8 #8) ─────────────


def _plant_schema(specs: Path, src: Path) -> None:
    # An item with an UNRESOLVED subject (no such symbol) → BL-SCHEMA.
    _write_item(
        specs,
        "bad-schema",
        "intents:\n  - subject: { kind: code, ref: pkg/m.py#NoSuchSymbol }\n    change: x\n",
    )


def _plant_dup(specs: Path, src: Path) -> None:
    _write_item(specs, "dup-a", _VALID_INTENT_WIDGET)
    _write_item(specs, "dup-b", _VALID_INTENT_WIDGET)  # same anchor + same change


def _plant_conflict(specs: Path, src: Path) -> None:
    # C->D then C->E: same anchor, differing change → BL-CONFLICT (the divergent twin).
    _write_item(
        specs,
        "twin-d",
        "intents:\n  - subject: { kind: code, ref: pkg/m.py#Widget }\n    change: change to D\n",
    )
    _write_item(
        specs,
        "twin-e",
        "intents:\n  - subject: { kind: code, ref: pkg/m.py#Widget }\n    change: change to E\n",
    )


def _plant_stale(specs: Path, src: Path) -> None:
    _write_item(specs, "shipped-feature", _VALID_INTENT_WIDGET)
    archive = specs / "_archive" / "v0.1.20"
    archive.mkdir(parents=True)
    (archive / "consumed_backlog.json").write_text(
        json.dumps(
            {"release": "v0.1.20", "consumed": [{"slug": "shipped-feature", "shipped_anchors": []}]}
        ),
        encoding="utf-8",
    )


@pytest.mark.parametrize(
    ("planter", "expected_code"),
    [
        (_plant_schema, BacklogDoctorCode.BL_SCHEMA),
        (_plant_dup, BacklogDoctorCode.BL_DUP),
        (_plant_conflict, BacklogDoctorCode.BL_CONFLICT),
        (_plant_stale, BacklogDoctorCode.BL_STALE),
    ],
)
def test_each_violation_is_flagged(
    tmp_path: Path,
    planter: object,
    expected_code: BacklogDoctorCode,
) -> None:
    specs, src = _build_specs(tmp_path)
    planter(specs, src)  # type: ignore[operator]
    findings = _run(specs, src)
    codes = {f.code for f in findings}
    assert expected_code in codes, [f.to_dict() for f in findings]
    assert all(f.severity is Severity.ERROR for f in findings if f.code is expected_code)


def test_stale_noop_when_no_ledger(tmp_path: Path) -> None:
    """BL-STALE is a no-op (never a false ERROR) when no archived ledger exists (§3.7.6)."""
    specs, src = _build_specs(tmp_path)
    _write_item(specs, "live-feature", _VALID_INTENT_WIDGET)
    findings = _run(specs, src)
    assert not any(f.code is BacklogDoctorCode.BL_STALE for f in findings)
