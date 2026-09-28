#!/usr/bin/env python3
"""``backlog.py subjects`` — the operator alias map's anchors. Resolving a ref is the
doctor's `BL-SCHEMA` registry's alone; this verb never answers it."""

from __future__ import annotations

import argparse
from pathlib import Path


def subjects(args: argparse.Namespace, specs: Path, alias_default: str) -> int:
    """List the alias map's anchors, optionally one kind."""
    alias_map = args.alias_map if args.alias_map is not None else specs.parent / alias_default
    text = alias_map.read_text(encoding="utf-8") if alias_map.is_file() else ""
    anchors = sorted(
        {
            line.split("->", 1)[1].strip()
            for line in text.splitlines()
            if "->" in line and not line.lstrip().startswith("#")
        }
    )
    listed = [a for a in anchors if args.kind is None or a.startswith(f"{args.kind}:")]
    for anchor in listed:
        print(anchor)
    print(f"\n[ok] {len(listed)} anchor(s).")
    return 0
