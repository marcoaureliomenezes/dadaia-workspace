"""T3 grader: /workspace onboards file:///srv/demo.git (one ALIVE context, its specs initialized,
`dadaia doctor` with no error) and the repo's own backlog, or a lane tree's, passes the library's
backlog check with an active entry. Reads only the verbs and fields the candidate offers."""

import json
import subprocess
import sys
from pathlib import Path

URL = "file:///srv/demo.git"
WORKSPACE = Path("/workspace")
DADAIA = WORKSPACE / ".dadaia/.venv/bin/dadaia"
BACKLOG = WORKSPACE / ".agents/skills/dd-backlog-definition/scripts/backlog.py"


def run(*cmd):
    done = subprocess.run(cmd, cwd=WORKSPACE, capture_output=True, text=True)
    return done.returncode, json.loads(done.stdout)


def dadaia(*args):
    return run(DADAIA, *args, "--json")


def filled(specs):
    """The backlog under `specs` passes the library's check and holds an active entry."""
    failed, findings = run(sys.executable, BACKLOG, "check", "--specs", specs, "--json")
    if failed or findings:
        return False
    return bool(
        json.loads(Path(specs, "backlog/BACKLOG.json").read_text(encoding="utf-8"))["active"]
    )


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
    if not doctor["specs_dir"] or not Path(doctor["specs_dir"], "constitution.md").is_file():
        errors.append("specs not initialized")
    repo = alive[0]["main_repo"]
    trees = [
        WORKSPACE / "repos" / repo / "specs",
        *(Path(w["path"], "specs") for w in dadaia("worktree", "list")[1] if w["repo"] == repo),
    ]
    if not any(filled(t) for t in trees):
        errors.append("no valid backlog entry")
    return errors


if __name__ == "__main__":
    sys.exit("\n".join(map(str, problems())) or None)
