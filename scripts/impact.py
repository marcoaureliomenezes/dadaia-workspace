"""Which tests a change reaches: ``python scripts/impact.py`` prints ``test: <path>`` and
``unmapped: <path>`` (sorted) for the working tree against HEAD plus untracked files. A test
is reached when it imports a changed module, directly or through others; a changed skill
script reaches the tests in the mirrored ``tests/public/skills/dd_<x>/``. Paths given as
arguments replace that read. A developer read, called by ``ci.py --changed`` and
``mutate.py``. Standard library only."""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = "dadaia_workspace/public/skills/"


def _git(*args: str) -> list[str]:
    done = subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=True
    )
    return done.stdout.splitlines()


def _module(rel: str) -> str:
    return rel.removesuffix(".py").removesuffix("/__init__").replace("/", ".")


def _imports(path: Path) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text("utf-8"))):
        if isinstance(node, ast.Import):
            found |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            found |= {node.module, *(f"{node.module}.{a.name}" for a in node.names)}
    return found


def main() -> None:
    changed = sorted(
        sys.argv[1:]
        or {
            *_git("diff", "--name-only", "HEAD"),
            *_git("ls-files", "--others", "--exclude-standard"),
        }
    )
    files = [
        p.relative_to(ROOT).as_posix()
        for d in ("dadaia_workspace", "tests")
        for p in (ROOT / d).rglob("*.py")
    ]
    importers: dict[str, set[str]] = {}
    for rel in files:
        for name in _imports(ROOT / rel):
            importers.setdefault(name, set()).add(_module(rel))
    tests = {_module(f): f for f in files if Path(f).name.startswith("test_")}
    selected: set[str] = set()
    unmapped: list[str] = []
    for rel in changed:
        reached, todo = set(), [_module(rel)]
        while todo:
            name = todo.pop()
            if name not in reached:
                reached.add(name)
                todo += importers.get(name, ())
        hits = {tests[m] for m in reached if m in tests}
        if rel.startswith(SKILLS):
            mirror = f"tests/public/skills/{rel[len(SKILLS) :].split('/')[0].replace('-', '_')}/"
            hits |= {f for f in tests.values() if f.startswith(mirror)}
        selected |= hits
        unmapped += [] if hits else [rel]
    print(
        "\n".join(
            [*(f"test: {f}" for f in sorted(selected)), *(f"unmapped: {f}" for f in unmapped)]
        )
    )


if __name__ == "__main__":
    main()
