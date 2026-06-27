"""Integration tests for the workflow model-governance CLI surface (T-28-A-09).

Covers D-3 (``--step-model`` profile ids only), ``--show-policy``, the read-only
``workflow policy show`` / ``workflow profiles list`` verbs, and LAW-1 harness rejection
(``claude`` / ``opencode`` are not Layer-2 workers).

CLI rejection assertions are **terminal-width-independent**: Typer/Rich wraps the error
box at an env-dependent width and inserts box glyphs + line breaks mid-message, which
breaks naive substring asserts in CI. :func:`_norm` strips ANSI escapes and box-drawing
glyphs and collapses whitespace so a substring assert is stable regardless of width.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app

_runner = CliRunner()

_ANSI = re.compile(r"\x1b\[[0-9;]*m")
# Box-drawing + decorative glyphs Rich injects around error panels.
_BOX = re.compile(r"[─-╿‘’“”]")


def _norm(text: str) -> str:
    """Strip ANSI + box glyphs and collapse whitespace for width-independent asserts."""
    text = _ANSI.sub("", text)
    text = _BOX.sub(" ", text)
    return " ".join(text.split())


def _init_states(path: Path) -> Path:
    states = path / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text(
        json.dumps({"version": "1", "contexts": []}), encoding="utf-8"
    )
    (path / "repos").mkdir(exist_ok=True)
    return path


# ---------------------------------------------------------------------------
# Read-only inspection verbs
# ---------------------------------------------------------------------------


def test_workflow_profiles_list_json() -> None:
    result = _runner.invoke(app, ["lifecycle", "workflow", "profiles", "list", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    ids = {p["id"] for p in payload["profiles"]}
    assert "codex-implementation-standard" in ids
    assert "codex-review-deep" in ids
    # No Layer-1 / claude profiles.
    assert all(not p["model_id"].startswith("claude-") for p in payload["profiles"])


def test_workflow_profiles_list_filtered_by_harness() -> None:
    result = _runner.invoke(
        app, ["lifecycle", "workflow", "profiles", "list", "--harness", "pi", "--json"]
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["profiles"]
    assert all(p["harness"] == "pi" for p in payload["profiles"])


def test_workflow_policy_show_json(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    workspace = _init_states(tmp_path)
    monkeypatch.chdir(workspace)
    result = _runner.invoke(
        app, ["lifecycle", "workflow", "policy", "show", "implementation", "--json"]
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["workflow_id"] == "implementation"
    steps = {s["step"]: s for s in payload["steps"]}
    assert steps["implement"]["model_profile"] == "codex-implementation-standard"
    assert steps["implement"]["source"] == "library-default"


def test_workflow_policy_show_unknown_workflow_rejected(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    workspace = _init_states(tmp_path)
    monkeypatch.chdir(workspace)
    result = _runner.invoke(app, ["lifecycle", "workflow", "policy", "show", "ghost-workflow"])
    assert result.exit_code != 0
    assert "unknown workflow" in _norm(result.output)


def test_workflow_policy_show_closure_resolves(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """T-29-B-03 (AC-7): the completed catalog makes `policy show closure` resolvable."""
    workspace = _init_states(tmp_path)
    monkeypatch.chdir(workspace)
    result = _runner.invoke(app, ["lifecycle", "workflow", "policy", "show", "closure", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["workflow_id"] == "closure"
    steps = {s["step"]: s for s in payload["steps"]}
    assert "close" in steps, "closure's real close worker step is not in the resolved policy"
    # The generic close step resolves a governed model profile on the default harness.
    assert steps["close"]["model_profile"]
    assert steps["close"]["harness"] in {"codex", "pi"}


@pytest.mark.parametrize("name", ["audit", "research", "bug_report"])
def test_workflow_policy_show_deferred_rejected(name: str, tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """A deferred workflow has no governed steps — `policy show` rejects it actionably."""
    workspace = _init_states(tmp_path)
    monkeypatch.chdir(workspace)
    result = _runner.invoke(app, ["lifecycle", "workflow", "policy", "show", name])
    assert result.exit_code != 0
    assert "unknown workflow" in _norm(result.output)


# ---------------------------------------------------------------------------
# workflow doctor (T-28-D-02 — WMP-* governance invariants)
# ---------------------------------------------------------------------------


def test_workflow_doctor_clean_tree_passes(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    workspace = _init_states(tmp_path)
    monkeypatch.chdir(workspace)
    result = _runner.invoke(app, ["lifecycle", "workflow", "doctor", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    errors = [f for f in payload["findings"] if f["severity"] == "error"]
    assert errors == [], errors


def test_workflow_doctor_invalid_overlay_fails_actionably(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    workspace = _init_states(tmp_path)
    monkeypatch.chdir(workspace)
    overlay = workspace / ".dadaia" / "states" / "workflow_model_policy.json"
    overlay.write_text("{ not valid json", encoding="utf-8")
    result = _runner.invoke(app, ["lifecycle", "workflow", "doctor", "--json"])
    # Invalid state file is an ERROR → exit non-zero, but never a crash (clean JSON out).
    assert result.exit_code != 0, result.output
    payload = json.loads(result.output)
    codes = {f["code"] for f in payload["findings"]}
    assert "WMP-STATE" in codes


def test_workflow_doctor_bad_overlay_override_fails(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    workspace = _init_states(tmp_path)
    monkeypatch.chdir(workspace)
    overlay = workspace / ".dadaia" / "states" / "workflow_model_policy.json"
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
    result = _runner.invoke(app, ["lifecycle", "workflow", "doctor", "--json"])
    assert result.exit_code != 0, result.output
    payload = json.loads(result.output)
    assert "WMP-OVERLAY" in {f["code"] for f in payload["findings"]}


# ---------------------------------------------------------------------------
# pipeline --step-model (D-3: profile ids only) + --show-policy
# ---------------------------------------------------------------------------


def test_pipeline_show_policy_json(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    workspace = _init_states(tmp_path)
    monkeypatch.chdir(workspace)
    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "pipeline",
            "--release-id",
            "v0.1.28",
            "--harness",
            "fake",
            "--step-model",
            "implement=codex-review-deep",
            "--show-policy",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    steps = {s["step"]: s for s in payload["steps"]}
    assert steps["implement"]["model_profile"] == "codex-review-deep"
    assert steps["implement"]["source"] == "cli"


def test_pipeline_harness_pi_show_policy_resolves_pi(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    # v0.1.29 / T-29-A-07 — --harness pi threads into the governed resolver: every step's
    # snapshot resolves harness=pi with the PI default profile auto-selected.
    workspace = _init_states(tmp_path)
    monkeypatch.chdir(workspace)
    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "pipeline",
            "--release-id",
            "v0.1.29",
            "--harness",
            "pi",
            "--show-policy",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    steps = {s["step"]: s for s in payload["steps"]}
    assert steps["implement"]["harness"] == "pi"
    assert steps["implement"]["model_profile"] == "pi-implementation-standard"
    assert steps["review_qa"]["harness"] == "pi"
    assert steps["review_qa"]["model_profile"] == "pi-reasoning-high"


def test_pipeline_harness_pi_with_codex_step_model_rejected(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    # --harness pi + a codex --step-model is a clean rejection (effective-harness conflict).
    workspace = _init_states(tmp_path)
    monkeypatch.chdir(workspace)
    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "pipeline",
            "--release-id",
            "v0.1.29",
            "--harness",
            "pi",
            "--step-model",
            "implement=codex-implementation-standard",
            "--show-policy",
        ],
    )
    assert result.exit_code != 0
    text = _norm(result.output).lower()
    assert "harness" in text
    assert "pi" in text


def test_pipeline_step_harness_pi_only_that_step(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    workspace = _init_states(tmp_path)
    monkeypatch.chdir(workspace)
    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "pipeline",
            "--release-id",
            "v0.1.29",
            "--step-harness",
            "implement=pi",
            "--show-policy",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    steps = {s["step"]: s for s in json.loads(result.output)["steps"]}
    assert steps["implement"]["harness"] == "pi"
    assert steps["review_qa"]["harness"] == "codex"


def test_pipeline_step_model_rejects_raw_model_string(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    workspace = _init_states(tmp_path)
    monkeypatch.chdir(workspace)
    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "pipeline",
            "--release-id",
            "v0.1.28",
            "--step-model",
            "implement=gpt-5.5:high",  # raw <id>:<effort> — must be rejected (D-3)
            "--show-policy",
        ],
    )
    assert result.exit_code != 0
    text = _norm(result.output)
    assert "profile id" in text
    assert "not a raw model string" in text


def test_pipeline_step_model_rejects_unknown_profile(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    workspace = _init_states(tmp_path)
    monkeypatch.chdir(workspace)
    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "pipeline",
            "--release-id",
            "v0.1.28",
            "--step-model",
            "implement=no-such-profile",
            "--show-policy",
        ],
    )
    assert result.exit_code != 0
    assert "unknown model profile" in _norm(result.output)


def test_pipeline_step_model_rejects_harness_mismatch(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    workspace = _init_states(tmp_path)
    monkeypatch.chdir(workspace)
    # implement resolves to codex; a pi profile mismatches the step harness.
    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "pipeline",
            "--release-id",
            "v0.1.28",
            "--step-model",
            "implement=pi-reasoning-high",
            "--show-policy",
        ],
    )
    assert result.exit_code != 0
    assert "harness" in _norm(result.output).lower()


# ---------------------------------------------------------------------------
# LAW 1 — claude / opencode rejected as Layer-2 harnesses
# ---------------------------------------------------------------------------


def test_pipeline_rejects_claude_harness(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    workspace = _init_states(tmp_path)
    monkeypatch.chdir(workspace)
    result = _runner.invoke(
        app,
        ["lifecycle", "pipeline", "--release-id", "v0.1.28", "--harness", "claude"],
    )
    assert result.exit_code != 0
    text = _norm(result.output)
    assert "not a Layer-2 workflow harness" in text


def test_pipeline_rejects_opencode_harness(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    workspace = _init_states(tmp_path)
    monkeypatch.chdir(workspace)
    result = _runner.invoke(
        app,
        ["lifecycle", "pipeline", "--release-id", "v0.1.28", "--harness", "opencode"],
    )
    assert result.exit_code != 0
    text = _norm(result.output)
    assert "not a Layer-2 workflow harness" in text
