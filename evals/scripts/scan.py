"""Exit 1 when any file under the given paths holds the model secret's value
($SCAN_SECRET, passed by the job) or an Anthropic token shape (ADR 0217)."""

import os
import re
import sys
from pathlib import Path

# ponytail: plain-text match only; misses base64, UTF-16, archives and symlinked dirs.


def main(paths):
    if missing := [p for p in paths if not Path(p).exists()]:
        print(f"no such path: {missing}")
        return 1
    secret = os.environ.get("SCAN_SECRET", "")
    pattern = re.compile(r"sk-ant-[\w-]{20,}" + ("|" + re.escape(secret)) * bool(secret))
    roots = map(Path, paths)
    files = [f for p in roots for f in ([p] if p.is_file() else p.rglob("*")) if f.is_file()]
    hits = [f for f in files if pattern.search(f.read_text(encoding="utf-8", errors="replace"))]
    for f in hits:
        print(f"secret found: {f}")  # the path only, never the match
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
