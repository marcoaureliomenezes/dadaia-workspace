"""T-048-05 review finding 3 (CWE-59/CWE-367); ports v0.4.3 A17.1/A17.2,
v0.7.0 FR3 and 0.4.6 AC7 from the deleted ``scoped_law`` tests onto the one write path
``canon._write_absent`` behind ``scaffold_repo_law``. Size: SMALL (tmp filesystem only)."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from dadaia_workspace.features.specs import canon

pytest.importorskip("fcntl")  # POSIX symlink + O_NOFOLLOW semantics

_BODIES = {"repo-AGENTS.md": "# repo law\n"}


@pytest.fixture
def public(tmp_path: Path) -> Path:
    templates = tmp_path / "public" / "templates"
    templates.mkdir(parents=True)
    for name, body in _BODIES.items():
        (templates / name).write_text(body, encoding="utf-8")
    return tmp_path / "public"


def test_installs_the_absent_repo_law(tmp_path: Path, public: Path) -> None:
    """sa-public-install-writes-the-root-map-into-product-repos#K5."""
    repo = tmp_path / "repo"
    repo.mkdir()
    written = canon.scaffold_repo_law(repo, project_name="p", public_dir=public)
    assert written == [repo / "AGENTS.md"]
    assert (repo / "AGENTS.md").read_text(encoding="utf-8") == "# repo law\n"


def test_present_law_is_never_overwritten(tmp_path: Path, public: Path) -> None:
    """sa-public-install-writes-the-root-map-into-product-repos#K5."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "AGENTS.md").write_text("mine\n", encoding="utf-8")
    assert canon.scaffold_repo_law(repo, project_name="p", public_dir=public) == []
    assert (repo / "AGENTS.md").read_text(encoding="utf-8") == "mine\n"


def test_symlinked_repo_root_is_never_written_through(tmp_path: Path, public: Path) -> None:
    """sa-public-install-writes-the-root-map-into-product-repos#K5."""
    outside = tmp_path / "outside-repo"
    outside.mkdir()
    repo = tmp_path / "repo"
    repo.symlink_to(outside, target_is_directory=True)
    assert canon.scaffold_repo_law(repo, project_name="p", public_dir=public) == []
    assert list(outside.iterdir()) == []


@pytest.mark.parametrize("dangling", [True, False])
def test_symlinked_destination_is_never_written_through(
    tmp_path: Path, public: Path, dangling: bool
) -> None:
    """sa-public-install-writes-the-root-map-into-product-repos#K5."""
    repo = tmp_path / "repo"
    repo.mkdir()
    target = tmp_path / "elsewhere.md"
    if not dangling:
        target.write_text("real\n", encoding="utf-8")
    (repo / "AGENTS.md").symlink_to(target)
    assert canon.scaffold_repo_law(repo, project_name="p", public_dir=public) == []
    assert (repo / "AGENTS.md").is_symlink()
    assert (target.read_text(encoding="utf-8") if target.exists() else None) == (
        None if dangling else "real\n"
    )


def test_scaffold_never_writes_through_a_symlinked_parent_dir(tmp_path: Path) -> None:
    """sa-public-install-writes-the-root-map-into-product-repos#K5."""
    outside = tmp_path / "outside-memory"
    outside.mkdir()
    specs = tmp_path / "specs"
    specs.mkdir()
    (specs / "memory").symlink_to(outside, target_is_directory=True)
    canon.scaffold(specs)
    assert list(outside.iterdir()) == []


def test_an_unwritable_directory_raises_instead_of_skipping(tmp_path: Path, public: Path) -> None:
    """sa-public-install-writes-the-root-map-into-product-repos#K5: Review N2: only an existing file or a symlinked target is skipped."""
    if os.geteuid() == 0:
        pytest.skip("root ignores directory permissions")
    repo = tmp_path / "repo"
    repo.mkdir()
    repo.chmod(0o555)
    try:
        with pytest.raises(PermissionError):
            canon.scaffold_repo_law(repo, project_name="p", public_dir=public)
    finally:
        repo.chmod(0o755)


def test_repo_law_heading_carries_the_project_name(tmp_path: Path, public: Path) -> None:
    """sa-public-install-writes-the-root-map-into-product-repos#K1: Bug scaffold-repo-agents-keeps-repo-name-placeholder: the template's
    ``<repo-name>`` is filled at scaffold time, never left for a doctor to flag."""
    (public / "templates" / "repo-AGENTS.md").write_text(
        "# <repo-name> — Repo Rules\n", encoding="utf-8"
    )
    repo = tmp_path / "repo"
    repo.mkdir()

    canon.scaffold_repo_law(repo, project_name="acme", public_dir=public)

    assert (repo / "AGENTS.md").read_text(encoding="utf-8") == "# acme — Repo Rules\n"


