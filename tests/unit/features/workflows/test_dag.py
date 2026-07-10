"""Unit tests for dadaia_workspace.features.workflows.dag.

Coverage:
- Layouts (linear/parallel/cross-cutting/spec-refinement/single/cyclic): node/edge
  counts, layer assignment, well-formed XML — merged into one parametrized test.
- Node classes/attrs/accessibility (gate/placeholder/aria/data-*) — merged into one
  parametrized test.
- Stage-id XSS escaping (security) — kept named.
- T-45-01 optional node_meta enrichment.
"""

import xml.etree.ElementTree as ET

import pytest

from dadaia_workspace.features.workflows.dag import NODE_H_META, NodeMeta, render_dag_svg
from dadaia_workspace.features.workflows.service import StageDTO


def _parse_svg(svg: str) -> ET.Element:
    """Parse SVG string; raise on malformed XML."""
    return ET.fromstring(svg)


def _stage(
    id: str,
    agent: str,
    *,
    needs: list[str] | None = None,
    parallel_group: str | None = None,
    gate: bool = False,
) -> StageDTO:
    return StageDTO(
        id=id,
        agent=agent,
        needs=needs or [],
        parallel_group=parallel_group,
        gate=gate,
        expected_output_path=None,
        must_include=None,
        on_failure="stop",
    )


def _count_nodes(root: ET.Element) -> int:
    count = 0
    for elem in root.iter():
        cls = elem.get("class", "")
        if "dag-node" in cls:
            count += 1
    return count


def _count_edges(root: ET.Element) -> int:
    count = 0
    for elem in root.iter():
        cls = elem.get("class", "")
        if "dag-edge" in cls:
            count += 1
    return count


def _dag_nodes(root: ET.Element) -> list[ET.Element]:
    return [elem for elem in root.iter() if "dag-node" in elem.get("class", "")]


def _get_node_layers(root: ET.Element) -> dict[str, float]:
    """Return a mapping of stage-id → x-coordinate (proxy for layer assignment)."""
    layers: dict[str, float] = {}
    for elem in root.iter():
        cls = elem.get("class", "")
        if "dag-node" in cls:
            stage_id = elem.get("data-stage-id", "")
            transform = elem.get("transform", "")
            if "translate(" in transform:
                inner = transform.split("translate(")[1].split(")")[0]
                parts = inner.replace(" ", "").split(",")
                x = float(parts[0])
                layers[stage_id] = x
    return layers


_LINEAR_STAGES = [
    _stage("step_a", "product-engineer"),
    _stage("step_b", "software-engineer", needs=["step_a"]),
    _stage("step_c", "qa-engineer", needs=["step_b"]),
]

_PARALLEL_STAGES = [
    _stage("start", "product-engineer"),
    _stage("impl_a", "software-engineer", needs=["start"], parallel_group="impl"),
    _stage("impl_b", "frontend-engineer", needs=["start"], parallel_group="impl"),
    _stage("review", "qa-engineer", needs=["impl_a", "impl_b"], gate=True),
]

_CROSS_CUTTING_STAGES = [
    _stage("discovery", "product-engineer"),
    _stage("contract_review", "software-architect", needs=["discovery"], gate=True),
    _stage(
        "red_test_frontend", "qa-engineer", needs=["contract_review"], parallel_group="red_tests"
    ),
    _stage(
        "red_test_backend", "qa-engineer", needs=["contract_review"], parallel_group="red_tests"
    ),
    _stage(
        "green_frontend",
        "frontend-engineer",
        needs=["red_test_frontend"],
        parallel_group="green_impls",
    ),
    _stage(
        "green_backend",
        "backend-engineer",
        needs=["red_test_backend"],
        parallel_group="green_impls",
    ),
    _stage(
        "integration_validation",
        "qa-engineer",
        needs=["green_frontend", "green_backend"],
        gate=True,
    ),
]

_SPEC_REFINEMENT_STAGES = [
    _stage("discovery", "product-engineer", gate=True),
    _stage("arch_review", "software-architect", needs=["discovery"], parallel_group="specialists"),
    _stage("devops_review", "devops-engineer", needs=["discovery"], parallel_group="specialists"),
    _stage("qa_review", "qa-engineer", needs=["discovery"], parallel_group="specialists"),
    _stage(
        "frontend_review", "frontend-engineer", needs=["discovery"], parallel_group="specialists"
    ),
    _stage("backend_review", "backend-engineer", needs=["discovery"], parallel_group="specialists"),
    _stage(
        "synthesis",
        "product-engineer",
        needs=["arch_review", "devops_review", "qa_review", "frontend_review", "backend_review"],
        gate=True,
    ),
]

