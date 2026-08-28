"""`dadaia specs doctor --recipe` (T-050-05, FR1, A1.3).

Intent: CONTRACT — A1.3.

``--recipe`` renders the SAME finding objects ``--json`` already emits — the recipe
text hangs off each finding, never a second step table that could drift from the
findings (software-architect's accepted-with-condition on SA-11).
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.features.specs.scaffolder import scaffold

_runner = CliRunner()

_REPO_ROOT = Path(__file__).parent.parent.parent.parent
_TEMPLATES_DIR = _REPO_ROOT / "dadaia_workspace" / "public" / "templates"
_PUBLIC_DIR = _REPO_ROOT / "dadaia_workspace" / "public"


def _make_specs_with_findings(tmp_path: Path) -> Path:
    """A scaffolded tree with a real, un-fixed finding present (TREE-8 on a stray
    root folder) — deterministic and independent of this repo's own migration state.
    """
    specs = tmp_path / "specs"
    result = scaffold(
        specs_dir=specs, project_name="recipe-test", force=False, templates_dir=_TEMPLATES_DIR
    )
    assert result.errors == [], f"Scaffold errors: {result.errors}"
    (specs / "scratch-legacy-folder").mkdir()
    return specs


def test_recipe_steps_trace_to_a_finding_id_present_in_the_same_run_json_output(
    tmp_path: Path,
) -> None:
    """Every ``--recipe`` step embeds a finding code (id) that is present among the
    SAME run's ``--json`` finding codes — never a fabricated id from a second table."""
    specs = _make_specs_with_findings(tmp_path)

    json_result = _runner.invoke(
        app,
        ["specs", "doctor", "--json", "--specs-dir", str(specs), "--public-dir", str(_PUBLIC_DIR)],
    )
    payload = json.loads(json_result.output)
    json_codes = {issue["code"] for issue in payload["issues"]}
    assert json_codes, "Precondition: the fixture must produce at least one finding"

    recipe_result = _runner.invoke(
        app,
        [
            "specs",
            "doctor",
            "--recipe",
            "--specs-dir",
            str(specs),
            "--public-dir",
            str(_PUBLIC_DIR),
        ],
    )
    recipe_lines = [
        line for line in recipe_result.output.splitlines() if line and line[0].isdigit()
    ]
    assert recipe_lines, f"Expected numbered recipe steps; output:\n{recipe_result.output}"
    for line in recipe_lines:
        # Each step is "N. [CODE] (path) description" — the code must trace to --json.
        assert "[" in line and "]" in line, f"Step is not concrete/traceable: {line}"
        code = line.split("[", 1)[1].split("]", 1)[0]
        assert code in json_codes, (
            f"Recipe step traces to code {code!r}, not present in the same run's "
            f"--json output ({json_codes})"
        )


def test_recipe_emits_zero_steps_when_the_run_has_zero_findings() -> None:
    """A1.3: a run with zero findings emits zero recipe steps.

    Exercised directly at the rendering seam (``_render_recipe_steps``, the "own
    function" A1.3 requires) rather than through a real scaffolded tree: this repo's
    current v6-canon transition state carries one known, recorded, out-of-scope
    doctor_governance.py gap (SPEC-DOC-035 on backlog/AGENTS.md — see
    test_scaffolder_doctor.py / test_cli_specs_doctor_recipe.py's sibling assertions),
    so no real tree is reliably zero-finding today; the rendering function's own
    zero-in/zero-out behavior is what A1.3 actually asserts.
    """
    from dadaia_workspace.cli.commands.specs import _render_recipe_steps

    assert _render_recipe_steps([]) == []


def test_recipe_takes_precedence_over_json_when_both_flags_are_passed(tmp_path: Path) -> None:
    """``--recipe`` renders in its OWN function, never folded into the --json branch
    (A1.3) — passing both flags together still yields recipe text, not a JSON blob."""
    specs = _make_specs_with_findings(tmp_path)

    result = _runner.invoke(
        app,
        [
            "specs",
            "doctor",
            "--recipe",
            "--json",
            "--specs-dir",
            str(specs),
            "--public-dir",
            str(_PUBLIC_DIR),
        ],
    )
    assert "[recipe]" in result.output, f"Expected recipe output; got:\n{result.output}"
