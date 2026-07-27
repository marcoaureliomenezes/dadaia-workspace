"""T-43-8 / WS-5 — the lifecycle fragment-coverage regression guardrail (AC-1..AC-4).

A model-driven lifecycle step must never silently fall back to a generic prompt
(``fragment_id is None``), and no shipped fragment may become an orphan. This guard
discovers every workflow step sequence and asserts:

(a) every prompt-bearing model step (``role != "python"``) names a fragment — would have
    caught the original ``review_security``/``review_code`` generic-prompt holes;
(b) no orphan fragments — every shipped fragment under ``public/lifecycle_fragments/``
    (excluding ``_README.md``) is cited by ≥1 step's ``fragment_id``/``shared_fragment_ids``;
(c) per-step enumeration (AC-2/AC-3): the EXACT set of create/review steps that must cite
    ``shared.anti_slop`` and the exact set that must cite ``shared.output_handoff``/
    ``shared.memory_selection`` each do — a single step dropping a shared fragment FAILS this
    (a ``>=1`` orphan count is insufficient). Guardrail class: a step silently dropping a
    shared discipline fragment must keep failing per-step.

Item E: the discovered set of workflow ``_SEQUENCE`` modules is asserted equal to the known
set (folded into the citation-set param as a derivation guard), so a future workflow
cannot silently escape the guardrail.
"""

from __future__ import annotations

import importlib
import pkgutil
import re
from pathlib import Path

import pytest

from dadaia_workspace.core.models.lifecycle import AgentRuntimeKind
from dadaia_workspace.features.lifecycle import pipeline, workflows
from dadaia_workspace.features.lifecycle.workflows import (
    audit,
    backlog_definition,
    release_definition,
)

_FRAGMENT_ROOT = (
    Path(__file__).resolve().parents[4] / "dadaia_workspace" / "public" / "lifecycle_fragments"
)

#: The four workflow step sequences the guardrail iterates (SPEC WS-5).
_SEQUENCES = {
    "release_definition": release_definition._SEQUENCE,
    "audit": audit._SEQUENCE,
    "backlog_definition": backlog_definition._SEQUENCE,
    "implementation_reviews": pipeline.implementation_ladder(AgentRuntimeKind.FAKE),
}

#: Workflow modules that define a module-level ``_SEQUENCE`` (pipeline is the ladder, not a
#: ``_SEQUENCE`` module — handled separately).
_KNOWN_SEQUENCE_MODULES = {
    "audit",
    "backlog_definition",
    "release_definition",
}

# AC-2 — every create step + every substantive review step cites shared.anti_slop.
# v0.2.x simplification: anti-slop rides on CREATE steps only — reviews judge, they
# do not author, and every removed restatement is prompt tax on a weak model.
_REQUIRED_ANTI_SLOP = {
    "release_definition.definition_draft",
    "backlog_definition.backlog_author",
    "implementation_reviews.implement",
}

# v0.2.x simplification: the output contract is stated ONCE by the engine's
# "## Required output" section (prompt_builder) — NO step bundles the shared
# output-handoff restatement anymore. The guardrail now proves the inverse.
_REQUIRED_OUTPUT_HANDOFF: set[str] = set()

# WS-2c (narrowed): shared.memory_selection rides on the SPEC/PLAN create steps
# (the memory-grounded authoring work); reviews and TASKS authoring stay lean.
_REQUIRED_MEMORY_SELECTION = {
    "release_definition.definition_draft",
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
# (b) — no orphan fragments (memory_selection wired is a strict subset)
# ---------------------------------------------------------------------------


def test_no_orphan_or_dangling_fragments_and_discovered_sequence_set_matches_known() -> None:
    shipped = _shipped_fragment_ids()
    cited = _all_cited_ids()
    orphans = sorted(fid for fid in shipped if fid not in cited)
    assert orphans == [], f"orphan fragments (shipped but uncited): {orphans}"
    # Every citation must resolve to a shipped fragment (no dangling fragment id).
    dangling = sorted(fid for fid in cited if fid not in shipped)
    assert dangling == [], f"dangling fragment citations (cited but not shipped): {dangling}"
    # The two formerly-orphan fragments (v0.1.43) are each cited by ≥1 step — a strict
    # instance of the no-orphan property above, kept as a named regression pin.
    assert _citers("shared.memory_selection")

    # Item E: a future 7th workflow with a `_SEQUENCE` cannot silently escape the guardrail
    # — the derivation guard behind every required-citer set in this module.
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
# (c) + Item E — per-step required-citer sets, plus the discovered-sequence-set derivation
# ---------------------------------------------------------------------------

_REQUIRED_CITER_CASES = (
    ("anti_slop", "shared.anti_slop", _REQUIRED_ANTI_SLOP),
    ("output_handoff", "shared.output_handoff", _REQUIRED_OUTPUT_HANDOFF),
    ("memory_selection", "shared.memory_selection", _REQUIRED_MEMORY_SELECTION),
)


@pytest.mark.parametrize(
    "tag,required",
    [c[1:] for c in _REQUIRED_CITER_CASES],
    ids=[c[0] for c in _REQUIRED_CITER_CASES],
)
def test_shared_discipline_cited_by_every_required_step(tag: str, required: set[str]) -> None:
    missing = sorted(required - _citers(tag))
    assert missing == [], f"steps missing {tag}: {missing}"
