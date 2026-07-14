"""Unit tests for the lifecycle fragment loader (WS-3 / T-24-07).

Token lint (harness-universality) must survive — it is the cross-harness portability gate.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.core.models.lifecycle import AgentRuntimeKind
from dadaia_workspace.features.lifecycle.fragments.loader import (
    Fragment,
    FragmentLoader,
    FragmentNotFoundError,
    FragmentValidationError,
    forbidden_token_in,
    list_fragments,
    load_fragment,
    validate_all,
)
from dadaia_workspace.features.lifecycle.pipeline import implementation_ladder
from dadaia_workspace.features.lifecycle.workflows.release_definition import _SEQUENCE


def _release_definition_step_ids() -> set[str]:
    """Fragment ids the release_definition workflow actually drives — derived from the
    real ``_SEQUENCE`` so this check can never drift from the workflow it asserts."""
    return {step.fragment_id for step in _SEQUENCE if step.fragment_id is not None}


def _shared_ids_cited_by_release_definition() -> set[str]:
    """Shared fragment ids cited by the release_definition steps, derived from
    ``_SEQUENCE`` rather than hand-copied."""
    shared: set[str] = set()
    for step in _SEQUENCE:
        shared.update(step.shared_fragment_ids)
    return shared


def _implementation_ladder_fragment_ids() -> set[str]:
    """Fragment ids (own + shared) the implementation pipeline ladder drives — derived
    from the real ladder so the check tracks the actual pipeline."""
    ids: set[str] = set()
    for step in implementation_ladder(AgentRuntimeKind.FAKE):
        if step.fragment_id is not None:
            ids.add(step.fragment_id)
        ids.update(step.shared_fragment_ids)
    return ids


# Derived from the real workflow + ladder (fix #2: no hand-copied id set can drift).
_RELEASE_DEFINITION_STEP_IDS = _release_definition_step_ids()
_SHARED_IDS = {
    "shared.anti_slop",
    "shared.grill_questionnaire",
    "shared.memory_selection",
    "shared.write_scope",
}
# No canonical workflow ships a deferred README-only directory.
_DEFERRED_WORKFLOW_DIRS: set[str] = set()

# Workflow dirs that ship authored step fragments backing a real fragment+gate body.
_AUTHORED_WORKFLOW_DIRS = {
    "audit",
}

_VALID_FRONTMATTER = """\
---
id: shared.fixture
role: shared
workflow: shared
step: fixture
static_inputs: []
dynamic_inputs: [available_evidence]
output_schema: handoff-v1.1
max_context_policy: summary
---

