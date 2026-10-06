"""T-047-95: `memory.py drift --since <sha>` is the worklist a closure
reconciles from. Size: SMALL.

The fixture is a real, tiny git repository rather than the live tree: the verb's answer is
a function of a commit window, and a window fabricated by patching `git` would assert the
patch. Every case below is a property of the window, never of this repo's atom count.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from tests.helpers.skill_scripts import stage_skill_scripts

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
    """memory.py staged alone: the navigator imports nothing from any other skill."""
    staged = tmp_path / "skills" / "dd-spec-navigator" / "scripts"
    return stage_skill_scripts("dd-spec-navigator", staged) / "memory.py"


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


def test_every_code_directory_no_atom_covers_is_listed(script: Path, repo: Path) -> None:
    base = _git(repo, "rev-parse", "HEAD")

    report = json.loads(_run(script, repo, "--since", base, "--json").stdout)

    assert report["uncovered"] == [
        "dadaia_workspace/features/beta",
        "dadaia_workspace/hooks",
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


def test_drift_requires_since_and_resolves_no_window_itself(script: Path, repo: Path) -> None:
    """The window resolver is the release skill's alone: the human tool is told its start."""
    result = _run(script, repo)

    assert result.returncode == 2
    assert "--since" in result.stderr


@pytest.mark.parametrize("orphaned", ["since", "until"])
def test_a_bound_head_does_not_reach_refuses_as_a_clean_clone_would(
    script: Path, repo: Path, orphaned: str
) -> None:
    """memory-window-bound-unreachable-from-head: a rebased-away sha still in the object
    store is refused by the one decider every verb calls, as a single-branch clone (which
    lacks it) refuses it."""
    base = _git(repo, "rev-parse", "HEAD")
    (repo / "README.md").write_text("dropped\n", "utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-qm", "dropped by a rebase")
    orphan = _git(repo, "rev-parse", "HEAD")
    _git(repo, "reset", "-q", "--hard", base)
    bounds = {"since": base, "until": base, orphaned: orphan}
    call = (
        f"import sys; sys.path.insert(0, {str(script.parent)!r}); import _memory_drift as d\n"
        f"try: d.report(__import__('pathlib').Path({str(repo / 'specs')!r}), "
        f"{bounds['since']!r}, {bounds['until']!r})\n"
        "except d.Refusal as r: print(r); print(r.fix)"
    )

    shown = subprocess.run([sys.executable, "-c", call], capture_output=True, text=True, check=True)

    assert shown.stdout.splitlines() == [
        f"{orphan} is not an ancestor of HEAD — a clone of this branch lacks it (a rebase rewrote it)",
        f"Operator action: replace {orphan[:12]} with the commit HEAD reaches in its place",
    ]


