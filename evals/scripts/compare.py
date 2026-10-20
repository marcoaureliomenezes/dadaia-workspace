"""Gate a candidate run against a baseline run.

Usage: compare.py BASE_JOBS_DIR CAND_JOBS_DIR. Reads every harbor trial result.json.
Blocks (exit 1) when the candidate is below its floor on a gated task (t1 3/3, t2 2/3,
t3 2/3), or a task at >=2/3 on the baseline falls to <=1/3. t3's baseline is readout
only. A missing trial is a fail. Prints a Markdown table with the trials found per side.
"""

import json
import os
import sys
from collections import Counter
from pathlib import Path

TRIALS = 3
FLOOR = {"t1-cold-onboarding": 3, "t2-block-list-bug": 2, "t3-discovery": 2}


def passes(jobs_dir):
    count, found = Counter(), Counter()
    for f in Path(jobs_dir).rglob("result.json"):
        r = json.loads(f.read_text(encoding="utf-8"))
        if "task_name" in r:  # skip the job-level result.json
            task = r["task_name"].rsplit("/", 1)[-1]
            reward = ((r.get("verifier_result") or {}).get("rewards") or {}).get("reward", 0)
            count[task] += reward >= 1
            found[task] += 1
    return count, found


def main(base_dir, cand_dir):
    (base, nb), (cand, nc) = passes(base_dir), passes(cand_dir)
    block = False
    name = os.environ.get("BASELINE", "baseline")
    print(f"| task | {name} | candidate | verdict |\n|---|---|---|---|")
    for task in sorted(set(base) | set(cand) | set(FLOOR)):
        drop = base[task] >= 2 and cand[task] <= 1
        floor = cand[task] < FLOOR.get(task, 0)
        block |= drop or floor
        verdict = "BLOCK: drop" if drop else "BLOCK: below floor" if floor else "readout"
        b = f"{base[task]}/{TRIALS} ({nb[task]} found)"
        c = f"{cand[task]}/{TRIALS} ({nc[task]} found)"
        print(f"| {task} | {b} | {c} | {verdict} |")
    print(f"\n**{'BLOCKING' if block else 'non-blocking'}**")
    return 1 if block else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:3]))
