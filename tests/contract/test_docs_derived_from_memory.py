"""Every human- and agent-facing document derives from a named memory atom.

Intent: CONTRACT — T-047-36 (SPEC 0.4.7 FR3): `README.md`, `llms.txt` and every
`docs/*.md` carry, under each `## ` heading, one or more
`<!-- derived-from: <slug> sha256:<12 hex> -->` markers; the slug resolves by stem to
exactly one file under `specs/memory/`, the hash is that file's CURRENT content hash,
and `docs/cli.md` is the committed output of `dadaia help tree`.
Size: SMALL — reads this repo's own tree plus in-memory mutation fixtures; no
subprocess, no network, no tmp workspace.

One changed atom byte reddens every section derived from it, and the failure names the
atom to re-read and the line to re-record — the `behavior-map.json` pattern, applied to
prose. There is no generator verb: a derived section is re-derived by a reader, and
this test is what makes forgetting impossible.
"""

from __future__ import annotations

import hashlib
import re
import tomllib
from pathlib import Path

import pytest

from dadaia_workspace.cli.help_digest import command_paths, render_digest
from dadaia_workspace.features.specs.citations import dead_citations

pytestmark = pytest.mark.contract

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MEMORY_DIR = _REPO_ROOT / "specs" / "memory"
_DOCS_DIR = _REPO_ROOT / "docs"
_README_MAX_BYTES = 10_240
#: `docs/cli.md` is generated, not derived: it names its generator, not an atom.
_GENERATED = ("cli.md",)

_H2_RE = re.compile(r"^## (.+)$")
_MARKER_RE = re.compile(r"^<!-- derived-from: ([A-Za-z0-9._-]+) sha256:([0-9a-f]{12}) -->$")
_HASH_CHARS = 12


def _atom_hash(path: Path) -> str:
    """The atom's content hash — over LF bytes, so a CRLF checkout (Windows autocrlf)
    pins the same twelve characters as the LF checkout that recorded them."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()[:_HASH_CHARS]


def _atoms() -> dict[str, Path]:
    """Every memory file addressable by stem — the 22 product atoms plus the trio."""
    by_slug: dict[str, Path] = {}
    for path in sorted(_MEMORY_DIR.rglob("*.md")):
        if path.name == "AGENTS.md":
            continue
        by_slug.setdefault(path.stem, path)
    return by_slug


def _derived_docs() -> list[Path]:
    """The derived set is a glob, never a list: a new `docs/*.md` is governed at birth."""
    docs = [_REPO_ROOT / "README.md", _REPO_ROOT / "llms.txt"]
    docs.extend(p for p in sorted(_DOCS_DIR.glob("*.md")) if p.name not in _GENERATED)
    return [p for p in docs if p.is_file()]


def _sections(text: str) -> list[tuple[str, list[tuple[str, str]]]]:
    """Each `## ` heading with the markers that immediately follow it (blank lines
    tolerated, so a section may be introduced by one marker per atom it derives from)."""
    lines = text.splitlines()
    out: list[tuple[str, list[tuple[str, str]]]] = []
    for index, line in enumerate(lines):
        heading = _H2_RE.match(line)
        if heading is None:
            continue
        markers: list[tuple[str, str]] = []
        for follower in lines[index + 1 :]:
            stripped = follower.strip()
            if not stripped:
                continue
            marker = _MARKER_RE.match(stripped)
            if marker is None:
                break
            markers.append((marker.group(1), marker.group(2)))
        out.append((heading.group(1).strip(), markers))
    return out


def _violations(rel: str, text: str, atoms: dict[str, Path]) -> list[str]:
    """The one checker the repo tree and the mutation fixtures share."""
    found: list[str] = []
    for heading, markers in _sections(text):
        where = f"{rel}#{heading}"
        if not markers:
            found.append(
                f"{where}: no derived-from marker — name the atom this section derives from"
            )
            continue
        for slug, recorded in markers:
            if slug == "none":
                found.append(
                    f"{where}: derived-from none — a section that can name no atom is slop"
                )
                continue
            atom = atoms.get(slug)
            if atom is None:
                found.append(f"{where}: derived-from {slug} unknown — no specs/memory/**/{slug}.md")
                continue
            current = _atom_hash(atom)
            if current != recorded:
                found.append(
                    f"{where}: derived-from {slug} stale — re-read "
                    f"{atom.relative_to(_REPO_ROOT).as_posix()}, re-derive the section, "
                    f"re-record sha256:{current}"
                )
    return found


def test_every_derived_section_names_a_current_atom() -> None:
    """The repo's own derived set: every `## ` heading names an atom that exists and
    whose bytes are the ones the section was written from."""
    atoms = _atoms()
    violations = [
        v
        for doc in _derived_docs()
        for v in _violations(doc.relative_to(_REPO_ROOT).as_posix(), doc.read_text("utf-8"), atoms)
    ]

    assert violations == [], "\n".join(violations)


def test_the_derived_set_covers_the_readme_the_agent_index_and_every_authored_doc() -> None:
    """The glob is the set: `README.md` and `llms.txt` are always in it, and every
    authored `docs/*.md` joins it the moment it lands — a doc cannot opt out."""
    names = {doc.relative_to(_REPO_ROOT).as_posix() for doc in _derived_docs()}

    assert {"README.md", "llms.txt"} <= names
    assert names - {"README.md", "llms.txt"} == {
        p.relative_to(_REPO_ROOT).as_posix()
        for p in _DOCS_DIR.glob("*.md")
        if p.name not in _GENERATED
    }


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ("missing", "no derived-from marker"),
        ("unknown", "unknown"),
        ("stale", "stale"),
        ("none", "derived-from none"),
    ],
)
def test_each_red_direction_is_proven_on_a_fixture(mutation: str, expected: str) -> None:
    """Four mutants, four reds: a section with no marker, a slug memory does not carry,
    a hash one byte behind the atom, and the explicit `none` escape hatch."""
    atoms = _atoms()
    slug, atom = next(iter(sorted(atoms.items())))
    body = {
        "missing": "## A section\n\nprose\n",
        "unknown": "## A section\n\n<!-- derived-from: not-an-atom sha256:000000000000 -->\n",
        "stale": f"## A section\n\n<!-- derived-from: {slug} sha256:000000000000 -->\n",
        "none": "## A section\n\n<!-- derived-from: none sha256:000000000000 -->\n",
    }[mutation]

    violations = _violations("FIXTURE.md", body, atoms)

    assert len(violations) == 1, violations
    assert expected in violations[0]
    if mutation == "stale":
        assert atom.relative_to(_REPO_ROOT).as_posix() in violations[0]
        assert f"sha256:{_atom_hash(atom)}" in violations[0]


def test_a_current_marker_is_green_on_a_fixture() -> None:
    """The other direction: the checker passes exactly when the recorded hash is the
    atom's own — otherwise every red above would be vacuous."""
    atoms = _atoms()
    slug, atom = next(iter(sorted(atoms.items())))
    body = f"## A section\n\n<!-- derived-from: {slug} sha256:{_atom_hash(atom)} -->\n\nprose\n"

    assert _violations("FIXTURE.md", body, atoms) == []


