"""T1 grader: /workspace onboards file:///srv/demo.git — one ALIVE context, its specs
initialized, `dadaia doctor` with no error. Reads only fields 0.4.7 and the candidate share."""

import json
import subprocess
import sys
from pathlib import Path

URL = "file:///srv/demo.git"


def dadaia(*args):
    out = subprocess.run(
        ["/workspace/.dadaia/.venv/bin/dadaia", *args, "--json"],
        cwd="/workspace",
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return json.loads(out)


def problems():
    alive = [
        c["name"]
        for c in dadaia("context", "list")
        if c["repo_url"] == URL and c["state"] == "alive"
    ]
    if len(alive) != 1:
        return [f"expected one ALIVE context on {URL}, found {alive}"]
    doctor = dadaia("doctor", "--context", alive[0])
    errors = [
        f for s in doctor["sections"].values() for f in s["findings"] if f["verdict"] == "error"
    ]
    if not doctor["specs_dir"] or not Path(doctor["specs_dir"], "constitution.md").is_file():
        errors.append("specs not initialized")
    return errors


if __name__ == "__main__":
    sys.exit("\n".join(map(str, problems())) or None)
