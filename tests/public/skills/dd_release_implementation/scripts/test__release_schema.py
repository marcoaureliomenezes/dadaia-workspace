"""A release id has ONE grammar, the
script's bare M.m.p (`_release_schema.SEMVER_RE`); core consults it; archived dirs are
exempt by location. Size: SMALL.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from dadaia_workspace.core.release_state import RELEASE_ID_RE
from dadaia_workspace.features.specs.canon import is_canon_path
from tests.fixtures.harness_env import suite_env

_REPO_ROOT = Path(__file__).resolve().parents[5]
_SCRIPTS = _REPO_ROOT / "dadaia_workspace/public/skills/dd-release-implementation/scripts"
sys.path.insert(0, str(_SCRIPTS))
sys.path.append(str(_SCRIPTS.parents[1] / "dd-bug-resolution" / "scripts"))
import _release_schema  # noqa: E402


@pytest.mark.parametrize(
    ("release_id", "legal"),
    [
        ("0.5.0", True),
        ("10.20.30", True),
        ("0.5.0-rc1", False),
        ("v0.5.0", False),
        ("1.2", False),
        ("1.2.3-", False),
        ("next", False),
    ],  # fmt: skip
)
def test_one_release_id_grammar_everywhere(tmp_path: Path, release_id: str, legal: bool) -> None:
    """Core, the canon and `release.py new` agree on every id — a suffix and a `v` are refused."""
    assert bool(RELEASE_ID_RE.match(release_id)) is legal
    assert is_canon_path(f"releases/{release_id}/rc-1/SPEC.md") is legal
    (tmp_path / "specs" / "releases").mkdir(parents=True)
    new = subprocess.run([sys.executable, str(_SCRIPTS / "release.py"), "new", release_id,
                          "--specs", str(tmp_path / "specs")], capture_output=True, text=True)  # fmt: skip
    assert (new.returncode == 0) is legal, new.stderr


def test_the_release_instant_reader_reads_an_instant_with_no_offset_as_utc() -> None:
    """`_utc` reads every
    instant in UTC — an offset converts, `Z` and `+00:00` are UTC, no offset is UTC and never
    the host's zone (run on a host three hours behind UTC), a malformed one raises ValueError."""
    probe = (
        "import sys; sys.path.insert(0, sys.argv[1]); sys.path.append(sys.argv[1] + '/../../dd-bug-resolution/scripts')\n"
        "import _release_schema as r\n"
        "for ts in sys.argv[2:]:\n"
        "    try: print(r.utc(ts).isoformat())\n"
        "    except ValueError: print('ValueError')\n"
    )  # fmt: skip
    instants = ["2026-10-06T23:30:00", "2026-10-06T23:30:00Z", "2026-10-06T23:30:00+00:00",
                "2026-10-06T23:30:00-03:00", "not-a-timestamp", ""]  # fmt: skip
    env = suite_env(os.environ, Path.home(), overrides={"TZ": "UTC+3"})
    out = subprocess.run([sys.executable, "-c", probe, str(_SCRIPTS), *instants],
                         capture_output=True, text=True, env=env, check=True)  # fmt: skip
    assert out.stdout.split() == ["2026-10-06T23:30:00+00:00"] * 3 + ["2026-10-07T02:30:00+00:00"] + ["ValueError"] * 2  # fmt: skip


@pytest.mark.parametrize("task_id", ["J2.T3", "J2.S1.T3"], ids=["current", "historical"])
def test_a_job_accepts_both_supported_task_id_shapes(task_id: str) -> None:
    job = (
        "# Job 2\n\n"
        "| task | AC | `W:` | outcome |\n"
        "|---|---|---|---|\n"
        f"| {task_id} | AC2.1 | `src/x.py` | parser owner |\n"
    )

    assert _release_schema.job_errors(job, "tasks/job2.md") == []


@pytest.mark.parametrize(
    "header",
    [
        "task | AC | notes | outcome",
        "id | AC | `W:` | outcome",
        "task | acceptance | `W:` | outcome",
    ],
)
def test_a_current_job_requires_its_canonical_task_columns(header: str) -> None:
    job = (
        "# Job 2\n\n"
        f"| {header} |\n"
        "|---|---|---|---|\n"
        "| J2.T3 | AC2.1 | `src/x.py` | parser owner |\n"
    )

    assert _release_schema.job_errors(job, "tasks/job2.md")


