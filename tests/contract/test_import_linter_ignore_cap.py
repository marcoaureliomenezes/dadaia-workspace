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
# Breakdown at the recorded count (v0.1.10, after T-010-24's documented model-resolution
# edge): features-no-infrastructure = 12, features-no-subprocess = 5, total = 17.
#
# SHRINK NOTE (arch A4 + T-010-33): the cap stays at 17 — none of the 17 suppressed edges
# is yet retired. The container-DI cleanup that retires them is tracked in backlog
# `features-import-infrastructure-direct-debt`; when it lands, drop the corresponding
# `ignore_imports` edges from setup.cfg AND lower this cap in the same commit (the
# `test_recorded_cap_is_not_stale_above_reality` test re-pins it). T-010-33's
# reverse-direction `forbidden` contracts (core-no-upper-layers,
# infrastructure-no-upper-layers) add ZERO ignore edges — they freeze layers verified
# clean — so they do not move this number.
_RECORDED_IGNORE_EDGE_CAP = 17


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


def test_ignore_edge_count_does_not_exceed_recorded_cap() -> None:
    """The total ignored-import edge count must not grow past the recorded cap."""
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


def test_recorded_cap_is_not_stale_above_reality() -> None:
    """The recorded cap must equal the live total so a removed edge is re-pinned lower.

    This catches the *lowering* direction: if a DI cleanup deletes an ignored edge but the
    author forgets to lower ``_RECORDED_IGNORE_EDGE_CAP``, the cap would drift above reality
    and silently re-admit a future exception. The cap must track the true count exactly.
    """
    total = sum(len(v) for v in _ignore_edges_by_contract().values())
    assert total == _RECORDED_IGNORE_EDGE_CAP, (
        f"_RECORDED_IGNORE_EDGE_CAP={_RECORDED_IGNORE_EDGE_CAP} but setup.cfg has {total} "
        "ignored edges. If you removed an edge, LOWER the cap in this test to re-pin it "
        "(good — ratchet down). If you added one, see the cap-growth test's message."
    )


def test_every_ignored_edge_is_a_features_layering_exception() -> None:
    """Every ignored edge must be a ``features ->`` edge (the only sanctioned exceptions).

    The layering law's exceptions are exclusively about ``features`` reaching a concrete
    adapter while DI is incomplete. An ignored edge that does NOT start at
    ``dadaia_workspace.features`` would be a new, unrelated suppression smuggled into the
    list — fail loudly so it cannot hide among the documented feature-DI debt.
    """
    offenders: list[str] = []
    for section, section_edges in _ignore_edges_by_contract().items():
        for edge in section_edges:
            source = edge.split("->", 1)[0].strip()
            if not source.startswith("dadaia_workspace.features"):
                offenders.append(f"[{section}] {edge}")
    assert not offenders, (
        "ignored import edges that are not features-layering exceptions:\n" + "\n".join(offenders)
    )
