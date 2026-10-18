#!/usr/bin/env python3
"""Write the reviewer's verdict handoff, bound to the sha and diff it judged."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
#: One bootstrap statement: this folder and the kernel, at the front.
sys.path[:0] = [
    str(Path(__file__).resolve().parent),
    str(Path(__file__).resolve().parents[2] / "dd-bug-resolution" / "scripts"),
]

import _atomic
import _clock
import _ledger
import _root
from _git import scrubbed_env
from _grammar import CONTEXT_NAME_RE
from _handoffs import REVIEWER
from _platform import act, run, use_utf8_stdio, write_text
from _refusal import Refusal, fix_of, report
from _specs import find_specs, run_cli
from _stats import table as _stats_table

_WORKTREE = Path(__file__).resolve().parents[2] / "dd-gitflow-default" / "scripts" / "worktree.py"
_OWN = (
    "agent", "verdict", "verdict_reason", "reviewed_sha", "diff_sha256",
    "scope", "produced_at", "context", "schema_version",
)  # fmt: skip


def _body(text: str) -> dict[str, object]:
    """The stdin object. Raises `Refusal` when it is not one verdict.py may extend."""
    fix = act(
        "agent", "pipe one JSON object without the keys verdict.py owns, then rerun verdict.py"
    )
    try:
        body = json.loads(text)
    except ValueError:
        raise Refusal("stdin is not JSON", fix) from None
    if not isinstance(body, dict):
        raise Refusal("stdin is not a JSON object", fix)
    if taken := [k for k in _OWN if k in body]:
        raise Refusal(f"stdin sets keys verdict.py owns: {', '.join(taken)}", fix)
    return body


def _reason(stdout: str, stderr: str) -> Refusal:
    """The refusal for a failed `reports validate --json`: its first error, or its own text."""
    try:
        err = json.loads(stdout)[0]["errors"][0]
    except (ValueError, LookupError, TypeError):  # no JSON: the CLI refused before validating
        said = stderr.splitlines()
        fix = fix_of(
            stderr, act("agent", "resolve the workspace CLI error above, then rerun verdict.py")
        )
        why = next((x[7:] for x in said if x.startswith("Error: ")), stderr.strip() or "no output")
        return Refusal(why, fix)
    where, why = err["field_path"], err["message"]
    return Refusal(
        f"{where}: {why}",
        act("agent", f"correct {where} in the stdin body ({why}), then rerun verdict.py"),
    )


def _stats(argv: list[str]) -> int:
    """Print the local metric table of one candidate over its birth-to-CLOSURE window."""
    parser = argparse.ArgumentParser(prog="verdict.py stats", description=_stats.__doc__)
    parser.add_argument("rc", help="<M.m.p>-rc<N>")
    parser.add_argument("--specs", type=Path)
    args = parser.parse_args(argv)
    root = _root.workspace_of(Path.cwd())
    if root is None:
        raise Refusal(
            "no workspace above the current directory",
            act("agent", "run verdict.py stats from inside the workspace, then rerun it"),
        )
    sys.stdout.write(_stats_table(root, find_specs(args.specs), args.rc))
    return 0


def main(argv: list[str] | None = None) -> int:
    use_utf8_stdio()
    try:
        return _run(sys.argv[1:] if argv is None else argv)
    except Refusal as refusal:
        report(refusal, refusal.fix)
        return 1


def _run(argv: list[str]) -> int:
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
    for name, pattern in (("context", CONTEXT_NAME_RE.pattern), ("slug", slug)):
        if not re.fullmatch(pattern, getattr(args, name)):
            raise Refusal(
                f"--{name} must match {pattern}",
                act("agent", f"pass a {name} matching that pattern, then rerun verdict.py"),
            )
    tree = Path(args.path).resolve()
    body = _body(sys.stdin.read())
    done = run([sys.executable, str(_WORKTREE), "hash", str(tree), "--sha", args.sha])
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
    root = Path(bound["root"])
    out = root / ".dadaia/handoff" / args.context
    out.mkdir(parents=True, exist_ok=True)
    target = out / f"{now.replace(':', '')}-{REVIEWER}-{args.slug}.handoff.json"
    try:
        target.touch(exist_ok=False)
        write_text(target, json.dumps(handoff, indent=2) + "\n")
    except FileExistsError:
        raise Refusal(
            f"{target.name} exists; rerun in a second",
            act("agent", "rerun verdict.py in a second"),
        ) from None
    try:
        checked = run_cli(root, "reports", "validate", str(target), "--reviewed-root", str(tree), "--json", env=scrubbed_env())  # fmt: skip
        if checked.returncode:
            raise _reason(checked.stdout, checked.stderr)
    except Refusal:
        _atomic.atomic_write(target, None)
        raise
    print(target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
