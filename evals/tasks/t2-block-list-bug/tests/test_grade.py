"""T2 grader, on feature/0.1.0 since /opt/eval/base: a BUGS.jsonl record lands before the
fix commit (the first touching slug.py); HEAD's tests fail on the pre-fix sha and pass on
the fix; the suite is green at HEAD; every assertion node under tests/ at the base (`assert`,
`assert*` / `raises` / `warns` calls) is still there at HEAD, unedited, wherever it moved."""

import ast
import json
import subprocess
import sys
import tempfile
from collections import Counter
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


def assertions(sha):
    """Multiset of `ast.dump`s of every assertion node under tests/ at `sha`."""
    found = Counter()
    for path in git("ls-tree", "-r", "--name-only", sha, "tests").split():
        if not path.endswith(".py"):
            continue
        for n in ast.walk(ast.parse(git("show", f"{sha}:{path}"))):
            func = getattr(n, "func", None)
            name = getattr(func, "attr", None) or getattr(func, "id", "")
            if isinstance(n, ast.Assert) or name.startswith(("assert", "raises", "warns")):
                found[ast.dump(n)] += 1
    return found


def weakened(base, head):
    """Assertions at `base` that `head` no longer holds, edited or removed."""
    return list((assertions(base) - assertions(head)).elements())


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
    base, head = (
        Path("/opt/eval/base").read_text(encoding="utf-8").strip(),
        git("rev-parse", BRANCH).strip(),
    )
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
    if weaker := weakened(base, head):
        errors.append(f"assertions removed or edited: {[w[:120] for w in weaker]}")
    return errors


if __name__ == "__main__":
    sys.exit("\n".join(problems()) or None)
