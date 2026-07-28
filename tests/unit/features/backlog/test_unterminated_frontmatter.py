"""A backlog file whose frontmatter opens and never closes must say so.

Bug ``r9-f26-author-accepts-unterminated-frontmatter`` (found by the consumer-side
validator on R9/F-26, live Codex canary): the worker materialised an item starting with
``---`` and no closing delimiter. ``_parse_frontmatter`` matches on a regex that requires
BOTH delimiters, so a truncated block was indistinguishable from a file with no
frontmatter at all: both returned ``(None, None)``. The item was promoted with
``status=None``, and the failure surfaced much later at ``backlog_review_gate`` as
"status missing" — a diagnosis that points at the wrong thing and never mentions the
truncation the worker actually produced.

``frontmatter_error`` already existed for unparseable YAML; the truncated case simply
never reached it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.backlog.preview import load_backlog_items

pytestmark = pytest.mark.unit

_GOOD = """---
name: good-item
status: candidate
intents: []
---

# BACKLOG — good
"""

_UNTERMINATED = """---
name: greeting-cli
status: candidate
intents: []

# BACKLOG — the worker stopped writing before closing the block
"""

_NO_FRONTMATTER = """# BACKLOG — a plain markdown file with no frontmatter at all
"""


def _item(tmp_path: Path, name: str, body: str):
    backlog = tmp_path / "backlog"
    backlog.mkdir(exist_ok=True)
    (backlog / f"{name}.md").write_text(body, encoding="utf-8")
    return {item.slug: item for item in load_backlog_items(backlog)}[name]


def test_a_well_formed_item_reports_no_frontmatter_error(tmp_path: Path) -> None:
    item = _item(tmp_path, "good-item", _GOOD)
    assert item.frontmatter_error is None
    assert item.status == "candidate"


def test_an_unterminated_block_is_reported_as_such(tmp_path: Path) -> None:
    item = _item(tmp_path, "greeting-cli", _UNTERMINATED)
    assert item.frontmatter_error is not None, (
        "an unterminated frontmatter block was silently read as 'no frontmatter', so the "
        "real defect surfaced later as a misleading 'status missing'"
    )
    assert "unterminated" in item.frontmatter_error.lower()


def test_a_file_with_no_frontmatter_is_not_confused_with_a_truncated_one(
    tmp_path: Path,
) -> None:
    """The two cases must stay distinguishable — conflating them is the bug."""
    item = _item(tmp_path, "plain", _NO_FRONTMATTER)
    assert item.frontmatter_error is None
    assert item.status is None
