"""CI v2 gitflow trigger + PR-gate contract (v0.4.4 FR4, T-044-07).

Workflow YAML behaviour is impractical to execute in a unit test, so this pins its
CONTENT: the v2 triggers (A4.1), the single pr-source-guard job's two rules (A4.2),
the security-verdict-gate job's shape and its A4.4 recorded-limit comment, and a
regression guard proving the push-time verdict reader never came back (A4.5). A4.3
(the gate's real pass/fail behaviour) is proven for real, against a disposable git
repo, by tests/integration/scripts/test_pr_verdict_check_wiring.py — that script is
this job's backend, kept out of the YAML on purpose.

Intent: CONTRACT — v0.4.4 A4.1, A4.2, A4.4, A4.5 (T-044-07)
Owner: software-engineer
"""

from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

pytestmark = pytest.mark.contract

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CI_YML = _REPO_ROOT / ".github" / "workflows" / "ci.yml"
_SCRIPT = _REPO_ROOT / ".github" / "scripts" / "pr-verdict-check.sh"
_CHOKEPOINTS_SERVICE = _REPO_ROOT / "dadaia_workspace" / "features" / "chokepoints" / "service.py"


def _load_workflow() -> dict[Any, Any]:
    # PyYAML's default (YAML 1.1) resolver reads the unquoted `on:` key as the
    # boolean True, not the string "on" — the top-level key set is not str-only, so
    # this is typed dict[Any, Any] rather than dict[str, Any].
    return cast("dict[Any, Any]", yaml.safe_load(_CI_YML.read_text(encoding="utf-8")))


def _jobs() -> dict[str, Any]:
    return cast("dict[str, Any]", _load_workflow()["jobs"])


def test_a4_1_push_and_pull_request_triggers_extended() -> None:
    workflow = _load_workflow()
    # PyYAML's default (YAML 1.1) resolver reads the unquoted `on:` key as the boolean
    # True, not the string "on" — a documented GitHub Actions/PyYAML interop quirk,
    # not a bug in ci.yml.
    on = workflow[True]
    assert on["push"]["branches"] == ["main", "develop", "feature/**"]
    assert on["pull_request"]["branches"] == ["main", "develop"]


def test_a4_2_pr_source_guard_is_one_job_covering_both_edges() -> None:
    jobs = _jobs()
    assert "pr-source-guard" in jobs
    guard = jobs["pr-source-guard"]

    condition = guard["if"]
    assert "pull_request" in condition
    assert "'main'" in condition
    assert "'develop'" in condition

    steps_text = "\n".join(step.get("run", "") for step in guard["steps"])
    assert '"$BASE_REF" = "main"' in steps_text
    assert '"$BASE_REF" = "develop"' in steps_text
    assert '"$HEAD_REF" != "develop"' in steps_text
    # Derived from the SAME pattern as features/chokepoints/service.py::_FEATURE_RE
    # (r"^feature/\d+\.\d+\.\d+$"), not a second, drifted regex literal (A3.2).
    assert "feature/[0-9]+\\.[0-9]+\\.[0-9]+" in steps_text
    assert "chokepoints/service.py" in steps_text
    assert "_FEATURE_RE" in steps_text
    # Exactly one job carries the source-guard logic — no second job for the
    # develop edge.
    assert sum(1 for name in jobs if "source-guard" in name) == 1


def test_a4_4_recorded_limit_is_documented_above_the_job() -> None:
    text = _CI_YML.read_text(encoding="utf-8")
    idx = text.find("security-verdict-gate:")
    assert idx != -1, "security-verdict-gate job is missing"
    preamble = text[:idx][-3000:]
    assert "rc-1" in preamble
    assert "rc-2" in preamble
    assert "advisory" in preamble.lower()
    assert "required_status_checks" in preamble
    assert "clobber" in preamble.lower()


def test_security_verdict_gate_job_shape() -> None:
    jobs = _jobs()
    assert "security-verdict-gate" in jobs
    job = jobs["security-verdict-gate"]

    condition = job["if"]
    assert "pull_request" in condition
    assert "'develop'" in condition
    assert "'main'" in condition

    steps = job["steps"]
    checkout_steps = [step for step in steps if "checkout" in step.get("uses", "")]
    assert len(checkout_steps) == 1
    checkout = checkout_steps[0]
    with_block = checkout.get("with", {})
    assert with_block.get("fetch-depth") == 0
    assert "head.sha" in str(with_block.get("ref", ""))

    run_text = "\n".join(step.get("run", "") for step in steps)
    assert "pr-verdict-check.sh" in run_text

    env_text = "\n".join(str(step.get("env", {})) for step in steps)
    assert "PR_HEAD_SHA" in env_text
    assert "head.sha" in env_text


def test_a4_5_push_gate_decision_never_calls_the_verdict_reader() -> None:
    text = _CHOKEPOINTS_SERVICE.read_text(encoding="utf-8")
    start = text.index("def push_gate_decision")
    rest = text[start + 1 :]
    end = start + 1 + rest.index("\ndef ") if "\ndef " in rest else len(text)
    body = text[start:end]
    assert "iter_security_approvals" not in body, (
        "the push-time path must never read a security-verdict handoff — that check "
        "relocated to the CI PR gate (A3.4/A4.5)"
    )


def test_ci_workflow_yaml_is_well_formed() -> None:
    # A trivial but real guard: yaml.safe_load already ran (via _load_workflow) for
    # every test above; this asserts the top-level shape explicitly so a malformed
    # edit fails here first, with a direct message, rather than obscurely elsewhere.
    workflow = _load_workflow()
    assert isinstance(workflow, dict)
    assert "jobs" in workflow


def test_pr_verdict_check_script_exists_and_is_executable() -> None:
    assert _SCRIPT.is_file(), f"expected {_SCRIPT}"
    if os.name != "nt":
        mode = _SCRIPT.stat().st_mode
        assert mode & stat.S_IXUSR, f"{_SCRIPT} is not executable"
