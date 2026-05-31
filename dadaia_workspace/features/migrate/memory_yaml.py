"""HTML → YAML migration for dadaia-workspace memory atoms (T-MSS-07 / C-7).

Public API
----------
migrate_html_atom_to_yaml(html_path) -> tuple[dict, str, list[str]]
    Parse an existing HTML memory atom and return:
    - extracted data dict (schema-ready)
    - inferred atom type string
    - list of human-readable warning messages about placeholder usage

The extraction is best-effort using stdlib ``html.parser``.  For fields that
cannot be confidently extracted the returned dict contains a clearly-marked
placeholder string (``"TODO: migrate from HTML"``) so the resulting YAML
still passes ``validate_atom`` (all required fields are present).

Security: this module uses only stdlib; no external dependencies.  Input
HTML is operator-authored (trusted source); no sanitisation is required for
the parser to function correctly.  ``yaml.safe_load`` / ``yaml.safe_dump``
are enforced by callers (OWASP A03 / SPEC §8).

Atom types inferred from path (mirrors renderer._infer_atom_type):
- stem == "architecture"          → memory-architecture-v1
- stem in ("tech-stack", "tech_stack") → memory-tech-stack-v1
- parent.name == "product" and stem == "index" → memory-product-index-v1
- parent.name == "product" and stem != "index" → memory-product-feature-v1
"""

from __future__ import annotations

import html as html_module
import logging
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Placeholder sentinel
# ---------------------------------------------------------------------------

_TODO = "TODO: migrate from HTML"
_TODO_LIST: list[str] = [_TODO]

# ---------------------------------------------------------------------------
# Generic tree-building HTML parser
# ---------------------------------------------------------------------------


class _Node:
    """Minimal DOM-like node for HTML parsing."""

    __slots__ = ("tag", "attrs", "text_parts", "children", "parent")

    def __init__(self, tag: str, attrs: dict[str, str], parent: _Node | None = None) -> None:
        self.tag = tag
        self.attrs = attrs
        self.text_parts: list[str] = []
        self.children: list[_Node] = []
        self.parent = parent

    # ------------------------------------------------------------------
    # Text helpers
    # ------------------------------------------------------------------

    @property
    def text(self) -> str:
        """Flat text content (depth-first, strips extra whitespace)."""
        parts: list[str] = list(self.text_parts)
        for child in self.children:
            parts.append(child.text)
        return "".join(parts)

    @property
    def text_stripped(self) -> str:
        return " ".join(self.text.split())

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def find_all(self, tag: str) -> list[_Node]:
        """Return all descendant nodes with the given tag (BFS)."""
        results: list[_Node] = []
        stack = list(self.children)
        while stack:
            node = stack.pop(0)
            if node.tag == tag:
                results.append(node)
            stack = list(node.children) + stack
        return results

    def find(self, tag: str) -> _Node | None:
        """Return the first descendant node with the given tag."""
        results = self.find_all(tag)
        return results[0] if results else None

    def find_by_id(self, section_id: str) -> _Node | None:
        """Return the first section/div with id == section_id."""
        stack = list(self.children)
        while stack:
            node = stack.pop(0)
            if node.attrs.get("id") == section_id:
                return node
            stack = list(node.children) + stack
        return None

    def find_all_by_class(self, tag: str, css_class: str) -> list[_Node]:
        """Return all nodes with the given tag and a class containing css_class."""
        results: list[_Node] = []
        stack = list(self.children)
        while stack:
            node = stack.pop(0)
            if node.tag == tag:
                classes = node.attrs.get("class", "").split()
                if css_class in classes:
                    results.append(node)
            stack = list(node.children) + stack
        return results


# Self-closing / void elements in HTML5 that should never be pushed as parents.
_VOID_ELEMENTS = frozenset(
    {
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr",
    }
)


