"""A tmp workspace for `worktree.py` tests: one repo `r` on `main` with an Approved release
trio, a valid `_RELEASE.json`, a `scripts/ci.py` whose level L fails iff the tree holds
`RED-<L>`, and `feature/0.5.0`; its `verify:` lines declare it, and a stub CLI in the fake venv's
scripts dir (`cli_path`) standing for the two reads the script makes — `context list --json` (gitflow `dev` as integration, so a
hardcoded `main`/`develop` fails) and `reports validate` (valid iff `schema_version`)."""

from __future__ import annotations

import hashlib
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

from dadaia_workspace.core import clock, session_store
from dadaia_workspace.core.cli_line import shell_line
from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.core.platform import PLATFORM
from dadaia_workspace.core.skill_owner import load_owner
from dadaia_workspace.features.spec_context.doctor import DoctorService
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
from tests.fixtures.harness_env import CLAUDE_SESSION_ENV_VAR, run_bash, suite_env
from tests.fixtures.stores import context_store, fake_venv
from tests.helpers.oslib import run as run_text
from tests.helpers.oslib import write_text

SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "dadaia_workspace/public/skills/dd-gitflow-default/scripts/worktree.py"
)
#: The refusal line of a session no workspace hook governs.
RELAUNCH = "fix: Operator action: relaunch the session at the workspace root"
FLOW = {"principal": "trunk", "integration": "dev", "work": "feature/"}
#: The repo's gate: prints its argv; level L fails iff the tree holds `RED-<L>`.
CI = 'import pathlib, sys\nprint("ci", *sys.argv[1:])\nsys.exit(pathlib.Path("RED-" + sys.argv[1]).exists())\n'
#: The hierarchy's names: a job's main tree and its first task tree (`JOB` stays for `test__specs__workspace_root`).
JOB = "0.5.0-rc1/j1"
NEW_JOB, NEW_TASK = "0.5.0/rc-1/job-1/wt-main", "0.5.0/rc-1/job-1/wt-task-001"
_CLI = """#!python
import json, sys
args = sys.argv[1:]
if args[:2] == ["context", "list"]:
    import os
    fenced = [os.path.realpath(p) for p in os.environ.get("DADAIA_FENCED_ROOTS", "").split(os.pathsep) if p]
    if os.path.realpath(os.getcwd()) in fenced:
        print("[error] the workspace root is fenced", file=sys.stderr)
        sys.exit(1)
    print({rows!r})
elif args[:2] == ["context", "session-check"]:
    import os
    sid = os.environ.get("DADAIA_SESSION_ID") or os.environ.get("CLAUDE_CODE_SESSION_ID") or ""
    if sid and not os.path.exists(os.path.join(os.getcwd(), ".dadaia", "sessions", sid + ".json")):
        print("[error] no workspace hook governs this session", file=sys.stderr)
        print({relaunch!r}, file=sys.stderr)
        sys.exit(1)
elif args[:2] == ["reports", "validate"]:
    sys.exit(0 if "schema_version" in json.load(open(args[2])) else 1)
elif args[:1] == ["doctor"]:
    import os
    specs = args[args.index("--specs-dir") + 1]
    print("doctor --specs-dir " + specs, "fenced " + os.environ.get("DADAIA_FENCED_ROOTS", ""),
          "cwd " + os.getcwd(), sep="\\n")
    sys.exit(os.path.exists(os.path.join(specs, "RED-doctor")))
else:
    sys.stdin.read()
"""


def spelled(*parts: str) -> list[str]:
    """The argv the kernel's `shell_line` of *parts* splits to: the expected side of a printed fix."""
    return shlex.split(shell_line(*parts))


def cli_path(root: Path) -> Path:
    """Where the stub CLI lives: the fake venv's scripts dir, `dadaia` plus `PLATFORM`'s suffix."""
    return root / ".dadaia/.venv" / PLATFORM.venv_scripts_dir / f"dadaia{PLATFORM.venv_exe_suffix}"


_STUBS: dict[Path, str] = {}  # each workspace's stub source: on Windows the stub is an .exe


def _stub_cli(root: Path, *listed: dict[str, object]) -> None:
    """The `dadaia` stub over *listed*, placed at `cli_path` by `fake_venv` (startable per platform)."""
    _STUBS[root] = _CLI.format(rows=json.dumps(list(listed)), relaunch=RELAUNCH)
    fake_venv(root, cli=_STUBS[root])


def patch_cli(root: Path, old: str, new: str) -> None:
    """Re-stub *root*'s CLI with *old* replaced by *new* in its source (the `.exe` is no text)."""
    assert old in _STUBS[root]
    _STUBS[root] = _STUBS[root].replace(old, new)
    fake_venv(root, cli=_STUBS[root])


