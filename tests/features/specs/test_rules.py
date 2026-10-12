"""The doctor parses shared facts once per check run, and derives check order, fix dispatch
and the ``--fix`` help from one ordered rule table.
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.features.specs import rules as rules_mod
from dadaia_workspace.features.specs.doctor import SpecsDoctor


def _minimal_specs(tmp_path: Path) -> Path:
    specs = tmp_path / "specs"
    (specs / "memory" / "product").mkdir(parents=True)
    (specs / "releases" / "1.2.3").mkdir(parents=True)
    (specs / "releases" / "1.2.3" / "_RELEASE.json").write_text(
        '{"schema": "release-state-v1", "release": "1.2.3", "phase": "IMPLEMENTATION",'
        ' "defined": null, "implemented": null, "shipped": null,'
        ' "log": []}',
        encoding="utf-8",
    )
    return specs


def test_active_release_is_parsed_once_per_check_run(tmp_path: Path, monkeypatch: object) -> None:
    import dadaia_workspace.features.specs.specs_tree as st

    calls = {"n": 0}
    real = st.resolve_active_release

    def _counting(specs_dir: Path):  # type: ignore[no-untyped-def]
        calls["n"] += 1
        return real(specs_dir)

    monkeypatch.setattr(st, "resolve_active_release", _counting)  # type: ignore[attr-defined]
    SpecsDoctor(_minimal_specs(tmp_path)).check()
    assert calls["n"] == 1, f"active release parsed {calls['n']}x — must be once per run"


def test_fix_dispatch_and_help_derive_from_the_registry() -> None:
    fixable = set(rules_mod.FIX_BY_CODE)
    assert fixable == {
        "TREE-3",  # sa-unfixable-doctor-findings-say-doctor-fix: seeds a missing atom
        "TREE-4",
        "TREE-5",
        "SPEC-DOC-034",
        "MEM-PLACEHOLDER-1",
        "FIXED-1",
        "FIXED-2",
        "SPEC-DOC-046",  # the legacy RELEASE.json rename
    }
    help_text = rules_mod.render_fix_help()
    for code in fixable:
        assert code in help_text, code
    assert "TREE-8" not in help_text, "TREE-8 is never auto-fixed (decision D8)"
