"""Intent: CONTRACT — P-10 suppressed layering-edge cap (setup.cfg ignore_imports)

Import-linter ignore-edge **cap** contract (WS-R8 / AC-R8-04, release v0.1.10).

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
# (for example `agents.reader -> markdown_agent_store`)
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
# v0.3.0 DEMOLITION NOTE: deleting the workflow engine removed the whole
# `lifecycle-no-workflows` contract and 13 ignored edges (panel->lifecycle x4,
# panel->workflows x1, workflows->lifecycle x1, lifecycle->reports x1,
# lifecycle->backlog x5, cli.lifecycle->fake_runtime x1). Cap ratcheted 29 -> 16.
#
# v0.12.0 T-120-08 NOTE: `features.specs.doctor_governance -> features.backlog.document`
# added (SPEC PLAN §6) — the governance validator's SPEC-DOC-031/035 re-target reads the
# single-source `BACKLOG.md` through the pure `document.py` parser (leaf -> leaf) instead
# of duplicating a second parser inside `features/specs/`. Cap raised 15 -> 16
# (+1 features-no-cross-feature).
#
# v0.4.3 T-043-20/FR16 NOTE: `doctor_memory -> subprocess_runner` REMOVED from BOTH
# `features-no-infrastructure` and `features-no-subprocess` — LINT-1 no longer shells
# out at all (imports `features.specs.memory_lint` directly instead of subprocess-ing
# the projected `public/scripts/lint-memory-atoms.py`). Cap lowered 16 -> 14 (-2).
#
# v0.4.3 T-043-42/FR27 NOTE: `chokepoints.service -> infrastructure.jsonl_log_rotation`
# ADDED — the push-verdict-gc ledger appender funnels through the single shared
# rotation helper (a function-scoped lazy import, same ADR-1-style DI-pending idiom as
# the telemetry-lock edges already in this family). Cap raised 14 -> 15 (+1).
#
# v0.5.0 T-050-08 NOTE (FR2, AR-1 §2.4(v)): `cli.commands.bugs ->
# infrastructure.jsonl_bug_store` REMOVED — the CLI now obtains the bug-record store
# through `container.build_bug_record_store`/`build_bug_archive_store` (the sanctioned
# composition-root direction) instead of constructing the concrete infrastructure
# adapter directly, and `infrastructure/jsonl_bug_store.py` itself is deleted. Cap
# lowered 15 -> 14 (-1 cli-no-infrastructure).
#
# v0.5.0 specs-canon closure NOTE (operator ruling 2026-08-28):
# `chokepoints.service -> specs.specs_canon` ADDED — the pre-push specs-canon policy
# step reuses the SAME canon predicate module the doctor's TREE-8 check uses (one
# canon source, never a second hand-kept copy). Cap raised 17 -> 18
# (+1 features-no-cross-feature).
# v0.5.0 T-050-29 NOTE (FR18/A18.5, V32): the `features-no-cross-feature` contract's
# `modules =` was measurably incomplete (20 of the 24 `dadaia_workspace/features/*/`
# packages on disk) — the missing four (`capabilities`, `certification`, `reconcile`,
# `tmp_gc`) were added, which makes import-linter analyze `reconcile/service.py`'s three
# pre-existing cross-feature imports for the first time: `-> capabilities`,
# `-> migrate.legacy_dadaia_dirs`, `-> migrate.state_v2`. Each is declared as a capped,
# documented `ignore_imports` edge with its own reason comment (collapsing them is a
# `reconcile` feature rewrite, routed to intake — not attempted here). Cap raised
# 14 -> 17 (+3 features-no-cross-feature) in the same commit as `setup.cfg`.
#
# v0.5.1 K7 NOTE ("split chokepoints.service into its four modules; one verdict
# store"): three `chokepoints.service ->` edges REMOVED. `-> infrastructure.
# jsonl_log_rotation` (features-no-infrastructure): the push-verdict GC lane it served
# (`gc_consumed_push_verdicts`, `dadaia ci gc-push-verdicts`) is deleted outright — it
# read a `.dadaia/handoff/` store no verdict reader consults any more (the committed
# `specs/releases/**/verdicts/` tree is the ONE verdict store,
# `features.chokepoints.verdict.covering_verdict`). `-> spec_context.presence` and
# `-> specs.canon` (both features-no-cross-feature): the split `pre_commit.py`/
# `push_gate.py` modules now receive `others_alive`/`canon_violations_fn`/
# `verdict_violations_fn` as INJECTED callables instead of importing them at module
# scope — the CLI composition root wires the real functions straight through, no
# adapter needed (mirroring `push_gate_decision`'s pre-existing `object_source`
# injection, FR7/A7.2). Cap lowered 18 -> 15 (-1 features-no-infrastructure, -2
# features-no-cross-feature) in the same commit as `setup.cfg`. A fourth edge,
# `cli.commands.ci -> infrastructure.process_probe_adapter` (cli-no-infrastructure),
# is ALSO removed in the same K7 commit: `pre_commit_check` no longer wires a
# pid-liveness probe (the dead params it served are deleted). Cap lowered 15 -> 14
# (-1 cli-no-infrastructure).
#
# ADR-0001 NOTE (protocol retirement — one adapter, no port): `features-no-infrastructure`
# (6 edges) and `cli-no-infrastructure` (1 edge) contracts are DELETED outright — the port
# requirement they enforced is retired; a feature/CLI verb now imports its sole concrete
# infrastructure adapter directly (`tests/contract/test_protocols_have_two_adapters.py`
# polices the remaining Protocol set instead). `features-no-subprocess` (P-02) stays and
# gains 4 new documented edges for the same reason: GitClient/CertificationProcess had one
# adapter each (`git_subprocess`/`certification_process`, both `subprocess`-backed) —
# `spec_context.service`, `spec_context.doctor`, `export.service` -> `git_subprocess`, and
# `certification.service` -> `certification_process`. Cap 14 -> 11
# (-6 features-no-infrastructure, -1 cli-no-infrastructure, +4 features-no-subprocess).
#
# ADR-0001 NOTE 2 (same retirement, PublicAssetManager/PythonEnvironmentManager): both
# single-adapter (`public_assets`/`python_env`, both `subprocess`-backed at install time) —
# `public.service`/`workspace.service` -> `public_assets`, `workspace.service` ->
# `python_env`. Cap 11 -> 14 (+3 features-no-subprocess).
#
# ADR-0001 NOTE 3 (same retirement, GitObjectReader/GitHistoryReader): GitObjectReader
# stays a container.py seam (build_git_object_reader — genuinely shared by two CLI verbs,
# ci.push_gate_check and specs.doctor's head/parent-sha resolution) so it adds no NEW
# features->infrastructure edge; its pure data shapes (ScannedObject/GitObjectReadError/
# ZERO_SHA) move to core/models/git_scan.py (zero I/O) so the security-sensitive
# features.chokepoints.push_gate (which must NEVER import infrastructure/subprocess, even
# transitively) can still type `object_source` structurally via a feature-local Protocol
# (`ObjectSource`) instead. GitHistoryReader (single adapter, GitSubprocessClient — reused
# from GitClient's own retirement) had no real production caller (only a test); its
# `history_reader` consumer, bugs.service, imports the concrete class directly, +1 edge.
# HistoryCommit/GitHistoryReadError move to core/models/git_history.py for the same
# zero-I/O reason. Cap 14 -> 15 (+1 features-no-subprocess).
#
# 0.4.6 T-046-26 NOTE (FR4/AC15): `reconcile.service -> migrate.legacy_dadaia_dirs`
# REMOVED — the legacy-dir quarantine module is deleted (its set is "not in the
# registry", which `dadaia doctor` now reports as WS-dadaia-slop), so the reconcile
# step and its ignored edge die together. Cap lowered 4 -> 3 (-1 features-no-cross-feature).
_RECORDED_IGNORE_EDGE_CAP = 3

# Per-family recorded breakdown, pinned per contract section so a wrong edge-count set
# (or a silent shift between families) fails loudly, not just the grand total.
_RECORDED_PER_FAMILY_CAP: dict[str, int] = {
    "features-no-cross-feature": 3,
}

# A18.1 (V13): the total count of `[importlinter:contract:*]` sections in setup.cfg,
# pinned so a tenth contract added without a matching Part-1 principle in
# specs/memory/ARCHITECTURE.md goes RED here first (the test at the bottom of this
# file). Raising this requires the same discipline as the ignore-edge cap: a new
# contract AND a bump of this constant, in the same commit, with the new principle
# authored alongside it (FR18/A18.1) — not attempted in this task (T-050-29's
# mechanical half writes zero new contracts).
# ADR-0001: features-no-infrastructure and cli-no-infrastructure DELETED. 9 -> 7.
_RECORDED_CONTRACT_COUNT = 7


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
    """Every ignored edge must originate from ``dadaia_workspace.features``.

    ADR-0001 retired the ``cli-no-infrastructure`` family (the CLI now imports
    infrastructure freely — no port, no container detour required), so the two
    remaining families (``features-no-subprocess``, ``features-no-cross-feature``) both
    keep a ``dadaia_workspace.features`` source. An ignored edge whose source is not a
    ``features`` module would be a new, unrelated suppression smuggled into the list —
    fail loudly so it cannot hide among the documented layering debt.
    """
    offenders = [
        f"[{section}] {edge}"
        for section, section_edges in by_contract.items()
        for edge in section_edges
        if not edge.split("->", 1)[0].strip().startswith("dadaia_workspace.features")
    ]
    assert not offenders, (
        "ignored import edges that are not features-layering exceptions:\n" + "\n".join(offenders)
    )


# --- A18.5/V32 — the independence contract is complete before promotion --------------


def test_cross_feature_contract_modules_equals_disk_and_contract_count_is_pinned() -> None:
    """Intent: CONTRACT — 0.5.0 A18.5.

    V32: the ``features-no-cross-feature`` contract's ``modules =`` list must equal
    every ``dadaia_workspace/features/<name>/`` package on disk. A principle
    ("features are mutually independent", FR18) whose ``Measured by:`` check cannot see
    every feature package is decoration, not a contract — this test is what makes that
    impossible to author unnoticed: a package added to ``dadaia_workspace/features/``
    tomorrow without a matching ``modules =`` line goes RED here (T-050-29 completed the
    list 20 -> 24: ``capabilities``, ``certification``, ``reconcile``, ``tmp_gc`` added).

    Same function also pins the total number of ``[importlinter:contract:*]`` sections
    in ``setup.cfg`` (A18.1) — a tenth contract added without a matching Part-1 principle
    (and without bumping ``_RECORDED_CONTRACT_COUNT`` above) goes RED here too. One
    function, not two (SPEC v0.5.0 FR18 bug-surface paragraph).
    """
    features_dir = _REPO_ROOT / "dadaia_workspace" / "features"
    on_disk_packages = {
        f"dadaia_workspace.features.{p.name}"
        for p in features_dir.iterdir()
        if p.is_dir() and p.name != "__pycache__" and (p / "__init__.py").is_file()
    }
    assert (
        len(on_disk_packages) == 19
    )  # 0.4.6 T-046-26 (23 -> 21), T-046-28 (21 -> 20), T-046-25 reports pkg (20 -> 19)

    parser = configparser.ConfigParser()
    read = parser.read(_SETUP_CFG, encoding="utf-8")
    assert read, f"setup.cfg not found at {_SETUP_CFG}"

    raw_modules = parser["importlinter:contract:features-no-cross-feature"]["modules"]
    declared_modules = {line.strip() for line in raw_modules.splitlines() if line.strip()}
    assert declared_modules == on_disk_packages, (
        "features-no-cross-feature's modules = list drifted from the packages on disk "
        f"(missing from setup.cfg: {sorted(on_disk_packages - declared_modules)}; "
        f"stale in setup.cfg: {sorted(declared_modules - on_disk_packages)}). A18.5/V32: "
        "the independence contract must see every feature package before the 'features "
        "are mutually independent' principle is authored."
    )

    contract_sections = [s for s in parser.sections() if s.startswith("importlinter:contract:")]
    assert len(contract_sections) == _RECORDED_CONTRACT_COUNT, (
        f"setup.cfg carries {len(contract_sections)} [importlinter:contract:*] sections "
        f"but the pinned inventory count is {_RECORDED_CONTRACT_COUNT} (A18.1). A new "
        "contract requires a matching Part-1 principle in specs/memory/ARCHITECTURE.md "
        "before this pin is raised, in the same commit."
    )
