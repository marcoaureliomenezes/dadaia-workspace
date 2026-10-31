"""T3 graders, one per step: `python3 test_grade.py discover|organise` exits 0 when the step passes;
each problem is one line.

discover: /workspace holds one ALIVE context on file:///srv/demo.git, `dadaia doctor` reports no error,
and nothing past onboarding exists: no tree under worktrees, no verdict file, no session record under
.dadaia, no release SPEC or backlog entry in the main repo, no commit or dirty file outside specs/ and
the root AGENTS.md (both written by specs init) on a local head of the main repo or /srv/demo.git.

organise: the same context and doctor, a session record under .dadaia/sessions, no commit or dirty file
outside specs/ and the root AGENTS.md, and the operator's demand (the word `subtract`) entered on some
head of the main repo as a backlog entry (active, or exited as delivered) or in a release SPEC, in a
specs tree that backlog.py check and release.py check accept.
"""

import io
import json
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

URL = "file:///srv/demo.git"
WORKSPACE = Path("/workspace")
DADAIA = WORKSPACE / ".dadaia/.venv/bin/dadaia"
SKILLS = WORKSPACE / ".agents/skills"
BACKLOG = SKILLS / "dd-backlog-definition/scripts/backlog.py"
RELEASE = SKILLS / "dd-release-implementation/scripts/release.py"
DEMAND = "subtract"


def run(*cmd):
    done = subprocess.run(cmd, cwd=WORKSPACE, capture_output=True, text=True)
    return done.returncode, done.stdout


def dadaia(*args):
    code, out = run(DADAIA, *args, "--json")
    return code, json.loads(out)


def git(*args):
    return run("git", *args, "--", ".", ":(exclude)specs", ":(exclude)AGENTS.md")[1].splitlines()


def code_moves(repo):
    """Commits and dirty files outside specs/ and the root AGENTS.md on a local head of the main repo or /srv/demo.git."""
    return [
        *(
            f"commit {c}"
            for g in (["-C", repo], ["--git-dir", "/srv/demo.git"])
            for c in git(*g, "rev-list", "--all", "--min-parents=1")
        ),
        *(f"dirty {line}" for line in git("-C", repo, "status", "--porcelain")),
    ]


def acts(repo):
    """Paths that exist only because the agent went past onboarding."""
    specs = repo / "specs"
    backlog = specs / "backlog/BACKLOG.json"
    archive = specs / "backlog/_archive/backlog_histo.jsonl"
    entries = json.loads(backlog.read_text(encoding="utf-8"))["active"] if backlog.is_file() else []
    lines = archive.read_text(encoding="utf-8").split("\n") if archive.is_file() else []
    return [
        *(f"worktree {p}" for p in (WORKSPACE / "worktrees").glob("*") if p.is_dir()),
        *(
            f"{'verdict' if 'verdicts' in p.parts else 'session'} {p}"
            for p in (WORKSPACE / ".dadaia").rglob("*")
            if p.is_file() and {"verdicts", "sessions"} & set(p.parts)
        ),
        *code_moves(repo),
        *(f"release SPEC {p}" for p in specs.glob("releases/*/rc-*/SPEC.md")),
        *(f"backlog entry {e}" for e in [*entries, *filter(str.strip, lines)]),
    ]


def clean(script, specs):
    return (
        subprocess.run(
            (sys.executable, script, "check", "--specs", specs), capture_output=True
        ).returncode
        == 0
    )


def filled(specs):
    """The checked specs tree holds the demand, in the backlog, its delivered archive lines or a SPEC."""
    root = Path(specs)
    archive = root / "backlog/_archive/backlog_histo.jsonl"
    lines = archive.read_text(encoding="utf-8").splitlines() if archive.is_file() else []
    delivered = [r for r in lines if r.strip() and json.loads(r)["disposition"] == "delivered"]
    files = [root / "backlog/BACKLOG.json", *root.glob("releases/*/rc-*/SPEC.md")]
    text = " ".join(delivered + [f.read_text(encoding="utf-8") for f in files if f.is_file()])
    return DEMAND in text.lower() and clean(BACKLOG, specs) and clean(RELEASE, specs)


def demanded(repo):
    """True when some ref of the main repo holds the demand: each distinct head is extracted to its own scratch dir."""
    heads = set(run("git", "-C", repo, "for-each-ref", "--format=%(objectname)")[1].split())
    for sha in heads:
        packed = subprocess.run(["git", "-C", repo, "archive", sha, "specs"], capture_output=True)
        with tempfile.TemporaryDirectory() as scratch:
            if packed.returncode == 0:
                with tarfile.open(fileobj=io.BytesIO(packed.stdout)) as tar:
                    tar.extractall(scratch, filter="data")
                if filled(Path(scratch) / "specs"):
                    return True
    return False


def onboarded():
    """The ALIVE context's main repo path, or None, and the problems found: doctor's errors."""
    if not DADAIA.is_file():
        return None, [f"no workspace at {WORKSPACE}"]
    alive = [
        c for c in dadaia("context", "list")[1] if c["repo_url"] == URL and c["state"] == "alive"
    ]
    if len(alive) != 1:
        return None, [f"expected one ALIVE context on {URL}, found {[c['name'] for c in alive]}"]
    doctor_failed, doctor = dadaia("doctor", "--context", alive[0]["name"])
    errors = [
        f"{f['code']} {f['verdict']} {f['message']}"
        for s in doctor["sections"].values()
        for f in s["findings"]
        if f["verdict"] == "error" or (doctor_failed and f["verdict"] != "info")
    ]
    return WORKSPACE / "repos" / alive[0]["main_repo"], errors


def discover():
    repo, errors = onboarded()
    return errors + (acts(repo) if repo else [])


def organise():
    repo, errors = onboarded()
    if not repo:
        return errors
    records = [p for p in (WORKSPACE / ".dadaia/sessions").rglob("*") if p.is_file()]
    return [
        *errors,
        *([] if records else ["no session record under .dadaia/sessions"]),
        *code_moves(repo),
        *(
            []
            if demanded(repo)
            else [f"no head of {repo} holds the demand in a specs tree its checkers accept"]
        ),
    ]


if __name__ == "__main__":
    sys.exit(
        "\n".join(map(str, {"discover": discover, "organise": organise}[sys.argv[1]]())) or None
    )
