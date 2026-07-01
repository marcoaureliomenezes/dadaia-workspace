"""DAG layout + SVG renderer — features/workflows/dag.py.

Implements server-side SVG rendering for workflow DAGs using a
longest-path layering algorithm (Sugiyama-lite).

Public API:
    render_dag_svg(stages: list[StageDTO], node_meta=None) -> str
    NodeMeta(harness: str = "", model: str = "")  # optional per-node enrichment

Algorithm:
    1. Topological sort using Kahn's algorithm.
    2. Layer assignment: each stage gets layer = max(layer of predecessors) + 1.
       Stages with no predecessors get layer 0.
    3. Parallel-group override: all stages in the same parallel_group are forced
       to the same layer = max layer among all group members.
    4. Within each layer, stages are ordered by their original appearance order.
    5. Layers are placed as columns (left to right); stages within a layer as rows.

SVG output spec (SPEC §4, §7.5, §5.4):
    - role="img" on <svg>
    - <title> element inside <svg>
    - Per-node <g class="dag-node [dag-gate] [dag-placeholder]"
              data-stage-id="..." data-agent="..." data-status="pending"
              aria-label="...">
    - Rounded rectangle node (node_w x node_h)
    - Gate stages: class="dag-node dag-gate" + visual ⊙ marker
    - Placeholder agents ({{var}}): class="dag-node dag-placeholder"
    - Parallel-group dashed band behind grouped nodes
    - Edges: <path class="dag-edge"> with arrowhead <marker>
    - Embedded <style> with CSS classes (uses currentColor + explicit strokes
      so the DAG integrates with the panel's theme system via CSS class inheritance)
    - All text embedded in SVG is HTML-escaped to prevent injection

Security: every stage id and agent name is passed through html.escape() before
embedding in SVG attributes or text content. This satisfies OWASP A03 (injection).
"""

from __future__ import annotations

import html
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dadaia_workspace.features.workflows.service import StageDTO

# ---------------------------------------------------------------------------
# Layout constants
# ---------------------------------------------------------------------------

NODE_W: int = 140  # node width in px
NODE_H: int = 40  # node height in px (default, no per-node meta)
NODE_H_META: int = 58  # node height in px when node_meta adds a harness/model line
GAP_X: int = 80  # horizontal gap between columns
GAP_Y: int = 20  # vertical gap between nodes in same column
MARGIN_X: int = 20  # left margin
MARGIN_Y: int = 20  # top margin
BAND_PAD: int = 8  # padding around parallel-group band


# ---------------------------------------------------------------------------
# Optional per-node enrichment (AC-1 / T-45-01)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NodeMeta:
    """Optional per-stage enrichment drawn inside a DAG node.

    Carries the harness and model a workflow step runs on so the Workflows-card
    fluxogram can show ``harness · model`` beneath the role. Built catalog-side
    (``dadaia_catalog.py``) from ``DadaiaWorkflowStepDTO`` — the shared ``StageDTO``
    is never widened. Both fields are plain strings (empty = not shown).
    """

    harness: str = ""
    model: str = ""


# ---------------------------------------------------------------------------
# Internal layout types
# ---------------------------------------------------------------------------


class _NodeLayout:
    __slots__ = ("stage_id", "agent", "gate", "layer", "row", "x", "y", "is_placeholder")

    def __init__(
        self,
        stage_id: str,
        agent: str,
        gate: bool,
        layer: int,
        row: int,
        x: int,
        y: int,
        is_placeholder: bool,
    ) -> None:
        self.stage_id = stage_id
        self.agent = agent
        self.gate = gate
        self.layer = layer
        self.row = row
        self.x = x
        self.y = y
        self.is_placeholder = is_placeholder


# ---------------------------------------------------------------------------
# Layout algorithm
# ---------------------------------------------------------------------------