class _TreeParser(HTMLParser):
    """Build a minimal _Node tree from an HTML string."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = _Node("root", {})
        self._stack: list[_Node] = [self.root]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        parent = self._stack[-1]
        attr_dict = {k: (v or "") for k, v in attrs}
        node = _Node(tag, attr_dict, parent)
        parent.children.append(node)
        if tag not in _VOID_ELEMENTS:
            self._stack.append(node)

    def handle_endtag(self, tag: str) -> None:
        if tag in _VOID_ELEMENTS:
            return
        # Pop until we find the matching open tag (handles unclosed tags gracefully).
        for i in range(len(self._stack) - 1, 0, -1):
            if self._stack[i].tag == tag:
                self._stack = self._stack[: i]
                break

    def handle_data(self, data: str) -> None:
        if self._stack:
            self._stack[-1].text_parts.append(data)

    @classmethod
    def parse(cls, html_text: str) -> _Node:
        parser = cls()
        parser.feed(html_text)
        return parser.root


# ---------------------------------------------------------------------------
# Low-level extraction helpers
# ---------------------------------------------------------------------------


def _get_section_text(root: _Node, section_id: str) -> str | None:
    """Return clean text content of the section with the given id (excl. h2)."""
    section = root.find_by_id(section_id)
    if section is None:
        return None
    # Collect all text except the heading children (h2/h3)
    parts: list[str] = []
    for child in section.children:
        if child.tag in ("h2", "h3"):
            continue
        parts.append(child.text)
    return " ".join(" ".join(p.split()) for p in parts if p.strip()).strip() or None


def _get_section_li_texts(root: _Node, section_id: str) -> list[str]:
    """Return list of stripped text for each <li> inside the section."""
    section = root.find_by_id(section_id)
    if section is None:
        return []
    items = []
    for li in section.find_all("li"):
        t = li.text_stripped
        if t:
            items.append(t)
    return items


def _get_section_pre_mermaid(root: _Node, section_id: str) -> str | None:
    """Return the mermaid diagram source inside a section's <pre class="mermaid">."""
    section = root.find_by_id(section_id)
    if section is None:
        return None
    for pre in section.find_all("pre"):
        classes = pre.attrs.get("class", "").split()
        if "mermaid" in classes:
            return pre.text.strip() or None
    return None


def _get_all_pre_mermaid_in_section(root: _Node, section_id: str) -> list[str]:
    """Return all mermaid diagram sources in a section (multiple diagrams)."""
    section = root.find_by_id(section_id)
    if section is None:
        return []
    diagrams = []
    for pre in section.find_all("pre"):
        classes = pre.attrs.get("class", "").split()
        if "mermaid" in classes:
            t = pre.text.strip()
            if t:
                diagrams.append(t)
    return diagrams


def _get_table_rows(root: _Node, section_id: str) -> list[list[str]]:
    """Return list of rows as lists of cell text for the first table in section."""
    section = root.find_by_id(section_id)
    if section is None:
        return []
    table = section.find("table")
    if table is None:
        return []
    rows = []
    tbody = table.find("tbody")
    container = tbody if tbody else table
    for tr in container.find_all("tr"):
        cells = [td.text_stripped for td in tr.find_all("td")]
        if cells:
            rows.append(cells)
    return rows


def _unescape(text: str) -> str:
    """Unescape HTML entities in extracted text."""
    return html_module.unescape(text)


# ---------------------------------------------------------------------------
# Per-atom-type extractors
# ---------------------------------------------------------------------------


