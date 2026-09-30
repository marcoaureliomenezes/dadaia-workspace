"""A tmp workspace for `worktree.py` tests: one repo `r` on `main` with an Approved 0.5.0 trio
and `feature/0.5.0`, and a stub CLI at `.dadaia/.venv/bin/dadaia` standing for the two
reads the script makes — `context list --json` (gitflow `dev` as integration, so a
hardcoded `main`/`develop` fails) and `reports validate` (valid iff `schema_version`)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.features.spec_context.doctor import DoctorService
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
from tests.fixtures.stores import context_store, workspace_cli

SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "dadaia_workspace/public/skills/dd-gitflow-default/scripts/worktree.py"
)
FLOW = {"principal": "trunk", "integration": "dev", "work": "feature/"}


def git(repo: Path, *args: str) -> str:
    env = {"HOME": str(repo), "PATH": os.environ["PATH"], "GIT_CONFIG_NOSYSTEM": "1"}
    ident = ["-c", "user.name=t", "-c", "user.email=t@t", "-c", "init.defaultBranch=main"]
    out = subprocess.run(
        ["git", *ident, "-C", str(repo), *args], env=env, check=True, capture_output=True, text=True
    )
    return out.stdout


def make_workspace(root: Path) -> Path:
    (root / ".gitconfig").write_text("[user]\n\tname = t\n\temail = t@t\n")  # HOME for rebase
    (root / ".dadaia/states").mkdir(parents=True)
    (root / ".dadaia/states/spec_contexts.json").write_text("{}")
    workspace_cli(root, {"main_repo": "r", "associated_repos": [], "gitflow": FLOW})
    repo = root / "repos/r"
    rel = repo / "specs/releases/0.5.0"
    rel.mkdir(parents=True)
    git(repo, "init", "-q")
    for doc in ("SPEC", "PLAN", "TASKS"):
        (rel / f"{doc}.md").write_text(f"# {doc}\n\n**Status:** Approved\n")
    (repo / ".gitignore").write_text("*.scratch\n__pycache__/\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "init")
    git(repo, "branch", "feature/0.5.0")
    return root


def run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {
        "HOME": str(root),
        "PATH": os.environ["PATH"],
        "GIT_DIR": "/nonexistent",
        "GIT_CONFIG_NOSYSTEM": "1",
    }
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], cwd=root, env=env, capture_output=True, text=True
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


def approve(root: Path, sha: str, *, verdict: str = "APPROVED", valid: bool = True) -> Path:
    """The reviewer's verdict as the main thread writes it: a handoff naming *sha*."""
    handoff = root / ".dadaia/handoff/c" / f"{sha[:8]}-{verdict}-dd-code-reviewer.handoff.json"
    handoff.parent.mkdir(parents=True, exist_ok=True)
    body = {"agent": "dd-code-reviewer", "verdict": verdict, "scope": f"wt/0.5.0a-impl@{sha}"}
    handoff.write_text(json.dumps({**body, **({"schema_version": "1.2"} if valid else {})}))
    return handoff


def run_fix(root: Path, result: subprocess.CompletedProcess[str]) -> None:
    """Run the refusal's one `fix:` line as an agent would, from the workspace root."""
    (fix,) = fixes(result)
    command = fix.removeprefix("fix: ").replace("python3 ", f"{sys.executable} ", 1)
    env = {"HOME": str(root), "PATH": "/usr/bin:/bin", "GIT_CONFIG_NOSYSTEM": "1"}
    subprocess.run(command, shell=True, cwd=root, env=env, check=True, capture_output=True)
