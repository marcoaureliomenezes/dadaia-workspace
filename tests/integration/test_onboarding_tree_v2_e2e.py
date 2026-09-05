"""Intent: CONTRACT — context-alive-copies-scaffold-image-bypassing-canon-fold (AC-O-1).

``dadaia context alive`` materialises a consumer repo's ``specs/`` through the ONE canon
fold — ``features.specs.canon.scaffold``, injected by the composition root — the same fold
``dadaia specs init`` runs, never by copying the ``public/scaffold/`` image. An alive-born
tree is therefore exactly the canon's ``required_at_birth`` set, carries the rendered fixed
law blocks, and passes the doctor clean at birth; a pre-existing ``specs/`` keeps every
operator file and gains only the missing canon entries, which are exactly the paths the
scaffold commit stages.

Runs the real composition root (``container.build_spec_context_service``) against a real git
repo in ``tmp_path`` — the executed path, not a fake. Size: MEDIUM (integration): the
scaffold commit needs a real ``git``.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

pytest.importorskip("fcntl")

from dadaia_workspace import container  # noqa: E402
from dadaia_workspace.core.fixed_sections import extract_fixed_section  # noqa: E402
from dadaia_workspace.features.specs import Severity, SpecsDoctor, SpecsDoctorIssue  # noqa: E402
from dadaia_workspace.features.specs.canon import CANON  # noqa: E402
from dadaia_workspace.features.specs.memory_canon import read_fixed_fragment  # noqa: E402

pytestmark = [pytest.mark.integration, pytest.mark.slow]

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_PUBLIC_DIR = _REPO_ROOT / "dadaia_workspace" / "public"
_TEMPLATES_DIR = _PUBLIC_DIR / "templates"

#: What the canon fold writes at birth — the ONE table ``alive`` must fold over.
_BORN_SET = frozenset(entry.dest for entry in CANON if entry.required_at_birth and entry.dest)


def _run(args: list[str], cwd: Path) -> str:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=True).stdout


def _workspace_with_repo(tmp_path: Path) -> tuple[Path, Path]:
    """An initialised workspace (``.dadaia/states/`` present) holding one born git repo."""
    workspace_root = tmp_path / "ws"
    states = workspace_root / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text(
        '{"schema_version": "3", "contexts": []}\n', encoding="utf-8"
    )
    repo = workspace_root / "repos" / "ctx-repo"
    repo.mkdir(parents=True)
    _run(["git", "init", "-q"], repo)
    _run(["git", "config", "user.email", "t@t"], repo)
    _run(["git", "config", "user.name", "t"], repo)
    (repo / "README.md").write_text("# ctx-repo\n", encoding="utf-8")
    _run(["git", "add", "README.md"], repo)
    _run(["git", "commit", "-q", "-m", "init"], repo)
    return workspace_root, repo


def _alive(workspace_root: Path) -> None:
    service = container.build_spec_context_service(workspace_root)
    service.create("proj", "ctx-repo", "https://example.invalid/ctx-repo.git")
    service.alive("proj")


def _head_commit_paths(repo: Path) -> set[str]:
    stat = _run(["git", "show", "--stat=200", "--format=", "HEAD"], repo)
    return {line.split("|")[0].strip() for line in stat.splitlines() if "|" in line}


def _doctor_issues(specs_dir: Path) -> list[SpecsDoctorIssue]:
    return SpecsDoctor(
        specs_dir,
        public_dir=_PUBLIC_DIR,
        templates_dir=_TEMPLATES_DIR,
        bug_store_factory=container.build_bug_record_store,
    ).check()


def test_alive_born_specs_tree_is_the_canon_fold_and_doctor_clean(tmp_path: Path) -> None:
    """Repro of the bug: ``alive`` on a repo with no ``specs/``. At the image-copy HEAD the
    born tree carried empty ``<!-- dadaia:fixed … -->`` pairs (FIXED-2 x3 until
    ``specs doctor --fix``) and lacked ``backlog/BACKLOG.json`` — the image, not the canon."""
    workspace_root, repo = _workspace_with_repo(tmp_path)
    _alive(workspace_root)
    specs_dir = repo / "specs"

    constitution = (specs_dir / "constitution.md").read_text(encoding="utf-8")
    assert extract_fixed_section(constitution, "slop-law") == read_fixed_fragment(
        _PUBLIC_DIR, "slop-law"
    ), "the slop-law block must be the library fragment, byte for byte, at birth"

    born = {p.relative_to(specs_dir).as_posix() for p in specs_dir.rglob("*") if p.is_file()}
    assert born == _BORN_SET, (
        f"alive-born tree is not the canon fold: extra={sorted(born - _BORN_SET)} "
        f"missing={sorted(_BORN_SET - born)}"
    )

    issues = _doctor_issues(specs_dir)
    fixed = [i for i in issues if i.code.startswith("FIXED-")]
    assert fixed == [], "\n".join(f"  {i.code}: {i.description}" for i in fixed)
    errors = [i for i in issues if i.severity is Severity.ERROR]
    assert errors == [], "\n".join(f"  {i.code}: {i.description}" for i in errors)

    committed = _head_commit_paths(repo)
    assert {p for p in committed if p.startswith("specs/")} == {f"specs/{d}" for d in _BORN_SET}


def test_alive_keeps_operator_specs_and_stages_only_the_missing_canon_entries(
    tmp_path: Path,
) -> None:
    """A pre-existing ``specs/`` is never overwritten: the operator's ``constitution.md``
    stays byte-identical, every other canon entry is rendered (fixed block included), and
    the scaffold commit stages exactly those added entries."""
    workspace_root, repo = _workspace_with_repo(tmp_path)
    specs_dir = repo / "specs"
    specs_dir.mkdir()
    operator_text = "# My custom constitution\n\nOperator-authored content.\n"
    (specs_dir / "constitution.md").write_text(operator_text, encoding="utf-8")
    _run(["git", "add", "specs"], repo)
    _run(["git", "commit", "-q", "-m", "operator specs"], repo)

    _alive(workspace_root)

    assert (specs_dir / "constitution.md").read_text(encoding="utf-8") == operator_text
    architecture = (specs_dir / "memory" / "ARCHITECTURE.md").read_text(encoding="utf-8")
    assert extract_fixed_section(architecture, "slop-code") == read_fixed_fragment(
        _PUBLIC_DIR, "slop-code"
    )

    added = {f"specs/{d}" for d in _BORN_SET - {"constitution.md"}}
    committed = _head_commit_paths(repo)
    assert "specs/constitution.md" not in committed
    assert {p for p in committed if p.startswith("specs/")} == added


def test_repository_own_specs_tree_has_no_tree_errors() -> None:
    """AC-O-1's second half, unchanged: this repository's real ``specs/`` tree produces 0
    TREE-* ERROR issues."""
    repo_specs = _REPO_ROOT / "specs"
    if not repo_specs.exists():
        pytest.skip("specs/ not found outside the dadaia-workspace repo context")

    issues = SpecsDoctor(
        repo_specs, public_dir=_PUBLIC_DIR, bug_store_factory=container.build_bug_record_store
    ).check()
    tree_errors = [i for i in issues if i.code.startswith("TREE-") and i.severity is Severity.ERROR]
    assert tree_errors == [], "Repository specs triggered TREE ERROR invariants:\n" + "\n".join(
        f"  {issue.code}: {issue.description}" for issue in tree_errors
    )
