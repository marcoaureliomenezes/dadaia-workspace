#!/usr/bin/env python3
"""Generate catalog.json from memory atom .md frontmatter.

Usage:
    generate-memory-catalog.py --memory-dir <path> --out <catalog.json path>
                               [--index-out <index.md path>]
                               [--context <name>]

    --memory-dir   Path to the specs/memory directory (must contain product/*.md).
    --out          Output path for catalog.json.
    --index-out    Optional output path for an index.md TOC.
    --context      Workspace context name embedded in catalog.json (default: dadaia-workspace).

Exit codes:
    0  — success
    1  — at least one error (missing required frontmatter, unreadable file, etc.)

Catalog JSON shape (compatible with the existing catalog.json):
    {
      "generated_at": "<ISO 8601 UTC>",
      "context": "<workspace-context-name>",
      "features": [
        {
          "rank": <int>,
          "slug": "<slug>",
          "title": "<title>",
          "category": "<core|product|ops>",
          "tldr": "<one-sentence>",
          "summary": "<1-2 sentences>",
          "tags": ["<tag>", ...],
          "token_estimate": <int>,
          "agent_tier": "<inject|self-pull>",
          "path": "specs/memory/product/<slug>.md",
          "depends_on": ["<slug>", ...]
        },
        ...
      ]
    }

Sourced ENTIRELY from frontmatter — no HTML scraping.
'depends_on' is derived from [[slug]] wikilinks in the body.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

# ---------------------------------------------------------------------------
# Regexes
# ---------------------------------------------------------------------------

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")

# Required frontmatter fields for catalog generation.
_REQUIRED_FIELDS: tuple[str, ...] = (
    "slug",
    "title",
    "category",
    "tldr",
    "summary",
    "tags",
    "agent_tier",
    "token_estimate",
)


# ---------------------------------------------------------------------------
# Parsers
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
        fm = yaml.safe_load(raw_yaml)
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


def _validate_required(fm: dict[str, Any], path: Path) -> list[str]:
    """Return list of error messages for missing required fields."""
    errors: list[str] = []
    for field in _REQUIRED_FIELDS:
        if field not in fm:
            errors.append(f"'{path}': required frontmatter field '{field}' is missing.")
    return errors


# ---------------------------------------------------------------------------
# Catalog entry builder
# ---------------------------------------------------------------------------


def _build_feature_entry(
    md_path: Path,
    fm: dict[str, Any],
    body: str,
    rank: int,
    memory_dir: Path,
) -> dict[str, Any]:
    """Build a single catalog feature entry from parsed frontmatter + body."""
    slug: str = str(fm.get("slug", md_path.stem))
    depends_on = _extract_depends_on(body)

    # Compute path relative to repo root (specs/memory/product/<slug>.md)
    try:
        rel_path = str(md_path.relative_to(memory_dir.parent.parent))
    except ValueError:
        rel_path = str(md_path)

    return {
        "rank": rank,
        "slug": slug,
        "title": str(fm.get("title", slug)),
        "category": str(fm.get("category", "product")),
        "tldr": str(fm.get("tldr", "")),
        "summary": str(fm.get("summary", "")),
        "tags": list(fm.get("tags") or []),
        "token_estimate": int(fm.get("token_estimate", 0)),
        "agent_tier": str(fm.get("agent_tier", "self-pull")),
        "path": rel_path,
        "depends_on": depends_on,
    }


# ---------------------------------------------------------------------------
# Catalog generator
# ---------------------------------------------------------------------------


def generate_catalog(
    memory_dir: Path,
    context: str = "dadaia-workspace",
) -> tuple[dict[str, Any] | None, list[str]]:
    """Generate catalog dict from product/*.md frontmatter.

    Returns (catalog_dict, errors).  catalog_dict is None if there are errors.
    """
    product_dir = memory_dir / "product"
    if not product_dir.is_dir():
        return None, [f"product/ subdirectory not found in '{memory_dir}'."]

    # index.md is the GENERATED TOC, not a feature atom — never index itself.
    md_files = sorted(p for p in product_dir.glob("*.md") if p.name != "index.md")
    if not md_files:
        # Empty product dir is valid — return an empty catalog.
        catalog: dict[str, Any] = {
            "generated_at": datetime.now(UTC).isoformat(),
            "context": context,
            "features": [],
        }
        return catalog, []

    errors: list[str] = []
    features: list[dict[str, Any]] = []
    rank = 1

    for md_path in md_files:
        fm, body, parse_error = _parse_md_file(md_path)
        if parse_error:
            errors.append(parse_error)
            continue

        # fm and body are non-None here
        assert fm is not None
        assert body is not None

        field_errors = _validate_required(fm, md_path)
        if field_errors:
            errors.extend(field_errors)
            continue

        entry = _build_feature_entry(md_path, fm, body, rank, memory_dir)
        features.append(entry)
        rank += 1

    if errors:
        return None, errors

    catalog = {
        "generated_at": datetime.now(UTC).isoformat(),
        "context": context,
        "features": features,
    }
    return catalog, []


# ---------------------------------------------------------------------------
# Index.md generator
# ---------------------------------------------------------------------------

_INDEX_MD_TEMPLATE = """\
# Memory Catalog — {context}

> Generated automatically from `specs/memory/product/*.md` frontmatter.
> Do not edit this file manually — re-run `generate-memory-catalog.py` to refresh.

## Features by category

{tables}
"""

_TABLE_ROW = "| `{slug}` | {title} | {tldr} |"
_TABLE_HEADER = "| slug | title | tldr |\n|------|-------|------|\n"


def generate_index_md(catalog: dict[str, Any]) -> str:
    """Generate a Markdown TOC from a catalog dict."""
    # Group features by category
    by_category: dict[str, list[dict[str, Any]]] = {}
    for feature in catalog.get("features", []):
        cat = feature.get("category", "product")
        by_category.setdefault(cat, []).append(feature)

    sections: list[str] = []
    for category in sorted(by_category.keys()):
        features = by_category[category]
        lines = [f"### {category}\n", _TABLE_HEADER]
        for feat in features:
            lines.append(
                _TABLE_ROW.format(
                    slug=feat["slug"],
                    title=feat["title"],
                    tldr=feat.get("tldr", ""),
                )
            )
        sections.append("\n".join(lines))

    tables = "\n\n".join(sections) if sections else "_No features found._"
    context = catalog.get("context", "dadaia-workspace")
    return _INDEX_MD_TEMPLATE.format(context=context, tables=tables)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.  Returns exit code."""
    parser = argparse.ArgumentParser(
        description="Generate catalog.json from memory atom .md frontmatter."
    )
    parser.add_argument(
        "--memory-dir",
        type=Path,
        required=True,
        help="Path to specs/memory directory.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Output path for catalog.json.",
    )
    parser.add_argument(
        "--index-out",
        type=Path,
        default=None,
        help="Optional output path for generated index.md.",
    )
    parser.add_argument(
        "--context",
        type=str,
        default="dadaia-workspace",
        help="Workspace context name embedded in catalog.json.",
    )
    args = parser.parse_args(argv)

    memory_dir = args.memory_dir.resolve()
    if not memory_dir.is_dir():
        print(f"ERROR: --memory-dir '{memory_dir}' is not a directory.", file=sys.stderr)
        return 1

    catalog, errors = generate_catalog(memory_dir, context=args.context)

    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        return 1

    assert catalog is not None

    # Write catalog.json
    out_path: Path = args.out.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(catalog, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"catalog.json written to {out_path} ({len(catalog['features'])} feature(s))")

    # Optionally write index.md
    if args.index_out is not None:
        index_md = generate_index_md(catalog)
        index_out: Path = args.index_out.resolve()
        index_out.parent.mkdir(parents=True, exist_ok=True)
        index_out.write_text(index_md, encoding="utf-8")
        print(f"index.md written to {index_out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
