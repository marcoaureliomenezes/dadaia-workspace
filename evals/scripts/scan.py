"""Exit 1 when any file under the given paths holds a needle: a value of $SCAN_SECRET
(each string leaf when it parses as JSON, else the whole value), a token or key shape,
a JWT, or a creator id. Prints the file path only, never the match."""

import json
import os
import re
import sys
from pathlib import Path

# ponytail: plain-text match only; misses base64, UTF-16, archives and symlinked dirs.
SHAPES = [
    r"\bsk-[\w-]{20,}",  # Anthropic token and OpenAI key shapes
    r"\beyJ[\w-]+\.eyJ[\w-]+\.[\w-]+",  # JWT
    r"\bcreator_(?:user|account)_id\\?\"\s*:\s*\\?\"[^\"\\]+",  # plain or inside a JSON string
]


MIN_LEAF = 16  # shorter JSON leaves are enum-like words, not secrets


def _leaves(node):
    if isinstance(node, str):
        if len(node) >= MIN_LEAF:
            yield node
    elif isinstance(node, dict):
        yield from (leaf for v in node.values() for leaf in _leaves(v))
    elif isinstance(node, list):
        yield from (leaf for v in node for leaf in _leaves(v))


def _needles(secret):
    if not secret:
        return []
    try:
        leaves = list(_leaves(json.loads(secret)))
    except ValueError:
        return [secret]
    return leaves or [secret]


def main(paths):
    if missing := [p for p in paths if not Path(p).exists()]:
        print(f"no such path: {missing}")
        return 1
    needles = [re.escape(n) for n in _needles(os.environ.get("SCAN_SECRET", ""))]
    pattern = re.compile("|".join(SHAPES + needles))
    roots = map(Path, paths)
    files = [f for p in roots for f in ([p] if p.is_file() else p.rglob("*")) if f.is_file()]
    hits = [f for f in files if pattern.search(f.read_text(encoding="utf-8", errors="replace"))]
    for f in hits:
        print(f"secret found: {f}")  # the path only, never the match
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
