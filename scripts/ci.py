"""The ONE source of the Linux CI jobs and repository verification:
``python scripts/ci.py [<job>...]`` runs the named ``ci.yml`` jobs (all of them when none is
given); ``task FILE...`` runs ruff and mypy on the touched files and the touched tests;
``stage`` and ``job`` run lint, mypy, guards and the small tier. Each step
prints ``PASS``/``FAIL <step>: <command>``; every step runs; exit 1 if any failed. Standard
library only: the ``repo-hygiene`` and ``doctor`` jobs install no dev group."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
# ruff errors on an absent path, so only the trees this checkout has.
SRC = [d for d in ("dadaia_workspace/", "tests/", "scripts/", "evals/") if (ROOT / d).is_dir()]
# -n 2 caps the workers (machine limit); pytest-randomly, in the dev group, shuffles the order.
PYTEST = [PY, "-m", "pytest", "-q", "-n", "2", "--durations=25"]

Step = tuple[str, list[str], dict[str, str]]
JOBS: dict[str, list[Step]] = {
    "lint": [
        ("ruff format", [PY, "-m", "ruff", "format", "--check", "--no-cache", *SRC], {}),
        ("ruff check", [PY, "-m", "ruff", "check", "--no-cache", *SRC], {}),
        # import-linter has no __main__: its console script sits beside the interpreter.
        (
            "lint-imports",
            [str(Path(PY).parent / "lint-imports"), "--config", "setup.cfg", "--no-cache"],
            {},
        ),
    ],
    "typecheck": [("mypy", [PY, "-m", "mypy", "--strict", "dadaia_workspace/", "scripts/"], {})],
    "guards": [
        ("guards", [PY, "scripts/guards/run.py"], {}),
        ("guards --planted", [PY, "scripts/guards/run.py", "--planted"], {}),
    ],
    "unit-fast": [
        ("unit-fast", [*PYTEST, "-m", "small and not slow and not quarantine", "tests"], {}),
    ],
    "contract-coverage": [
        (
            "contract-coverage",
            [
                *PYTEST,
                "-m",
                "not e2e and not quarantine",
                "-p",
                "scripts.covdata",
                "--cov=dadaia_workspace",
                "--cov-report=term-missing",
                "--cov-fail-under=80",
                "tests",
            ],
            {},
        ),
    ],
    "integration": [
        ("integration", [*PYTEST, "-m", "medium and not quarantine", "tests"], {}),
    ],
    # The whole e2e tree; DADAIA_REQUIRE_UVX turns the journey's "uvx absent" skip into a failure.
    "e2e-python": [
        (
            "e2e-python",
            [*PYTEST, "-m", "e2e and not quarantine", "tests/e2e"],
            {"DADAIA_REQUIRE_UVX": "1"},
        ),
    ],
    "repo-hygiene": [
        ("repo-hygiene", ["bash", ".github/scripts/check_no_repo_local_claude.sh"], {})
    ],
    # PYTHONPATH: the checkout's package is judged, never an installed one.
    "doctor": [
        (
            "doctor",
            [PY, "-m", "dadaia_workspace", "doctor", "--specs-dir", "specs"],
            {"PYTHONPATH": str(ROOT)},
        ),
    ],
}


STAGE = ("lint", "typecheck", "guards", "unit-fast")


def _task(files: list[str]) -> list[Step]:
    """The task level over the touched *files*: format, lint, types, then the touched tests."""
    py = [f for f in files if f.endswith(".py")]
    tests = [f for f in py if f.startswith("tests/") and Path(f).name.startswith("test_")]
    src = [f for f in py if f not in tests and f.startswith(("dadaia_workspace/", "scripts/"))]
    return [
        *(
            [("ruff format", [PY, "-m", "ruff", "format", "--check", "--no-cache", *py], {}),
             ("ruff check", [PY, "-m", "ruff", "check", "--no-cache", *py], {})]
            if py else []
        ),
        *([("mypy", [PY, "-m", "mypy", "--strict", *src], {})] if src else []),
        *([("owner tests", [*PYTEST, *tests], {})] if tests else []),
    ]  # fmt: skip


def plan(argv: list[str]) -> list[tuple[str, Step]]:
    """``(job, step)`` in run order for *argv*: a level, else the named CI jobs, else all."""
    if argv[:1] == ["task"]:
        return [("task", step) for step in _task(argv[1:])]
    jobs = STAGE if argv in ([], ["job"], ["stage"]) else argv
    return [(job, step) for job in jobs for step in JOBS[job]]


def main(argv: list[str]) -> int:
    # The fence (ADR 0088) mirrors the resolver's rungs: the inherited fence, every root above
    # the checkout, and the instance owning this venv (``fenced_env`` omits that last one, and
    # importing it would judge whichever ``dadaia_workspace`` is importable).
    fence = [os.environ.get("DADAIA_FENCED_ROOTS", ""), *map(str, ROOT.parents)]
    fence.append(str(Path(sys.prefix).resolve().parent.parent))
    failed = []
    base = {
        **os.environ,
        "PYTHONDONTWRITEBYTECODE": "1",
        "DADAIA_FENCED_ROOTS": os.pathsep.join(p for p in fence if p),
    }
    for job, (name, cmd, env) in plan(argv):
        print(f"--- {job}: {name}", flush=True)
        step_env = {**base, **env}
        code = subprocess.run(cmd, cwd=ROOT, env=step_env, check=False).returncode
        print(f"{'FAIL' if code else 'PASS'} {name}: {' '.join(cmd)}", flush=True)
        failed += [name] if code else []
    print(f"FAILED: {', '.join(failed)}" if failed else "ALL PASS", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
