"""F017 (20260830-design-bug-surface-audit): the bug-ledger ``component`` field gains
a normalizer at the ONE write seam. 539 records held 3+ spellings of the same file and
114 no parseable component — blunting the recurrence analysis the permanent
architecture-review law depends on. Normalization is conservative and NEVER blocks
registration (the bugs lane is ADDITIVE): path-shaped and module-shaped values
canonicalize to the on-disk repo-relative ``path#symbol`` form; free text passes
through stripped. Intent: contract; size: unit.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.bugs.service import normalize_component


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    (tmp_path / "dadaia_workspace" / "cli" / "commands").mkdir(parents=True)
    (tmp_path / "dadaia_workspace" / "cli" / "commands" / "context.py").write_text(
        "", encoding="utf-8"
    )
    (tmp_path / "dadaia_workspace" / "container.py").write_text("", encoding="utf-8")
    return tmp_path


def test_dotted_module_spelling_canonicalizes(repo: Path) -> None:
    assert (
        normalize_component("cli.commands.context", repo_root=repo)
        == "dadaia_workspace/cli/commands/context.py"
    )


def test_bare_path_without_prefix_or_suffix_canonicalizes(repo: Path) -> None:
    assert (
        normalize_component("cli/commands/context", repo_root=repo)
        == "dadaia_workspace/cli/commands/context.py"
    )
    assert (
        normalize_component("cli/commands/context.py", repo_root=repo)
        == "dadaia_workspace/cli/commands/context.py"
    )


def test_already_canonical_and_symbol_suffix_preserved(repo: Path) -> None:
    assert (
        normalize_component("dadaia_workspace/container.py#build_panel_views", repo_root=repo)
        == "dadaia_workspace/container.py#build_panel_views"
    )


def test_free_text_passes_through_stripped(repo: Path) -> None:
    assert (
        normalize_component("  workflow engine (demolished) ", repo_root=repo)
        == "workflow engine (demolished)"
    )
    assert normalize_component("", repo_root=repo) == ""


def test_backslashes_normalize(repo: Path) -> None:
    assert (
        normalize_component("dadaia_workspace\\container.py", repo_root=repo)
        == "dadaia_workspace/container.py"
    )
