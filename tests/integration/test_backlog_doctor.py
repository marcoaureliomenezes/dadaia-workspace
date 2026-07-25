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
from dadaia_workspace.features.spec_artifacts.new_artifacts import backlog_new

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


def test_driving_fake_canary_item_is_doctor_valid(tmp_path: Path) -> None:
    """Bug fake-backlog-workflow-materializes-doctor-invalid-status-042 (Hermes R1-B):
    the backlog-definition driving fake materialized `status: proposed`, a token
    outside the documented vocabulary — the workflow's own output failed the
    workflow's own doctor. Producer and validator must agree on the status set."""
    from dadaia_workspace.container import _backlog_definition_runtime_factory
    from dadaia_workspace.core.models.lifecycle import AgentRunRequest, AgentRuntimeKind

    specs, src = _build_specs(tmp_path)
    factory = _backlog_definition_runtime_factory(context="ctx", run_cwd=tmp_path)
    fake = factory(AgentRuntimeKind.FAKE)
    fake.run(
        AgentRunRequest(
            role="product-engineer",
            prompt="author the item",
            runtime=AgentRuntimeKind.FAKE,
            context="ctx",
            release_id="v0.1.0",
            task_id="bd-canary:backlog_author",
        )
    )
    # The slug is run-scoped (bug fake-backlog-canary-fixed-slug-blocks-multi-item-release-flow).
    item = specs / "backlog" / "dadaia-fake-harness-canary-bd-canary.md"
    assert item.is_file(), "driving fake must materialize the canary item"

    findings = run_backlog_doctor(
        specs_dir=specs,
        source_root=src,
        catalog_path=specs / "memory" / "product" / "catalog.json",
        alias_map_path=specs / "no-aliases.txt",
        archive_root=specs / "_archive",
        cli_anchors=frozenset({"backlog doctor"}),
    )
    invalid = [f for f in findings if "invalid status" in f.message]
    assert not invalid, [f.message for f in invalid]


def _run(specs: Path, src: Path) -> list:
    return run_backlog_doctor(
        specs_dir=specs,
        source_root=src,
        catalog_path=specs / "memory" / "product" / "catalog.json",
        alias_map_path=specs / "no-aliases.txt",
        archive_root=specs / "_archive",
        cli_anchors=frozenset(),
    )


# ── one parameterized matrix over the four BL-* checks (SPEC §3.8 #8) ─────────────


