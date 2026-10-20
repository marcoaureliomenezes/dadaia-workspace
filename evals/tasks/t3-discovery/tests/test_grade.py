"""T3 grader: /workspace onboards file:///srv/demo.git (one ALIVE context, its specs initialized,
`dadaia doctor` with no error) and some BACKLOG.json of that repo or its lane trees holds an active entry.
Reads only fields 0.4.7 and the candidate share."""

import json
import subprocess
import sys
from pathlib import Path

URL = "file:///srv/demo.git"


def dadaia(*args):
    done = subprocess.run(
        ["/workspace/.dadaia/.venv/bin/dadaia", *args, "--json"],
        cwd="/workspace",
        capture_output=True,
        text=True,
    )
    return done.returncode, json.loads(done.stdout)


def problems():
    alive = [
        c["name"]
        for c in dadaia("context", "list")[1]
        if c["repo_url"] == URL and c["state"] == "alive"
    ]
    if len(alive) != 1:
        return [f"expected one ALIVE context on {URL}, found {alive}"]
    doctor_failed, doctor = dadaia("doctor", "--context", alive[0])
    errors = [
        f"{f['code']} {f['verdict']} {f['message']}"
        for s in doctor["sections"].values()
        for f in s["findings"]
        if f["verdict"] == "error" or (doctor_failed and f["verdict"] != "info")
    ]
    if not doctor["specs_dir"] or not Path(doctor["specs_dir"], "constitution.md").is_file():
        errors.append("specs not initialized")
    if not any(entry_in(p) for p in backlogs(alive[0])):
        errors.append("no backlog entry")
    return errors


def backlogs(name):
    return [
        *Path("/workspace/repos", name).glob("specs/backlog/BACKLOG.json"),
        *Path("/workspace/worktrees", name).glob("**/specs/backlog/BACKLOG.json"),
    ]


def entry_in(path):
    try:
        return bool(json.loads(path.read_text()).get("active"))
    except (OSError, ValueError, AttributeError):
        return False


if __name__ == "__main__":
    sys.exit("\n".join(map(str, problems())) or None)
