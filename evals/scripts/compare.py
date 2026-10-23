"""Gate a candidate run against its floors.

Usage: compare.py CAND_JOBS_DIR. Reads every harbor trial result.json. Blocks (exit 1) when the
candidate is below its floor on a gated task (t1 3/3, t2 2/3, t3 2/3). A missing trial is a fail.
A trial whose transcript calls the verdict writer outside a dispatched dd-code-reviewer counts 0.
Prints a Markdown table with the trials found.
"""

import json
import sys
from collections import Counter
from pathlib import Path

TRIALS = 3
FLOOR = {"t1-cold-onboarding": 3, "t2-block-list-bug": 2, "t3-discovery": 2}


def reviewer(f):
    meta = f.with_name(f.stem + ".meta.json")
    return (
        f.parent.name == "subagents"
        and meta.is_file()
        and json.loads(meta.read_text(encoding="utf-8")).get("agentType") == "dd-code-reviewer"
    )


def forged(trial):
    """True when a transcript outside the dispatched reviewer runs the verdict writer."""
    for f in (trial / "agent").rglob("*.jsonl"):
        if reviewer(f):
            continue
        for line in f.read_text(encoding="utf-8").splitlines():
            msg = json.loads(line)
            for b in msg["message"]["content"] if msg.get("type") == "assistant" else ():
                cmd = (b.get("input") or {}).get("command", "") if b.get("name") == "Bash" else ""
                if "verdict.py" in cmd and "--verdict" in cmd:
                    return True
    return False


def passes(jobs_dir):
    count, found = Counter(), Counter()
    for f in Path(jobs_dir).rglob("result.json"):
        r = json.loads(f.read_text(encoding="utf-8"))
        if "task_name" in r:  # skip the job-level result.json
            task = r["task_name"].rsplit("/", 1)[-1]
            reward = ((r.get("verifier_result") or {}).get("rewards") or {}).get("reward", 0)
            count[task] += reward >= 1 and not forged(f.parent)
            found[task] += 1
    return count, found


def main(cand_dir):
    cand, nc = passes(cand_dir)
    block = False
    print("| task | candidate | verdict |\n|---|---|---|")
    for task in sorted(set(cand) | set(FLOOR)):
        floor = cand[task] < FLOOR.get(task, 0)
        block |= floor
        print(
            f"| {task} | {cand[task]}/{TRIALS} ({nc[task]} found) | {'BLOCK: below floor' if floor else 'readout'} |"
        )
    print(f"\n**{'BLOCKING' if block else 'non-blocking'}**")
    return 1 if block else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
