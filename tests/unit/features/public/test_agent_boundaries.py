"""T-12 — Agent boundary tests (AC C4, C5).

Verifies that ``design-specialist`` and ``frontend-engineer`` frontmatter honour
their declared ownership boundaries, encoding the plugin-scope governance law as one
merged parametrized boundary check.
"""

from __future__ import annotations

import pathlib
from typing import Any

import pytest
import yaml

_REPO_ROOT = pathlib.Path(__file__).parents[4]
_AGENTS_DIR = _REPO_ROOT / "dadaia_workspace" / "public" / "agents"

_BROWSER_CODE_EXTENSIONS = {".js", ".ts", ".tsx", ".jsx", ".html", ".css"}

_SPEC_AUTHORSHIP_PREFIXES = ("specs/releases", "specs/features", "specs/memory")
_SPEC_AUTHORSHIP_EXACT = {"specs/", "specs"}


def _parse_frontmatter(path: pathlib.Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}
    return yaml.safe_load(text[4:end]) or {}


def _load_agent(name: str) -> dict[str, Any]:
    path = _AGENTS_DIR / f"{name}.md"
    assert path.exists(), f"Agent file not found: {path}"
    return _parse_frontmatter(path)


@pytest.mark.parametrize(
    "agent_name",
    ["design-specialist", "frontend-engineer"],
)
def test_agent_boundary_matrix(agent_name: str) -> None:
    """AC C4 (design-specialist) + AC C5 (frontend-engineer) ownership boundaries."""
    fm = _load_agent(agent_name)
    tools: list[str] = fm.get("tools") or []
    skills: list[str] = fm.get("skills") or []
    paths: dict[str, Any] = fm.get("paths") or {}
    write_allowlist: list[str] = paths.get("write_allowlist") or []

    if agent_name == "design-specialist":
        # 1 — No Bash or Edit in tools.
        forbidden_tools = {"Edit", "Bash"}
        present_forbidden = forbidden_tools & set(tools)
        assert not present_forbidden, (
            f"design-specialist must not have tools {forbidden_tools!r}. "
            f"Found: {present_forbidden!r}. Tools list: {tools!r}"
        )
        # 2 — No Playwright, browser, or image-generation skills.
        disallowed_substrings = {"playwright", "browser", "image-generation"}
        for skill in skills:
            skill_lower = skill.lower()
            matched = [s for s in disallowed_substrings if s in skill_lower]
            assert not matched, (
                f"design-specialist skill {skill!r} matches disallowed pattern(s) {matched!r}."
            )
        # 3 — No frontend-implementation-quality (belongs to frontend-engineer).
        assert "frontend-implementation-quality" not in skills, (
            "design-specialist must NOT list 'frontend-implementation-quality' in skills."
        )
        # 4 — write_allowlist must not include browser-code paths.
        for entry in write_allowlist:
            suffix = pathlib.PurePosixPath(entry).suffix.lower()
            assert suffix not in _BROWSER_CODE_EXTENSIONS, (
                f"design-specialist write_allowlist entry {entry!r} ends with browser-code "
                f"extension {suffix!r}. Full allowlist: {write_allowlist!r}"
            )
    else:  # frontend-engineer
        # 1 — No ux-ui-review (belongs to design-specialist).
        assert "ux-ui-review" not in skills, (
            "frontend-engineer must NOT list 'ux-ui-review' in skills."
        )
        # 2 — No Playwright MCP skill ownership (belongs to qa-engineer).
        for skill in skills:
            assert "playwright" not in skill.lower(), (
                f"frontend-engineer skill {skill!r} must not reference playwright."
            )
        # 3 — No specs/ authorship paths (belongs to product-engineer).
        specs_entries = [
            entry
            for entry in write_allowlist
            if (
                entry in _SPEC_AUTHORSHIP_EXACT
                or any(entry.startswith(p) for p in _SPEC_AUTHORSHIP_PREFIXES)
            )
        ]
        assert not specs_entries, (
            f"frontend-engineer write_allowlist must NOT include specs authorship paths. "
            f"Found: {specs_entries!r}"
        )
        # 4 — No Agent tool (must not dispatch sub-agents).
        assert "Agent" not in tools, (
            f"frontend-engineer must NOT have 'Agent' in its tools list. Tools: {tools!r}"
        )
