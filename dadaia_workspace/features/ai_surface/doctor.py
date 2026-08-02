"""AI-surface doctor — prevent mandatory ordered-lifecycle ritual from creeping back
into the dehydrated AI surface (release v0.1.24 / WS-7, epic §8.6).

Background
----------
v0.1.24 moves lifecycle *authority* out of the probabilistically-read instruction
surfaces (``AGENTS.md``, lifecycle skills) and into the Python ``dadaia lifecycle``
workflows. The dehydrated surfaces are allowed to *reference* the ritual (to say "this
is owned by the dadaia-workflows, open ``dadaia panel``"), but they must NOT carry the
**mandatory ordered-lifecycle ritual** itself as an authoritative agent procedure.

This module scans the dehydrated bodies for that ritual and ``[drift]``-flags any
*reintroduction*, so a future edit cannot silently paste the procedure back in.

The forbidden-pattern rule-set (documented + testable)
------------------------------------------------------
A body is in violation when it contains **mandatory ordered-lifecycle ritual presented
as an authoritative agent procedure**. We detect that with a deliberately narrow,
structural pattern set (substring/regex on the raw text) — NOT loose keyword presence —
so a single descriptive mention ("ordered lifecycle is owned by the workflows") never
trips it:

- ``AISURF-1`` — an ``[SDD HARD STOP]`` hard-stop ritual block (the literal token).
- ``AISURF-2`` — a **numbered** ordered procedure step that reserves a task by flipping
  the markers ``[ ] -> [-]`` (e.g. ``"3. Reserve your task: flip `[ ]` -> `[-]`"``).
  Requires the leading ``<n>.`` ordinal AND the reserve verb AND the ``[ ]``->``[-]``
  transition on one line — a marker *legend* (``[-] IN PROGRESS``) does not match.
- ``AISURF-3`` — an explicit ordered **read** procedure sequencing the three artifacts:
  ``SPEC ... (then|->|→) ... PLAN ... (then|->|→) ... TASKS``. A prose mention that
  merely lists "SPEC/PLAN/TASKS" without ``then``/arrow sequencing does not match.

Governed surfaces (scan scope)
------------------------------
The rule is about **where** the procedure lives, not whether it may exist. The root law
is loaded into every session of every harness, so it must stay lean and point at the
procedure; the skill is loaded on demand and **is** the procedure. So the doctor polices
only the always-loaded surfaces:

- ``public/data/AGENTS.md`` and ``public/scaffold/AGENTS.md`` — always loaded. Ordered
  ritual here is always a regression: state the law, name the skill, stop.

``public/skills/*/SKILL.md`` is deliberately **out of scope**: once the workflow engine
was demolished the skill became the authoritative procedure, so ritual in a skill is
correct by construction. ``public/agents/*.md`` and ``public/rules/*.md`` stay out of
scope too — a persona legitimately carries its own per-role discipline.
"""

from __future__ import annotations

import re
from pathlib import Path

# AISURF-1 — the hard-stop ritual block token.
_SDD_HARD_STOP = "[SDD HARD STOP]"

# AISURF-2 — a numbered ordered-procedure line that reserves a task by flipping
# `[ ]` -> `[-]`. Anchored on a leading ordinal so a marker legend does not match.
_NUMBERED_RESERVE = re.compile(
    r"^\s*\d+\.\s+.*\b(reserve|flip)\b.*`?\[ \]`?\s*(?:->|→|to)\s*`?\[-\]`?",
    re.IGNORECASE,
)

# AISURF-3 — an explicit ordered read procedure: SPEC -> PLAN -> TASKS with sequencing.
_ORDERED_READ = re.compile(
    r"spec\.?(?:md)?\b.*\b(?:then|->|→)\b.*plan\.?(?:md)?\b.*\b(?:then|->|→)\b.*tasks",
    re.IGNORECASE,
)

# Globs (relative to the public dir) the doctor scans this release.
GOVERNED_SCAN_GLOBS: tuple[str, ...] = (
    "data/AGENTS.md",
    "scaffold/AGENTS.md",
)

# Surfaces deliberately out of scope: the skill IS the procedure, and a persona or rule
# carries its own per-role discipline.
DEFERRED_SCAN_GLOBS: tuple[str, ...] = (
    "skills/*/SKILL.md",
    "agents/*.md",
    "rules/*.md",
)


def _governed_files(public_dir: Path) -> list[Path]:
    out: list[Path] = []
    seen: set[Path] = set()
    for pattern in GOVERNED_SCAN_GLOBS:
        for path in sorted(public_dir.glob(pattern)):
            if path.is_file() and path not in seen:
                seen.add(path)
                out.append(path)
    return out


def _ritual_findings(text: str) -> list[tuple[int, str]]:
    """Return (line_number, rule_id) for every forbidden ordered-ritual hit."""
    findings: list[tuple[int, str]] = []
    for n, line in enumerate(text.splitlines(), start=1):
        if _SDD_HARD_STOP in line:
            findings.append((n, "AISURF-1"))
        if _NUMBERED_RESERVE.search(line):
            findings.append((n, "AISURF-2"))
        if _ORDERED_READ.search(line):
            findings.append((n, "AISURF-3"))
    return findings


def check_ai_surface_ritual(public_dir: Path) -> list[str]:
    """Scan the dehydrated AI surface for reintroduced ordered-lifecycle ritual.

    Returns doctor report lines. ``[drift]`` lines (one per violation) make
    ``dadaia public doctor`` exit non-zero; an ``[ok]`` summary line is emitted when the
    governed surface is clean.
    """
    public_dir = Path(public_dir)
    if not public_dir.exists():
        return []

    out: list[str] = []
    for path in _governed_files(public_dir):
        rel = path.relative_to(public_dir)
        rel_posix = rel.as_posix()

        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue

        for line_no, rule_id in _ritual_findings(text):
            out.append(
                f"[drift] ai-surface:{rel_posix}:{line_no}: mandatory ordered-lifecycle "
                f"ritual in an always-loaded surface ({rule_id}). The root law states the "
                f"law and names the skill; the procedure belongs in the skill."
            )

    if not out:
        out.append("[ok] ai-surface (no reintroduced lifecycle ritual)")
    return out
