"""Tests for inline SVG logo validity (XML well-formed, no hardcoded colors).

Spec: dadaia-workspace-brand-identity-v1 SPEC.md §3 logo specs.

One param over both logos: well-formed XML + viewBox + no hardcoded hex fills
+ <=3 drawables.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

import pytest

from dadaia_workspace.features.panel.views.static import LOGO_RHINO_16, LOGO_RHINO_24

pytestmark = pytest.mark.unit

_HEX_RE = re.compile(r"^#[0-9a-fA-F]{3,8}$")


def _all_descendants(root: ET.Element) -> list[ET.Element]:
    return [el for el in root.iter() if el is not root]


def _drawable_count(root: ET.Element) -> int:
    return sum(
        1
        for el in _all_descendants(root)
        if el.tag.endswith("}path") or el.tag.endswith("}circle") or el.tag in ("path", "circle")
    )


@pytest.mark.parametrize(
    ("logo_svg", "expected_viewbox"),
    [
        pytest.param(LOGO_RHINO_24, "0 0 24 24", id="logo-rhino-24"),
        pytest.param(LOGO_RHINO_16, "0 0 16 16", id="logo-rhino-16"),
    ],
)
def test_logo_svg_is_well_formed_no_hardcoded_color_and_bounded_drawables(
    logo_svg: str, expected_viewbox: str
) -> None:
    root = ET.fromstring(logo_svg)

    assert root.tag.endswith("svg")
    assert root.attrib.get("viewBox") == expected_viewbox

    for el in [root, *_all_descendants(root)]:
        for attr in ("fill", "stroke"):
            value = el.attrib.get(attr)
            if value is None:
                continue
            assert not _HEX_RE.match(value), f"logo has hardcoded hex {attr}={value!r} in {el.tag}"

    assert _drawable_count(root) <= 3
