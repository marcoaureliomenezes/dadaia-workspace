"""ENT-DERIVE-1 behavioral-fidelity mutation fixtures (v0.4.3 T-043-35).

Intent: CONTRACT — v0.4.3 A22.5

Before this task, ``check_entities_derivation`` proved pure NAME/SHAPE matching only:
a Persona ↔ core sub-agent bijection by filename stem, and a Deterministic Behavior's
``implementations`` dict having exactly the right harness KEYS. Neither check ever
opened a scaffolded agent file's own content, nor followed a ``dadaia_workspace.<module>``
reference embedded in a Behavior's free-text implementation description back to a real
source file. A stub/blank persona file at the right filename, an internal identity
swap (frontmatter ``name:`` diverging from its own filename), or a hook module quietly
deleted while its registry entry is left untouched (the concrete "a hook silently stops
enforcing" drift the T-043-32 scoping note names) all passed silently.

Every fixture below builds an isolated scratch entity tree under ``tmp_path`` — never
the live package tree — mutates exactly one aspect of an otherwise-clean baseline, and
asserts ``check_entities_derivation`` reports the drift as a BLOCKING line. The
already-name/shape-covered drift classes (orphan sub-agent, dead Persona, missing
harness key) are included too, under the same scratch-render methodology, so this file
is the single exhaustive fixture set for every drift class ENT-DERIVE-1 defends.
"""

from __future__ import annotations

import json
from pathlib import Path

from dadaia_workspace.core.models.doctor_report import DoctorStatus
from dadaia_workspace.infrastructure.codex_doctor import check_entities_derivation

# ---------------------------------------------------------------------------
# Scratch-render builder
# ---------------------------------------------------------------------------


def _build_clean_scratch(root: Path) -> Path:
    """Build a minimal, fully-conformant scratch entity tree under *root*.

    Mirrors the real package shape (``public_dir.parent`` is the package root a
    Behavior's ``dadaia_workspace.<module>`` reference resolves against):

    - ``root/public/entities/registry.json`` — 2 Personas, 1 Behavior citing
      ``dadaia_workspace.hooks.pre_gate``.
    - ``root/public/agents/{alpha,beta}.md`` — both correctly bijected AND
      internally self-consistent (frontmatter ``name:`` == filename stem).
    - ``root/hooks/pre_gate.py`` — the module the one Behavior's implementation
      text names, so the baseline is genuinely drift-free.

    Returns the ``public_dir`` to pass into ``check_entities_derivation``.
    """
    public_dir = root / "public"
    (public_dir / "entities").mkdir(parents=True)
    (public_dir / "agents").mkdir(parents=True)
    (root / "hooks").mkdir(parents=True)

    registry = {
        "schema_version": "agentic-entities-v1",
        "personas": [
            {"id": "alpha", "mandate": "alpha mandate"},
            {"id": "beta", "mandate": "beta mandate"},
        ],
        "behaviors": [
            {
                "id": "gate-behavior",
                "mandate": "gates something",
                "implementations": {
                    "claude": "PreToolUse hook via dadaia_workspace.hooks.pre_gate",
                    "codex": ".codex/hooks.json wrapper -> the same gate",
                    "kimi-code": "managed hook block -> the same gate",
                },
            }
        ],
        "rules": [],
        "universal": {},
    }
    (public_dir / "entities" / "registry.json").write_text(json.dumps(registry), encoding="utf-8")

    for pid in ("alpha", "beta"):
        (public_dir / "agents" / f"{pid}.md").write_text(
            f"---\nname: {pid}\ndescription: test persona {pid}\n---\nBody.\n",
            encoding="utf-8",
        )
    (root / "hooks" / "pre_gate.py").write_text("# stub gate module\n", encoding="utf-8")
    return public_dir


def _texts(lines: list[object]) -> list[str]:
    return [line.text for line in lines]  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Baseline — the clean render must pass, or every fixture below is meaningless
# ---------------------------------------------------------------------------


def test_clean_scratch_render_passes(tmp_path: Path) -> None:
    public_dir = _build_clean_scratch(tmp_path)

    lines = check_entities_derivation(public_dir)

    assert len(lines) == 1
    assert lines[0].status is DoctorStatus.OK


# ---------------------------------------------------------------------------
# Pre-existing name/shape drift classes — same scratch-render methodology
# ---------------------------------------------------------------------------


def test_orphan_subagent_without_persona_blocks(tmp_path: Path) -> None:
    public_dir = _build_clean_scratch(tmp_path)
    (public_dir / "agents" / "rogue.md").write_text(
        "---\nname: rogue\n---\nBody.\n", encoding="utf-8"
    )

    lines = check_entities_derivation(public_dir)

    assert any("'rogue' has no abstract Persona" in text for text in _texts(lines))
    assert all(line.status.blocking for line in lines)  # type: ignore[attr-defined]


def test_dead_persona_without_subagent_blocks(tmp_path: Path) -> None:
    public_dir = _build_clean_scratch(tmp_path)
    (public_dir / "agents" / "beta.md").unlink()

    lines = check_entities_derivation(public_dir)

    assert any("Persona 'beta' has no derived core" in text for text in _texts(lines))
    assert all(line.status.blocking for line in lines)  # type: ignore[attr-defined]


