"""Integration tests for the workflow model-governance CLI surface (T-28-A-09).

Covers D-3 (``--step-model`` profile ids only), ``--show-policy``, the read-only
``workflow policy show`` / ``workflow profiles list`` verbs, and LAW-1 harness rejection
(``claude`` / ``opencode`` are not Layer-2 workers).

Merged per plan-integration.md (18 -> 4): (1) profiles list + harness filter; (2) policy
show table-driven (implementation/closure/audit/research/bug_report + unknown->reject);
(3) workflow doctor (clean / invalid JSON WMP-STATE / bad override WMP-OVERLAY); (4)
rejection matrix (raw model, unknown profile, harness mismatch, pi+codex conflict,
claude/opencode LAW1) — THE canonical D-3/LAW1 rejection owner; all other files' dupes
are deleted against it. Show-policy positive paths (pi per-step, step-harness) fold into
``test_pipeline_harness_governance_e2e.py``.

CLI rejection assertions are **terminal-width-independent**: Typer/Rich wraps the error
box at an env-dependent width and inserts box glyphs + line breaks mid-message, which
breaks naive substring asserts in CI. :func:`_norm` strips ANSI escapes and box-drawing
glyphs and collapses whitespace so a substring assert is stable regardless of width.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from tests.helpers.golden_platform import norm_stderr

_runner = CliRunner()

# _norm: consolidated into tests/helpers/golden_platform.norm_stderr (v0.1.64 FR1) —
# the wide-glyph variant (box-drawing block + smart quotes, stripped).


def _norm(text: str) -> str:
    return norm_stderr(text, wide_glyphs=True)


def _init_states(path: Path) -> Path:
    states = path / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text(
        json.dumps({"version": "1", "contexts": []}), encoding="utf-8"
    )
    (path / "repos").mkdir(exist_ok=True)
    return path


# ---------------------------------------------------------------------------
# (1) profiles list + harness filter
# ---------------------------------------------------------------------------


def test_workflow_profiles_list_and_harness_filter() -> None:
    result = _runner.invoke(app, ["lifecycle", "workflow", "profiles", "list", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    ids = {p["id"] for p in payload["profiles"]}
    assert "codex-implementation-standard" in ids
    assert "codex-review-deep" in ids
    # No Layer-1 / claude profiles.
    assert all(not p["model_id"].startswith("claude-") for p in payload["profiles"])

    filtered_result = _runner.invoke(
        app, ["lifecycle", "workflow", "profiles", "list", "--harness", "pi", "--json"]
    )
    assert filtered_result.exit_code == 0, filtered_result.output
    filtered_payload = json.loads(filtered_result.output)
    assert filtered_payload["profiles"]
    assert all(p["harness"] == "pi" for p in filtered_payload["profiles"])


# ---------------------------------------------------------------------------
# (2) policy show — table-driven (implementation/closure/audit/research/bug_report +
# unknown -> reject)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("workflow_id", "expected_steps"),
    [
        ("implementation", {"implement": ("codex-implementation-standard", "library-default")}),
        ("closure", {"close": (None, None)}),
        ("audit", {}),
        ("research", {}),
        ("bug_report", {}),
    ],
)
def test_workflow_policy_show_resolves_known_workflows(
    workflow_id: str,
    expected_steps: dict[str, tuple[str | None, str | None]],
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    workspace = _init_states(tmp_path)
    monkeypatch.chdir(workspace)
    result = _runner.invoke(app, ["lifecycle", "workflow", "policy", "show", workflow_id, "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["workflow_id"] == workflow_id
    steps = {s["step"]: s for s in payload["steps"]}
    assert payload["steps"], "resolved policy carries no governed steps"

    for step_label, (expected_profile, expected_source) in expected_steps.items():
        assert step_label in steps, f"{step_label} missing from resolved policy for {workflow_id}"
        if expected_profile is not None:
            assert steps[step_label]["model_profile"] == expected_profile
        if expected_source is not None:
            assert steps[step_label]["source"] == expected_source
        # Every governed step carries a resolved model profile on a real Layer-2 harness.
        assert steps[step_label]["model_profile"]
        assert steps[step_label]["harness"] in {"codex", "pi"}


def test_workflow_policy_show_unknown_workflow_rejected(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    workspace = _init_states(tmp_path)
    monkeypatch.chdir(workspace)
    result = _runner.invoke(app, ["lifecycle", "workflow", "policy", "show", "ghost-workflow"])
    assert result.exit_code != 0
    assert "unknown workflow" in _norm(result.output)


# ---------------------------------------------------------------------------
# (3) workflow doctor (T-28-D-02 — WMP-* governance invariants): clean / invalid
# JSON (WMP-STATE) / bad override (WMP-OVERLAY)
# ---------------------------------------------------------------------------


def test_workflow_doctor_clean_invalid_json_and_bad_overlay(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    workspace = _init_states(tmp_path)
    monkeypatch.chdir(workspace)

    clean_result = _runner.invoke(app, ["lifecycle", "workflow", "doctor", "--json"])
    assert clean_result.exit_code == 0, clean_result.output
    clean_payload = json.loads(clean_result.output)
    errors = [f for f in clean_payload["findings"] if f["severity"] == "error"]
    assert errors == [], errors

    overlay = workspace / ".dadaia" / "states" / "workflow_model_policy.json"
    overlay.write_text("{ not valid json", encoding="utf-8")
    invalid_json_result = _runner.invoke(app, ["lifecycle", "workflow", "doctor", "--json"])
    # Invalid state file is an ERROR → exit non-zero, but never a crash (clean JSON out).
    assert invalid_json_result.exit_code != 0, invalid_json_result.output
    invalid_json_payload = json.loads(invalid_json_result.output)
    codes = {f["code"] for f in invalid_json_payload["findings"]}
    assert "WMP-STATE" in codes

    overlay.write_text(
        json.dumps(
            {
                "schema_version": "workflow-model-policy-v1",
                "policy_id": "default",
                "contexts": {
                    "default": {
                        "workflows": {"implementation": {"steps": {"ghost": "codex-review-deep"}}}
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    bad_overlay_result = _runner.invoke(app, ["lifecycle", "workflow", "doctor", "--json"])
    assert bad_overlay_result.exit_code != 0, bad_overlay_result.output
    bad_overlay_payload = json.loads(bad_overlay_result.output)
    assert "WMP-OVERLAY" in {f["code"] for f in bad_overlay_payload["findings"]}


# ---------------------------------------------------------------------------
# (4) THE canonical D-3/LAW1 rejection matrix — raw model, unknown profile, harness
# mismatch, pi+codex step-model conflict, claude/opencode LAW1. All other files'
# copies of these rejections are deleted against this single owner.
# ---------------------------------------------------------------------------


def test_rejection_matrix_d3_and_law1(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    workspace = _init_states(tmp_path)
    monkeypatch.chdir(workspace)

    def _pipeline(args: list[str]):  # type: ignore[no-untyped-def]
        return _runner.invoke(
            app,
            [
                "lifecycle",
                "pipeline",
                "--skip-preflight",
                "--release-id",
                "v0.1.28",
                *args,
                "--show-policy",
            ],
        )

    # D-3: a raw <id>:<effort> model string is rejected — profile ids only.
    raw_result = _pipeline(["--step-model", "implement=gpt-5.5:high"])
    assert raw_result.exit_code != 0
    raw_text = _norm(raw_result.output)
    assert "profile id" in raw_text
    assert "not a raw model string" in raw_text

    # D-3: an unknown profile id is rejected.
    unknown_result = _pipeline(["--step-model", "implement=no-such-profile"])
    assert unknown_result.exit_code != 0
    assert "unknown model profile" in _norm(unknown_result.output)

    # D-3: a profile whose harness mismatches the step's resolved harness is rejected.
    mismatch_result = _pipeline(["--step-model", "implement=pi-reasoning-high"])
    assert mismatch_result.exit_code != 0
    assert "harness" in _norm(mismatch_result.output).lower()

    # --harness pi + a codex --step-model is a clean rejection (effective-harness conflict).
    conflict_result = _pipeline(
        ["--harness", "pi", "--step-model", "implement=codex-implementation-standard"]
    )
    assert conflict_result.exit_code != 0
    conflict_text = _norm(conflict_result.output).lower()
    assert "harness" in conflict_text
    assert "pi" in conflict_text

    # LAW 1: claude is not a Layer-2 workflow harness.
    claude_result = _runner.invoke(
        app,
        ["lifecycle", "pipeline", "--release-id", "v0.1.28", "--harness", "claude"],
    )
    assert claude_result.exit_code != 0
    assert "not a Layer-2 workflow harness" in _norm(claude_result.output)

    # LAW 1: opencode is not a Layer-2 workflow harness.
    opencode_result = _runner.invoke(
        app,
        ["lifecycle", "pipeline", "--release-id", "v0.1.28", "--harness", "opencode"],
    )
    assert opencode_result.exit_code != 0
    assert "not a Layer-2 workflow harness" in _norm(opencode_result.output)
