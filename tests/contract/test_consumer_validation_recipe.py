"""The packaged consumer-validation recipe must state real contracts.

Bug recipe-f23-demands-empty-stdout (validation 0.2.11): F-23 claimed an EMPTY
stdout from ctx-inject on a fresh unbound session is the correct result, while the
real (and correct) contract is a NON-empty generic dispatcher preflight with no
context memory. A recipe statement that contradicts the executed contract turns
every validation of that statement into a false FAIL — the recipe is a contract
surface and gets the same coherence law as any gate: it never demands what the
tooling correctly refuses to do.
"""

from __future__ import annotations

import re
from pathlib import Path

import dadaia_workspace

_RECIPE = (
    Path(dadaia_workspace.__file__).parent / "public" / "data" / "CONSUMER_VALIDATION_RECIPE.md"
)


def _f23_section() -> str:
    text = _RECIPE.read_text(encoding="utf-8")
    match = re.search(r"### F-23.*?(?=\n### |\n---|\Z)", text, flags=re.DOTALL)
    assert match, "recipe must carry an F-23 statement"
    return match.group(0)


def test_recipe_exists_in_package() -> None:
    assert _RECIPE.is_file()


def test_f15_cites_only_real_memory_verbs() -> None:
    """Bug recipe-f15-cites-nonexistent-memory-list: the recipe must cite verbs that
    exist on the CLI surface ('memory product add', 'memory catalog generate')."""
    text = _RECIPE.read_text(encoding="utf-8")
    assert "memory list" not in text
    assert "memory catalog generate" in text


def test_f23_describes_generic_preflight_not_empty_stdout() -> None:
    section = _f23_section()
    # The unbound ctx-inject contract: generic dispatcher preflight IS printed.
    assert "preflight" in section.lower()
    # The recipe must not demand an empty stdout — that contradicts the contract.
    assert "empty stdout" not in section.lower()
