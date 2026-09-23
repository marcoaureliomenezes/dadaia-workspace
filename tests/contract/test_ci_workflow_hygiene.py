"""Intent: CONTRACT — T-047-82: the release workflow publishes the built skills
repository and fails closed on the missing SKILLS_REPO_TOKEN secret, with the token
never interpolated outside the push remote URL.

Intent: CONTRACT — T-047-87: release-please.yml is the one workflow minting the
version, CHANGELOG and tag: push-to-main trigger, sha-pinned action, release type
read from the config file rather than an input.

Intent: CONTRACT — T-047-88: release.yml is gone and its publishing jobs live inside
release-please.yml behind the single `release_created` gate: no `release:` event, no
`push: tags`, no hand-rolled tag arithmetic. Size: SMALL."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.contract

_WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"
_RELEASE_YML = _WORKFLOWS / "release-please.yml"
_TOKEN = "SKILLS_REPO_TOKEN"
_REMOTE_PREFIX = "https://x-access-token:"


def _workflows() -> dict[str, Any]:
    return {
        path.name: yaml.safe_load(path.read_text(encoding="utf-8"))
        for path in sorted(_WORKFLOWS.glob("*.yml"))
    }


def _jobs() -> dict[str, Any]:
    return dict(yaml.safe_load(_RELEASE_YML.read_text(encoding="utf-8"))["jobs"])


def _skills_job() -> tuple[str, dict[str, Any]]:
    candidates = [
        (name, job)
        for name, job in _jobs().items()
        if any("build-skills-repo.py" in (step.get("run") or "") for step in job.get("steps") or [])
    ]
    assert len(candidates) == 1, (
        f"expected exactly one release job building the skills repository, got {[n for n, _ in candidates]}"
    )
    return candidates[0]


def test_skills_repo_job_runs_after_publish_and_builds_the_repository() -> None:
    name, job = _skills_job()
    needs = job.get("needs") or []
    needs = [needs] if isinstance(needs, str) else list(needs)
    assert "publish" in needs, f"job {name} must depend on the publish job, needs={needs}"
    build = next(s for s in job["steps"] if "build-skills-repo.py" in (s.get("run") or ""))
    assert "dadaia_workspace/public/scripts/build-skills-repo.py" in build["run"]
    assert job.get("permissions") == {"contents": "read"}, (
        f"job {name} must declare minimal permissions; got {job.get('permissions')}"
    )


def test_missing_skills_repo_token_fails_closed_with_one_error_annotation() -> None:
    name, job = _skills_job()
    assert (job.get("env") or {}).get(_TOKEN) == "${{ secrets." + _TOKEN + " }}"
    guards = [s for s in job["steps"] if f"env.{_TOKEN} == ''" in str(s.get("if") or "")]
    assert len(guards) == 1, (
        f"job {name} must carry exactly one fail-closed guard, got {len(guards)}"
    )
    run = guards[0]["run"]
    assert run.count("::error::") == 1, f"the guard must emit exactly one annotation: {run!r}"
    assert _TOKEN in run and "exit 1" in run


def test_the_token_is_interpolated_only_in_the_push_remote_url() -> None:
    offenders: list[str] = []
    for job_name, job in _jobs().items():
        for step in job.get("steps") or []:
            for line in (step.get("run") or "").splitlines():
                if _TOKEN not in line:
                    continue
                guard = f"env.{_TOKEN} == ''" in str(step.get("if") or "")
                if guard or f"{_REMOTE_PREFIX}${{{_TOKEN}}}" in line:
                    continue
                offenders.append(f"{job_name}: {line.strip()}")
    assert offenders == [], (
        f"{_TOKEN} may appear only inside the {_REMOTE_PREFIX} remote URL or the "
        f"fail-closed guard — never echoed or logged: {offenders}"
    )


def _run_bodies() -> list[tuple[str, str, str | None, str]]:
    """Every `run:` body in every workflow, as (workflow, job, step name, line)."""
    return [
        (name, job_name, step.get("name"), line)
        for name, document in _workflows().items()
        for job_name, job in (document.get("jobs") or {}).items()
        for step in job.get("steps") or []
        for line in (step.get("run") or "").splitlines()
    ]


@pytest.mark.parametrize("workflow", sorted(p.name for p in _WORKFLOWS.glob("*.yml")))
def test_no_run_body_of_any_workflow_interpolates_a_workflow_expression(workflow: str) -> None:
    """A workflow expression pasted into a shell body is the template-injection shape:
    the expression is substituted before the shell parses the line, so attacker-authored
    text becomes code. Every value reaches a run body through `env:` and is read as a
    quoted shell variable — in EVERY job of EVERY workflow, not just the ones that were
    reviewed."""
    offenders = [
        f"{job}/{step or '<unnamed>'}: {line.strip()}"
        for name, job, step, line in _run_bodies()
        if name == workflow and "${{" in line
    ]
    assert offenders == [], (
        f"{workflow} must pass every workflow expression through env:, never a run "
        f"body: {offenders}"
    )


# ---------------------------------------------------------------------------
# release-please.yml — the one workflow that mints the version, CHANGELOG and tag
# ---------------------------------------------------------------------------

_RELEASE_PLEASE_YML = _RELEASE_YML
_ACTION = "googleapis/release-please-action"
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def _release_please_step() -> dict[str, Any]:
    """The single step invoking the release-please action, with its `uses:` comment."""
    document = yaml.safe_load(_RELEASE_PLEASE_YML.read_text(encoding="utf-8"))
    steps = [
        step
        for job in document["jobs"].values()
        for step in job.get("steps") or []
        if _ACTION in str(step.get("uses") or "")
    ]
    assert len(steps) == 1, f"expected exactly one release-please step, got {len(steps)}"
    return dict(steps[0])


def test_release_please_workflow_runs_on_a_push_to_main() -> None:
    document = yaml.safe_load(_RELEASE_PLEASE_YML.read_text(encoding="utf-8"))
    # PyYAML reads the bare `on:` key as the boolean True (the YAML 1.1 truthy set).
    triggers = document.get("on", document.get(True))
    assert triggers["push"]["branches"] == ["main"], (
        f"the release workflow triggers on a push to main alone: {triggers}"
    )
    assert "workflow_dispatch" in triggers, "the workflow stays manually runnable"
    assert document["permissions"] == {"contents": "write", "pull-requests": "write"}, (
        "release-please writes the release PR and the tag — and nothing wider"
    )


def test_the_release_please_job_runs_only_on_main() -> None:
    """`workflow_dispatch` accepts any ref: without this guard a run started off a
    feature branch would let the action read that history and mint a version from it."""
    job = _jobs()["release-please"]
    assert str(job.get("if") or "").strip() == "github.ref == 'refs/heads/main'", (
        f"the version-minting job is main-only whatever ref dispatched it: {job.get('if')!r}"
    )


def test_release_please_action_is_sha_pinned_with_its_version_comment() -> None:
    """A mutable tag on a release-minting action is a supply-chain hole; the trailing
    `# v<x.y.z>` comment is what makes the pin auditable by a human."""
    raw = _RELEASE_PLEASE_YML.read_text(encoding="utf-8")
    uses_lines = [line for line in raw.splitlines() if _ACTION in line and "uses:" in line]
    assert len(uses_lines) == 1, uses_lines
    ref, _, comment = uses_lines[0].partition("#")
    sha = ref.split("@", 1)[1].strip()
    assert _SHA_RE.match(sha), f"the action must be pinned to a 40-hex commit sha: {sha!r}"
    assert re.match(r"^\s*v\d+\.\d+\.\d+\s*$", comment), (
        f"the pin carries a trailing `# v<x.y.z>` comment naming the tag: {comment!r}"
    )


def test_release_please_reads_its_release_type_from_the_config_file() -> None:
    """A `release-type:` input switches the action out of manifest mode and the config
    file is then ignored — the type belongs in the config's root package instead."""
    step = _release_please_step()
    inputs = step.get("with") or {}
    assert "release-type" not in inputs, (
        f"no release-type input — it lives in release-please-config.json: {inputs}"
    )
    assert inputs["config-file"] == "release-please-config.json"
    assert inputs["manifest-file"] == ".release-please-manifest.json"
    assert step.get("id") == "release-please", (
        "the step is identified so its release_created/tag_name outputs can gate the "
        f"publishing jobs: {step}"
    )


