"""dd-spec-navigator/scripts/memory.py owns specs/memory/product/
{index.md,catalog.json} and NOTHING else: its grammar is the atoms' one grammar, the
schema is the library lint's (LINT-1), so `check` compares the catalog against
the atoms and there is no atom generator. Size: SMALL.

The byte-reproduction case is the anti-drift one: the script regenerates THIS repo's
committed catalog.json and index.md byte for byte from the committed atoms, so a
renderer change that would rewrite the tree is red here rather than in `git status`.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from dadaia_workspace.features.specs.memory_lint import lint_atom, load_frontmatter_schema
from tests.fixtures.harness_env import git_bash
from tests.helpers.oslib import read_text, run, spell, write_text
from tests.helpers.skill_scripts import stage_skill_scripts

_REPO = Path(__file__).resolve().parents[5]
_PUBLIC = _REPO / "dadaia_workspace" / "public"
_SCRIPTS = _PUBLIC / "skills" / "dd-spec-navigator" / "scripts"


@pytest.fixture
def script(tmp_path: Path) -> Path:
    """The staged shape: the sibling modules copied beside memory.py, and the release
    skill projected beside this one (the live-release reader `drift` imports)."""
    shutil.copytree(_SCRIPTS.parents[1] / "dd-release-implementation" / "scripts",
                    tmp_path / "skills" / "dd-release-implementation" / "scripts")  # fmt: skip
    staged = tmp_path / "skills" / "dd-spec-navigator" / "scripts"
    return stage_skill_scripts("dd-spec-navigator", staged) / "memory.py"


@pytest.fixture
def specs(tmp_path: Path) -> Path:
    """A copy of this repo's committed memory tree under a checkout folder NOT named after
    the repo: the catalog is a pure function of the atoms, never of the folder name."""
    tree = tmp_path / "any-checkout-name" / "specs"
    shutil.copytree(_REPO / "specs" / "memory", tree / "memory")
    return tree


def _run(script: Path, *argv: str) -> subprocess.CompletedProcess[str]:
    return run([sys.executable, str(script), *argv], check=False)


def test_catalog_generate_byte_reproduces_the_committed_catalog_and_index(
    script: Path, specs: Path
) -> None:
    """Regenerating this repo's committed pair in a
    checkout folder named otherwise changes not one byte — the property `git status`
    measures after the verb runs."""
    product = specs / "memory" / "product"
    committed = {
        name: read_text(_REPO / "specs" / "memory" / "product" / name).encode("utf-8")
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
    committed = json.loads(read_text(_REPO / "specs" / "memory" / "product" / "catalog.json"))
    committed_index = read_text(_REPO / "specs" / "memory" / "product" / "index.md")
    (product / "catalog.json").unlink()
    (product / "index.md").unlink()

    assert _run(script, "catalog", "generate", "--specs", str(specs)).returncode == 0

    rebuilt = json.loads(read_text(product / "catalog.json"))
    assert rebuilt["features"] == committed["features"]
    assert rebuilt["generated_at"] != committed["generated_at"]
    catalog_section = committed_index.split("## Feature catalog\n\n", 1)[1]
    assert catalog_section.rstrip("\n") in read_text(product / "index.md")


def test_catalog_generate_preserves_non_catalog_sections_verbatim(
    script: Path, specs: Path
) -> None:
    index = specs / "memory" / "product" / "index.md"
    write_text(index, read_text(index) + "\n## Operator notes\n\nkept verbatim.\n")

    assert _run(script, "catalog", "generate", "--specs", str(specs)).returncode == 0
    assert read_text(index).endswith("## Operator notes\n\nkept verbatim.\n")


@pytest.mark.parametrize(
    ("authored", "kept_before", "kept_after"),
    [
        ("# Mine\n\n## Authored\n\nkeep me.\n", "# Mine\n\n## Authored\n\nkeep me.\n\n", ""),
        (
            "# Mine\n\n## Feature catalog (generated)\n\nhand text.\n",
            "# Mine\n\n## Feature catalog (generated)\n\nhand text.\n\n",
            "",
        ),
        (
            "# Mine\n\n### Feature catalog\n\nsub.\n",
            "# Mine\n\n### Feature catalog\n\nsub.\n\n",
            "",
        ),
        (
            "# Mine\n\n## Feature catalog\n\nSTALE row\n\n## Notes\n\nafter.\n",
            "# Mine\n\n## Feature catalog\n\n",
            "\n\n## Notes\n\nafter.\n",
        ),
        (
            "# Mine\n\n\n## Feature catalog\n\nSTALE row\n\n## Notes\n\nafter.\n",
            "# Mine\n\n\n## Feature catalog\n\n",
            "\n\n## Notes\n\nafter.\n",
        ),
        ("\n# Mine\n\n## Feature catalog\n\nSTALE row\n", "\n# Mine\n\n## Feature catalog\n\n", ""),
        (
            "# Mine\n\n## Authored\n\nkeep.\n\n\n",
            "# Mine\n\n## Authored\n\nkeep.\n\n## Feature catalog\n\n### ",
            "",
        ),
    ],
    ids=[
        "no-heading",
        "longer-heading-line",
        "deeper-heading",
        "exact-heading",
        "two-blank-lines-before-exact",
        "leading-blank-line",
        "append-after-trailing-blanks",
    ],
)
def test_catalog_generate_keeps_every_authored_line_and_owns_one_exact_section(
    script: Path, specs: Path, authored: str, kept_before: str, kept_after: str
) -> None:
    index = specs / "memory" / "product" / "index.md"
    write_text(index, authored)

    assert _run(script, "catalog", "generate", "--specs", str(specs)).returncode == 0
    text = read_text(index)
    assert text.startswith(kept_before) and text.endswith(kept_after or "|\n")
    assert text.count("\n## Feature catalog\n\n### ") == 1
    assert "STALE" not in text
    assert _run(script, "check", "--specs", str(specs)).returncode == 0


def test_catalog_generate_writes_the_template_for_a_missing_index(
    script: Path, specs: Path
) -> None:
    index = specs / "memory" / "product" / "index.md"
    index.unlink()

    assert _run(script, "catalog", "generate", "--specs", str(specs)).returncode == 0
    assert read_text(index).startswith("# Memory Catalog\n\n> Generated automatically")


def test_check_passes_in_a_checkout_folder_not_named_after_the_repo(
    script: Path, specs: Path
) -> None:
    """The committed pair checked from
    a folder named anything but the repo is in sync (exit 0), and carries no folder name."""
    result = _run(script, "check", "--specs", str(specs))

    assert result.returncode == 0, result.stdout
    assert "any-checkout-name" not in read_text(specs / "memory" / "product" / "catalog.json")


def test_check_ignores_frontmatter_the_library_lint_owns(script: Path, specs: Path) -> None:
    """A tldr over the schema ceiling is LINT-1's
    finding over the one grammar's dict; `check` reports only the catalog."""
    assert _run(script, "check", "--specs", str(specs)).returncode == 0

    atom = next((specs / "memory" / "product").glob("*/*.md"))
    lines = read_text(atom).splitlines(keepends=True)
    write_text(
        atom,
        "".join(f"tldr: {'x' * 161}\n" if line.startswith("tldr: ") else line for line in lines),
    )
    over_ceiling = _run(script, "check", "--specs", str(specs))

    assert over_ceiling.returncode == 1, "the tldr edit drifted the catalog, which check owns"
    assert "catalog.json" in over_ceiling.stdout
    assert "tldr" not in over_ceiling.stdout
    lint = lint_atom(atom, specs / "memory", load_frontmatter_schema())
    assert f"Frontmatter schema violation: '{'x' * 161}' is too long" in lint.errors


