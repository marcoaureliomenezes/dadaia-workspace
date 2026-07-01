"""Unit tests for dadaia_workspace.features.workflows.dag.

Coverage:
- Linear workflow (3 sequential stages): correct node count + edge count
- Parallel-group workflow: parallel stages assigned to same layer
- Gate stage: receives distinguishing markup (dag-gate class)
- Complex workflow (cross-cutting-feature fixture, 7 stages): renders without
  exception, expected node count
- SVG output is well-formed XML (parseable by xml.etree.ElementTree)
- Every node carries data-stage-id, data-agent, data-status="pending"
- SVG root element has role="img" and contains a <title> element
- Per-node aria-label present on every node
- Placeholder agent ({{var}}) stage renders with dag-placeholder class
"""

import xml.etree.ElementTree as ET

from dadaia_workspace.features.workflows.dag import NodeMeta, render_dag_svg
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
    """Count <g class="dag-node ..."> elements at any depth."""
    # ElementTree uses Clark notation for namespaced elements.
    # SVG elements have the SVG namespace.
    count = 0
    for elem in root.iter():
        cls = elem.get("class", "")
        if "dag-node" in cls:
            count += 1
    return count


def _count_edges(root: ET.Element) -> int:
    """Count elements with class 'dag-edge' at any depth."""
    count = 0
    for elem in root.iter():
        cls = elem.get("class", "")
        if "dag-edge" in cls:
            count += 1
    return count


def _find_nodes_with_attr(root: ET.Element, attr: str, value: str) -> list[ET.Element]:
    """Find all node elements where the given attribute equals value."""
    result = []
    for elem in root.iter():
        cls = elem.get("class", "")
        if "dag-node" in cls and elem.get(attr) == value:
            result.append(elem)
    return result


def _dag_nodes(root: ET.Element) -> list[ET.Element]:
    return [elem for elem in root.iter() if "dag-node" in elem.get("class", "")]


