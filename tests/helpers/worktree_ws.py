"""A tmp workspace for `worktree.py` tests: one repo `r` on `main` with an Approved 0.5.0 rc-1
trio, a valid `_RELEASE.json`, a `scripts/ci.py` whose level L fails iff the tree holds
`RED-<L>`, and `feature/0.5.0`; its `verify:` lines declare it, and a stub CLI in the fake venv's
scripts dir (`cli_path`) standing for the two reads the script makes — `context list --json` (gitflow `dev` as integration, so a
hardcoded `main`/`develop` fails) and `reports validate` (valid iff `schema_version`)."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.core.platform import PLATFORM
from dadaia_workspace.features.spec_context.doctor import DoctorService
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
from tests.fixtures.harness_env import run_bash, suite_env
from tests.fixtures.stores import context_store, fake_venv

SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "dadaia_workspace/public/skills/dd-gitflow-default/scripts/worktree.py"
)
FLOW = {"principal": "trunk", "integration": "dev", "work": "feature/"}
#: The repo's gate (ADR 0190): prints its argv; level L fails iff the tree holds `RED-<L>`.
CI = 'import pathlib, sys\nprint("ci", *sys.argv[1:])\nsys.exit(pathlib.Path("RED-" + sys.argv[1]).exists())\n'
JOB, TASK = "0.5.0-rc1/j1", "0.5.0-rc1/j1--J1.S1.T1"
_CLI = """#!python
import json, sys
args = sys.argv[1:]
if args[:2] == ["context", "list"]:
    print({rows!r})
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


def cli_path(root: Path) -> Path:
    """Where the stub CLI lives: the fake venv's scripts dir, `dadaia` plus `PLATFORM`'s suffix."""
    return root / ".dadaia/.venv" / PLATFORM.venv_scripts_dir / f"dadaia{PLATFORM.venv_exe_suffix}"


_STUBS: dict[Path, str] = {}  # each workspace's stub source: on Windows the stub is an .exe


def _stub_cli(root: Path, *listed: dict[str, object]) -> None:
    """The `dadaia` stub over *listed*, placed at `cli_path` by `fake_venv` (startable per platform)."""
    _STUBS[root] = _CLI.format(rows=json.dumps(list(listed)))
    fake_venv(root, cli=_STUBS[root])


def patch_cli(root: Path, old: str, new: str) -> None:
    """Re-stub *root*'s CLI with *old* replaced by *new* in its source (the `.exe` is no text)."""
    assert old in _STUBS[root]
    _STUBS[root] = _STUBS[root].replace(old, new)
    fake_venv(root, cli=_STUBS[root])


def git(repo: Path, *args: str) -> str:
    env = {
        **suite_env(os.environ, Path.home()),
        "HOME": str(repo),
        "PATH": os.environ["PATH"],
        "GIT_CONFIG_NOSYSTEM": "1",
    }
    ident = ["-c", "user.name=t", "-c", "user.email=t@t", "-c", "init.defaultBranch=main"]
    out = subprocess.run(
        ["git", *ident, "-C", str(repo), *args], env=env, check=True, capture_output=True, text=True
    )
    return out.stdout


def make_workspace(root: Path) -> Path:
    (root / ".gitconfig").write_text("[user]\n\tname = t\n\temail = t@t\n")  # HOME for rebase
    (root / ".dadaia/states").mkdir(parents=True)
    (root / ".dadaia/states/spec_contexts.json").write_text("{}")
    _stub_cli(root, {"main_repo": "r", "associated_repos": [], "gitflow": FLOW})
    repo = root / "repos/r"
    rel = repo / "specs/releases/0.5.0/rc-1"
    rel.mkdir(parents=True)
    git(repo, "init", "-q")
    for doc in ("SPEC", "PLAN", "TASKS"):
        (rel / f"{doc}.md").write_text(
            f"# {doc}\n\n**Status:** Approved\n\n**Origin:** operator-demand\n"
            + ("\n## Bug window review\n" if doc == "SPEC" else "")
        )
    state = {"schema": "release-state-v1", "release": "0.5.0", "phase": "DEFINITION",
             "defined": None, "implemented": None, "shipped": None, "log": []}  # fmt: skip
    (rel.parent / "_RELEASE.json").write_text(json.dumps(state))
    (repo / ".gitignore").write_text("*.scratch\n__pycache__/\n")
    (repo / "scripts").mkdir()
    (repo / "scripts/ci.py").write_text(CI)
    (repo / "AGENTS.md").write_text(
        "verify: python scripts/ci.py job\n"
        + "".join(f"verify-{lv}: python scripts/ci.py {lv}\n" for lv in ("task", "stage"))
    )
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "init")
    git(repo, "branch", "feature/0.5.0")
    return root


