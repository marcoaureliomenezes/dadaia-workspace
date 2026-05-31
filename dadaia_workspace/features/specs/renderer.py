"""Deterministic YAML → HTML renderer for dadaia-workspace memory atoms.

Public API
----------
render_atom(yaml_path, atom_type=None) -> str
    Parse, validate, and render a YAML memory atom to an HTML string.

validate_atom(data, atom_type) -> None
    Validate a pre-loaded dict against the matching schema.  Raises
    jsonschema.ValidationError on failure.

The renderer is byte-deterministic: identical YAML input always produces
identical HTML output.  It never reads system time or injects dynamic values
unless they are present as optional fields in the YAML source itself.

Design decisions
----------------
* `yaml.safe_load` — never `yaml.load` (security: prevents arbitrary object
  deserialisation, OWASP A03).
* Template loading mirrors `scaffolder.py`: `jinja2.Environment` with
  `FileSystemLoader` from `public/templates/`.
* `jinja2.Undefined` (silent) for optional template variables so the template
  defaults fire cleanly when a field is absent.
* No `datetime.now()` / `datetime.today()` calls inside the renderer.
  `today` / `last_updated_iso` / `last_release_id` are only injected when
  the caller provides them via `extra_context`; otherwise the template's own
  `| default(...)` fallback fires.
* Catalog entries are sorted by `rank` ascending before rendering to guarantee
  stable, deterministic output (D-4 / MAPPING.md sort note).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import jinja2
import yaml
from jsonschema import Draft7Validator, validate

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_THIS_FILE = Path(__file__).resolve()
# dadaia_workspace/features/specs/renderer.py → dadaia_workspace/public/
_PUBLIC_DIR = _THIS_FILE.parent.parent.parent / "public"
_TEMPLATES_DIR = _PUBLIC_DIR / "templates"
_SCHEMAS_DIR = _PUBLIC_DIR / "schemas" / "memory"

# ---------------------------------------------------------------------------
# Schema → atom-type mapping
# ---------------------------------------------------------------------------

_SCHEMA_FILENAMES: dict[str, str] = {
    "memory-architecture-v1": "memory-architecture-v1.schema.json",
    "memory-tech-stack-v1": "memory-tech-stack-v1.schema.json",
    "memory-product-index-v1": "memory-product-index-v1.schema.json",
    "memory-product-feature-v1": "memory-product-feature-v1.schema.json",
}

_TEMPLATE_FILENAMES: dict[str, str] = {
    "memory-architecture-v1": "memory-architecture.html.j2",
    "memory-tech-stack-v1": "memory-tech-stack.html.j2",
    "memory-product-index-v1": "memory-product-index.html.j2",
    "memory-product-feature-v1": "memory-product-feature.html.j2",
}

# Heuristic: map common atom filenames / path segments → atom type.
# Checked in order; first match wins.
_PATH_TYPE_HINTS: list[tuple[str, str]] = [
    ("architecture", "memory-architecture-v1"),
    ("tech-stack", "memory-tech-stack-v1"),
    ("tech_stack", "memory-tech-stack-v1"),
    ("product/index", "memory-product-index-v1"),
    # product/<slug>.yaml — any yaml under a product/ directory that is NOT index
    # is a feature atom.  Handled separately in _infer_atom_type().
]

# ---------------------------------------------------------------------------
# Type inference
# ---------------------------------------------------------------------------


def _infer_atom_type(yaml_path: Path) -> str:
    """Infer the atom type from the file path.

    Resolution order:
    1. Known filename stems (architecture, tech-stack).
    2. product/index.yaml → product-index.
    3. Any other file under a `product/` directory → product-feature.
    4. Raises ValueError if none matches.
    """
    # Normalise to forward slashes for portable matching.
    path_str = yaml_path.as_posix()
    stem = yaml_path.stem

    if stem == "architecture":
        return "memory-architecture-v1"
    if stem in ("tech-stack", "tech_stack"):
        return "memory-tech-stack-v1"
    if stem == "index" and "product" in path_str:
        return "memory-product-index-v1"
    # Any yaml file whose parent directory is named "product" (or is under it)
    # and is not index.yaml → feature atom.
    if "product" in path_str and stem != "index":
        return "memory-product-feature-v1"

    raise ValueError(
        f"Cannot infer atom type from path: {yaml_path}. "
        "Pass atom_type explicitly (one of: "
        + ", ".join(_SCHEMA_FILENAMES.keys())
        + ")."
    )


# ---------------------------------------------------------------------------
# Schema loading (cached per process; schemas are static files)
# ---------------------------------------------------------------------------

_schema_cache: dict[str, dict[str, Any]] = {}


def _load_schema(atom_type: str) -> dict[str, Any]:
    """Load and cache the JSON Schema for *atom_type*."""
    if atom_type not in _schema_cache:
        filename = _SCHEMA_FILENAMES.get(atom_type)
        if filename is None:
            raise ValueError(
                f"Unknown atom_type: {atom_type!r}. "
                f"Valid types: {list(_SCHEMA_FILENAMES.keys())}"
            )
        schema_path = _SCHEMAS_DIR / filename
        try:
            _schema_cache[atom_type] = json.loads(schema_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Failed to load schema for {atom_type!r}: {exc}") from exc
    return _schema_cache[atom_type]


# ---------------------------------------------------------------------------
# Public: validate_atom
# ---------------------------------------------------------------------------


def validate_atom(data: dict[str, Any], atom_type: str) -> None:
    """Validate *data* against the JSON Schema for *atom_type*.

    Raises:
        jsonschema.ValidationError: if the data does not match the schema.
        ValueError: if *atom_type* is not recognised.
    """
    schema = _load_schema(atom_type)
    validate(instance=data, schema=schema, cls=Draft7Validator)


# ---------------------------------------------------------------------------
# HTML fragment builders (per MAPPING.md)
# ---------------------------------------------------------------------------


def _build_layers_html(layers: list[dict[str, str]]) -> str:
    """architecture: layers → layers_html.

    MAPPING.md design fork 2: description is passed through |safe to allow
    inline HTML tags.  We emit the raw description string; Jinja2 will mark it
    safe when the template uses {{ layers_html | safe }} or the renderer
    supplies it pre-built.
    """
    parts: list[str] = []
    for layer in layers:
        name = layer.get("name", "")
        desc = layer.get("description", "")
        parts.append(
            f'<div class="layer"><strong>{name}</strong> — {desc}</div>'
        )
    return "\n".join(parts)


def _build_contracts_rows(contracts: list[dict[str, str]]) -> str:
    """architecture: contracts → contracts_rows (4-col <tr> per entry)."""
    parts: list[str] = []
    for c in contracts:
        parts.append(
            "<tr>"
            f"<td>{c.get('from', '')}</td>"
            f"<td>{c.get('to', '')}</td>"
            f"<td>{c.get('contract_type', '')}</td>"
            f"<td>{c.get('notes', '')}</td>"
            "</tr>"
        )
    return "\n".join(parts)


def _build_li_bullets(items: list[str]) -> str:
    """Shared: list of strings → <li> items joined."""
    return "\n".join(f"<li>{item}</li>" for item in items)


def _build_screenshots_html(screenshots: list[dict[str, str]] | None) -> str:
    """Optional screenshots array → img+caption HTML."""
    if not screenshots:
        return ""
    parts: list[str] = []
    for s in screenshots:
        src = s.get("src", "")
        alt = s.get("alt", "")
        caption = s.get("caption", "")
        img = f'<img src="{src}" alt="{alt}">'
        if caption:
            parts.append(f"{img}\n<p>{caption}</p>")
        else:
            parts.append(img)
    return "\n".join(parts)


def _build_languages_rows(languages: list[dict[str, str]]) -> str:
    """tech-stack: languages → languages_rows (3-col <tr>)."""
    return "\n".join(
        f"<tr><td>{r['language']}</td><td>{r['version']}</td><td>{r['usage']}</td></tr>"
        for r in languages
    )


def _build_runtimes_rows(runtimes: list[dict[str, str]]) -> str:
    """tech-stack: runtimes → runtimes_rows (3-col <tr>)."""
    return "\n".join(
        f"<tr><td>{r['tool']}</td><td>{r['version']}</td><td>{r['role']}</td></tr>"
        for r in runtimes
    )


def _build_dependencies_rows(dependencies: list[dict[str, str]]) -> str:
    """tech-stack: dependencies → dependencies_rows (4-col <tr>)."""
    return "\n".join(
        "<tr>"
        f"<td>{d['dependency']}</td>"
        f"<td>{d['version']}</td>"
        f"<td>{d['layer']}</td>"
        f"<td>{d['justification']}</td>"
        "</tr>"
        for d in dependencies
    )


def _build_users_bullets(users: list[dict[str, str]]) -> str:
    """product-index: users → users_bullets (<li> with bold name)."""
    return "\n".join(
        f"<li><strong>{u['name']}</strong> — {u['description']}</li>"
        for u in users
    )


def _build_catalog_items(catalog: list[dict[str, Any]]) -> str:
    """product-index: catalog sorted by rank → catalog_items HTML.

    MAPPING.md: rank and keywords are NOT rendered into visible HTML — they
    are machine-readable metadata for Phase-1 catalog.json.  Only slug,
    title, and summary appear in the rendered list item.

    MAPPING.md sort note: MUST sort by rank ascending for determinism (D-4).
    """
    sorted_catalog = sorted(catalog, key=lambda e: e.get("rank", 0))
    parts: list[str] = []
    for entry in sorted_catalog:
        slug = entry.get("slug", "")
        title = entry.get("title", slug)
        summary = entry.get("summary", "")
        parts.append(
            f'<li><a href="{slug}.html">{title}</a>'
            f'<span class="desc">— {summary}</span></li>'
        )
    return "\n".join(parts)


def _build_purpose_paragraphs(purpose: str) -> str:
    """product-feature: purpose → purpose_paragraphs.

    Split on double newlines; wrap each paragraph in <p>.
    """
    paragraphs = [p.strip() for p in purpose.strip().split("\n\n") if p.strip()]
    return "\n".join(f"<p>{p}</p>" for p in paragraphs)


def _build_flow_mermaid_optional(diagram: str | None) -> str:
    """product-feature: optional diagram → <pre class="mermaid"> or empty."""
    if not diagram:
        return ""
    return f'<pre class="mermaid">\n{diagram.strip()}\n</pre>'


# ---------------------------------------------------------------------------
# Template-variable builders per atom type
# ---------------------------------------------------------------------------


def _build_architecture_context(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "architecture_overview": data.get("overview", ""),
        "layers_html": _build_layers_html(data.get("layers", [])),
        "dependency_rules_mermaid": data.get("dependency_rules_diagram", ""),
        "data_flow_mermaid": data.get("data_flow_diagram", ""),
        "contracts_rows": _build_contracts_rows(data.get("contracts", [])),
        "runtime_state_bullets": _build_li_bullets(data.get("runtime_state", [])),
        "screenshots_html": _build_screenshots_html(data.get("screenshots")),
    }


def _build_tech_stack_context(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "languages_rows": _build_languages_rows(data.get("languages", [])),
        "runtimes_rows": _build_runtimes_rows(data.get("runtimes", [])),
        "dependencies_rows": _build_dependencies_rows(data.get("dependencies", [])),
        "constraints_bullets": _build_li_bullets(data.get("constraints", [])),
        "canonical_commands": data.get("canonical_commands", ""),
    }


def _build_product_index_context(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "product_vision_oneliner": data.get("vision_oneliner", ""),
        "product_vision_paragraph": data.get("vision_paragraph", ""),
        "users_bullets": _build_users_bullets(data.get("users", [])),
        "catalog_items": _build_catalog_items(data.get("catalog", [])),
        "capability_map_mermaid": data.get("capability_map_diagram", ""),
        "explicit_non_goals": _build_li_bullets(data.get("non_goals", [])),
        "screenshots_html": _build_screenshots_html(data.get("screenshots")),
    }


def _build_product_feature_context(
    data: dict[str, Any], yaml_path: Path
) -> dict[str, Any]:
    feature_name = data.get("feature_name") or yaml_path.stem
    feature_subtitle = data.get("feature_subtitle") or feature_name
    return {
        "feature_name": feature_name,
        "feature_subtitle": feature_subtitle,
        "purpose_paragraphs": _build_purpose_paragraphs(data.get("purpose", "")),
        "flow_steps": _build_li_bullets(data.get("flow_steps", [])),
        "flow_mermaid_optional": _build_flow_mermaid_optional(data.get("diagram")),
        "typical_trigger": data.get("typical_trigger", ""),
        "differential": data.get("differential", ""),
        "runtime_state_bullets": _build_li_bullets(data.get("runtime_state", [])),
        "dependencies_bullets": _build_li_bullets(data.get("dependencies", [])),
    }


_CONTEXT_BUILDERS = {
    "memory-architecture-v1": lambda data, path: _build_architecture_context(data),
    "memory-tech-stack-v1": lambda data, path: _build_tech_stack_context(data),
    "memory-product-index-v1": lambda data, path: _build_product_index_context(data),
    "memory-product-feature-v1": _build_product_feature_context,
}

# ---------------------------------------------------------------------------
# Jinja2 environment
# ---------------------------------------------------------------------------


def _make_jinja_env(templates_dir: Path) -> jinja2.Environment:
    """Create a Jinja2 Environment that allows pre-built HTML fragments.

    `autoescape=False` because template variables contain pre-built HTML
    fragments (e.g. `layers_html`, `contracts_rows`).  Individual string
    fields (like `architecture_overview`) are plain text and do NOT require
    escaping for the panel's purposes; the atoms are operator-authored in a
    trusted environment.
    """
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(templates_dir)),
        undefined=jinja2.Undefined,
        autoescape=False,
        keep_trailing_newline=True,
    )


# ---------------------------------------------------------------------------
# Public: render_atom
# ---------------------------------------------------------------------------


def render_atom(
    yaml_path: Path,
    atom_type: str | None = None,
    extra_context: dict[str, Any] | None = None,
    templates_dir: Path | None = None,
) -> str:
    """Parse, validate, and render a YAML memory atom to an HTML string.

    Args:
        yaml_path: Absolute path to the `.yaml` atom file.
        atom_type: One of the four atom type identifiers
            (``"memory-architecture-v1"``, ``"memory-tech-stack-v1"``,
            ``"memory-product-index-v1"``, ``"memory-product-feature-v1"``).
            If ``None``, the type is inferred from the file path.
        extra_context: Optional dict of additional Jinja2 variables to inject
            (e.g. ``{"project_name": "my-proj", "last_release_id": "v1"}``).
            These are NOT injected automatically — pass them explicitly to keep
            the renderer deterministic.  The template's own ``| default(...)``
            fallbacks fire for any variable not supplied here.
        templates_dir: Override the templates directory (default:
            ``dadaia_workspace/public/templates/``).  Useful in tests.

    Returns:
        Rendered HTML string (byte-identical for identical inputs).

    Raises:
        ValueError: if atom_type is unknown or cannot be inferred.
        jsonschema.ValidationError: if the YAML data fails schema validation.
        OSError: if the YAML file cannot be read.
        RuntimeError: if template loading fails.
    """
    yaml_path = Path(yaml_path).resolve()

    # 1. Load YAML — safe_load only (OWASP A03 / SPEC §8).
    raw = yaml_path.read_text(encoding="utf-8")
    data: dict[str, Any] = yaml.safe_load(raw)
    if not isinstance(data, dict):
        raise ValueError(
            f"YAML atom at {yaml_path} did not parse to a dict "
            f"(got {type(data).__name__}). Atoms must be YAML mappings."
        )

    # 2. Infer atom type if not supplied.
    resolved_type = atom_type if atom_type is not None else _infer_atom_type(yaml_path)

    # 3. Validate against the JSON Schema — raises ValidationError on failure.
    validate_atom(data, resolved_type)

    # 4. Build the template context from the structured YAML data.
    builder = _CONTEXT_BUILDERS.get(resolved_type)
    if builder is None:
        raise ValueError(f"No context builder registered for atom_type {resolved_type!r}")
    context: dict[str, Any] = builder(data, yaml_path)

    # 5. Merge optional extra context (caller-supplied render-time variables).
    # Extra context values win over built context for the same key.
    if extra_context:
        context = {**context, **extra_context}

    # 6. Render via Jinja2 from the canonical template.
    tdir = templates_dir if templates_dir is not None else _TEMPLATES_DIR
    env = _make_jinja_env(tdir)
    template_name = _TEMPLATE_FILENAMES[resolved_type]
    try:
        template = env.get_template(template_name)
    except jinja2.TemplateNotFound as exc:
        raise RuntimeError(
            f"Template not found: {template_name} in {tdir}. "
            "Ensure dadaia_workspace/public/templates/ is intact."
        ) from exc

    rendered: str = template.render(context)
    return rendered