_CYCLIC_STAGES = [
    _stage("node_a", "product-engineer", needs=["node_b"]),
    _stage("node_b", "software-engineer", needs=["node_a"]),
]

_SINGLE_STAGE = [_stage("solo", "product-engineer")]


@pytest.mark.parametrize(
    ("case", "stages", "expect_nodes", "expect_edges", "layer_assertion"),
    [
        pytest.param(
            "linear-3-sequential",
            _LINEAR_STAGES,
            3,
            2,
            lambda layers: len(set(layers.values())) == 3,
            id="linear-workflow",
        ),
        pytest.param(
            "parallel-shared-layer",
            _PARALLEL_STAGES,
            4,
            4,
            lambda layers: layers["impl_a"] == layers["impl_b"],
            id="parallel-workflow",
        ),
        pytest.param(
            "cross-cutting-7-stages",
            _CROSS_CUTTING_STAGES,
            7,
            None,
            lambda layers: (
                layers["red_test_frontend"] == layers["red_test_backend"]
                and layers["green_frontend"] == layers["green_backend"]
            ),
            id="cross-cutting-workflow",
        ),
        pytest.param(
            "spec-refinement-specialist-layer",
            _SPEC_REFINEMENT_STAGES,
            7,
            None,
            lambda layers: (
                len(
                    {
                        layers[s]
                        for s in (
                            "arch_review",
                            "devops_review",
                            "qa_review",
                            "frontend_review",
                            "backend_review",
                        )
                    }
                )
                == 1
            ),
            id="spec-refinement-workflow",
        ),
        pytest.param("single-stage-no-edges", _SINGLE_STAGE, 1, 0, None, id="single-stage"),
        pytest.param(
            "cyclic-handled-gracefully", _CYCLIC_STAGES, 2, None, None, id="cyclic-stages"
        ),
        pytest.param("empty-stages", [], 0, 0, None, id="empty-stages"),
    ],
)
def test_layouts_matrix(case, stages, expect_nodes, expect_edges, layer_assertion) -> None:  # type: ignore[no-untyped-def]
    svg = render_dag_svg(stages)
    root = _parse_svg(svg)
    assert root is not None
    assert _count_nodes(root) == expect_nodes, f"{case}: node count"
    if expect_edges is not None:
        assert _count_edges(root) == expect_edges, f"{case}: edge count"
    if layer_assertion is not None:
        layers = _get_node_layers(root)
        assert layer_assertion(layers), f"{case}: layer assertion failed, layers={layers}"
    # Purity: identical output for identical inputs (checked once, on the linear case).
    if case == "linear-3-sequential":
        assert render_dag_svg(stages) == render_dag_svg(stages)


# ---------------------------------------------------------------------------
# Node classes/attrs/accessibility (gate/placeholder/aria/data-*) — 1 param
# ---------------------------------------------------------------------------


def test_gate_and_placeholder_classes_and_required_attributes() -> None:
    # gate node carries data-stage-id + dag-gate class; non-gate nodes never do.
    svg = render_dag_svg(_PARALLEL_STAGES)
    root = _parse_svg(svg)
    gate_nodes = [
        e
        for e in root.iter()
        if "dag-node" in e.get("class", "") and e.get("data-stage-id") == "review"
    ]
    assert len(gate_nodes) == 1
    assert "dag-gate" in gate_nodes[0].get("class", "")

    linear_svg = render_dag_svg(_LINEAR_STAGES)
    linear_root = _parse_svg(linear_svg)
    for elem in _dag_nodes(linear_root):
        assert "dag-gate" not in elem.get("class", "")
        assert elem.get("data-stage-id"), "Node missing data-stage-id"
        assert elem.get("data-agent"), "Node missing data-agent"
        assert elem.get("data-status") == "pending"
        assert elem.get("aria-label"), f"Node {elem.get('data-stage-id')!r} missing aria-label"

    # SVG root accessibility metadata.
    assert linear_root.get("role") == "img"
    has_title = any(
        (e.tag.split("}")[-1] if "}" in e.tag else e.tag) == "title" for e in linear_root.iter()
    )
    assert has_title
    assert linear_svg.lstrip().startswith("<svg")

    # placeholder agent ({{var}}) stage gets dag-placeholder class.
    placeholder_svg = render_dag_svg([_stage("impl", "{{implementer_agent}}")])
    placeholder_root = _parse_svg(placeholder_svg)
    placeholder_nodes = [
        e for e in placeholder_root.iter() if "dag-placeholder" in e.get("class", "")
    ]
    assert len(placeholder_nodes) >= 1

    # single gate-only stage: one node with BOTH dag-node and dag-gate.
    gate_only_svg = render_dag_svg([_stage("approval", "qa-engineer", gate=True)])
    gate_only_root = _parse_svg(gate_only_svg)
    nodes_with_gate = [
        e
        for e in gate_only_root.iter()
        if "dag-node" in e.get("class", "") and "dag-gate" in e.get("class", "")
    ]
    assert len(nodes_with_gate) == 1


