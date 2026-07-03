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

Pure module — only ``re``, ``json``, and ``yaml`` from runtime deps.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Regexes
# ---------------------------------------------------------------------------

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")

# Required frontmatter fields for catalog generation.
# ``agent_tier`` was removed here in v0.1.53 (FR3): it has zero runtime consumers, so the
# catalog neither requires it as input (tolerate) nor emits it in output (drop). The two
# renderers move in lockstep — the byte-identical twin is
# ``public/scripts/generate-memory-catalog.py`` (pinned by
# tests/contract/test_memory_catalog_render_contract.py).
_REQUIRED_FIELDS: tuple[str, ...] = (
    "slug",
    "title",
    "category",
    "tldr",
    "summary",
    "tags",
    "token_estimate",
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

    m = _FRONTMATTER_RE.match(content)
    if not m:
        return None, None, f"'{md_path}': no YAML frontmatter found."

    raw_yaml = m.group(1)
    body = content[m.end() :]

    try:
        fm: Any = yaml.safe_load(raw_yaml)
    except yaml.YAMLError as exc:
        return None, None, f"'{md_path}': YAML parse error: {exc}"

    if not isinstance(fm, dict):
        return None, None, f"'{md_path}': frontmatter is not a YAML mapping."

    return fm, body, None


def _extract_depends_on(body: str) -> list[str]:
    """Extract unique, ordered [[slug]] wikilinks from the body."""
    seen: set[str] = set()
    result: list[str] = []
    for slug in _WIKILINK_RE.findall(body):
        if slug not in seen:
            seen.add(slug)
            result.append(slug)
    return result


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
        missing = [f for f in _REQUIRED_FIELDS if f not in fm]
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
                "token_estimate": int(fm.get("token_estimate", 0)),
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


def write_catalog(specs_dir: Path, catalog: dict[str, Any]) -> Path:
    """Serialise ``catalog`` to ``specs_dir/memory/product/catalog.json``.

    Args:
        specs_dir: Path to the ``specs/`` directory.
        catalog: Dict returned by :func:`generate_catalog`.

    Returns:
        The path where the file was written.
    """
    out_path = Path(specs_dir) / "memory" / "product" / "catalog.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Pretty-print JSON with a trailing newline; no trailing commas (stdlib json never adds them)
    json_text = json.dumps(catalog, ensure_ascii=False, indent=2) + "\n"
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

_INDEX_MD_TEMPLATE = """\
# Memory Catalog — {context}

> Generated automatically from `specs/memory/product/<area>/*.md` frontmatter.
> Do not edit this file manually — re-run `dadaia memory catalog generate` to refresh.

## Features by area

{tables}
"""

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
    return _INDEX_MD_TEMPLATE.format(context=context, tables=tables)


def write_index(specs_dir: Path, catalog: dict[str, Any]) -> Path:
    """Serialise the rendered TOC to ``specs_dir/memory/product/index.md``.

    Returns the path where the file was written. Guarantees a trailing newline.
    """
    out_path = Path(specs_dir) / "memory" / "product" / "index.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    text = render_index_md(catalog)
    if not text.endswith("\n"):
        text += "\n"
    out_path.write_text(text, encoding="utf-8")
    return out_path
