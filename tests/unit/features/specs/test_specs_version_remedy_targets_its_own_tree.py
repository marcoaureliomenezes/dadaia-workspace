"""The remedy a doctor prescribes must act on the tree the doctor just judged.

Found by sweeping the same class twice over: for every corruption a doctor reports, does
the command it prescribes actually repair it? `dadaia public doctor` was swept first and
gave up `r25-doctor-blind-to-a-disabled-git-chokepoint`. `dadaia specs doctor` gives up
this one.

`dadaia specs doctor --context X` reports SPECS-VERSION against context X and prescribes
the bare line ``Run: dadaia specs upgrade``. That command has no ``--context`` option at
all — it takes ``--specs-dir``, and with neither it operates on the **bound** context. So
pasting the prescribed remedy after a ``--context`` diagnosis either does nothing (no bind),
or, worse, silently upgrades a DIFFERENT specs tree than the one that was just judged. An
upgrade rewrites artifacts and stamps the constitution; doing that to the wrong repo is a
considerably worse outcome than the staleness it was meant to fix.

The rule this repository keeps relearning: a remedy that does not carry its target is not a
remedy. R-23 says the same thing about lifecycle blocks, and this is the doctor's version of
it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.specs.doctor_coherence import CoherenceValidator

pytestmark = pytest.mark.unit


def _stale_tree(tmp_path: Path) -> Path:
    specs = tmp_path / "repos" / "somerepo" / "specs"
    specs.mkdir(parents=True)
    # No specs_pattern_version stamp ⇒ reads as 0, which is below canonical.
    (specs / "constitution.md").write_text("# Constitution\n", encoding="utf-8")
    return specs


def test_the_version_remedy_names_the_tree_it_was_produced_for(tmp_path: Path) -> None:
    specs = _stale_tree(tmp_path)

    issues = CoherenceValidator(specs).check_specs_pattern_version()

    assert issues, "a tree below the canonical pattern version reported nothing"
    description = issues[0].description
    assert "--specs-dir" in description, (
        "the prescribed upgrade carries no target, so it acts on the bound context — a "
        f"different tree than the one just judged: {description!r}"
    )
    assert str(specs) in description, (
        f"the remedy must name THIS specs dir so it can be pasted verbatim: {description!r}"
    )


def test_a_current_tree_still_reports_nothing(tmp_path: Path) -> None:
    """The guard the other way: this check is WARN-only and must stay silent when fine."""
    from dadaia_workspace.core import specs_version as ver

    specs = _stale_tree(tmp_path)
    # The stamp lives in YAML FRONTMATTER; writing it as a body line reads as unstamped,
    # which is how the first draft of this guard failed for its own reason rather than the
    # product's.
    (specs / "constitution.md").write_text(
        f"---\nspecs_pattern_version: {ver.CANONICAL_SPECS_VERSION}\n---\n\n# Constitution\n",
        encoding="utf-8",
    )

    assert CoherenceValidator(specs).check_specs_pattern_version() == []
