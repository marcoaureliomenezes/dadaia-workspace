"""Fragment / selector / role-map coherence doctor + sel_constitution decision (v0.1.57 FR3 / W3).

Covers:

* **AC-5 (doctor green on the current tree)** — with the shipped fragments,
  ``run_fragment_coherence_doctor`` reports ``ok=True`` and zero ERROR findings (the ~25
  shared/implementation unregistered inputs are FRAG-COH-2 WARN, not ERROR); ``persona_doctor``
  stays green and is never re-implemented. The doctor is a pure CODE-coherence check —
  FRAG-COH-4 grounds against a self-contained oracle, so it is ambient-tree-independent.
* **AC-5 (RED-first)** — an unregistered ``dynamic_inputs`` entry on the selector-wired
  ``release_definition.definition_draft`` MAIN fragment (a sabotaged loader copy, NOT the shipped
  file) fires **FRAG-COH-2** (ERROR), flips ``ok`` to False, and the rendered output contains
  the literal ``FRAG-COH-2``.
* **FRAG-COH-1 / FRAG-COH-3 / FRAG-COH-4** unit bites — an unmapped fragment role fires
  FRAG-COH-1; an unbound fragment fires FRAG-COH-3 (WARN); a ``ROLE_ATOM_MAP`` entry drifting
  from the canonical layout fires FRAG-COH-4.
* **W2 boundary** — FRAG-COH-4's covered scope is exactly the three FR2 delivery surfaces and
  EXCLUDES ``backlog_definition`` (mixin-only, no ``_run_model_step``), while FRAG-COH-2's
  selector-wired scope INCLUDES it.
* **sel_constitution (A4)** — the ``spec_create`` static constitution injection is intact
  (``specs/constitution.md`` is a declared static input and resolves to the file content), the
  selector is registered, and the ``write_set_guidance`` → ``sel_write_set_guidance`` →
  ``sel_constitution`` indirection resolves.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from dadaia_workspace.features.lifecycle import fragment_coherence_doctor as fcd
from dadaia_workspace.features.lifecycle import persona_doctor, role_atoms
from dadaia_workspace.features.lifecycle.context_selector import (
    ContextSelector,
    MaxContextPolicy,
    SpecContext,
    known_dynamic_inputs,
)
from dadaia_workspace.features.lifecycle.fragment_coherence_doctor import (
    FragCohCode,
    Severity,
    run_fragment_coherence_doctor,
)
from dadaia_workspace.features.lifecycle.fragments.loader import Fragment, FragmentLoader

pytestmark = pytest.mark.unit

_SPEC_CREATE = "release_definition.definition_draft"


def _seed_specs(tmp_path: Path) -> Path:
    """Author a minimal specs tree carrying constitution.md (for the sel_constitution tests)."""
    specs = tmp_path / "specs"
    specs.mkdir(parents=True)
    (specs / "constitution.md").write_text("# Constitution\n\nBody.\n", encoding="utf-8")
    return specs


class _SabotagedLoader(FragmentLoader):
    """Shipped fragments, but the ``spec_create`` main fragment gains an unregistered input.

    Subclasses the real loader (so it IS a ``FragmentLoader``) and rewrites ONLY the
    ``release_definition.definition_draft`` copy in-memory — the shipped file on disk is untouched.
    """

    def list_fragments(self, workflow: str | None = None) -> list[Fragment]:
        out: list[Fragment] = []
        for fragment in super().list_fragments(workflow):
            if fragment.id == _SPEC_CREATE:
                fragment = replace(
                    fragment,
                    dynamic_inputs=(*fragment.dynamic_inputs, "bogus_unregistered_selector"),
                )
            out.append(fragment)
        return out


# ---------------------------------------------------------------------------
# AC-5 — green on the current tree (persona_doctor stays green, never re-implemented)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# ① AC-5 RED-first — unregistered input on selector-wired main fires FRAG-COH-2
# ---------------------------------------------------------------------------


def test_ac5_doctor_green_on_current_tree_and_red_first_sabotaged_loader() -> None:
    clean_report = run_fragment_coherence_doctor()
    assert clean_report.ok is True
    assert [f for f in clean_report.findings if f.severity is Severity.ERROR] == []
    # Every canonical fragment input resolves through a registered selector.
    warns = [f for f in clean_report.findings if f.code is FragCohCode.FRAG_COH_2]
    assert warns == []
    # The coherence doctor does NOT re-implement or modify persona_doctor.
    assert persona_doctor.check_persona_resolution().ok is True

    report = run_fragment_coherence_doctor(loader=_SabotagedLoader())
    assert report.ok is False
    coh2_errors = [
        f
        for f in report.findings
        if f.code is FragCohCode.FRAG_COH_2 and f.severity is Severity.ERROR
    ]
    assert coh2_errors, "sabotaged selector-wired main fragment must fire a FRAG-COH-2 ERROR"
    assert any(_SPEC_CREATE in f.message for f in coh2_errors)
    # the doctor output STRING carries the literal stable id (grep-assertable, AC-5).
    rendered = "\n".join(
        f"[{f.severity.value}] {f.code.value}: {f.message}" for f in report.findings
    )
    assert "FRAG-COH-2" in rendered
    # persona_doctor is unaffected by the fragment sabotage.
    assert persona_doctor.check_persona_resolution().ok is True


# ---------------------------------------------------------------------------
# ② FRAG-COH-1 / FRAG-COH-3 / FRAG-COH-4 bite param
# ---------------------------------------------------------------------------


def _fragment(**overrides: object) -> Fragment:
    base = dict(
        id="fixture.step",
        role="product-engineer",
        workflow="fixture",
        step="step",
        static_inputs=(),
        dynamic_inputs=(),
        output_schema="fixture-out-v1",
        max_context_policy="catalog-only",
        body="Body.",
        path=Path("fixture/step.md"),
    )
    base.update(overrides)
    return Fragment(**base)  # type: ignore[arg-type]


class _StaticLoader(FragmentLoader):
    def __init__(self, fragments: list[Fragment]) -> None:
        super().__init__()
        self._fragments = fragments

    def list_fragments(self, workflow: str | None = None) -> list[Fragment]:
        return list(self._fragments)


def test_frag_coh_1_3_4_bites(monkeypatch: pytest.MonkeyPatch) -> None:
    """FRAG-COH-1 (unmapped role -> ERROR; shared/python roles pass), FRAG-COH-3 (orphan
    fragment -> WARN, never ERROR), and FRAG-COH-4 (ROLE_ATOM_MAP drift -> ERROR) share the
    ``_StaticLoader``/monkeypatch fixture shape — one bite table."""
    bad = run_fragment_coherence_doctor(
        loader=_StaticLoader([_fragment(id="fixture.bad", role="no-such-role")])
    )
    coh1 = [f for f in bad.findings if f.code is FragCohCode.FRAG_COH_1]
    assert coh1 and coh1[0].severity is Severity.ERROR
    assert "no-such-role" in coh1[0].message
    assert bad.ok is False

    ok = run_fragment_coherence_doctor(
        loader=_StaticLoader(
            [_fragment(id="fixture.s", role="shared"), _fragment(id="fixture.p", role="python")]
        )
    )
    assert [f for f in ok.findings if f.code is FragCohCode.FRAG_COH_1] == []

    # a non-shared fragment bound to no workflow step → orphan WARN (never an ERROR).
    orphan_report = run_fragment_coherence_doctor(
        loader=_StaticLoader([_fragment(id="fixture.orphan", role="product-engineer")])
    )
    coh3 = [f for f in orphan_report.findings if f.code is FragCohCode.FRAG_COH_3]
    assert coh3 and all(f.severity is Severity.WARNING for f in coh3)
    assert any("orphan" in f.message for f in coh3)

    # Point qa-engineer's mapped atom at a path the canonical oracle does NOT seed → every
    # covered qa-engineer step's atom is absent from its injected refs → FRAG-COH-4 ERROR
    # (the mechanical grounding proof bites; ambient-tree-independent).
    monkeypatch.setitem(role_atoms.ROLE_ATOM_MAP, "qa-engineer", "memory/does-not-exist.md")
    drift_report = run_fragment_coherence_doctor()
    coh4 = [f for f in drift_report.findings if f.code is FragCohCode.FRAG_COH_4]
    assert coh4 and all(f.severity is Severity.ERROR for f in coh4)
    assert any("does-not-exist.md" in f.message for f in coh4)
    assert drift_report.ok is False


# ---------------------------------------------------------------------------
# ③ W2 boundary scopes + sel_constitution static-input + write_set_guidance indirection
# ---------------------------------------------------------------------------


def test_w2_boundary_and_sel_constitution_indirection(tmp_path: Path) -> None:
    # W2 boundary: FRAG-COH-4's covered scope EXCLUDES backlog_definition (mixin-only, no
    # _run_model_step); FRAG-COH-2's selector-wired scope INCLUDES it.
    covered = fcd._fr2_covered_sequences()
    assert "backlog_definition" not in covered
    assert set(covered) == {
        "release_definition",
        "audit",
        "implementation_reviews",
    }

    wired = fcd._selector_wired_sequences()
    assert "backlog_definition" in wired  # its main-fragment inputs ARE resolved (assembly mixin)
    main_ids = fcd._selector_wired_main_fragment_ids()
    assert "backlog_definition.backlog_authoring" in main_ids
    assert "implementation.combined_review" in main_ids

    # sel_constitution (A4) — NOT dead: the selector stays registered under its named-atom key.
    assert "constitution.md" in known_dynamic_inputs()

    specs = _seed_specs(tmp_path)
    # spec_create declares specs/constitution.md as a static input (the DIRECT path).
    fragment = FragmentLoader().load_fragment(_SPEC_CREATE)
    assert "specs/constitution.md" in fragment.static_inputs
    # and it resolves to the on-disk constitution content (present=True).
    selector = ContextSelector(SpecContext(specs_dir=specs, release_id="v0.1.57"))
    resolved = selector.resolve_static_input("specs/constitution.md")
    assert resolved.present is True
    assert "# Constitution" in resolved.content

    # The INDIRECT chain (A4): write_set_guidance → sel_write_set_guidance → sel_constitution.
    result = selector.select("write_set_guidance", MaxContextPolicy.SUMMARY)
    # resolves through sel_constitution to the constitution.md ref (never mistaken for dead).
    assert result.refs == ("specs/constitution.md",)
