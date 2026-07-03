"""Tests for inline SVG logo validity (XML well-formed, no hardcoded colors).

Spec: dadaia-workspace-brand-identity-v1 SPEC.md §3 logo specs.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from dadaia_workspace.features.panel.views.static import LOGO_RHINO_16, LOGO_RHINO_24

_HEX_RE = re.compile(r"^#[0-9a-fA-F]{3,8}$")


def _all_descendants(root: ET.Element) -> list[ET.Element]:
    return [el for el in root.iter() if el is not root]


def _drawable_count(root: ET.Element) -> int:
    return sum(
        1
        for el in _all_descendants(root)
        if el.tag.endswith("}path") or el.tag.endswith("}circle") or el.tag in ("path", "circle")
    )


def test_logo_24_is_well_formed() -> None:
    root = ET.fromstring(LOGO_RHINO_24)
    assert root.tag.endswith("svg")
    assert root.attrib.get("viewBox") == "0 0 24 24"


def test_logo_16_is_well_formed() -> None:
    root = ET.fromstring(LOGO_RHINO_16)
    assert root.tag.endswith("svg")
    assert root.attrib.get("viewBox") == "0 0 16 16"


def test_logo_24_uses_only_current_color() -> None:
    root = ET.fromstring(LOGO_RHINO_24)
    for el in [root, *_all_descendants(root)]:
        for attr in ("fill", "stroke"):
            value = el.attrib.get(attr)
            if value is None:
                continue
            assert not _HEX_RE.match(value), (
                f"logo-24 has hardcoded hex {attr}={value!r} in {el.tag}"
            )


def test_logo_16_uses_only_current_color() -> None:
    root = ET.fromstring(LOGO_RHINO_16)
    for el in [root, *_all_descendants(root)]:
        for attr in ("fill", "stroke"):
            value = el.attrib.get(attr)
            if value is None:
                continue
            assert not _HEX_RE.match(value), (
                f"logo-16 has hardcoded hex {attr}={value!r} in {el.tag}"
            )


def test_logo_24_has_at_most_three_drawable_elements() -> None:
    root = ET.fromstring(LOGO_RHINO_24)
    assert _drawable_count(root) <= 3


def test_logo_16_has_at_most_three_drawable_elements() -> None:
    root = ET.fromstring(LOGO_RHINO_16)
    assert _drawable_count(root) <= 3
