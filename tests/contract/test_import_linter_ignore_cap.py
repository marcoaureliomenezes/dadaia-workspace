"""Import-linter ignore-edge **cap** contract (WS-R8 / AC-R8-04, release v0.1.10).

Architect finding F10: the ``ignore_imports`` lists in ``setup.cfg`` are documented,
transitional exceptions to the ``features -> infrastructure`` / ``features -> subprocess``
layering bans. Each ignored edge is a *suppressed* architecture violation. Left unguarded,
that list silently grows — every new exception erodes the layering law one line at a time,
and import-linter itself still passes because the edge is ignored. Nothing fails.

This contract pins the **total number** of ignored edges across every import-linter
contract in ``setup.cfg`` and fails CI when it *grows* beyond the recorded cap. The cap is
a ratchet, not a target:

* **Lowering is always welcome** — when a DI cleanup removes an exception, drop the edge
  from ``setup.cfg`` *and* lower ``_RECORDED_IGNORE_EDGE_CAP`` here in the same commit. The
  test then re-pins the new, lower number.
* **Raising requires explicit justification in the same commit** — a new ignored edge is a
  new suppressed layering violation. Adding one means editing ``setup.cfg`` (with a
  rationale comment on the edge) *and* bumping ``_RECORDED_IGNORE_EDGE_CAP`` here, both in
  the same change, so review sees the architecture debt grow on purpose, never by accident.

The cap is also comment-pinned in ``setup.cfg`` itself (header block) so the two stay in
sync by review discipline; this test is the enforcement.
"""

from __future__ import annotations

import configparser
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SETUP_CFG = _REPO_ROOT / "setup.cfg"

# RECORDED CAP — the current total of ``ignore_imports`` edges across all import-linter
# contracts in setup.cfg. Lowering this (after deleting an edge) is good and encouraged.
# RAISING this requires a new documented edge in setup.cfg + justification in the SAME
# commit (a new ignored edge = a new suppressed layering violation; see module docstring).
#
# Breakdown at the recorded count (v0.1.54 W3 / FR5): features-no-infrastructure = 9,
# features-no-subprocess = 4, features-no-cross-feature = 13, total = 26.
#
# W2 NOTE (v0.1.54 FR3): the new `features-no-cross-feature` independence contract documents
# the 13 surviving post-FR2 cross-feature module-pair edges as ignores (each a suppressed
# cross-feature composition-debt exception — a feature reaching a sibling feature instead of
# composing via the container). W2 raised the cap 15 -> 28 (+13).
#
# W3 NOTE (v0.1.54 FR5): the two `markdown_*_store` direct-debt edges
# (`workflows.service -> markdown_workflow_store`, `agents.reader -> markdown_agent_store`)
# were removed via container `store_factory` DI completion, lowering the cap 28 -> 26 (-2)
# and the features-no-infrastructure family 11 -> 9 in the same commit.
#
# SHRINK NOTE (arch A4 + T-010-33): v0.1.53 lowered the cap 17 -> 15. W1 deleted the panel
# workflow-launcher chain (workflow_launcher_adapter), which retired BOTH
# `panel.service -> workflow_launcher_adapter` ignore edges (one per contract) — they no
# longer matched any import and made `lint-imports` error. The remaining container-DI
# cleanup is still tracked in backlog `features-import-infrastructure-direct-debt`; when it
# lands, drop the corresponding `ignore_imports` edges from setup.cfg AND lower this cap in
# the same commit (the `test_recorded_cap_is_not_stale_above_reality` test re-pins it).
# T-010-33's reverse-direction `forbidden` contracts (core-no-upper-layers,
# infrastructure-no-upper-layers) add ZERO ignore edges — they freeze layers verified
# clean — so they do not move this number.
#
# W3 NOTE (v0.1.61 FR5, T-61-30, ADR-4 / audit A-2): the new `cli-no-infrastructure`
# forbidden contract caps the cli -> infrastructure edge class (11 sites at audit time,
# growing silently — v0.1.60 added 2 unnoticed). The post-W2 edge set (plugin.py's
# public-asset-manager wiring edge remains; the FR4/W2-removed edge is gone) was
# re-enumerated by grep at implementation time = 10 module-pair edges. None is
# composition-root wiring (container.py's monopoly); all are accepted, capped, ratcheted
# debt. Cap raised 26 -> 36 (+10) in the same commit as the setup.cfg contract.
_RECORDED_IGNORE_EDGE_CAP = 36

# Per-family recorded breakdown, pinned per contract section so a wrong 13-edge cross-feature
# set (or a silent shift between families) fails loudly, not just the grand total.
_RECORDED_PER_FAMILY_CAP: dict[str, int] = {
    "features-no-infrastructure": 9,
    "features-no-subprocess": 4,
    "features-no-cross-feature": 13,
    "cli-no-infrastructure": 10,
}