# ---------------------------------------------------------------------------
# T-047-88 — one workflow, one trigger, one boolean deciding publication
# ---------------------------------------------------------------------------

_GATE = "needs.release-please.outputs.release_created == 'true'"


def test_the_folded_release_workflow_is_the_only_one_and_release_yml_is_gone() -> None:
    assert not (_WORKFLOWS / "release.yml").exists(), (
        "release.yml folded into release-please.yml (PLAN D8) and must not exist"
    )
    carriers = [
        name for name in _workflows() if _ACTION in (_WORKFLOWS / name).read_text(encoding="utf-8")
    ]
    assert carriers == ["release-please.yml"], (
        f"exactly one workflow may carry the release-please action: {carriers}"
    )


def test_no_workflow_listens_to_a_release_event_or_a_tag_push() -> None:
    offenders: list[str] = []
    for name, document in _workflows().items():
        triggers = document.get("on", document.get(True)) or {}
        if not isinstance(triggers, dict):
            triggers = {str(triggers): {}}
        if "release" in triggers:
            offenders.append(f"{name}: release event")
        push = triggers.get("push") or {}
        if isinstance(push, dict) and ("tags" in push or "tags-ignore" in push):
            offenders.append(f"{name}: push.tags")
    assert offenders == [], (
        f"same-workflow chaining only — a second trigger would need a PAT (PLAN D8): {offenders}"
    )


