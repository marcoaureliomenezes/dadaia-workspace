"""``secret-scan.yml`` gitflow-trigger contract (v0.5.1 T-051-19).

Regression seam for
``secret-scan-workflow-never-runs-on-develop-prs-so-its-required-context-blocks-every-merge``:
branch protection requires the ``gitleaks`` job's context on every PR edge (DADAIA.md
Sec 4 — both PR edges gated the same way), but the workflow used to trigger only on
``pull_request`` to ``main`` — so a ``feature/{M.m.p}`` -> ``develop`` PR never produced
the context and the merge stayed BLOCKED with every other check green. Pins the fix the
same way ``test_ci_v2_gitflow_pr_gate.py`` pins ``ci.yml``'s own v2 triggers: assert the
YAML content directly, since executing the workflow is impractical in a unit test.

Intent: CONTRACT — v0.5.1 A-12.1, A-12.2 (T-051-19)
Owner: software-engineer
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
import yaml

pytestmark = pytest.mark.contract

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SECRET_SCAN_YML = _REPO_ROOT / ".github" / "workflows" / "secret-scan.yml"


def _load_workflow() -> dict[Any, Any]:
    # PyYAML's default (YAML 1.1) resolver reads the unquoted `on:` key as the boolean
    # True, not the string "on" — the top-level key set is not str-only, so this is
    # typed dict[Any, Any] rather than dict[str, Any] (same quirk as
    # test_ci_v2_gitflow_pr_gate.py::_load_workflow).
    return cast("dict[Any, Any]", yaml.safe_load(_SECRET_SCAN_YML.read_text(encoding="utf-8")))


def test_gitleaks_job_name_matches_the_required_branch_protection_context() -> None:
    """The required context branch protection lists is the literal job id/name
    ``gitleaks`` — the workflow must keep producing exactly that on every gated edge."""
    workflow = _load_workflow()
    jobs = workflow["jobs"]
    assert "gitleaks" in jobs
    assert jobs["gitleaks"]["name"] == "gitleaks"


def test_pull_request_trigger_covers_both_develop_and_main_edges() -> None:
    """A-12.1/A-12.2: the required context must report on a feature -> develop PR, not
    only feature -> main — both PR edges DADAIA.md Sec 4 gates the same way."""
    workflow = _load_workflow()
    on = workflow[True]
    assert on["pull_request"]["branches"] == ["main", "develop"]


def test_push_trigger_is_main_only_and_the_retired_hotfix_pattern_is_gone() -> None:
    """``hotfix/*`` was retired outright (DADAIA.md Sec 4 / G2) — its push trigger must
    not linger in a workflow that never got the memo."""
    workflow = _load_workflow()
    on = workflow[True]
    assert on["push"]["branches"] == ["main"]
    text = _SECRET_SCAN_YML.read_text(encoding="utf-8")
    assert "hotfix" not in text


def test_secret_scan_workflow_yaml_is_well_formed() -> None:
    workflow = _load_workflow()
    assert isinstance(workflow, dict)
    assert "jobs" in workflow
