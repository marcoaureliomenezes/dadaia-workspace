"""``scripts/ci.py`` names the failing step and exits 1, run over a tmp tree (never the
checkout): the script, ``pyproject.toml`` and a one-contract ``setup.cfg`` copied in, beside
the planted files."""

from __future__ import annotations

import importlib.util
import os
import shlex
import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path

import pytest
import yaml

from tests.fixtures.harness_env import suite_env
from tests.fixtures.stores import fake_venv

pytestmark = pytest.mark.slow(reason="each case spawns scripts/ci.py and its tools")
_REPO = Path(__file__).resolve().parents[2]
_CONTRACT = """[importlinter]
root_package = dadaia_workspace
[importlinter:contract:one]
name = one
type = independence
modules =
    dadaia_workspace.a
    dadaia_workspace.m
"""


def _checkout(root: Path, files: dict[str, str]) -> Path:
    for d in ("scripts", "tests"):
        (root / d).mkdir(parents=True)
    for kept in ("scripts/ci.py", "scripts/covdata.py", "pyproject.toml"):
        shutil.copyfile(_REPO / kept, root / kept)
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")
    return root


def _ci(checkout: Path, job: str, python: str = sys.executable) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [python, str(checkout / "scripts" / "ci.py"), job],
        cwd=checkout,
        # an outer coverage session (the medium tests run under it) must not steer this inner one
        env=suite_env(
            os.environ,
            Path.home(),
            unset=tuple(
                k
                for k in os.environ
                if k == "PYTHONDONTWRITEBYTECODE" or k.startswith(("COV_CORE_", "COVERAGE"))
            ),
        ),
        capture_output=True,
        text=True,
        check=False,
    )


def _instance(root: Path) -> Path:
    (root / ".dadaia" / "states").mkdir(parents=True)
    (root / ".dadaia" / "states" / "spec_contexts.json").write_text('{"contexts": []}\n')
    return root


def _venv_owned_by(instance: Path) -> str:
    """A python whose ``sys.prefix`` is ``<instance>/.dadaia/.venv``: ``fake_venv``'s copy of
    this interpreter, and a ``.pth`` onto its packages — no install."""
    venv = instance / ".dadaia" / ".venv"
    site = venv / Path(sysconfig.get_path("purelib")).relative_to(sys.prefix)
    site.mkdir(parents=True)
    (site / "deps.pth").write_text(sysconfig.get_path("purelib") + "\n")
    return str(fake_venv(instance))


@pytest.mark.parametrize(
    ("source", "last", "code"),
    [("import os\n", "FAILED: ruff check", 1), ("x = 1\n", "ALL PASS", 0)],
)
def test_lint_exits_by_the_step_that_failed(
    tmp_path: Path, source: str, last: str, code: int
) -> None:
    files = {
        "setup.cfg": _CONTRACT,
        "dadaia_workspace/__init__.py": "",
        "dadaia_workspace/a.py": "",
    }
    done = _ci(_checkout(tmp_path, {**files, "dadaia_workspace/m.py": source}), "lint")
    assert done.stdout.splitlines()[-1] == last
    assert done.returncode == code


@pytest.mark.parametrize(
    ("check", "verdict", "code"),
    [
        ("1 == 2", "FAIL unit-fast", 1),
        ("1 == 1", "PASS unit-fast", 0),
        ("1 == 2", "FAIL integration", 1),
        ("1 == 1", "PASS integration", 0),
    ],
)
def test_unit_fast_exits_by_its_unit_tests(
    tmp_path: Path, check: str, verdict: str, code: int
) -> None:
    job = verdict.split()[1]
    size = "medium" if job == "integration" else "small"
    test = f"import pytest\n\n\n@pytest.mark.{size}\ndef test_one() -> None:\n    assert {check}\n"
    done = _ci(_checkout(tmp_path, {"tests/unit/test_one.py": test}), job)
    assert verdict in done.stdout
    assert done.returncode == code
    assert list(tmp_path.rglob("__pycache__")) == []  # no step writes bytecode into the tree


@pytest.mark.parametrize("owner", ["encloses the checkout", "owns the venv"])
def test_doctor_judges_no_instance(tmp_path: Path, owner: str) -> None:
    instance = _instance(tmp_path / "inst")
    nested = owner == "encloses the checkout"
    checkout = _checkout(instance / "repos" / "co" if nested else tmp_path / "co", {})
    (checkout / "dadaia_workspace").symlink_to(_REPO / "dadaia_workspace")
    done = _ci(checkout, "doctor", sys.executable if nested else _venv_owned_by(instance))
    assert "doctor --specs-dir specs" in done.stdout
    # The workspace section (WS-*) judges a resolved instance; the fenced run resolves none.
    assert [ln for ln in done.stdout.splitlines() if ln.startswith("WS-")] == []


