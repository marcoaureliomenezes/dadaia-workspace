"""AC-6 handoff-v1.2 + self_pull instruction adoption — repinned to the FR26 pointer
contract (v0.4.4 SPEC Amendment 1, T-044-55, commit f4ab1779).

FR26 moved ``dadaia-handoff-emitter``'s field tables and its TWO full JSON examples out
of ``SKILL.md``: the skill now POINTS at
``.dadaia/agentic/schemas/handoff-v1.schema.json`` as the single source of field
semantics and never restates it (A26.1/A26.5). The v0.1.62 contract this file used to
pin — "the emitter skill carries exactly two fenced ```json examples, each schema-valid,
each carrying the handoff-v1.2/self_pull tokens" — is RETIRED by that Amendment and went
RED as fallout (flagged by T-044-55, T-044-56 dispatch note): ``_skill_json_examples()``
now finds zero blocks where it used to require two.

This file is repinned here, in place, to the surviving contract. Coverage is never
dropped, only re-aimed at what's true post-FR26:

* the 9 core agent bodies + ``handoff-AGENTS.md`` are UNCHANGED by FR26 and still
  instruct ``handoff-v1.2`` emission with ``self_pull.refs`` — roster completeness and
  the whole-file token check both survive verbatim (``test_roster_completeness_and_...``);
* the emitter skill NAMES the schema path instead of duplicating its content, and
  carries ZERO fenced ```json handoff examples — the two examples are GONE, not merely
  rewritten (A26.2's >=40% per-invocation body drop across the five disclosed skills
  depends on this being a hard zero);
* the schema file the skill points at actually EXISTS on disk and is load-bearing: the
  REAL ``StdlibHandoffValidator`` (the same validator ``dadaia reports validate`` runs in
  production) loads it without hitting an unsupported keyword, accepts a minimal
  conformant handoff-v1.2 instance, and rejects one missing a required field, naming it
  — proving the pointer target is a working contract, not a broken link.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.infrastructure.stdlib_handoff_validator import StdlibHandoffValidator

pytestmark = pytest.mark.contract

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PUBLIC = _REPO_ROOT / "dadaia_workspace" / "public"

_TOKEN_V12 = "handoff-v1.2"
_TOKEN_SELF_PULL = "self_pull"

#: The 9 core agent bodies carrying the emission instruction — the complete roster.
_CORE_AGENT_BODIES: tuple[str, ...] = (
    "agents/ai-engineer.md",
    "agents/code-reviewer.md",
    "agents/product-engineer.md",
    "agents/project-auditor.md",
    "agents/project-manager.md",
    "agents/qa-engineer.md",
    "agents/security-reviewer.md",
    "agents/software-architect.md",
    "agents/software-engineer.md",
)

_DOC_SURFACES: tuple[str, ...] = ("data/handoff-AGENTS.md",)

_EMITTER_SKILL = "skills/dadaia-handoff-emitter/SKILL.md"

#: The 10 whole-file surfaces FR26 left untouched.
_FILE_SURFACES: tuple[str, ...] = (
    *_CORE_AGENT_BODIES,
    *_DOC_SURFACES,
)

#: FR26's pointer text — the schema is named, never re-transcribed (A26.1/A26.5).
_SCHEMA_POINTER_TEXT = ".dadaia/agentic/schemas/handoff-v1.schema.json"

_SCHEMA_PATH = _PUBLIC / "schemas" / "handoff-v1.schema.json"


def _read(rel: str) -> str:
    path = _PUBLIC / rel
    assert path.is_file(), f"enumerated surface missing on disk: {rel}"
    return path.read_text(encoding="utf-8")


def _skill_json_examples(text: str) -> list[str]:
    return re.findall(r"```json\n(.*?)```", text, flags=re.DOTALL)


# ---------------------------------------------------------------------------
# Roster completeness — unchanged by FR26; the whole-file surfaces still instruct
# handoff-v1.2 + self_pull emission verbatim.
# ---------------------------------------------------------------------------


def test_roster_completeness_and_surface_v12_self_pull_adoption() -> None:
    """Roster completeness (the 9 core agent bodies) backs the surface enumeration, and
    every whole-file surface — the 9 agent bodies + handoff-AGENTS.md — still carries
    both the handoff-v1.2 and self_pull tokens. FR26 touched only the emitter skill's
    JSON examples (see the second test below), never this surface."""
    on_disk_core = {f"agents/{p.name}" for p in (_PUBLIC / "agents").glob("*.md")}
    assert on_disk_core == set(_CORE_AGENT_BODIES), (
        "public/agents/*.md roster drifted — update the surface enumeration: "
        f"{sorted(on_disk_core.symmetric_difference(set(_CORE_AGENT_BODIES)))}"
    )

    for surface in _FILE_SURFACES:
        text = _read(surface)
        missing = [t for t in (_TOKEN_V12, _TOKEN_SELF_PULL) if t not in text]
        assert not missing, (
            f"surface {surface} lacks the emission-instruction token(s) {missing} — "
            "every FR4 surface must instruct handoff-v1.2 emission with self_pull.refs "
            "(the atoms actually self-pulled/read; never an unread atom)"
        )


# ---------------------------------------------------------------------------
# FR26 repin — the emitter skill points at the schema instead of duplicating it, and
# the schema it points at is a real, working contract.
#
# Regression guard, unchanged in purpose from the retired
# handoff-emitter-example-omits-required-artifact bug this file used to guard: a doc
# edit that quietly re-adds a stale/broken inline JSON example, or a pointer to a
# schema path that does not exist, must fail here.
# ---------------------------------------------------------------------------


def test_emitter_skill_points_at_schema_with_no_inline_json_example() -> None:
    """FR26/A26.1/A26.5: the emitter skill NAMES the schema path as the single source
    of field semantics instead of duplicating it, and carries ZERO fenced ```json
    handoff examples — the two v0.1.62 examples are gone, not merely rewritten."""
    text = _read(_EMITTER_SKILL)

    assert _SCHEMA_POINTER_TEXT in text, (
        f"{_EMITTER_SKILL} must name the schema path {_SCHEMA_POINTER_TEXT!r} as the "
        "single source of field semantics (FR26/A26.1) — pointer text not found"
    )

    json_examples = _skill_json_examples(text)
    assert json_examples == [], (
        f"{_EMITTER_SKILL} must carry ZERO fenced ```json handoff examples post-FR26 "
        f"(A26.2's per-invocation body-size drop depends on this); found "
        f"{len(json_examples)} — field tables and both examples belong only in "
        f"{_SCHEMA_POINTER_TEXT}"
    )