def test_behavior_missing_harness_key_blocks(tmp_path: Path) -> None:
    public_dir = _build_clean_scratch(tmp_path)
    registry_path = public_dir / "entities" / "registry.json"
    data = json.loads(registry_path.read_text(encoding="utf-8"))
    del data["behaviors"][0]["implementations"]["kimi-code"]
    registry_path.write_text(json.dumps(data), encoding="utf-8")

    lines = check_entities_derivation(public_dir)

    assert any("expected every entry harness" in text for text in _texts(lines))
    assert all(line.status.blocking for line in lines)  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# NEW behavioral drift classes (A22.5) — RED against the pre-T-043-35 check
# ---------------------------------------------------------------------------


def test_persona_stub_body_blocks(tmp_path: Path) -> None:
    """A scaffolded agent file at the right filename with no parseable frontmatter
    identity (a blank stub, or malformed YAML) is DRIFT — filename-only bijection
    would pass this silently."""
    public_dir = _build_clean_scratch(tmp_path)
    (public_dir / "agents" / "alpha.md").write_text(
        "placeholder — nothing but prose, no frontmatter block\n", encoding="utf-8"
    )

    lines = check_entities_derivation(public_dir)

    assert any("'alpha' has no parseable frontmatter identity" in text for text in _texts(lines))
    assert all(line.status.blocking for line in lines)  # type: ignore[attr-defined]


def test_persona_identity_mismatch_blocks(tmp_path: Path) -> None:
    """A scaffolded agent file at the right filename but declaring a DIFFERENT
    persona's identity in its own frontmatter (a copy-paste swap) is DRIFT — the
    filename alone lies about which persona actually lives at that path."""
    public_dir = _build_clean_scratch(tmp_path)
    (public_dir / "agents" / "alpha.md").write_text(
        "---\nname: beta\ndescription: copy-pasted from the wrong persona\n---\nBody.\n",
        encoding="utf-8",
    )

    lines = check_entities_derivation(public_dir)

    assert any(
        "frontmatter name 'beta' does not match its filename" in text for text in _texts(lines)
    )
    assert all(line.status.blocking for line in lines)  # type: ignore[attr-defined]


def test_behavior_implementation_module_reference_broken_blocks(tmp_path: Path) -> None:
    """The concrete "a hook silently stops enforcing" drift (T-043-32 scoping note):
    the Behavior's registry entry still names ``dadaia_workspace.hooks.pre_gate`` as
    its implementation, but the module itself is gone from the source tree — the
    registry entry is now a claim about nothing. Pure harness-key coverage cannot see
    this: the ``implementations`` dict still has all three keys."""
    public_dir = _build_clean_scratch(tmp_path)
    (tmp_path / "hooks" / "pre_gate.py").unlink()

    lines = check_entities_derivation(public_dir)

    assert any(
        "references module 'dadaia_workspace.hooks.pre_gate' which no longer exists" in text
        for text in _texts(lines)
    )
    assert all(line.status.blocking for line in lines)  # type: ignore[attr-defined]


def test_behavior_implementation_module_reference_as_package_blocks(tmp_path: Path) -> None:
    """A referenced module resolved as a package (``__init__.py``) is honored — only
    when NEITHER the bare-module form nor the package form exists is it DRIFT."""
    public_dir = _build_clean_scratch(tmp_path)
    (tmp_path / "hooks" / "pre_gate.py").unlink()
    package_dir = tmp_path / "hooks" / "pre_gate"
    package_dir.mkdir()
    (package_dir / "__init__.py").write_text("# now a package\n", encoding="utf-8")

    lines = check_entities_derivation(public_dir)

    assert len(lines) == 1
    assert lines[0].status is DoctorStatus.OK


def test_multiple_behavioral_drifts_all_reported(tmp_path: Path) -> None:
    """A registry-plus-scaffold render with more than one independent behavioral
    drift reports every one of them, not just the first — each drift class is an
    independent, additive check."""
    public_dir = _build_clean_scratch(tmp_path)
    (public_dir / "agents" / "alpha.md").write_text(
        "placeholder, no frontmatter\n", encoding="utf-8"
    )
    (tmp_path / "hooks" / "pre_gate.py").unlink()

    lines = check_entities_derivation(public_dir)
    texts = _texts(lines)

    assert any("'alpha' has no parseable frontmatter identity" in text for text in texts)
    assert any("which no longer exists" in text for text in texts)
    assert all(line.status.blocking for line in lines)  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# The real packaged tree must still pass GREEN — behavioral fidelity is additive,
# never a false positive against the actual registry + scaffold.
# ---------------------------------------------------------------------------


def test_the_real_packaged_registry_has_no_behavioral_drift() -> None:
    real_public = Path(__file__).resolve().parents[3] / "dadaia_workspace" / "public"

    lines = check_entities_derivation(real_public)

    assert len(lines) == 1
    assert lines[0].status is DoctorStatus.OK