def _get_node_layers(root: ET.Element) -> dict[str, float]:
    """Return a mapping of stage-id → x-coordinate (proxy for layer assignment)."""
    layers: dict[str, float] = {}
    for elem in root.iter():
        cls = elem.get("class", "")
        if "dag-node" in cls:
            stage_id = elem.get("data-stage-id", "")
            # x-coordinate encodes the layer
            transform = elem.get("transform", "")
            if "translate(" in transform:
                # parse translate(x, y)
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
        "red_test_frontend",
        "qa-engineer",
        needs=["contract_review"],
        parallel_group="red_tests",
    ),
    _stage(
        "red_test_backend",
        "qa-engineer",
        needs=["contract_review"],
        parallel_group="red_tests",
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


def test_render_returns_string() -> None:
    """render_dag_svg is a pure function that returns a string."""
    result = render_dag_svg(_LINEAR_STAGES)
    assert isinstance(result, str)
    assert len(result) > 0


def test_render_empty_stages_returns_empty_svg() -> None:
    """Empty stage list returns a valid (minimal) SVG string."""
    result = render_dag_svg([])
    assert isinstance(result, str)
    # Must still parse as XML
    root = _parse_svg(result)
    assert root is not None


def test_render_is_pure_function() -> None:
    """Same input produces identical output (deterministic / pure)."""
    result_a = render_dag_svg(_LINEAR_STAGES)
    result_b = render_dag_svg(_LINEAR_STAGES)
    assert result_a == result_b


def test_linear_workflow_layout() -> None:
    """3 sequential stages render 3 nodes, 2 edges, and distinct layers."""
    svg = render_dag_svg(_LINEAR_STAGES)
    root = _parse_svg(svg)
    layers = _get_node_layers(root)
    assert _count_nodes(root) == 3
    assert _count_edges(root) == 2
    assert len(set(layers.values())) == 3, f"Expected 3 distinct layers, got: {layers}"


def test_parallel_workflow_layout() -> None:
    """Parallel stages share a layer and render the expected graph size."""
    svg = render_dag_svg(_PARALLEL_STAGES)
    root = _parse_svg(svg)
    layers = _get_node_layers(root)

    assert _count_nodes(root) == 4
    assert _count_edges(root) == 4
    impl_a_x = layers.get("impl_a")
    impl_b_x = layers.get("impl_b")
    assert impl_a_x is not None, "impl_a not found in SVG"
    assert impl_b_x is not None, "impl_b not found in SVG"
    assert impl_a_x == impl_b_x, (
        f"Parallel stages should share x-layer: impl_a={impl_a_x} impl_b={impl_b_x}"
    )


def test_gate_node_carries_stage_id_and_class() -> None:
    """Gate node carries data-stage-id and the dag-gate class modifier."""
    svg = render_dag_svg(_PARALLEL_STAGES)
    root = _parse_svg(svg)
    gate_nodes = _find_nodes_with_attr(root, "data-stage-id", "review")
    assert len(gate_nodes) == 1
    cls = gate_nodes[0].get("class", "")
    assert "dag-gate" in cls, f"Gate node class should contain dag-gate, got: {cls!r}"


def test_non_gate_nodes_do_not_carry_dag_gate() -> None:
    """Non-gate nodes must NOT have dag-gate class."""
    svg = render_dag_svg(_LINEAR_STAGES)
    root = _parse_svg(svg)
    for elem in root.iter():
        cls = elem.get("class", "")
        if "dag-node" in cls:
            assert "dag-gate" not in cls, (
                f"Non-gate node has dag-gate class: {elem.get('data-stage-id')!r}"
            )


def test_all_nodes_have_required_data_and_accessibility_attributes() -> None:
    """Every node carries stage, agent, pending status, and aria-label metadata."""
    svg = render_dag_svg(_LINEAR_STAGES)
    root = _parse_svg(svg)
    for elem in _dag_nodes(root):
        assert elem.get("data-stage-id"), "Node missing data-stage-id"
        assert elem.get("data-agent"), "Node missing data-agent"
        assert elem.get("data-status") == "pending", (
            f"Node {elem.get('data-stage-id')!r} has wrong data-status: {elem.get('data-status')!r}"
        )
        assert elem.get("aria-label"), f"Node {elem.get('data-stage-id')!r} missing aria-label"


def test_svg_root_has_accessibility_metadata() -> None:
    """SVG root has role='img', title metadata, and starts with the svg element."""
    svg = render_dag_svg(_LINEAR_STAGES)
    root = _parse_svg(svg)
    assert root.get("role") == "img", f"SVG role should be 'img', got: {root.get('role')!r}"
    has_title = False
    for elem in root.iter():
        local = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if local == "title":
            has_title = True
            break
    assert has_title, "SVG missing <title> element"
    assert svg.lstrip().startswith("<svg"), f"SVG does not start with <svg: {svg[:50]!r}"


def test_fixture_svgs_are_well_formed_xml() -> None:
    """Representative workflow SVGs parse as valid XML."""
    fixtures = [
        _LINEAR_STAGES,
        _PARALLEL_STAGES,
        _CROSS_CUTTING_STAGES,
        _SPEC_REFINEMENT_STAGES,
    ]
    for stages in fixtures:
        root = _parse_svg(render_dag_svg(stages))
        assert root is not None


def test_cross_cutting_workflow_layout() -> None:
    """Cross-cutting fixture renders expected graph size, gates, and parallel layers."""
    svg = render_dag_svg(_CROSS_CUTTING_STAGES)
    root = _parse_svg(svg)
    layers = _get_node_layers(root)

    assert _count_nodes(root) == 7
    gate_nodes = [
        elem
        for elem in root.iter()
        if "dag-node" in elem.get("class", "") and "dag-gate" in elem.get("class", "")
    ]
    assert len(gate_nodes) == 2, f"Expected 2 gate nodes, got {len(gate_nodes)}"
    assert layers["red_test_frontend"] == layers["red_test_backend"], (
        "red_tests group stages should share x-layer"
    )
    assert layers["green_frontend"] == layers["green_backend"], (
        "green_impls group stages should share x-layer"
    )


def test_spec_refinement_workflow_layout() -> None:
    """Spec-refinement fixture renders expected size and specialist layer."""
    svg = render_dag_svg(_SPEC_REFINEMENT_STAGES)
    root = _parse_svg(svg)
    layers = _get_node_layers(root)

    assert _count_nodes(root) == 7
    specialist_ids = [
        "arch_review",
        "devops_review",
        "qa_review",
        "frontend_review",
        "backend_review",
    ]
    specialist_xs = {sid: layers.get(sid) for sid in specialist_ids}
    assert all(x is not None for x in specialist_xs.values()), (
        f"Some specialist nodes not found in SVG: {specialist_xs}"
    )
    xs = list(specialist_xs.values())
    assert len(set(xs)) == 1, (  # type: ignore[arg-type]
        f"Specialists group stages should share x-layer, got: {specialist_xs}"
    )


def test_stage_id_xss_is_escaped() -> None:
    """Stage id containing '<' must be HTML-escaped in SVG output."""
    malicious_stages = [_stage("stage<script>", "agent&name")]
    svg = render_dag_svg(malicious_stages)
    assert "<script>" not in svg
    root = _parse_svg(svg)
    assert root is not None


def test_placeholder_agent_node_has_dag_placeholder_class() -> None:
    """A stage whose agent is a {{template_var}} gets class dag-placeholder."""
    placeholder_stages = [_stage("impl", "{{implementer_agent}}")]
    svg = render_dag_svg(placeholder_stages)
    root = _parse_svg(svg)
    placeholder_nodes = []
    for elem in root.iter():
        cls = elem.get("class", "")
        if "dag-placeholder" in cls:
            placeholder_nodes.append(elem)
    assert len(placeholder_nodes) >= 1, "Placeholder agent stage missing dag-placeholder class"


def test_cyclic_stages_render_without_exception() -> None:
    """Stages with a cycle are handled gracefully — no exception, valid SVG."""
    cyclic_stages = [
        _stage("node_a", "product-engineer", needs=["node_b"]),
        _stage("node_b", "software-engineer", needs=["node_a"]),
    ]
    svg = render_dag_svg(cyclic_stages)
    assert isinstance(svg, str)
    root = _parse_svg(svg)
    assert _count_nodes(root) == 2


def test_cyclic_stages_nodes_have_required_attributes() -> None:
    """Even cycle-affected nodes carry all required data attributes."""
    cyclic_stages = [
        _stage("cycle_x", "software-engineer", needs=["cycle_y"]),
        _stage("cycle_y", "qa-engineer", needs=["cycle_x"]),
    ]
    svg = render_dag_svg(cyclic_stages)
    root = _parse_svg(svg)
    for elem in root.iter():
        cls = elem.get("class", "")
        if "dag-node" in cls:
            assert elem.get("data-stage-id"), "Cyclic node missing data-stage-id"
            assert elem.get("data-agent"), "Cyclic node missing data-agent"
            assert elem.get("data-status") == "pending"


def test_single_stage_no_edges() -> None:
    """A single stage with no needs has no edges in the SVG."""
    single = [_stage("solo", "product-engineer")]
    svg = render_dag_svg(single)
    root = _parse_svg(svg)
    assert _count_nodes(root) == 1
    assert _count_edges(root) == 0


def test_agent_name_xss_is_escaped() -> None:
    """Agent name containing '<' is HTML-escaped in SVG output."""
    malicious_stages = [_stage("stage-id", "<evil>agent&name")]
    svg = render_dag_svg(malicious_stages)
    assert "<evil>" not in svg
    root = _parse_svg(svg)
    assert root is not None


def test_single_gate_node_has_correct_classes() -> None:
    """A single gate stage produces one node with both dag-node and dag-gate classes."""
    gate_only = [_stage("approval", "qa-engineer", gate=True)]
    svg = render_dag_svg(gate_only)
    root = _parse_svg(svg)
    assert _count_nodes(root) == 1
    nodes_with_gate = [
        e
        for e in root.iter()
        if "dag-node" in e.get("class", "") and "dag-gate" in e.get("class", "")
    ]
    assert len(nodes_with_gate) == 1


# ---------------------------------------------------------------------------
# T-45-01 — optional node_meta enrichment (AC-1 fluxogram)
# ---------------------------------------------------------------------------


def test_no_node_meta_output_is_byte_identical_to_positional_call() -> None:
    """render_dag_svg(stages) and render_dag_svg(stages, None) are byte-identical.

    The optional node_meta parameter defaults to None; the first-class detail view
    (which calls with no meta) must be byte-for-byte unchanged.
    """
    fixtures = [_LINEAR_STAGES, _PARALLEL_STAGES, _CROSS_CUTTING_STAGES, []]
    for stages in fixtures:
        assert render_dag_svg(stages) == render_dag_svg(stages, None)


def test_no_node_meta_output_has_no_meta_markup() -> None:
    """Without node_meta the SVG carries no node-meta text or style rule."""
    svg = render_dag_svg(_LINEAR_STAGES)
    assert "node-meta" not in svg
    # Default node height (40) is used — no taller-node meta layout.
    assert 'height="40"' in svg
    assert 'height="58"' not in svg


def test_node_meta_draws_harness_and_model_line() -> None:
    """With node_meta a node carries a node-meta line with harness · model."""
    meta = {"step_a": NodeMeta(harness="pi", model="kimi-2.7:high")}
    svg = render_dag_svg(_LINEAR_STAGES, meta)
    assert "node-meta" in svg
    assert "kimi-2.7:high" in svg
    assert "pi" in svg
    # The meta style rule is emitted only when meta is present.
    assert ".dag-node text.node-meta" in svg
    # Nodes are taller to fit the extra line.
    assert 'height="58"' in svg
    root = _parse_svg(svg)
    assert root is not None


def test_node_meta_enriches_aria_label() -> None:
    """A node with meta includes harness/model in its aria-label."""
    meta = {"step_b": NodeMeta(harness="codex", model="gpt-5.3-codex:high")}
    svg = render_dag_svg(_LINEAR_STAGES, meta)
    root = _parse_svg(svg)
    labelled = [
        e
        for e in root.iter()
        if "dag-node" in e.get("class", "") and e.get("data-stage-id") == "step_b"
    ]
    assert labelled
    aria = labelled[0].get("aria-label", "")
    assert "codex" in aria
    assert "gpt-5.3-codex:high" in aria


def test_node_meta_partial_map_only_enriches_present_stages() -> None:
    """Only stages present in node_meta get a meta line; others stay bare."""
    meta = {"step_a": NodeMeta(harness="pi", model="claude")}
    svg = render_dag_svg(_LINEAR_STAGES, meta)
    # Exactly one node-meta text element (step_a).
    assert svg.count('class="node-meta"') == 1


def test_node_meta_empty_fields_render_no_meta_line() -> None:
    """A NodeMeta with empty harness+model adds no meta text for that node."""
    meta = {"step_a": NodeMeta(harness="", model="")}
    svg = render_dag_svg(_LINEAR_STAGES, meta)
    assert 'class="node-meta"' not in svg


def test_node_meta_is_html_escaped() -> None:
    """Harness/model text in node_meta is HTML-escaped (OWASP A03)."""
    meta = {"step_a": NodeMeta(harness="<x>", model="a&b")}
    svg = render_dag_svg(_LINEAR_STAGES, meta)
    assert "<x>" not in svg
    root = _parse_svg(svg)
    assert root is not None


def test_node_meta_render_is_pure() -> None:
    """Same stages + same node_meta produce identical output."""
    meta = {"step_a": NodeMeta(harness="pi", model="kimi-2.7:high")}
    assert render_dag_svg(_LINEAR_STAGES, meta) == render_dag_svg(_LINEAR_STAGES, meta)