def _compute_layers(stages: list[StageDTO]) -> dict[str, int]:
    """Assign a layer (column index) to each stage.

    Uses longest-path layering:
    - Kahn's topological order.
    - layer[stage] = max(layer[pred] for pred in predecessors) + 1
    - Parallel-group override: all stages in a group get the same layer
      (max layer among group members after initial assignment).
    """
    if not stages:
        return {}

    id_to_stage = {s.id: s for s in stages}
    in_degree: dict[str, int] = {s.id: 0 for s in stages}
    successors: dict[str, list[str]] = defaultdict(list)

    for s in stages:
        for dep in s.needs:
            if dep in id_to_stage:
                in_degree[s.id] += 1
                successors[dep].append(s.id)

    layer: dict[str, int] = {}
    queue: deque[str] = deque()
    for s in stages:
        if in_degree[s.id] == 0:
            queue.append(s.id)
            layer[s.id] = 0

    while queue:
        node_id = queue.popleft()
        current_layer = layer[node_id]
        for successor in successors[node_id]:
            # Longest-path: use max predecessor layer + 1
            proposed = current_layer + 1
            if layer.get(successor, -1) < proposed:
                layer[successor] = proposed
            in_degree[successor] -= 1
            if in_degree[successor] == 0:
                queue.append(successor)

    # Fill in any nodes that were never reached (disconnected / cycle members)
    for s in stages:
        if s.id not in layer:
            layer[s.id] = 0

    # Parallel-group override: unify layer to max within each group
    groups: dict[str, list[str]] = defaultdict(list)
    for s in stages:
        if s.parallel_group:
            groups[s.parallel_group].append(s.id)

    for group_members in groups.values():
        max_layer = max(layer[sid] for sid in group_members)
        for sid in group_members:
            layer[sid] = max_layer

    return layer


def _compute_positions(
    stages: list[StageDTO],
    layer: dict[str, int],
    node_h: int = NODE_H,
) -> list[_NodeLayout]:
    """Compute pixel (x, y) for each node given its layer and row assignment.

    Stages within a layer are ordered by their original appearance order in the
    input list, preserving workflow intent. ``node_h`` is the effective node height
    (taller when per-node meta is drawn); it defaults to :data:`NODE_H` so the
    no-meta layout is unchanged.
    """
    # Group stages by layer, preserving original order within each layer
    layer_members: dict[int, list[StageDTO]] = defaultdict(list)
    for s in stages:
        layer_members[layer[s.id]].append(s)

    nodes: list[_NodeLayout] = []
    for col_idx, layer_stages in sorted(layer_members.items()):
        x = MARGIN_X + col_idx * (NODE_W + GAP_X)
        for row_idx, s in enumerate(layer_stages):
            y = MARGIN_Y + row_idx * (node_h + GAP_Y)
            is_placeholder = s.agent.startswith("{{") and s.agent.endswith("}}")
            nodes.append(
                _NodeLayout(
                    stage_id=s.id,
                    agent=s.agent,
                    gate=s.gate,
                    layer=col_idx,
                    row=row_idx,
                    x=x,
                    y=y,
                    is_placeholder=is_placeholder,
                )
            )

    return nodes


# ---------------------------------------------------------------------------
# SVG serialisation helpers
# ---------------------------------------------------------------------------


def _esc(value: str) -> str:
    """HTML-escape a string for safe embedding in SVG attributes or text."""
    return html.escape(value, quote=True)


def _svg_style(include_meta: bool = False) -> str:
    """Embedded CSS for DAG nodes, edges, and bands.

    Uses currentColor and explicit strokes; theme integration is via the panel
    CSS which sets color and stroke on the DAG container element. When
    ``include_meta`` is set (a ``node_meta`` map was supplied) an extra
    ``.node-meta`` rule is appended for the harness/model line; otherwise the
    style block is byte-for-byte the historical one so the no-meta output is
    unchanged.
    """
    meta_rule = (
        "\n  .dag-node text.node-meta { font-size: 8px; fill: #7a86a0; "
        "font-family: system-ui, sans-serif; }"
        if include_meta
        else ""
    )
    return f"""<style>
  .dag-node rect {{ fill: #f0f4f8; stroke: #6b7a99; stroke-width: 1.5; rx: 6; ry: 6; }}
  .dag-node text.stage-id {{ font-size: 11px; font-weight: 600; fill: #1a2133; font-family: system-ui, sans-serif; }}
  .dag-node text.agent-name {{ font-size: 9px; fill: #5a6480; font-family: system-ui, sans-serif; }}
  .dag-gate rect {{ fill: #fff8e1; stroke: #c49a00; stroke-width: 2; }}
  .dag-gate text.stage-id {{ fill: #6b4c00; }}
  .dag-gate text.agent-name {{ fill: #8a6a00; }}
  .dag-gate .gate-marker {{ font-size: 12px; fill: #c49a00; }}
  .dag-placeholder rect {{ fill: #f9f9f9; stroke: #aaa; stroke-width: 1.5; stroke-dasharray: 4 2; }}
  .dag-placeholder text.stage-id {{ font-style: italic; fill: #888; }}
  .dag-edge {{ fill: none; stroke: #8090b0; stroke-width: 1.5; }}
  .dag-band {{ fill: rgba(100, 140, 220, 0.06); stroke: #8aabdd; stroke-width: 1; stroke-dasharray: 5 3; rx: 6; ry: 6; }}{meta_rule}
</style>"""