# ---------------------------------------------------------------------------
# Security: stage-id and agent-name XSS escaping — kept named
# ---------------------------------------------------------------------------


def test_stage_id_and_agent_name_xss_is_escaped() -> None:
    """Stage id and agent name containing '<' must be HTML-escaped in SVG output."""
    svg1 = render_dag_svg([_stage("stage<script>", "agent&name")])
    assert "<script>" not in svg1
    assert _parse_svg(svg1) is not None

    svg2 = render_dag_svg([_stage("stage-id", "<evil>agent&name")])
    assert "<evil>" not in svg2
    assert _parse_svg(svg2) is not None


# ---------------------------------------------------------------------------
# T-45-01 — optional node_meta enrichment (AC-1 fluxogram)
# ---------------------------------------------------------------------------


def test_node_meta_draws_line_enriches_aria_and_is_html_escaped() -> None:
    """Without node_meta: render_dag_svg(stages) and render_dag_svg(stages, None) are
    byte-identical, and the SVG carries no node-meta text or style rule. With node_meta:
    a node carries a harness/model line, taller card height, an enriched aria-label,
    partial-map scoping, empty-fields suppression, escaping, and deterministic output."""
    fixtures = [_LINEAR_STAGES, _PARALLEL_STAGES, _CROSS_CUTTING_STAGES, []]
    for stages in fixtures:
        assert render_dag_svg(stages) == render_dag_svg(stages, None)

    no_meta_svg = render_dag_svg(_LINEAR_STAGES)
    assert "node-meta" not in no_meta_svg
    assert 'height="40"' in no_meta_svg
    assert f'height="{NODE_H_META}"' not in no_meta_svg

    meta = {"step_a": NodeMeta(harness="pi", model="kimi-2.7:high")}
    svg = render_dag_svg(_LINEAR_STAGES, meta)
    assert "node-meta" in svg
    assert "kimi-2.7:high" in svg
    assert "pi" in svg
    assert ".dag-node text.node-meta" in svg
    assert f'height="{NODE_H_META}"' in svg
    assert 'height="40"' not in svg
    assert _parse_svg(svg) is not None
    # partial map: exactly one node-meta text element (only step_a).
    assert svg.count('class="node-meta"') == 1
    # pure: identical output for identical inputs.
    assert render_dag_svg(_LINEAR_STAGES, meta) == svg

    meta_aria = {"step_b": NodeMeta(harness="codex", model="gpt-5.3-codex:high")}
    svg_aria = render_dag_svg(_LINEAR_STAGES, meta_aria)
    root = _parse_svg(svg_aria)
    labelled = [
        e
        for e in root.iter()
        if "dag-node" in e.get("class", "") and e.get("data-stage-id") == "step_b"
    ]
    assert labelled
    aria = labelled[0].get("aria-label", "")
    assert "codex" in aria
    assert "gpt-5.3-codex:high" in aria

    empty_meta = {"step_a": NodeMeta(harness="", model="")}
    svg_empty = render_dag_svg(_LINEAR_STAGES, empty_meta)
    assert 'class="node-meta"' not in svg_empty

    xss_meta = {"step_a": NodeMeta(harness="<x>", model="a&b")}
    svg_xss = render_dag_svg(_LINEAR_STAGES, xss_meta)
    assert "<x>" not in svg_xss
    assert _parse_svg(svg_xss) is not None
