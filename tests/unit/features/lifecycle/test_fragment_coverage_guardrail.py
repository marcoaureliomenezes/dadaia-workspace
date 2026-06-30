"""T-43-8 / WS-5 — the lifecycle fragment-coverage regression guardrail (AC-1..AC-4).

A model-driven lifecycle step must never silently fall back to a generic prompt
(``fragment_id is None``), and no shipped fragment may become an orphan. This guard
discovers every workflow step sequence and asserts:

(a) every prompt-bearing model step (``role != "python"``) names a fragment — would have
    caught the original ``review_security``/``review_code`` generic-prompt holes;
(b) no orphan fragments — every shipped fragment under ``public/lifecycle_fragments/``
    (excluding ``_README.md``) is cited by ≥1 step's ``fragment_id``/``shared_fragment_ids``
    (so ``conflict_scan`` + ``memory_selection`` must stay wired);
(c) per-step enumeration (AC-2/AC-3): the EXACT set of create/review steps that must cite
    ``shared.anti_slop`` and the exact set that must cite ``shared.output_handoff`` each do —
    a single step dropping a shared fragment FAILS this (a ``>=1`` orphan count is insufficient).

Item E: the discovered set of workflow ``_SEQUENCE`` modules is asserted equal to the known
set, so a future 7th workflow cannot silently escape the guardrail.
"""

from __future__ import annotations

import importlib
import pkgutil
import re
from pathlib import Path

from dadaia_workspace.core.models.lifecycle import AgentRuntimeKind
from dadaia_workspace.features.lifecycle import pipeline, workflows
from dadaia_workspace.features.lifecycle.workflows import (
    audit,
    backlog_definition,
    bug_report,
    release_definition,
    research,
)

_FRAGMENT_ROOT = (
    Path(__file__).resolve().parents[4] / "dadaia_workspace" / "public" / "lifecycle_fragments"
)

#: The six workflow step sequences the guardrail iterates (SPEC WS-5).
_SEQUENCES = {
    "release_definition": release_definition._SEQUENCE,
    "audit": audit._SEQUENCE,
    "bug_report": bug_report._SEQUENCE,
    "research": research._SEQUENCE,
    "backlog_definition": backlog_definition._SEQUENCE,
    "pipeline": pipeline.implementation_ladder(AgentRuntimeKind.FAKE),
}

#: Workflow modules that define a module-level ``_SEQUENCE`` (pipeline is the ladder, not a
#: ``_SEQUENCE`` module — handled separately).
_KNOWN_SEQUENCE_MODULES = {
    "audit",
    "backlog_definition",
    "bug_report",
    "release_definition",
    "research",
}

# AC-2 — every create step + every substantive review step cites shared.anti_slop.
_REQUIRED_ANTI_SLOP = {
    "release_definition.release_scope",
    "release_definition.spec_create",
    "release_definition.plan_create",
    "release_definition.tasks_create",
    "release_definition.spec_arch_review",
    "release_definition.plan_review",
    "backlog_definition.backlog_author",
    "pipeline.implement",
    "pipeline.review_security",
    "pipeline.review_code",
}

# AC-3 — every verdict-emitting review step + every audit/bug/research model step cites
# shared.output_handoff.
_REQUIRED_OUTPUT_HANDOFF = {
    "release_definition.spec_arch_review",
    "release_definition.spec_qa_review",
    "release_definition.plan_review",
    "release_definition.tasks_implementability_review",
    "pipeline.review_qa",
    "pipeline.review_security",
    "pipeline.review_code",
    "audit.drift_scan",
    "audit.triage",
    "bug_report.bug_intake",
    "bug_report.dedupe",
    "research.investigate",
    "research.synthesis",
}

# WS-2c — shared.memory_selection is wired to the spec/plan/tasks create + review steps.
_REQUIRED_MEMORY_SELECTION = {
    "release_definition.spec_create",
    "release_definition.plan_create",
    "release_definition.tasks_create",
    "release_definition.spec_arch_review",
    "release_definition.spec_qa_review",
    "release_definition.plan_review",
    "release_definition.tasks_implementability_review",
}


def _qualified_steps() -> dict[str, object]:
    """Map ``<workflow>.<label>`` → step object across all six sequences."""
    out: dict[str, object] = {}
    for name, seq in _SEQUENCES.items():
        for step in seq:
            out[f"{name}.{getattr(step, 'label')}"] = step  # noqa: B009 — heterogeneous step types
    return out