def _extract_feature(root: _Node, html_path: Path) -> tuple[dict[str, Any], list[str]]:
    """Extract memory-product-feature-v1 fields from a feature HTML atom."""
    warnings: list[str] = []
    data: dict[str, Any] = {}

    # feature_name from h1
    h1 = root.find("h1")
    if h1:
        data["feature_name"] = _unescape(h1.text_stripped)
    else:
        data["feature_name"] = html_path.stem
        warnings.append("feature_name: could not find <h1>; using filename stem")

    # feature_subtitle from <p class="meta">
    meta_paras = root.find_all_by_class("p", "meta")
    if meta_paras:
        data["feature_subtitle"] = _unescape(meta_paras[0].text_stripped)
    # feature_subtitle is optional; no warning needed

    # purpose — section id="purpose"
    section_purpose = root.find_by_id("purpose")
    if section_purpose:
        paras = []
        for child in section_purpose.children:
            if child.tag in ("h2", "h3"):
                continue
            text = _unescape(child.text_stripped)
            if text:
                paras.append(text)
        if paras:
            data["purpose"] = "\n\n".join(paras)
        else:
            data["purpose"] = _TODO
            warnings.append("purpose: section empty; placeholder used")
    else:
        data["purpose"] = _TODO
        warnings.append("purpose: section#purpose not found; placeholder used")

    # flow_steps — <ol class="flow"> inside section#flow
    section_flow = root.find_by_id("flow")
    flow_items: list[str] = []
    if section_flow:
        ols = section_flow.find_all_by_class("ol", "flow")
        if not ols:
            # fallback: any ol in the section
            ols = section_flow.find_all("ol")
        if ols:
            for li in ols[0].find_all("li"):
                t = _unescape(li.text_stripped)
                if t:
                    flow_items.append(t)
    if flow_items:
        data["flow_steps"] = flow_items
    else:
        data["flow_steps"] = [_TODO]
        warnings.append("flow_steps: could not extract <ol class='flow'> items; placeholder used")

    # diagram — optional; first <pre class="mermaid"> in section#flow
    if section_flow:
        for pre in section_flow.find_all("pre"):
            classes = pre.attrs.get("class", "").split()
            if "mermaid" in classes:
                diagram_text = pre.text.strip()
                if diagram_text:
                    data["diagram"] = diagram_text
                break

    # typical_trigger — section#trigger
    section_trigger = root.find_by_id("trigger")
    if section_trigger:
        paras = []
        for child in section_trigger.children:
            if child.tag in ("h2", "h3"):
                continue
            text = _unescape(child.text_stripped)
            if text:
                paras.append(text)
        if paras:
            data["typical_trigger"] = " ".join(paras)
        else:
            data["typical_trigger"] = _TODO
            warnings.append("typical_trigger: section empty; placeholder used")
    else:
        data["typical_trigger"] = _TODO
        warnings.append("typical_trigger: section#trigger not found; placeholder used")

    # differential — section#differential
    section_diff = root.find_by_id("differential")
    if section_diff:
        paras = []
        for child in section_diff.children:
            if child.tag in ("h2", "h3"):
                continue
            text = _unescape(child.text_stripped)
            if text:
                paras.append(text)
        if paras:
            data["differential"] = " ".join(paras)
        else:
            data["differential"] = _TODO
            warnings.append("differential: section empty; placeholder used")
    else:
        data["differential"] = _TODO
        warnings.append("differential: section#differential not found; placeholder used")

    # runtime_state — <ul> in section#runtime-state
    rs_items = _get_section_li_texts(root, "runtime-state")
    if rs_items:
        data["runtime_state"] = [_unescape(t) for t in rs_items]
    else:
        data["runtime_state"] = [_TODO]
        warnings.append("runtime_state: could not extract <li> items; placeholder used")

    # dependencies — <ul> in section#dependencies
    dep_items = _get_section_li_texts(root, "dependencies")
    if dep_items:
        data["dependencies"] = [_unescape(t) for t in dep_items]
    else:
        data["dependencies"] = [_TODO]
        warnings.append("dependencies: could not extract <li> items; placeholder used")

    return data, warnings


