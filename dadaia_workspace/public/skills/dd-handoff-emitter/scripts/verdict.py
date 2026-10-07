"""Write the reviewer's verdict handoff, bound to the sha and diff it judged (ADR 0218)."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

_SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path")
    parser.add_argument("--sha", required=True)
    parser.add_argument("--context", required=True)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--verdict", required=True, choices=("APPROVED", "REJECTED"))
    parser.add_argument("--reason", required=True)
    args = parser.parse_args(argv)
    for name in ("context", "slug"):
        if not _SLUG.match(getattr(args, name)):
            return _refuse(f"--{name} must match {_SLUG.pattern}")
    body = _body(sys.stdin.read())
    if isinstance(body, str):
        return _refuse(body)
    done = subprocess.run(
        [sys.executable, str(_WORKTREE), "hash", args.path, "--sha", args.sha],
        capture_output=True,
        text=True,
    )
    if done.returncode:
        sys.stderr.write(done.stderr)
        return done.returncode
    bound = json.loads(done.stdout)
    now = datetime.now(UTC)
    handoff = {
        "schema_version": "handoff-v1.2",
        "agent": "dd-code-reviewer",
        "context": args.context,
        "produced_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "verdict": args.verdict,
        "verdict_reason": args.reason,
        "scope": bound["scope"],
        "reviewed_sha": bound["reviewed_sha"],
        "diff_sha256": bound["diff_sha256"],
        **body,
    }
    out = Path(bound["root"]) / ".dadaia/handoff" / args.context
    out.mkdir(parents=True, exist_ok=True)
    target = out / f"{now:%Y-%m-%dT%H%M%SZ}-dd-code-reviewer-{args.slug}.handoff.json"
    try:
        with target.open("x", encoding="utf-8") as fh:
            fh.write(json.dumps(handoff, indent=2) + "\n")
    except FileExistsError:
        return _refuse(f"{target.name} exists; rerun in a second")
    print(target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
