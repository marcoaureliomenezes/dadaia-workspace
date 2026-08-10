"""Workspace filesystem-layout constants — the single authority (pure ``core`` leaf).

Bug class (transversal, 2026-08-06 analysis): the same invariant declared in multiple
modules diverges. The root whitelist lived independently in ``hooks/root_whitelist.py``
AND ``features/spec_context/doctor.py`` — and diverged the day ``DADAIA.md`` was added
to one but not the other. The law-file path set was constructed in four places. One
fact, one place: every consumer DERIVES from this module (both ``hooks`` and
``features`` may import ``core``; the reverse edges are forbidden by import-linter).

Same regime as :mod:`dadaia_workspace.core.harness_registry`: stdlib-only, no I/O, no
internal imports — a pure constants leaf, pinned by contract tests.
"""

from __future__ import annotations

__all__ = [
    "DADAIA_MD_HARNESS_TARGETS",
    "LAW_BASENAMES",
    "LAW_HARNESS_DIRS",
    "ROOT_ALLOWED_DIRS",
    "ROOT_ALLOWED_FILES",
]

#: Directories the workspace root may contain (the Workspace Root Law).
ROOT_ALLOWED_DIRS: frozenset[str] = frozenset(
    {".agents", ".claude", ".codex", ".dadaia", ".kimi-code", "repos"}
)

#: Files the workspace root may contain. ``DADAIA.md`` is the workspace system prompt
#: (the single always-on law file); ``AGENTS.md`` its harness-discovery bridge;
#: ``CLAUDE.md`` the Claude Code import bridge; ``prompt.md`` the optional operator
#: long-prompt file.
ROOT_ALLOWED_FILES: frozenset[str] = frozenset({"AGENTS.md", "CLAUDE.md", "DADAIA.md", "prompt.md"})

#: Basenames of the projected LAW files — human-only in an instantiated workspace.
LAW_BASENAMES: frozenset[str] = frozenset({"DADAIA.md", "AGENTS.md", "CLAUDE.md"})

#: Harness/projection directories that host a projected law file (relative to the
#: workspace root). The gate composes its guarded set FROM this; the installer projects
#: ``DADAIA.md`` into the subset in :data:`DADAIA_MD_HARNESS_TARGETS`.
LAW_HARNESS_DIRS: frozenset[str] = frozenset({".claude/rules", ".codex", ".kimi-code", ".agents"})

#: Where the workspace system prompt is projected, per Layer-1 harness. The workspace
#: root copy (``DADAIA.md``) is canonical and always written.
DADAIA_MD_HARNESS_TARGETS: dict[str, str] = {
    "claude": ".claude/rules/DADAIA.md",
    "codex": ".codex/DADAIA.md",
    "kimi-code": ".kimi-code/DADAIA.md",
}