def test_the_cli_reference_is_the_committed_output_of_the_generator() -> None:
    """`docs/cli.md` carries no atom marker — it IS `render_digest()`'s output, header
    line included; regenerate with `dadaia help tree > docs/cli.md`."""
    committed = (_DOCS_DIR / "cli.md").read_text("utf-8")

    assert committed == render_digest(), (
        "docs/cli.md drifted from the live command tree — "
        "regenerate: dadaia help tree > docs/cli.md"
    )


def test_the_readme_fits_the_long_description_budget() -> None:
    """The README is PyPI's long description, read by humans and pulled whole into agent
    context: 10 KB is the budget, and a section that cannot earn its bytes is deleted."""
    size = (_REPO_ROOT / "README.md").stat().st_size

    assert size <= _README_MAX_BYTES, f"README.md is {size} bytes (max {_README_MAX_BYTES})"


def test_no_derived_document_cites_a_dead_verb_or_path() -> None:
    """The same finders that keep `public/**` and `specs/memory/**` honest: a backticked
    `dadaia <verb>` absent from the live command tree, or a `specs/`/`dadaia_workspace/`/
    `.github/` path absent from the checkout, is dead the day it is written."""
    paths = command_paths()
    violations = [
        v
        for doc in [*_derived_docs(), _DOCS_DIR / "cli.md"]
        if doc.is_file()
        for v in dead_citations(
            doc.read_text("utf-8"),
            command_paths=paths,
            repo_root=_REPO_ROOT,
            rel=doc.relative_to(_REPO_ROOT).as_posix(),
        )
    ]

    assert violations == [], "\n".join(violations)


def _readme_tagline() -> str:
    """The README's first non-badge paragraph — PyPI's summary line, in prose."""
    for block in (_REPO_ROOT / "README.md").read_text("utf-8").split("\n\n"):
        line = block.strip()
        if not line or line.startswith(("#", "[![", "<!--")):
            continue
        return " ".join(line.split())
    raise AssertionError("README.md carries no prose paragraph")


def _llms_tagline() -> str:
    for line in (_REPO_ROOT / "llms.txt").read_text("utf-8").splitlines():
        if line.startswith("> "):
            return " ".join(line[2:].split())
    raise AssertionError("llms.txt carries no `> ` tagline line")


def _pyproject_poetry() -> dict[str, object]:
    with (_REPO_ROOT / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)["tool"]["poetry"]  # type: ignore[index,no-any-return]


def test_one_tagline_across_the_readme_pyproject_and_the_agent_index() -> None:
    """The three discovery surfaces say one thing: PyPI's `description`, the README's
    first paragraph and `llms.txt`'s `> ` line are the same sentence (SPEC 0.4.7 FR4)."""
    readme = _readme_tagline()

    assert _pyproject_poetry()["description"] == readme
    assert _llms_tagline() == readme


def test_every_pypi_link_a_reader_needs_is_declared() -> None:
    """`[tool.poetry.urls]` is what PyPI renders beside the long description: the five
    keys are the project page, the source, the docs entry point, the changelog and the
    issue tracker — a missing one is a dead end on the package page."""
    urls = _pyproject_poetry()["urls"]

    assert isinstance(urls, dict)
    assert sorted(urls) == ["Changelog", "Documentation", "Homepage", "Issues", "Repository"]
    assert all(str(value).startswith("https://") for value in urls.values())
