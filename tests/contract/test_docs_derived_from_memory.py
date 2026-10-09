"""Behavioral contracts for documentation navigation and generated CLI reference."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from dadaia_workspace.cli.help_digest import command_paths, render_digest
from dadaia_workspace.features.specs.citations import dead_citations

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MEMORY_DIR = _REPO_ROOT / "specs" / "memory"
_DOCS_DIR = _REPO_ROOT / "docs"
#: `docs/cli.md` is generated, not derived: it names its generator, not an atom.
_GENERATED = ("cli.md",)


def _derived_docs() -> list[Path]:
    """The derived set is a glob, never a list: a new `docs/*.md` is governed at birth."""
    docs = [_REPO_ROOT / "README.md", _REPO_ROOT / "llms.txt"]
    docs.extend(p for p in sorted(_DOCS_DIR.glob("*.md")) if p.name not in _GENERATED)
    return [p for p in docs if p.is_file()]


def test_the_derived_set_covers_the_readme_the_agent_index_and_every_authored_doc() -> None:
    """The glob is the set: `README.md` and `llms.txt` are always in it, and every
    authored `docs/*.md` joins it the moment it lands — a doc cannot opt out."""
    names = {doc.relative_to(_REPO_ROOT).as_posix() for doc in _derived_docs()}

    assert {"README.md", "llms.txt"} <= names
    assert {
        "docs/index.md",
        "docs/quickstart.md",
        "docs/positioning.md",
        "docs/bug-loop.md",
        "docs/bug-ledger-lessons.md",
    } <= names, "the site's entry pages are derived documents like any other"
    assert names - {"README.md", "llms.txt"} == {
        p.relative_to(_REPO_ROOT).as_posix()
        for p in _DOCS_DIR.glob("*.md")
        if p.name not in _GENERATED
    }


_DOCS_URL = "https://github.com/marcoaureliomenezes/dadaia-workspace/tree/main/docs"


def test_the_agent_index_lists_every_page_of_the_site() -> None:
    """`llms.txt` is the agent's map of the human site: a page it does not name is a page
    no agent finds, so the list is the `docs/` glob and nothing narrower."""
    index = (_REPO_ROOT / "llms.txt").read_text("utf-8")
    missing = sorted(
        p.relative_to(_REPO_ROOT).as_posix()
        for p in _DOCS_DIR.glob("*.md")
        if p.relative_to(_REPO_ROOT).as_posix() not in index
    )

    assert missing == [], f"llms.txt names no entry for: {', '.join(missing)}"


def test_the_readme_sends_a_reader_to_the_docs_folder() -> None:
    """docs-url-dead-and-readme-links-break-on-pypi. No Pages site
    exists: the Documentation URL and the README both name the repository's docs folder."""
    readme = (_REPO_ROOT / "README.md").read_text("utf-8")

    assert _DOCS_URL in readme
    assert _pyproject_poetry()["urls"]["Documentation"] == _DOCS_URL  # type: ignore[index]
    assert "github.io" not in readme


def test_every_readme_link_is_absolute() -> None:
    """docs-url-dead-and-readme-links-break-on-pypi. PyPI renders the
    README outside the checkout, where a relative link or image target is a dead end."""
    readme = (_REPO_ROOT / "README.md").read_text("utf-8")
    targets = re.findall(r"\]\(([^)\s]+)", readme) + re.findall(r'(?:src|href)="([^"]+)"', readme)
    relative = [t for t in targets if not re.match(r"(?:https?:|mailto:|#)", t)]
    assert relative == []


def test_the_cli_reference_is_the_committed_output_of_the_generator() -> None:
    """`docs/cli.md` carries no atom marker — it IS `render_digest()`'s output, header
    line included; regenerate with `dadaia help tree > docs/cli.md`."""
    committed = (_DOCS_DIR / "cli.md").read_text("utf-8")

    assert committed == render_digest(), (
        "docs/cli.md drifted from the live command tree — "
        "regenerate: dadaia help tree > docs/cli.md"
    )


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


_CONTEXT_CREATE_RE = re.compile(r"dadaia context create [^`\n]*")


def _onboarding_texts() -> list[Path]:
    """Every surface a newcomer copies a command from: the derived docs, the memory
    atoms they derive from, and the public skills."""
    skills = sorted((_REPO_ROOT / "dadaia_workspace" / "public" / "skills").glob("*/SKILL.md"))
    return [*_derived_docs(), *sorted(_MEMORY_DIR.rglob("*.md")), *skills]


def test_no_onboarding_text_claims_offline_operation() -> None:
    """bug `onboarding-docs-contradict-the-cli`, AC2.4. `init`
    resolves its dependencies from PyPI, so no surface may call it offline."""
    violations = [
        f"{path.relative_to(_REPO_ROOT).as_posix()}:{number}: claims offline operation"
        for path in _onboarding_texts()
        for number, line in enumerate(path.read_text("utf-8").splitlines(), start=1)
        if re.search(r"\boffline\b", line, re.IGNORECASE)
    ]
    assert violations == [], "\n".join(violations)


def test_no_onboarding_text_cites_a_retired_create_flag() -> None:
    """AC3.8, bug `onboarding-docs-contradict-the-cli`. `context
    create` takes `--main-repo <url>` and repeatable `--associated-repo <url>`; a cited
    `--url` or `--associated-repos` exits 2."""
    violations = [
        f"{path.relative_to(_REPO_ROOT).as_posix()}:{number}: `{match.group(0).strip()}`"
        for path in _onboarding_texts()
        for number, line in enumerate(path.read_text("utf-8").splitlines(), start=1)
        for match in _CONTEXT_CREATE_RE.finditer(line)
        if re.search(r"--url\b|--associated-repos\b", match.group(0))
    ]
    assert violations == [], "\n".join(violations)
