"""The eval deploy gate: `gate.py HEAD_SHA`.

Passes (exit 0, prints the evaluated sha and its run URL) when the newest successful eval run
dispatched by hand or on schedule evaluated a commit E whose diff to HEAD_SHA is release
bookkeeping only: the release's _RELEASE.json, CHANGELOG.md, the release-please manifest, and
pyproject.toml lines that are `version = ...`. Otherwise it exits 1 and prints one
`fix: Agent action:` line, never a traceback. The repository is $GITHUB_REPOSITORY.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys

_WORK = "feature/"  # specs/constitution.md, gitflow.work
_SHA = re.compile(r"[0-9a-f]{40}")
_RELEASE_ID = re.compile(r"\d+(\.\d+)*")
_VERSION = re.compile(r"version = ")


def _git(*argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *argv], capture_output=True, text=True, errors="replace")


def _release_id(head: str) -> str | None:
    done = _git("ls-tree", "-d", "--name-only", head, "specs/releases/")
    ids = [name.rsplit("/", 1)[-1] for name in done.stdout.splitlines()]
    ids = [i for i in ids if _RELEASE_ID.fullmatch(i)]
    return ids[0] if done.returncode == 0 and len(ids) == 1 else None


def _runs() -> list[dict]:
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    path = f"repos/{repo}/actions/workflows/eval.yml/runs?status=success&per_page=100"
    try:
        done = subprocess.run(["gh", "api", path], capture_output=True, text=True, errors="replace")
        body = json.loads(done.stdout) if done.returncode == 0 else {}
    except (OSError, ValueError):
        return []
    runs = body.get("workflow_runs", []) if isinstance(body, dict) else []
    return [
        r
        for r in runs
        if isinstance(r, dict)
        and r.get("event") in ("workflow_dispatch", "schedule")
        and r.get("conclusion") == "success"
    ]


def _version_only(sha: str, head: str) -> bool:
    body = _git("diff", "-U0", "--no-color", sha, head, "--", "pyproject.toml").stdout
    changed = [ln[1:] for ln in body.partition("\n@@")[2].splitlines() if ln[:1] in ("+", "-")]
    return all(_VERSION.match(line) for line in changed)


def _bookkeeping_only(sha: str, head: str, rid: str) -> bool:
    listed = _git("diff", "--name-only", sha, head, "--")
    allowed = {
        f"specs/releases/{rid}/_RELEASE.json",
        "CHANGELOG.md",
        ".release-please-manifest.json",
        "pyproject.toml",
    }
    if listed.returncode != 0 or not set(listed.stdout.splitlines()) <= allowed:
        return False
    return _version_only(sha, head)


def main(head: str) -> int:
    rid = _release_id(head)
    if rid is None:
        print("fix: Operator action: the head must hold exactly one specs/releases/<id>/ directory")
        return 1
    for run in _runs():
        sha = run.get("head_sha")
        if isinstance(sha, str) and _SHA.fullmatch(sha) and _bookkeeping_only(sha, head, rid):
            print(f"{sha} {run.get('html_url', '')}")
            return 0
    print(
        f"fix: Agent action: run the eval pipeline on the work branch: gh workflow run eval.yml --ref {_WORK}{rid}"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
