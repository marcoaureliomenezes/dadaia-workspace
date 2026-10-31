#!/usr/bin/env python3
"""The memory atom grammar's door: the kernel's `_memory_drift` owns the rules and the path
constants; the navigator, the library lint and `memory_canon` read them from here."""

from __future__ import annotations

from _memory_drift import CODE, INDEX, PRODUCT, WIKILINK_RE, parse

__all__ = ["CODE", "INDEX", "PRODUCT", "WIKILINK_RE", "parse"]