def test_every_publishing_job_needs_the_release_please_job_and_its_gate() -> None:
    jobs = _jobs()
    assert "release-please" in jobs
    ungated = []
    for name, job in jobs.items():
        if name == "release-please":
            continue
        needs = job.get("needs") or []
        needs = [needs] if isinstance(needs, str) else list(needs)
        if "release-please" not in needs or str(job.get("if") or "").strip() != _GATE:
            ungated.append(f"{name}: needs={needs} if={job.get('if')!r}")
    assert ungated == [], (
        f"every publishing job is gated on {_GATE!r} and reaches the release-please job: {ungated}"
    )


def test_no_job_needs_an_undefined_job() -> None:
    jobs = _jobs()
    dangling = []
    for name, job in jobs.items():
        needs = job.get("needs") or []
        needs = [needs] if isinstance(needs, str) else list(needs)
        dangling += [f"{name} -> {dep}" for dep in needs if dep not in jobs]
    assert dangling == [], f"needs: naming a job that does not exist: {dangling}"


def test_the_workflow_never_computes_a_version_or_a_tag_by_hand() -> None:
    """The action creates the tag and owns the version; `check`'s pyproject-vs-tags
    arithmetic and publish's `git tag` step died with it (T-047-88)."""
    offenders = [
        f"{job_name}: {line.strip()}"
        for job_name, job in _jobs().items()
        for step in job.get("steps") or []
        for line in (step.get("run") or "").splitlines()
        if "git ls-remote --tags" in line or "git tag " in line
    ]
    assert offenders == [], f"the tag is the action's to mint, never the workflow's: {offenders}"


def test_the_approve_job_keeps_the_release_gate_environment() -> None:
    approve = _jobs()["approve"]
    assert approve.get("environment") == "release-gate", (
        f"the human approval gate survives the fold: {approve.get('environment')}"
    )