def test_a_bound_a_shallow_clone_holds_beyond_its_cut_names_the_cut_not_a_rebase(
    script: Path, repo: Path, tmp_path: Path
) -> None:
    """memory-window-bound-shallow-clone-named-as-rebase: a shallow clone that fetched an
    older bound by sha holds it, yet HEAD does not reach it through the cut history; the
    refusal names the cut and its fix line, never a rebase."""
    older = _git(repo, "rev-parse", "HEAD")
    (repo / "later.txt").write_text("later\n", "utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "later")
    clone = tmp_path / "clone"
    _git(tmp_path, "clone", "-q", "--depth", "1", f"file://{repo}", str(clone))
    _git(clone, "fetch", "-q", "--depth", "1", "origin", older)
    shown = _refusal(
        script, f"d.report(__import__('pathlib').Path({str(clone / 'specs')!r}), {older!r})"
    )

    assert shown == [
        f"{older} is out of reach: a shallow clone lacks the window's history",
        f"git -C {clone.as_posix()} fetch --unshallow",
    ]


def _refusal(script: Path, call: str) -> list[str]:
    """The message and fix line of the `Refusal` the python *call* raises, in the staged skill."""
    code = (
        f"import sys; sys.path.insert(0, {str(script.parent)!r}); import _memory_drift as d\n"
        f"try: {call}\nexcept d.Refusal as r: print(r); print(r.fix)"
    )
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    return done.stdout.splitlines()


def test_an_absent_bound_is_left_to_gits_own_refusal_not_named_a_rebase(
    script: Path, repo: Path
) -> None:
    """The decider tells three bounds apart: an absent one is neither a cut nor a rebase."""
    shown = _refusal(
        script, f"d.report(__import__('pathlib').Path({str(repo / 'specs')!r}), '0' * 40)"
    )

    assert "rebase" not in shown[0] and "shallow" not in shown[0]
    assert shown[1] == (
        "Operator action: run this verb from a checkout whose history holds the --since commit"
    )


def test_a_git_read_that_fails_in_a_shallow_clone_names_the_cut(
    script: Path, repo: Path, tmp_path: Path
) -> None:
    """A caller that passes no bound (release.py, _release_tree.py) gets the same cut naming."""
    (repo / "later.txt").write_text("later\n", "utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "later")
    clone = tmp_path / "clone"
    _git(tmp_path, "clone", "-q", "--depth", "1", f"file://{repo}", str(clone))

    shown = _refusal(
        script,
        f"d.git(__import__('pathlib').Path({str(clone)!r}), 'rev-parse', '--verify', '-q', 'nope')",
    )

    assert shown == [
        f"git rev-parse --verify -q nope failed in {clone}: a shallow clone lacks the window's history",
        f"git -C {clone.as_posix()} fetch --unshallow",
    ]


def _release_drift(script: Path, repo: Path, state: dict[str, object]) -> dict[str, object]:
    """`release.py drift` over a live release carrying *state*: the release skill is
    projected beside the navigator, as `public install` lays it out."""
    release = stage_skill_scripts(
        "dd-release-implementation", script.parents[2] / "dd-release-implementation" / "scripts"
    )
    (repo / "specs" / "releases" / "9.9.9").mkdir(parents=True)
    (repo / "specs" / "releases" / "9.9.9" / "_RELEASE.json").write_text(json.dumps(state))
    result = subprocess.run(
        [sys.executable, str(release / "release.py"), "drift", "--specs", str(repo / "specs"),
         "--json"], capture_output=True, text=True, check=False, cwd=repo,
    )  # fmt: skip
    assert result.returncode in (0, 1), result.stderr
    return dict(json.loads(result.stdout))


def test_the_closure_window_opens_at_the_live_release_defined_sha(script: Path, repo: Path) -> None:
    """memory-drift-requires-since-that-the-procedure-says-it-infers#window: the closure
    worklist is asked with no sha; with no memory entry the window opens at defined.sha."""
    base = _git(repo, "rev-parse", "HEAD")
    (repo / "dadaia_workspace" / "features" / "alpha" / "core.py").write_text("x = 2\n", "utf-8")
    _git(repo, "commit", "-aqm", "touch alpha")

    report = _release_drift(script, repo, {"defined": {"sha": base}, "log": []})

    assert report["since"] == base
    assert [a["slug"] for a in report["atoms"]] == ["alpha"]  # type: ignore[union-attr]


def test_the_closure_window_opens_at_the_last_memory_entry_until(script: Path, repo: Path) -> None:
    """memory-drift-requires-since-that-the-procedure-says-it-infers#window: a recorded
    `kind: memory` entry moves the window start to its `until`."""
    base = _git(repo, "rev-parse", "HEAD")
    (repo / "README.md").write_text("later\n", "utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-qm", "later")
    until = _git(repo, "rev-parse", "HEAD")
    state = {"defined": {"sha": base}, "log": [{"kind": "memory", "since": base, "until": until}]}

    assert _release_drift(script, repo, state)["since"] == until


@pytest.mark.parametrize(
    ("path", "unit"),
    [
        ("main.py", None),
        ("cmd/tool/main.go", "cmd/tool"),
        ("src/lex.c", "src"),
        (".github/workflows/ci.yml", None),
    ],
)
def test_any_tracked_file_makes_its_directory_a_unit(
    script: Path, repo: Path, path: str, unit: str | None
) -> None:
    """T-050-154: no language list — a `.c` dir is a unit; a unit is a directory, so a
    root-level file or one under a dot-dir is never listed."""
    (repo / path).parent.mkdir(parents=True, exist_ok=True)
    (repo / path).write_text("z = 1\n", "utf-8")
    _git(repo, "add", path)
    _git(repo, "commit", "-qm", "code")
    base = _git(repo, "rev-parse", "HEAD")

    report = json.loads(_run(script, repo, "--since", base, "--json").stdout)

    if unit is None:
        assert report["uncovered"] and not [u for u in report["uncovered"] if path.startswith(u)]
    else:
        assert unit in report["uncovered"]
