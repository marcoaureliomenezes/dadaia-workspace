"""T-12 — Agent boundary tests (AC C4, C5).

Verifies that ``design-specialist`` and ``frontend-engineer`` frontmatter honour
their declared ownership boundaries:

* ``test_design_specialist_boundary`` — AC C4
* ``test_frontend_engineer_boundary`` — AC C5
"""

from __future__ import annotations

import pathlib
from typing import Any

import yaml

# ---------------------------------------------------------------------------
# Repository root
# ---------------------------------------------------------------------------

_REPO_ROOT = pathlib.Path(__file__).parents[4]
_AGENTS_DIR = _REPO_ROOT / "dadaia_workspace" / "public" / "agents"

# Extensions that design-specialist must NOT own write access to
# (browser production code)
_BROWSER_CODE_EXTENSIONS = {".js", ".ts", ".tsx", ".jsx", ".html", ".css"}


# ---------------------------------------------------------------------------
# Helper: frontmatter parser
# ---------------------------------------------------------------------------


def _parse_frontmatter(path: pathlib.Path) -> dict[str, Any]:
    """Return the YAML frontmatter dict from a ``---`` fenced Markdown file.

    Returns an empty dict when the file has no frontmatter or fences are
    malformed.
    """
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


# ---------------------------------------------------------------------------
# AC C4 — design-specialist boundary
# ---------------------------------------------------------------------------


def test_design_specialist_boundary() -> None:
    """design-specialist must stay within its declared no-code, no-raster boundary.

    Assertions (AC C4):
    1. ``tools`` must NOT contain ``Edit`` or ``Bash``.
    2. ``skills`` must NOT contain any name matching ``playwright``, ``browser``,
       or ``image-generation`` (case-insensitive substring).
    3. ``skills`` must NOT contain ``frontend-implementation-quality``
       (belongs exclusively to frontend-engineer).
    4. ``paths.write_allowlist`` entries must NOT end with a browser-code
       extension (``.js``, ``.ts``, ``.tsx``, ``.jsx``, ``.html``, ``.css``).
    """
    fm = _load_agent("design-specialist")

    tools: list[str] = fm.get("tools") or []
    skills: list[str] = fm.get("skills") or []
    paths: dict[str, Any] = fm.get("paths") or {}
    write_allowlist: list[str] = paths.get("write_allowlist") or []

    # 1 — No Bash or Edit in tools
    forbidden_tools = {"Edit", "Bash"}
    present_forbidden = forbidden_tools & set(tools)
    assert not present_forbidden, (
        f"design-specialist must not have tools {forbidden_tools!r} in its frontmatter. "
        f"Found: {present_forbidden!r}. Tools list: {tools!r}"
    )

    # 2 — No Playwright, browser, or image-generation skills
    disallowed_substrings = {"playwright", "browser", "image-generation"}
    for skill in skills:
        skill_lower = skill.lower()
        matched = [s for s in disallowed_substrings if s in skill_lower]
        assert not matched, (
            f"design-specialist skill {skill!r} matches disallowed pattern(s) {matched!r}. "
            f"Playwright, browser automation, and image-generation are out of scope."
        )

    # 3 — No frontend-implementation-quality (that belongs to frontend-engineer)
    assert "frontend-implementation-quality" not in skills, (
        "design-specialist must NOT list 'frontend-implementation-quality' in skills — "
        "this skill belongs to frontend-engineer only."
    )

    # 4 — write_allowlist must not include browser-code paths
    for entry in write_allowlist:
        entry_path = pathlib.PurePosixPath(entry)
        suffix = entry_path.suffix.lower()
        # A glob pattern like "**/*.ts" still has suffix ".ts"
        assert suffix not in _BROWSER_CODE_EXTENSIONS, (
            f"design-specialist write_allowlist entry {entry!r} ends with browser-code "
            f"extension {suffix!r}. design-specialist must not write browser code "
            f"(.js, .ts, .tsx, .jsx, .html, .css). Full allowlist: {write_allowlist!r}"
        )


# ---------------------------------------------------------------------------
# AC C5 — frontend-engineer boundary
# ---------------------------------------------------------------------------


def test_frontend_engineer_boundary() -> None:
    """frontend-engineer must not own UX/UI review, E2E, Playwright, or specs.

    Assertions (AC C5):
    1. ``skills`` must NOT contain ``ux-ui-review``.
    2. ``skills`` must NOT contain any name matching ``playwright`` (case-insensitive
       substring) — Playwright MCP is owned by qa-engineer.
    3. ``paths.write_allowlist`` must NOT contain ``specs/`` as a writable root
       — frontend-engineer must not own specs authorship.
    4. ``tools`` must NOT contain ``Agent`` — frontend-engineer must not
       dispatch sub-agents.
    """
    fm = _load_agent("frontend-engineer")

    tools: list[str] = fm.get("tools") or []
    skills: list[str] = fm.get("skills") or []
    paths: dict[str, Any] = fm.get("paths") or {}
    write_allowlist: list[str] = paths.get("write_allowlist") or []

    # 1 — No ux-ui-review (UX judgment belongs to design-specialist)
    assert "ux-ui-review" not in skills, (
        "frontend-engineer must NOT list 'ux-ui-review' in skills — "
        "UX/UI review authority belongs to design-specialist."
    )

    # 2 — No Playwright MCP skill ownership
    for skill in skills:
        assert "playwright" not in skill.lower(), (
            f"frontend-engineer skill {skill!r} contains 'playwright'. "
            "Playwright and E2E ownership belong to qa-engineer, not frontend-engineer."
        )

    # 3 — No specs/ as a writable root (no spec authorship paths)
    # frontend-engineer may write to specs/assets/ (design token drop zone) but must
    # not own specs authorship paths: specs/releases/**, specs/features/**,
    # specs/memory/**, or bare specs/ itself.
    _SPEC_AUTHORSHIP_PREFIXES = (
        "specs/releases",
        "specs/features",
        "specs/memory",
    )
    _SPEC_AUTHORSHIP_EXACT = {"specs/", "specs"}
    specs_entries = [
        entry
        for entry in write_allowlist
        if (
            entry in _SPEC_AUTHORSHIP_EXACT
            or any(entry.startswith(p) for p in _SPEC_AUTHORSHIP_PREFIXES)
        )
    ]
    assert not specs_entries, (
        f"frontend-engineer write_allowlist must NOT include specs authorship paths "
        f"(specs/releases/**, specs/features/**, specs/memory/**, or bare specs/). "
        f"Specs authorship belongs to product-engineer. Found: {specs_entries!r}"
    )

    # 4 — No Agent tool (frontend-engineer must not dispatch sub-agents)
    assert "Agent" not in tools, (
        f"frontend-engineer must NOT have 'Agent' in its tools list. "
        f"Sub-agent dispatch is not in scope for frontend-engineer. Tools: {tools!r}"
    )