def _extract_architecture(root: _Node, _html_path: Path) -> tuple[dict[str, Any], list[str]]:
    """Extract memory-architecture-v1 fields from architecture.html."""
    warnings: list[str] = []
    data: dict[str, Any] = {}

    # overview — section#overview
    section_ov = root.find_by_id("overview")
    if section_ov:
        paras = []
        for child in section_ov.children:
            if child.tag in ("h2", "h3"):
                continue
            text = _unescape(child.text_stripped)
            if text:
                paras.append(text)
        if paras:
            data["overview"] = "\n\n".join(paras)
        else:
            data["overview"] = _TODO
            warnings.append("overview: section empty; placeholder used")
    else:
        data["overview"] = _TODO
        warnings.append("overview: section#overview not found; placeholder used")

    # layers — <div class="layer"> items in section#layers
    section_layers = root.find_by_id("layers")
    layers: list[dict[str, str]] = []
    if section_layers:
        layer_divs = section_layers.find_all_by_class("div", "layer")
        for div in layer_divs:
            text = _unescape(div.text_stripped)
            # Try to split "name — description" using the strong tag
            strong = div.find("strong")
            if strong:
                name = _unescape(strong.text_stripped)
                # Remove the name from the full text to get description
                rest = text[len(name) :].lstrip(" —").strip()
                desc = rest if rest else _TODO
            else:
                name = text[:50] if text else _TODO
                desc = _TODO
            layers.append({"name": name, "description": desc})
    if layers:
        data["layers"] = layers
    else:
        data["layers"] = [{"name": _TODO, "description": _TODO}]
        warnings.append("layers: could not extract layer divs; placeholder used")

    # dependency_rules_diagram — section#dependency-rules
    dep_diag = _get_section_pre_mermaid(root, "dependency-rules")
    if dep_diag:
        data["dependency_rules_diagram"] = dep_diag
    else:
        data["dependency_rules_diagram"] = _TODO
        warnings.append("dependency_rules_diagram: section#dependency-rules mermaid not found")

    # data_flow_diagram — sections#data-flow and #data-flow-gate (concatenated)
    # The architecture HTML has TWO data-flow diagrams; combine them.
    diagrams: list[str] = []
    for sid in ("data-flow", "data-flow-gate"):
        ds = _get_all_pre_mermaid_in_section(root, sid)
        diagrams.extend(ds)
    # Also check the generic "data_flow" id.
    if not diagrams:
        ds = _get_all_pre_mermaid_in_section(root, "data_flow")
        diagrams.extend(ds)
    if diagrams:
        data["data_flow_diagram"] = "\n\n".join(diagrams)
    else:
        data["data_flow_diagram"] = _TODO
        warnings.append("data_flow_diagram: no mermaid diagrams found in data-flow sections")

    # contracts — table in section#contracts (4 cols: De, Para, Tipo, Notas)
    rows = _get_table_rows(root, "contracts")
    contracts: list[dict[str, str]] = []
    for row in rows:
        if len(row) >= 4:
            contracts.append(
                {
                    "from": _unescape(row[0]),
                    "to": _unescape(row[1]),
                    "contract_type": _unescape(row[2]),
                    "notes": _unescape(row[3]),
                }
            )
        elif len(row) >= 2:
            contracts.append(
                {
                    "from": _unescape(row[0]),
                    "to": _unescape(row[1]),
                    "contract_type": _TODO,
                    "notes": _TODO,
                }
            )
    if contracts:
        data["contracts"] = contracts
    else:
        data["contracts"] = []
        # contracts is not required by schema (minItems not specified); empty is valid

    # runtime_state — <li> items in section#runtime-state
    rs_items = _get_section_li_texts(root, "runtime-state")
    if rs_items:
        data["runtime_state"] = [_unescape(t) for t in rs_items]
    else:
        data["runtime_state"] = [_TODO]
        warnings.append("runtime_state: could not extract items; placeholder used")

    return data, warnings