@pytest.mark.parametrize(
    "rows",
    [
        "| J2.T3 | AC2.1 | `src/x.py` | owner | extra |\n",
        "| J2.T3 | AC2.1 | `src/x.py` | owner |\n| J2.T3 | AC2.2 | `tests/test_x.py` | owner |\n",
        "| J2.T3 | AC2.1 | `src/x.py` | owner |\n|  |  |  |  |\n",
    ],
    ids=["malformed", "duplicate", "empty"],
)
def test_a_current_job_refuses_malformed_duplicate_and_empty_rows(rows: str) -> None:
    job = f"# Job 2\n\n| task | AC | `W:` | outcome |\n|---|---|---|---|\n{rows}"

    assert _release_schema.job_errors(job, "tasks/job2.md")


def test_a_current_job_keeps_every_task_after_its_canonical_separator() -> None:
    job = (
        "# Job 2\n\n"
        "| task | AC | `W:` | outcome |\n"
        "|---|---|---|---|\n"
        "| J2.T1 | AC3.3 | `src/first.py` | owner |\n"
        "| J2.T2 | AC3.3 | `src/second.py` | owner |\n"
    )

    assert _release_schema.current_job_writes(job, "tasks/job2.md") == (
        {"src/first.py", "src/second.py"},
        [],
    )
    assert _release_schema.job_errors(job, "tasks/job2.md") == []


@pytest.mark.parametrize(
    "separator",
    [
        pytest.param("", id="missing"),
        pytest.param("|---|---|---|\n", id="wrong-column-count"),
        pytest.param("|---|---|owner|---|\n", id="non-separator-cell"),
    ],
)
def test_a_current_job_refuses_noncanonical_table_framing(separator: str) -> None:
    job = (
        "# Job 2\n\n"
        "| task | AC | `W:` | outcome |\n"
        f"{separator}"
        "| J2.T1 | AC3.3 | `src/first.py` | owner |\n"
        "| J2.T2 | AC3.3 | `src/second.py` | owner |\n"
    )

    _, errors = _release_schema.current_job_writes(job, "tasks/job2.md")
    assert errors
    assert _release_schema.job_errors(job, "tasks/job2.md") == errors


def test_a_current_plan_keeps_every_job_after_its_canonical_separator() -> None:
    plan = (
        "## As-is review\n\n"
        "## DAG\n\n"
        "| job | waits on | wave | `W:` |\n"
        "|---|---|---|---|\n"
        "| Job 1 | — | 1 | `src/first.py` |\n"
        "| Job 2 | Job 1 | 2 | `src/second.py` |\n"
    )

    assert _release_schema.current_plan_jobs(plan) == (
        {
            "Job 1": (1, {"src/first.py"}),
            "Job 2": (2, {"src/second.py"}),
        },
        [],
    )
    assert _release_schema.plan_errors(plan) == []


@pytest.mark.parametrize(
    "separator",
    [
        pytest.param("", id="missing"),
        pytest.param("|---|---|---|\n", id="wrong-column-count"),
        pytest.param("|---|---|owner|---|\n", id="non-separator-cell"),
    ],
)
def test_a_current_plan_refuses_noncanonical_table_framing(separator: str) -> None:
    plan = (
        "## As-is review\n\n"
        "## DAG\n\n"
        "| job | waits on | wave | `W:` |\n"
        f"{separator}"
        "| Job 1 | — | 1 | `src/first.py` |\n"
        "| Job 2 | Job 1 | 2 | `src/second.py` |\n"
    )

    _, errors = _release_schema.current_plan_jobs(plan)
    assert errors
    assert _release_schema.plan_errors(plan) == errors


def _state(*stamps: tuple[int, str]) -> dict:
    """A `release-state-v1` object whose log holds one `milestone` entry per stamp."""
    return {
        "log": [
            {"ts": "2026-10-01T00:00:00Z", "agent": "main", "kind": "milestone",
             "text": f"rc-{n} {slot}", "candidate": f"rc-{n}", "milestone": slot, "sha": "abc1234"}
            for n, slot in stamps
        ]
    }  # fmt: skip


@pytest.mark.parametrize(
    ("folders", "files", "stamps", "expected"),
    [
        pytest.param([1, 2], [], [(1, "implemented")], "rc-2", id="closed-rc1-with-a-draft"),
        pytest.param([1], [], [(1, "implemented")], "rc-2", id="closed-rc1-no-draft"),
        pytest.param([1, 2], [], [(1, "implemented"), (2, "implemented")], "rc-3", id="two-closed"),
        pytest.param(
            [1], ["rc-9"], [(1, "implemented")], "rc-2", id="a-stray-file-changes-nothing"
        ),
        pytest.param([1, 2], [], [(1, "defined")], "rc-2", id="draft-cancelled-before-a-milestone"),
    ],  # fmt: skip
)
def test_the_next_candidate_is_the_last_milestone_plus_one(
    tmp_path: Path,
    folders: list[int],
    files: list[str],
    stamps: list[tuple[int, str]],
    expected: str,
) -> None:
    for n in folders:
        (tmp_path / f"rc-{n}").mkdir()
    if 2 in folders:
        (tmp_path / "rc-2" / "SPEC.md").write_text("draft")
    for name in files:
        (tmp_path / name).write_text("")
    assert _release_schema.next_candidate(tmp_path, _state(*stamps)) == tmp_path / expected


