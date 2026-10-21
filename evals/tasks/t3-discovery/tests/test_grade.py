"""T3 grader: /workspace onboards file:///srv/demo.git (one ALIVE context, its specs initialized,
`dadaia doctor` with no error) and the repo's own specs, or a lane tree's, show work entered: a
backlog that passes the library's check with an active entry, or a release candidate whose SPEC
passes the library's release check. Reads only the verbs and fields the candidate offers."""

import json
import subprocess
import sys
from pathlib import Path

URL = "file:///srv/demo.git"
WORKSPACE = Path("/workspace")
DADAIA = WORKSPACE / ".dadaia/.venv/bin/dadaia"
BACKLOG = WORKSPACE / ".agents/skills/dd-backlog-definition/scripts/backlog.py"
RELEASE = WORKSPACE / ".agents/skills/dd-release-implementation/scripts/release.py"


def run(*cmd):
    done = subprocess.run(cmd, cwd=WORKSPACE, capture_output=True, text=True)
    return done.returncode, json.loads(done.stdout)


def dadaia(*args):
    return run(DADAIA, *args, "--json")


def clean(script, specs):
    failed, findings = run(sys.executable, script, "check", "--specs", specs, "--json")
    return not (failed or findings)


def filled(specs):
    """The specs tree enters work by an active backlog entry or by a SPEC, each judged by its checker."""
    if (
        clean(BACKLOG, specs)
        and json.loads(Path(specs, "backlog/BACKLOG.json").read_text(encoding="utf-8"))["active"]
    ):
        return True
    return any(Path(specs, "releases").glob("*/rc-*/SPEC.md")) and clean(RELEASE, specs)


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
