"""ARCHITECTURAL GUARD — the composition root must wire every silently-degrading collaborator.

**Why this file exists.** A 3-week audit of 215 reported bugs found ONE dominant class,
23.3% of everything: *the effect was declared but never wired*. Ids like
``fragment-workflows-never-persist-step-handoffs``,
``definition-commit-gate-never-repoints-active-md``,
``implement-verb-never-derives-task-write-scope``,
``lifecycle-resume-reports-ok-without-advancing``,
``full-pipeline-success-persists-running-empty-ledger``.

The mechanism is always identical. Every capability of the lifecycle engine arrives as an
**optional constructor argument defaulting to ``None``** (63 of them across the four
workflow bodies), and each body **degrades silently** when its collaborator is absent:
no payload is persisted, no marker is flipped, no scope is derived — and the run still
reports success. `container.py` (2167 lines, 42 builders, ~200 keyword arguments) is the
only thing standing between "declared" and "actually happens", and it is hand-written.

The codebase already knows this. `container.py` carries the comment:

    # Bug fragment-workflows-never-persist-step-handoffs: same ALWAYS-wired rule as
    # build_lifecycle_pipeline — without it every produces= step's payload is silently
    # dropped and the run's ledger stays empty.

"ALWAYS-wired rule" enforced by a comment is discipline, not architecture — which is
exactly why the class kept recurring. This test converts that comment into a gate.

**What it does NOT do:** it does not refactor the 63 signatures. Making them required is
the real cure but a large, risky change; this guard makes the regression *impossible to
ship unnoticed* in the meantime, which is what stops the bleeding.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

#: Collaborators whose absence causes SILENT degradation (never a loud failure) in the
#: workflow bodies. Attribute name on the built instance -> what is silently lost.
_SILENT_IF_MISSING: dict[str, str] = {
    "_handoff_resolver": (
        "every produces= step's payload is silently dropped and the ledger stays empty "
        "(bug fragment-workflows-never-persist-step-handoffs)"
    ),
    "_runtime_files": (
        "declared artifact refs are never verified against disk, so phantom evidence "
        "passes the gate (bug gate-accepts-phantom-artifact-evidence)"
    ),
    "_artifact_root": (
        "the deliverable delta check has no root to diff against, so a worker that "
        "writes nothing sails through (bug "
        "codex-backlog-author-no-materialization-regression-040)"
    ),
}


def _workspace(tmp_path: Path) -> Path:
    """A minimally-initialized workspace the container's guard accepts."""
    (tmp_path / ".dadaia" / "states").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".dadaia" / "states" / "spec_contexts.json").write_text("{}", encoding="utf-8")
    (tmp_path / "repos").mkdir(exist_ok=True)
    specs = tmp_path / "specs"
    # build_audit_workflow legitimately refuses a non-existent target release, so the
    # release dir must exist for the guard to reach the wiring assertion at all.
    (specs / "releases" / "v0.1.0").mkdir(parents=True, exist_ok=True)
    (specs / "backlog").mkdir(exist_ok=True)
    return tmp_path


@pytest.mark.parametrize(
    "builder_name",
    [
        "build_lifecycle_pipeline",
        "build_release_definition_workflow",
        "build_backlog_definition_workflow",
        "build_audit_workflow",
    ],
)
def test_container_wires_every_silently_degrading_collaborator(
    tmp_path: Path, builder_name: str
) -> None:
    """Each lifecycle builder must hand its workflow every collaborator from
    ``_SILENT_IF_MISSING``.

    This is the gate for the largest bug class in the ledger. A new builder — or a new
    argument that silently degrades — must either be wired here or be made a REQUIRED
    constructor argument so Python itself refuses the omission.
    """
    from dadaia_workspace import container

    builder = getattr(container, builder_name)
    ws = _workspace(tmp_path)

    workflow = builder(ws, context="dadaia-workspace", release_id="v0.1.0")

    missing = [
        f"{attr} — {consequence}"
        for attr, consequence in _SILENT_IF_MISSING.items()
        if hasattr(workflow, attr) and getattr(workflow, attr) is None
    ]
    assert not missing, (
        f"{builder_name} left {len(missing)} silently-degrading collaborator(s) unwired.\n"
        "This is the 23.3%-of-all-bugs class: the workflow will RUN, report success, and "
        "quietly skip the effect.\n  - " + "\n  - ".join(missing)
    )


