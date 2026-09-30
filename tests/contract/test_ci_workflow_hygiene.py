"""The GitHub workflows: what every job may never do, how release.yml publishes, and the gitflow
the triggers and the PR source guard encode.

Intent: CONTRACT — bugs release-publishes-an-unordered-dadaia-skills-repository,
release-workflow-coverage-file-in-checkout, pr-source-guard-refuses-the-release-please-pr-to-main,
dependabot-targets-main-and-every-update-pr-is-refused, ci-history-depth-is-decided-per-job,
secret-scan-workflow-never-runs-on-develop-prs-so-its-required-context-blocks-every-merge
(v0.5.1 A-12.1, A-12.2); T-047-87/88 (release.yml mints and publishes behind one gate); ADR 0026;
sa-doctor-job-not-a-required-check (AC1.7, ADR 0078). Size: SMALL (YAML reads; the guard runs bash).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml

from dadaia_workspace.core.gitflow import read_gitflow

pytestmark = pytest.mark.contract

_WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"
_RELEASE_YML = _WORKFLOWS / "release.yml"
_REPO_ROOT = _WORKFLOWS.parents[1]
_ACTION = "googleapis/release-please-action"
_GATE = "needs.release-please.outputs.release_created == 'true'"


def _load(name: str) -> Any:
    return yaml.safe_load((_WORKFLOWS / name).read_text(encoding="utf-8"))


def _workflows() -> dict[str, Any]:
    return {
        p.name: _load(p.name)
        for p in sorted([*_WORKFLOWS.glob("*.yml"), *_WORKFLOWS.glob("*.yaml")])
    }


def _on(document: Any) -> Any:
    """PyYAML (YAML 1.1) reads the bare `on:` key as the boolean True."""
    return document.get("on", document.get(True)) or {}


def _jobs() -> dict[str, Any]:
    return dict(_load("release.yml")["jobs"])


def _needs(job: dict[str, Any]) -> list[str]:
    needs = job.get("needs") or []
    return [needs] if isinstance(needs, str) else list(needs)


def _steps() -> list[tuple[str, str, dict[str, Any]]]:
    return [
        (name, job_name, step)
        for name, doc in _workflows().items()
        for job_name, job in (doc.get("jobs") or {}).items()
        if isinstance(job, dict)
        for step in job.get("steps") or []
    ]


def _skills_repo_mentions() -> list[str]:
    """Grill Q14: no standalone skills repository was ordered (delete this row when it is)."""
    rx = re.compile(
        r"dadaia-skills|SKILLS_REPO_TOKEN|build-skills-repo|npx skills add|skills-repository"
    )
    surfaces = [
        *sorted(_WORKFLOWS.glob("*.yml")),
        _REPO_ROOT / "README.md",
        _REPO_ROOT / "llms.txt",
        *sorted((_REPO_ROOT / "docs").rglob("*.md")),
        *sorted((_REPO_ROOT / "specs" / "memory").rglob("*.md")),
    ]
    hits = [
        f"{p.relative_to(_REPO_ROOT)}:{n}"
        for p in surfaces
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
        if rx.search(line)
    ]
    return hits + [
        p
        for p in ["dadaia_workspace/public/scripts/build-skills-repo.py"]
        if (_REPO_ROOT / p).exists()
    ]


def _model_api_calls() -> list[str]:
    """P-33 (ADR 0025): no `anthropics/*` action, model API secret or endpoint in any workflow."""
    rx = re.compile(r"CLAUDE_API_KEY|ANTHROPIC_(?:API_)?KEY|api\.anthropic\.com", re.IGNORECASE)
    hits = []
    for name, doc in _workflows().items():
        jobs = [j for j in ((doc or {}).get("jobs") or {}).values() if isinstance(j, dict)]
        uses = [str(j.get("uses", "")) for j in jobs] + [
            str(s["uses"])
            for j in jobs
            for s in j.get("steps") or []
            if isinstance(s, dict) and "uses" in s
        ]
        hits += [f"{name}: uses {u}" for u in uses if u.lower().startswith("anthropics/")]
        text = (_WORKFLOWS / name).read_text(encoding="utf-8")
        hits += [f"{name}:{n}" for n, line in enumerate(text.splitlines(), 1) if rx.search(line)]
    return hits


def _uncovered_coverage_files() -> list[str]:
    """release-workflow-coverage-file-in-checkout: a `pytest --cov` step writes COVERAGE_FILE
    under runner.temp (step or job env), never `.coverage` in the checkout."""
    return [
        f"{name}:{job_name}"
        for name, doc in _workflows().items()
        for job_name, job in (doc.get("jobs") or {}).items()
        for step in job.get("steps") or []
        if "pytest" in (run := step.get("run") or "")
        and "--cov" in run
        and "runner.temp"
        not in str(
            (step.get("env") or {}).get("COVERAGE_FILE")
            or (job.get("env") or {}).get("COVERAGE_FILE")
        )
    ]


_NEVER: dict[str, Callable[[], list[str]]] = {
    "skills-repository-published": _skills_repo_mentions,
    # the template-injection shape: every value reaches a run body through env:
    "workflow-expression-in-a-run-body": lambda: [
        f"{n}/{j}/{s.get('name')}: {line.strip()}"
        for n, j, s in _steps()
        for line in (s.get("run") or "").splitlines()
        if "${{" in line
    ],
    "model-api-call": _model_api_calls,
    "coverage-file-in-the-checkout": _uncovered_coverage_files,
    "release-please-outside-release-yml": lambda: [
        n
        for n in _workflows()
        if _ACTION in (_WORKFLOWS / n).read_text(encoding="utf-8") and n != "release.yml"
    ],
    "pypi-publisher-outside-release-yml": lambda: [
        n
        for n in _workflows()
        if "pypa/gh-action-pypi-publish" in (_WORKFLOWS / n).read_text(encoding="utf-8")
        and n != "release.yml"
    ],
    # same-workflow chaining only: a second trigger would need a PAT (PLAN D8)
    "release-event-or-tag-push-trigger": lambda: [
        n
        for n, doc in _workflows().items()
        if "release" in (t := _on(doc))
        or (isinstance(t, dict) and bool({"tags", "tags-ignore"} & set(t.get("push") or {})))
    ],
    "publishing-job-without-the-release-gate": lambda: [
        n
        for n, job in _jobs().items()
        if n != "release-please"
        and ("release-please" not in _needs(job) or str(job.get("if") or "").strip() != _GATE)
    ],
    "needs-an-undefined-job": lambda: [
        f"{n} -> {d}" for n, job in _jobs().items() for d in _needs(job) if d not in _jobs()
    ],
    # T-047-88: the action mints the tag, never workflow arithmetic
    "hand-computed-tag": lambda: [
        f"{j}: {line.strip()}"
        for n, j, s in _steps()
        if n == "release.yml"
        for line in (s.get("run") or "").splitlines()
        if "git ls-remote --tags" in line or "git tag " in line
    ],
}


@pytest.mark.parametrize("rule", list(_NEVER))
def test_no_workflow_breaks_the_rule(rule: str) -> None:
    offenders = _NEVER[rule]()
    assert offenders == [], f"{rule}: {offenders}"


def test_release_please_mints_on_main_only_pinned_and_config_driven() -> None:
    """T-047-87: push-to-main trigger (and manual dispatch), a main-only job whatever ref
    dispatched it, contents/pull-requests write only, a sha-pinned action with its `# vX.Y.Z`
    comment, and the release type read from the config file (a `release-type` input leaves
    manifest mode); the step id exposes release_created/tag_name."""
    doc = _load("release.yml")
    assert _on(doc)["push"]["branches"] == ["main"] and "workflow_dispatch" in _on(doc)
    assert doc["permissions"] == {"contents": "write", "pull-requests": "write"}
    assert (
        str(_jobs()["release-please"].get("if") or "").strip() == "github.ref == 'refs/heads/main'"
    )
    (uses,) = [
        ln
        for ln in _RELEASE_YML.read_text(encoding="utf-8").splitlines()
        if _ACTION in ln and "uses:" in ln
    ]
    ref, _, comment = uses.partition("#")
    assert re.match(r"^[0-9a-f]{40}$", ref.split("@", 1)[1].strip()) and re.match(
        r"^\s*v\d+\.\d+\.\d+\s*$", comment
    )
    (step,) = [s for _, _, s in _steps() if _ACTION in str(s.get("uses") or "")]
    inputs = step.get("with") or {}
    assert "release-type" not in inputs and step.get("id") == "release-please"
    assert inputs["config-file"] == "release-please-config.json"
    assert inputs["manifest-file"] == ".release-please-manifest.json"


def test_the_publish_chain_is_one_gated_path() -> None:
    """ADR 0026: publish runs under environment `pypi` with id-token write (the trusted publisher
    binds the file name); approval keeps `release-gate`; one `id: version` step strips the tag's
    `v` for approve/publish/smoke-test; a dispatch with `tag` republishes an existing tag by
    checking it out; the build waits for ci.yml itself and no job redeclares pytest
    (sa-doctor-job-not-a-required-check#B2)."""
    jobs = _jobs()
    assert (
        jobs["publish"]["environment"] == "pypi"
        and jobs["publish"]["permissions"]["id-token"] == "write"
    )
    assert jobs["approve"].get("environment") == "release-gate"
    build = jobs["build"]
    assert build.get("outputs", {}).get("version") == "${{ steps.version.outputs.version }}"
    step = next(s for s in build["steps"] if s.get("id") == "version")
    assert step["env"] == {"TAG": "${{ needs.release-please.outputs.tag_name }}"}
    assert 'echo "version=${TAG#v}" >> "$GITHUB_OUTPUT"' in step["run"]
    assert {n for n, j in jobs.items() if "needs.build.outputs.version" in yaml.safe_dump(j)} == {
        "approve",
        "publish",
        "smoke-test",
    }
    assert "tag" in _on(_load("release.yml"))["workflow_dispatch"]["inputs"]
    existing = [s for s in jobs["release-please"]["steps"] if s.get("id") == "existing"]
    assert existing and "inputs.tag" in existing[0]["if"]
    assert build["steps"][0]["with"]["ref"] == "${{ needs.release-please.outputs.tag_name }}"
    assert jobs["ci"]["uses"] == "./.github/workflows/ci.yml" and "ci" in build["needs"]
    assert not any("pytest" in yaml.safe_dump(job) for job in jobs.values())


def _step_texts(workflow: str, job: str) -> str:
    return "\n".join(
        f"{s.get('run', '')}\n{s.get('env', '')}" for s in _load(workflow)["jobs"][job]["steps"]
    )


def test_the_onboarding_journey_runs_with_uv_and_the_smoke_walks_greenfield() -> None:
    """Intent: CONTRACT — 0.4.8 AC8.3 (T-048-11): the e2e job installs uv, requires uvx (absent
    uvx fails, never skips) and selects the journey; the post-publish smoke runs the published
    version through `init --repo` + `specs init` + `doctor`."""
    e2e = _step_texts("ci.yml", "e2e-python")
    assert "install uv==" in e2e and "'DADAIA_REQUIRE_UVX': '1'" in e2e, e2e
    assert re.search(r"tests/e2e(?:\s|$|/test_onboarding_journey\.py)", e2e), e2e
    smoke = _step_texts("release.yml", "smoke-test")
    for needle in (
        'uvx "dadaia-workspace==$VERSION" init',
        "--repo",
        "specs init --context",
        "doctor --context",
    ):
        assert needle in smoke, needle


def test_the_ci_triggers_are_the_library_gitflow() -> None:
    """T-050-19 AC6.9: GitHub reads no file, so the literal triggers are pinned to the library
    constitution's gitflow. secret-scan's required `gitleaks` context reports on both PR edges
    (A-12.1/A-12.2), pushes only to the principal, and the retired `hotfix/*` is gone; every
    Dependabot update targets the integration branch (dependabot-targets-main-...)."""
    flow, warning = read_gitflow(_REPO_ROOT / "specs")
    assert warning is None
    ci, release, scan = _on(_load("ci.yml")), _on(_load("release.yml")), _load("secret-scan.yml")
    assert ci["push"]["branches"] == [flow.principal, flow.integration, f"{flow.work_prefix}**"]
    assert ci["pull_request"]["branches"] == [flow.principal, flow.integration]
    assert release["push"]["branches"] == [flow.principal]
    assert _on(scan)["pull_request"]["branches"] == [flow.principal, flow.integration]
    assert _on(scan)["push"]["branches"] == [flow.principal]
    assert scan["jobs"]["gitleaks"]["name"] == "gitleaks"
    assert "hotfix" not in (_WORKFLOWS / "secret-scan.yml").read_text(encoding="utf-8")
    bot = yaml.safe_load((_WORKFLOWS.parent / "dependabot.yml").read_text(encoding="utf-8"))
    assert bot["updates"] and {u.get("target-branch") for u in bot["updates"]} == {
        flow.integration
    } == {"develop"}


def _guard_exit(head: str, base: str, cwd: Path) -> int:
    """pr-source-guard's step exactly as CI runs it, reading the constitution under *cwd*."""
    step = next(
        s
        for s in _load("ci.yml")["jobs"]["pr-source-guard"]["steps"]
        if "HEAD_REF" in s.get("env", {})
    )
    env = {"HEAD_REF": head, "BASE_REF": base, "PATH": os.pathsep.join([str(Path(sys.executable).parent), os.environ["PATH"]]),
           "PYTHONPATH": str(_REPO_ROOT), "BASE_SPECS": str(cwd / "specs")}  # fmt: skip
    return subprocess.run(
        ["bash", "-c", step["run"]], env=env, cwd=cwd, capture_output=True
    ).returncode


_RENAMED = "gitflow: {principal: trunk, integration: next, work: work/}\n"


@pytest.mark.skipif(sys.platform == "win32", reason="the guard is a bash step on ubuntu-latest")
@pytest.mark.parametrize(
    ("gitflow", "head", "base", "allowed"),
    [
        # ADR 0021: main takes develop and release-please's own branch; develop takes feature/ and Dependabot
        ("repo", "develop", "main", True),
        ("repo", "release-please--branches--main", "main", True),
        ("repo", "feature/0.4.7", "main", False),
        ("repo", "release-please--branches--develop", "main", False),
        ("repo", "feature/0.4.7", "develop", True),
        ("repo", "develop", "develop", False),
        ("repo", "dependabot/pip/ruff-0.16.8", "develop", True),
        ("repo", "dependabot/github_actions/actions/checkout-7.1.0", "develop", True),
        ("repo", "dependabot/pip/ruff-0.16.8", "main", False),
        # T-050-19 AC6.8: the guard names no branch; a renamed gitflow moves its rules
        ("renamed", "next", "trunk", True),
        ("renamed", "develop", "trunk", False),
        ("renamed", "work/1.2.3", "next", True),
        ("renamed", "feature/1.2.3", "next", False),
        # a base with no constitution reads the default gitflow
        ("absent", "develop", "main", True),
        ("absent", "feature/0.5.0", "main", False),
    ],
)
def test_pr_source_guard_admits_the_release_pr_into_main(
    tmp_path: Path, gitflow: str, head: str, base: str, allowed: bool
) -> None:
    cwd = _REPO_ROOT
    if gitflow != "repo":
        cwd = tmp_path
        (tmp_path / "specs").mkdir()
        if gitflow == "renamed":
            (tmp_path / "specs" / "constitution.md").write_text(
                f"---\nspecs_pattern_version: 6\n{_RENAMED}---\n# C\n", encoding="utf-8"
            )
    assert (_guard_exit(head, base, cwd) == 0) is allowed


def test_every_ci_checkout_carries_full_history() -> None:
    """ci-history-depth-is-decided-per-job: all 13 ci.yml checkouts fetch depth 0, so no job
    edit strips the history a suite reads."""
    depths = [
        (name, (s.get("with") or {}).get("fetch-depth"))
        for name, job in _load("ci.yml")["jobs"].items()
        for s in job.get("steps", [])
        if str(s.get("uses", "")).startswith("actions/checkout@")
    ]
    assert len(depths) == 13
    assert [name for name, depth in depths if depth != 0] == []


def test_the_required_checks_file_lists_every_check_a_pr_runs() -> None:
    """sa-doctor-job-not-a-required-check#B1: a PR check absent from the file is
    red-but-mergeable; a stale entry blocks every merge."""
    contexts: set[str] = set()
    for doc in _workflows().values():
        if "pull_request" not in _on(doc):
            continue
        for job in doc["jobs"].values():
            matrix = ((job.get("strategy") or {}).get("matrix") or {}).get("os")
            contexts |= {f"{job['name']} ({v})" for v in matrix} if matrix else {job["name"]}
    required = json.loads((_WORKFLOWS.parent / "required-checks.json").read_text("utf-8"))
    assert "Compliance (workspace/specs/ledgers sections)" in required
    assert sorted(required) == sorted(contexts)