def test_one_version_step_feeds_every_consumer_of_the_version() -> None:
    """One `id: version` step in `build` strips the tag's `v`; artifact name, approval
    message, pip install line and skills-repo subject all read that one output."""
    build = _jobs()["build"]
    assert build.get("outputs", {}).get("version") == "${{ steps.version.outputs.version }}"
    step = next(s for s in build["steps"] if s.get("id") == "version")
    assert step["env"] == {"TAG": "${{ needs.release-please.outputs.tag_name }}"}
    assert 'echo "version=${TAG#v}" >> "$GITHUB_OUTPUT"' in step["run"]
    assert "${{" not in step["run"], "no workflow expression inside a run body"
    consumers = [
        name
        for name, job in _jobs().items()
        if "needs.build.outputs.version" in yaml.safe_dump(job)
    ]
    assert set(consumers) == {"approve", "publish", "smoke-test", "publish-skills-repo"}, consumers


_MODEL_API_TEXT = re.compile(
    r"CLAUDE_API_KEY|ANTHROPIC_(?:API_)?KEY|api\.anthropic\.com", re.IGNORECASE
)


def _uses(document: Any) -> list[str]:
    """Every `uses:` a workflow declares — job-level reusable workflows and step actions."""
    jobs = (document or {}).get("jobs") or {}
    found = [str(job.get("uses", "")) for job in jobs.values() if isinstance(job, dict)]
    for job in jobs.values():
        for step in (job.get("steps") or []) if isinstance(job, dict) else []:
            if isinstance(step, dict) and "uses" in step:
                found.append(str(step["uses"]))
    return [use for use in found if use]


def test_no_workflow_calls_a_model_api() -> None:
    """P-33 (ADR 0025): no CI job calls a model API — no `anthropics/*` action (any case,
    any quoting, `.yml` or `.yaml`) and no model API secret or endpoint in any workflow;
    the security review is the local dd-code-reviewer lens."""
    offenders: list[str] = []
    for path in sorted([*_WORKFLOWS.glob("*.yml"), *_WORKFLOWS.glob("*.yaml")]):
        text = path.read_text(encoding="utf-8")
        offenders += [f"{path.name}: uses {u}" for u in _uses(yaml.safe_load(text))
                      if u.lower().startswith("anthropics/")]  # fmt: skip
        offenders += [f"{path.name}:{n}: {line.strip()}"
                      for n, line in enumerate(text.splitlines(), start=1)
                      if _MODEL_API_TEXT.search(line)]  # fmt: skip
    assert offenders == [], "a workflow calls a model API:\n" + "\n".join(offenders)


def _guard_exit(head: str, base: str) -> int:
    """Run pr-source-guard's shell step exactly as CI does, for one (head, base) pair."""
    import subprocess

    ci = yaml.safe_load((_WORKFLOWS / "ci.yml").read_text(encoding="utf-8"))
    step = ci["jobs"]["pr-source-guard"]["steps"][0]
    env = {"HEAD_REF": head, "BASE_REF": base, "PATH": "/usr/bin:/bin"}
    return subprocess.run(["bash", "-c", step["run"]], env=env, capture_output=True).returncode


@pytest.mark.parametrize(
    ("head", "base", "allowed"),
    [
        ("develop", "main", True),
        ("release-please--branches--main", "main", True),
        ("feature/0.4.7", "main", False),
        ("release-please--branches--develop", "main", False),
        ("feature/0.4.7", "develop", True),
        ("develop", "develop", False),
    ],
)
def test_pr_source_guard_admits_the_release_pr_into_main(
    head: str, base: str, allowed: bool
) -> None:
    """ADR 0021: promote is merging release-please's release PR, so main accepts exactly
    develop and release-please's own branch; develop accepts only feature/{M.m.p}."""
    assert (_guard_exit(head, base) == 0) is allowed
