#!/usr/bin/env python3
"""The birth of one ``active[]`` entry, and the redaction every backlog write runs.

Redaction is a WRITE-time seam, not a reporting one: an operator-local path or IP that
reaches the file is already published to every later reader.
"""

from __future__ import annotations

import datetime as _dt
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _backlog_store import SCRIPT, Items, Refusal  # noqa: E402

_SLUG_RE = re.compile(r"^[a-z][a-z0-9-]+$")
_INTENT_RE = re.compile(r"^(?P<kind>[a-z]+):(?P<ref>[^=]+)=(?P<change>.+)$", re.DOTALL)
_KINDS = ("code", "api", "cli", "panel", "doc", "invariant", "catalog")
_UNSAFE_RE = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\x80-\x9f\u2028\u2029]")
_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_POSIX_HOME_RE = re.compile(r"(/home/|/Users/)[^/\s:]+")
_WIN_HOME_RE = re.compile(r"([A-Za-z]:\\Users\\)[^\\\s:]+")


def today() -> str:
    return _dt.datetime.now(tz=_dt.UTC).strftime("%Y-%m-%d")


def redact(value: Any) -> Any:
    """Strip control/format characters, then mask operator-local home paths and IPv4
    addresses — the same three passes the retired CLI write seam ran."""
    if isinstance(value, dict):
        return {key: redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    if not isinstance(value, str):
        return value
    out = _UNSAFE_RE.sub("", value)
    out = _IPV4_RE.sub("[REDACTED-IP]", out)
    out = _POSIX_HOME_RE.sub(r"\1[REDACTED]", out)
    return _WIN_HOME_RE.sub(r"\1[REDACTED]", out)


def parse_intents(raw: list[str] | None) -> list[dict[str, Any]]:
    """``--intent <kind>:<ref>=<change>`` into the typed ``intents[]`` shape."""
    intents: list[dict[str, Any]] = []
    for item in raw or []:
        match = _INTENT_RE.match(item)
        if match is None or match.group("kind") not in _KINDS:
            raise Refusal(
                f"intent {item!r} is not '<kind>:<ref>=<change>' with kind in {list(_KINDS)}",
                f"{SCRIPT} subjects --specs <specs>",
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
        raise Refusal(
            f"invalid slug {slug!r}: must match ^[a-z][a-z0-9-]+$ (lowercase letters, "
            "digits and hyphens, starting with a letter)",
            f"{SCRIPT} new <a-valid-slug> --specs <specs>",
        )
    if any(item.get("id") == slug for item in active):
        raise Refusal(
            f"backlog slug {slug!r} is already a live active[] entry — an item is retained "
            "forever, so a second entry under this id would be a second identity for it",
            f"{SCRIPT} new <another-slug> --specs <specs>",
        )
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
    return [*active, redact(entry)]
