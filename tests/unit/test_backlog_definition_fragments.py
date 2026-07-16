"""T-26-02 — the real backlog_definition step fragments load + validate (SPEC §3.4).

Each model-step fragment carries the fixed 8-key frontmatter and a markdown body, modelled
on release_definition/*.md. The pure Python steps (subject_bind, reconcile_decision,
backlog_review_gate) carry NO fragment, so only four fragments exist here. The loader
already enforces frontmatter shape + the harness-universal token lint; this test pins the
ids, declared output schemas, and the _README stub removal.
"""

from __future__ import annotations

import pytest

from dadaia_workspace.features.lifecycle.fragments.loader import (
    FragmentLoader,
    FragmentNotFoundError,
)

# (fragment id, declared output schema) per SPEC §4.
_EXPECTED = {
    "backlog_definition.intake_grill": "backlog-demand-v1",
    "backlog_definition.backlog_authoring": "backlog-item-v1",
}


@pytest.mark.parametrize(("frag_id", "schema"), sorted(_EXPECTED.items()))
def test_fragment_loads_with_expected_schema(frag_id: str, schema: str) -> None:
    loader = FragmentLoader()
    fragment = loader.load_fragment(frag_id)
    assert fragment.id == frag_id
    assert fragment.workflow == "backlog_definition"
    assert fragment.output_schema == schema
    assert fragment.body.strip(), "fragment body must be non-empty"


def test_backlog_definition_dir_shape_readme_removed_and_pure_python_steps_absent() -> None:
    loader = FragmentLoader()

    fragments = loader.list_fragments("backlog_definition")
    assert {f.id for f in fragments} == set(_EXPECTED)

    readme = loader.root / "backlog_definition" / "_README.md"
    assert not readme.exists()

    # subject_bind / reconcile_decision / backlog_review_gate must not exist as
    # fragments — they are pure Python steps.
    for absent in (
        "backlog_definition.subject_bind",
        "backlog_definition.reconcile_decision",
        "backlog_definition.backlog_review_gate",
    ):
        with pytest.raises(FragmentNotFoundError):
            loader.load_fragment(absent)