def test_schema_the_skill_points_at_exists_and_validates() -> None:
    """The schema FR26's pointer names is not a broken link: it exists on disk, the
    REAL StdlibHandoffValidator (the one `dadaia reports validate` runs in production)
    loads it cleanly, accepts a minimal conformant handoff-v1.2 instance, and rejects
    one missing a required field, naming it."""
    assert _SCHEMA_PATH.is_file(), (
        f"the schema the emitter skill points at does not exist on disk: {_SCHEMA_PATH}"
    )

    # Construction alone proves the schema is valid JSON using only supported
    # keywords (StdlibHandoffValidator.__init__ raises HandoffSchemaError otherwise).
    validator = StdlibHandoffValidator(_SCHEMA_PATH)

    conformant: dict[str, Any] = {
        "schema_version": "handoff-v1.2",
        "agent": "software-engineer",
        "context": "dadaia-workspace",
        "produced_at": "2026-08-23T00:00:00Z",
        "scope": "tests/contract/test_handoff_instruction_adoption.py",
        "metrics": {},
        "artifact": {"type": "other"},
        "self_pull": {"refs": ["specs/memory/architecture.md"]},
    }
    errors = list(validator.validate(conformant))
    assert not errors, (
        f"a minimal conformant handoff-v1.2 instance must validate cleanly against the "
        f"schema the emitter skill points at — errors: {errors}"
    )

    missing_artifact = {k: v for k, v in conformant.items() if k != "artifact"}
    errors = list(validator.validate(missing_artifact))
    assert errors, (
        "an instance missing the required 'artifact' object must fail validation — the "
        "schema is not vacuously permissive"
    )
    assert any("artifact" in str(err) for err in errors), (
        f"the validation error(s) must name the missing 'artifact' field: {errors}"
    )
