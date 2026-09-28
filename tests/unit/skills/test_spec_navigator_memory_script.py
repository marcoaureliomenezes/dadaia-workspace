"""Intent: CONTRACT — dd-spec-navigator/scripts/memory.py owns specs/memory/product/
{index.md,catalog.json} and NOTHING else: its grammar is the atoms' one grammar, the
schema is the library lint's (LINT-1), so `check` compares the generated pair against
the atoms and there is no atom generator. Size: SMALL.

The byte-reproduction case is the anti-drift one: the script regenerates THIS repo's
committed catalog.json and index.md byte for byte from the committed atoms, so a
renderer change that would rewrite the tree is red here rather than in `git status`.
"""

from __future__ import annotations

import json
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from dadaia_workspace.features.specs.memory_lint import lint_atom, load_frontmatter_schema

pytestmark = pytest.mark.unit

_REPO = Path(__file__).resolve().parents[3]
_PUBLIC = _REPO / "dadaia_workspace" / "public"
_SCRIPTS = _PUBLIC / "skills" / "dd-spec-navigator" / "scripts"


@pytest.fixture
def script(tmp_path: Path) -> Path:
    """The staged shape: the sibling modules copied beside memory.py, and the release
    skill projected beside this one (the live-release reader `drift` imports)."""
    staged = tmp_path / "skills" / "dd-spec-navigator" / "scripts"
    staged.mkdir(parents=True)
    shutil.copytree(_SCRIPTS.parents[1] / "dd-release-implementation" / "scripts",
                    tmp_path / "skills" / "dd-release-implementation" / "scripts")  # fmt: skip
    for module in sorted(_SCRIPTS.glob("*.py")):
        shutil.copy2(module, staged / module.name)
    return staged / "memory.py"


@pytest.fixture
def specs(tmp_path: Path) -> Path:
    """A copy of this repo's committed memory tree under a checkout folder NOT named after
    the repo: the catalog is a pure function of the atoms, never of the folder name."""
    tree = tmp_path / "any-checkout-name" / "specs"
    shutil.copytree(_REPO / "specs" / "memory", tree / "memory")
    return tree


def _run(script: Path, *argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *argv], capture_output=True, text=True, check=False
    )


def test_catalog_generate_byte_reproduces_the_committed_catalog_and_index(
    script: Path, specs: Path
) -> None:
    """sa-memory-atom-has-two-grammars#B29-4: regenerating this repo's committed pair in a
    checkout folder named otherwise changes not one byte — the property `git status`
    measures after the verb runs."""
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


def test_check_passes_in_a_checkout_folder_not_named_after_the_repo(
    script: Path, specs: Path
) -> None:
    """memory-catalog-context-is-the-checkout-folder-name: the committed pair checked from
    a folder named anything but the repo is in sync (exit 0), and carries no folder name."""
    result = _run(script, "check", "--specs", str(specs))

    assert result.returncode == 0, result.stdout
    assert "any-checkout-name" not in (specs / "memory" / "product" / "catalog.json").read_text(
        encoding="utf-8"
    )


def test_check_ignores_frontmatter_the_library_lint_owns(script: Path, specs: Path) -> None:
    """sa-memory-atom-has-two-grammars#B29-3: a tldr over the schema ceiling is LINT-1's
    finding over the one grammar's dict; `check` reports only the generated pair."""
    assert _run(script, "check", "--specs", str(specs)).returncode == 0

    atom = next((specs / "memory" / "product").glob("*/*.md"))
    lines = atom.read_text(encoding="utf-8").splitlines(keepends=True)
    atom.write_text(
        "".join(f"tldr: {'x' * 161}\n" if line.startswith("tldr: ") else line for line in lines),
        encoding="utf-8",
    )
    over_ceiling = _run(script, "check", "--specs", str(specs))

    assert over_ceiling.returncode == 1, "the tldr edit drifted the catalog, which check owns"
    assert "catalog.json" in over_ceiling.stdout
    assert "tldr" not in over_ceiling.stdout
    lint = lint_atom(atom, specs / "memory", load_frontmatter_schema())
    assert f"Frontmatter schema violation: '{'x' * 161}' is too long" in lint.errors


