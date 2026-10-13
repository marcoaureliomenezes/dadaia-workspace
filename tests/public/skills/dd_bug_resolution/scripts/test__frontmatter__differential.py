"""The kernel's frontmatter owner equals ``yaml.safe_load`` or refuses.

``yaml`` is the dev-only oracle and is imported by this test only. Every case is a block:
the owner must raise ``ValueError`` or return what ``yaml.safe_load`` returns (compared by
``repr``); where ``safe_load`` itself raises, the owner must raise too. Files are
enumerated at collection and parsed inside the test; the mutation corpus is committed data
(``tests/fixtures/frontmatter_mutations.json``), never regenerated here.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest
import yaml

from dadaia_workspace.core.skill_owner import load_owner

_ROOT = Path(__file__).resolve().parents[5]
_BLOCK = re.compile(r"\A---[ \t]*\n(.*?)\n---[ \t]*\n?", re.DOTALL)
_SHIPPED = sorted(
    [*(_ROOT / "dadaia_workspace/public").rglob("*.md"), *(_ROOT / "specs").rglob("*.md")]
)
_TESTS = sorted((_ROOT / "tests").rglob("*.py"))
_CORPUS = _ROOT / "tests/fixtures/frontmatter_mutations.json"


def _block(text: str) -> str | None:
    match = _BLOCK.match(text.removeprefix("﻿").replace("\r\n", "\n"))
    return match.group(1) if match else None


def _assert_equals_or_refuses(block: str) -> None:
    fm = load_owner("dd-bug-resolution", "_frontmatter")
    try:
        expected = repr(yaml.safe_load(block))
    except yaml.YAMLError:
        with pytest.raises(ValueError):
            fm.parse(block)
        return
    try:
        got = repr(fm.parse(block))
    except ValueError:
        return
    assert got == expected, block


@pytest.mark.parametrize("path", _SHIPPED, ids=lambda p: p.relative_to(_ROOT).as_posix())
def test_every_shipped_and_instance_frontmatter_equals_safe_load_or_is_refused(
    path: Path,
) -> None:
    block = _block(path.read_text(encoding="utf-8"))
    if block is not None:
        _assert_equals_or_refuses(block)


def test_every_inline_frontmatter_literal_of_the_suite_equals_safe_load_or_is_refused() -> None:
    seen = 0
    for path in _TESTS:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                block = _block(node.value)
                if block is not None:
                    seen += 1
                    _assert_equals_or_refuses(block)
    assert seen > 20


def test_the_pinned_mutation_corpus_equals_safe_load_or_is_refused() -> None:
    cases = json.loads(_CORPUS.read_text(encoding="utf-8"))["cases"]
    assert len(cases) >= 3000
    for case in cases:
        _assert_equals_or_refuses(case)