_TESTS_LINE = "tests: tests/** src/**/test_*.py"


def _declare(repo: Path, public: Path) -> list[Path]:
    declare = getattr(canon, "declare_tests_line", None)
    assert callable(declare), "canon.declare_tests_line is the one declaring function"
    return declare(repo, public_dir=public)


@pytest.fixture
def declaring_public(public: Path) -> Path:
    (public / "templates" / "repo-AGENTS.md").write_text(
        f"# repo law\n\n{_TESTS_LINE}\n", encoding="utf-8"
    )
    return public


def test_a_law_without_a_tests_line_gains_the_templates_line_appended(
    tmp_path: Path, declaring_public: Path
) -> None:
    """onboarding-writes-no-tests-line: ADR 0216 — onboarding declares the freeze."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "AGENTS.md").write_text("# mine\nverify: make test\n", encoding="utf-8")

    assert _declare(repo, declaring_public) == [repo / "AGENTS.md"]

    text = (repo / "AGENTS.md").read_text(encoding="utf-8")
    assert text.startswith("# mine\nverify: make test\n")
    assert text.splitlines()[-1] == _TESTS_LINE


@pytest.mark.parametrize("line", ["tests:", "tests: custom/**"])
def test_a_present_tests_line_is_left_alone(
    tmp_path: Path, declaring_public: Path, line: str
) -> None:
    """onboarding-writes-no-tests-line: an operator's line, empty or not, is never rewritten."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "AGENTS.md").write_text(f"# mine\n\n{line}\n", encoding="utf-8")

    assert _declare(repo, declaring_public) == []
    assert (repo / "AGENTS.md").read_text(encoding="utf-8") == f"# mine\n\n{line}\n"


def test_the_shipped_template_declares_a_non_empty_tests_line() -> None:
    """onboarding-writes-no-tests-line: the one default lives in the shipped template."""
    template = canon.default_public_dir() / "templates" / "repo-AGENTS.md"
    values = [
        ln.removeprefix("tests:").strip()
        for ln in template.read_text(encoding="utf-8").splitlines()
        if ln.startswith("tests:")
    ]
    assert len(values) == 1
    assert values[0] != ""


def test_an_absent_law_gets_nothing_from_the_declaration(
    tmp_path: Path, declaring_public: Path
) -> None:
    """onboarding-writes-no-tests-line: scaffold_repo_law installs the template; declaring adds no file."""
    repo = tmp_path / "repo"
    repo.mkdir()

    assert _declare(repo, declaring_public) == []
    assert list(repo.iterdir()) == []


def test_a_symlinked_law_is_never_declared_through(tmp_path: Path, declaring_public: Path) -> None:
    """onboarding-writes-no-tests-line: CWE-59 — the append never follows a symlink."""
    repo = tmp_path / "repo"
    repo.mkdir()
    target = tmp_path / "elsewhere.md"
    target.write_text("real\n", encoding="utf-8")
    (repo / "AGENTS.md").symlink_to(target)

    assert _declare(repo, declaring_public) == []
    assert target.read_text(encoding="utf-8") == "real\n"


