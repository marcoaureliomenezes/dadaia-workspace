#!/usr/bin/env python3
"""Refuse an e2e (LARGE) test file with no declared `Intent:` line. Exit 0=ok, 1=undeclared.

FR19 (v0.4.3 T-043-27): dadaia-test-stewardship §A / tests/AGENTS.md require every test to
declare intent in its module docstring (Python) or header comment (TypeScript) —
`Intent: <KIND> — <AC id | bug-id | task-id>`. Scoped to `tests/e2e/**` (the LARGE tier
T-043-24..26 fully backfilled): the wider suite carries no such mechanical gate yet.
"""

import os
import re
import sys
from pathlib import Path

_ROOT = Path(os.environ.get("DADAIA_WORKSPACE_ROOT", Path(__file__).resolve().parent.parent.parent))
_E2E_DIR = _ROOT / "tests" / "e2e"

_INTENT_RE = re.compile(r"Intent:\s*\S")

# Non-test support modules under tests/e2e/** — zero collected test items, so no
# declaration is required (mirrors the exclusion the T-043-26 census itself applied).
_EXCLUDED_NAMES = frozenset({"__init__.py", "rendezvous.py", "conftest.py"})


def _candidate_files() -> list[Path]:
    if not _E2E_DIR.is_dir():
        return []
    py_files = [
        p
        for p in _E2E_DIR.rglob("test_*.py")
        if p.name not in _EXCLUDED_NAMES and "node_modules" not in p.parts
    ]
    ts_files = [p for p in _E2E_DIR.rglob("*.spec.ts") if "node_modules" not in p.parts]
    return sorted(py_files + ts_files)


def main() -> int:
    offenders = [
        path for path in _candidate_files() if not _INTENT_RE.search(path.read_text("utf-8"))
    ]
    if offenders:
        for path in offenders:
            print(path, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
