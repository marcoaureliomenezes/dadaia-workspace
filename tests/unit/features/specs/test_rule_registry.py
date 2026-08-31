"""F010/F012 (20260830-design-bug-surface-audit): the doctor has a parsed SpecsTree
snapshot and ONE rule registry.

- F010: shared facts are parsed ONCE per check() run — RELEASE.json was re-read and
  re-parsed by four checks per run, so rules could observe different states mid-run.
- F012: check order, fix dispatch and the --fix CLI help all derive from one ordered
  RULES table — the hand-kept if/elif chain and the wrong hand-written help (TREE-3
  claimed fixable, six real fixables omitted) cannot drift again.

Intent: contract; size: unit.
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.features.specs import rules as rules_mod
from dadaia_workspace.features.specs.doctor import SpecsDoctor


def _minimal_specs(tmp_path: Path) -> Path:
    specs = tmp_path / "specs"
    (specs / "memory" / "product").mkdir(parents=True)
    (specs / "releases" / "1.2.3").mkdir(parents=True)
    (specs / "releases" / "1.2.3" / "RELEASE.json").write_text(
        '{"schema": "release-state-v1", "release": "1.2.3", "phase": "IMPLEMENTATION",'
        ' "rc": 0, "defined": null, "implemented": null, "shipped": null,'
        ' "audited": null, "log": []}',
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
        "TREE-4",
        "TREE-5",
        "REPO-DADAIA-1",
        "TREE-8",
        "SPEC-DOC-034",
        "SPEC-DOC-044",
        "SPEC-DOC-046",
        "MEM-PLACEHOLDER-1",
    }
    help_text = rules_mod.render_fix_help()
    for code in fixable:
        assert code in help_text, code
    assert "TREE-3" not in help_text, "--fix help claimed TREE-3 fixable; it is not"


def test_cli_fix_help_is_the_derived_text() -> None:
    src = Path("dadaia_workspace/cli/commands/specs.py").read_text(encoding="utf-8")
    assert "render_fix_help()" in src
    assert "TREE-3: render missing memory HTML" not in src


def test_check_iterates_the_registry() -> None:
    import inspect

    src = inspect.getsource(SpecsDoctor.check)
    assert "RULES" in src, "check() must iterate the ONE ordered registry"
    fix_src = inspect.getsource(SpecsDoctor.fix)
    assert "FIX_BY_CODE" in fix_src and "elif issue.code" not in fix_src