def test_contract_coverage_writes_no_coverage_file_into_the_checkout(tmp_path: Path) -> None:
    files = {
        "dadaia_workspace/__init__.py": "",
        "dadaia_workspace/m.py": "def one() -> int:\n    return 1\n",
        "tests/unit/test_m.py": (
            "import pytest\n\nfrom dadaia_workspace.m import one\n\n\n"
            "@pytest.mark.small\ndef test_one() -> None:\n    assert one() == 1\n"
        ),
    }
    checkout = _checkout(tmp_path, files)
    (checkout / "tests" / "contract").mkdir()
    done = _ci(checkout, "contract-coverage")
    assert done.returncode == 0
    assert list(tmp_path.rglob("*coverage*")) == []


def _plan(*argv: str) -> list[str]:
    """``ci.py``'s step plan for *argv*, read without running a step."""
    spec = importlib.util.spec_from_file_location("ci", _REPO / "scripts" / "ci.py")
    assert spec and spec.loader
    ci = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ci)
    return [f"{job}: {name}" for job, (name, _, _) in ci.plan(list(argv))]


def test_job_verify_is_the_fast_check() -> None:
    assert _plan("job") == _plan() == [
        "lint: ruff format", "lint: ruff check", "lint: lint-imports", "typecheck: mypy",
        "guards: guards", "guards: guards --planted", "unit-fast: unit-fast",
    ]  # fmt: skip


def test_pushes_use_linux_and_pull_requests_use_the_full_matrix() -> None:
    workflow = yaml.load(
        (_REPO / ".github/workflows/ci.yml").read_text("utf-8"), Loader=yaml.BaseLoader
    )
    triggers = workflow["on"]
    assert set(triggers["push"]["branches"]) >= {"feature/**", "wt/**"}
    assert set(triggers["pull_request"]["branches"]) == {"main", "develop"}
    cross_platform = [
        job
        for job in workflow["jobs"].values()
        if set(job.get("strategy", {}).get("matrix", {}).get("os", []))
        & {"windows-latest", "macos-latest"}
    ]
    assert cross_platform
    assert {job.get("if") for job in cross_platform} == {
        "${{ github.event_name == 'pull_request' }}"
    }


@pytest.mark.parametrize("doc", ["tests/README.md", "tests/AGENTS.md"])
def test_documented_coverage_line_leaves_no_coverage_file_in_the_checkout(
    tmp_path: Path, doc: str
) -> None:
    """AC2.1: on CI, the doc's own ``pytest --cov`` line, run in a git checkout, leaves no
    coverage file there (tracked, untracked or ignored)."""
    line = next(
        ln for ln in (_REPO / doc).read_text(encoding="utf-8").splitlines()
        if ln.startswith("python -m pytest") and "--cov" in ln
    )  # fmt: skip
    files = {
        ".gitignore": ".coverage\n",
        "dadaia_workspace/__init__.py": "",
        "dadaia_workspace/m.py": "def one() -> int:\n    return 1\n",
        "tests/unit/test_m.py": (
            "import pytest\n\nfrom dadaia_workspace.m import one\n\n\n"
            "@pytest.mark.small\ndef test_one() -> None:\n    assert one() == 1\n"
        ),
    }
    checkout = _checkout(tmp_path, files)
    subprocess.run(["git", "init", "-q"], cwd=checkout, check=True)
    tmp = tmp_path / "tmp"  # where the plugin's temp dir lives, and is gone after exit
    tmp.mkdir()
    env = suite_env(
        os.environ,
        Path.home(),
        unset=("COVERAGE_FILE",),
        overrides={"CI": "true", "TMPDIR": str(tmp)},
    )
    argv = [sys.executable, *shlex.split(line)[1:]]
    assert subprocess.run(argv, cwd=checkout, env=env, check=False).returncode == 0
    assert [p.name for p in tmp.iterdir() if p.name.startswith("dadaia-cov-")] == []
    status = subprocess.run(
        ["git", "status", "--porcelain", "--ignored"],
        cwd=checkout, capture_output=True, text=True, check=True,
    ).stdout  # fmt: skip
    assert [ln for ln in status.splitlines() if "coverage" in ln] == []
