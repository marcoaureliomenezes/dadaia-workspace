"""Intent: CONTRACT — 0.4.6 AC7 (V32, V33, V34); size: SMALL (contract).

Three repo-pure slop ratchets: measured at birth, pinned, ratcheting down only; every
tree walk goes through the one tracked-files enumeration the other ratchets use.
"""

from __future__ import annotations

import ast
import io
import re
import tokenize
from collections.abc import Iterable
from pathlib import Path

import pytest

from tests.helpers.suite_files import tracked_test_files

pytestmark = pytest.mark.contract

_REPO_ROOT = Path(__file__).resolve().parents[2]
_THIS_FILE = Path(__file__).resolve()

# ---------------------------------------------------------------------------
# V32 — governance ids in production comments and docstrings
# ---------------------------------------------------------------------------

_GOVERNANCE_ID_RE = re.compile(
    r"\b(FR[0-9]+|T-[0-9]{2,3}(-[0-9]+)?|ADR[ -]?[0-9]+|v0\.[0-9]+(\.[0-9]+)?)\b"
)
_DOCSTRING_OWNERS = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)

# RECORDED CEILING (ratchet DOWN ONLY) — measured 2026-09-03 on this HEAD, every comment
# token plus every docstring line under dadaia_workspace/**/*.py. Lower it in the commit
# that deletes the ids; raising it is never a ratchet move.
_V32_CEILING = 912


def _governance_id_lines(source: str) -> int:
    """Comment tokens and docstring lines of *source* that carry a governance id."""
    hits = sum(
        1
        for token in tokenize.generate_tokens(io.StringIO(source).readline)
        if token.type == tokenize.COMMENT and _GOVERNANCE_ID_RE.search(token.string)
    )
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, _DOCSTRING_OWNERS):
            docstring = ast.get_docstring(node, clean=False) or ""
            hits += sum(1 for line in docstring.splitlines() if _GOVERNANCE_ID_RE.search(line))
    return hits


def test_v32_governance_ids_in_production_comments_and_docstrings() -> None:
    """V32 — comment tokens and docstring lines under dadaia_workspace/ naming an FR, T-,
    ADR or v0.x id, pinned at 912. Ratchet DOWN ONLY; target 0 (tests/ are excluded)."""
    total = sum(
        _governance_id_lines(path.read_text(encoding="utf-8"))
        for path in tracked_test_files(_REPO_ROOT, "*.py", tree="dadaia_workspace")
    )
    assert total <= _V32_CEILING, (
        f"governance ids in production comments/docstrings grew to {total} "
        f"(ceiling {_V32_CEILING}). The what, the history and any spec, task, ADR or "
        "version id live in git and the ledgers — delete the id, never raise the ceiling."
    )

    # Mutation fixture — a clean module counts 0; one docstring line and one comment
    # carrying an id count 2.
    clean = 'X = 1  # the non-obvious why\n\n\ndef f() -> None:\n    """Contract."""\n'
    assert _governance_id_lines(clean) == 0
    violating = '"""Entrypoint (FR99, T-000-00)."""\nX = 1  # see ADR 0000\n'
    assert _governance_id_lines(violating) == 2


# ---------------------------------------------------------------------------
# V33 — PREFIX-NN families without a mechanical reader
# ---------------------------------------------------------------------------

_FAMILY_TOKEN_RE = re.compile(r"\b[A-Z]{1,4}-?[0-9]{2,3}\b")
_UPPER_RUN_RE = re.compile(r"[A-Z]+")
_WORD_CHARS = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-")
_V33_TOKEN_TREES = ("specs", "dadaia_workspace", "tests")
_V33_READER_TREES = ("dadaia_workspace", "tests")

# RECORDED CEILING (ratchet DOWN ONLY) — measured 2026-09-03 on this HEAD; the failing
# assertion prints the orphan family list so the number is reproducible.
_V33_CEILING = 54


def _family_witnesses(texts: Iterable[str]) -> dict[str, set[tuple[str, int]]]:
    """Each family prefix mapped to the words its tokens sit in and the prefix offset."""
    families: dict[str, set[tuple[str, int]]] = {}
    for text in texts:
        for match in _FAMILY_TOKEN_RE.finditer(text):
            left, right = match.start(), match.end()
            while left > 0 and text[left - 1] in _WORD_CHARS:
                left -= 1
            while right < len(text) and text[right] in _WORD_CHARS:
                right += 1
            prefix = _UPPER_RUN_RE.match(match.group(0))
            assert prefix is not None
            families.setdefault(prefix.group(0), set()).add(
                (text[left:right], match.start() - left)
            )
    return families


