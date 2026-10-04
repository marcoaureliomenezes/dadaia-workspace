"""The ONE source of the Linux CI jobs: ``python scripts/ci.py [<job>...]`` runs the named
``ci.yml`` jobs (all of them when none is given), prints ``PASS``/``FAIL <step>: <command>``
per step, runs every step and exits 1 if any failed. Standard library only: the
``repo-hygiene`` and ``doctor`` jobs install no dev group."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
SRC = ["dadaia_workspace/", "tests/", "scripts/"]
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
        ("unit-fast", [*PYTEST, "-m", "unit and not slow and not quarantine", "tests/unit"], {}),
    ],
    "contract-coverage": [
        (
            "contract-coverage",
            [
                *PYTEST,
                "-m",
                "(unit or contract) and not quarantine",
                "--cov=dadaia_workspace",
                "--cov-report=term-missing",
                "--cov-fail-under=80",
                "tests/unit",
                "tests/contract",
            ],
            {"COVERAGE_FILE": "{tmp}/.coverage"},  # the run's own temp dir, removed at exit
        ),
    ],
    "integration": [
        ("integration", [*PYTEST, "-m", "integration and not quarantine", "tests/integration"], {}),
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


def main(argv: list[str]) -> int:
    # The fence (ADR 0088) mirrors the resolver's rungs: the inherited fence, every root above
    # the checkout, and the instance owning this venv (``fenced_env`` omits that last one, and
    # importing it would judge whichever ``dadaia_workspace`` is importable).
    fence = [os.environ.get("DADAIA_FENCED_ROOTS", ""), *map(str, ROOT.parents)]
    fence.append(str(Path(sys.prefix).resolve().parent.parent))
    base = {
        **os.environ,
        "PYTHONDONTWRITEBYTECODE": "1",
        "DADAIA_FENCED_ROOTS": os.pathsep.join(p for p in fence if p),
    }
    failed = []
    with tempfile.TemporaryDirectory(prefix="dadaia-ci-") as tmp:
        for job in argv or list(JOBS):
            for name, cmd, env in JOBS[job]:
                print(f"--- {job}: {name}", flush=True)
                step_env = {**base, **{k: v.replace("{tmp}", tmp) for k, v in env.items()}}
                code = subprocess.run(cmd, cwd=ROOT, env=step_env, check=False).returncode
                print(f"{'FAIL' if code else 'PASS'} {name}: {' '.join(cmd)}", flush=True)
                failed += [name] if code else []
    print(f"FAILED: {', '.join(failed)}" if failed else "ALL PASS", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
