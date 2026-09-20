#!/usr/bin/env python3
"""``backlog.py subjects`` — what an intent author can bind to, and how one ref binds.

The ~5k derived code/doc/cli anchors stay where their reader lives: the doctor's
`BL-SCHEMA` registry derives them from the source tree, and a second derivation inside
a stdlib skill script would be exactly the drift that registry exists to prevent. What
this verb shows is what the two files this script owns can answer: the operator alias
map, and the subjects the live document already binds.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _backlog_schema import LEDGER  # noqa: E402
from _backlog_store import read_active  # noqa: E402


def _anchors(specs: Path, alias_map: Path) -> dict[str, tuple[str, str]]:
    """Every bindable subject this script can see, keyed by its lowercase synonym: the
    operator alias map plus the subjects the live document already binds."""
    found: dict[str, tuple[str, str]] = {}
    text = alias_map.read_text(encoding="utf-8") if alias_map.is_file() else ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "->" not in line:
            continue
        synonym, anchor = (part.strip() for part in line.split("->", 1))
        kind = anchor.split(":", 1)[0] if ":" in anchor else "alias"
        found[synonym.lower()] = (kind, anchor)
    for item in read_active(specs / LEDGER):
        for intent in item.get("intents", []):
            subject = intent["subject"]
            found[str(subject["ref"]).lower()] = (str(subject["kind"]), str(subject["ref"]))
    return found


def subjects(args: argparse.Namespace, specs: Path, alias_default: str) -> int:
    """List the bindable anchors, or resolve one proposed subject ref against them."""
    alias_map = args.alias_map if args.alias_map is not None else specs.parent / alias_default
    anchors = _anchors(specs, alias_map)
    if args.resolve is not None:
        hit = anchors.get(args.resolve.strip().lower())
        if hit is not None and (args.kind is None or hit[0] == args.kind):
            print(f"RESOLVED  {args.resolve}  ->  {hit[1]}")
            return 0
        print(f"UNRESOLVED  {args.resolve}", file=sys.stderr)
        print(f"fix: {Path(__file__).name} subjects --specs {specs}", file=sys.stderr)
        return 1
    listed = sorted(v for v in anchors.values() if args.kind is None or v[0] == args.kind)
    for kind, anchor in listed:
        print(f"{kind:10s}  {anchor}")
    print(f"\n[ok] {len(listed)} anchor(s).")
    return 0