def test_check_flags_a_catalog_that_drifted_from_the_atoms(script: Path, specs: Path) -> None:
    catalog = specs / "memory" / "product" / "catalog.json"
    document = json.loads(read_text(catalog))
    document["features"] = document["features"][:-1]
    write_text(catalog, json.dumps(document, ensure_ascii=False, indent=2) + "\n")

    result = _run(script, "check", "--specs", str(specs))

    assert result.returncode == 1
    assert "the catalog in catalog.json does not match the atoms" in result.stdout


def test_check_flags_an_index_that_drifted_from_the_atoms(script: Path, specs: Path) -> None:
    """The index's `## Feature catalog` is checked beside catalog.json."""
    index = specs / "memory" / "product" / "index.md"
    write_text(index, read_text(index).replace("| `agent-comms` |", "| `agent-coms` |", 1))

    result = _run(script, "check", "--specs", str(specs))

    assert result.returncode == 1
    assert "the catalog in index.md does not match the atoms" in result.stdout


def test_a_drifted_pair_names_the_generator_as_its_fix(
    script: Path, specs: Path, tmp_path: Path
) -> None:
    """A catalog written by an older generator (it carried `context`) is
    drift whose fix regenerates the pair by its absolute specs path, from any directory."""
    catalog = specs / "memory" / "product" / "catalog.json"
    document = {"context": "old-folder", **json.loads(read_text(catalog))}
    write_text(catalog, json.dumps(document, ensure_ascii=False, indent=2) + "\n")

    (finding,) = json.loads(_run(script, "check", "--specs", str(specs), "--json").stdout)

    assert run([git_bash(), "-c", finding["fix"]], cwd=tmp_path).returncode == 0
    assert _run(script, "check", "--specs", str(specs)).returncode == 0