def _string_constants(source: str) -> list[str]:
    """Every non-empty string constant in *source* that is not a bare docstring statement."""
    tree = ast.parse(source)
    bare = {
        id(node.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)
    }
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and node.value
        and id(node) not in bare
    ]


def _reads_family(constant: str, prefix: str, witnesses: Iterable[tuple[str, int]]) -> bool:
    """*constant* (a regex, else a literal) matches a witness through its prefix and beyond."""
    try:
        pattern = re.compile(constant)
    except re.error:
        pattern = re.compile(re.escape(constant))
    return any(
        (match := pattern.search(word)) is not None
        and match.start() <= offset
        and match.end() > offset + len(prefix)
        for word, offset in witnesses
    )


def _orphan_families(texts: Iterable[str], constants: Iterable[str]) -> list[str]:
    """Family prefixes found in *texts* that no constant in *constants* reads."""
    readers: dict[str, list[str]] = {}
    for constant in constants:
        for run in set(_UPPER_RUN_RE.findall(constant)):
            readers.setdefault(run, []).append(constant)
    return sorted(
        prefix
        for prefix, witnesses in _family_witnesses(texts).items()
        if not any(_reads_family(c, prefix, witnesses) for c in readers.get(prefix, ()))
    )


def _tracked_texts(tree: str, pattern: str) -> Iterable[str]:
    for path in tracked_test_files(_REPO_ROOT, pattern, tree=tree):
        if "_archive" in path.relative_to(_REPO_ROOT).parts or path == _THIS_FILE:
            continue
        try:
            yield path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue


def test_v33_prefix_families_without_a_mechanical_reader() -> None:
    """V33 — distinct `PREFIX-NN` families over specs/ (minus _archive/), dadaia_workspace/
    and tests/ that no regex or string constant in the source trees reads. DOWN ONLY."""
    texts = [text for tree in _V33_TOKEN_TREES for text in _tracked_texts(tree, "*")]
    constants = [
        constant
        for tree in _V33_READER_TREES
        for source in _tracked_texts(tree, "*.py")
        for constant in _string_constants(source)
    ]
    orphans = _orphan_families(texts, constants)
    assert len(orphans) <= _V33_CEILING, (
        f"{len(orphans)} PREFIX-NN families have no mechanical reader (ceiling "
        f"{_V33_CEILING}). A concept takes a glossary name; a numbered code exists only "
        f"where a mechanical index reads it. Orphan families: {orphans}"
    )

    # Mutation fixture — upper-cased at runtime so the fixture never enters the scan
    # itself: one read family, one orphan; dropping the reader makes both orphans.
    corpus = ["foo-01 has a reader, bar-02 has none".upper()]
    assert _orphan_families(corpus, ["foo-".upper()]) == ["BAR"]
    assert _orphan_families(corpus, []) == ["BAR", "FOO"]


# ---------------------------------------------------------------------------
# V34 — bytes of the live candidate's SPEC.md and TASKS.md
# ---------------------------------------------------------------------------

_V34_CEILINGS = {"SPEC.md": 24 * 1024, "TASKS.md": 12 * 1024}


def _live_release_dir() -> Path:
    """The one non-archived `specs/releases/<id>/` carrying a `_RELEASE.json`."""
    releases = _REPO_ROOT / "specs" / "releases"
    live = [
        path.parent
        for path in tracked_test_files(_REPO_ROOT, "_RELEASE.json", tree="specs/releases")
        if path.parent.parent == releases
    ]
    assert len(live) == 1, f"exactly one live release expected, found {live}"
    return live[0]


def _byte_ceiling_violations(sizes: dict[str, int]) -> list[str]:
    return [
        f"{name}: {size} B > {_V34_CEILINGS[name]} B"
        for name, size in sizes.items()
        if size > _V34_CEILINGS[name]
    ]


def test_v34_live_candidate_trio_bytes_under_the_fixed_ceiling() -> None:
    """V34 — the live candidate's SPEC.md is at most 24 KB and its TASKS.md at most 12 KB;
    a fixed ceiling, never a pin."""
    live = _live_release_dir()
    sizes = {name: (live / name).stat().st_size for name in _V34_CEILINGS}
    assert _byte_ceiling_violations(sizes) == [], (
        f"{live.name} trio exceeds the byte ceiling — above it the scope is open enough "
        "to be two candidates."
    )

    # Mutation fixture — one byte over either ceiling is a violation.
    assert _byte_ceiling_violations({"SPEC.md": 24 * 1024 + 1, "TASKS.md": 12 * 1024}) == [
        "SPEC.md: 24577 B > 24576 B"
    ]