def test_check_flags_a_catalog_that_drifted_from_the_atoms(script: Path, specs: Path) -> None:
    catalog = specs / "memory" / "product" / "catalog.json"
    document = json.loads(catalog.read_text(encoding="utf-8"))
    document["features"] = document["features"][:-1]
    catalog.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result = _run(script, "check", "--specs", str(specs))

    assert result.returncode == 1
    assert "catalog.json" in result.stdout


def test_check_flags_an_index_that_drifted_from_the_atoms(script: Path, specs: Path) -> None:
    """Both halves of the generated pair are checked — index.md is not the catalog's
    shadow, it is the second file `catalog generate` writes in the same act."""
    index = specs / "memory" / "product" / "index.md"
    index.write_text(
        index.read_text(encoding="utf-8").replace("| `agent-comms` |", "| `agent-coms` |", 1),
        encoding="utf-8",
    )

    result = _run(script, "check", "--specs", str(specs))

    assert result.returncode == 1
    assert "index.md" in result.stdout


def test_a_drifted_pair_names_the_generator_as_its_fix(
    script: Path, specs: Path, tmp_path: Path
) -> None:
    """memory-catalog-context-is-the-checkout-folder-name#fix,
    sa-memory-atom-has-two-grammars#B29-5: a catalog written by an older generator (it carried `context`) is
    drift whose fix regenerates the pair by its absolute specs path, from any directory."""
    catalog = specs / "memory" / "product" / "catalog.json"
    document = {"context": "old-folder", **json.loads(catalog.read_text(encoding="utf-8"))}
    catalog.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", "utf-8")

    (finding,) = json.loads(_run(script, "check", "--specs", str(specs), "--json").stdout)

    prefix = "python3 .agents/skills/dd-spec-navigator/scripts/memory.py"
    assert finding["fix"] == f"{prefix} catalog generate --specs {specs}"
    argv = [sys.executable, str(script), *shlex.split(finding["fix"])[2:]]
    assert subprocess.run(argv, cwd=tmp_path, check=False).returncode == 0
    assert _run(script, "check", "--specs", str(specs)).returncode == 0


@pytest.mark.parametrize(
    ("line", "verdict"),
    [
        ("# owner: someone", False),
        ("tldr: >\n  folded tldr", False),
        ('tags: ["a, b", c]', False),
        ("owner: a: b", False),
        ('tags: ["a", b]', True),
    ],
)
def test_generate_check_and_lint1_reach_one_verdict_per_atom(
    script: Path, specs: Path, line: str, verdict: bool
) -> None:
    """sa-memory-atom-has-two-grammars#B29-1 sa-memory-atom-has-two-grammars#B29-2:
    `catalog generate`, `check` and
    LINT-1 parse the atom with one grammar and accept or refuse it alike; a refused
    generate names the atom and writes nothing."""
    atom = next((specs / "memory" / "product").glob("*/*.md"))
    new = line if line.startswith("tags") else f"{line}\ntags: [x]"
    text = re.sub(r"^tags: .*$", lambda _: new, atom.read_text("utf-8"), count=1, flags=re.M)
    atom.write_text(text, encoding="utf-8")
    catalog = (specs / "memory" / "product" / "catalog.json").read_bytes()

    generate = _run(script, "catalog", "generate", "--specs", str(specs))
    check = _run(script, "check", "--specs", str(specs))
    lint = lint_atom(atom, specs / "memory", load_frontmatter_schema())
    parsed = not any(e.startswith("Frontmatter is outside") for e in lint.errors)

    assert (generate.returncode == 0, check.returncode == 0, parsed) == (verdict,) * 3
    if not verdict:
        assert atom.name in generate.stdout + generate.stderr
        assert (specs / "memory" / "product" / "catalog.json").read_bytes() == catalog
