"""Per-input ``max_context_policy`` override (v0.1.57 FR3 / AC-6 / N2).

Covers:

* **loader** — an optional ``input_policies`` frontmatter mapping loads onto
  ``Fragment.input_policies``; a fragment declaring none defaults to ``{}`` (byte-stable); a
  malformed ``input_policies`` (non-mapping / non-string values) is rejected by the loader.
* **AC-6** — one ``select_all`` call resolves mixed per-input policies from a TEST-FIXTURE
  fragment (NOT a shipped public fragment, N2): the overridden input resolves at its own policy
  while an unlisted input falls back to the fragment-global ``max_context_policy``.
* **byte-stable** — ``select_all`` with ``input_policies`` absent (``None``) is identical to
  ``input_policies={}`` and to the pre-FR3 single-policy behaviour.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.lifecycle.context_selector import (
    ContextSelector,
    MaxContextPolicy,
    SpecContext,
)
from dadaia_workspace.features.lifecycle.fragments.loader import (
    FragmentLoader,
    FragmentValidationError,
)

pytestmark = pytest.mark.unit

# A distinctive body marker present in the fixture SPEC.md body but NOT its frontmatter, so an
# EXACT_FILES_ONLY resolution includes it while a SUMMARY (frontmatter-only) resolution omits it.
_MARKER = "DISTINCTIVE_BODY_MARKER"


def _write_fragment(root: Path, *, input_policies_block: str) -> FragmentLoader:
    frag_dir = root / "fixture"
    frag_dir.mkdir(parents=True)
    (frag_dir / "per-input.md").write_text(
        "---\n"
        "id: fixture.per_input\n"
        "role: product-engineer\n"
        "workflow: fixture\n"
        "step: per_input\n"
        "static_inputs: []\n"
        "dynamic_inputs: [spec_draft, approved_spec]\n"
        "output_schema: fixture-out-v1\n"
        "max_context_policy: summary\n"
        f"{input_policies_block}"
        "---\n"
        "Fixture body.\n",
        encoding="utf-8",
    )
    return FragmentLoader(root)


def _seed_specs(tmp_path: Path) -> Path:
    specs = tmp_path / "specs"
    (specs / "releases" / "v0.1.57").mkdir(parents=True)
    (specs / "releases" / "v0.1.57" / "SPEC.md").write_text(
        f"---\ntitle: Fixture Spec\n---\n{_MARKER} appears only in the body.\n", encoding="utf-8"
    )
    return specs


def _selector(tmp_path: Path) -> ContextSelector:
    return ContextSelector(SpecContext(specs_dir=_seed_specs(tmp_path), release_id="v0.1.57"))


# ---------------------------------------------------------------------------
# loader
# ---------------------------------------------------------------------------


def test_loader_parses_input_policies(tmp_path: Path) -> None:
    loader = _write_fragment(
        tmp_path / "frags",
        input_policies_block="input_policies:\n  spec_draft: exact-files-only\n",
    )
    fragment = loader.load_fragment("fixture.per_input")
    assert fragment.input_policies == {"spec_draft": "exact-files-only"}
    assert fragment.max_context_policy == "summary"  # the fragment-global default is intact


def test_loader_absent_input_policies_defaults_empty(tmp_path: Path) -> None:
    loader = _write_fragment(tmp_path / "frags", input_policies_block="")
    fragment = loader.load_fragment("fixture.per_input")
    assert fragment.input_policies == {}


def test_loader_rejects_non_mapping_input_policies(tmp_path: Path) -> None:
    loader = _write_fragment(
        tmp_path / "frags", input_policies_block="input_policies: not-a-mapping\n"
    )
    with pytest.raises(FragmentValidationError, match="input_policies.*must be a mapping"):
        loader.load_fragment("fixture.per_input")


def test_loader_rejects_non_string_policy_value(tmp_path: Path) -> None:
    loader = _write_fragment(
        tmp_path / "frags", input_policies_block="input_policies:\n  spec_draft: 3\n"
    )
    with pytest.raises(FragmentValidationError, match="must map strings to strings"):
        loader.load_fragment("fixture.per_input")


# ---------------------------------------------------------------------------
# AC-6 — mixed per-input policy resolution in one select_all
# ---------------------------------------------------------------------------


def test_ac6_mixed_per_input_policies_in_one_select_all(tmp_path: Path) -> None:
    loader = _write_fragment(
        tmp_path / "frags",
        input_policies_block="input_policies:\n  spec_draft: exact-files-only\n",
    )
    fragment = loader.load_fragment("fixture.per_input")
    selector = _selector(tmp_path)

    audit = selector.select_all(
        "per_input",
        fragment.dynamic_inputs,
        fragment.max_context_policy,  # fragment-global = summary
        input_policies=dict(fragment.input_policies),
    )
    by_name = {result.name: result for result in audit.results}
    # spec_draft is overridden to EXACT_FILES_ONLY → full body (marker present).
    assert by_name["spec_draft"].policy is MaxContextPolicy.EXACT_FILES_ONLY
    assert _MARKER in by_name["spec_draft"].content
    # approved_spec is NOT listed → falls back to the fragment-global SUMMARY (marker absent).
    assert by_name["approved_spec"].policy is MaxContextPolicy.SUMMARY
    assert _MARKER not in by_name["approved_spec"].content


# ---------------------------------------------------------------------------
# byte-stable — absent input_policies == today's behaviour
# ---------------------------------------------------------------------------


def test_select_all_byte_stable_when_input_policies_absent(tmp_path: Path) -> None:
    selector = _selector(tmp_path)
    names = ("spec_draft", "approved_spec")
    without = selector.select_all("s", names, MaxContextPolicy.SUMMARY)
    with_empty = selector.select_all("s", names, MaxContextPolicy.SUMMARY, input_policies={})
    with_none = selector.select_all("s", names, MaxContextPolicy.SUMMARY, input_policies=None)
    assert without == with_empty == with_none
    # every input resolved at the single fragment-global policy.
    assert all(result.policy is MaxContextPolicy.SUMMARY for result in without.results)
