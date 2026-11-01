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
from tests.fixtures.real_git import git
from tests.helpers.oslib import read_text, write_text
from tests.helpers.suite_files import tracked

_ROOT = Path(__file__).resolve().parents[5]
_BLOCK = re.compile(r"\A---[ \t]*\n(.*?)\n---[ \t]*\n?", re.DOTALL)


_SHIPPED = tracked(_ROOT, "dadaia_workspace/public/*.md", "specs/*.md")
_TESTS = tracked(_ROOT, "tests/*.py")
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
    block = _block(read_text(path))
    if block is not None:
        _assert_equals_or_refuses(block)


def test_every_inline_frontmatter_literal_of_the_suite_equals_safe_load_or_is_refused() -> None:
    seen = 0
    for path in _TESTS:
        for node in ast.walk(ast.parse(read_text(path))):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                block = _block(node.value)
                if block is not None:
                    seen += 1
                    _assert_equals_or_refuses(block)
    assert seen > 20


def test_the_suite_walk_holds_no_untracked_file(tmp_path: Path) -> None:
    git(tmp_path, "init", "-q")
    (tmp_path / "tests/tmp").mkdir(parents=True)
    write_text(tmp_path / "tests" / "test_kept.py", "X = 1\n")
    git(tmp_path, "add", "tests/test_kept.py")
    write_text(tmp_path / "tests" / "test_gone.py", "X = 1\n")
    assert tracked(tmp_path, "tests/*.py") == [tmp_path / "tests/test_kept.py"]


def test_the_pinned_mutation_corpus_equals_safe_load_or_is_refused() -> None:
    cases = json.loads(read_text(_CORPUS))["cases"]
    assert len(cases) >= 3000
    for case in cases:
        _assert_equals_or_refuses(case)