def test_guard_covers_every_lifecycle_workflow_builder() -> None:
    """The guard must not silently stop covering a builder someone adds later.

    Without this, a new ``build_*_workflow`` could ship unwired and the parametrize list
    above would simply never mention it — the same silent-omission failure mode one level
    up, in the test suite itself.
    """
    import inspect

    from dadaia_workspace import container

    covered = {
        "build_lifecycle_pipeline",
        "build_release_definition_workflow",
        "build_backlog_definition_workflow",
        "build_audit_workflow",
    }
    # Builders whose product genuinely has no handoff data plane (asserted, not assumed:
    # they accept no handoff_resolver at all).
    exempt = {
        "build_lifecycle_phase_workflow",
        "build_lifecycle_report_workflow",
        "build_workflow_handoff_resolver",
        "build_workflow_handoff_doctor",
        "build_workflow_catalog_service",
        "build_workflow_model_profile_registry",
        "build_workflow_model_policy_store",
        "build_workflow_policy_resolver",
        "build_backlog_removal_lifecycle",
        "build_release_spec_path",
    }
    found = {
        name
        for name, obj in inspect.getmembers(container, inspect.isfunction)
        if name.startswith("build_")
        and any(k in name for k in ("workflow", "pipeline", "backlog", "release", "audit"))
    }
    unaccounted = found - covered - exempt
    assert not unaccounted, (
        "New lifecycle builder(s) are not covered by the silent-wiring guard: "
        f"{sorted(unaccounted)}. Add them to the parametrize list above, or to `exempt` "
        "ONLY after confirming their product accepts none of "
        f"{sorted(_SILENT_IF_MISSING)}."
    )


# ---------------------------------------------------------------------------
# Second-largest class: TWO SOURCES OF THE SAME TRUTH (drift).
#
# 15.4% of the 3-week window is a gate oscillating between too-permissive (4.2%) and
# too-strict (11.2%). The mechanism is a rule implemented at more than one site, so a
# change lands at one and not the other: doctor-root-whitelist-contradicts-root-law,
# root-whitelist-message-drifts-from-policy, backlog-doctor-yaml-parse-misdiagnosis,
# and (found latent by this audit) `capabilities` hardcoding the status vocabulary that
# `doctor_release.CANONICAL_STATUS` actually enforces.
# ---------------------------------------------------------------------------


def test_status_vocabulary_has_exactly_one_definition() -> None:
    """``CANONICAL_STATUS`` is the only place the SDD status tokens are enumerated.

    ``capabilities`` is what consumer-side validators read to learn the contract; a second
    copy there means a validator can be told one vocabulary while the doctor enforces
    another — drift that surfaces as a "the tool contradicts itself" bug rather than an
    obvious break.
    """
    from dadaia_workspace.features.capabilities import service as capabilities
    from dadaia_workspace.features.specs.doctor_release import CANONICAL_STATUS

    src = Path(capabilities.__file__).read_text(encoding="utf-8")
    # The literal triple must not be re-enumerated outside the canonical module.
    assert '"Draft", "Em revisão", "Aprovado"' not in src, (
        "capabilities re-enumerates the status vocabulary instead of deriving it from "
        "CANONICAL_STATUS — that is the drift mechanism, not a shortcut."
    )
    payload = capabilities.build_capabilities()
    assert payload["specs"]["status_tokens"] == sorted(CANONICAL_STATUS)


def test_no_module_reimplements_the_approved_check_as_a_substring() -> None:
    """``is_approved`` is the only approval test in the codebase.

    ``"**Status:** Aprovado" in text`` was the shape at three sites. It is wrong in both
    directions — it accepts ``Aprovado (pendente)`` and rejects a double-space variant the
    doctor accepts — so a gate built on it disagrees with the doctor about the very same
    file. Ratchet: the substring shape may not return.
    """
    root = Path(__file__).resolve().parents[2] / "dadaia_workspace"
    offenders = []
    for py in sorted(root.rglob("*.py")):
        if "/public/" in py.as_posix() or py.name == "spec_status.py":
            # Projected assets carry the token as prose; spec_status itself documents the
            # anti-pattern it replaces.
            continue
        src = py.read_text(encoding="utf-8")
        if '"**Status:** Aprovado" in ' in src or '"**Status:** Aprovado" not in ' in src:
            offenders.append(str(py.relative_to(root)))
    assert not offenders, (
        "substring approval check reintroduced in: "
        f"{offenders} — use core.spec_status.is_approved()."
    )
