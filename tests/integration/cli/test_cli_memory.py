"""Integration tests for `dadaia memory product add` CLI command.

Merged per plan-integration.md (6 -> 1): one happy fn (create + frontmatter +
idempotent + multi-slug asserts). Both exit-nonzero error greps (invalid slug,
missing specs-dir) deleted — pure service logic, unit-owned.

memory-markdown-source-v1 (T-MMS-10/11): `memory product add <slug>` creates
`<slug>.md` (born-markdown scaffold with YAML frontmatter). The index.html
generation path was retired when the Jinja templates were deleted.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app

_runner = CliRunner()


@pytest.fixture()
def specs(tmp_path: Path) -> Path:
    """Return an empty specs/ directory."""
    s = tmp_path / "specs"
    s.mkdir()
    return s


def test_memory_product_add_creates_frontmatter_idempotent_and_multi_slug(
    specs: Path,
) -> None:
    """AC-T3-2/3, AC-C-6/7: creates feature Markdown atom with valid YAML frontmatter
    (no index.html — that pipeline was retired), a second call is idempotent
    (no re-create), and all added slugs each produce their own .md file."""
    result = _runner.invoke(
        app,
        ["memory", "product", "add", "payments", "--specs-dir", str(specs)],
    )
    assert result.exit_code == 0, result.output
    assert "created" in result.output
    assert (specs / "memory" / "product" / "payments.md").is_file()
    assert not (specs / "memory" / "product" / "index.html").exists(), (
        "index.html must NOT be generated (T-MMS-10/11 retired the HTML index)"
    )

    content = (specs / "memory" / "product" / "payments.md").read_text(encoding="utf-8")
    assert content.startswith("---"), "Feature .md must start with YAML frontmatter '---'"
    assert "slug: payments" in content, "Frontmatter must contain 'slug: payments'"

    result2 = _runner.invoke(
        app,
        ["memory", "product", "add", "payments", "--specs-dir", str(specs)],
    )
    assert result2.exit_code == 0, result2.output
    assert "already exists" in result2.output

    for slug in ("zebra", "alpha", "middle"):
        multi_result = _runner.invoke(
            app,
            ["memory", "product", "add", slug, "--specs-dir", str(specs)],
        )
        assert multi_result.exit_code == 0, multi_result.output

    for slug in ("zebra", "alpha", "middle"):
        assert (specs / "memory" / "product" / f"{slug}.md").is_file(), (
            f"{slug}.md must exist after add"
        )
