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
    "DADAIA_ADDITIVE_PREFIXES",
    "DADAIA_ALLOWED_SUBDIRS",
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

#: Canonical top-level subdirectories allowed inside ``.dadaia/`` (ROOT-4), documented in
#: the projected ``.dadaia/AGENTS.md`` canonical-folder table — anything else is slop and
#: flags ROOT-4. ONE fact, one place: ``doctor.py`` and ``legacy_dadaia_dirs.py`` derive
#: from here — a hand-copied duplicate caused bug
#: dadaia-reconcile-quarantines-sanctioned-references-clone.
DADAIA_ALLOWED_SUBDIRS: frozenset[str] = frozenset(
    {
        # ── Projections (lib-originated; regen via `dadaia public install`) ──
        "agentic",  # staged public assets + manifest.json (projection source-of-truth)
        "hooks",  # projected Python governance hook entrypoints (v0.1.47 W1-9)
        "scripts",  # projected runtime/git-hook scripts
        # ── Runtime working areas ──
        "mcps",  # per-MCP-server working dirs (mcps/<server>/)
        "runtime",  # long-lived local runtime working area for tooling
        # ── Operator-owned (never touched by any lifecycle verb, O4/T-045-23) ──
        "references",  # operator-placed reference clones: .dadaia/references/<clone>/
        # ── CLI/service-owned state ──
        "states",  # machine-readable runtime state JSON
        "sessions",  # per-session identity/bind records (PROTECTED)
        # ── Outputs ──
        "handoff",  # machine-readable agent handoffs (handoff/<context>/)
        "reports",  # human-readable HTML reports (reports/<context>/<agent>/)
        "academy",  # durable agent study/mastery notes + validation ledgers
        # ── Ephemeral (disposable, GC'd) ──
        "tmp",  # scratch + evidence, tmp/<agent>/<YYYYMMDD>/
        "logs",  # telemetry/event logs
        "runs",  # workflow run transcripts
        "dev-report",  # generated developer diagnostic reports
        # ── Artifacts / managed environments ──
        "dist",  # built wheels + local exports
        ".venv",  # managed workspace Python environment
        ".cache",  # redirected tool caches (ruff/coverage), kept out of repos
    }
)

#: The ``.dadaia/`` runtime zones that are operator/agent-writable by law (DADAIA.md §3
#: ADDITIVE class) — always writable, expected to hold non-lib files. Consumers: the SDD
#: gate (``features/spec_context/gate_policy``) allows writes here unconditionally, and
#: the public doctor's foreign-projections scan skips them (a runtime artifact in an
#: ADDITIVE zone is normal operation, never a ``[foreign]`` finding).
DADAIA_ADDITIVE_PREFIXES: tuple[str, ...] = (
    ".dadaia/reports/",
    ".dadaia/handoff/",
    ".dadaia/tmp/",
)

#: Basenames of the projected LAW files — human-only in an instantiated workspace.
LAW_BASENAMES: frozenset[str] = frozenset({"DADAIA.md", "AGENTS.md", "CLAUDE.md"})

#: Harness/projection directories that host a projected law file (relative to the
#: workspace root). The gate composes its guarded set FROM this; the installer projects
#: ``DADAIA.md`` into the subset in :data:`DADAIA_MD_HARNESS_TARGETS`.
LAW_HARNESS_DIRS: frozenset[str] = frozenset({".claude/rules", ".codex", ".kimi-code", ".agents"})

#: Where the law is projected per harness whose root-import chain does not already
#: deliver it — Claude Code's does, so no entry here (bug FR31, see workspace-law rule).
DADAIA_MD_HARNESS_TARGETS: dict[str, str] = {
    "codex": ".codex/DADAIA.md",
    "kimi-code": ".kimi-code/DADAIA.md",
}