def _extract_tech_stack(root: _Node, _html_path: Path) -> tuple[dict[str, Any], list[str]]:
    """Extract memory-tech-stack-v1 fields from tech-stack.html."""
    warnings: list[str] = []
    data: dict[str, Any] = {}

    # languages — table in section#languages (3 cols: Linguagem, Versão, Uso)
    lang_rows = _get_table_rows(root, "languages")
    languages: list[dict[str, str]] = []
    for row in lang_rows:
        if len(row) >= 3:
            languages.append(
                {
                    "language": _unescape(row[0]),
                    "version": _unescape(row[1]),
                    "usage": _unescape(row[2]),
                }
            )
    if languages:
        data["languages"] = languages
    else:
        data["languages"] = [{"language": _TODO, "version": _TODO, "usage": _TODO}]
        warnings.append("languages: could not extract table rows; placeholder used")

    # runtimes — table in section#runtimes (3 cols: Ferramenta, Versão, Função)
    rt_rows = _get_table_rows(root, "runtimes")
    runtimes: list[dict[str, str]] = []
    for row in rt_rows:
        if len(row) >= 3:
            runtimes.append(
                {
                    "tool": _unescape(row[0]),
                    "version": _unescape(row[1]),
                    "role": _unescape(row[2]),
                }
            )
    if runtimes:
        data["runtimes"] = runtimes
    else:
        data["runtimes"] = [{"tool": _TODO, "version": _TODO, "role": _TODO}]
        warnings.append("runtimes: could not extract table rows; placeholder used")

    # dependencies — not a required field in tech-stack schema (it IS required though).
    # table in section#dependencies (4 cols: dep, version, layer, justification)
    # Note: tech-stack HTML may use section#dependencies or section id="approved-deps"
    dep_rows = _get_table_rows(root, "dependencies")
    if not dep_rows:
        dep_rows = _get_table_rows(root, "approved-deps")
    dependencies: list[dict[str, str]] = []
    for row in dep_rows:
        if len(row) >= 4:
            dependencies.append(
                {
                    "dependency": _unescape(row[0]),
                    "version": _unescape(row[1]),
                    "layer": _unescape(row[2]),
                    "justification": _unescape(row[3]),
                }
            )
    data["dependencies"] = dependencies  # can be empty list; schema does not require minItems

    # constraints — <li> items in section#constraints
    # May also be section#restrictions
    constraint_items = _get_section_li_texts(root, "constraints")
    if not constraint_items:
        constraint_items = _get_section_li_texts(root, "restrictions")
    if constraint_items:
        data["constraints"] = [_unescape(t) for t in constraint_items]
    else:
        data["constraints"] = [_TODO]
        warnings.append("constraints: could not extract <li> items; placeholder used")

    # canonical_commands — <pre><code> in section#commands (or section#canonical-commands)
    canonical: str | None = None
    for sid in ("commands", "canonical-commands"):
        section = root.find_by_id(sid)
        if section:
            pre = section.find("pre")
            if pre:
                # get text from <code> inside pre, or pre itself
                code = pre.find("code")
                raw = (code or pre).text
                canonical = _unescape(raw.strip())
                break
    if canonical:
        data["canonical_commands"] = canonical
    else:
        data["canonical_commands"] = _TODO
        warnings.append("canonical_commands: <pre><code> block not found; placeholder used")

    return data, warnings


