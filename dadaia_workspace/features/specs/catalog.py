"""Catalog generator for product memory feature index.

Reads frontmatter from ``specs/memory/product/<area>/*.md`` atom files (plus any
top-level ``product/*.md``) and returns a structured dict suitable for
serialisation as ``catalog.json``.

memory-markdown-source-v1: .md is the canonical source; the old HTML-scraping
path (``index.html`` / ``<ol class="catalog">``) is retired.

Public API
----------
generate_catalog(specs_dir: Path) -> dict
    Read ``specs_dir/memory/product/<area>/*.md`` frontmatter and return the
    catalog dict.
estimate_tokens(body: str) -> int
    Compute an atom's ``token_estimate`` from its body (SPEC v0.4.2 FR2) — the value
    is never read from frontmatter.

Schema of the returned dict
---------------------------
{
  "generated_at": "<ISO-8601 UTC>",
  "context": "<str>",
  "features": [
    {
      "rank": 1,
      "slug": "workspace-init",
      "title": "workspace-init",
      "category": "product",
      "area": "platform",
      "tldr": "...",
      "summary": "...",
      "path": "specs/memory/product/platform/workspace-init.md",
      "tags": [],
      "token_estimate": 413,
      "depends_on": []
    },
    ...
  ]
}

``rank`` is the 1-based position in the alphabetical (sorted-path) file order —
a stable enumeration aid, NOT a priority signal. ``area`` is the atom's parent
directory name under ``product/`` (top-level ``product/`` files get ``"product"``).

Pure module — only ``re``, ``json``, and the package's own :mod:`core.frontmatter`
(itself lazy about ``yaml``) from runtime deps.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from dadaia_workspace.core import frontmatter as _fm
from dadaia_workspace.features.specs import memory_canon
from dadaia_workspace.features.specs.canon import is_canon_path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Regexes
# ---------------------------------------------------------------------------

_WIKILINK_RE = memory_canon.WIKILINK_RE

# Required frontmatter fields for catalog generation.
# ``agent_tier`` was removed here in v0.1.53 (FR3): it has zero runtime consumers, so the
# catalog neither requires it as input (tolerate) nor emits it in output (drop). The
# duplicate ``public/scripts/generate-memory-catalog.py`` renderer this list used to move
# in lockstep with is DELETED (v0.5.1 T-051-16/A10.1/A10.4) — this module is now the only
# catalog generator.
# ``token_estimate`` was removed here at SPEC v0.4.2 FR2/GRILL D5: the catalog COMPUTES
# it from the atom body (:func:`estimate_tokens`) rather than reading a stored,
# hand-maintained frontmatter copy — a value that is stored AND derivable drifts (two
# instances measured 37% and 42% off across consecutive releases). It is no longer
# required as INPUT; forward-compatible with the CLOSURE-phase memory half, which strips
# the key from every atom's frontmatter entirely (A2.5 — this generator must keep
# working with the key present-but-ignored today and absent tomorrow).
_REQUIRED_FIELDS: tuple[str, ...] = (
    "slug",
    "title",
    "category",
    "tldr",
    "summary",
    "tags",
)


# ---------------------------------------------------------------------------
# Internal parsers
# ---------------------------------------------------------------------------


def _parse_md_file(
    md_path: Path,
) -> tuple[dict[str, Any] | None, str | None, str | None]:
    """Parse a .md file into (frontmatter_dict, body, error_message).

    Returns (None, None, error_msg) on failure.
    """
    try:
        content = md_path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, None, f"Cannot read '{md_path}': {exc}"

    parsed = _fm.parse(content)
    if isinstance(parsed, _fm.FrontmatterError):
        if parsed.kind == "missing_delimiter":
            return None, None, f"'{md_path}': no YAML frontmatter found."
        if parsed.kind == "invalid_yaml":
            return None, None, f"'{md_path}': YAML parse error: {parsed.message}"
        return None, None, f"'{md_path}': frontmatter is not a YAML mapping."

    return parsed.data, parsed.body, None


def _extract_depends_on(body: str) -> list[str]:
    """Extract unique, ordered [[slug]] wikilinks from the body."""
    seen: set[str] = set()
    result: list[str] = []
    for slug in _WIKILINK_RE.findall(body):
        if slug not in seen:
            seen.add(slug)
            result.append(slug)
    return result


def estimate_tokens(body: str) -> int:
    """Approximate an atom body's token count: ``word_count * 1.35`` (stdlib only, no
    tiktoken dependency).

    SPEC v0.4.2 FR2/GRILL D5: the ONE formula this release computes
    ``token_estimate`` from — moved here from the (now-deleted)
    ``public/scripts/lint-memory-atoms.py:_estimate_tokens`` drift-check duplicate, not
    copied. ``public/scripts/generate-memory-catalog.py`` (the importless projected
    twin, A2.2) carries an identical copy of this exact formula — the two are pinned to
    byte-identical catalog output by
    ``tests/contract/test_memory_catalog_render_contract.py``.
    """
    return round(len(body.split()) * 1.35)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_catalog(specs_dir: Path) -> dict[str, Any]:
    """Read ``specs_dir/memory/product/<area>/*.md`` frontmatter and return the catalog dict.

    Args:
        specs_dir: Path to the ``specs/`` directory (e.g.
            ``/path/to/repo/specs``).

    Returns:
        A dict matching the catalog JSON schema:
        ``{ "generated_at": ..., "context": ..., "features": [...] }``

    Raises:
        FileNotFoundError: if ``specs_dir/memory/product/`` directory is absent.
        ValueError: if any required frontmatter field is missing in any atom.
    """
    product_dir = Path(specs_dir) / "memory" / "product"
    if not product_dir.is_dir():
        raise FileNotFoundError(f"product/ directory not found at expected path: {product_dir}")

    # Discover feature atoms: *.md recursively excluding index.md at any depth
    md_files = sorted(p for p in product_dir.rglob("*.md") if p.name != "index.md")

    # Derive context name from the parent of specs_dir (the repo/project name)
    context_name = Path(specs_dir).parent.name

    features: list[dict[str, Any]] = []
    errors: list[str] = []

    for rank, md_path in enumerate(md_files, start=1):
        fm, body, parse_error = _parse_md_file(md_path)
        if parse_error:
            errors.append(parse_error)
            continue

        assert fm is not None
        assert body is not None

        # Validate required fields
        missing = _fm.missing_fields(fm, _REQUIRED_FIELDS)
        if missing:
            errors.append(f"'{md_path}': required frontmatter field(s) missing: {missing}")
            continue

        slug: str = str(fm.get("slug", md_path.stem))
        depends_on = _extract_depends_on(body)

        # Compute path relative to repo root (specs/memory/product/<slug>.md).
        # Always emit POSIX "/" separators: this path is a stable identifier the
        # panel and handoffs consume, so it must not vary by host OS (Windows
        # Path.__str__ would otherwise yield "\"-separated slugs). See FR-RC2-1.
        try:
            rel_path = md_path.relative_to(product_dir.parent.parent.parent).as_posix()
        except ValueError:
            rel_path = md_path.as_posix()

        # F-75: `area` = the atom's parent directory name under product/;
        # atoms living directly in product/ belong to the "product" area.
        area = "product" if md_path.parent == product_dir else md_path.parent.name

        # NOTE: `rank` is the 1-based alphabetical (sorted-path) file order — a
        # stable enumeration aid, NOT a priority signal (F-77).
        features.append(
            {
                "rank": rank,
                "slug": slug,
                "title": str(fm.get("title", slug)),
                "category": str(fm.get("category", "product")),
                "area": area,
                "tldr": str(fm.get("tldr", "")),
                "summary": str(fm.get("summary", "")),
                "path": rel_path,
                "tags": list(fm.get("tags") or []),
                "token_estimate": estimate_tokens(body),
                "depends_on": depends_on,
            }
        )

    if errors:
        raise ValueError(
            f"Catalog generation failed with {len(errors)} error(s):\n"
            + "\n".join(f"  - {e}" for e in errors)
        )

    generated_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    catalog: dict[str, Any] = {
        "generated_at": generated_at,
        "context": context_name,
        "features": features,
    }

    logger.debug(
        "Catalog generated: %d features for context=%r",
        len(features),
        context_name,
    )

    return catalog


# FR12 (T-045-26): the persisted catalog.json drops ``tldr`` outside
# ``_TLDR_INJECTED_CATEGORIES`` (category, not rank — F-77) to shrink ctx_inject's
# digest; index.md and the in-memory dict stay full (A12.3). Default pending PE
# ratification (DADAIA.md §2).
_TLDR_INJECTED_CATEGORIES: frozenset[str] = frozenset({"core"})


def curate_catalog_for_persistence(catalog: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of *catalog* with ``tldr`` dropped for non-tier-1 features.

    Shared by both catalog writers (this module's :func:`write_catalog` and the
    importless-fallback twin ``public/scripts/generate-memory-catalog.py``, which
    imports this function directly) so the persisted output never diverges (FR23
    Firing 3). Never mutates *catalog* or its feature dicts.
    """
    curated_features = [
        dict(feat)
        if str(feat.get("category", "")) in _TLDR_INJECTED_CATEGORIES
        else {k: v for k, v in feat.items() if k != "tldr"}
        for feat in catalog.get("features", [])
    ]
    return {**catalog, "features": curated_features}


def write_catalog(specs_dir: Path, catalog: dict[str, Any]) -> Path:
    """Serialise the FR12-curated ``catalog`` to ``specs_dir/memory/product/catalog.json``."""
    out_path = Path(specs_dir) / "memory" / "product" / "catalog.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    persisted = curate_catalog_for_persistence(catalog)
    json_text = json.dumps(persisted, ensure_ascii=False, indent=2) + "\n"
    out_path.write_text(json_text, encoding="utf-8")
    return out_path


# ---------------------------------------------------------------------------
# index.md TOC generation (F10 / T-PIO-10)
#
# The standalone ``public/scripts/generate-memory-catalog.py`` can emit an
# ``index.md`` TOC via ``--index-out``; the canonical CLI path
# (``dadaia memory catalog generate``) historically wrote only ``catalog.json``,
# letting ``index.md`` silently drift (bug memory-catalog-cli-skips-index-md).
# These functions give the CLI the same single-source-of-truth index rendering so
# both files stay in lockstep with the atom frontmatter.
# ---------------------------------------------------------------------------

#: The canonical, ANCHOR-STABLE catalog section heading. Backlog intents bind doc
#: anchors like ``memory/product/index.md#Catálogo de features`` (bug
#: closure-breaks-canonical-backlog-anchor) — regeneration must never rename it.
CATALOG_SECTION_HEADING = "## Catálogo de features"

_INDEX_MD_TEMPLATE = """\
# Memory Catalog — {context}

> Generated automatically from `specs/memory/product/<area>/*.md` frontmatter.
> The catalog section below is refreshed by `dadaia memory catalog generate`; other
> sections of this file are preserved verbatim.

{heading}

{tables}
"""


def merge_catalog_section(existing: str | None, tables: str, context: str) -> str:
    """Merge the regenerated catalog tables into *existing* index.md, anchor-stable.

    When *existing* carries the canonical ``## Catálogo de features`` heading, ONLY that
    section's body is replaced (up to the next ``## `` heading or EOF) — every other
    heading, and therefore every derivable doc anchor, survives regeneration verbatim
    (bug closure-breaks-canonical-backlog-anchor). A missing/absent file (or a legacy
    full-template file without the canonical heading) is written fresh with the
    canonical heading.
    """
    if existing and CATALOG_SECTION_HEADING in existing:
        lines = existing.splitlines(keepends=True)
        start = next(i for i, line in enumerate(lines) if line.strip() == CATALOG_SECTION_HEADING)
        end = len(lines)
        for j in range(start + 1, len(lines)):
            stripped = lines[j].lstrip()
            if stripped.startswith("## "):
                end = j
                break
        replacement = f"{CATALOG_SECTION_HEADING}\n\n{tables}\n\n"
        return "".join([*lines[:start], replacement, *lines[end:]])
    return _INDEX_MD_TEMPLATE.format(
        context=context, heading=CATALOG_SECTION_HEADING, tables=tables
    )


_TABLE_ROW = "| `{slug}` | {title} | {tldr} |"
# No trailing newline: sections are "\n".join-ed, so a trailing "\n" here would
# insert a blank line between the separator row and the first data row, breaking
# the GFM table block (bug memory-index-table-broken-gfm / F-73).
_TABLE_HEADER = "| slug | title | tldr |\n|------|-------|------|"


def render_index_md(catalog: dict[str, Any]) -> str:
    """Render a Markdown TOC from a catalog dict (sourced entirely from the catalog).

    Mirrors ``generate-memory-catalog.py:generate_index_md``: for the same catalog the
    two renderers produce identical output EXCEPT the "re-run" instruction line, which
    names the tool that produced the file (``dadaia memory catalog generate`` here vs
    ``generate-memory-catalog.py`` in the standalone script). Both write the same
    ``index.md`` from the same atom frontmatter, so whichever path runs keeps the file
    in lockstep with the catalog. The standalone script is a projected, importless
    consumer-workspace fallback that cannot import this module, so the small template is
    duplicated by necessity and kept aligned by the render contract
    (``tests/contract/test_memory_catalog_render_contract.py``); ``TestIndexMdParity``
    covers the catalog→index single-source rendering.

    Sections group by ``area`` (the atom's parent directory under ``product/``,
    F-75), falling back to ``"product"`` for catalogs predating the field.
    """
    by_area: dict[str, list[dict[str, Any]]] = {}
    for feature in catalog.get("features", []):
        area = str(feature.get("area", "product"))
        by_area.setdefault(area, []).append(feature)

    sections: list[str] = []
    for area in sorted(by_area.keys()):
        lines = [f"### {area}\n", _TABLE_HEADER]
        for feat in by_area[area]:
            lines.append(
                _TABLE_ROW.format(
                    slug=feat["slug"],
                    title=feat["title"],
                    tldr=feat.get("tldr", ""),
                )
            )
        sections.append("\n".join(lines))

    tables = "\n\n".join(sections) if sections else "_No features found._"
    context = str(catalog.get("context", "dadaia-workspace"))
    return _INDEX_MD_TEMPLATE.format(
        context=context, heading=CATALOG_SECTION_HEADING, tables=tables
    )


def write_index(specs_dir: Path, catalog: dict[str, Any]) -> Path:
    """Serialise the rendered TOC to ``specs_dir/memory/product/index.md``.

    Returns the path where the file was written. Guarantees a trailing newline.
    """
    out_path = Path(specs_dir) / "memory" / "product" / "index.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    existing: str | None
    try:
        existing = out_path.read_text(encoding="utf-8")
    except OSError:
        existing = None
    by_area: dict[str, list[dict[str, Any]]] = {}
    for feature in catalog.get("features", []):
        area = str(feature.get("area", "product"))
        by_area.setdefault(area, []).append(feature)
    sections: list[str] = []
    for area in sorted(by_area.keys()):
        lines = [f"### {area}\n", _TABLE_HEADER]
        for feat in by_area[area]:
            lines.append(
                _TABLE_ROW.format(slug=feat["slug"], title=feat["title"], tldr=feat.get("tldr", ""))
            )
        sections.append("\n".join(lines))
    tables = "\n\n".join(sections) if sections else "_No features found._"
    text = merge_catalog_section(existing, tables, str(catalog.get("context", "dadaia-workspace")))
    if not text.endswith("\n"):
        text += "\n"
    out_path.write_text(text, encoding="utf-8")
    return out_path


# ---------------------------------------------------------------------------
# memory_product_add — creates one feature Markdown atom (moved from the retired
# features.spec_artifacts package, v0.5.1 K4: spec_artifacts existed only to dodge a
# features -> features cross-feature edge; both this writer and the catalog it feeds
# already live in features/specs/, so the edge never existed here).
# ---------------------------------------------------------------------------

_PUBLIC_DIR = Path(__file__).parent.parent.parent / "public"
_MEMORY_FEATURE_TEMPLATE_PATH = _PUBLIC_DIR / "templates" / "memory-feature.md"

_PRODUCT_SLUG_RE = re.compile(r"^[a-z][a-z0-9-]+$")


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
    feature_template = (
        scaffold_dir / "feature.md" if scaffold_dir is not None else _MEMORY_FEATURE_TEMPLATE_PATH
    )
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
    area: str,
    templates_dir: Path | None = None,
    scaffold_dir: Path | None = None,
    project_name: str = "Projeto",
) -> MemoryProductAddResult:
    """Create a product feature Markdown atom under its canon area directory.

    1. Validates ``slug`` against ``^[a-z][a-z0-9-]+$``.
    2. Validates the resulting ``memory/product/<area>/<slug>.md`` path against
       :func:`~dadaia_workspace.features.specs.canon.is_canon_path` — the SAME
       decider ``doctor``/the pre-push gate use, never a second, hand-kept area
       regex (bug memory-product-add-writes-a-flat-atom-path-outside-the-canon
       -area-layout: this writer used to mint a flat ``memory/product/<slug>.md``,
       a shape the v6 canon's ``memory/product/<area>/<slug>.md`` pattern refuses).
    3. Creates ``specs/memory/product/<area>/<slug>.md`` from the born-markdown
       scaffold template (``public/templates/memory-feature.md``) if it does not
       yet exist.
    4. Returns the sorted list of all feature slugs across every area.

    This operation is idempotent: calling it twice with the same area/slug
    produces the same result.

    Args:
        specs_dir:     Absolute path to the ``specs/`` directory.
        slug:          Feature slug (e.g. ``payments``). Must match
                       ``^[a-z][a-z0-9-]+$``.
        area:          The canon area directory (e.g. ``platform``). Must match
                       the canon's area shape (lowercase letters/digits/hyphens/
                       underscores, starting with a letter) — the SAME shape
                       :func:`~dadaia_workspace.features.specs.catalog
                       .generate_catalog` reads back off an atom's parent
                       directory name (F-75).
        templates_dir: Unused; kept for API compatibility during migration.
        scaffold_dir:  Optional compatibility directory containing ``feature.md``.
        project_name:  Unused; kept for API compatibility during migration.

    Returns:
        :class:`MemoryProductAddResult`

    Raises:
        ValueError: If ``slug`` or the resulting area path is not canon-conformant.
        OSError:    If the product directory cannot be created or written.
    """
    if not _PRODUCT_SLUG_RE.match(slug):
        raise ValueError(
            f"Invalid slug {slug!r}. Must match ^[a-z][a-z0-9-]+$ "
            "(lowercase letters, digits, and hyphens; must start with a letter)."
        )

    rel_path = f"memory/product/{area}/{slug}.md"
    if not is_canon_path(rel_path):
        raise ValueError(
            f"Invalid area {area!r}: 'memory/product/{area}/{slug}.md' is not a "
            "v6-canon-conformant path. area must be lowercase letters/digits/"
            "hyphens/underscores, starting with a letter (features.specs.canon.CANON)."
        )

    product_dir = specs_dir / "memory" / "product"
    area_dir = product_dir / area
    area_dir.mkdir(parents=True, exist_ok=True)

    feature_path = area_dir / f"{slug}.md"
    created_feature = False

    if not feature_path.exists():
        today = datetime.now(tz=UTC).strftime("%Y-%m-%d")
        md_content = _build_feature_md(slug, today, scaffold_dir)
        feature_path.write_text(md_content, encoding="utf-8")
        created_feature = True

    # Collect all feature slugs from *.md files across every area (excluding index.md).
    feature_slugs = sorted(p.stem for p in product_dir.rglob("*.md") if p.name != "index.md")

    return MemoryProductAddResult(
        feature_html=feature_path,
        created_feature=created_feature,
        slug_entries=feature_slugs,
    )
