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

Exemption rule (avoids false positives)
---------------------------------------
A body is **exempt** (ritual allowed) when EITHER:

1. it carries the **non-authoritative banner** — the marker
   ``**Not the lifecycle enforcement mechanism.**`` (the ai-engineer relabelled the
   retained lifecycle skills with this blockquote banner); OR
2. it lives under ``public/lifecycle_fragments/`` — fragments ARE the ritual, by design.

So the check fails ONLY when ritual appears in an **un-bannered** governed surface.

Governed surfaces (scan scope) — v0.1.24 conservative
-----------------------------------------------------
Per SPEC §3.12 the dehydration that ships this release is **AGENTS.md + the lifecycle
skills**; deep dehydration of every persona/rule is *explicitly deferred* to a follow-up
(personas legitimately carry their own per-role TDD/reservation discipline, which is
authoritative, not "the lifecycle enforcement mechanism"). The doctor therefore polices
exactly the surfaces this release dehydrated:

- ``public/data/AGENTS.md`` and ``public/scaffold/AGENTS.md`` — fully dehydrated; NOT
  banner-eligible. Any forbidden pattern here is always a regression.
- ``public/skills/*/SKILL.md`` — the lifecycle skills; banner-exempt.

``public/agents/*.md`` and ``public/rules/*.md`` are intentionally **out of scope this
release** (see ``DEFERRED_SCAN_GLOBS``); extend ``_GOVERNED`` when their dehydration
ships so the same banner-exemption logic applies to them.
"""

from __future__ import annotations

import re
from pathlib import Path

from dadaia_workspace.core.models.doctor_report import DoctorLine, DoctorStatus

# The non-authoritative banner marker the ai-engineer added to retained lifecycle
# skills (a blockquote line: "> **Not the lifecycle enforcement mechanism.** ...").
BANNER_MARKER = "**Not the lifecycle enforcement mechanism.**"

# Fragment library root (relative to the public dir). Bodies here are exempt by design.
_FRAGMENTS_DIRNAME = "lifecycle_fragments"

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
    "skills/*/SKILL.md",
)

# Surfaces whose dehydration is deferred (SPEC §3.12); documented for the follow-up.
DEFERRED_SCAN_GLOBS: tuple[str, ...] = (
    "agents/*.md",
    "rules/*.md",
)

# Surfaces that are fully dehydrated and therefore NOT banner-eligible: ritual in them
# is always a regression. (Skills remain banner-exempt for the migration window.)
_NON_BANNER_ELIGIBLE: tuple[str, ...] = (
    "data/AGENTS.md",
    "scaffold/AGENTS.md",
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


def _is_banner_eligible(rel_posix: str) -> bool:
    return rel_posix not in _NON_BANNER_ELIGIBLE


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


def check_ai_surface_ritual(public_dir: Path) -> list[DoctorLine]:
    """Scan the dehydrated AI surface for reintroduced ordered-lifecycle ritual.

    Returns doctor report lines. ``[drift]`` lines (one per violation) make
    ``dadaia public doctor`` exit non-zero; an ``[ok]`` summary line is emitted when the
    governed surface is clean. A body is exempt when it carries the non-authoritative
    banner (banner-eligible surfaces only) or lives under ``lifecycle_fragments/``.
    """
    public_dir = Path(public_dir)
    if not public_dir.exists():
        return []

    out: list[DoctorLine] = []
    for path in _governed_files(public_dir):
        rel = path.relative_to(public_dir)
        rel_posix = rel.as_posix()

        # Fragments are exempt by design (defensive — fragments are not in the globs).
        if _FRAGMENTS_DIRNAME in rel.parts:
            continue

        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue

        findings = _ritual_findings(text)
        if not findings:
            continue

        # Banner exemption — only for banner-eligible surfaces (skills), not the
        # fully-dehydrated AGENTS.md pair.
        if _is_banner_eligible(rel_posix) and BANNER_MARKER in text:
            continue

        for line_no, rule_id in findings:
            out.append(
                DoctorLine(
                    DoctorStatus.DRIFT,
                    f"ai-surface:{rel_posix}:{line_no}: mandatory ordered-lifecycle "
                    f"ritual reintroduced into a dehydrated surface ({rule_id}). Lifecycle is "
                    f"owned by the dadaia-workflows — point at them, or carry the "
                    f"non-authoritative banner ({BANNER_MARKER!r}).",
                )
            )

    if not out:
        out.append(DoctorLine(DoctorStatus.OK, "ai-surface (no reintroduced lifecycle ritual)"))
    return out
