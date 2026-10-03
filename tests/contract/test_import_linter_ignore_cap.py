"""Intent: CONTRACT — P-10 suppressed layering-edge cap (setup.cfg ignore_imports)

Each ignored import-linter edge is a suppressed layering violation: the count is a ratchet (lower it
with the edge, raise it only with a documented edge in the same commit), and the contract set is pinned.
"""

from __future__ import annotations

import configparser
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

_REPO_ROOT = Path(__file__).resolve().parents[2]
_RECORDED_IGNORE_EDGE_CAP = 2
_RECORDED_PER_FAMILY_CAP: dict[str, int] = {"features-no-cross-feature": 2}
_RECORDED_CONTRACT_COUNT = 6  # a new contract needs its Part-1 principle in ARCHITECTURE.md (A18.1)


def _setup_cfg() -> configparser.ConfigParser:
    parser = configparser.ConfigParser()
    assert parser.read(_REPO_ROOT / "setup.cfg", encoding="utf-8"), "setup.cfg not found"
    return parser


def test_ignore_edge_cap_family_breakdown_and_sanctioned_sources() -> None:
    """The ignored-edge total and per-family counts equal the recorded caps, and every edge starts in features."""
    parser = _setup_cfg()
    by_family = {
        section.split(":")[-1]: edges
        for section in parser.sections()
        if section.startswith("importlinter:contract")
        if (
            edges := [
                line.strip()
                for line in parser[section].get("ignore_imports", "").splitlines()
                if "->" in line and not line.strip().startswith("#")
            ]
        )
    }
    total = sum(len(v) for v in by_family.values())
    assert total == _RECORDED_IGNORE_EDGE_CAP, (
        f"{total} ignored edges; cap {_RECORDED_IGNORE_EDGE_CAP} (move both together)"
    )
    assert {k: len(v) for k, v in by_family.items()} == _RECORDED_PER_FAMILY_CAP
    offenders = [
        e
        for edges in by_family.values()
        for e in edges
        if not e.startswith("dadaia_workspace.features")
    ]
    assert not offenders, f"ignored edges that are not features-layering exceptions: {offenders}"


def test_cross_feature_contract_modules_equals_disk_and_contract_count_is_pinned() -> None:
    """features-no-cross-feature's ``modules =`` equals every feature package on disk; the contract count is pinned (A18.5/V32)."""
    features_dir = _REPO_ROOT / "dadaia_workspace" / "features"
    on_disk = {
        f"dadaia_workspace.features.{p.name}"
        for p in features_dir.iterdir()
        if p.is_dir() and (p / "__init__.py").is_file()
    }
    assert len(on_disk) == 12
    parser = _setup_cfg()
    raw = parser["importlinter:contract:features-no-cross-feature"]["modules"]
    declared = {line.strip() for line in raw.splitlines() if line.strip()}
    assert declared == on_disk, (
        f"missing: {sorted(on_disk - declared)}; stale: {sorted(declared - on_disk)}"
    )
    sections = [s for s in parser.sections() if s.startswith("importlinter:contract:")]
    assert len(sections) == _RECORDED_CONTRACT_COUNT
