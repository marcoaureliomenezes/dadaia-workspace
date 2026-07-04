"""Fragment / selector / role-map coherence doctor (v0.1.57 FR3 / T-57-30).

``persona_doctor`` already asserts every model-driven catalog/pipeline step's *role* resolves
to a non-PM persona atom. It does **not** cover the fragment-file surface: whether each
fragment's declared role is grounded, whether a fragment's ``dynamic_inputs`` name a real
selector, whether a fragment is bound to a workflow, and whether the declarative role→atom map
(FR2) actually reaches every model-driven step it is supposed to ground. This doctor adds those
NEW checks — it does **not** re-implement or modify ``persona_doctor``.

Each check carries a **stable ID + fixed severity** (Q6) so the output is mechanically
grep-assertable, and the label order is identical across SPEC FR3 / AC-5 / AC-10 / T-57-30 (A3):

* **FRAG-COH-1 (ERROR)** — every fragment file's ``role`` resolves to a persona atom OR is
  ``shared`` / ``python``.
* **FRAG-COH-2 (ERROR, SCOPED — A2)** — a ``dynamic_inputs`` entry resolves to a registered
  ``ContextSelector`` selector, checked as ERROR **only** for a dynamic_input that is actually
  resolved at runtime: the **MAIN fragment of a selector-wired workflow step**
  (release_definition / audit / research / bug_report / backlog_definition ``_SEQUENCE`` main
  fragments). It is **WARN** for (i) shared-fragment inputs (body-only, the workflow resolves
  only a step's main fragment inputs, never the cited shared fragments' inputs) and (ii)
  main-fragment inputs of a **selector-less path** (the ``implementation.*`` fragments the
  selector-less pipeline / phase_workflow consume). This scope is what makes the doctor green on
  the current tree while a sabotage of a selector-wired main fragment fires the ERROR.
* **FRAG-COH-3 (WARN)** — orphan check: every non-shared fragment is bound to some workflow
  step, and every cited shared fragment id exists.
* **FRAG-COH-4 (ERROR)** — role→atom-map coverage: each model-driven step's role-mapped atom
  appears in its resolved injected refs (the mechanical Layer-2 grounding proof, FR4). The
  covered scope is the **three FR2 delivery surfaces** — the ``FragmentGateWorkflow`` base
  (release_definition / audit / research / bug_report), the ``LifecyclePipeline`` ladder, and
  the ``LifecyclePhaseWorkflow`` path. ``backlog_definition`` is **excluded**: it shares only
  the pure ``_FragmentAssemblyMixin`` (no ``_run_model_step``), so its steps receive no
  role→atom injection — the coverage scope must match the FR2 delivery scope exactly, or the
  doctor would lie.

``ok`` is computed from the **ERROR checks only** (FRAG-COH-1/2/4); WARNs never fail the doctor.
The doctor never mutates — it reports.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from dadaia_workspace.core.models.lifecycle import (
    AgentRuntimeKind,
    LifecyclePhase,
    LifecycleRun,
    LifecycleRunStatus,
)
from dadaia_workspace.features.lifecycle import pipeline
from dadaia_workspace.features.lifecycle.context_selector import known_dynamic_inputs
from dadaia_workspace.features.lifecycle.fragments.loader import Fragment, FragmentLoader
from dadaia_workspace.features.lifecycle.personas.loader import PersonaLoader
from dadaia_workspace.features.lifecycle.role_atoms import (
    ROLE_ATOM_MAP,
    inject_role_atoms,
)
from dadaia_workspace.features.lifecycle.workflows import (
    audit,
    backlog_definition,
    bug_report,
    release_definition,
    research,
)

#: Fragment ``role`` values that are NOT Layer-2 worker personas and need no persona atom:
#: ``python`` (a pure-Python gate/step) and ``shared`` (a shared-fragment role). Mirrors
#: ``persona_doctor._NON_WORKER_ROLES`` — kept local so this doctor never imports or mutates
#: ``persona_doctor``.
_NON_WORKER_ROLES = frozenset({"python", "shared"})

#: The canonical on-disk memory-atom layout the FR2 role→atom map is expected to target
#: (``specs/memory/architecture.md``, ``specs/memory/quality-assurance.md``,
#: ``specs/memory/product/catalog.json``). FRAG-COH-4 seeds a self-contained fixture at these
#: paths — an INDEPENDENT oracle, deliberately not read from :data:`ROLE_ATOM_MAP` — and asserts
#: every covered mapped step's ``ROLE_ATOM_MAP`` atom resolves against it. Because the oracle is
#: independent, a map entry that drifts from the real memory layout (a typo'd path) is caught,
#: and the check is ambient-tree-independent (green on a bare workspace, no memory tree required).
_CANONICAL_ATOM_PATHS: tuple[str, ...] = (
    "memory/architecture.md",
    "memory/quality-assurance.md",
    "memory/product/catalog.json",
)


class FragCohCode(StrEnum):
    """The ``FRAG-COH-*`` stable-id namespace for the coherence doctor (Q6/A3)."""

    FRAG_COH_1 = "FRAG-COH-1"
    FRAG_COH_2 = "FRAG-COH-2"
    FRAG_COH_3 = "FRAG-COH-3"
    FRAG_COH_4 = "FRAG-COH-4"


class Severity(StrEnum):
    """The two fixed severities. ``ok`` counts ERROR findings only; WARN never fails."""

    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class FragCohFinding:
    """One coherence-doctor finding — a stable check id + fixed severity + message."""

    code: FragCohCode
    severity: Severity
    message: str

    def to_dict(self) -> dict[str, str]:
        return {
            "code": self.code.value,
            "severity": self.severity.value,
            "message": self.message,
        }


@dataclass(frozen=True)
class FragmentCoherenceReport:
    """The doctor outcome — ``ok`` iff there are no ERROR findings (WARNs are advisory)."""

    ok: bool
    findings: tuple[FragCohFinding, ...]


# ---------------------------------------------------------------------------
# sequence enumeration
# ---------------------------------------------------------------------------


def _split_roles(role: str) -> tuple[str, ...]:
    """Comma-split a (possibly multi-)role label (mirrors ``role_atoms._split_roles``)."""
    return tuple(part.strip() for part in role.split(",") if part.strip())


def _selector_wired_sequences() -> dict[str, tuple[object, ...]]:
    """The five workflows whose main-fragment ``dynamic_inputs`` are resolved by a selector.

    ``release_definition`` / ``audit`` / ``research`` / ``bug_report`` run on a wired
    ``ContextSelector`` via the ``FragmentGateWorkflow`` base; ``backlog_definition`` resolves
    its main-fragment inputs through the shared ``_FragmentAssemblyMixin``. FRAG-COH-2 ERRORs
    are scoped to these bodies' MAIN fragments (A2).
    """
    return {
        "release_definition": release_definition._SEQUENCE,
        "audit": audit._SEQUENCE,
        "research": research._SEQUENCE,
        "bug_report": bug_report._SEQUENCE,
        "backlog_definition": backlog_definition._SEQUENCE,
    }


def _fr2_covered_sequences() -> dict[str, tuple[object, ...]]:
    """The workflows whose model-driven steps receive the FR2 role→atom injection.

    The three FR2 delivery surfaces are the ``FragmentGateWorkflow`` base
    (release_definition / audit / research / bug_report), the ``LifecyclePipeline`` ladder, and
    the ``LifecyclePhaseWorkflow`` single-step path (structurally identical to a ladder step —
    represented here by the ladder). ``backlog_definition`` is **excluded**: it shares only the
    pure assembly mixin (no ``_run_model_step``), so its steps are NOT grounded by the map —
    FRAG-COH-4's coverage scope must match the FR2 delivery scope exactly (W2 boundary note).
    """
    return {
        "release_definition": release_definition._SEQUENCE,
        "audit": audit._SEQUENCE,
        "research": research._SEQUENCE,
        "bug_report": bug_report._SEQUENCE,
        "pipeline": pipeline.implementation_ladder(AgentRuntimeKind.FAKE),
    }


def _selector_wired_main_fragment_ids() -> frozenset[str]:
    """The MAIN fragment ids of every selector-wired workflow step (FRAG-COH-2 ERROR scope).

    Deliberately EXCLUDES the ``implementation.*`` pipeline fragments: the pipeline /
    phase_workflow are the selector-less path, so their main-fragment inputs are WARN, not ERROR
    (A2 clause (ii)).
    """
    ids: set[str] = set()
    for seq in _selector_wired_sequences().values():
        for step in seq:
            fid = getattr(step, "fragment_id", None)
            if isinstance(fid, str):
                ids.add(fid)
    return frozenset(ids)


# ---------------------------------------------------------------------------
# checks
# ---------------------------------------------------------------------------


def _check_frag_coh_1(
    fragments: tuple[Fragment, ...], persona_loader: PersonaLoader
) -> list[FragCohFinding]:
    """FRAG-COH-1 (ERROR): every fragment role resolves to a persona atom or is shared/python."""
    out: list[FragCohFinding] = []
    for fragment in fragments:
        for name in _split_roles(fragment.role):
            if name in _NON_WORKER_ROLES:
                continue
            if persona_loader.load_optional(name) is None:
                out.append(
                    FragCohFinding(
                        FragCohCode.FRAG_COH_1,
                        Severity.ERROR,
                        f"fragment {fragment.id!r} role {name!r} resolves to no persona atom "
                        "(a fragment role must resolve to a persona atom or be shared/python).",
                    )
                )
    return out


def _check_frag_coh_2(
    fragments: tuple[Fragment, ...],
    main_fragment_ids: frozenset[str],
    registered: frozenset[str],
) -> list[FragCohFinding]:
    """FRAG-COH-2 (ERROR, SCOPED — A2): a selector-wired main fragment's dynamic_input is
    registered; shared / selector-less inputs are WARN (body-only, never runtime-resolved)."""
    out: list[FragCohFinding] = []
    for fragment in fragments:
        unregistered = [name for name in fragment.dynamic_inputs if name not in registered]
        if not unregistered:
            continue
        is_selector_wired_main = fragment.id in main_fragment_ids
        for name in unregistered:
            if is_selector_wired_main:
                out.append(
                    FragCohFinding(
                        FragCohCode.FRAG_COH_2,
                        Severity.ERROR,
                        f"selector-wired main fragment {fragment.id!r} dynamic_input {name!r} "
                        "resolves to no registered ContextSelector selector.",
                    )
                )
            else:
                out.append(
                    FragCohFinding(
                        FragCohCode.FRAG_COH_2,
                        Severity.WARNING,
                        f"fragment {fragment.id!r} dynamic_input {name!r} has no registered "
                        "selector but is body-only (shared fragment / selector-less path) — "
                        "never runtime-resolved.",
                    )
                )
    return out


def _check_frag_coh_3(fragments: tuple[Fragment, ...]) -> list[FragCohFinding]:
    """FRAG-COH-3 (WARN): orphan fragment / dangling shared id.

    Every non-shared fragment must be bound as a main fragment or cited as a shared fragment by
    some workflow step (the pipeline ladder included); every cited shared fragment id must have
    a fragment file.
    """
    out: list[FragCohFinding] = []
    bound_main: set[str] = set()
    cited_shared: set[str] = set()
    sequences = {**_selector_wired_sequences(), "pipeline": _fr2_covered_sequences()["pipeline"]}
    for seq in sequences.values():
        for step in seq:
            fid = getattr(step, "fragment_id", None)
            if isinstance(fid, str):
                bound_main.add(fid)
            for sid in getattr(step, "shared_fragment_ids", ()):
                cited_shared.add(sid)
    existing_ids = {fragment.id for fragment in fragments}
    for fragment in fragments:
        if fragment.role == "shared":
            continue  # shared fragments are validated by the citation check below
        if fragment.id not in bound_main and fragment.id not in cited_shared:
            out.append(
                FragCohFinding(
                    FragCohCode.FRAG_COH_3,
                    Severity.WARNING,
                    f"fragment {fragment.id!r} is bound to no workflow step (orphan).",
                )
            )
    for sid in sorted(cited_shared):
        if sid not in existing_ids:
            out.append(
                FragCohFinding(
                    FragCohCode.FRAG_COH_3,
                    Severity.WARNING,
                    f"cited shared fragment id {sid!r} has no fragment file (dangling).",
                )
            )
    return out


def _bare_run() -> LifecycleRun:
    """A minimal run used to exercise the ``inject_role_atoms`` helper for FRAG-COH-4."""
    return LifecycleRun(
        run_id="frag-coh-4",
        context="dadaia-workspace",
        release_id="_",
        command="fragment-coherence-doctor",
        phase=LifecyclePhase.IMPLEMENTATION,
        status=LifecycleRunStatus.RUNNING,
        current_step="_",
    )


def _injected_refs(run: LifecycleRun, step_label: str) -> tuple[str, ...]:
    for entry in run.injected_context:
        if entry.step == step_label:
            return entry.refs
    return ()


def _seed_oracle_specs(root: Path) -> Path:
    """Seed the self-contained independent-oracle specs tree at the canonical atom layout."""
    specs = root / "specs"
    for relpath in _CANONICAL_ATOM_PATHS:
        target = specs / relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"# FRAG-COH-4 oracle atom: {relpath}\n", encoding="utf-8")
    return specs


def _check_frag_coh_4() -> list[FragCohFinding]:
    """FRAG-COH-4 (ERROR): role→atom-map coverage across the three FR2 delivery surfaces.

    A CODE-coherence check (not a data-completeness check): for each FR2-covered model-driven
    step whose role is in :data:`ROLE_ATOM_MAP`, exercise the SAME single ``inject_role_atoms``
    helper every assembly surface calls, against a self-contained fixture seeded at the
    :data:`_CANONICAL_ATOM_PATHS` independent oracle, and assert the mapped atom ref lands in the
    resulting run's ``InjectedContext.refs`` — the mechanical Layer-2 grounding proof. A covered
    step whose mapped atom is absent from its refs (an enumeration gap, or a ``ROLE_ATOM_MAP``
    entry that drifts from the canonical layout) fires an ERROR. The covered scope EXCLUDES
    ``backlog_definition`` (W2 boundary: mixin-only, no ``_run_model_step``), so the doctor never
    lies about which surfaces the FR2 map actually grounds.
    """
    out: list[FragCohFinding] = []
    with tempfile.TemporaryDirectory() as tmp:
        specs = _seed_oracle_specs(Path(tmp))
        for workflow_name, seq in _fr2_covered_sequences().items():
            for step in seq:
                fragment_id = getattr(step, "fragment_id", None)
                role = str(getattr(step, "role", ""))
                if fragment_id is None or role in _NON_WORKER_ROLES:
                    continue
                mapped_roles = [name for name in _split_roles(role) if name in ROLE_ATOM_MAP]
                if not mapped_roles:
                    continue
                label = str(getattr(step, "label", "?"))
                run, _ = inject_role_atoms(
                    run=_bare_run(),
                    step_label=label,
                    role=role,
                    specs_dir=specs,
                    prompt="",
                )
                refs = _injected_refs(run, label)
                for name in mapped_roles:
                    expected = f"specs/{ROLE_ATOM_MAP[name]}"
                    if expected not in refs:
                        out.append(
                            FragCohFinding(
                                FragCohCode.FRAG_COH_4,
                                Severity.ERROR,
                                f"model-driven step {workflow_name}.{label} role {name!r}: "
                                f"mapped atom {expected} is absent from its injected refs "
                                "(role→atom grounding not recorded).",
                            )
                        )
    return out


def run_fragment_coherence_doctor(
    *,
    loader: FragmentLoader | None = None,
    persona_loader: PersonaLoader | None = None,
) -> FragmentCoherenceReport:
    """Run every ``FRAG-COH-*`` coherence check and return the report.

    A pure CODE-coherence doctor: it validates the fragment-file surface + the FR2 role→atom
    wiring, ambient-tree-independent (FRAG-COH-4 grounds against a self-contained oracle, so the
    doctor is green even on a bare workspace with no memory tree). ``loader`` / ``persona_loader``
    are injectable for deterministic fixture testing (defaulting to the packaged fragment /
    persona roots). ``ok`` is computed from the ERROR findings only; WARN findings are advisory
    and never fail the doctor.
    """
    fragment_loader = loader or FragmentLoader()
    resolved_persona_loader = persona_loader or PersonaLoader()
    fragments = tuple(fragment_loader.list_fragments())
    registered = frozenset(known_dynamic_inputs())
    main_fragment_ids = _selector_wired_main_fragment_ids()

    findings: list[FragCohFinding] = []
    findings.extend(_check_frag_coh_1(fragments, resolved_persona_loader))
    findings.extend(_check_frag_coh_2(fragments, main_fragment_ids, registered))
    findings.extend(_check_frag_coh_3(fragments))
    findings.extend(_check_frag_coh_4())
    ok = not any(finding.severity is Severity.ERROR for finding in findings)
    return FragmentCoherenceReport(ok=ok, findings=tuple(findings))


__all__ = [
    "FragCohCode",
    "FragCohFinding",
    "FragmentCoherenceReport",
    "Severity",
    "run_fragment_coherence_doctor",
]