def _citers(tag: str) -> set[str]:
    """Qualified labels of every step citing ``tag`` (fragment_id or shared_fragment_ids)."""
    hits: set[str] = set()
    for qualified, step in _qualified_steps().items():
        shared = set(getattr(step, "shared_fragment_ids", ()))
        if tag in shared or getattr(step, "fragment_id", None) == tag:
            hits.add(qualified)
    return hits


def _shipped_fragment_ids() -> dict[str, str]:
    """Map each shipped fragment id (from frontmatter) → its relative path."""
    shipped: dict[str, str] = {}
    for path in sorted(_FRAGMENT_ROOT.rglob("*.md")):
        if path.name == "_README.md":
            continue
        match = re.search(r"^id:\s*(.+)$", path.read_text(encoding="utf-8"), re.MULTILINE)
        assert match is not None, f"fragment {path} has no `id:` frontmatter"
        shipped[match.group(1).strip()] = str(path.relative_to(_FRAGMENT_ROOT))
    return shipped


def _all_cited_ids() -> set[str]:
    cited: set[str] = set()
    for step in _qualified_steps().values():
        if getattr(step, "fragment_id", None):
            cited.add(step.fragment_id)  # type: ignore[attr-defined]
        cited |= set(getattr(step, "shared_fragment_ids", ()))
    return cited


# ---------------------------------------------------------------------------
# Item E — the discovered workflow set is exactly the known six
# ---------------------------------------------------------------------------


def test_discovered_sequence_modules_match_known_set() -> None:
    """A future 7th workflow with a `_SEQUENCE` cannot silently escape the guardrail."""
    discovered = {
        name
        for _finder, name, _ispkg in pkgutil.iter_modules(workflows.__path__)
        if not name.startswith("_")
        and hasattr(importlib.import_module(f"{workflows.__name__}.{name}"), "_SEQUENCE")
    }
    assert discovered == _KNOWN_SEQUENCE_MODULES, (
        "workflow `_SEQUENCE` modules changed; update the guardrail's enumerated set "
        f"(discovered={sorted(discovered)}, known={sorted(_KNOWN_SEQUENCE_MODULES)})"
    )


# ---------------------------------------------------------------------------
# (a) — no model step falls back to a generic prompt
# ---------------------------------------------------------------------------


def test_no_model_step_uses_generic_prompt() -> None:
    offenders = [
        qualified
        for qualified, step in _qualified_steps().items()
        if getattr(step, "role", "") != "python" and getattr(step, "fragment_id", None) is None
    ]
    assert offenders == [], f"prompt-bearing model steps without a fragment: {offenders}"


# ---------------------------------------------------------------------------
# (b) — no orphan fragments
# ---------------------------------------------------------------------------


def test_no_orphan_fragments() -> None:
    shipped = _shipped_fragment_ids()
    cited = _all_cited_ids()
    orphans = sorted(fid for fid in shipped if fid not in cited)
    assert orphans == [], f"orphan fragments (shipped but uncited): {orphans}"
    # Every citation must resolve to a shipped fragment (no dangling fragment id).
    dangling = sorted(fid for fid in cited if fid not in shipped)
    assert dangling == [], f"dangling fragment citations (cited but not shipped): {dangling}"


def test_conflict_scan_and_memory_selection_are_wired() -> None:
    """The two formerly-orphan fragments (v0.1.43) are each cited by ≥1 step."""
    assert _citers("backlog_definition.conflict_scan")
    assert _citers("shared.memory_selection")


# ---------------------------------------------------------------------------
# (c) — per-step enumeration for the shared disciplines
# ---------------------------------------------------------------------------


def test_anti_slop_cited_by_every_required_step() -> None:
    missing = sorted(_REQUIRED_ANTI_SLOP - _citers("shared.anti_slop"))
    assert missing == [], f"steps missing shared.anti_slop: {missing}"


def test_output_handoff_cited_by_every_required_step() -> None:
    missing = sorted(_REQUIRED_OUTPUT_HANDOFF - _citers("shared.output_handoff"))
    assert missing == [], f"steps missing shared.output_handoff: {missing}"


def test_memory_selection_cited_by_every_required_step() -> None:
    missing = sorted(_REQUIRED_MEMORY_SELECTION - _citers("shared.memory_selection"))
    assert missing == [], f"steps missing shared.memory_selection: {missing}"
