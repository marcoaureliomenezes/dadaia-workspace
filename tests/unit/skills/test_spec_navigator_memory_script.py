"""Intent: CONTRACT — dd-spec-navigator/scripts/memory.py owns specs/memory/product/
{index.md,catalog.json} and the atoms' five-field frontmatter (0.4.7 c7 T-047-67: the
memory catalog renderer moves into a stdlib skill script). Size: SMALL.

The byte-reproduction case is the anti-drift one: the script regenerates THIS repo's
committed catalog.json and index.md byte for byte from the committed atoms, so a
renderer change that would rewrite the tree is red here rather than in `git status`.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_REPO = Path(__file__).resolve().parents[3]
_PUBLIC = _REPO / "dadaia_workspace" / "public"
_SCRIPTS = _PUBLIC / "skills" / "dd-spec-navigator" / "scripts"
_SCHEMAS = (_PUBLIC / "schemas" / "memory" / "memory-frontmatter-v1.schema.json",)


@pytest.fixture
def script(tmp_path: Path) -> Path:
    """The staged shape: memory.py with its schema copy beside it."""
    staged = tmp_path / "staged" / "scripts"
    (staged / "schemas").mkdir(parents=True)
    for module in sorted(_SCRIPTS.glob("*.py")):
        shutil.copy2(module, staged / module.name)
    for schema in _SCHEMAS:
        shutil.copy2(schema, staged / "schemas" / schema.name)
    return staged / "memory.py"


@pytest.fixture
def specs(tmp_path: Path) -> Path:
    """A copy of this repo's committed memory tree, under a same-named parent so the
    catalog's `context` (the specs dir's parent name) reproduces too."""
    tree = tmp_path / _REPO.name / "specs"
    shutil.copytree(_REPO / "specs" / "memory", tree / "memory")
    return tree


def _run(script: Path, *argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *argv], capture_output=True, text=True, check=False
    )


def test_catalog_generate_byte_reproduces_the_committed_catalog_and_index(
    script: Path, specs: Path
) -> None:
    """Regenerating this repo's committed pair changes not one byte — the property
    `git status` measures after the verb runs."""
    product = specs / "memory" / "product"
    committed = {
        name: (_REPO / "specs" / "memory" / "product" / name).read_bytes()
        for name in ("catalog.json", "index.md")
    }

    result = _run(script, "catalog", "generate", "--specs", str(specs))

    assert result.returncode == 0, result.stderr
    assert (product / "catalog.json").read_bytes() == committed["catalog.json"]
    assert (product / "index.md").read_bytes() == committed["index.md"]


def test_catalog_generate_rebuilds_the_committed_content_from_the_atoms_alone(
    script: Path, specs: Path
) -> None:
    """The stamp is the only field carried over: with both generated files deleted, the
    atoms alone reproduce every committed entry and every rendered row."""
    product = specs / "memory" / "product"
    committed = json.loads(
        (_REPO / "specs" / "memory" / "product" / "catalog.json").read_text("utf-8")
    )
    committed_index = (_REPO / "specs" / "memory" / "product" / "index.md").read_text("utf-8")
    (product / "catalog.json").unlink()
    (product / "index.md").unlink()

    assert _run(script, "catalog", "generate", "--specs", str(specs)).returncode == 0

    rebuilt = json.loads((product / "catalog.json").read_text("utf-8"))
    assert rebuilt["features"] == committed["features"]
    assert rebuilt["context"] == committed["context"]
    assert rebuilt["generated_at"] != committed["generated_at"]
    catalog_section = committed_index.split("## Feature catalog\n\n", 1)[1]
    assert catalog_section.rstrip("\n") in (product / "index.md").read_text("utf-8")


def test_catalog_generate_preserves_non_catalog_sections_verbatim(
    script: Path, specs: Path
) -> None:
    index = specs / "memory" / "product" / "index.md"
    index.write_text(
        index.read_text(encoding="utf-8") + "\n## Operator notes\n\nkept verbatim.\n",
        encoding="utf-8",
    )

    assert _run(script, "catalog", "generate", "--specs", str(specs)).returncode == 0
    assert index.read_text(encoding="utf-8").endswith("## Operator notes\n\nkept verbatim.\n")


def test_product_add_writes_an_atom_that_check_accepts(script: Path, specs: Path) -> None:
    result = _run(
        script, "product", "add", "platform", "widget-forge",
        "--title", "widget-forge", "--tldr", "Forges widgets from the one registry.",
        "--summary", "The widget forge reads the registry and emits one widget per row.",
        "--tags", "platform,widgets", "--specs", str(specs),
    )  # fmt: skip

    assert result.returncode == 0, result.stderr
    atom = specs / "memory" / "product" / "platform" / "widget-forge.md"
    assert atom.is_file()
    assert _run(script, "catalog", "generate", "--specs", str(specs)).returncode == 0
    assert _run(script, "check", "--specs", str(specs)).returncode == 0
    slugs = [
        feature["slug"]
        for feature in json.loads(
            (specs / "memory" / "product" / "catalog.json").read_text("utf-8")
        )["features"]
    ]
    assert "widget-forge" in slugs


def test_check_flags_a_tldr_over_the_schema_ceiling(script: Path, specs: Path) -> None:
    assert _run(script, "check", "--specs", str(specs)).returncode == 0

    atom = next((specs / "memory" / "product").glob("*/*.md"))
    lines = atom.read_text(encoding="utf-8").splitlines(keepends=True)
    atom.write_text(
        "".join(f"tldr: {'x' * 161}\n" if line.startswith("tldr: ") else line for line in lines),
        encoding="utf-8",
    )
    broken = _run(script, "check", "--specs", str(specs))

    assert broken.returncode == 1
    assert "LEDGER-MEMORY-SCHEMA" in broken.stdout
    assert "tldr" in broken.stdout


def test_check_flags_a_catalog_that_drifted_from_the_atoms(script: Path, specs: Path) -> None:
    catalog = specs / "memory" / "product" / "catalog.json"
    document = json.loads(catalog.read_text(encoding="utf-8"))
    document["features"] = document["features"][:-1]
    catalog.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result = _run(script, "check", "--specs", str(specs))

    assert result.returncode == 1
    assert "catalog.json" in result.stdout
