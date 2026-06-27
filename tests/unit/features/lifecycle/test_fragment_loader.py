"""Unit tests for the lifecycle fragment loader (WS-3 / T-24-07)."""

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
    "shared.output_handoff",
    "shared.write_scope",
}
# Workflow dirs that still ship only a `_README.md` stub (no authored step fragments).
# ``implementation`` left this set in v0.1.24 (T-24-11): it now ships three authored step
# fragments (implement_tdd, self_verify, qa_review). ``backlog_definition`` left this set in
# v0.1.26 R2 (T-26-02): it now ships four authored step fragments. ``audit`` left this set
# in v0.1.30 Wave E (T-30-E-01); ``research``/``bug_report`` follow in T-30-E-02/03.
# ``closure`` stays a README-only stub (its close worker is generic, no fragment).
_DEFERRED_WORKFLOW_DIRS = {
    "closure",
    "research",
    "bug_report",
}

# Workflow dirs that ship authored step fragments backing a real fragment+gate body.
# Grown task-by-task across Wave E: audit (E-01), research (E-02), bug_report (E-03).
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


# ---------------------------------------------------------------------------
# Shipped fragment library — load + validate the real packaged tree.
# ---------------------------------------------------------------------------


def test_validate_all_loads_every_shipped_fragment() -> None:
    fragments = validate_all()
    assert fragments, "expected the packaged fragment library to be non-empty"
    assert all(isinstance(f, Fragment) for f in fragments)


def test_release_definition_step_fragments_exist_and_load() -> None:
    rd = {f.id for f in list_fragments(workflow="release_definition")}
    missing = _RELEASE_DEFINITION_STEP_IDS - rd
    assert not missing, f"release_definition workflow references missing fragments: {missing}"
    # The derived set is non-empty — guards against a refactor silently emptying _SEQUENCE.
    assert _RELEASE_DEFINITION_STEP_IDS


def test_shared_fragments_cited_by_release_definition_exist() -> None:
    shared = {f.id for f in list_fragments(workflow="shared")}
    assert shared >= _SHARED_IDS
    # Every shared id the workflow actually cites is a real, loadable shared fragment.
    assert _shared_ids_cited_by_release_definition() <= shared


def test_implementation_ladder_fragments_exist_and_load() -> None:
    # Fix #2: the implementation pipeline ladder's fragment ids must all resolve to real
    # shipped fragments; the set is derived from the ladder, not hand-copied.
    ladder_ids = _implementation_ladder_fragment_ids()
    assert ladder_ids, "implementation ladder declared no fragment ids"
    loadable = {f.id for f in validate_all()}
    missing = ladder_ids - loadable
    assert not missing, f"implementation ladder references missing fragments: {missing}"


def test_load_fragment_by_id_round_trips() -> None:
    fragment = load_fragment("release_definition.spec_review_architecture")
    assert fragment.id == "release_definition.spec_review_architecture"
    assert fragment.workflow == "release_definition"
    assert fragment.step == "spec_review_architecture"
    assert fragment.output_schema == "spec-review-verdict-v1"
    assert "specs/memory/architecture.md" in fragment.static_inputs
    assert fragment.body.startswith("# SPEC architecture review")


def test_load_fragment_by_path_round_trips() -> None:
    loader = FragmentLoader()
    fragment = loader.load_fragment(Path("shared") / "anti-slop.md")
    assert fragment.id == "shared.anti_slop"


def test_load_fragment_unknown_id_raises() -> None:
    with pytest.raises(FragmentNotFoundError):
        load_fragment("release_definition.does_not_exist")


# ---------------------------------------------------------------------------
# Counts (5 shared, 8 release_definition; backlog_definition now ships 4 authored fragments).
# ---------------------------------------------------------------------------


def test_fragment_counts() -> None:
    loader = FragmentLoader()
    assert len(loader.list_fragments(workflow="shared")) == 5
    assert len(loader.list_fragments(workflow="release_definition")) == 8


def test_implementation_dir_ships_its_three_authored_fragments() -> None:
    # T-24-11: the implementation workflow now ships three authored step fragments
    # backing the pipeline's implementation + QA-review steps. It is no longer a
    # README-only deferred stub dir.
    loader = FragmentLoader()
    ids = {f.id for f in loader.list_fragments(workflow="implementation")}
    assert ids == {
        "implementation.implement_tdd",
        "implementation.self_verify",
        "implementation.qa_review",
    }


def test_deferred_workflow_dirs_present_with_readme_stub_only() -> None:
    loader = FragmentLoader()
    dirs = set(loader.list_workflow_dirs())
    assert dirs >= _DEFERRED_WORKFLOW_DIRS
    # Deferred dirs ship only a `_README.md` stub: no fragments are discovered there.
    for workflow in _DEFERRED_WORKFLOW_DIRS:
        assert loader.list_fragments(workflow=workflow) == [], (
            f"deferred workflow '{workflow}' must carry no step fragments yet"
        )
        readme = loader.root / workflow / "_README.md"
        assert readme.exists(), f"deferred workflow '{workflow}' must ship a _README.md stub"


