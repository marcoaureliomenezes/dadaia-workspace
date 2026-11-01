"""Print the full text of every repository page that ``llms.txt`` links, in its order.

Usage: ``python scripts/llms_full.py > llms-full.txt``.
"""

from __future__ import annotations

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SKIPPED = {"CHANGELOG.md", "llms-full.txt"}


def render(root: Path = _ROOT) -> str:
    """Return each linked file of *root*, under a ``# <path>`` heading, in ``llms.txt`` order.

    Links that are not files of *root*, the changelog and ``llms-full.txt`` itself are skipped.
    """
    index = (root / "llms.txt").read_text(encoding="utf-8")
    paths: list[str] = []
    for target in re.findall(r"\]\(([^)#\s]+)", index):
        if target not in paths and target not in _SKIPPED and (root / target).is_file():
            paths.append(target)
    return "".join(f"# {p}\n\n{(root / p).read_text(encoding='utf-8').rstrip()}\n\n" for p in paths)


if __name__ == "__main__":
    print(render(), end="")
