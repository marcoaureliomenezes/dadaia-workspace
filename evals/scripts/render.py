"""Render a harness variant of the eval tasks: `render.py SRC DST HARNESS LABEL`.

Copies the task tree SRC to a new DST, then swaps the T1 harness words for LABEL and the T2
`--harness` flag for HARNESS. Exits non-zero when a token is absent from the copy.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path


def main(src: str, dst: str, harness: str, label: str) -> int:
    out = Path(dst)
    shutil.copytree(src, out)
    swaps = {
        "t1-cold-onboarding/instruction.md": (
            b"the Claude Code harness",
            f"the {label} harness".encode(),
        ),
        "t2-block-list-bug/environment/project.sh": (
            b"--harness claude",
            f"--harness {harness}".encode(),
        ),
    }
    for rel, (old, new) in swaps.items():
        path = out / rel
        text = path.read_bytes()
        if old not in text:
            print(f"token absent: {rel}", file=sys.stderr)
            return 1
        path.write_bytes(text.replace(old, new))
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:5]))