def test_authored_workflow_dirs_ship_step_fragments() -> None:
    # T-30-E-01..03: audit / research / bug_report are no longer README-only deferred
    # stubs — each ships real fragment+gate step fragments backing its workflow body.
    loader = FragmentLoader()
    for workflow in _AUTHORED_WORKFLOW_DIRS:
        fragments = loader.list_fragments(workflow=workflow)
        assert fragments, f"authored workflow '{workflow}' must ship step fragments"
        for fragment in fragments:
            assert fragment.workflow == workflow


def test_readme_stubs_are_not_treated_as_fragments() -> None:
    # No fragment id should ever resolve to a _README stub.
    ids = {f.id for f in validate_all()}
    assert all(not fid.endswith("_README") for fid in ids)


# ---------------------------------------------------------------------------
# Malformed metadata is rejected.
# ---------------------------------------------------------------------------


def _write_fragment(tmp_path: Path, name: str, text: str) -> FragmentLoader:
    root = tmp_path / "lifecycle_fragments"
    (root / "shared").mkdir(parents=True, exist_ok=True)
    (root / "shared" / name).write_text(text, encoding="utf-8")
    return FragmentLoader(root=root)


def test_valid_fixture_loads(tmp_path: Path) -> None:
    loader = _write_fragment(tmp_path, "fixture.md", _VALID_FRONTMATTER)
    fragment = loader.load_fragment(Path("shared") / "fixture.md")
    assert fragment.id == "shared.fixture"
    assert fragment.dynamic_inputs == ("available_evidence",)


def test_missing_required_key_rejected(tmp_path: Path) -> None:
    text = _VALID_FRONTMATTER.replace("output_schema: handoff-v1.1\n", "")
    loader = _write_fragment(tmp_path, "fixture.md", text)
    with pytest.raises(FragmentValidationError, match="output_schema"):
        loader.load_fragment(Path("shared") / "fixture.md")


def test_wrong_type_for_list_key_rejected(tmp_path: Path) -> None:
    text = _VALID_FRONTMATTER.replace(
        "dynamic_inputs: [available_evidence]", "dynamic_inputs: not-a-list"
    )
    loader = _write_fragment(tmp_path, "fixture.md", text)
    with pytest.raises(FragmentValidationError, match="dynamic_inputs"):
        loader.load_fragment(Path("shared") / "fixture.md")


def test_empty_string_key_rejected(tmp_path: Path) -> None:
    text = _VALID_FRONTMATTER.replace("output_schema: handoff-v1.1", 'output_schema: ""')
    loader = _write_fragment(tmp_path, "fixture.md", text)
    with pytest.raises(FragmentValidationError, match="output_schema"):
        loader.load_fragment(Path("shared") / "fixture.md")


def test_non_string_list_item_rejected(tmp_path: Path) -> None:
    text = _VALID_FRONTMATTER.replace("dynamic_inputs: [available_evidence]", "dynamic_inputs: [3]")
    loader = _write_fragment(tmp_path, "fixture.md", text)
    with pytest.raises(FragmentValidationError, match="dynamic_inputs"):
        loader.load_fragment(Path("shared") / "fixture.md")


def test_missing_frontmatter_delimiter_rejected(tmp_path: Path) -> None:
    loader = _write_fragment(tmp_path, "fixture.md", "# no frontmatter here\n")
    with pytest.raises(FragmentValidationError, match="frontmatter"):
        loader.load_fragment(Path("shared") / "fixture.md")


def test_unclosed_frontmatter_rejected(tmp_path: Path) -> None:
    text = "---\nid: shared.fixture\nrole: shared\n# never closed\n"
    loader = _write_fragment(tmp_path, "fixture.md", text)
    with pytest.raises(FragmentValidationError, match="not closed"):
        loader.load_fragment(Path("shared") / "fixture.md")


# ---------------------------------------------------------------------------
# Harness-specific token lint (SECONDARY guarantee).
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


def test_forbidden_token_match_is_case_insensitive(tmp_path: Path) -> None:
    text = _VALID_FRONTMATTER.rsplit("\n# ", 1)[0] + "\n# Use CODEX EXEC for this step.\n"
    loader = _write_fragment(tmp_path, "fixture.md", text)
    with pytest.raises(FragmentValidationError, match="codex exec"):
        loader.load_fragment(Path("shared") / "fixture.md")


def test_forbidden_token_in_helper() -> None:
    assert forbidden_token_in("call the read tool") == "read tool"
    assert forbidden_token_in("a clean universal sentence") is None


def test_every_shipped_fragment_passes_the_token_lint() -> None:
    # The packaged fragments are loaded through validate_all, which runs the lint;
    # this assertion is the explicit statement that no shipped body trips it.
    for fragment in validate_all():
        assert forbidden_token_in(fragment.body) is None, (
            f"shipped fragment {fragment.id} contains a harness-specific token"
        )
