"""Memory product catalog management for dadaia CLI.

Implements:
- memory_product_add: creates a feature Markdown atom (born-markdown).

Template used:
- public/templates/memory-feature.md → specs/memory/product/<slug>.md

The legacy HTML index (memory-product-index.html.j2 → index.html) was retired
in memory-markdown-source-v1 (T-MMS-10/11). The catalog is now generated from
.md frontmatter via ``dadaia memory catalog generate``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

# ── canonical directories ─────────────────────────────────────────────────────
_PUBLIC_DIR = Path(__file__).parent.parent.parent / "public"
_TEMPLATE_PATH = _PUBLIC_DIR / "templates" / "memory-feature.md"

_SLUG_RE = re.compile(r"^[a-z][a-z0-9-]+$")


@dataclass
class MemoryProductAddResult:
    """Outcome of a memory_product_add call.

    Attributes:
        feature_html: Path to the created (or existing) feature Markdown file.
                      Named ``feature_html`` for backwards-compatibility with
                      callers; the actual file written is ``<slug>.md``.
        created_feature: True when the feature Markdown file was freshly written.
        slug_entries: Sorted list of all feature slugs discovered in product dir.
    """

    feature_html: Path
    created_feature: bool = False
    slug_entries: list[str] = field(default_factory=list)


def _build_feature_md(slug: str, today: str, scaffold_dir: Path | None = None) -> str:
    """Build the Markdown content for a new product feature atom.

    Reads an injected legacy ``feature.md`` when ``scaffold_dir`` is supplied; otherwise
    reads the canonical template outside the live scaffold atom tree.

    Args:
        slug:         Feature slug (already validated by the caller).
        today:        ISO-8601 date string (``YYYY-MM-DD``).
        scaffold_dir: Optional compatibility directory containing ``feature.md``.

    Returns:
        Rendered Markdown string ready to be written to ``<slug>.md``.
    """
    feature_template = scaffold_dir / "feature.md" if scaffold_dir is not None else _TEMPLATE_PATH
    template_content = feature_template.read_text(encoding="utf-8")
    # Substitute canonical placeholders in the frontmatter stubs.
    content = template_content.replace("SLUG_PLACEHOLDER", slug)
    content = content.replace("TITLE_PLACEHOLDER", slug.replace("-", " ").title())
    content = content.replace("RELEASE_PLACEHOLDER", "none")
    content = content.replace('"2026-01-01"', f'"{today}"')
    return content


def memory_product_add(
    specs_dir: Path,
    slug: str,
    *,
    templates_dir: Path | None = None,
    scaffold_dir: Path | None = None,
    project_name: str = "Projeto",
) -> MemoryProductAddResult:
    """Create a product feature Markdown atom.

    1. Validates ``slug`` against ``^[a-z][a-z0-9-]+$``.
    2. Creates ``specs/memory/product/<slug>.md`` from the born-markdown scaffold
       template (``public/templates/memory-feature.md``) if it does not
       yet exist.
    3. Returns the sorted list of all feature slugs in the product directory.

    This operation is idempotent: calling it twice with the same slug produces
    the same result.

    Args:
        specs_dir:     Absolute path to the ``specs/`` directory.
        slug:          Feature slug (e.g. ``payments``). Must match
                       ``^[a-z][a-z0-9-]+$``.
        templates_dir: Unused; kept for API compatibility during migration.
        scaffold_dir:  Optional compatibility directory containing ``feature.md``.
        project_name:  Unused; kept for API compatibility during migration.

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

    product_dir = specs_dir / "memory" / "product"
    product_dir.mkdir(parents=True, exist_ok=True)

    feature_path = product_dir / f"{slug}.md"
    created_feature = False

    if not feature_path.exists():
        today = datetime.now(tz=UTC).strftime("%Y-%m-%d")
        md_content = _build_feature_md(slug, today, scaffold_dir)
        feature_path.write_text(md_content, encoding="utf-8")
        created_feature = True

    # Collect all feature slugs from *.md files (excluding index.md).
    feature_slugs = sorted(p.stem for p in product_dir.glob("*.md") if p.name != "index.md")

    return MemoryProductAddResult(
        feature_html=feature_path,
        created_feature=created_feature,
        slug_entries=feature_slugs,
    )
