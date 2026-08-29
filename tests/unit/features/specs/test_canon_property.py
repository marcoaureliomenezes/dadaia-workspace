"""Intent: CONTRACT — v0.5.1 K4, "one canon table: scaffold is canon rendered, doctor
is canon checked."

The property this task exists to hold: for every shape the scaffolder produces,
``canon.scaffold(t)`` (or the on-demand ``canon.release_new``/``backlog_new`` siblings)
leaves a tree where ``canon.check_tree(t) == []`` AND the full ``SpecsDoctor`` reports
ZERO errors. This ONE parametrized test replaces the six historical regression tests
that each pinned one bug where a fresh scaffold failed its own doctor (all resolved,
``specs/bugs/BUGS.jsonl``): ``fresh-specs-scaffold-fails-specs-doctor``,
``specs-init-creates-what-doctor-refuses``, ``scaffold-artifacts-fail-own-workflow
-gates``, ``fresh-release-scaffold-emits-spec-doctor-warnings-042``,
``default-context-scaffold-fails-specs-doctor``, ``release-new-rejects-semver-but
-doctor-requires-it``. Deleted regression tests replaced by this file:

- ``tests/unit/features/specs/test_doctor.py::
  test_freshly_opened_release_segment_is_doctor_clean`` (named bug-042 regression) —
  covered here by the "fresh release segment" case.
- ``tests/unit/features/specs/test_doctor.py::
  test_fresh_scaffold_passes_all_tree_invariants`` (generic "scaffold -> 0 TREE errors")
  — covered here by the "fresh root specs" case, now asserting the FULL doctor (every
  code, not just TREE-*) is clean, a strictly stronger bar.

Every OTHER scaffolder/doctor test in the suite stays: they pin distinct facts (exact
file lists, idempotence, --force overwrite, individual TREE-8/SPEC-DOC-NNN codes on a
deliberately BROKEN fixture) this property test does not restate.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.backlog.document import backlog_new
from dadaia_workspace.features.specs import SpecsDoctor
from dadaia_workspace.features.specs import canon as canon_mod
from dadaia_workspace.features.specs.scaffolder import scaffold, scaffold_release_segment

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[4]
_TEMPLATES_DIR = _REPO_ROOT / "dadaia_workspace" / "public" / "templates"
_PUBLIC_DIR = _REPO_ROOT / "dadaia_workspace" / "public"


def _assert_canon_and_doctor_clean(specs_dir: Path) -> None:
    violations = canon_mod.check_tree(specs_dir)
    assert violations == [], f"canon.check_tree found violations: {violations}"

    issues = SpecsDoctor(specs_dir, public_dir=_PUBLIC_DIR, templates_dir=_TEMPLATES_DIR).check()
    errors = [i for i in issues if i.severity.value == "error"]
    assert errors == [], (
        f"SpecsDoctor reported {len(errors)} error(s): {[e.to_dict() for e in errors]}"
    )


def _fresh_root_specs(tmp_path: Path) -> Path:
    """Fresh root-level specs/ tree — the ``dadaia specs init`` shape."""
    specs_dir = tmp_path / "specs"
    result = scaffold(
        specs_dir=specs_dir, project_name="root-project", force=False, templates_dir=_TEMPLATES_DIR
    )
    assert result.errors == [], result.errors
    return specs_dir


def _fresh_repo_specs(tmp_path: Path) -> Path:
    """Fresh specs/ tree nested under a repo — the ``repos/<slug>/specs`` shape.

    ``scaffold()`` itself is location-agnostic (it never inspects anything above
    *specs_dir*) — this case proves the canon table's cleanliness property does not
    depend on being scaffolded at a workspace root."""
    specs_dir = tmp_path / "repos" / "my-repo" / "specs"
    result = scaffold(
        specs_dir=specs_dir, project_name="repo-project", force=False, templates_dir=_TEMPLATES_DIR
    )
    assert result.errors == [], result.errors
    return specs_dir


def _fresh_release(tmp_path: Path) -> Path:
    """Fresh root specs/ plus one freshly-minted release (``dadaia release new``)."""
    specs_dir = _fresh_root_specs(tmp_path)
    canon_mod.release_new(specs_dir, "0.6.0")
    return specs_dir


def _fresh_release_segment(tmp_path: Path) -> Path:
    """Fresh root specs/ plus one freshly-opened release SEGMENT
    (``scaffold_release_segment``) — the exact shape bug
    ``fresh-release-scaffold-emits-spec-doctor-warnings-042`` regressed on."""
    specs_dir = _fresh_root_specs(tmp_path)
    result = scaffold_release_segment(specs_dir, "0.6.0", "alpha-1")
    assert result.errors == [], result.errors
    return specs_dir


def _fresh_backlog_entry(tmp_path: Path) -> Path:
    """Fresh root specs/ plus one freshly-created backlog entry (``dadaia backlog
    new``, ``features.backlog.document.backlog_new`` — untouched by this task, but a
    canon-conformant writer this property test must also hold for)."""
    specs_dir = _fresh_root_specs(tmp_path)
    backlog_new(specs_dir, "a-fresh-idea")
    return specs_dir


@pytest.mark.parametrize(
    "make_tree",
    [
        pytest.param(_fresh_root_specs, id="fresh-root-specs"),
        pytest.param(_fresh_repo_specs, id="fresh-repo-specs"),
        pytest.param(_fresh_release, id="fresh-release"),
        pytest.param(_fresh_release_segment, id="fresh-release-segment"),
        pytest.param(_fresh_backlog_entry, id="fresh-backlog-entry"),
    ],
)
def test_scaffold_then_check_tree_and_doctor_are_both_clean(tmp_path, make_tree) -> None:  # type: ignore[no-untyped-def]
    specs_dir = make_tree(tmp_path)
    _assert_canon_and_doctor_clean(specs_dir)


def test_canon_scaffold_bare_call_matches_scaffolder_wrapper_output(tmp_path: Path) -> None:
    """``canon.scaffold`` (the design-mandated ``scaffold(specs_dir) -> list[Path]``
    shape) is clean on its own, with zero caller-supplied context — not merely through
    the CLI-facing ``scaffolder.scaffold`` wrapper's richer signature."""
    specs_dir = tmp_path / "specs"
    created = canon_mod.scaffold(specs_dir, public_dir=_PUBLIC_DIR)
    assert created, "canon.scaffold must write at least the required_at_birth entries"
    _assert_canon_and_doctor_clean(specs_dir)
