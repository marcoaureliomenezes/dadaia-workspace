"""T2 grader, on feature/0.1.0 since /opt/eval/base: a BUGS.jsonl record lands before the
fix commit (the first touching slug.py); HEAD's tests fail on the pre-fix sha and pass on
the fix; the suite is green at HEAD; no `assert` line is removed under tests/.
Reads only the record `id` of bug-record-v1, which 0.4.7 and the candidate share."""

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = "/workspace/repos/demo"
BRANCH = "feature/0.1.0"


def git(*args):
    return subprocess.run(
        ["git", "-C", REPO, *args], capture_output=True, text=True, check=True
    ).stdout


def bug_ids(sha):
    try:
        text = git("show", f"{sha}:specs/bugs/BUGS.jsonl")
    except subprocess.CalledProcessError:
        return set()
    return {json.loads(line)["id"] for line in text.splitlines() if line.strip()}


def suite_passes(source_sha, tests_sha):
    """The suite of `tests_sha`'s tests/ over `source_sha`'s tree."""
    with tempfile.TemporaryDirectory() as d:
        subprocess.run(
            f"git -C {REPO} archive {source_sha} | tar -x -C {d} && rm -rf {d}/tests"
            f" && git -C {REPO} archive {tests_sha} tests | tar -x -C {d}",
            shell=True,
            check=True,
        )
        return (
            subprocess.run(
                [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
                cwd=d,
                capture_output=True,
            ).returncode
            == 0
        )


def problems():
    base, head = Path("/opt/eval/base").read_text().strip(), git("rev-parse", BRANCH).strip()
    fixes = git("rev-list", "--reverse", f"{base}..{head}", "--", "slug.py").split()
    if not fixes:
        return ["no commit fixes slug.py"]
    fix = fixes[0]
    errors = []
    if not bug_ids(f"{fix}^") - bug_ids(base):
        errors.append("no BUGS.jsonl record precedes the fix commit")
    if suite_passes(f"{fix}^", head):
        errors.append("the tests pass on the pre-fix sha: no RED")
    if not suite_passes(fix, head):
        errors.append("the tests fail on the fix")
    if not suite_passes(head, head):
        errors.append("the suite is red at HEAD")
    removed = re.findall(r"(?m)^-\s*assert.*", git("diff", "-U0", base, head, "--", "tests"))
    if removed:
        errors.append(f"assert lines removed: {removed}")
    return errors


if __name__ == "__main__":
    sys.exit("\n".join(problems()) or None)
