"""Unit tests for the lifecycle persona loader (AC-1 / T-44-3).

Covers the shipped persona library AND negative fixtures (tmp roots, not ``public/``):
forbidden-token body, dangling ``source_agent``, missing required key.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.lifecycle.personas.loader import (
    Persona,
    PersonaLoader,
    PersonaNotFoundError,
    PersonaValidationError,
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
# Shipped persona library — load + validate the real packaged tree.
# ---------------------------------------------------------------------------


def test_validate_all_loads_every_shipped_persona() -> None:
    personas = validate_all()
    assert personas, "expected the packaged persona library to be non-empty"
    assert all(isinstance(p, Persona) for p in personas)


def test_persona_id_set_equals_the_8_non_pm_roles() -> None:
    ids = {p.id for p in list_personas()}
    assert ids == _EXPECTED_ROLES
    # project-manager is the Layer-1 orchestrator — it must NOT have a persona atom (D-1).
    assert "project-manager" not in ids


def test_every_persona_role_matches_its_id_and_resolves_source_agent() -> None:
    loader = PersonaLoader()
    for persona in loader.validate_all():
        assert persona.role == persona.id
        assert persona.harness_universal is True
        assert persona.source_agent == f"agents/{persona.id}.md"


def test_load_persona_by_role_round_trips() -> None:
    persona = load_persona("product-engineer")
    assert persona.id == "product-engineer"
    assert persona.role == "product-engineer"
    assert persona.body
    assert persona.source_agent == "agents/product-engineer.md"


def test_load_persona_unknown_role_raises() -> None:
    with pytest.raises(PersonaNotFoundError):
        load_persona("project-manager")


def test_load_optional_returns_none_for_shared_and_unmapped() -> None:
    loader = PersonaLoader()
    assert loader.load_optional("shared") is None
    assert loader.load_optional("project-manager") is None
    assert loader.load_optional("") is None
    assert loader.load_optional("product-engineer") is not None


def test_every_shipped_persona_passes_the_token_lint() -> None:
    from dadaia_workspace.features.lifecycle.personas.loader import forbidden_token_in

    for persona in validate_all():
        assert forbidden_token_in(persona.body) is None, (
            f"shipped persona {persona.id} contains a harness-specific token"
        )


# ---------------------------------------------------------------------------
# Negative fixtures — tmp roots, NOT public/.
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


def test_valid_fixture_loads(tmp_path: Path) -> None:
    loader = _write_persona(tmp_path, _VALID_FRONTMATTER)
    personas = loader.validate_all()
    assert len(personas) == 1
    assert personas[0].id == "software-engineer"


def test_forbidden_token_body_raises(tmp_path: Path) -> None:
    text = _VALID_FRONTMATTER.rsplit("\n\n", 1)[0] + "\n\nUse codex exec to run this step.\n"
    loader = _write_persona(tmp_path, text)
    with pytest.raises(PersonaValidationError, match="harness-specific token"):
        loader.validate_all()


def test_dangling_source_agent_raises(tmp_path: Path) -> None:
    # The sibling agents/software-engineer.md is absent — the pointer is dangling.
    loader = _write_persona(tmp_path, _VALID_FRONTMATTER, with_agent=False)
    with pytest.raises(PersonaValidationError, match="dangling"):
        loader.validate_all()


def test_missing_required_key_raises(tmp_path: Path) -> None:
    text = _VALID_FRONTMATTER.replace("summary: A one-line mandate for the role.\n", "")
    loader = _write_persona(tmp_path, text)
    with pytest.raises(PersonaValidationError, match="summary"):
        loader.validate_all()


def test_non_boolean_harness_universal_raises(tmp_path: Path) -> None:
    text = _VALID_FRONTMATTER.replace("harness_universal: true", "harness_universal: yes-please")
    loader = _write_persona(tmp_path, text)
    with pytest.raises(PersonaValidationError, match="harness_universal"):
        loader.validate_all()
