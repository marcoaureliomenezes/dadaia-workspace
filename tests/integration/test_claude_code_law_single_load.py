"""Bug ``dadaia-md-projected-twice-into-claude-code-context`` (MEDIUM) — FR31.

Intent: REGRESSION (bug dadaia-md-projected-twice-into-claude-code-context). Size: MEDIUM.

A Claude Code session carries ``DADAIA.md``'s body **twice** at HEAD: once through the
root import chain ``CLAUDE.md -> @AGENTS.md -> @DADAIA.md`` (Claude Code resolves an
``@file`` reference as a real import — ``dd-ai-eng-knowhow/CLAUDE-CODE.md`` §2: "In
Claude Code, only an ``@import`` or a symlink actually pulls a file in"), and again
through ``.claude/rules/DADAIA.md`` — an **unscoped** rule file (no ``paths:``
frontmatter), which the harness auto-loads for *every* session regardless of the root
chain (same doc §3: "No ``paths:`` -> Always-on; loads every session for every task").
Both paths carry the identical ~3.3k-token law body, so it enters context twice on every
turn — against the law's own "one file, every rule, no second source" (``DADAIA.md`` §0).

This test models that harness load rule directly (it does not invoke Claude Code) and
proves it against the real, installed projection tree produced by
``FileSystemPublicAssetManager.install(..., target="all")`` — the executed path a real
workspace goes through. RED at HEAD (root chain + rules-dir mirror both resolve to the
law body -> 2 occurrences); GREEN once the projection seam emits the law to Claude Code
through exactly one of the two paths (A31.1/A31.3).
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager


def _installed_ws(tmp_path: Path) -> Path:
    ws = tmp_path / "ws"
    ws.mkdir()
    FileSystemPublicAssetManager().install(ws, target="all")
    return ws


def _claude_code_auto_loaded_texts(ws: Path) -> dict[str, str]:
    """Every file body a Claude Code session loads automatically, every turn.

    (a) The root import chain: ``CLAUDE.md`` resolves ``@AGENTS.md``, which resolves
    ``@DADAIA.md`` — both real ``@import``s the harness follows (cited above). The
    resolved body of that chain is exactly the root ``DADAIA.md`` file's text.
    (b) Every **unscoped** file under ``.claude/rules/`` (no ``paths:`` frontmatter in
    its own body) — auto-loaded every session, independent of (a). Every rule file this
    projection currently ships is unscoped, so no ``paths:`` filter applies here.
    """
    loaded: dict[str, str] = {}
    claude_md = ws / "CLAUDE.md"
    agents_md = ws / "AGENTS.md"
    dadaia_md = ws / "DADAIA.md"
    if claude_md.is_file() and agents_md.is_file() and dadaia_md.is_file():
        # The root chain always resolves to the root DADAIA.md body — Claude Code
        # inlines the imported file's own text, not a second copy of it.
        loaded["root-chain:DADAIA.md"] = dadaia_md.read_text(encoding="utf-8")
    rules_dir = ws / ".claude" / "rules"
    if rules_dir.is_dir():
        for rule_file in sorted(rules_dir.glob("*.md")):
            loaded[f"rules-dir:{rule_file.name}"] = rule_file.read_text(encoding="utf-8")
    return loaded


def test_claude_code_session_carries_the_law_exactly_once(tmp_path: Path) -> None:
    ws = _installed_ws(tmp_path)
    law_body = (ws / "DADAIA.md").read_text(encoding="utf-8")

    loaded = _claude_code_auto_loaded_texts(ws)
    carriers = [source for source, text in loaded.items() if text == law_body]

    assert carriers == ["root-chain:DADAIA.md"], (
        "a Claude Code session must carry DADAIA.md's body through exactly one "
        f"auto-loaded path (the root import chain); found it in: {carriers}"
    )


def test_claude_rules_dir_projects_no_dadaia_md_mirror(tmp_path: Path) -> None:
    """A31.3 — one decision at the projection seam: Claude Code's root-import chain
    already delivers the law, so the installer must not also emit the rules-dir mirror
    for Claude. This pins the concrete file the bug named."""
    ws = _installed_ws(tmp_path)
    assert not (ws / ".claude" / "rules" / "DADAIA.md").exists()


def test_root_law_still_reaches_claude_code(tmp_path: Path) -> None:
    """A31.4 — no harness ends with zero copies. The root import chain must remain
    intact and resolve to the canonical law file for Claude Code."""
    ws = _installed_ws(tmp_path)
    assert (ws / "CLAUDE.md").is_file()
    assert (ws / "AGENTS.md").is_file()
    assert (ws / "DADAIA.md").is_file()
    assert "@AGENTS.md" in (ws / "CLAUDE.md").read_text(encoding="utf-8")
    assert "@DADAIA.md" in (ws / "AGENTS.md").read_text(encoding="utf-8")
