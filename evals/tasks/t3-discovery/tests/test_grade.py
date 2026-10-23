"""T3 grader: /workspace onboards file:///srv/demo.git (one ALIVE context, its specs initialized,
`dadaia doctor` with no error) and the repo's own specs, or a lane tree's, show the operator's
demand entered as work, in a backlog and release that pass the library's checks. Reads only the verbs and fields the candidate offers."""

import json
import subprocess
import sys
from pathlib import Path

URL = "file:///srv/demo.git"
WORKSPACE = Path("/workspace")
DADAIA = WORKSPACE / ".dadaia/.venv/bin/dadaia"
BACKLOG = WORKSPACE / ".agents/skills/dd-backlog-definition/scripts/backlog.py"
DEMAND = "subtract"
RELEASE = WORKSPACE / ".agents/skills/dd-release-implementation/scripts/release.py"


def run(*cmd):
    done = subprocess.run(cmd, cwd=WORKSPACE, capture_output=True, text=True)
    return done.returncode, json.loads(done.stdout)


def dadaia(*args):
    return run(DADAIA, *args, "--json")


def clean(script, specs):
    cmd = (sys.executable, script, "check", "--specs", specs)
    return subprocess.run(cmd, capture_output=True).returncode == 0


def filled(specs):
    """The checked specs tree holds the operator's demand, in the backlog, its archive or a SPEC."""
    root = Path(specs)
    archive = root / "backlog/_archive/backlog_histo.jsonl"
    lines = (
        archive.read_text(encoding="utf-8").splitlines(keepends=True) if archive.is_file() else []
    )
    delivered = [
        row for row in lines if row.strip() and json.loads(row)["disposition"] == "delivered"
    ]
    files = [root / "backlog/BACKLOG.json", *root.glob("releases/*/rc-*/SPEC.md")]
    text = "".join(
        delivered + [f.read_text(encoding="utf-8") for f in files if f.is_file()]
    ).lower()
    return clean(BACKLOG, specs) and clean(RELEASE, specs) and DEMAND in text


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
        errors.append("no valid backlog entry or SPEC")
    return errors


if __name__ == "__main__":
    sys.exit("\n".join(map(str, problems())) or None)
