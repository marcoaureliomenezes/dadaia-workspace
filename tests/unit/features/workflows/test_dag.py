"""Unit tests for dadaia_workspace.features.workflows.dag.

TDD — written before the implementation; all tests must fail first, then pass.

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

import time
import xml.etree.ElementTree as ET

import pytest

from dadaia_workspace.features.workflows.dag import render_dag_svg
from dadaia_workspace.features.workflows.service import StageDTO


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_svg(svg: str) -> ET.Element:
    """Parse SVG string; raise on malformed XML."""
    return ET.fromstring(svg)


def _count_nodes(root: ET.Element) -> int:
    """Count <g class="dag-node ..."> elements at any depth."""
    ns = {"svg": "http://www.w3.org/2000/svg"}
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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_LINEAR_STAGES = [
    StageDTO(
        id="step_a",
        agent="product-engineer",
        needs=[],
        parallel_group=None,
        gate=False,
        expected_output_path=None,
        must_include=None,
        on_failure="stop",
    ),
    StageDTO(
        id="step_b",
        agent="software-engineer",
        needs=["step_a"],
        parallel_group=None,
        gate=False,
        expected_output_path=None,
        must_include=None,
        on_failure="stop",
    ),
    StageDTO(
        id="step_c",
        agent="qa-engineer",
        needs=["step_b"],
        parallel_group=None,
        gate=False,
        expected_output_path=None,
        must_include=None,
        on_failure="stop",
    ),
]

_PARALLEL_STAGES = [
    StageDTO(
        id="start",
        agent="product-engineer",
        needs=[],
        parallel_group=None,
        gate=False,
        expected_output_path=None,
        must_include=None,
        on_failure="stop",
    ),
    StageDTO(
        id="impl_a",
        agent="software-engineer",
        needs=["start"],
        parallel_group="impl",
        gate=False,
        expected_output_path=None,
        must_include=None,
        on_failure="stop",
    ),
    StageDTO(
        id="impl_b",
        agent="frontend-engineer",
        needs=["start"],
        parallel_group="impl",
        gate=False,
        expected_output_path=None,
        must_include=None,
        on_failure="stop",
    ),
    StageDTO(
        id="review",
        agent="qa-engineer",
        needs=["impl_a", "impl_b"],
        parallel_group=None,
        gate=True,
        expected_output_path=None,
        must_include=None,
        on_failure="stop",
    ),
]

# cross-cutting-feature equivalent: 7 stages, 2 parallel groups, 2 gates
_CROSS_CUTTING_STAGES = [
    StageDTO(
        id="discovery",
        agent="product-engineer",
        needs=[],
        parallel_group=None,
        gate=False,
        expected_output_path=None,
        must_include=None,
        on_failure="stop",
    ),
    StageDTO(
        id="contract_review",
        agent="software-architect",
        needs=["discovery"],
        parallel_group=None,
        gate=True,  # gate stage
        expected_output_path=None,
        must_include=None,
        on_failure="stop",
    ),
    StageDTO(
        id="red_test_frontend",
        agent="qa-engineer",
        needs=["contract_review"],
        parallel_group="red_tests",
        gate=False,
        expected_output_path=None,
        must_include=None,
        on_failure="stop",
    ),
    StageDTO(
        id="red_test_backend",
        agent="qa-engineer",
        needs=["contract_review"],
        parallel_group="red_tests",
        gate=False,
        expected_output_path=None,
        must_include=None,
        on_failure="stop",
    ),
    StageDTO(
        id="green_frontend",
        agent="frontend-engineer",
        needs=["red_test_frontend"],
        parallel_group="green_impls",
        gate=False,
        expected_output_path=None,
        must_include=None,
        on_failure="stop",
    ),
    StageDTO(
        id="green_backend",
        agent="backend-engineer",
        needs=["red_test_backend"],
        parallel_group="green_impls",
        gate=False,
        expected_output_path=None,
        must_include=None,
        on_failure="stop",
    ),
    StageDTO(
        id="integration_validation",
        agent="qa-engineer",
        needs=["green_frontend", "green_backend"],
        parallel_group=None,
        gate=True,  # gate stage
        expected_output_path=None,
        must_include=None,
        on_failure="stop",
    ),
]

# spec-refinement equivalent: 7 stages, 1 wide parallel group (5 nodes), 2 gates
_SPEC_REFINEMENT_STAGES = [
    StageDTO(
        id="discovery",
        agent="product-engineer",
        needs=[],
        parallel_group=None,
        gate=True,  # gate at end of discovery
        expected_output_path=None,
        must_include=None,
        on_failure="stop",
    ),
    StageDTO(
        id="arch_review",
        agent="software-architect",
        needs=["discovery"],
        parallel_group="specialists",
        gate=False,
        expected_output_path=None,
        must_include=None,
        on_failure="stop",
    ),
    StageDTO(
        id="devops_review",
        agent="devops-engineer",
        needs=["discovery"],
        parallel_group="specialists",
        gate=False,
        expected_output_path=None,
        must_include=None,
        on_failure="stop",
    ),
    StageDTO(
        id="qa_review",
        agent="qa-engineer",
        needs=["discovery"],
        parallel_group="specialists",
        gate=False,
        expected_output_path=None,
        must_include=None,
        on_failure="stop",
    ),
    StageDTO(
        id="frontend_review",
        agent="frontend-engineer",
        needs=["discovery"],
        parallel_group="specialists",
        gate=False,
        expected_output_path=None,
        must_include=None,
        on_failure="stop",
    ),
    StageDTO(
        id="backend_review",
        agent="backend-engineer",
        needs=["discovery"],
        parallel_group="specialists",
        gate=False,
        expected_output_path=None,
        must_include=None,
        on_failure="stop",
    ),
    StageDTO(
        id="synthesis",
        agent="product-engineer",
        needs=["arch_review", "devops_review", "qa_review", "frontend_review", "backend_review"],
        parallel_group=None,
        gate=True,
        expected_output_path=None,
        must_include=None,
        on_failure="stop",
    ),
]


# ---------------------------------------------------------------------------
# Tests: basic contract
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Tests: linear workflow
# ---------------------------------------------------------------------------


def test_linear_node_count() -> None:
    """3 sequential stages → 3 nodes."""
    svg = render_dag_svg(_LINEAR_STAGES)
    root = _parse_svg(svg)
    assert _count_nodes(root) == 3


def test_linear_edge_count() -> None:
    """3 sequential stages → 2 edges (a→b, b→c)."""
    svg = render_dag_svg(_LINEAR_STAGES)
    root = _parse_svg(svg)
    assert _count_edges(root) == 2


def test_linear_layers_are_distinct() -> None:
    """Each stage in a linear chain occupies a distinct x-layer."""
    svg = render_dag_svg(_LINEAR_STAGES)
    root = _parse_svg(svg)
    layers = _get_node_layers(root)
    assert len(set(layers.values())) == 3, f"Expected 3 distinct layers, got: {layers}"


# ---------------------------------------------------------------------------
# Tests: parallel-group workflow
# ---------------------------------------------------------------------------


def test_parallel_stages_same_layer() -> None:
    """Parallel stages (same parallel_group) share the same x-coordinate layer."""
    svg = render_dag_svg(_PARALLEL_STAGES)
    root = _parse_svg(svg)
    layers = _get_node_layers(root)

    impl_a_x = layers.get("impl_a")
    impl_b_x = layers.get("impl_b")
    assert impl_a_x is not None, "impl_a not found in SVG"
    assert impl_b_x is not None, "impl_b not found in SVG"
    assert impl_a_x == impl_b_x, (
        f"Parallel stages should share x-layer: impl_a={impl_a_x} impl_b={impl_b_x}"
    )


def test_parallel_node_count() -> None:
    """4-stage parallel workflow → 4 nodes."""
    svg = render_dag_svg(_PARALLEL_STAGES)
    root = _parse_svg(svg)
    assert _count_nodes(root) == 4


def test_parallel_edge_count() -> None:
    """start→impl_a, start→impl_b, impl_a→review, impl_b→review = 4 edges."""
    svg = render_dag_svg(_PARALLEL_STAGES)
    root = _parse_svg(svg)
    assert _count_edges(root) == 4


# ---------------------------------------------------------------------------
# Tests: gate stage
# ---------------------------------------------------------------------------


def test_gate_node_has_dag_gate_class() -> None:
    """Gate stage node must carry the dag-gate class modifier."""
    svg = render_dag_svg(_PARALLEL_STAGES)
    root = _parse_svg(svg)
    gate_nodes = []
    for elem in root.iter():
        cls = elem.get("class", "")
        if "dag-gate" in cls:
            gate_nodes.append(elem)
    assert len(gate_nodes) >= 1, "Expected at least one element with class dag-gate"


def test_gate_node_carries_stage_id() -> None:
    """Gate node carries data-stage-id of the gate stage."""
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


# ---------------------------------------------------------------------------
# Tests: data attributes on nodes
# ---------------------------------------------------------------------------


def test_all_nodes_have_data_stage_id() -> None:
    """Every node <g class='dag-node'> must have data-stage-id."""
    svg = render_dag_svg(_LINEAR_STAGES)
    root = _parse_svg(svg)
    for elem in root.iter():
        cls = elem.get("class", "")
        if "dag-node" in cls:
            assert elem.get("data-stage-id"), (
                "Node missing data-stage-id"
            )


def test_all_nodes_have_data_agent() -> None:
    """Every node must have data-agent."""
    svg = render_dag_svg(_LINEAR_STAGES)
    root = _parse_svg(svg)
    for elem in root.iter():
        cls = elem.get("class", "")
        if "dag-node" in cls:
            assert elem.get("data-agent"), "Node missing data-agent"


def test_all_nodes_have_data_status_pending() -> None:
    """Every node must have data-status='pending' (future highlighting hook)."""
    svg = render_dag_svg(_LINEAR_STAGES)
    root = _parse_svg(svg)
    for elem in root.iter():
        cls = elem.get("class", "")
        if "dag-node" in cls:
            assert elem.get("data-status") == "pending", (
                f"Node {elem.get('data-stage-id')!r} has wrong data-status: "
                f"{elem.get('data-status')!r}"
            )


def test_all_nodes_have_aria_label() -> None:
    """Every node must have aria-label per SPEC §7.5 / D14."""
    svg = render_dag_svg(_LINEAR_STAGES)
    root = _parse_svg(svg)
    for elem in root.iter():
        cls = elem.get("class", "")
        if "dag-node" in cls:
            assert elem.get("aria-label"), (
                f"Node {elem.get('data-stage-id')!r} missing aria-label"
            )


# ---------------------------------------------------------------------------
# Tests: SVG accessibility metadata
# ---------------------------------------------------------------------------


def test_svg_has_role_img() -> None:
    """SVG root must have role='img' per SPEC D14."""
    svg = render_dag_svg(_LINEAR_STAGES)
    root = _parse_svg(svg)
    assert root.get("role") == "img", f"SVG role should be 'img', got: {root.get('role')!r}"


def test_svg_has_title_element() -> None:
    """SVG must contain a <title> element per SPEC D14."""
    svg = render_dag_svg(_LINEAR_STAGES)
    root = _parse_svg(svg)
    has_title = False
    for elem in root.iter():
        local = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if local == "title":
            has_title = True
            break
    assert has_title, "SVG missing <title> element"


def test_svg_starts_with_svg_tag() -> None:
    """SVG string must start with <svg."""
    svg = render_dag_svg(_LINEAR_STAGES)
    assert svg.lstrip().startswith("<svg"), f"SVG does not start with <svg: {svg[:50]!r}"


# ---------------------------------------------------------------------------
# Tests: well-formed XML
# ---------------------------------------------------------------------------


def test_linear_svg_is_well_formed_xml() -> None:
    """Linear workflow SVG must parse as valid XML."""
    svg = render_dag_svg(_LINEAR_STAGES)
    root = _parse_svg(svg)  # raises ParseError if invalid
    assert root is not None


def test_parallel_svg_is_well_formed_xml() -> None:
    """Parallel workflow SVG must parse as valid XML."""
    svg = render_dag_svg(_PARALLEL_STAGES)
    root = _parse_svg(svg)
    assert root is not None


def test_complex_cross_cutting_svg_is_well_formed_xml() -> None:
    """cross-cutting-feature equivalent SVG must parse as valid XML."""
    svg = render_dag_svg(_CROSS_CUTTING_STAGES)
    root = _parse_svg(svg)
    assert root is not None


def test_spec_refinement_svg_is_well_formed_xml() -> None:
    """spec-refinement equivalent SVG must parse as valid XML."""
    svg = render_dag_svg(_SPEC_REFINEMENT_STAGES)
    root = _parse_svg(svg)
    assert root is not None


# ---------------------------------------------------------------------------
# Tests: complex workflows — correctness
# ---------------------------------------------------------------------------


def test_cross_cutting_node_count() -> None:
    """cross-cutting-feature: 7 stages → 7 nodes."""
    svg = render_dag_svg(_CROSS_CUTTING_STAGES)
    root = _parse_svg(svg)
    assert _count_nodes(root) == 7


def test_cross_cutting_parallel_groups_same_layer() -> None:
    """cross-cutting-feature: red_tests group and green_impls group each occupy same layer."""
    svg = render_dag_svg(_CROSS_CUTTING_STAGES)
    root = _parse_svg(svg)
    layers = _get_node_layers(root)

    # red_tests group
    assert layers["red_test_frontend"] == layers["red_test_backend"], (
        "red_tests group stages should share x-layer"
    )
    # green_impls group
    assert layers["green_frontend"] == layers["green_backend"], (
        "green_impls group stages should share x-layer"
    )


def test_cross_cutting_has_two_gate_nodes() -> None:
    """cross-cutting-feature has 2 gate stages → 2 elements with dag-gate class."""
    svg = render_dag_svg(_CROSS_CUTTING_STAGES)
    root = _parse_svg(svg)
    gate_nodes = []
    for elem in root.iter():
        cls = elem.get("class", "")
        if "dag-node" in cls and "dag-gate" in cls:
            gate_nodes.append(elem)
    assert len(gate_nodes) == 2, f"Expected 2 gate nodes, got {len(gate_nodes)}"


def test_spec_refinement_node_count() -> None:
    """spec-refinement: 7 stages → 7 nodes."""
    svg = render_dag_svg(_SPEC_REFINEMENT_STAGES)
    root = _parse_svg(svg)
    assert _count_nodes(root) == 7


def test_spec_refinement_wide_parallel_group_same_layer() -> None:
    """spec-refinement: 5-node specialists group all share same x-layer."""
    svg = render_dag_svg(_SPEC_REFINEMENT_STAGES)
    root = _parse_svg(svg)
    layers = _get_node_layers(root)

    specialist_ids = ["arch_review", "devops_review", "qa_review", "frontend_review", "backend_review"]
    specialist_xs = {sid: layers.get(sid) for sid in specialist_ids}
    assert all(x is not None for x in specialist_xs.values()), (
        f"Some specialist nodes not found in SVG: {specialist_xs}"
    )
    xs = list(specialist_xs.values())
    assert len(set(xs)) == 1, (  # type: ignore[arg-type]
        f"Specialists group stages should share x-layer, got: {specialist_xs}"
    )


# ---------------------------------------------------------------------------
# Tests: performance
# ---------------------------------------------------------------------------


def test_render_complex_workflow_under_50ms() -> None:
    """render_dag_svg for the most complex fixture should complete in <50ms."""
    start = time.perf_counter()
    render_dag_svg(_CROSS_CUTTING_STAGES)
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert elapsed_ms < 50, f"Render took {elapsed_ms:.1f}ms (limit: 50ms)"


# ---------------------------------------------------------------------------
# Tests: HTML-escape at embedding points
# ---------------------------------------------------------------------------


def test_stage_id_xss_is_escaped() -> None:
    """Stage id containing '<' must be HTML-escaped in SVG output."""
    malicious_stages = [
        StageDTO(
            id="stage<script>",
            agent="agent&name",
            needs=[],
            parallel_group=None,
            gate=False,
            expected_output_path=None,
            must_include=None,
            on_failure="stop",
        )
    ]
    svg = render_dag_svg(malicious_stages)
    # The raw unescaped string must NOT appear literally
    assert "<script>" not in svg
    # Must still be parseable XML
    root = _parse_svg(svg)
    assert root is not None


# ---------------------------------------------------------------------------
# Tests: placeholder agent
# ---------------------------------------------------------------------------


def test_placeholder_agent_node_has_dag_placeholder_class() -> None:
    """A stage whose agent is a {{template_var}} gets class dag-placeholder."""
    placeholder_stages = [
        StageDTO(
            id="impl",
            agent="{{implementer_agent}}",
            needs=[],
            parallel_group=None,
            gate=False,
            expected_output_path=None,
            must_include=None,
            on_failure="stop",
        )
    ]
    svg = render_dag_svg(placeholder_stages)
    root = _parse_svg(svg)
    placeholder_nodes = []
    for elem in root.iter():
        cls = elem.get("class", "")
        if "dag-placeholder" in cls:
            placeholder_nodes.append(elem)
    assert len(placeholder_nodes) >= 1, "Placeholder agent stage missing dag-placeholder class"


# ---------------------------------------------------------------------------
# Tests: cycle / disconnected node fallback (line 136)
# ---------------------------------------------------------------------------


def test_cyclic_stages_render_without_exception() -> None:
    """Stages with a cycle are handled gracefully — no exception, valid SVG."""
    # A → B → A (cycle): Kahn's algorithm never drains the queue for these,
    # so the disconnected-node fallback (line 136) is triggered.
    cyclic_stages = [
        StageDTO(
            id="node_a",
            agent="product-engineer",
            needs=["node_b"],  # depends on node_b which depends back on node_a
            parallel_group=None,
            gate=False,
            expected_output_path=None,
            must_include=None,
            on_failure="stop",
        ),
        StageDTO(
            id="node_b",
            agent="software-engineer",
            needs=["node_a"],  # creates a cycle
            parallel_group=None,
            gate=False,
            expected_output_path=None,
            must_include=None,
            on_failure="stop",
        ),
    ]
    svg = render_dag_svg(cyclic_stages)
    assert isinstance(svg, str)
    root = _parse_svg(svg)
    # Both nodes must still appear in the output (assigned to layer 0 fallback)
    assert _count_nodes(root) == 2


def test_cyclic_stages_nodes_have_required_attributes() -> None:
    """Even cycle-affected nodes carry all required data attributes."""
    cyclic_stages = [
        StageDTO(
            id="cycle_x",
            agent="software-engineer",
            needs=["cycle_y"],
            parallel_group=None,
            gate=False,
            expected_output_path=None,
            must_include=None,
            on_failure="stop",
        ),
        StageDTO(
            id="cycle_y",
            agent="qa-engineer",
            needs=["cycle_x"],
            parallel_group=None,
            gate=False,
            expected_output_path=None,
            must_include=None,
            on_failure="stop",
        ),
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
    single = [
        StageDTO(
            id="solo",
            agent="product-engineer",
            needs=[],
            parallel_group=None,
            gate=False,
            expected_output_path=None,
            must_include=None,
            on_failure="stop",
        )
    ]
    svg = render_dag_svg(single)
    root = _parse_svg(svg)
    assert _count_nodes(root) == 1
    assert _count_edges(root) == 0


# ---------------------------------------------------------------------------
# Tests: agent name HTML escape
# ---------------------------------------------------------------------------


def test_agent_name_xss_is_escaped() -> None:
    """Agent name containing '<' is HTML-escaped in SVG output."""
    malicious_stages = [
        StageDTO(
            id="stage-id",
            agent="<evil>agent&name",
            needs=[],
            parallel_group=None,
            gate=False,
            expected_output_path=None,
            must_include=None,
            on_failure="stop",
        )
    ]
    svg = render_dag_svg(malicious_stages)
    assert "<evil>" not in svg
    root = _parse_svg(svg)
    assert root is not None


# ---------------------------------------------------------------------------
# Tests: single-node workflow (no cycle, no parallel group)
# ---------------------------------------------------------------------------


def test_single_gate_node_has_correct_classes() -> None:
    """A single gate stage produces one node with both dag-node and dag-gate classes."""
    gate_only = [
        StageDTO(
            id="approval",
            agent="qa-engineer",
            needs=[],
            parallel_group=None,
            gate=True,
            expected_output_path=None,
            must_include=None,
            on_failure="stop",
        )
    ]
    svg = render_dag_svg(gate_only)
    root = _parse_svg(svg)
    assert _count_nodes(root) == 1
    nodes_with_gate = [
        e for e in root.iter()
        if "dag-node" in e.get("class", "") and "dag-gate" in e.get("class", "")
    ]
    assert len(nodes_with_gate) == 1


# ---------------------------------------------------------------------------
# AGT-33 — audit-cycle fixture (gate + 4-way parallel group + synthesis)
# ---------------------------------------------------------------------------

_AUDIT_CYCLE_STAGES = [
    StageDTO(
        id="audit_intake",
        agent="project-auditor",
        needs=[],
        parallel_group=None,
        gate=True,
        expected_output_path=None,
        must_include=None,
        on_failure="stop",
    ),
    StageDTO(
        id="code_review",
        agent="code-reviewer",
        needs=["audit_intake"],
        parallel_group="audit",
        gate=False,
        expected_output_path=None,
        must_include=None,
        on_failure="stop",
    ),
    StageDTO(
        id="security_review",
        agent="security-reviewer",
        needs=["audit_intake"],
        parallel_group="audit",
        gate=False,
        expected_output_path=None,
        must_include=None,
        on_failure="stop",
    ),
    StageDTO(
        id="research_review",
        agent="researcher",
        needs=["audit_intake"],
        parallel_group="audit",
        gate=False,
        expected_output_path=None,
        must_include=None,
        on_failure="stop",
    ),
    StageDTO(
        id="qa_audit",
        agent="qa-engineer",
        needs=["audit_intake"],
        parallel_group="audit",
        gate=False,
        expected_output_path=None,
        must_include=None,
        on_failure="stop",
    ),
    StageDTO(
        id="synthesis",
        agent="project-auditor",
        needs=["code_review", "security_review", "research_review", "qa_audit"],
        parallel_group=None,
        gate=False,
        expected_output_path=None,
        must_include=None,
        on_failure="stop",
    ),
]

# ---------------------------------------------------------------------------
# AGT-33 — design-validation fixture (2 sequential stages)
# ---------------------------------------------------------------------------

_DESIGN_VALIDATION_STAGES = [
    StageDTO(
        id="capture_screens",
        agent="qa-engineer",
        needs=[],
        parallel_group=None,
        gate=False,
        expected_output_path=None,
        must_include=None,
        on_failure="stop",
    ),
    StageDTO(
        id="ux_review",
        agent="design-specialist",
        needs=["capture_screens"],
        parallel_group=None,
        gate=False,
        expected_output_path=None,
        must_include=None,
        on_failure="stop",
    ),
]


# ---------------------------------------------------------------------------
# Tests: audit-cycle DAG
# ---------------------------------------------------------------------------


def test_audit_cycle_svg_is_well_formed_xml() -> None:
    """audit-cycle SVG must parse as valid XML."""
    svg = render_dag_svg(_AUDIT_CYCLE_STAGES)
    root = _parse_svg(svg)
    assert root is not None


def test_audit_cycle_node_count() -> None:
    """audit-cycle has 6 stages → 6 nodes."""
    svg = render_dag_svg(_AUDIT_CYCLE_STAGES)
    root = _parse_svg(svg)
    assert _count_nodes(root) == 6


def test_audit_cycle_parallel_group_same_layer() -> None:
    """4-node audit parallel group must all share the same x-layer."""
    svg = render_dag_svg(_AUDIT_CYCLE_STAGES)
    root = _parse_svg(svg)
    layers = _get_node_layers(root)
    audit_ids = ["code_review", "security_review", "research_review", "qa_audit"]
    audit_xs = [layers.get(sid) for sid in audit_ids]
    assert all(x is not None for x in audit_xs), (
        f"Some audit parallel-group nodes not found: {dict(zip(audit_ids, audit_xs))}"
    )
    assert len(set(audit_xs)) == 1, (  # type: ignore[arg-type]
        f"audit parallel-group stages should share x-layer, got: {dict(zip(audit_ids, audit_xs))}"
    )


def test_audit_cycle_gate_node_has_dag_gate_class() -> None:
    """audit_intake (gate=True) must carry dag-gate class."""
    svg = render_dag_svg(_AUDIT_CYCLE_STAGES)
    root = _parse_svg(svg)
    intake_nodes = _find_nodes_with_attr(root, "data-stage-id", "audit_intake")
    assert len(intake_nodes) == 1
    assert "dag-gate" in intake_nodes[0].get("class", ""), (
        "audit_intake gate node missing dag-gate class"
    )


def test_audit_cycle_non_gate_nodes_no_dag_gate() -> None:
    """Non-gate nodes in audit-cycle must not carry dag-gate class."""
    svg = render_dag_svg(_AUDIT_CYCLE_STAGES)
    root = _parse_svg(svg)
    non_gate_ids = ["code_review", "security_review", "research_review", "qa_audit", "synthesis"]
    for sid in non_gate_ids:
        nodes = _find_nodes_with_attr(root, "data-stage-id", sid)
        if nodes:
            assert "dag-gate" not in nodes[0].get("class", ""), (
                f"Stage {sid!r} should not have dag-gate class"
            )


def test_audit_cycle_edge_count() -> None:
    """audit-cycle: intake→4 parallel (4 edges) + 4 parallel→synthesis (4 edges) = 8."""
    svg = render_dag_svg(_AUDIT_CYCLE_STAGES)
    root = _parse_svg(svg)
    assert _count_edges(root) == 8


# ---------------------------------------------------------------------------
# Tests: design-validation DAG
# ---------------------------------------------------------------------------


def test_design_validation_svg_is_well_formed_xml() -> None:
    """design-validation SVG must parse as valid XML."""
    svg = render_dag_svg(_DESIGN_VALIDATION_STAGES)
    root = _parse_svg(svg)
    assert root is not None


def test_design_validation_node_count() -> None:
    """design-validation has 2 stages → 2 nodes."""
    svg = render_dag_svg(_DESIGN_VALIDATION_STAGES)
    root = _parse_svg(svg)
    assert _count_nodes(root) == 2


def test_design_validation_edge_count() -> None:
    """design-validation: capture_screens → ux_review = 1 edge."""
    svg = render_dag_svg(_DESIGN_VALIDATION_STAGES)
    root = _parse_svg(svg)
    assert _count_edges(root) == 1


def test_design_validation_layers_are_distinct() -> None:
    """design-validation: sequential stages occupy distinct x-layers."""
    svg = render_dag_svg(_DESIGN_VALIDATION_STAGES)
    root = _parse_svg(svg)
    layers = _get_node_layers(root)
    assert len(set(layers.values())) == 2, (
        f"Expected 2 distinct layers for design-validation, got: {layers}"
    )


def test_design_validation_all_nodes_have_data_agent() -> None:
    """All design-validation nodes carry correct data-agent attributes."""
    svg = render_dag_svg(_DESIGN_VALIDATION_STAGES)
    root = _parse_svg(svg)
    capture_nodes = _find_nodes_with_attr(root, "data-stage-id", "capture_screens")
    ux_nodes = _find_nodes_with_attr(root, "data-stage-id", "ux_review")
    assert len(capture_nodes) == 1 and capture_nodes[0].get("data-agent") == "qa-engineer"
    assert len(ux_nodes) == 1 and ux_nodes[0].get("data-agent") == "design-specialist"
