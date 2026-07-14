"""Persona-resolution anti-regression doctor (v0.1.44 / AC-4 / T-44-9).

Every model-driven lifecycle step's ``role`` must resolve to a real Layer-2 persona atom
and must never be ``project-manager`` (the Layer-1 orchestrator is not a worker persona —
D-1). This rule enforces that invariant by enumerating the **actual resolved role of every
model-driven catalog/pipeline step** — the SAME catalog/pipeline construction the engine
runs, resolved the SAME way ``pipeline._scope()`` resolves a role (comma-split, trimmed,
through the persona loader) — NOT a static ``rglob`` over fragment files.

That distinction matters: a role can be set in the workflow **catalog/pipeline binding**
independently of any fragment file (the surface T-44-8 edits), so a fragment-file-only scan
would pass vacuously there. This rule covers that catalog-layer surface because it reads the
step ``role`` bindings, which is where a fragment's role ultimately lands as a runnable step.

The doctor never mutates — it reports. ``ok`` is ``True`` only when there are no violations.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from dadaia_workspace.core.models.lifecycle import AgentRuntimeKind
from dadaia_workspace.features.lifecycle import pipeline
from dadaia_workspace.features.lifecycle.personas.loader import PersonaLoader
from dadaia_workspace.features.lifecycle.workflows import (
    audit,
    backlog_definition,
    release_definition,
)

#: Step ``role`` values that are NOT Layer-2 worker personas and are excluded from the
#: resolution check: ``python`` (a pure-Python gate/step) and ``shared`` (a shared-fragment
#: role, never a runnable step role).
_NON_WORKER_ROLES = frozenset({"python", "shared"})


class PersonaResolutionFindingKind(StrEnum):
    """Why a step's resolved role failed the guardrail."""

    NO_PERSONA_ATOM = "no-persona-atom"
    PROJECT_MANAGER = "project-manager"


@dataclass(frozen=True)
class PersonaResolutionViolation:
    """One model-driven step whose resolved role has no valid persona."""

    step: str  # qualified ``<workflow>.<label>``
    role: str  # the offending role token (one of a comma-split set)
    kind: PersonaResolutionFindingKind


@dataclass(frozen=True)
class PersonaResolutionReport:
    """The guardrail outcome — ``ok`` iff there are no violations."""

    ok: bool
    violations: tuple[PersonaResolutionViolation, ...]


def model_driven_step_roles() -> dict[str, str]:
    """Map ``<workflow>.<label>`` → ``role`` for every model-driven catalog/pipeline step.

    Enumerates the SAME catalog/pipeline construction the engine runs (the five workflow
    ``_SEQUENCE`` modules + the implementation pipeline ladder), NOT a fragment ``rglob``.
    ``python`` / ``shared`` step roles are excluded — they are never worker personas.
    """
    sequences: dict[str, tuple[object, ...]] = {
        "release_definition": release_definition._SEQUENCE,
        "audit": audit._SEQUENCE,
        "backlog_definition": backlog_definition._SEQUENCE,
        "implementation_reviews": pipeline.implementation_ladder(AgentRuntimeKind.FAKE),
    }
    out: dict[str, str] = {}
    for name, seq in sequences.items():
        for step in seq:
            role = str(getattr(step, "role", ""))
            if role in _NON_WORKER_ROLES:
                continue
            out[f"{name}.{getattr(step, 'label', '?')}"] = role
    return out


def check_step_roles(
    step_roles: dict[str, str],
    *,
    persona_loader: PersonaLoader | None = None,
) -> PersonaResolutionReport:
    """Resolve each step ``role`` the SAME way ``pipeline._scope`` does and collect violations.

    For each model-driven step, the ``role`` is comma-split (multi-role) and trimmed; each
    named role must (1) NOT be ``project-manager`` and (2) resolve to an existing persona
    atom via the injected loader. Anything else is a violation.
    """
    loader = persona_loader or PersonaLoader()
    violations: list[PersonaResolutionViolation] = []
    for qualified, role in sorted(step_roles.items()):
        for name in (part.strip() for part in role.split(",")):
            if not name:
                continue
            if name == "project-manager":
                violations.append(
                    PersonaResolutionViolation(
                        qualified, name, PersonaResolutionFindingKind.PROJECT_MANAGER
                    )
                )
                continue
            if loader.load_optional(name) is None:
                violations.append(
                    PersonaResolutionViolation(
                        qualified, name, PersonaResolutionFindingKind.NO_PERSONA_ATOM
                    )
                )
    return PersonaResolutionReport(ok=not violations, violations=tuple(violations))


def check_persona_resolution(
    *, persona_loader: PersonaLoader | None = None
) -> PersonaResolutionReport:
    """The shipped-tree guardrail: every model-driven catalog/pipeline step resolves to a
    non-PM persona atom. ``ok`` is ``True`` on the current tree."""
    return check_step_roles(model_driven_step_roles(), persona_loader=persona_loader)
