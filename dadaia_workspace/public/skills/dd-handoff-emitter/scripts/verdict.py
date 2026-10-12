#!/usr/bin/env python3
"""Write the reviewer's verdict handoff, bound to the sha and diff it judged."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
#: One bootstrap statement: the kernel, at the front.
sys.path[:0] = [str(Path(__file__).resolve().parents[2] / "dd-bug-resolution" / "scripts")]

import _clock
import _ledger
import _root
from _handoffs import REVIEWER, reviewer_records

_CONTEXT = r"^[a-z0-9][a-z0-9-]*$"
_WORKTREE = Path(__file__).resolve().parents[2] / "dd-gitflow-default" / "scripts" / "worktree.py"
_OWN = (
    "agent", "verdict", "verdict_reason", "reviewed_sha", "diff_sha256",
    "scope", "produced_at", "context", "schema_version",
)  # fmt: skip


def _refuse(message: str) -> int:
    print(f"[error] {message}", file=sys.stderr)
    return 1


def _body(text: str) -> dict[str, object] | str:
    """The stdin object, or the reason it is refused."""
    try:
        body = json.loads(text)
    except ValueError:
        return "stdin is not JSON"
    if not isinstance(body, dict):
        return "stdin is not a JSON object"
    if taken := [k for k in _OWN if k in body]:
        return f"stdin sets keys verdict.py owns: {', '.join(taken)}"
    return body


def _stats(argv: list[str]) -> int:
    """Count the verdict sequences of one candidate: a tree name's verdicts up to an APPROVED."""
    parser = argparse.ArgumentParser(prog="verdict.py stats", description=_stats.__doc__)
    parser.add_argument("rc", help="<M.m.p>-rc<N>")
    rc = parser.parse_args(argv).rc
    root = _root.workspace_of(Path.cwd())
    if root is None:
        return _refuse("no workspace above the current directory")
    by_tree: dict[str, list[tuple[str, str]]] = {}
    for _path, data in reviewer_records(root):
        branch = str(data.get("scope", "")).partition("@")[0]
        if branch.startswith(f"wt/{rc}/"):
            by_tree.setdefault(branch, []).append(
                (str(data.get("produced_at")), str(data.get("verdict")))
            )
    sequences = rejected_first = verdicts = rejected = 0
    for trail in by_tree.values():
        opening = True
        for _at, verdict in sorted(trail):
            verdicts += 1
            rejected += verdict == "REJECTED"
            if opening:
                sequences += 1
                rejected_first += verdict == "REJECTED"
            opening = verdict == "APPROVED"
    print(
        f"sequences {sequences}\nverdicts {verdicts}\nrejected {rejected}\nfirst_pass_rejected {rejected_first}/{sequences}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["stats"]:
        return _stats(argv[1:])
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path")
    parser.add_argument("--sha", required=True)
    parser.add_argument("--context", required=True)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--verdict", required=True, choices=("APPROVED", "REJECTED"))
    parser.add_argument("--reason", required=True)
    args = parser.parse_args(argv)
    slug = _ledger.load_schema("backlog-v1")["$defs"]["slug"]["pattern"]
    for name, pattern in (("context", _CONTEXT), ("slug", slug)):
        if not re.fullmatch(pattern, getattr(args, name)):
            return _refuse(f"--{name} must match {pattern}")
    body = _body(sys.stdin.read())
    if isinstance(body, str):
        return _refuse(body)
    done = subprocess.run(
        [sys.executable, str(_WORKTREE), "hash", args.path, "--sha", args.sha],
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
    )  # fmt: skip
    if done.returncode:
        sys.stderr.write(done.stderr)
        return done.returncode
    bound = json.loads(done.stdout)
    now = _clock.now_iso()
    handoff = {
        "schema_version": "handoff-v1.2",
        "agent": REVIEWER,
        "context": args.context,
        "produced_at": now,
        "verdict": args.verdict,
        "verdict_reason": args.reason,
        "scope": bound["scope"],
        "reviewed_sha": bound["reviewed_sha"],
        "diff_sha256": bound["diff_sha256"],
        **body,
    }
    out = Path(bound["root"]) / ".dadaia/handoff" / args.context
    out.mkdir(parents=True, exist_ok=True)
    target = out / f"{now.replace(':', '')}-{REVIEWER}-{args.slug}.handoff.json"
    try:
        with target.open("x", encoding="utf-8") as fh:
            fh.write(json.dumps(handoff, indent=2) + "\n")
    except FileExistsError:
        return _refuse(f"{target.name} exists; rerun in a second")
    print(target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
