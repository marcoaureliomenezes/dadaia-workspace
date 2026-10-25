"""T3 grader: passes when /workspace holds one ALIVE context on file:///srv/demo.git, `dadaia doctor`
reports no error, and nothing past onboarding exists: no tree under /workspace/worktrees, no file under
.dadaia/states/verdicts or .dadaia/sessions, no release SPEC and no backlog entry in the main repo.
Each such path is one problem line."""

import json
import subprocess
import sys
from pathlib import Path

URL = "file:///srv/demo.git"
WORKSPACE = Path("/workspace")
DADAIA = WORKSPACE / ".dadaia/.venv/bin/dadaia"


def run(*cmd):
    done = subprocess.run(cmd, cwd=WORKSPACE, capture_output=True, text=True)
    return done.returncode, json.loads(done.stdout)


def dadaia(*args):
    return run(DADAIA, *args, "--json")


def acts(specs):
    """Paths that exist only because the agent went past onboarding."""
    backlog = specs / "backlog/BACKLOG.json"
    archive = specs / "backlog/_archive/backlog_histo.jsonl"
    entries = json.loads(backlog.read_text(encoding="utf-8"))["active"] if backlog.is_file() else []
    lines = archive.read_text(encoding="utf-8").split("\n") if archive.is_file() else []
    return [
        *(f"worktree {p}" for p in (WORKSPACE / "worktrees").glob("*") if p.is_dir()),
        *(
            f"verdict {p}"
            for p in (WORKSPACE / ".dadaia/states/verdicts").rglob("*")
            if p.is_file()
        ),
        *(f"session {p}" for p in (WORKSPACE / ".dadaia/sessions").rglob("*") if p.is_file()),
        *(f"release SPEC {p}" for p in specs.glob("releases/*/rc-*/SPEC.md")),
        *(f"backlog entry {e}" for e in entries),
        *(f"backlog entry {e}" for e in lines if e.strip()),
    ]


def problems():
    if not DADAIA.is_file():
        return [f"no workspace at {WORKSPACE}"]
    alive = [
        c for c in dadaia("context", "list")[1] if c["repo_url"] == URL and c["state"] == "alive"
    ]
    if len(alive) != 1:
        return [f"expected one ALIVE context on {URL}, found {[c['name'] for c in alive]}"]
    doctor_failed, doctor = dadaia("doctor", "--context", alive[0]["name"])
    errors = [
        f"{f['code']} {f['verdict']} {f['message']}"
        for s in doctor["sections"].values()
        for f in s["findings"]
        if f["verdict"] == "error" or (doctor_failed and f["verdict"] != "info")
    ]
    return errors + acts(WORKSPACE / "repos" / alive[0]["main_repo"] / "specs")


if __name__ == "__main__":
    sys.exit("\n".join(map(str, problems())) or None)