def test_a_specs_tree_without_product_names_the_cross_shell_mkdir_by_absolute_path(
    script: Path, tmp_path: Path
) -> None:
    """Both the generator's refusal and `check`'s finding carry the interpreter mkdir act with the
    absolute product folder, and running that line creates it."""
    bare = tmp_path / "bare" / "specs"
    (bare / "memory").mkdir(parents=True)
    product = bare / "memory" / "product"

    refusal = _run(script, "catalog", "generate", "--specs", str(bare))
    (finding,) = json.loads(_run(script, "check", "--specs", str(bare), "--json").stdout)

    assert refusal.returncode == 1
    for fix in (finding["fix"], refusal.stderr.split("fix: ", 1)[1].strip()):
        assert fix.endswith(f" {spell(str(product))}")
        assert not fix.startswith(("mkdir", "Agent action"))
        assert run([git_bash(), "-c", fix], cwd=tmp_path).returncode == 0
        assert product.is_dir()
        product.rmdir()


@pytest.mark.parametrize(
    ("line", "verdict"),
    [
        ("# owner: someone", False),
        ("tldr: >\n  folded tldr", False),
        ('tags: ["a, b", c]', True),
        ("owner: a: b", False),
        ('tags: ["a", b]', True),
    ],
)
def test_generate_check_and_lint1_reach_one_verdict_per_atom(
    script: Path, specs: Path, line: str, verdict: bool
) -> None:
    """`catalog generate`, `check` and
    LINT-1 parse the atom with one grammar and accept or refuse it alike; a refused
    generate names the atom and writes nothing."""
    atom = next((specs / "memory" / "product").glob("*/*.md"))
    new = line if line.startswith("tags") else f"{line}\ntags: [x]"
    text = re.sub(r"^tags: .*$", lambda _: new, read_text(atom), count=1, flags=re.M)
    write_text(atom, text)
    catalog = (specs / "memory" / "product" / "catalog.json").read_bytes()

    generate = _run(script, "catalog", "generate", "--specs", str(specs))
    check = _run(script, "check", "--specs", str(specs))
    lint = lint_atom(atom, specs / "memory", load_frontmatter_schema())
    parsed = not any(e.startswith("Frontmatter is outside") for e in lint.errors)

    assert (generate.returncode == 0, check.returncode == 0, parsed) == (verdict,) * 3
    if not verdict:
        assert atom.name in generate.stdout + generate.stderr
        assert (specs / "memory" / "product" / "catalog.json").read_bytes() == catalog


def test_every_committed_atom_parses_to_the_dict_safe_load_reads() -> None:
    """The atoms' grammar is the kernel owner; the committed tree parses to what
    `yaml.safe_load` reads from each block."""
    import yaml

    from dadaia_workspace.core.skill_owner import load_owner

    parse = load_owner("dd-spec-navigator", "_memory_schema").parse
    atoms = sorted((_REPO / "specs" / "memory" / "product").glob("*/*.md"))
    assert len(atoms) >= 29
    for atom in atoms:
        text = read_text(atom)
        data, _body, error = parse(text)
        assert error is None, atom.name
        assert data == yaml.safe_load(text.split("\n---\n", 1)[0].removeprefix("---\n")), atom.name