def _ignore_edges_by_contract() -> dict[str, list[str]]:
    """Parse setup.cfg → {contract-section: [<ignored import edge>, ...]}.

    An edge is any ``a -> b`` line in an ``[importlinter:contract:*]`` section's
    ``ignore_imports`` value. Comment lines (``# ...``) inside the value are skipped by
    configparser's ``inline_comment_prefixes`` for full-line comments; we additionally
    require the literal ``->`` arrow so only real edges count.
    """
    parser = configparser.ConfigParser()
    read = parser.read(_SETUP_CFG, encoding="utf-8")
    assert read, f"setup.cfg not found at {_SETUP_CFG}"
    edges: dict[str, list[str]] = {}
    for section in parser.sections():
        if not section.startswith("importlinter:contract"):
            continue
        raw = parser[section].get("ignore_imports", "")
        section_edges = [
            line.strip()
            for line in raw.splitlines()
            if "->" in line and not line.strip().startswith("#")
        ]
        if section_edges:
            edges[section] = section_edges
    return edges


def test_ignore_edge_cap_family_breakdown_and_sanctioned_sources() -> None:
    """The total ignored-import edge count must equal the recorded cap exactly (never
    silently grow past it, never drift stale below it), the per-family breakdown must
    match the recorded shape, and every ignored edge must originate in its family's
    sanctioned source layer."""
    by_contract = _ignore_edges_by_contract()
    total = sum(len(v) for v in by_contract.values())
    breakdown = ", ".join(f"{sec.split(':')[-1]}={len(v)}" for sec, v in by_contract.items())
    assert total <= _RECORDED_IGNORE_EDGE_CAP, (
        f"import-linter ignore_imports grew to {total} edges "
        f"(cap {_RECORDED_IGNORE_EDGE_CAP}); breakdown: {breakdown}. "
        "Each ignored edge is a SUPPRESSED layering violation (arch F10). Adding one "
        "requires a documented rationale comment on the edge in setup.cfg AND a bump of "
        "_RECORDED_IGNORE_EDGE_CAP in this test, both in the SAME commit."
    )
    assert total == _RECORDED_IGNORE_EDGE_CAP, (
        f"_RECORDED_IGNORE_EDGE_CAP={_RECORDED_IGNORE_EDGE_CAP} but setup.cfg has {total} "
        "ignored edges. If you removed an edge, LOWER the cap in this test to re-pin it "
        "(good — ratchet down). If you added one, see the cap-growth message above."
    )

    by_family = {section.split(":")[-1]: len(edges) for section, edges in by_contract.items()}
    assert by_family == _RECORDED_PER_FAMILY_CAP, (
        f"per-family ignore breakdown {by_family} != recorded {_RECORDED_PER_FAMILY_CAP}. "
        "Each family's suppressed-edge count is pinned; adjust the setup.cfg ignores AND "
        "_RECORDED_PER_FAMILY_CAP together in the same commit."
    )

    _assert_every_ignored_edge_is_a_features_layering_exception(by_contract)


def _assert_every_ignored_edge_is_a_features_layering_exception(
    by_contract: dict[str, list[str]],
) -> None:
    """Every ignored edge must originate in its family's sanctioned source layer.

    The layering law's sanctioned exceptions come in three kinds now:
    (1) ``features -> infrastructure`` reach while container DI is incomplete
    (``features-no-infrastructure`` / ``features-no-subprocess``), (2) v0.1.54 FR3:
    ``features -> features`` cross-feature composition debt (``features-no-cross-feature``),
    and (3) v0.1.61 FR5 (ADR-4): ``cli -> infrastructure`` capped debt
    (``cli-no-infrastructure``) — the CLI reaching adapters instead of composing via the
    container. The first two keep a ``dadaia_workspace.features`` **source**; the cli family
    keeps a ``dadaia_workspace.cli`` source. An ignored edge whose source does not match its
    family's sanctioned layer would be a new, unrelated suppression smuggled into the list —
    fail loudly so it cannot hide among the documented layering debt.
    """
    _SANCTIONED_SOURCE_BY_FAMILY = {
        "cli-no-infrastructure": "dadaia_workspace.cli",
    }
    offenders: list[str] = []
    for section, section_edges in by_contract.items():
        family = section.split(":")[-1]
        sanctioned = _SANCTIONED_SOURCE_BY_FAMILY.get(family, "dadaia_workspace.features")
        for edge in section_edges:
            source = edge.split("->", 1)[0].strip()
            if not source.startswith(sanctioned):
                offenders.append(f"[{section}] {edge}")
    assert not offenders, (
        "ignored import edges that are not features-layering exceptions:\n" + "\n".join(offenders)
    )
