#!/usr/bin/env python3
"""The catalog renderer: `memory/product/<area>/*.md` frontmatter -> `catalog.json`.

`rank` is the 1-based position in the alphabetical (sorted-path) file order — a stable
enumeration aid, NOT a priority signal. `area` is the atom's parent directory name under
`product/` (a top-level `product/` file gets `"product"`). `token_estimate` is COMPUTED
from the body (`word_count * 1.35`) rather than read from a stored, hand-maintained
copy — a value that is stored AND derivable drifts.

`generated_at` records when the catalog's CONTENT last changed, not when this command
last ran: regenerating an unchanged catalog keeps the recorded stamp, so running the
verb is idempotent down to the byte and a clean tree stays clean.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _memory_schema import CATALOG, PRODUCT, WIKILINK_RE, parse  # noqa: E402

Catalog = dict[str, Any]


class Refusal(Exception):
    """A write this script refuses, carrying the one `fix:` line that unblocks it."""

    def __init__(self, message: str, fix: str = "") -> None:
        super().__init__(message)
        self.fix = fix


def atoms(specs: Path) -> list[Path]:
    """Every feature atom under `product/`, in the alphabetical order `rank` follows."""
    product = specs / PRODUCT
    if not product.is_dir():
        raise Refusal(
            f"no {PRODUCT}/ under {specs} — there is no catalog to generate",
            f"mkdir -p {specs / PRODUCT}",
        )
    return sorted(path for path in product.rglob("*.md") if path.name != "index.md")


def _depends_on(body: str) -> list[str]:
    seen: list[str] = []
    for slug in WIKILINK_RE.findall(body):
        if slug not in seen:
            seen.append(slug)
    return seen


def estimate_tokens(body: str) -> int:
    """An atom body's approximate token count — the ONE formula."""
    return round(len(body.split()) * 1.35)


def feature(path: Path, specs: Path, rank: int) -> dict[str, Any]:
    """One catalog entry built from *path*'s frontmatter and body."""
    data, body, error = parse(path.read_text(encoding="utf-8"))
    if error is not None or data is None:
        raise Refusal(
            f"{path}: {error}",
            f"python3 {Path(__file__).parent / 'memory.py'} check --specs {specs}",
        )
    product = specs / PRODUCT
    return {
        "rank": rank,
        "slug": str(data.get("slug", path.stem)),
        "title": str(data.get("title", data.get("slug", path.stem))),
        "area": "product" if path.parent == product else path.parent.name,
        "tldr": str(data.get("tldr", "")),
        "summary": str(data.get("summary", "")),
        "path": path.relative_to(specs.parent).as_posix(),
        "tags": list(data.get("tags") or []),
        "token_estimate": estimate_tokens(body),
        "depends_on": _depends_on(body),
    }


def generate(specs: Path) -> Catalog:
    """The catalog dict for *specs*, `generated_at` carried over when nothing changed."""
    features = [feature(path, specs, rank) for rank, path in enumerate(atoms(specs), start=1)]
    return {
        "generated_at": _stamp(specs, features),
        "context": specs.parent.name,
        "features": features,
    }


def _stamp(specs: Path, features: list[dict[str, Any]]) -> str:
    path = specs / CATALOG
    if path.is_file():
        try:
            previous = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            previous = {}
        if previous.get("features") == features and isinstance(previous.get("generated_at"), str):
            return str(previous["generated_at"])
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def serialize(catalog: Catalog) -> str:
    return json.dumps(catalog, ensure_ascii=False, indent=2) + "\n"