def test_the_next_candidate_with_no_state_is_the_highest_folder_plus_one(tmp_path: Path) -> None:
    for n in (1, 4):
        (tmp_path / f"rc-{n}").mkdir()
    (tmp_path / "rc-9").write_text("")
    assert _release_schema.next_candidate(tmp_path, None) == tmp_path / "rc-5"


@pytest.mark.parametrize(
    ("folders", "flat", "next_rc", "stateless_rc", "current_rc"),
    [
        pytest.param([1, 2, 3], False, "rc-4", "rc-4", "rc-3", id="empty-log-over-three-folders"),
        pytest.param(
            [], True, "rc-2", "rc-1", None, id="a-live-flat-trio-is-rc1-a-stateless-one-is-placed"
        ),
    ],
)
def test_a_state_with_no_milestone_reads_the_folders(
    tmp_path: Path,
    folders: list[int],
    flat: bool,
    next_rc: str,
    stateless_rc: str,
    current_rc: str | None,
) -> None:
    for n in folders:
        (tmp_path / f"rc-{n}").mkdir()
    if flat:
        (tmp_path / "SPEC.md").write_text("flat")
    state = {"phase": "CLOSURE", "log": []}
    assert _release_schema.next_candidate(tmp_path, state) == tmp_path / next_rc
    assert _release_schema.next_candidate(tmp_path, None) == tmp_path / stateless_rc
    assert _release_schema.current_candidate(tmp_path, state) == (
        tmp_path / current_rc if current_rc else None
    )


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=cwd, check=True,
                   capture_output=True, env={**os.environ, "GIT_CONFIG_GLOBAL": os.devnull})  # fmt: skip


def _repo(path: Path, *, spec: bool) -> Path:
    """A repo of two commits; with *spec*, the first adds a Draft SPEC for the live candidate."""
    path.mkdir()
    _git("init", "-q", cwd=path)
    if spec:
        (path / "releases/0.5.0/rc-1").mkdir(parents=True)
        (path / "releases/0.5.0/rc-1/SPEC.md").write_text("**Status:** Draft\n")
    (path / "f").write_text("1")
    _git("add", "-A", cwd=path)
    _git("commit", "-qm", "one", cwd=path)
    (path / "f").write_text("2")
    _git("commit", "-qam", "two", cwd=path)
    return path


def _adds_under_foreign_git_env(specs: Path, other: Path) -> subprocess.CompletedProcess[str]:
    """`candidate_adds(specs)` run with GIT_DIR and GIT_WORK_TREE both on *other* (GIT_DIR alone
    would let git take the cwd as the work tree and pass by accident)."""
    probe = (
        "import sys; sys.path.insert(0, sys.argv[1]); sys.path.append(sys.argv[1] + '/../../dd-bug-resolution/scripts')\n"
        "import _release_schema as r\n"
        "print([[a, b] for _, a, b in r.candidate_adds(__import__('pathlib').Path(sys.argv[2]))])\n"
    )  # fmt: skip
    env = {**os.environ, "GIT_DIR": str(other / ".git"), "GIT_WORK_TREE": str(other)}
    return subprocess.run([sys.executable, "-c", probe, str(_SCRIPTS), str(specs)],
                          capture_output=True, text=True, env=env, check=False)  # fmt: skip


def test_the_birth_log_answers_for_the_repo_given_not_for_git_dir(tmp_path: Path) -> None:
    """The release runner: with GIT_DIR and GIT_WORK_TREE on another repo, the log read
    still lists the Draft SPEC that repo A holds — today it reads B and finds none."""
    a, b = _repo(tmp_path / "a", spec=True), _repo(tmp_path / "b", spec=False)
    out = _adds_under_foreign_git_env(a, b)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "[['0.5.0', 'rc-1']]"


def test_the_shallow_check_answers_for_the_repo_given_not_for_git_dir(tmp_path: Path) -> None:
    """A shallow GIT_DIR repo B must not make the full repo A read as shallow."""
    a, b = _repo(tmp_path / "a", spec=True), _repo(tmp_path / "src", spec=False)
    shallow = tmp_path / "shallow"
    subprocess.run(["git", "clone", "-q", "--depth", "1", f"file://{b}", str(shallow)], check=True,
                   capture_output=True, env={**os.environ, "GIT_CONFIG_GLOBAL": os.devnull})  # fmt: skip
    out = _adds_under_foreign_git_env(a, shallow)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "[['0.5.0', 'rc-1']]"