# A harness-universal fixture body.
"""


def _write_fragment(tmp_path: Path, name: str, text: str) -> FragmentLoader:
    root = tmp_path / "lifecycle_fragments"
    (root / "shared").mkdir(parents=True, exist_ok=True)
    (root / "shared" / name).write_text(text, encoding="utf-8")
    return FragmentLoader(root=root)


# ---------------------------------------------------------------------------
# ① shipped-library existence derived from _SEQUENCE / ladder
# ---------------------------------------------------------------------------


def test_shipped_library_existence_derived_from_sequence_and_ladder() -> None:
    fragments = validate_all()
    assert fragments, "expected the packaged fragment library to be non-empty"
    assert all(isinstance(f, Fragment) for f in fragments)
    loadable = {f.id for f in fragments}

    rd = {f.id for f in list_fragments(workflow="release_definition")}
    missing = _RELEASE_DEFINITION_STEP_IDS - rd
    assert not missing, f"release_definition workflow references missing fragments: {missing}"
    assert _RELEASE_DEFINITION_STEP_IDS  # guards against a refactor silently emptying _SEQUENCE

    shared = {f.id for f in list_fragments(workflow="shared")}
    assert shared >= _SHARED_IDS
    assert _shared_ids_cited_by_release_definition() <= shared

    ladder_ids = _implementation_ladder_fragment_ids()
    assert ladder_ids, "implementation ladder declared no fragment ids"
    ladder_missing = ladder_ids - loadable
    assert not ladder_missing, (
        f"implementation ladder references missing fragments: {ladder_missing}"
    )

    # No fragment id should ever resolve to a _README stub.
    assert all(not fid.endswith("_README") for fid in loadable)


# ---------------------------------------------------------------------------
# ② load-by-id/path round trip + unknown-id raises
# ---------------------------------------------------------------------------


def test_load_by_id_and_path_round_trip_unknown_id_raises() -> None:
    fragment = load_fragment("release_definition.spec_review")
    assert fragment.id == "release_definition.spec_review"
    assert fragment.workflow == "release_definition"
    assert fragment.step == "spec_review"
    assert fragment.output_schema == "spec-review-verdict-v1"
    assert "specs/memory/architecture.md" in fragment.static_inputs
    assert fragment.body.startswith("# SPEC review")

    loader = FragmentLoader()
    by_path = loader.load_fragment(Path("shared") / "anti-slop.md")
    assert by_path.id == "shared.anti_slop"

    with pytest.raises(FragmentNotFoundError):
        load_fragment("release_definition.does_not_exist")


def test_release_definition_prompts_treat_validation_as_dependency() -> None:
    """Regression: an early task must not require a later integration surface to pass."""
    plan_create = load_fragment("release_definition.plan_create").body
    plan_review = load_fragment("release_definition.plan_review").body
    tasks_create = load_fragment("release_definition.tasks_create").body
    tasks_review = load_fragment("release_definition.tasks_review_implementability").body

    assert "validation dependency-safe" in plan_create
    assert "validation depends on work scheduled later" in plan_review
    assert "validation is part of its dependency graph" in tasks_create
    assert "Validation is a dependency" in tasks_review


def test_spec_create_requires_proof_for_internal_negative_constraints() -> None:
    """Regression: internal "must not" claims need evidence beyond equal outputs."""
    spec_create = load_fragment("release_definition.spec_create").body

    assert "concrete verification path for every acceptance criterion" in spec_create
    assert "controlled probe/fake" in spec_create
    assert "structural/static inspection" in spec_create
    assert "equal end results to prove which internal path" in spec_create


def test_release_definition_binds_public_contract_before_implementation() -> None:
    plan_create = load_fragment("release_definition.plan_create").body
    plan_review = load_fragment("release_definition.plan_review").body
    tasks_create = load_fragment("release_definition.tasks_create").body
    tasks_review = load_fragment("release_definition.tasks_review_implementability").body

    for body in (plan_create, plan_review, tasks_create, tasks_review):
        assert "module/export path" in body
    assert "do not leave them for TASKS or implementation to invent" in plan_create
    assert "no public design decision is deferred" in plan_review
    assert "Copy those bindings faithfully" in tasks_create
    assert "not defer it to the implementer" in tasks_review


# ---------------------------------------------------------------------------
# ③ workflow-dir shape param: authored / deferred README-only / README-never-a-fragment /
#    implementation ships its 6
# ---------------------------------------------------------------------------


def test_workflow_dir_shape_matrix() -> None:
    """authored dirs ship fragments / deferred README-only / README-never-a-fragment /
    implementation ships its 6 — one loader, one param-shaped assertion table."""
    loader = FragmentLoader()

    # v0.1.43 added the security-review and code-review gate fragments. No README-only
    # deferred stub.
    ids = {f.id for f in loader.list_fragments(workflow="implementation")}
    assert ids == {
        "implementation.implement_tdd",
        "implementation.self_verify",
        "implementation.combined_review",
        "implementation.close_release",
    }
    assert len(loader.list_fragments(workflow="shared")) == 4
    assert len(loader.list_fragments(workflow="release_definition")) == 7

    dirs = set(loader.list_workflow_dirs())
    assert dirs >= _DEFERRED_WORKFLOW_DIRS
    for workflow in _DEFERRED_WORKFLOW_DIRS:
        assert loader.list_fragments(workflow=workflow) == [], (
            f"deferred workflow '{workflow}' must carry no step fragments yet"
        )
        readme = loader.root / workflow / "_README.md"
        assert readme.exists(), f"deferred workflow '{workflow}' must ship a _README.md stub"

    # Audit ships real fragment+gate step fragments backing its workflow body.
    for workflow in _AUTHORED_WORKFLOW_DIRS:
        fragments = loader.list_fragments(workflow=workflow)
        assert fragments, f"authored workflow '{workflow}' must ship step fragments"
        for fragment in fragments:
            assert fragment.workflow == workflow


# ---------------------------------------------------------------------------
# ④ malformed-frontmatter rejection param
# ---------------------------------------------------------------------------

_MALFORMED_CASES = (
    (
        "missing-required-key",
        lambda t: t.replace("output_schema: handoff-v1.1\n", ""),
        "output_schema",
    ),
    (
        "wrong-type-for-list-key",
        lambda t: t.replace("dynamic_inputs: [available_evidence]", "dynamic_inputs: not-a-list"),
        "dynamic_inputs",
    ),
    (
        "empty-string-key",
        lambda t: t.replace("output_schema: handoff-v1.1", 'output_schema: ""'),
        "output_schema",
    ),
    (
        "non-string-list-item",
        lambda t: t.replace("dynamic_inputs: [available_evidence]", "dynamic_inputs: [3]"),
        "dynamic_inputs",
    ),
    (
        "no-frontmatter-delimiter",
        lambda t: "# no frontmatter here\n",
        "frontmatter",
    ),
    (
        "unclosed-frontmatter",
        lambda t: "---\nid: shared.fixture\nrole: shared\n# never closed\n",
        "not closed",
    ),
)


@pytest.mark.parametrize(
    "mutate,match",
    [c[1:] for c in _MALFORMED_CASES],
    ids=[c[0] for c in _MALFORMED_CASES],
)
def test_malformed_frontmatter_rejected(tmp_path: Path, mutate, match: str) -> None:
    # Positive control: the base (unmutated) fixture loads cleanly — proves the
    # rejections below are caused by the mutation, not a broken base fixture.
    valid_loader = _write_fragment(tmp_path / "valid", "fixture.md", _VALID_FRONTMATTER)
    fragment = valid_loader.load_fragment(Path("shared") / "fixture.md")
    assert fragment.id == "shared.fixture"
    assert fragment.dynamic_inputs == ("available_evidence",)

    text = mutate(_VALID_FRONTMATTER)
    loader = _write_fragment(tmp_path / "mutated", "fixture.md", text)
    with pytest.raises(FragmentValidationError, match=match):
        loader.load_fragment(Path("shared") / "fixture.md")


# ---------------------------------------------------------------------------
# ⑤ token lint: forbidden-token param + case-insensitive + every-shipped-passes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "token",
    ["read tool", "codex exec", "pi --mode json", ".claude/", "apply_patch", "message_end"],
)
def test_forbidden_harness_token_rejected(tmp_path: Path, token: str) -> None:
    body = f"# A body that mentions {token} explicitly.\n"
    text = _VALID_FRONTMATTER.rsplit("\n# ", 1)[0] + "\n" + body
    loader = _write_fragment(tmp_path, "fixture.md", text)
    with pytest.raises(FragmentValidationError, match="harness-specific token"):
        loader.load_fragment(Path("shared") / "fixture.md")


def test_forbidden_token_lint_case_insensitive_and_shipped_library_passes(
    tmp_path: Path,
) -> None:
    text = _VALID_FRONTMATTER.rsplit("\n# ", 1)[0] + "\n# Use CODEX EXEC for this step.\n"
    loader = _write_fragment(tmp_path, "fixture.md", text)
    with pytest.raises(FragmentValidationError, match="codex exec"):
        loader.load_fragment(Path("shared") / "fixture.md")

    assert forbidden_token_in("call the READ TOOL now") == "READ TOOL"
    assert forbidden_token_in("call the read tool") == "read tool"
    assert forbidden_token_in("a clean universal sentence") is None

    for fragment in validate_all():
        assert forbidden_token_in(fragment.body) is None, (
            f"shipped fragment {fragment.id} contains a harness-specific token"
        )
