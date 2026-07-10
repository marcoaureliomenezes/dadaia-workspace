"""Unit tests for the lifecycle persona loader (AC-1 / T-44-3).

Covers the shipped persona library AND negative fixtures (tmp roots, not ``public/``):
forbidden-token body, dangling ``source_agent``, missing required key, non-boolean
harness_universal.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.lifecycle.personas.loader import (
    Persona,
    PersonaLoader,
    PersonaNotFoundError,
    PersonaValidationError,
    forbidden_token_in,
    list_personas,
    load_persona,
    validate_all,
)

#: The 8 non-PM core roles that MUST each have a persona atom (SPEC AC-1). PM is excluded.
_EXPECTED_ROLES = {
    "ai-engineer",
    "code-reviewer",
    "product-engineer",
    "project-auditor",
    "qa-engineer",
    "security-reviewer",
    "software-architect",
    "software-engineer",
}

_VALID_FRONTMATTER = """\
---
id: software-engineer
role: software-engineer
summary: A one-line mandate for the role.
source_agent: agents/software-engineer.md
harness_universal: true
---

You are acting as the software-engineer. Implement the change with tests.
"""


# ---------------------------------------------------------------------------
# ① shipped-library invariants: 8 non-PM roles / no PM atom / role==id / source_agent
#    resolves / harness_universal / token lint / validate_all non-empty
# ---------------------------------------------------------------------------


def test_shipped_library_invariants() -> None:
    personas = validate_all()
    assert personas, "expected the packaged persona library to be non-empty"
    assert all(isinstance(p, Persona) for p in personas)

    ids = {p.id for p in list_personas()}
    assert ids == _EXPECTED_ROLES
    # project-manager is the Layer-1 orchestrator — it must NOT have a persona atom (D-1).
    assert "project-manager" not in ids

    loader = PersonaLoader()
    for persona in loader.validate_all():
        assert persona.role == persona.id
        assert persona.harness_universal is True
        assert persona.source_agent == f"agents/{persona.id}.md"

    for persona in personas:
        assert forbidden_token_in(persona.body) is None, (
            f"shipped persona {persona.id} contains a harness-specific token"
        )


# ---------------------------------------------------------------------------
# ② load round-trip + unknown raises + load_optional shared/PM/empty/mapped
# ---------------------------------------------------------------------------


def test_load_round_trip_unknown_raises_and_load_optional_matrix() -> None:
    persona = load_persona("product-engineer")
    assert persona.id == "product-engineer"
    assert persona.role == "product-engineer"
    assert persona.body
    assert persona.source_agent == "agents/product-engineer.md"

    with pytest.raises(PersonaNotFoundError):
        load_persona("project-manager")

    loader = PersonaLoader()
    assert loader.load_optional("shared") is None
    assert loader.load_optional("project-manager") is None
    assert loader.load_optional("") is None
    assert loader.load_optional("product-engineer") is not None


# ---------------------------------------------------------------------------
# ③ negative fixtures param: forbidden-token / dangling source_agent / missing key /
#    non-boolean
# ---------------------------------------------------------------------------


def _write_persona(tmp_path: Path, text: str, *, with_agent: bool = True) -> PersonaLoader:
    """Write a persona + (optionally) its sibling agent file under a tmp public root."""
    public = tmp_path / "public"
    personas = public / "personas"
    agents = public / "agents"
    personas.mkdir(parents=True, exist_ok=True)
    agents.mkdir(parents=True, exist_ok=True)
    (personas / "software-engineer.md").write_text(text, encoding="utf-8")
    if with_agent:
        (agents / "software-engineer.md").write_text("# agent\n", encoding="utf-8")
    return PersonaLoader(root=personas)


_NEGATIVE_CASES = (
    (
        "forbidden-token",
        lambda t: t.rsplit("\n\n", 1)[0] + "\n\nUse codex exec to run this step.\n",
        True,
        "harness-specific token",
    ),
    (
        "dangling-source-agent",
        lambda t: t,
        False,
        "dangling",
    ),
    (
        "missing-required-key",
        lambda t: t.replace("summary: A one-line mandate for the role.\n", ""),
        True,
        "summary",
    ),
    (
        "non-boolean-harness-universal",
        lambda t: t.replace("harness_universal: true", "harness_universal: yes-please"),
        True,
        "harness_universal",
    ),
)


@pytest.mark.parametrize(
    "mutate,with_agent,match",
    [c[1:] for c in _NEGATIVE_CASES],
    ids=[c[0] for c in _NEGATIVE_CASES],
)
def test_negative_fixtures_rejected(tmp_path: Path, mutate, with_agent: bool, match: str) -> None:
    text = mutate(_VALID_FRONTMATTER)
    loader = _write_persona(tmp_path, text, with_agent=with_agent)
    with pytest.raises(PersonaValidationError, match=match):
        loader.validate_all()

    # Positive control (runs once per param, cheap, proves the mutator is the sole cause of
    # rejection): the UNMUTATED valid frontmatter loads cleanly under the same fixture root.
    control_loader = _write_persona(tmp_path / "control", _VALID_FRONTMATTER)
    control_personas = control_loader.validate_all()
    assert len(control_personas) == 1
    assert control_personas[0].id == "software-engineer"