def git(repo: Path, *args: str) -> str:
    env = suite_env(
        os.environ,
        Path.home(),
        overrides={"HOME": str(repo), "PATH": os.environ["PATH"], "GIT_CONFIG_NOSYSTEM": "1"},
    )
    ident = ["-c", "user.name=t", "-c", "user.email=t@t", "-c", "init.defaultBranch=main"]
    return run_text(["git", *ident, "-C", str(repo), *args], env=env, check=True).stdout


def make_workspace(root: Path) -> Path:
    write_text(root / ".gitconfig", "[user]\n\tname = t\n\temail = t@t\n")  # HOME for rebase
    (root / ".dadaia/states").mkdir(parents=True)
    write_text(root / ".dadaia/states/spec_contexts.json", "{}")
    _stub_cli(root, {"main_repo": "r", "associated_repos": [], "gitflow": FLOW})
    repo = root / "repos/r"
    rel = repo / "specs/releases/0.5.0/rc-1"
    rel.mkdir(parents=True)
    git(repo, "init", "-q")
    write_text(
        rel / "SPEC.md",
        "# SPEC\n\n**Status:** Approved\n\n**Origin:** operator-demand\n\n## Bug window review\n",
    )
    write_text(
        rel / "PLAN.md",
        "# PLAN\n\n**Status:** Approved\n\n"
        "## As-is review\n\n"
        "| unit | today | bugs | verdict | why |\n"
        "|---|---|---|---|---|\n"
        "| worktree | current | 0 | KEEP | fixture |\n\n"
        "## DAG\n\n"
        "| job | wave | waits on | `W:` |\n"
        "|---|---|---|---|\n"
        "| Job 1 | 1 | — | `src/a.py` |\n",
    )
    tasks = rel / "tasks"
    tasks.mkdir()
    write_text(
        tasks / "job1.md",
        "# Job 1\n\n| task | AC | `W:` |\n|---|---|---|\n| J1.T1 | AC2.1 | `src/a.py` |\n",
    )
    state = {"schema": "release-state-v1", "release": "0.5.0", "phase": "IMPLEMENTATION",
             "defined": {"sha": "initial", "ts": "2026-10-09T09:00:00Z"},
             "implemented": None, "shipped": None, "log": []}  # fmt: skip
    write_text(rel.parent / "_RELEASE.json", json.dumps(state))
    write_text(repo / ".gitignore", "*.scratch\n__pycache__/\n")
    (repo / "scripts").mkdir()
    write_text(repo / "scripts/ci.py", CI)
    write_text(repo / "AGENTS.md", "verify: python scripts/ci.py job\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "init")
    git(repo, "branch", "feature/0.5.0")
    return root


def associate(root: Path, spec: str, slugs: tuple[str, ...] = ("a",)) -> None:
    """Repos *slugs* join `r`'s context with `feature/0.5.0` and no specs; `r`'s SPEC is *spec*."""
    _stub_cli(root, {"main_repo": "r", "associated_repos": [{"slug": s} for s in slugs],
                     "gitflow": FLOW})  # fmt: skip
    write_text(root / ".dadaia/states/spec_contexts.json", json.dumps({"contexts": [
        {"repo_slug": "r", "associated_repos": [{"slug": s} for s in slugs]}]}))  # fmt: skip
    for slug in slugs:
        (repo := root / "repos" / slug).mkdir()
        git(repo, "init", "-q")
        git(repo, "commit", "-q", "--allow-empty", "-m", "init")
        git(repo, "branch", "feature/0.5.0")
    spec_md = root / "repos/r/specs/releases/0.5.0/rc-1/SPEC.md"
    write_text(
        spec_md,
        f"# SPEC\n\n**Status:** {spec}\n\n**Origin:** operator-demand\n\n## Bug window review\n",
    )  # a SPEC `release.py check` passes
    git(root / "repos/r", "commit", "-qam", "spec", "--allow-empty")
    git(root / "repos/r", "branch", "-f", "feature/0.5.0")


def record_session(root: Path, session_id: str) -> None:
    """The live record a workspace hook leaves for *session_id*: its id and a fresh heartbeat."""
    session_store.write_session(
        root, session_id, {"session_id": session_id, "last_seen_at": clock.now_iso()}
    )


def run(
    root: Path, *args: str, input: str | None = None, session: str | None = None
) -> subprocess.CompletedProcess[str]:
    """`worktree.py *args*` from *root*; *session* is the harness session id the run carries (none
    by default: an operator terminal)."""
    env = suite_env(
        os.environ,
        Path.home(),
        overrides={
            "HOME": str(root),
            "PATH": os.environ["PATH"],
            "GIT_DIR": "/nonexistent",
            "GIT_CONFIG_NOSYSTEM": "1",
            "TZ": "Asia/Tokyo",  # a naive produced_at never orders by the local zone
            **({CLAUDE_SESSION_ENV_VAR: session} if session else {}),
        },
    )
    return run_text([sys.executable, str(SCRIPT), *args], cwd=root, env=env, input=input)


def registered_doctor(root: Path) -> DoctorService:
    """The doctor over *root* with context `c` (main repo `r`) ALIVE."""
    write_text(root / ".dadaia/states/spec_contexts.json", '{"contexts": []}')
    store = context_store(root / ".dadaia/states")
    store.save(SpecContextProject("c", ContextState.ALIVE, "r", "", "2026-09-30T00:00:00+00:00"))
    return DoctorService(store, GitSubprocessClient(), root)


def fixes(result: subprocess.CompletedProcess[str]) -> list[str]:
    return [line for line in result.stderr.splitlines() if line.startswith("fix: ")]


def commit(tree: Path, rel: str, text: str = "x = 1\n") -> str:
    (tree / rel).parent.mkdir(parents=True, exist_ok=True)
    write_text(tree / rel, text)
    git(tree, "add", rel)
    git(tree, "commit", "-q", "--allow-empty", "-m", rel)
    return git(tree, "rev-parse", "HEAD").strip()


def _parent(name: str) -> str:
    """The branch tree *name* is cut from, the work branch's prefix `feature/` (`base_of`)."""
    return str(load_owner("dd-gitflow-default", "_worktree_names").base_of(name, "feature/"))


def open_tree(root: Path, name: str) -> Path:
    """The tree *name* opened by `new`, which must succeed."""
    created = run(root, "new", "r", name)
    assert created.returncode == 0, created.stderr
    return root / "worktrees/r" / name


def diff_hash(root: Path, sha: str, name: str | None = None, repo: str = "r") -> str:
    """The oracle: sha256 (UTF-8) of `git diff-tree -r -z --full-index <merge-base> <sha>` in repo *repo*,
    the merge-base taken against the branch tree *name* is cut from; the work branch with no *name*."""
    checkout = root / "repos" / repo
    base = git(checkout, "merge-base", _parent(name) if name else "feature/0.5.0", sha).strip()
    diff = git(checkout, "diff-tree", "-r", "-z", "--full-index", base, sha)
    return hashlib.sha256(diff.encode("utf-8")).hexdigest()


def approve(
    root: Path,
    sha: str,
    *,
    name: str | None = None,
    verdict: str = "APPROVED",
    valid: bool = True,
    at: str = "T10:00:00Z",
    repo: str = "r",
) -> Path:
    """The reviewer's verdict as `verdict.py` writes it: a handoff naming *sha*, its diff bound over
    the base of tree *name* (the work branch with no *name*), emitted *at*."""
    file = f"2026-10-02{at.replace(':', '')}-dd-code-reviewer-{sha[:8]}-{verdict}.handoff.json"
    handoff = root / ".dadaia/states/verdicts/c" / file
    handoff.parent.mkdir(parents=True, exist_ok=True)
    body = {
        "agent": "dd-code-reviewer",
        "context": "c",
        "verdict": verdict,
        "verdict_reason": "r",
        "scope": f"wt/{name or NEW_JOB}@{sha}",
        "reviewed_sha": sha,
        "diff_sha256": diff_hash(root, sha, name, repo),
        "produced_at": f"2026-10-02{at}",
    }
    write_text(
        handoff, json.dumps({**body, **({"schema_version": "handoff-v1.2"} if valid else {})})
    )
    return handoff


def run_fix(root: Path, result: subprocess.CompletedProcess[str]) -> None:
    """Run the refusal's one `fix:` line as an agent would, from the workspace root."""
    (fix,) = fixes(result)
    command = fix.removeprefix("fix: ")
    env = suite_env(
        os.environ,
        Path.home(),
        overrides={"HOME": str(root), "GIT_CONFIG_NOSYSTEM": "1"},
    )
    run_bash(command, cwd=root, env=env, check=True)


def attempt(
    root: Path, files: dict[str, str], task_id: str = "", mv: tuple[str, str] = ("", "")
) -> tuple[str, subprocess.CompletedProcess[str]]:
    """Commit *files* (a `git mv` of *mv* first) in task `NEW_TASK` of `NEW_JOB` and try to merge
    it: (the commit, the merge's result). With *task_id* (`J<n>.T<m>`) the subject opens with it."""
    assert (tree := open_tree(root, NEW_TASK)).is_dir()
    if mv[0]:
        git(tree, "mv", *mv)
    for rel, text in files.items():
        (tree / rel).parent.mkdir(parents=True, exist_ok=True)
        write_text(tree / rel, text)
        git(tree, "add", rel)
    name = f"test({task_id}): {next(iter(files), mv[1])}" if task_id else next(iter(files), mv[1])
    git(tree, "commit", "-qm", name)
    return git(tree, "rev-parse", "HEAD").strip(), run(root, "merge", f"worktrees/r/{NEW_TASK}")


def land(root: Path, rel: str, text: str = "x = 1\n", task_id: str = "") -> str:
    """Commit *rel* in task `NEW_TASK` of `NEW_JOB` and merge it: a job branch takes code only so."""
    sha, merged = attempt(root, {rel: text}, task_id)
    assert merged.returncode == 0, merged.stderr
    return sha