@pytest.mark.parametrize(
    ("before", "after"),
    [
        ("# a\r\nb\r\n", f"# a\r\nb\r\n{_TESTS_LINE}\r\n"),
        ("# a\nb", f"# a\nb\n{_TESTS_LINE}\n"),
        ("# a\r\nb", f"# a\r\nb\r\n{_TESTS_LINE}\r\n"),
        ("", f"{_TESTS_LINE}\n"),
    ],
)
def test_the_declared_line_keeps_the_laws_own_newline_style(
    tmp_path: Path, declaring_public: Path, before: str, after: str
) -> None:
    """onboarding-writes-no-tests-line: CRLF, no final newline and an empty law each get a well-formed line."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "AGENTS.md").write_bytes(before.encode())

    assert _declare(repo, declaring_public) == [repo / "AGENTS.md"]
    assert (repo / "AGENTS.md").read_bytes() == after.encode()


def test_a_law_that_is_not_utf8_gains_the_line_with_its_bytes_kept(
    tmp_path: Path, declaring_public: Path
) -> None:
    """onboarding-writes-no-tests-line: a Latin-1 law is appended to as bytes, never decoded."""
    repo = tmp_path / "repo"
    repo.mkdir()
    before = "# caf\xe9\n".encode("latin-1")
    (repo / "AGENTS.md").write_bytes(before)

    assert _declare(repo, declaring_public) == [repo / "AGENTS.md"]
    assert (repo / "AGENTS.md").read_bytes() == before + f"{_TESTS_LINE}\n".encode()


def test_a_tests_line_after_a_utf8_bom_is_left_alone(
    tmp_path: Path, declaring_public: Path
) -> None:
    """onboarding-writes-no-tests-line: the BOM does not hide a declared first line."""
    repo = tmp_path / "repo"
    repo.mkdir()
    law = b"\xef\xbb\xbftests: custom/**\n# mine\n"
    (repo / "AGENTS.md").write_bytes(law)

    assert _declare(repo, declaring_public) == []
    assert (repo / "AGENTS.md").read_bytes() == law


def test_an_unreadable_law_is_skipped_not_raised(tmp_path: Path, declaring_public: Path) -> None:
    """onboarding-writes-no-tests-line: a law the user cannot read is left as found."""
    if os.geteuid() == 0:
        pytest.skip("root reads any file")
    repo = tmp_path / "repo"
    repo.mkdir()
    law = repo / "AGENTS.md"
    law.write_text("# mine\n", encoding="utf-8")
    law.chmod(0)
    try:
        assert _declare(repo, declaring_public) == []
    finally:
        law.chmod(0o644)
    assert law.read_text(encoding="utf-8") == "# mine\n"


def test_the_shipped_default_freezes_the_common_test_layouts(tmp_path: Path) -> None:
    """onboarding-writes-no-tests-line: judged as the freeze judges, by git's `:(glob)` pathspec."""
    template = canon.default_public_dir() / "templates" / "repo-AGENTS.md"
    globs = next(
        (
            ln.removeprefix("tests:").split()
            for ln in template.read_text(encoding="utf-8").splitlines()
            if ln.startswith("tests:")
        ),
        [],
    )
    assert globs, "the template declares no tests: globs"  # an empty pathspec would list every file
    paths = [
        "src/test/java/a/FooTest.java",
        "spec/foo_spec.rb",
        "web/__tests__/a.js",
        "pkg/tests/conftest.py",
    ]
    for rel in paths:
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text("x\n", encoding="utf-8")
    run = lambda *a: subprocess.run(  # noqa: E731
        ["git", "-c", "user.name=t", "-c", "user.email=t@t.invalid", *a],
        cwd=tmp_path, check=True, capture_output=True, text=True,
    ).stdout  # fmt: skip
    run("init", "-q")
    run("add", ".")
    run("commit", "-q", "-m", "x")

    listed = run("ls-files", "--", *(f":(glob){g}" for g in globs)).split()

    assert sorted(listed) == sorted(paths)


def test_the_shipped_default_freezes_no_source_that_merely_ends_in_test(tmp_path: Path) -> None:
    """default-tests-globs-over-match-source: `ABTest.tsx` and `LoadTest.md` are source and docs."""
    template = canon.default_public_dir() / "templates" / "repo-AGENTS.md"
    globs = next(
        ln.removeprefix("tests:").split()
        for ln in template.read_text(encoding="utf-8").splitlines()
        if ln.startswith("tests:")
    )
    paths = ["src/ui/ABTest.tsx", "docs/LoadTest.md"]
    for rel in paths:
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text("x\n", encoding="utf-8")
    run = lambda *a: subprocess.run(  # noqa: E731
        ["git", "-c", "user.name=t", "-c", "user.email=t@t.invalid", *a],
        cwd=tmp_path, check=True, capture_output=True, text=True,
    ).stdout  # fmt: skip
    run("init", "-q")
    run("add", ".")

    assert run("ls-files", "--", *(f":(glob){g}" for g in globs)).split() == []


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="default-tests-globs-under-match-dotnet-android")  # fmt: skip
def test_the_shipped_default_freezes_dotnet_and_android_test_trees(tmp_path: Path) -> None:
    template = canon.default_public_dir() / "templates" / "repo-AGENTS.md"
    globs = next(
        ln.removeprefix("tests:").split()
        for ln in template.read_text(encoding="utf-8").splitlines()
        if ln.startswith("tests:")
    )
    paths = ["Foo.Tests/FooTest.cs", "app/src/androidTest/a/FooTest.kt"]
    for rel in paths:
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text("x\n", encoding="utf-8")
    run = lambda *a: subprocess.run(  # noqa: E731
        ["git", "-c", "user.name=t", "-c", "user.email=t@t.invalid", *a],
        cwd=tmp_path, check=True, capture_output=True, text=True,
    ).stdout  # fmt: skip
    run("init", "-q")
    run("add", ".")

    assert sorted(run("ls-files", "--", *(f":(glob){g}" for g in globs)).split()) == sorted(paths)
