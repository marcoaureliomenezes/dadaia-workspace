#!/usr/bin/env python3
"""Generate catalog.json from memory atom .md frontmatter.

Usage:
    generate-memory-catalog.py --memory-dir <path> --out <catalog.json path>
                               [--index-out <index.md path>]
                               [--context <name>]

    --memory-dir   Path to the specs/memory directory (must contain product/<area>/*.md).
    --out          Output path for catalog.json.
    --index-out    Optional output path for an index.md TOC.
    --context      Workspace context name embedded in catalog.json (default: dadaia-workspace).

Exit codes:
    0  — success
    1  — at least one error (missing required frontmatter, unreadable file, etc.)

Catalog JSON shape (canonical shape owned by features/specs/catalog.py; kept
identical here by tests/contract/test_memory_catalog_render_contract.py):
    {
      "generated_at": "<YYYY-MM-DDTHH:MM:SSZ>",
      "context": "<workspace-context-name>",
      "features": [
        {
          "rank": <int>,
          "slug": "<slug>",
          "title": "<title>",
          "category": "<core|product|ops>",
          "area": "<parent dir under product/, or 'product'>",
          "tldr": "<one-sentence>",
          "summary": "<1-2 sentences>",
          "path": "specs/memory/product/<area>/<slug>.md",
          "tags": ["<tag>", ...],
          "token_estimate": <int>,
          "depends_on": ["<slug>", ...]
        },
        ...
      ]
    }

'rank' is the 1-based position in the alphabetical (sorted-path) file order — a
stable enumeration aid, NOT a priority signal.
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

# Public-source hygiene (T-011-15 / FR-W5-01): never write a __pycache__/*.pyc under
# dadaia_workspace/public/. This guard fires no matter how the script is invoked
# (direct `python <script>`, subprocess, or import), complementing the `-B` flag at
# the subprocess call site in features/specs/doctor.py.
sys.dont_write_bytecode = True

# ---------------------------------------------------------------------------
# Regexes
# ---------------------------------------------------------------------------

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")

# Required frontmatter fields for catalog generation.
# ``agent_tier`` was removed here in v0.1.53 (FR3): it has zero runtime consumers, so the
# catalog neither requires it as input (tolerate) nor emits it in output (drop). Kept in
# lockstep with the production twin ``features/specs/catalog.py`` (pinned by
# tests/contract/test_memory_catalog_render_contract.py).
# ``token_estimate`` was removed here at SPEC v0.4.2 FR2/GRILL D5: COMPUTED from the
# atom body (:func:`estimate_tokens`), never read from frontmatter — no longer required
# as input, and forward-compatible with the CLOSURE-phase memory half that strips the
# key from every atom entirely.
_REQUIRED_FIELDS: tuple[str, ...] = (
    "slug",
    "title",
    "category",
    "tldr",
    "summary",
    "tags",
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


def estimate_tokens(body: str) -> int:
    """Approximate an atom body's token count: ``word_count * 1.35`` (stdlib only).

    SPEC v0.4.2 FR2/GRILL D5: MUST stay byte-identical to
    ``features/specs/catalog.py:estimate_tokens`` — this standalone, importless
    script cannot import that module, so the formula is duplicated by necessity and
    kept aligned by ``tests/contract/test_memory_catalog_render_contract.py`` (A2.2).
    """
    return round(len(body.split()) * 1.35)


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
    """Build a single catalog feature entry from parsed frontmatter + body.

    Field order and value shapes are the CANONICAL shape owned by
    ``features/specs/catalog.py:generate_catalog`` — keep the two in lockstep
    (pinned by tests/contract/test_memory_catalog_render_contract.py).
    ``rank`` is the 1-based alphabetical (sorted-path) file order — a stable
    enumeration aid, NOT a priority signal.
    """
    slug: str = str(fm.get("slug", md_path.stem))
    depends_on = _extract_depends_on(body)

    # Compute path relative to repo root (specs/memory/product/<area>/<slug>.md).
    # Always POSIX "/" separators — the path is a stable identifier.
    try:
        rel_path = md_path.relative_to(memory_dir.parent.parent).as_posix()
    except ValueError:
        rel_path = md_path.as_posix()

    # F-75: `area` = the atom's parent directory name under product/;
    # atoms living directly in product/ belong to the "product" area.
    product_dir = memory_dir / "product"
    area = "product" if md_path.parent == product_dir else md_path.parent.name

    return {
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


# ---------------------------------------------------------------------------
# Catalog generator
# ---------------------------------------------------------------------------


def _generated_at() -> str:
    """UTC timestamp in the canonical ``YYYY-MM-DDTHH:MM:SSZ`` shape (F-84)."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


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
    # Recurse into thematic subdirs (v0.1.9 product/ tree).
    md_files = sorted(p for p in product_dir.glob("**/*.md") if p.name != "index.md")
    if not md_files:
        # Empty product dir is valid — return an empty catalog.
        catalog: dict[str, Any] = {
            "generated_at": _generated_at(),
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
        "generated_at": _generated_at(),
        "context": context,
        "features": features,
    }
    return catalog, []


