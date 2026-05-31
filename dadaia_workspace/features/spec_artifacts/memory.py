"""Memory product catalog management for dadaia CLI.

Implements:
- memory_product_add: creates a feature HTML page and regenerates index.html
  (lexicographic, idempotent).

Templates used:
- memory-product-feature.html.j2  → specs/memory/product/<slug>.html
- memory-product-index.html.j2    → specs/memory/product/index.html (regenerated)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import jinja2

# ── canonical templates directory ────────────────────────────────────────────
_PUBLIC_DIR = Path(__file__).parent.parent.parent / "public"
_TEMPLATES_DIR = _PUBLIC_DIR / "templates"

_SLUG_RE = re.compile(r"^[a-z][a-z0-9-]+$")


def _jinja_env(templates_dir: Path) -> jinja2.Environment:
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(templates_dir)),
        undefined=jinja2.Undefined,
        autoescape=False,
    )


def _render(templates_dir: Path, template_name: str, ctx: dict[str, str]) -> str:
    env = _jinja_env(templates_dir)
    tmpl = env.get_template(template_name)
    rendered: str = tmpl.render(ctx)
    return rendered


@dataclass
class MemoryProductAddResult:
    """Outcome of a memory_product_add call.

    Attributes:
        feature_html: Path to the created (or existing) feature HTML file.
        index_html:   Path to the regenerated index.html.
        created_feature: True when the feature HTML was freshly written.
    """

    feature_html: Path
    index_html: Path
    created_feature: bool = False
    slug_entries: list[str] = field(default_factory=list)


def _build_catalog_items(feature_slugs: list[str]) -> str:
    """Return the HTML ``<ol class='catalog'>`` inner items for the given slugs."""
    lines: list[str] = []
    for slug in sorted(feature_slugs):
        lines.append(f'    <li><a href="{slug}.html">{slug}</a></li>')
    return "\n".join(lines)


def _regenerate_index(
    product_dir: Path,
    feature_slugs: list[str],
    templates_dir: Path,
    project_name: str = "Projeto",
) -> Path:
    """Re-render index.html deterministically (lexicographic order).

    Returns:
        Path to the written index.html.
    """
    today = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    catalog_items = _build_catalog_items(feature_slugs)
    ctx = {
        "project_name": project_name,
        "today": today,
        "last_release_id": "none",
        "catalog_items": catalog_items,
    }
    html = _render(templates_dir, "memory-product-index.html.j2", ctx)
    index_path = product_dir / "index.html"
    index_path.write_text(html, encoding="utf-8")
    return index_path


def memory_product_add(
    specs_dir: Path,
    slug: str,
    *,
    templates_dir: Path | None = None,
    project_name: str = "Projeto",
) -> MemoryProductAddResult:
    """Create a product feature HTML and regenerate index.html.

    1. Validates ``slug`` against ``^[a-z][a-z0-9-]+$``.
    2. Creates ``specs/memory/product/<slug>.html`` from the canonical template
       if it does not yet exist.
    3. Scans ``specs/memory/product/`` for all ``*.html`` files (excluding
       ``index.html``) and regenerates ``index.html`` deterministically in
       lexicographic order.

    This operation is idempotent: calling it twice with the same slug produces
    the same ``index.html`` content.

    Args:
        specs_dir:     Absolute path to the ``specs/`` directory.
        slug:          Feature slug (e.g. ``payments``). Must match
                       ``^[a-z][a-z0-9-]+$``.
        templates_dir: Directory containing Jinja2 ``.j2`` template files.
                       Defaults to the canonical ``public/templates/`` dir.
        project_name:  Project name used in rendered HTML.  Defaults to
                       ``"Projeto"``.

    Returns:
        :class:`MemoryProductAddResult`

    Raises:
        ValueError: If ``slug`` does not match the required pattern.
        OSError:    If the product directory cannot be created or written.
    """
    if not _SLUG_RE.match(slug):
        raise ValueError(
            f"Invalid slug {slug!r}. Must match ^[a-z][a-z0-9-]+$ "
            "(lowercase letters, digits, and hyphens; must start with a letter)."
        )

    tdl = templates_dir or _TEMPLATES_DIR
    product_dir = specs_dir / "memory" / "product"
    product_dir.mkdir(parents=True, exist_ok=True)

    feature_path = product_dir / f"{slug}.html"
    created_feature = False

    if not feature_path.exists():
        today = datetime.now(tz=UTC).strftime("%Y-%m-%d")
        ctx = {
            "feature_name": slug,
            "context_name": project_name,
            "feature_subtitle": f"{slug} — placeholder",
            "last_updated_iso": today,
            "last_release_id": "none",
            "purpose_paragraphs": "<p>Placeholder — document the feature purpose here.</p>",
            "flow_steps": "<li>Step 1 — placeholder.</li>",
            "flow_mermaid_optional": "",
            "typical_trigger": "Placeholder trigger.",
            "differential": "Placeholder differential.",
            "runtime_state_bullets": "<li>State placeholder.</li>",
            "dependencies_bullets": "<li>None yet.</li>",
        }
        html = _render(tdl, "memory-product-feature.html.j2", ctx)
        feature_path.write_text(html, encoding="utf-8")
        created_feature = True

    # Collect all feature slugs (any *.html except index.html)
    feature_slugs = sorted(p.stem for p in product_dir.glob("*.html") if p.name != "index.html")

    index_path = _regenerate_index(product_dir, feature_slugs, tdl, project_name)

    return MemoryProductAddResult(
        feature_html=feature_path,
        index_html=index_path,
        created_feature=created_feature,
        slug_entries=feature_slugs,
    )
