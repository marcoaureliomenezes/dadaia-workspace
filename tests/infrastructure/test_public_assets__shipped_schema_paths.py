"""Every `*.schema.json` path a shipped text names resolves to a shipped file.

Size: SMALL (reads the shipped tree, no install).

Owner: dd-sw-engineer-sr
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import dadaia_workspace

pytestmark = pytest.mark.small

PUBLIC = Path(dadaia_workspace.__file__).parent / "public"
_TEXT = {".md", ".txt", ".json", ".toml"}
_PATH = re.compile(r"[\w./-]*/[\w.-]*\.schema\.json")
_PROJECTED = (
    (".dadaia/agentic/schemas/", "schemas/"),
    ("dadaia_workspace/public/", ""),
)
_SKILL = re.compile(r"\.agents/skills/([\w-]+)/(scripts/schemas/.+)")


def _shipped(path: str) -> Path:
    if m := _SKILL.search(path):
        return PUBLIC / "skills" / m[1] / m[2]
    for prefix, target in _PROJECTED:
        if path.startswith(prefix):
            return PUBLIC / target / path[len(prefix) :]
    return PUBLIC / path  # any other form must already be a public-relative path


def _citations() -> list[tuple[str, str]]:
    found = []
    for f in sorted(PUBLIC.rglob("*")):
        if f.suffix not in _TEXT or f.name.endswith(".schema.json") or not f.is_file():
            continue
        for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            found += [(f"{f.relative_to(PUBLIC)}:{n}", p) for p in _PATH.findall(line)]
    return found


@pytest.mark.parametrize(("where", "cited"), _citations(), ids=[w for w, _ in _citations()])
def test_a_cited_schema_path_names_a_shipped_file(where: str, cited: str) -> None:
    assert _shipped(cited).is_file(), f"{where} cites {cited}"
