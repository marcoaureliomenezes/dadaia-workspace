"""Contract — the agentic-entity derivation law (constitution §12.5).

dadaia-workspace defines its scaffolded surface as ABSTRACT, harness-agnostic
entities first (``dadaia_workspace/public/entities/registry.json``) and only then
derives per-harness implementations:

  - no scaffolded core sub-agent without a **Persona**,
  - no wired core hook without a **Deterministic Behavior**,
  - no projected core rule file without an **Abstract Rule**,
  - skills and AGENTS.md are **universal** (read natively by every harness).

These tests pin the derivation mechanically, so adding a core agent .md, wiring
a new ``dadaia_workspace.hooks.*`` entrypoint, or projecting a new core rule
file WITHOUT first defining its abstract entity fails the suite — the
prohibition the operator demanded, enforced at the source. Operator-created
entities live in the instantiated workspace, not in the package, so they are
structurally out of this contract's reach (by design).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from dadaia_workspace.core.harness_registry import L1_ENTRY_HARNESSES
from dadaia_workspace.core.models.doctor_report import DoctorLine, DoctorStatus
from dadaia_workspace.features.panel.entities import (
    core_skills,
    load_registry,
    persona_ids,
)

_PKG_ROOT = Path(__file__).resolve().parents[2] / "dadaia_workspace"
_PUBLIC = _PKG_ROOT / "public"


def test_registry_loads_and_is_well_formed() -> None:
    registry = load_registry()
    ids = [p["id"] for p in registry["personas"]]
    assert len(ids) == len(set(ids)), "duplicate persona ids"
    for persona in registry["personas"]:
        assert persona["mandate"].strip(), f"persona {persona['id']} has an empty mandate"
    for section in ("behaviors", "rules"):
        for entity in registry[section]:
            assert entity["mandate"].strip(), f"{section}:{entity['id']} has an empty mandate"
            assert entity["implementations"], f"{section}:{entity['id']} derives nothing"


def test_every_core_subagent_derives_from_a_persona_and_vice_versa() -> None:
    """public/agents/*.md ↔ registry personas is a BIJECTION.

    A scaffolded sub-agent file with no Persona is a forbidden underived
    implementation; a Persona with no sub-agent file is a dead abstraction.
    """
    scaffolded = {p.stem for p in (_PUBLIC / "agents").glob("*.md")}
    abstract = set(persona_ids(load_registry()))
    assert scaffolded == abstract, (
        f"sub-agents without a Persona: {sorted(scaffolded - abstract)}; "
        f"Personas without a sub-agent: {sorted(abstract - scaffolded)}"
    )


def test_every_wired_core_hook_derives_from_a_deterministic_behavior() -> None:
    """Every ``dadaia_workspace.hooks.*`` entrypoint the installer wires must be
    named by some Deterministic Behavior's implementations."""
    runtime_config = (_PKG_ROOT / "infrastructure" / "runtime_config.py").read_text(
        encoding="utf-8"
    )
    wired = set(re.findall(r"dadaia_workspace\.hooks\.([a-z_]+)", runtime_config))
    assert wired, "no wired hook entrypoints found — the extraction regex broke"
    behaviors_blob = json.dumps(load_registry()["behaviors"])
    underived = {
        module for module in wired if f"dadaia_workspace.hooks.{module}" not in behaviors_blob
    }
    assert not underived, (
        f"core hook entrypoints wired without an abstract Deterministic Behavior: "
        f"{sorted(underived)}"
    )


def test_behaviors_cover_every_entry_harness() -> None:
    """A Deterministic Behavior is workspace law — it must be derived for ALL
    entry harnesses, and never for an unknown one."""
    harnesses = set(L1_ENTRY_HARNESSES)
    for behavior in load_registry()["behaviors"]:
        implemented = set(behavior["implementations"])
        assert implemented == harnesses, (
            f"behavior {behavior['id']}: implementations {sorted(implemented)} "
            f"!= entry harnesses {sorted(harnesses)}"
        )


def test_rule_implementations_target_known_harnesses_and_cover_the_law_projections() -> None:
    registry = load_registry()
    harnesses = set(L1_ENTRY_HARNESSES)
    rules_blob = json.dumps(registry["rules"])

    for rule in registry["rules"]:
        unknown = set(rule["implementations"]) - harnesses
        assert not unknown, f"rule {rule['id']} derives for unknown harnesses {sorted(unknown)}"

    # The DADAIA.md law projection must be derived for every entry harness.
    law_rule = next(r for r in registry["rules"] if r["id"] == "workspace-law")
    assert set(law_rule["implementations"]) == harnesses
    for impl in law_rule["implementations"].values():
        assert "DADAIA.md" in impl

    # The one non-law core rule file the installer projects (codex Starlark
    # command policy — public_assets.install) must trace to an abstract rule.
    assert "dadaia-command-policy.rules" in rules_blob, (
        "the projected codex command-policy rule file has no abstract rule in the registry"
    )


def test_universal_entities_match_the_scaffold() -> None:
    """Universal = read natively by every harness: skills under
    ``.agents/skills/`` (the installer's actual target) and the AGENTS.md
    guardrail files."""
    universal = load_registry()["universal"]
    assert universal["skills_root"] == ".agents/skills/"
    assert any("AGENTS.md" in str(entry) for entry in universal["agents_md"])

    skills = core_skills()
    packaged = {d.name for d in (_PUBLIC / "skills").iterdir() if d.is_dir()}
    assert {name for name, _ in skills} == packaged
    for name, description in skills:
        assert description.strip(), f"core skill {name} has no frontmatter description"


def test_doctor_check_blocks_on_missing_registry(tmp_path: Path) -> None:
    from dadaia_workspace.infrastructure.codex_doctor import check_entities_derivation

    lines = check_entities_derivation(tmp_path)
    assert len(lines) == 1 and lines[0].status.blocking
    assert "registry unreadable" in lines[0].text


def test_doctor_check_blocks_on_underived_subagent(tmp_path: Path) -> None:
    """A core sub-agent .md with no Persona is DRIFT (blocking) — the prohibition."""
    from dadaia_workspace.infrastructure.codex_doctor import check_entities_derivation

    (tmp_path / "entities").mkdir()
    (tmp_path / "entities" / "registry.json").write_text(
        json.dumps(
            {
                "schema_version": "agentic-entities-v1",
                "personas": [{"id": "known", "mandate": "m"}],
                "behaviors": [],
                "rules": [],
                "universal": {},
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "agents").mkdir()
    (tmp_path / "agents" / "known.md").write_text("x", encoding="utf-8")
    (tmp_path / "agents" / "rogue.md").write_text("x", encoding="utf-8")

    lines = check_entities_derivation(tmp_path)
    assert any("'rogue' has no abstract Persona" in line.text for line in lines)
    assert all(line.status.blocking for line in lines)


def test_doctor_check_passes_on_the_packaged_registry() -> None:
    from dadaia_workspace.infrastructure.codex_doctor import check_entities_derivation

    lines = check_entities_derivation(_PUBLIC)
    assert len(lines) == 1 and not lines[0].status.blocking
    assert "entities-derivation" in lines[0].text


def _write_registry(tmp_path: Path, payload: object) -> None:
    (tmp_path / "entities").mkdir()
    (tmp_path / "entities" / "registry.json").write_text(json.dumps(payload), encoding="utf-8")


def _assert_single_typed_blocking_line(lines: list[DoctorLine]) -> None:
    """FR3.3 (ENT-DERIVE-1): a malformed-but-valid-JSON shape must yield exactly one
    typed **ERROR** DoctorLine from the parse seam itself — never a Python traceback
    (AttributeError/TypeError), and never the *wrong* DRIFT line a downstream check
    would fabricate by silently misreading the malformed shape (e.g. iterating a
    string's characters as if they were harness names)."""
    assert len(lines) == 1, lines
    assert lines[0].status is DoctorStatus.ERROR, lines
    assert "entities-derivation:" in lines[0].text
    assert "(ENT-DERIVE-1)" in lines[0].text


def test_doctor_check_blocks_on_non_dict_top_level(tmp_path: Path) -> None:
    """Top-level JSON list instead of an object must not raise AttributeError on
    ``registry.get(...)`` downstream — it must yield a typed blocking line."""
    from dadaia_workspace.infrastructure.codex_doctor import check_entities_derivation

    _write_registry(tmp_path, ["not", "a", "dict"])

    lines = check_entities_derivation(tmp_path)
    _assert_single_typed_blocking_line(lines)


def test_doctor_check_blocks_on_personas_as_list_of_strings(tmp_path: Path) -> None:
    """``personas`` entries must be objects — a list of bare strings must not raise
    AttributeError on ``p.get("id")`` downstream."""
    from dadaia_workspace.infrastructure.codex_doctor import check_entities_derivation

    _write_registry(
        tmp_path,
        {
            "schema_version": "agentic-entities-v1",
            "personas": ["known", "rogue"],
            "behaviors": [],
            "rules": [],
            "universal": {},
        },
    )

    lines = check_entities_derivation(tmp_path)
    _assert_single_typed_blocking_line(lines)


def test_doctor_check_blocks_on_personas_as_dict(tmp_path: Path) -> None:
    """``personas`` as a mapping instead of a list must not silently iterate its
    keys as if they were persona objects."""
    from dadaia_workspace.infrastructure.codex_doctor import check_entities_derivation

    _write_registry(
        tmp_path,
        {
            "schema_version": "agentic-entities-v1",
            "personas": {"known": {"id": "known"}},
            "behaviors": [],
            "rules": [],
            "universal": {},
        },
    )

    lines = check_entities_derivation(tmp_path)
    _assert_single_typed_blocking_line(lines)


def test_doctor_check_blocks_on_non_dict_behavior_element(tmp_path: Path) -> None:
    """A ``behaviors`` list containing a non-dict element must not raise
    AttributeError on ``behavior.get(...)`` downstream."""
    from dadaia_workspace.infrastructure.codex_doctor import check_entities_derivation

    _write_registry(
        tmp_path,
        {
            "schema_version": "agentic-entities-v1",
            "personas": [],
            "behaviors": [{"id": "b1", "implementations": {}}, "rogue-behavior"],
            "rules": [],
            "universal": {},
        },
    )

    lines = check_entities_derivation(tmp_path)
    _assert_single_typed_blocking_line(lines)


def test_doctor_check_blocks_on_implementations_as_int(tmp_path: Path) -> None:
    """``implementations`` must be a mapping — an int must not raise TypeError on
    ``set(behavior.get("implementations", {}))`` downstream."""
    from dadaia_workspace.infrastructure.codex_doctor import check_entities_derivation

    _write_registry(
        tmp_path,
        {
            "schema_version": "agentic-entities-v1",
            "personas": [],
            "behaviors": [{"id": "b1", "implementations": 42}],
            "rules": [],
            "universal": {},
        },
    )

    lines = check_entities_derivation(tmp_path)
    _assert_single_typed_blocking_line(lines)


def test_doctor_check_blocks_on_implementations_as_string(tmp_path: Path) -> None:
    """The trap case: ``implementations`` as a bare string is iterable, so
    ``set("codex")`` silently produces a set of characters — a WRONG DRIFT line,
    not a crash. This must become a typed error, not a misleading DRIFT diagnosis."""
    from dadaia_workspace.infrastructure.codex_doctor import check_entities_derivation

    _write_registry(
        tmp_path,
        {
            "schema_version": "agentic-entities-v1",
            "personas": [],
            "behaviors": [{"id": "b1", "implementations": "codex"}],
            "rules": [],
            "universal": {},
        },
    )

    lines = check_entities_derivation(tmp_path)
    _assert_single_typed_blocking_line(lines)