def associate(root: Path, spec: str) -> None:
    """Repo `a` joins `r`'s context with `feature/0.5.0` and no specs; `r`'s SPEC is *spec*."""
    _stub_cli(root, {"main_repo": "r", "associated_repos": [{"slug": "a"}], "gitflow": FLOW})
    (repo := root / "repos/a").mkdir()
    git(repo, "init", "-q")
    git(repo, "commit", "-q", "--allow-empty", "-m", "init")
    git(repo, "branch", "feature/0.5.0")
    spec_md = root / "repos/r/specs/releases/0.5.0/rc-1/SPEC.md"
    spec_md.write_text(f"**Status:** {spec}\n")
    git(root / "repos/r", "commit", "-qam", "spec")
    git(root / "repos/r", "branch", "-f", "feature/0.5.0")


def run(root: Path, *args: str, input: str | None = None) -> subprocess.CompletedProcess[str]:
    env = {
        **suite_env(os.environ, Path.home()),
        "HOME": str(root),
        "PATH": os.environ["PATH"],
        "GIT_DIR": "/nonexistent",
        "GIT_CONFIG_NOSYSTEM": "1",
        "TZ": "Asia/Tokyo",  # a naive produced_at never orders by the local zone
    }
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        input=input,
    )


def registered_doctor(root: Path) -> DoctorService:
    """The doctor over *root* with context `c` (main repo `r`) ALIVE."""
    (root / ".dadaia/states/spec_contexts.json").write_text('{"contexts": []}')
    store = context_store(root / ".dadaia/states")
    store.save(SpecContextProject("c", ContextState.ALIVE, "r", "", "2026-09-30T00:00:00+00:00"))
    return DoctorService(store, GitSubprocessClient(), root)


def fixes(result: subprocess.CompletedProcess[str]) -> list[str]:
    return [line for line in result.stderr.splitlines() if line.startswith("fix: ")]


def commit(tree: Path, rel: str, text: str = "x = 1\n") -> str:
    (tree / rel).parent.mkdir(parents=True, exist_ok=True)
    (tree / rel).write_text(text)
    git(tree, "add", rel)
    git(tree, "commit", "-qm", rel)
    return git(tree, "rev-parse", "HEAD").strip()


def diff_hash(root: Path, sha: str) -> str:
    """The oracle: sha256 (UTF-8) of `git diff-tree -r -z --full-index <merge-base> <sha>` in `r`,
    the merge-base taken against `feature/0.5.0`."""
    repo = root / "repos/r"
    base = git(repo, "merge-base", "feature/0.5.0", sha).strip()
    diff = git(repo, "diff-tree", "-r", "-z", "--full-index", base, sha)
    return hashlib.sha256(diff.encode("utf-8")).hexdigest()


def approve(
    root: Path,
    sha: str,
    *,
    verdict: str = "APPROVED",
    valid: bool = True,
    at: str = "T10:00:00Z",
) -> Path:
    """The reviewer's verdict as `verdict.py` writes it: a handoff naming *sha*, emitted *at*."""
    name = f"2026-10-02{at.replace(':', '')}-dd-code-reviewer-{sha[:8]}-{verdict}.handoff.json"
    handoff = root / ".dadaia/handoff/c" / name
    handoff.parent.mkdir(parents=True, exist_ok=True)
    body = {
        "agent": "dd-code-reviewer",
        "verdict": verdict,
        "scope": f"wt/0.5.0-rc1/j1@{sha}",
        "reviewed_sha": sha,
        "diff_sha256": diff_hash(root, sha),
        "produced_at": f"2026-10-02{at}",
    }
    handoff.write_text(json.dumps({**body, **({"schema_version": "1.2"} if valid else {})}))
    return handoff


def run_fix(root: Path, result: subprocess.CompletedProcess[str]) -> None:
    """Run the refusal's one `fix:` line as an agent would, from the workspace root."""
    (fix,) = fixes(result)
    command = fix.removeprefix("fix: ")
    env = {**os.environ, "HOME": str(root), "GIT_CONFIG_NOSYSTEM": "1"}
    run_bash(command, cwd=root, env=env, check=True)


def attempt(
    root: Path, files: dict[str, str], task_id: str = "", mv: tuple[str, str] = ("", "")
) -> tuple[str, subprocess.CompletedProcess[str]]:
    """Commit *files* (a `git mv` of *mv* first) in a task of `JOB` and try to merge it:
    (the commit, the merge's result). With *task_id* (`J1.S2.T1`) the task tree is named for
    it and the subject opens with it."""
    task = f"0.5.0-rc1/j1--{task_id}" if task_id else TASK
    assert run(root, "new", "r", task).returncode == 0
    tree = root / "worktrees/r" / task
    if mv[0]:
        git(tree, "mv", *mv)
    for rel, text in files.items():
        (tree / rel).parent.mkdir(parents=True, exist_ok=True)
        (tree / rel).write_text(text)
        git(tree, "add", rel)
    name = f"test({task_id}): {next(iter(files), mv[1])}" if task_id else next(iter(files), mv[1])
    git(tree, "commit", "-qm", name)
    return git(tree, "rev-parse", "HEAD").strip(), run(root, "merge", f"worktrees/r/{task}")


def land(root: Path, rel: str, text: str = "x = 1\n", task_id: str = "") -> str:
    """Commit *rel* in task `TASK` of `JOB` and merge it: a job branch takes code only so."""
    sha, merged = attempt(root, {rel: text}, task_id)
    assert merged.returncode == 0, merged.stderr
    return sha
