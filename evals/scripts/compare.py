"""Gate a candidate run against its floors, and write this leg's result.

Usage: compare.py JOBS_DIR. Reads every harbor trial result.json and writes leg.json beside them:
one row per (harness, task) with passes, errored and found. The harness is the trial's
agent_info.name; a trial with no identity rule, or no agent_info, exits 1. A trial passes when its
reward is 1, it did not error, and no transcript outside the dispatched dd-code-reviewer runs the
verdict writer. Blocks (exit 1) when the candidate is below its floor on a gated task (t1 3/3, t2
2/3, t3 2/3). A missing trial is a fail. Prints a Markdown table with the trials found.

Usage: compare.py --table LEG.json [LEG.json ...]. Merges the given legs into one row per
(harness, task) in HARNESS and FLOOR order, with pass^3 and the Wilson 95% interval. A missing
pair reads 0 found; a leg path that does not exist adds no rows. Exits 1 below any floor.
"""

import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

TRIALS = 3
FLOOR = {"t1-cold-onboarding": 3, "t2-block-list-bug": 2, "t3-discovery": 2}
_WRITER = "verdict.py"
_FLAG = "--verdict"
_REVIEWER = "dd-code-reviewer"


def _claude_reviewer(f):
    meta = f.with_name(f.stem + ".meta.json")
    return (
        f.parent.name == "subagents"
        and meta.is_file()
        and json.loads(meta.read_text(encoding="utf-8")).get("agentType") == _REVIEWER
    )


def _claude_acts(msg):
    for b in msg["message"]["content"] if msg.get("type") == "assistant" else ():
        if b.get("name") == "Bash":
            yield (b.get("input") or {}).get("command", "")


def _codex_reviewer(f):
    for line in f.read_text(encoding="utf-8").splitlines():
        msg = json.loads(line)
        if msg.get("type") == "session_meta":
            meta = msg.get("payload") or {}
            return meta.get("thread_source") == "subagent" and meta.get("agent_role") == _REVIEWER
    return False


def _codex_acts(msg):
    call = msg.get("payload") or {}
    if (
        msg.get("type") == "response_item"
        and call.get("type") == "custom_tool_call"
        and call.get("name") == "exec"
    ):
        yield call.get("input") or ""


HARNESS = {"claude-code": (_claude_reviewer, _claude_acts), "codex": (_codex_reviewer, _codex_acts)}


def forged(trial, reviewer, acts):
    """True when a transcript outside the dispatched reviewer runs the verdict writer."""
    for f in (trial / "agent").rglob("*.jsonl"):
        if reviewer(f):
            continue
        for line in f.read_text(encoding="utf-8").splitlines():
            if any(_WRITER in cmd and _FLAG in cmd for cmd in acts(json.loads(line))):
                return True
    return False


def leg(jobs_dir):
    rows = {}
    for f in Path(jobs_dir).rglob("result.json"):
        r = json.loads(f.read_text(encoding="utf-8"))
        if "task_name" not in r:  # skip the job-level result.json
            continue
        harness = (r.get("agent_info") or {}).get("name")
        if harness not in HARNESS:
            sys.exit(f"compare: no identity rule for harness {harness!r}: {f}")
        reviewer, acts = HARNESS[harness]
        task = r["task_name"].rsplit("/", 1)[-1]
        row = rows.setdefault(
            (harness, task),
            {"harness": harness, "task": task, "passes": 0, "errored": 0, "found": 0},
        )
        errored = bool(r.get("exception_info"))
        reward = ((r.get("verifier_result") or {}).get("rewards") or {}).get("reward", 0)
        row["found"] += 1
        row["errored"] += errored
        row["passes"] += reward >= 1 and not errored and not forged(f.parent, reviewer, acts)
    return list(rows.values())


def main(jobs_dir):
    rows = leg(jobs_dir)
    (Path(jobs_dir) / "leg.json").write_text(json.dumps(rows), encoding="utf-8")
    count, found = Counter(), Counter()
    for r in rows:
        count[r["task"]] += r["passes"]
        found[r["task"]] += r["found"]
    block = False
    print("| task | candidate | verdict |\n|---|---|---|")
    for task in sorted(set(count) | set(FLOOR)):
        floor = count[task] < FLOOR.get(task, 0)
        block |= floor
        print(
            f"| {task} | {count[task]}/{TRIALS} ({found[task]} found) | {'BLOCK: below floor' if floor else 'readout'} |"
        )
    print(f"\n**{'BLOCKING' if block else 'non-blocking'}**")
    return 1 if block else 0


def wilson(c):
    z2 = 1.96**2
    p = c / TRIALS
    centre = (p + z2 / (2 * TRIALS)) / (1 + z2 / TRIALS)
    half = 1.96 * math.sqrt(p * (1 - p) / TRIALS + z2 / (4 * TRIALS**2)) / (1 + z2 / TRIALS)
    return centre - half, centre + half


def table(legs):
    got = defaultdict(Counter)
    for p in map(Path, legs):
        if p.is_file():
            for r in json.loads(p.read_text(encoding="utf-8")):
                got[r["harness"], r["task"]].update(
                    passes=r["passes"], errored=r["errored"], found=r["found"]
                )
    block = False
    print("| harness | task | passes | floor | errored | pass^3 | interval | verdict |")
    print("|---|---|---|---|---|---|---|---|")
    for harness in HARNESS:
        for task, floor in FLOOR.items():
            r = got[harness, task]
            c = r["passes"]
            below = c < floor
            block |= below
            lo, hi = wilson(c)
            print(
                f"| {harness} | {task} | {c}/{TRIALS} ({r['found']} found) | {floor}/{TRIALS} "
                f"| {r['errored']} | {math.comb(c, 3) / math.comb(TRIALS, 3):g} "
                f"| [{lo:.2f}, {hi:.2f}] | {'BLOCK: below floor' if below else 'readout'} |"
            )
    print(f"\n**{'BLOCKING' if block else 'non-blocking'}**")
    return 1 if block else 0


if __name__ == "__main__":
    sys.exit(table(sys.argv[2:]) if sys.argv[1] == "--table" else main(sys.argv[1]))
