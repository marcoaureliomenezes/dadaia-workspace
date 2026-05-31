"""Catalog generator for product memory feature index.

Reads ``specs/memory/product/index.html``, parses the
``<ol class="catalog">`` entries, and returns a structured dict
suitable for serialisation as ``catalog.json``.

Public API
----------
generate_catalog(specs_dir: Path) -> dict
    Read ``specs_dir/memory/product/index.html`` and return the catalog dict.

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
      "summary": "...",
      "path": "specs/memory/product/workspace-init.html",
      "tags": [],
      "depends_on": []
    },
    ...
  ]
}

Pure module — only ``html.parser`` and ``json`` from stdlib.
No new PyPI dependencies.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal HTML parser targeting <ol class="catalog"> entries
# ---------------------------------------------------------------------------


class _CatalogParser(HTMLParser):
    """Extract entries from the ``<ol class="catalog">`` list in ``index.html``.

    Each ``<li>`` directly under the target ``<ol>`` is expected to contain
    at least one ``<a href="<slug>.html"><title></a>`` element.  Adjacent
    text (e.g. a ``<span class="desc">`` sibling) is captured as the summary.

    State machine:
      IDLE  →  in_catalog_ol  →  in_li  →  in_anchor (within li)

    Entry collection is deferred until ``</li>`` so that all sibling text
    (including ``<span class="desc">`` content) is accumulated before the
    entry is recorded.
    """

    def __init__(self) -> None:
        super().__init__()
        self._depth: int = 0  # nesting depth inside the catalog <ol>
        self._in_catalog_ol: bool = False
        self._in_li: bool = False
        self._in_anchor: bool = False
        self._current_href: str = ""
        self._anchor_text: list[str] = []
        self._li_text: list[str] = []  # all text inside the current <li>
        # Pending anchor data: captured when </a> fires, committed when </li> fires
        self._pending_href: str = ""
        self._pending_anchor: str = ""

        # Results: list of (href, anchor_text, full_li_text)
        self.entries: list[tuple[str, str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map: dict[str, str] = {k: (v or "") for k, v in attrs}

        if tag == "ol":
            classes = attr_map.get("class", "").split()
            if "catalog" in classes:
                self._in_catalog_ol = True
                self._depth = 1
                return
            if self._in_catalog_ol:
                self._depth += 1
            return

        if not self._in_catalog_ol:
            return

        if tag == "li" and self._depth == 1:
            self._in_li = True
            self._li_text = []
            self._pending_href = ""
            self._pending_anchor = ""
            return

        if tag == "a" and self._in_li:
            self._in_anchor = True
            self._current_href = attr_map.get("href", "")
            self._anchor_text = []
            return

    def handle_endtag(self, tag: str) -> None:
        if not self._in_catalog_ol:
            return

        if tag == "ol":
            self._depth -= 1
            if self._depth <= 0:
                self._in_catalog_ol = False
                self._depth = 0
            return

        if tag == "a" and self._in_anchor:
            # Close anchor: save href + anchor_text as pending; do NOT emit yet
            self._in_anchor = False
            self._pending_href = self._current_href
            self._pending_anchor = "".join(self._anchor_text).strip()
            return

        if tag == "li" and self._in_li and self._depth == 1:
            # Close li: NOW emit the entry with all accumulated li text
            self._in_li = False
            href = self._pending_href
            anchor_text = self._pending_anchor
            li_text = "".join(self._li_text).strip()
            if href:
                self.entries.append((href, anchor_text, li_text))
            return

    def handle_data(self, data: str) -> None:
        if self._in_anchor:
            self._anchor_text.append(data)
        if self._in_li:
            self._li_text.append(data)


# ---------------------------------------------------------------------------
# Helper: extract summary from the full <li> text
# ---------------------------------------------------------------------------


def _extract_summary(li_text: str, anchor_text: str) -> str:
    """Return the descriptive part of a catalog list item.

    The li_text typically looks like:
        "workspace-init— porta de entrada; cria .dadaia/, .venv, hooks…"
    or
        "workspace-init — porta de entrada; …"

    We strip the anchor_text prefix and the leading em-dash / dash separator.
    """
    text = li_text.strip()
    # Remove the anchor text from the beginning (if present)
    if anchor_text and text.startswith(anchor_text):
        text = text[len(anchor_text) :]
    # Strip leading em-dash variants (— EM DASH, – EN DASH, - HYPHEN-MINUS) and whitespace
    text = text.lstrip()
    for dash in ("—", "–", "-"):
        if text.startswith(dash):
            text = text[len(dash) :].strip()
            break
    return text.strip()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_catalog(specs_dir: Path) -> dict:  # type: ignore[type-arg]
    """Read ``specs_dir/memory/product/index.html`` and return the catalog dict.

    Args:
        specs_dir: Path to the ``specs/`` directory (e.g.
            ``/path/to/repo/specs``).

    Returns:
        A dict matching the catalog JSON schema:
        ``{ "generated_at": ..., "context": ..., "features": [...] }``

    Raises:
        FileNotFoundError: if ``specs_dir/memory/product/index.html`` is absent.
        ValueError: if the catalog ``<ol class="catalog">`` is not found in the
            index HTML (malformed file).
    """
    index_path = Path(specs_dir) / "memory" / "product" / "index.html"
    if not index_path.exists():
        raise FileNotFoundError(f"index.html not found at expected path: {index_path}")

    html_text = index_path.read_text(encoding="utf-8")
    parser = _CatalogParser()
    parser.feed(html_text)

    # Derive context name from the parent of specs_dir (the repo/project name)
    context_name = Path(specs_dir).parent.name

    features: list[dict] = []  # type: ignore[type-arg]
    for rank, (href, anchor_text, li_text) in enumerate(parser.entries, start=1):
        # slug is the stem of the href filename (e.g. "workspace-init.html" → "workspace-init")
        slug = Path(href).stem
        title = anchor_text or slug
        summary = _extract_summary(li_text, anchor_text)
        path = f"specs/memory/product/{slug}.html"

        features.append(
            {
                "rank": rank,
                "slug": slug,
                "title": title,
                "summary": summary,
                "path": path,
                "tags": [],
                "depends_on": [],
            }
        )

    generated_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    catalog: dict = {  # type: ignore[type-arg]
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


def write_catalog(specs_dir: Path, catalog: dict) -> Path:  # type: ignore[type-arg]
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