def _extract_product_index(root: _Node, _html_path: Path) -> tuple[dict[str, Any], list[str]]:
    """Extract memory-product-index-v1 fields from product/index.html."""
    warnings: list[str] = []
    data: dict[str, Any] = {}

    # vision_oneliner + vision_paragraph — section#vision
    section_vision = root.find_by_id("vision")
    vision_paras: list[str] = []
    if section_vision:
        for child in section_vision.children:
            if child.tag in ("h2", "h3"):
                continue
            text = _unescape(child.text_stripped)
            if text:
                vision_paras.append(text)
    if vision_paras:
        data["vision_oneliner"] = vision_paras[0]
        data["vision_paragraph"] = " ".join(vision_paras[1:]) if len(vision_paras) > 1 else vision_paras[0]
    else:
        data["vision_oneliner"] = _TODO
        data["vision_paragraph"] = _TODO
        warnings.append("vision: section#vision not found or empty; placeholders used")

    # users — <li> items in section#users
    section_users = root.find_by_id("users")
    users: list[dict[str, str]] = []
    if section_users:
        for li in section_users.find_all("li"):
            # Try to split "name — description" using <strong> tag
            strong = li.find("strong")
            if strong:
                name = _unescape(strong.text_stripped)
                full = _unescape(li.text_stripped)
                rest = full[len(name) :].lstrip(" —").strip()
                desc = rest if rest else _TODO
            else:
                name = _unescape(li.text_stripped[:60])
                desc = _TODO
            if name:
                users.append({"name": name, "description": desc})
    if users:
        data["users"] = users
    else:
        data["users"] = [{"name": _TODO, "description": _TODO}]
        warnings.append("users: could not extract user <li> items; placeholder used")

    # catalog — <ol class="catalog"> in section#catalog
    section_catalog = root.find_by_id("catalog")
    catalog: list[dict[str, Any]] = []
    if section_catalog:
        # Find <ol class="catalog">
        catalog_ols = section_catalog.find_all_by_class("ol", "catalog")
        if not catalog_ols:
            catalog_ols = section_catalog.find_all("ol")
        if catalog_ols:
            for rank_idx, li in enumerate(catalog_ols[0].find_all("li"), start=1):
                anchor = li.find("a")
                if anchor:
                    href = anchor.attrs.get("href", "")
                    slug = re.sub(r"\.html$", "", href)
                    title = _unescape(anchor.text_stripped)
                    # Summary from <span class="desc">
                    desc_spans = li.find_all_by_class("span", "desc")
                    if desc_spans:
                        summary = _unescape(desc_spans[0].text_stripped).lstrip("—").strip()
                    else:
                        summary = _unescape(li.text_stripped)
                    catalog.append(
                        {
                            "slug": slug,
                            "title": title,
                            "summary": summary,
                            "rank": rank_idx,
                            "keywords": [slug],  # minimal; rank required by schema
                        }
                    )
    if catalog:
        data["catalog"] = catalog
    else:
        data["catalog"] = [
            {"slug": _TODO, "title": _TODO, "summary": _TODO, "rank": 1, "keywords": [_TODO]}
        ]
        warnings.append("catalog: could not extract catalog entries; placeholder used")

    # capability_map_diagram — section#capability-map
    cap_diag = _get_section_pre_mermaid(root, "capability-map")
    if not cap_diag:
        cap_diag = _get_section_pre_mermaid(root, "capability_map")
    if cap_diag:
        data["capability_map_diagram"] = cap_diag
    else:
        data["capability_map_diagram"] = _TODO
        warnings.append("capability_map_diagram: section mermaid not found; placeholder used")

    # non_goals — <li> items in section#limits or section#non-goals
    for sid in ("limits", "non-goals", "non_goals"):
        non_goal_items = _get_section_li_texts(root, sid)
        if non_goal_items:
            data["non_goals"] = [_unescape(t) for t in non_goal_items]
            break
    if "non_goals" not in data:
        data["non_goals"] = [_TODO]
        warnings.append("non_goals: section not found; placeholder used")

    return data, warnings


# ---------------------------------------------------------------------------
# Type inference from path
# ---------------------------------------------------------------------------


def _infer_atom_type_from_html(html_path: Path) -> str:
    """Infer atom type from the HTML file path (mirrors renderer._infer_atom_type)."""
    stem = html_path.stem
    if stem == "architecture":
        return "memory-architecture-v1"
    if stem in ("tech-stack", "tech_stack"):
        return "memory-tech-stack-v1"
    parent_name = html_path.parent.name
    if parent_name == "product" and stem == "index":
        return "memory-product-index-v1"
    if parent_name == "product" and stem != "index":
        return "memory-product-feature-v1"
    raise ValueError(
        f"Cannot infer atom type from HTML path: {html_path}. "
        "Expected one of: architecture.html, tech-stack.html, "
        "product/index.html, product/<slug>.html"
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def migrate_html_atom_to_yaml(
    html_path: Path,
) -> tuple[dict[str, Any], str, list[str]]:
    """Parse an HTML memory atom and extract its YAML-source fields.

    Args:
        html_path: Absolute path to the ``.html`` memory atom.

    Returns:
        A three-tuple of:
        - extracted data dict (ready for ``yaml.safe_dump`` and ``validate_atom``)
        - inferred atom type string (e.g. ``"memory-product-feature-v1"``)
        - list of human-readable warning strings about placeholder usage

    Raises:
        ValueError: if the atom type cannot be inferred from the path.
        OSError: if the HTML file cannot be read.
    """
    html_path = Path(html_path).resolve()
    atom_type = _infer_atom_type_from_html(html_path)

    html_text = html_path.read_text(encoding="utf-8")
    root = _TreeParser.parse(html_text)

    extractors = {
        "memory-product-feature-v1": _extract_feature,
        "memory-architecture-v1": _extract_architecture,
        "memory-tech-stack-v1": _extract_tech_stack,
        "memory-product-index-v1": _extract_product_index,
    }

    extractor = extractors[atom_type]
    data, warnings = extractor(root, html_path)
    return data, atom_type, warnings
