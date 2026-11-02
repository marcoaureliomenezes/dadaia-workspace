"""Exit 1 when a path is missing or a file under the given paths holds a needle: a value of
$SCAN_SECRET (each string leaf when it parses as JSON, else the whole value), a token or key
shape, a JWT, a creator id, or a value assigned to a secret-named variable or JSON key. A
JSON or JSON Lines file is also read with its strings decoded. Prints the file path only."""

import contextlib
import json
import os
import re
import sys
from pathlib import Path

# ponytail: raw text plus decoded JSON strings; misses base64, UTF-16, archives, symlinked dirs and
# escaped forms in a plain-text file that is not JSON or JSON Lines.
_NAME = r"[A-Z0-9_]*(?:TOKEN|SECRET|PASSWORD|PASSWD|API_KEY|PRIVATE_KEY|CREDENTIALS?)"
_VALUE = r"[\"']?(?![$<{*])[^\s\"'<>{}*$]{8}"  # not a placeholder
SHAPES = [
    r"\bsk-[\w-]{20,}",  # Anthropic token and OpenAI key shape
    r"\beyJ[\w-]+\.eyJ[\w-]+\.[\w-]+",  # JWT
    r"\bcreator_(?:user|account)_id\"\s*:\s*\"[^\"]+",
    rf"\b{_NAME}(?:=|\"\s*:\s*\"){_VALUE}",  # a secret named by its variable or key
]


MIN_LEAF = 16  # shorter JSON leaves are enum-like words, not secrets


def _leaves(node, floor=MIN_LEAF):
    if isinstance(node, str):
        if len(node) >= floor:
            yield node
    elif isinstance(node, dict):
        yield from (leaf for v in node.values() for leaf in _leaves(v, floor))
    elif isinstance(node, list):
        yield from (leaf for v in node for leaf in _leaves(v, floor))


def _haystack(text):
    """The text plus every string leaf of the JSON documents in it, escapes decoded: the whole
    text when it parses, else each line that parses on its own."""
    try:
        docs = [json.loads(text)]
    except ValueError:
        docs = []
        for line in text.splitlines():
            with contextlib.suppress(ValueError):
                docs.append(json.loads(line))
    return "\n".join([text, *(leaf for d in docs for leaf in _leaves(d, 0))])


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
    hits = [
        f
        for f in files
        if pattern.search(_haystack(f.read_text(encoding="utf-8", errors="replace")))
    ]
    for f in hits:
        print(f"secret found: {f}")  # the path only, never the match
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
