#!/usr/bin/env python3
"""The birth of one ``active[]`` entry."""

from __future__ import annotations

import datetime as _dt
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _backlog_store import SCRIPT, Items, Refusal  # noqa: E402
from _specs import choice  # noqa: E402

_SLUG_RE = re.compile(r"^[a-z][a-z0-9-]+$")
_INTENT_RE = re.compile(r"^(?P<kind>[a-z]+):(?P<ref>[^=]+)=(?P<change>.+)$", re.DOTALL)
KINDS = ("code", "doc", "invariant", "catalog")


def today() -> str:
    return _dt.datetime.now(tz=_dt.UTC).strftime("%Y-%m-%d")


def parse_intents(raw: list[str] | None) -> list[dict[str, Any]]:
    """``--intent <kind>:<ref>=<change>`` into the typed ``intents[]`` shape."""
    intents: list[dict[str, Any]] = []
    for item in raw or []:
        match = _INTENT_RE.match(item)
        if match is None or match.group("kind") not in KINDS:
            raise Refusal(
                f"intent {item!r} is not '<kind>:<ref>=<change>' with kind in {list(KINDS)}",
                f"{SCRIPT} new --help",
            )
        intents.append(
            {
                "subject": {"kind": match.group("kind"), "ref": match.group("ref").strip()},
                "change": match.group("change").strip(),
            }
        )
    return intents


def new_entry(active: Items, slug: str, values: dict[str, Any]) -> Items:
    """One brand-new entry, born at ``status: 'idea'`` — an unbound brainstorm, which is
    the one status exempt from the typed-intents requirement, so it is doctor-clean with
    no further edits."""
    if not _SLUG_RE.fullmatch(slug):
        raise choice(Refusal(f"invalid slug {slug!r}: must match ^[a-z][a-z0-9-]+$ (lowercase "
                     "letters, digits and hyphens, starting with a letter)"),
                     "with a valid slug in its place", slug)  # fmt: skip
    if any(item.get("id") == slug for item in active):
        raise choice(Refusal(f"backlog slug {slug!r} is already a live active[] entry — an item is "
                     "retained forever, so a second entry under this id would be a second "
                     "identity for it"), "with a slug no entry holds in its place",
                     slug)  # fmt: skip
    relates, live = values.get("relates"), [str(item.get("id")) for item in active]
    names = [] if relates in (None, "none") else str(relates).split(",")
    if not set(names) <= set(live) or live and relates is None:
        raise choice(Refusal("name the live entries this one updates, obsoletes or relates to "
                     f"(ADR 0127): {', '.join(live) or 'none'}"),
                     "with --relates set to the comma-separated live entries, or none",
                     "--relates")  # fmt: skip
    intents = parse_intents(values.get("intent"))
    entry: dict[str, Any] = {
        "id": slug,
        "title": values.get("title") or slug,
        "opened": today(),
        "status": "idea",
        "description": values.get("description") or "(one-line description of the need)",
        "provenance": values.get("provenance") or "operator request",
    }
    if intents:
        entry["intents"] = intents
    if live:
        entry["relates"] = names
    return [*active, entry]