# ---------------------------------------------------------------------------
# Index.md generator
# ---------------------------------------------------------------------------

#: The canonical, ANCHOR-STABLE catalog section heading — regeneration must never
#: rename it (bug closure-breaks-canonical-backlog-anchor; mirrors
#: features/specs/catalog.py:CATALOG_SECTION_HEADING).
CATALOG_SECTION_HEADING = "## Catálogo de features"

_INDEX_MD_TEMPLATE = """\
# Memory Catalog — {context}

> Generated automatically from `specs/memory/product/<area>/*.md` frontmatter.
> The catalog section below is refreshed by `generate-memory-catalog.py`; other
> sections of this file are preserved verbatim.

{heading}

{tables}
"""


def merge_catalog_section(existing: str | None, tables: str, context: str) -> str:
    """Anchor-stable merge (mirror of features/specs/catalog.py:merge_catalog_section)."""
    if existing and CATALOG_SECTION_HEADING in existing:
        lines = existing.splitlines(keepends=True)
        start = next(i for i, line in enumerate(lines) if line.strip() == CATALOG_SECTION_HEADING)
        end = len(lines)
        for j in range(start + 1, len(lines)):
            if lines[j].lstrip().startswith("## "):
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


def generate_index_md(catalog: dict[str, Any]) -> str:
    """Generate a Markdown TOC from a catalog dict.

    Sections group by ``area`` (the atom's parent directory under ``product/``,
    F-75), falling back to ``"product"`` for catalogs predating the field.
    Output must stay identical to ``features/specs/catalog.py:render_index_md``
    except the "re-run" tool name (contract-pinned).
    """
    by_area: dict[str, list[dict[str, Any]]] = {}
    for feature in catalog.get("features", []):
        area = str(feature.get("area", "product"))
        by_area.setdefault(area, []).append(feature)

    sections: list[str] = []
    for area in sorted(by_area.keys()):
        features = by_area[area]
        lines = [f"### {area}\n", _TABLE_HEADER]
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
    return _INDEX_MD_TEMPLATE.format(
        context=context, heading=CATALOG_SECTION_HEADING, tables=tables
    )


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

    # Write catalog.json (trailing newline — canonical write_catalog shape, F-84)
    out_path: Path = args.out.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"catalog.json written to {out_path} ({len(catalog['features'])} feature(s))")

    # Optionally write index.md
    if args.index_out is not None:
        index_out: Path = args.index_out.resolve()
        index_out.parent.mkdir(parents=True, exist_ok=True)
        try:
            existing = index_out.read_text(encoding="utf-8")
        except OSError:
            existing = None
        if existing and CATALOG_SECTION_HEADING in existing:
            by_area: dict[str, list[dict[str, str]]] = {}
            for feature in catalog.get("features", []):
                by_area.setdefault(str(feature.get("area", "product")), []).append(feature)
            sections = []
            for area in sorted(by_area):
                lines = [f"### {area}\n", _TABLE_HEADER]
                for feat in by_area[area]:
                    lines.append(
                        _TABLE_ROW.format(
                            slug=feat["slug"], title=feat["title"], tldr=feat.get("tldr", "")
                        )
                    )
                sections.append("\n".join(lines))
            tables = "\n\n".join(sections) if sections else "_No features found._"
            index_md = merge_catalog_section(
                existing, tables, catalog.get("context", "dadaia-workspace")
            )
        else:
            index_md = generate_index_md(catalog)
        if not index_md.endswith("\n"):
            index_md += "\n"
        index_out.write_text(index_md, encoding="utf-8")
        print(f"index.md written to {index_out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
