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

#: Bug ``r22-live-backlog-author-accepts-unterminated-frontmatter``: the mirror image of
#: the R9 case. The live Codex author wrote the keys and the CLOSING delimiter but omitted
#: the OPENING one, and the same conflation followed — read as "no frontmatter", promoted
#: with ``status=None``, and surfaced at ``backlog_review_gate`` as a missing status.
_UNOPENED = """name: greeting-cli
status: candidate
intents: []
---

# BACKLOG — the worker forgot the opening delimiter
"""

#: The shape that must NOT be mistaken for the above: prose, then a Markdown horizontal
#: rule. Nothing here declares frontmatter, and calling it malformed would block honest
#: files.
_HORIZONTAL_RULE = """# BACKLOG — a normal item

Some prose describing the work.

---

More prose after a horizontal rule.
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


def test_a_block_that_never_opened_is_reported_as_such(tmp_path: Path) -> None:
    """Bug ``r22-live-backlog-author-accepts-unterminated-frontmatter``.

    R9 taught the parser about a block that opens and never closes. A live worker then
    produced the mirror image — keys and a closing delimiter, no opening one — and the
    identical conflation followed, because the fix had been written for the reported
    shape rather than for the thing that was actually wrong: a file that DECLARES
    frontmatter and gets the delimiters wrong is malformed either way.
    """
    item = _item(tmp_path, "greeting-cli-2", _UNOPENED)
    assert item.frontmatter_error is not None, (
        "frontmatter missing its opening delimiter was read as 'no frontmatter', so the "
        "run blocked later at the review gate on a status the parser could not see"
    )
    assert "opening" in item.frontmatter_error.lower()


def test_a_markdown_horizontal_rule_is_not_called_malformed(tmp_path: Path) -> None:
    """The guard against fixing this by suspecting every '---' in the corpus.

    A false positive here blocks an item that is perfectly fine, which is worse than the
    defect: the operator cannot make the complaint go away by fixing anything.
    """
    item = _item(tmp_path, "prose", _HORIZONTAL_RULE)
    assert item.frontmatter_error is None