def _arrowhead_marker() -> str:
    """SVG <defs> block containing the arrowhead marker for edges."""
    return (
        "<defs>"
        '<marker id="dag-arrow" markerWidth="8" markerHeight="8" '
        'refX="6" refY="3" orient="auto" markerUnits="strokeWidth">'
        '<path d="M0,0 L0,6 L8,3 z" fill="#8090b0"/>'
        "</marker>"
        "</defs>"
    )


def _truncate(value: str, limit: int) -> str:
    """Truncate a display string with an ellipsis for readability at card size."""
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 1)] + "…"


def _render_node(
    node: _NodeLayout,
    node_h: int = NODE_H,
    meta: NodeMeta | None = None,
) -> str:
    """Render a single DAG node as an SVG <g> element.

    ``node_h`` is the effective node height (defaults to :data:`NODE_H` for the
    historical layout). ``meta``, when present, adds a compact ``harness · model``
    line beneath the role and enriches the aria-label; when ``None`` the emitted
    ``<g>`` is byte-for-byte the historical node.
    """
    classes = "dag-node"
    if node.gate:
        classes += " dag-gate"
    if node.is_placeholder:
        classes += " dag-placeholder"

    stage_id_escaped = _esc(node.stage_id)
    agent_escaped = _esc(node.agent)
    aria_label_text = f"Stage: {node.stage_id}, Agent: {node.agent}"
    if node.gate:
        aria_label_text += ", Gate"

    # Gate marker (⊙) positioned top-right of node
    gate_marker = ""
    if node.gate:
        gate_marker = (
            f'<text class="gate-marker" x="{node.x + NODE_W - 6}" '
            f'y="{node.y + 12}" text-anchor="end">&#x2299;</text>'
        )

    meta_line = ""
    if meta is not None and (meta.harness or meta.model):
        meta_parts = [p for p in (meta.harness, meta.model) if p]
        meta_text = _truncate(" · ".join(meta_parts), 28)
        aria_label_text += f", {' · '.join(meta_parts)}"
        meta_line = (
            f'<text class="node-meta" x="{NODE_W // 2}" y="46" text-anchor="middle">'
            f"{_esc(meta_text)}</text>"
        )

    aria_label_escaped = _esc(aria_label_text)

    return (
        f'<g class="{classes}" '
        f'data-stage-id="{stage_id_escaped}" '
        f'data-agent="{agent_escaped}" '
        f'data-status="pending" '
        f'aria-label="{aria_label_escaped}" '
        f'transform="translate({node.x},{node.y})">'
        f'<rect width="{NODE_W}" height="{node_h}" rx="6" ry="6"/>'
        f'<text class="stage-id" x="{NODE_W // 2}" y="16" text-anchor="middle">'
        f"{stage_id_escaped}</text>"
        f'<text class="agent-name" x="{NODE_W // 2}" y="30" text-anchor="middle">'
        f"{agent_escaped}</text>"
        f"{meta_line}"
        f"{gate_marker}"
        f"</g>"
    )


def _render_edge(
    src: _NodeLayout,
    dst: _NodeLayout,
    node_h: int = NODE_H,
) -> str:
    """Render a directed edge as an SVG <path> with arrowhead."""
    # Start at right-center of source, end at left-center of destination
    x1 = src.x + NODE_W
    y1 = src.y + node_h // 2
    x2 = dst.x
    y2 = dst.y + node_h // 2

    # Horizontal mid-point for the bezier control points
    mid_x = (x1 + x2) // 2

    return (
        f'<path class="dag-edge" '
        f'd="M{x1},{y1} C{mid_x},{y1} {mid_x},{y2} {x2},{y2}" '
        f'marker-end="url(#dag-arrow)"/>'
    )


