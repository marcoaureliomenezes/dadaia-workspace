"""Harness-independent public-asset coherence checks (F014, 20260830 audit).

These checks read only ``public/`` source assets (agents, skills, behavior map,
memory-phase law) — they are not Codex checks and never were; they lived in
``codex_doctor.py`` only because that file was split off ``public_assets.py`` by
line count, not by seam. One honestly named home:

- :func:`check_agent_skill_refs` — every skill an agent references exists.
- :func:`check_memory_phase_single_source` — the memory-write phase law has one home.
- :func:`check_entities_derivation` — behavior-map registry ↔ on-disk assets agree.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from dadaia_workspace.core.harness_registry import L1_ENTRY_HARNESSES
from dadaia_workspace.core.models.doctor_report import DoctorLine, DoctorStatus
from dadaia_workspace.infrastructure.runtime_transforms.codex_assets import (
    _parse_agent_frontmatter,
    _parse_skills_from_frontmatter,
)


def check_agent_skill_refs(public_dir: Path) -> list[DoctorLine]:
    """D-CX-SKILLS: every ``skills:`` name in agent frontmatter must exist in public/skills/."""
    agents_dir = public_dir / "agents"
    skills_dir = public_dir / "skills"
    out: list[DoctorLine] = []
    if not agents_dir.exists():
        return []

    for md_file in sorted(agents_dir.glob("*.md")):
        try:
            text = md_file.read_text(encoding="utf-8")
        except OSError:
            continue

        fm = _parse_agent_frontmatter(text)
        agent_name = str(fm.get("name", md_file.stem)) if fm else md_file.stem

        # Frontmatter skills — hard failure on missing skill directory
        skills_in_fm = _parse_skills_from_frontmatter(text)
        confirmed: set[str] = set()
        for skill in skills_in_fm:
            if (skills_dir / skill).is_dir():
                confirmed.add(skill)
            else:
                out.append(
                    DoctorLine(
                        DoctorStatus.DRIFT,
                        f"agent:{agent_name}: frontmatter references "
                        f"non-existent skill '{skill}' (D-CX-SKILLS)",
                    )
                )

        # Body scan — only inside "## Skills consumed" section (soft warning)
        body_start = text.find("\n---\n", 4)
        if body_start == -1:
            continue
        body = text[body_start + 5 :]
        sc_start = body.find("## Skills consumed")
        if sc_start == -1:
            continue
        sc_end = body.find("\n## ", sc_start + 1)
        section = body[sc_start:sc_end] if sc_end != -1 else body[sc_start:]
        already_flagged: set[str] = set(skills_in_fm)
        for m in re.finditer(r"`([a-z][a-z0-9\-]+)`", section):
            candidate = m.group(1)
            if candidate in already_flagged or candidate in confirmed:
                continue
            if not (skills_dir / candidate).is_dir():
                out.append(
                    DoctorLine(
                        DoctorStatus.WARN,
                        f"agent:{agent_name}: 'Skills consumed' body section "
                        f"mentions '{candidate}' absent from public/skills/ (D-CX-SKILLS)",
                    )
                )
                already_flagged.add(candidate)

    return out


_MEMORY_PHASE_CLAIM_MARKERS = (
    "write-locked",
    "only allows memory",
    "block writes to",
    "writes in this phase",
    "during the closure phase",
    "may edit memory",
    "may write memory",
)


def check_memory_phase_single_source(public_dir: Path) -> list[DoctorLine]:
    """SINGLE-SRC-1: the memory-write phase is DEFINITION+CLOSURE (constitution §13).

    Flags any public agent/skill line that asserts the memory-write *phase* permission but
    cites only CLOSURE (omitting DEFINITION) — the single-source drift behind
    `constitution-persona-single-source-drift`. Incidental "release closure"/"memory update"
    mentions are NOT flagged (they carry no phase-permission marker).
    """
    out: list[DoctorLine] = []
    for sub in ("agents", "skills"):
        base = public_dir / sub
        if not base.exists():
            continue
        for md_file in sorted(base.rglob("*.md")):
            try:
                text = md_file.read_text(encoding="utf-8")
            except OSError:
                continue
            for n, raw in enumerate(text.splitlines(), start=1):
                line = raw.lower()
                if "closure" not in line or "definition" in line:
                    continue
                if any(marker in line for marker in _MEMORY_PHASE_CLAIM_MARKERS):
                    rel = md_file.relative_to(public_dir)
                    out.append(
                        DoctorLine(
                            DoctorStatus.DRIFT,
                            f"{rel}:{n}: memory-write phase cites CLOSURE only — the "
                            f"canonical rule is DEFINITION+CLOSURE (constitution §13). (SINGLE-SRC-1)",
                        )
                    )
    return out


# By-name rule citation in a Codex-projected artifact, e.g. "`workspace-protocol` rule".
# The corpus is reachable iff each cited name resolves to .claude/rules/<name>.md on disk
# (the single source-of-truth law surface, identical across harnesses — WS-CDX-PROTOCOL).


# A `dadaia_workspace.<dotted.tail>` module reference embedded in a Deterministic
# Behavior's free-text implementation description (e.g. "PreToolUse hook via
# dadaia_workspace.hooks.pre_gate"). ENT-DERIVE-1 (A22.5) resolves every such
# reference against the real source tree, so a behavior whose enforcing module
# silently disappears — the concrete "a hook stops enforcing" drift — is DRIFT, not a
# quiet pass through harness-key-only coverage.
_ENT_DERIVE_MODULE_REF_RE: re.Pattern[str] = re.compile(
    r"\bdadaia_workspace\.([a-zA-Z_][a-zA-Z0-9_.]*)"
)


def _behavior_module_ref_missing(dotted_tail: str, package_root: Path) -> bool:
    """True when ``dadaia_workspace.<dotted_tail>`` resolves to no source file.

    *package_root* is ``public_dir.parent`` — the ``dadaia_workspace`` package
    directory itself in production, or an isolated scratch root in a mutation
    fixture. Neither a bare module file (``hooks/pre_gate.py``) nor a package
    (``hooks/pre_gate/__init__.py``) existing means the reference is broken.
    """
    rel = Path(*dotted_tail.split("."))
    module_file = package_root / rel.with_suffix(".py")
    package_init = package_root / rel / "__init__.py"
    return not module_file.is_file() and not package_init.is_file()


def _behavior_content_drift(behavior: dict[str, Any], package_root: Path) -> list[DoctorLine]:
    """Behavioral-fidelity DRIFT lines for one Deterministic Behavior (A22.5).

    Beyond harness-key coverage (checked by the caller), every
    ``dadaia_workspace.<module>`` reference embedded in any of this behavior's
    implementation descriptions must still resolve to a real source file.
    """
    out: list[DoctorLine] = []
    implementations = behavior.get("implementations", {})
    if not isinstance(implementations, Mapping):
        return out
    for harness_name, impl_text in implementations.items():
        if not isinstance(impl_text, str):
            continue
        for match in _ENT_DERIVE_MODULE_REF_RE.finditer(impl_text):
            dotted_tail = match.group(1)
            if _behavior_module_ref_missing(dotted_tail, package_root):
                out.append(
                    DoctorLine(
                        DoctorStatus.DRIFT,
                        f"entities-derivation: behavior '{behavior.get('id')}' "
                        f"implementation for '{harness_name}' references module "
                        f"'dadaia_workspace.{dotted_tail}' which no longer exists "
                        f"(ENT-DERIVE-1)",
                    )
                )
    return out


def _persona_content_drift(agent_id: str, agents_dir: Path) -> list[DoctorLine]:
    """Behavioral-fidelity DRIFT lines for one correctly-bijected sub-agent (A22.5).

    Filename-stem bijection alone cannot see a stub file at the right path, or an
    internal identity swap (frontmatter ``name:`` diverging from its own filename)
    — both are content-level drift a name-only check is blind to.
    """
    agent_file = agents_dir / f"{agent_id}.md"
    try:
        text = agent_file.read_text(encoding="utf-8")
    except OSError as exc:
        return [
            DoctorLine(
                DoctorStatus.ERROR,
                f"entities-derivation: core sub-agent '{agent_id}' unreadable "
                f"({exc.__class__.__name__}) (ENT-DERIVE-1)",
            )
        ]
    fm = _parse_agent_frontmatter(text)
    declared_name = fm.get("name") if fm else None
    if not declared_name:
        return [
            DoctorLine(
                DoctorStatus.DRIFT,
                f"entities-derivation: core sub-agent '{agent_id}' has no parseable "
                f"frontmatter identity — stub or malformed (ENT-DERIVE-1)",
            )
        ]
    if declared_name != agent_id:
        return [
            DoctorLine(
                DoctorStatus.DRIFT,
                f"entities-derivation: core sub-agent '{agent_id}' frontmatter name "
                f"'{declared_name}' does not match its filename — identity drift "
                f"(ENT-DERIVE-1)",
            )
        ]
    return []


def _entities_registry_shape_problem(raw: Any) -> str | None:
    """The single shape-tolerance seam for ``check_entities_derivation`` (ENT-DERIVE-1).

    Returns a human-readable description of the first shape violation found, or
    ``None`` when ``raw`` is safe for every ``.get``/iteration the caller performs
    downstream. Deliberately does not validate ``rules``/``universal`` — this check
    never reads those sections (only ``schema_version``, ``personas`` and
    ``behaviors[*].implementations``), so nothing beyond that is shape-checked here.
    """
    if not isinstance(raw, dict):
        return f"registry top level is a JSON {type(raw).__name__}, expected an object"

    personas = raw.get("personas", [])
    if not isinstance(personas, list) or not all(isinstance(p, dict) for p in personas):
        return "'personas' is not a list of JSON objects"

    behaviors = raw.get("behaviors", [])
    if not isinstance(behaviors, list) or not all(isinstance(b, dict) for b in behaviors):
        return "'behaviors' is not a list of JSON objects"

    for behavior in behaviors:
        implementations = behavior.get("implementations", {})
        if not isinstance(implementations, Mapping):
            return (
                f"behavior '{behavior.get('id')}' implementations is a "
                f"{type(implementations).__name__}, expected a JSON object"
            )

    return None


def check_entities_derivation(public_dir: Path) -> list[DoctorLine]:
    """ENT-DERIVE-1 (constitution §12.5): the abstract-entity registry grounds the scaffold.

    Independent verifier read — deliberately does NOT share the features-layer loader
    (``features.panel.entities``), so a loader bug cannot vouch for itself. Attests:

    1. ``public/entities/registry.json`` exists, parses, and carries the expected schema.
    2. Persona ↔ core sub-agent bijection: every ``public/agents/*.md`` derives from a
       Persona and every Persona has its derived sub-agent — BY NAME, plus, for every
       correctly-bijected pair, the sub-agent's own frontmatter is parseable and its
       ``name:`` matches its filename (:func:`_persona_content_drift`, A22.5). A stub
       file or a copy-paste identity swap at the right filename is DRIFT even though
       filename-only bijection would pass it.
    3. Every Deterministic Behavior is derived for exactly the entry harnesses, AND
       every ``dadaia_workspace.<module>`` reference embedded in an implementation's
       free-text description still resolves to a real source file
       (:func:`_behavior_content_drift`, A22.5) — a hook (or any other enforcing
       module) that silently disappears while its registry entry is left untouched is
       DRIFT, not a quiet pass through harness-key-only coverage.

    Any violation is DRIFT/ERROR (blocking): a scaffolded core implementation without
    its abstract entity is forbidden, not advisory.
    """
    registry_path = public_dir / "entities" / "registry.json"
    try:
        raw_registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [
            DoctorLine(
                DoctorStatus.ERROR,
                f"entities-derivation: registry unreadable at entities/registry.json "
                f"({exc.__class__.__name__}) (ENT-DERIVE-1)",
            )
        ]

    # Shape-validate the parsed JSON HERE, once, so every line below this seam may
    # assume the shape it needs — no isinstance scattered downstream. A malformed-but
    # -valid-JSON registry (wrong top-level type, non-dict entries, a string standing
    # in for a mapping) must never reach ``.get``/``set(...)`` and raise
    # AttributeError/TypeError, and must never be silently misread into a wrong DRIFT
    # line (e.g. ``set("codex")`` iterating characters as if they were harness ids).
    shape_problem = _entities_registry_shape_problem(raw_registry)
    if shape_problem is not None:
        return [
            DoctorLine(
                DoctorStatus.ERROR,
                f"entities-derivation: {shape_problem} (ENT-DERIVE-1)",
            )
        ]
    registry: dict[str, Any] = raw_registry

    if registry.get("schema_version") != "agentic-entities-v1":
        return [
            DoctorLine(
                DoctorStatus.ERROR,
                "entities-derivation: registry schema_version is not "
                "'agentic-entities-v1' (ENT-DERIVE-1)",
            )
        ]

    out: list[DoctorLine] = []
    personas = {str(p.get("id")) for p in registry.get("personas", [])}
    agents_dir = public_dir / "agents"
    scaffolded = {p.stem for p in agents_dir.glob("*.md")} if agents_dir.exists() else set()
    for orphan in sorted(scaffolded - personas):
        out.append(
            DoctorLine(
                DoctorStatus.DRIFT,
                f"entities-derivation: core sub-agent '{orphan}' has no abstract "
                f"Persona in the registry (ENT-DERIVE-1)",
            )
        )
    for dead in sorted(personas - scaffolded):
        out.append(
            DoctorLine(
                DoctorStatus.DRIFT,
                f"entities-derivation: Persona '{dead}' has no derived core "
                f"sub-agent under public/agents/ (ENT-DERIVE-1)",
            )
        )
    # Behavioral fidelity (A22.5): every correctly-bijected pair also gets its
    # content opened — a name-only pass cannot see a stub file or an identity swap.
    for matched_id in sorted(personas & scaffolded):
        out.extend(_persona_content_drift(matched_id, agents_dir))

    harnesses = set(L1_ENTRY_HARNESSES)
    package_root = public_dir.parent
    for behavior in registry.get("behaviors", []):
        implemented = set(behavior.get("implementations", {}))
        if implemented != harnesses:
            out.append(
                DoctorLine(
                    DoctorStatus.DRIFT,
                    f"entities-derivation: behavior '{behavior.get('id')}' is derived for "
                    f"{sorted(implemented)}, expected every entry harness "
                    f"{sorted(harnesses)} (ENT-DERIVE-1)",
                )
            )
        # Behavioral fidelity (A22.5): harness-key coverage is necessary, never
        # sufficient — also follow every module reference back to a real file.
        out.extend(_behavior_content_drift(behavior, package_root))

    if not out:
        out.append(
            DoctorLine(
                DoctorStatus.OK,
                f"entities-derivation: {len(personas)} Personas ↔ {len(scaffolded)} core "
                f"sub-agents; {len(registry.get('behaviors', []))} Deterministic Behaviors "
                f"derived for all entry harnesses (ENT-DERIVE-1)",
            )
        )
    return out
