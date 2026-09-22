"""Intent: CONTRACT — T-047-95: `memory.py drift --since <sha>` is the worklist a closure
reconciles from. Size: SMALL.

The fixture is a real, tiny git repository rather than the live tree: the verb's answer is
a function of a commit window, and a window fabricated by patching `git` would assert the
patch. Every case below is a property of the window, never of this repo's atom count.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.slow(reason="runs git over a tmp repository")]

_REPO = Path(__file__).resolve().parents[3]
_SCRIPTS = _REPO / "dadaia_workspace" / "public" / "skills" / "dd-spec-navigator" / "scripts"

_ATOM = """\
---
slug: {slug}
title: {slug}
tldr: {slug}
summary: {slug}
tags: [{slug}]
sources:{sources}
---

# {slug}
"""


def _git(cwd: Path, *argv: str) -> str:
    return subprocess.run(
        ["git", *argv], cwd=cwd, capture_output=True, text=True, check=True
    ).stdout.strip()


@pytest.fixture
def script(tmp_path: Path) -> Path:
    """memory.py staged with the release skill projected beside it, as install lays out."""
    skills = tmp_path / "skills"
    staged = skills / "dd-spec-navigator" / "scripts"
    staged.mkdir(parents=True)
    for module in sorted(_SCRIPTS.glob("*.py")):
        shutil.copy2(module, staged / module.name)
    shutil.copytree(_SCRIPTS.parents[1] / "dd-release-implementation" / "scripts",
                    skills / "dd-release-implementation" / "scripts")  # fmt: skip
    return staged / "memory.py"


@pytest.fixture
def repo(tmp_path: Path, script: Path) -> Path:
    """A repository carrying two feature packages, one hook, and one atom that declares
    the first package as its source — the second package and the hook are uncovered."""
    root = tmp_path / "fixture-repo"
    for package in ("alpha", "beta"):
        (root / "dadaia_workspace" / "features" / package).mkdir(parents=True)
        (root / "dadaia_workspace" / "features" / package / "__init__.py").write_text("", "utf-8")
        (root / "dadaia_workspace" / "features" / package / "core.py").write_text(
            "x = 1\n", "utf-8"
        )
    (root / "dadaia_workspace" / "hooks").mkdir(parents=True)
    (root / "dadaia_workspace" / "hooks" / "ctx_inject.py").write_text("y = 1\n", "utf-8")
    area = root / "specs" / "memory" / "product" / "platform"
    area.mkdir(parents=True)
    (area / "alpha.md").write_text(
        _ATOM.format(slug="alpha", sources="\n  - dadaia_workspace/features/alpha/**"), "utf-8"
    )

    _git(root.parent, "init", "-q", root.name)
    _git(root, "config", "user.email", "fixture@example.invalid")
    _git(root, "config", "user.name", "fixture")
    subprocess.run(
        [sys.executable, str(script), "catalog", "generate", "--specs", str(root / "specs")],
        capture_output=True,
        text=True,
        check=True,
    )
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "base")
    return root


def _run(script: Path, repo: Path, *argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), "drift", "--specs", str(repo / "specs"), *argv],
        capture_output=True,
        text=True,
        check=False,
        cwd=repo,
    )


def test_a_changed_source_lists_its_atom_with_the_matched_path(script: Path, repo: Path) -> None:
    base = _git(repo, "rev-parse", "HEAD")
    (repo / "dadaia_workspace" / "features" / "alpha" / "core.py").write_text("x = 2\n", "utf-8")
    _git(repo, "commit", "-aqm", "touch alpha")

    result = _run(script, repo, "--since", base, "--json")

    assert result.returncode == 1, result.stderr
    report = json.loads(result.stdout)
    assert report["since"] == base
    assert report["atoms"] == [
        {
            "slug": "alpha",
            "path": "specs/memory/product/platform/alpha.md",
            "matched": ["dadaia_workspace/features/alpha/core.py"],
        }
    ]


def test_every_package_and_hook_no_atom_covers_is_listed(script: Path, repo: Path) -> None:
    base = _git(repo, "rev-parse", "HEAD")

    report = json.loads(_run(script, repo, "--since", base, "--json").stdout)

    assert report["uncovered"] == [
        "dadaia_workspace/features/beta",
        "dadaia_workspace/hooks/ctx_inject.py",
    ]


def test_a_window_with_nothing_drifted_exits_zero(script: Path, repo: Path) -> None:
    """Coverage for beta and the hook too: an empty worklist is the only exit-0 state."""
    area = repo / "specs" / "memory" / "product" / "platform"
    (area / "beta.md").write_text(
        _ATOM.format(
            slug="beta",
            sources=(
                "\n  - dadaia_workspace/features/beta/**\n  - dadaia_workspace/hooks/ctx_inject.py"
            ),
        ),
        "utf-8",
    )
    subprocess.run(
        [sys.executable, str(script), "catalog", "generate", "--specs", str(repo / "specs")],
        check=True,
        capture_output=True,
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "cover beta")
    base = _git(repo, "rev-parse", "HEAD")
    (repo / "README.md").write_text("unrelated\n", "utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "unrelated change")

    result = _run(script, repo, "--since", base, "--json")

    assert result.returncode == 0, result.stdout
    assert json.loads(result.stdout) == {"since": base, "atoms": [], "uncovered": []}


def test_an_atom_without_sources_covers_nothing(script: Path, repo: Path) -> None:
    """`sources` arrives atom by atom: a catalog entry without the field is tolerated and
    simply covers no code — never a traceback, never a silent full-tree pass."""
    catalog = repo / "specs" / "memory" / "product" / "catalog.json"
    document = json.loads(catalog.read_text("utf-8"))
    for entry in document["features"]:
        entry.pop("sources", None)
    catalog.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", "utf-8")
    _git(repo, "commit", "-aqm", "catalog without sources")
    base = _git(repo, "rev-parse", "HEAD")

    report = json.loads(_run(script, repo, "--since", base, "--json").stdout)

    assert report["atoms"] == []
    assert "dadaia_workspace/features/alpha" in report["uncovered"]


def test_no_milestone_refuses_with_a_fix_naming_since(script: Path, repo: Path) -> None:
    """R5: a tree with no `implemented`/`defined` sha never defaults to the root commit and
    reports the whole tree — it refuses and names the flag that unblocks it."""
    releases = repo / "specs" / "releases" / "9.9.9"
    releases.mkdir(parents=True)
    (releases / "_RELEASE.json").write_text(
        json.dumps({"schema": "release-state-v1", "release": "9.9.9", "phase": "DEFINITION"}),
        "utf-8",
    )

    result = _run(script, repo)

    assert result.returncode == 1
    assert result.stdout == ""
    assert "fix: " in result.stderr
    assert "phase IMPLEMENTATION" in result.stderr


def _live(repo: Path, **state: object) -> None:
    releases = repo / "specs" / "releases" / "9.9.9"
    releases.mkdir(parents=True)
    document = {"schema": "release-state-v1", "release": "9.9.9", "phase": "CLOSURE", **state}
    (releases / "_RELEASE.json").write_text(json.dumps(document), "utf-8")


def test_since_defaults_to_the_live_release_defined_sha(script: Path, repo: Path) -> None:
    """L1: the same rule `release.py memory` derives — no memory entry yet, defined.sha."""
    base = _git(repo, "rev-parse", "HEAD")
    _live(repo, defined={"sha": base, "ts": "2026-01-01T00:00:00Z"},
          implemented={"sha": "deadbee", "ts": "2026-01-02T00:00:00Z"}, log=[])  # fmt: skip

    assert json.loads(_run(script, repo, "--json").stdout)["since"] == base


def test_since_defaults_to_the_last_memory_entry_until(script: Path, repo: Path) -> None:
    base = _git(repo, "rev-parse", "HEAD")
    entry = {"kind": "memory", "since": "deadbee", "until": base}
    _live(repo, defined={"sha": "deadbee", "ts": "2026-01-01T00:00:00Z"}, log=[entry])

    assert json.loads(_run(script, repo, "--json").stdout)["since"] == base