def _render_parallel_bands(
    stages: list[StageDTO],
    nodes_by_id: dict[str, _NodeLayout],
    node_h: int = NODE_H,
) -> list[str]:
    """Render dashed background bands for parallel groups."""
    groups: dict[str, list[str]] = defaultdict(list)
    for s in stages:
        if s.parallel_group:
            groups[s.parallel_group].append(s.id)

    bands: list[str] = []
    for group_nodes in groups.values():
        group_layouts = [nodes_by_id[nid] for nid in group_nodes if nid in nodes_by_id]
        if not group_layouts:
            continue

        xs = [n.x for n in group_layouts]
        ys = [n.y for n in group_layouts]
        min_x = min(xs) - BAND_PAD
        min_y = min(ys) - BAND_PAD
        max_x = max(xs) + NODE_W + BAND_PAD
        max_y = max(ys) + node_h + BAND_PAD

        bands.append(
            f'<rect class="dag-band" '
            f'x="{min_x}" y="{min_y}" '
            f'width="{max_x - min_x}" height="{max_y - min_y}" '
            f'rx="6" ry="6"/>'
        )

    return bands


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def render_dag_svg(
    stages: list[StageDTO],
    node_meta: dict[str, NodeMeta] | None = None,
) -> str:
    """Render a workflow DAG as an SVG string.

    Pure function: given the same inputs, returns the same SVG string every time.
    No I/O, no global state mutation.

    Args:
        stages: Ordered list of StageDTO objects from WorkflowDetailDTO.stages.
        node_meta: Optional map ``{stage_id: NodeMeta}`` carrying harness/model to
            draw inside each node (Workflows-card fluxogram). ``None`` (the default)
            yields the historical, byte-for-byte-identical output used by the
            first-class detail view — the enrichment is strictly additive and only
            the taller node layout / extra text/style are emitted when a non-empty
            map is supplied. The shared ``StageDTO`` is never widened.

    Returns:
        A complete SVG string with role="img", <title>, per-node data attributes,
        and embedded CSS. All user-supplied text is HTML-escaped.
    """
    if not stages:
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'width="200" height="60" role="img">'
            "<title>Workflow DAG (empty)</title>"
            '<text x="10" y="30" font-size="12" fill="#888">No stages</text>'
            "</svg>"
        )

    has_meta = bool(node_meta)
    node_h = NODE_H_META if has_meta else NODE_H

    # 1. Assign layers
    layer_map = _compute_layers(stages)

    # 2. Compute pixel positions
    nodes = _compute_positions(stages, layer_map, node_h)
    nodes_by_id: dict[str, _NodeLayout] = {n.stage_id: n for n in nodes}

    # 3. Compute canvas dimensions
    max_x = max(n.x + NODE_W for n in nodes) + MARGIN_X
    max_y = max(n.y + node_h for n in nodes) + MARGIN_Y

    # 4. Collect edges
    edge_pairs: list[tuple[str, str]] = []
    for s in stages:
        for dep_id in s.needs:
            if dep_id in nodes_by_id and s.id in nodes_by_id:
                edge_pairs.append((dep_id, s.id))

    # 5. Assemble SVG parts
    parts: list[str] = []

    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{max_x}" height="{max_y}" role="img" '
        f'viewBox="0 0 {max_x} {max_y}">'
    )
    parts.append(f"<title>Workflow DAG — {len(stages)} stage(s)</title>")
    parts.append(_svg_style(include_meta=has_meta))
    parts.append(_arrowhead_marker())

    # Parallel-group bands (rendered before nodes so nodes appear on top)
    bands = _render_parallel_bands(stages, nodes_by_id, node_h)
    parts.extend(bands)

    # Edges (rendered before nodes so nodes appear on top of edge endpoints)
    for src_id, dst_id in edge_pairs:
        parts.append(_render_edge(nodes_by_id[src_id], nodes_by_id[dst_id], node_h))

    # Nodes
    meta_map = node_meta or {}
    for node in nodes:
        parts.append(_render_node(node, node_h, meta_map.get(node.stage_id)))

    parts.append("</svg>")

    return "\n".join(parts)