def _plant_schema(specs: Path, src: Path) -> None:
    # A CANDIDATE item with an UNRESOLVED subject (no such symbol) → BL-SCHEMA.
    # v0.1.55 FR5: the unresolved-subject error is status-gated — an `idea` is exempt, so the
    # violation must be planted at `candidate` (or beyond) for the check to fire.
    (specs / "backlog" / "bad-schema.md").write_text(
        "---\nstatus: candidate\n"
        "intents:\n  - subject: { kind: code, ref: pkg/m.py#NoSuchSymbol }\n    change: x\n"
        "---\n\n# bad-schema\n",
        encoding="utf-8",
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


def test_clean_tree_matrix_each_violation_flagged_stale_noop_and_fresh_stub_status_gate(
    tmp_path: Path,
) -> None:
    """One fn: clean-tree zero findings + parametrized BL-SCHEMA/DUP/CONFLICT/STALE
    planters (each ERRORs) + stale-noop-without-ledger (never a false ERROR, §3.7.6).

    Plus (own workspace, v0.1.55 FR5): a fresh ``dadaia backlog new`` stub (status:
    idea, no intents, no catalog.json) is doctor-clean: zero BL-SCHEMA errors. AC-7(e):
    the SAME stub flipped to ``status: candidate`` FIRES BL-SCHEMA (a candidate
    carrying no intents is not exempt) — proving the gate is status-gated, not a
    blanket exemption.
    """
    specs, src = _build_specs(tmp_path)
    _write_item(specs, "clean-one", _VALID_INTENT_WIDGET)
    _write_item(
        specs,
        "clean-two",
        "intents:\n  - subject: { kind: code, ref: pkg/m.py#Gadget }\n    change: tweak Gadget\n",
    )
    findings = _run(specs, src)
    assert findings == [], [f.to_dict() for f in findings]

    for planter, expected_code in [
        (_plant_schema, BacklogDoctorCode.BL_SCHEMA),
        (_plant_dup, BacklogDoctorCode.BL_DUP),
        (_plant_conflict, BacklogDoctorCode.BL_CONFLICT),
        (_plant_stale, BacklogDoctorCode.BL_STALE),
    ]:
        case_specs, case_src = _build_specs(tmp_path / f"case-{expected_code.value}")
        planter(case_specs, case_src)  # type: ignore[operator]
        case_findings = _run(case_specs, case_src)
        codes = {f.code for f in case_findings}
        assert expected_code in codes, [f.to_dict() for f in case_findings]
        assert all(f.severity is Severity.ERROR for f in case_findings if f.code is expected_code)

    noop_specs, noop_src = _build_specs(tmp_path / "no-ledger-case")
    _write_item(noop_specs, "live-feature", _VALID_INTENT_WIDGET)
    noop_findings = _run(noop_specs, noop_src)
    assert not any(f.code is BacklogDoctorCode.BL_STALE for f in noop_findings)

    # Fresh-stub status gate: no catalog.json, real backlog_new + real doctor engine.
    fresh_specs = tmp_path / "fresh-stub-case" / "specs"
    fresh_specs.mkdir(parents=True)
    fresh_src = tmp_path / "fresh-stub-case" / "src"
    fresh_src.mkdir()

    def _run_fresh_doctor() -> list:
        return run_backlog_doctor(
            specs_dir=fresh_specs,
            source_root=fresh_src,
            catalog_path=fresh_specs / "memory" / "product" / "catalog.json",  # absent
            alias_map_path=fresh_specs / "no-aliases.txt",  # absent → tolerated
            archive_root=fresh_specs / "_archive",  # absent → BL-STALE no-op
            cli_anchors=frozenset(),
        )

    result = backlog_new(fresh_specs, "my-fresh-idea")
    assert result.path.is_file()

    fresh_findings = _run_fresh_doctor()
    fresh_schema = [f for f in fresh_findings if f.code is BacklogDoctorCode.BL_SCHEMA]
    assert fresh_schema == [], [f.to_dict() for f in fresh_schema]

    text = result.path.read_text(encoding="utf-8")
    assert "status: idea" in text
    result.path.write_text(text.replace("status: idea", "status: candidate"), encoding="utf-8")

    fresh_schema2 = [f for f in _run_fresh_doctor() if f.code is BacklogDoctorCode.BL_SCHEMA]
    assert fresh_schema2, (
        "a candidate with no intents[] must fire BL-SCHEMA (status-gate not blanket)"
    )


def test_distinct_runs_author_distinct_non_colliding_items(tmp_path: Path) -> None:
    """Bug fake-backlog-canary-fixed-slug-blocks-multi-item-release-flow.

    The fake upserted ONE hardcoded slug, so three runs reporting success left one item on
    disk — each silently overwriting the previous. That made the documented flow the
    operator actually validates (author N backlog items, then define one release consuming
    the set) unreachable with the fake, i.e. unreachable without spending Layer-2 credits.

    Two properties are required together, and the second is why a naive per-run slug is not
    enough: items sharing a canonical anchor with differing ``change`` text are a
    fail-closed ``DIVERGENT_CONFLICT``, so per-run items must also claim per-run anchors.
    """
    from dadaia_workspace.container import _backlog_definition_runtime_factory
    from dadaia_workspace.core.models.lifecycle import AgentRunRequest, AgentRuntimeKind

    specs, _src = _build_specs(tmp_path)
    factory = _backlog_definition_runtime_factory(context="ctx", run_cwd=tmp_path)
    fake = factory(AgentRuntimeKind.FAKE)

    def _author(run_id: str) -> None:
        fake.run(
            AgentRunRequest(
                role="product-engineer",
                prompt="author the item",
                runtime=AgentRuntimeKind.FAKE,
                context="ctx",
                release_id="v0.1.0",
                task_id=f"{run_id}:backlog_author",
            )
        )

    for run_id in ("bl-1", "bl-2", "bl-3"):
        _author(run_id)

    items = sorted(p for p in (specs / "backlog").glob("*.md") if p.name != "README.md")
    assert len(items) == 3, (
        "three runs must leave three items on disk; "
        f"found {[p.name for p in items]} — a run silently overwrote another's deliverable"
    )

    # Each item must claim a DIFFERENT anchor, else the pair is DIVERGENT_CONFLICT and a
    # release can never consume the set.
    anchors = [
        line.split("ref:", 1)[1].strip()
        for item in items
        for line in item.read_text(encoding="utf-8").splitlines()
        if "ref:" in line
    ]
    assert len(anchors) == 3, anchors
    assert len(set(anchors)) == 3, f"items must not collide on one anchor: {anchors}"

    # Re-running the SAME run id stays an idempotent EDIT of that run's own item — the
    # property the original fixed slug was protecting.
    before = {p.name for p in items}
    _author("bl-2")
    after = {p.name for p in (specs / "backlog").glob("*.md") if p.name != "README.md"}
    assert after == before, f"re-run must not create a new item: {after - before}"
